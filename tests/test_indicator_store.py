"""Lo store degli articoli, un file per indicatore.

Il guasto che chiude: scrittore e revisore condividono il perimetro, girano
tutti e due ogni giorno, e finche' la prosa e' stata un JSON unico da 365 voci
ogni loro modifica riscriveva l'intero file. Due run vicine su articoli diversi
producevano un conflitto su un file che nessun agente puo' risolvere leggendolo.

Quello che i test qui devono garantire non e' che il formato sia bello: e' che
il travaso non abbia perso niente e che la codifica delle chiavi sia
reversibile. Una chiave che non torna indietro non e' un file mal chiamato, e'
un articolo che sparisce dalla pagina senza che nessun errore lo dica.
"""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import indicator_store


class TheKeyEncodingIsReversible(unittest.TestCase):
    """Il nome del file e' la chiave, quindi deve tornare indietro esatta."""

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
        """La codifica regge perche' nessuna chiave del catalogo contiene gia'
        un doppio underscore. Se un giorno ne arrivasse una, il posto dove
        accorgersene e' qui e non la pagina vuota di un indicatore."""
        with self.assertRaises(indicator_store.StoreError):
            indicator_store.filename_for("famiglia__strana")

    def test_no_key_in_the_catalogue_breaks_the_assumption(self):
        for key in indicator_store.load_all():
            self.assertNotIn(indicator_store.FILENAME_SEP, key, key)
            self.assertLessEqual(key.count(":"), 1, key)


class TheStoreReadsBackWhatItWrote(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_an_entry_comes_back_identical(self):
        entry = {
            "lead": "Un lead con accenti: perche' no.",
            "sections": [{"role": "quadro", "h": None, "body": "Il quadro."}],
            "fonti": [], "vintage": 2024, "level": "regione",
        }
        indicator_store.write("bes:10AMB004", entry, root=self.root)
        self.assertEqual(indicator_store.read("bes:10AMB004", root=self.root), entry)
        self.assertEqual(indicator_store.load_all(self.root), {"bes:10AMB004": entry})

    def test_the_key_field_is_written_but_never_returned(self):
        """Il file dice di che cosa parla, cosi' uno aperto a mano si capisce e
        uno rinominato per sbaglio si riconosce. Fuori dal modello pero': i
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
        """E' tutta la ragione per cui lo store esiste. Se scrivere un articolo
        toccasse un file condiviso, due stadi che lavorano su articoli diversi
        continuerebbero a collidere."""
        indicator_store.write("920", {"lead": "a"}, root=self.root)
        indicator_store.write("bes:10AMB004", {"lead": "b"}, root=self.root)
        self.assertEqual(
            sorted(p.name for p in indicator_store.paths(self.root)),
            ["920.json", "bes__10AMB004.json"],
        )


class TheMigrationLostNothing(unittest.TestCase):
    """Il travaso e' avvenuto una volta sola e non e' piu' ripetibile sul file
    vero, che non e' piu' in repo. Quello che resta verificabile per sempre e'
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
            # E la lettura del file unico passa dallo stesso ingresso, che e'
            # cio' che permette a `--texts` di puntare a una vecchia copia.
            self.assertEqual(indicator_store.load_all(source), legacy)

    def test_the_committed_store_is_readable_and_not_empty(self):
        entries = indicator_store.load_all()
        self.assertGreater(len(entries), 300)
        for key, entry in entries.items():
            self.assertIsInstance(entry, dict, key)


if __name__ == "__main__":
    unittest.main()
