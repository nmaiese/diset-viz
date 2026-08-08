"""Lo store degli articoli, un file per indicatore.

Il guasto che ha chiuso: scrittore e revisore condividevano il perimetro,
giravano tutti e due ogni giorno, e finché la prosa è stata un JSON unico da
365 voci ogni loro modifica riscriveva l'intero file. Due run vicine su articoli
diversi producevano un conflitto su un file che nessun agente può risolvere
leggendolo.

Quello che i test qui devono garantire non è che il formato sia bello: è che
il travaso non abbia perso niente e che la codifica delle chiavi sia
reversibile. Una chiave che non torna indietro non è un file mal chiamato, è
un articolo che sparisce dalla pagina senza che nessun errore lo dica.

Qui c'è solo ciò che gira su file temporanei e costanti. Le due letture dello
store **committato** stanno in `tests/integration/test_indicator_store_live.py`.
"""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import indicator_store


class TheKeyEncodingIsReversible(unittest.TestCase):
    """Il nome del file è la chiave, quindi deve tornare indietro esatta."""

    CASES = (
        "1",
        "920",
        "bes:10AMB004",
        "bes:09PAE009-N25",
        "bes:SDG-405",
        "eur:rd_e_gerdreg",
        "multiscopo:MULTI_ABIT_SPESA_REDDITO",
        "dem:OLDAGEDEPR",
    )

    def test_every_shape_of_key_survives_the_round_trip(self):
        for key in self.CASES:
            with self.subTest(key=key):
                name = indicator_store.filename_for(key)
                self.assertEqual(indicator_store.key_of(name), key)
                self.assertNotIn(":", name)

    def test_a_key_that_would_be_ambiguous_is_refused_instead_of_mangled(self):
        """La codifica regge perché nessuna chiave del catalogo contiene già
        un doppio underscore. Se un giorno ne arrivasse una, il posto dove
        accorgersene è qui e non la pagina vuota di un indicatore."""
        with self.assertRaises(indicator_store.StoreError):
            indicator_store.filename_for("famiglia__strana")


class TheStoreReadsBackWhatItWrote(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_an_entry_comes_back_identical(self):
        entry = {
            "lead": "Un lead con accenti: perché no.",
            "sections": [{"role": "quadro", "h": None, "body": "Il quadro."}],
            "fonti": [], "vintage": 2024, "level": "regione",
        }
        indicator_store.write("bes:10AMB004", entry, root=self.root)
        self.assertEqual(indicator_store.read("bes:10AMB004", root=self.root), entry)
        self.assertEqual(indicator_store.load_all(self.root), {"bes:10AMB004": entry})

    def test_the_key_field_is_written_but_never_returned(self):
        """Il file dice di che cosa parla, così uno aperto a mano si capisce e
        uno rinominato per sbaglio si riconosce. Fuori dal modello però: i
        consumatori devono vedere lo stesso dizionario di prima del travaso, o
        il travaso non sarebbe stato a costo zero per loro."""
        indicator_store.write("920", {"lead": "x"}, root=self.root)
        on_disk = json.loads((self.root / "920.json").read_text(encoding="utf-8"))
        self.assertEqual(on_disk["key"], "920")
        self.assertNotIn("key", indicator_store.read("920", root=self.root))

    def test_a_file_filed_under_the_wrong_name_is_refused(self):
        """Il caso peggiore fra quelli possibili: la pagina si renderizza lo
        stesso, con la prosa di un altro indicatore sotto i numeri giusti."""
        indicator_store.write("920", {"lead": "x"}, root=self.root)
        (self.root / "921.json").write_text(
            json.dumps({"key": "920", "lead": "x"}), encoding="utf-8")
        with self.assertRaises(indicator_store.StoreError):
            indicator_store.load_all(self.root)

    def test_two_writes_of_two_articles_touch_two_files(self):
        """È tutta la ragione per cui lo store esiste. Se scrivere un articolo
        toccasse un file condiviso, due stadi che lavorano su articoli diversi
        continuerebbero a collidere."""
        indicator_store.write("920", {"lead": "a"}, root=self.root)
        indicator_store.write("bes:10AMB004", {"lead": "b"}, root=self.root)
        self.assertEqual(
            sorted(p.name for p in indicator_store.paths(self.root)),
            ["920.json", "bes__10AMB004.json"],
        )


class TheMigrationLostNothing(unittest.TestCase):
    """Il travaso è avvenuto una volta sola e non è più ripetibile sul file
    vero, che non è più in repo. Quello che resta verificabile per sempre è
    che le due letture siano la stessa: un vecchio file unico e la directory
    che ne nasce devono produrre lo stesso dizionario, chiave per chiave."""

    def test_a_legacy_file_and_its_shards_read_the_same(self):
        legacy = {
            "1": {"lead": "Uno.", "sections": [], "fonti": [], "vintage": 2023},
            "bes:10AMB004": {"lead": "Due.", "sections": [], "fonti": [],
                             "vintage": 2024, "level": "regione",
                             "reviewed_at": "2026-07-27", "reviewed_vintage": 2024},
        }
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "indicator_texts.json"
            source.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")
            root = Path(tmp) / "indicators"
            count = indicator_store.migrate(source, root=root)
            self.assertEqual(count, len(legacy))
            self.assertEqual(indicator_store.load_all(root), legacy)
            # E la lettura del file unico passa dallo stesso ingresso, che è
            # ciò che permette a `--texts` di puntare a una vecchia copia.
            self.assertEqual(indicator_store.load_all(source), legacy)


class TheUrlFormResolvesToTheInternalKey(unittest.TestCase):
    """Il difetto che questo repo ha già pagato tre volte.

    La catena scrive i codici come `ter-920` e `bes-10AMB004`, lo store li tiene
    come `920` e `bes:10AMB004`. Un comando che accetta solo la seconda forma
    risponde "nessun articolo" proprio all'invocazione scritta nei prompt, e chi
    la incontra o la aggira o salta il passo. È successo in `review_queue`,
    poi in `prose_lint` una settimana dopo, poi in questo store il giorno in cui
    è stato scritto. Adesso la funzione è una sola e sta dove stanno le chiavi.
    """

    KEYS = ("1", "920", "bes:10AMB004", "bes:09PAE009-N25", "eur:rd_e_gerdreg")

    def test_the_url_form_the_prompts_use(self):
        for code, expected in (
            ("ter-920", "920"),
            ("bes-10AMB004", "bes:10AMB004"),
            ("eur-rd_e_gerdreg", "eur:rd_e_gerdreg"),
        ):
            with self.subTest(code=code):
                self.assertEqual(indicator_store.resolve_key(self.KEYS, code), expected)

    def test_the_internal_form_keeps_working(self):
        self.assertEqual(indicator_store.resolve_key(self.KEYS, "920"), "920")
        self.assertEqual(
            indicator_store.resolve_key(self.KEYS, "bes:10AMB004"), "bes:10AMB004")

    def test_a_bes_id_with_its_own_dashes_survives(self):
        """Gli id BES contengono trattini, quindi il taglio è sul primo e uno
        solo: tagliare su tutti perderebbe `-N25`."""
        self.assertEqual(
            indicator_store.resolve_key(self.KEYS, "bes-09PAE009-N25"),
            "bes:09PAE009-N25",
        )

    def test_an_unknown_code_is_none_not_a_guess(self):
        self.assertIsNone(indicator_store.resolve_key(self.KEYS, "ter-99999"))
        self.assertIsNone(indicator_store.resolve_key(self.KEYS, "boh"))

    def test_prose_lint_delegates_instead_of_keeping_a_copy(self):
        from scripts import prose_lint

        self.assertEqual(prose_lint.resolve_key(self.KEYS, "ter-920"), "920")

class OneBrokenArticleCostsOneArticle(unittest.TestCase):
    """Chi legge decide che cosa costa un file rotto, e le due risposte sono
    opposte per una ragione.

    Il cancello e la suite devono fermarsi forte: un file illeggibile è un
    difetto e va visto. L'app no. Con la lettura severa un solo file mal
    scritto solleva, il chiamante ripiega su un dizionario vuoto, e tutte e
    trecentosessantacinque le pagine perdono la prosa insieme senza un errore
    visibile da nessuna parte."""

    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        indicator_store.write("920", {"lead": "buono"}, root=self.root)
        (self.root / "999.json").write_text("{ questo non è json", encoding="utf-8")

    def test_the_strict_read_refuses_and_says_which_file(self):
        with self.assertRaises(indicator_store.StoreError) as caught:
            indicator_store.load_all(self.root)
        self.assertIn("999.json", str(caught.exception))

    def test_the_lenient_read_keeps_every_other_article(self):
        entries = indicator_store.load_all(self.root, strict=False)
        self.assertEqual(sorted(entries), ["920"])
        self.assertEqual(entries["920"]["lead"], "buono")

    def test_the_app_reads_leniently(self):
        """La prova che la scelta è cablata dove serve, non solo possibile."""
        import unittest.mock as mock

        from app import indicator_texts

        seen = {}

        def fake(root=None, strict=True):
            seen["strict"] = strict
            return {}

        with mock.patch.object(indicator_store, "load_all", fake):
            indicator_texts._load.cache_clear()
            indicator_texts._load()
        indicator_texts._load.cache_clear()
        self.assertFalse(seen["strict"])


if __name__ == "__main__":
    unittest.main()
