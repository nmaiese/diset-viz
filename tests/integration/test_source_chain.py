"""La catena delle fonti, dal corpus fino alla pagina che il lettore vede.

Il difetto che questo file esiste per impedire, trovato leggendo `ter-176` e
non da nessuna guardia: **l'articolo scriveva "Eurostat scrive che quando
l'economia riparte..." e il blocco fonti visibile portava solo Istat.**

Perché nessun controllo lo vedeva. L'identificatore stava nel campo `corpus`
a livello di entry; il lint validava quel campo; la pagina rendeva `fonti`, un
altro campo, trascritto a mano. Due liste che parlavano della stessa cosa e non
si parlavano fra loro, con in mezzo un passaggio manuale che in una catena a
zero tempo umano non esiste.

Cosa vedeva il lettore: un'attribuzione a un'istituzione **senza un modo per
controllarla**. Su un sito di dati pubblici è peggio di un errore, perché un
errore si corregge e questa somiglia a una fonte inventata.

La riparazione ha tre pezzi, e questo file li tiene insieme:

1. l'attribuzione ha un posto, `sections[].claims`, non una lista in coda;
2. le fonti visibili si **derivano** da lì (`visible_sources`), non si
   trascrivono;
3. il lint blocca chi nomina un'istituzione che la pagina non mostra.
"""
import copy
import json
import os
import unittest
import unittest.mock

from app import app, indicator_texts
from officina import lint
from packs import context

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _entry(path="176.json"):
    with open(os.path.join(ROOT, "content", "indicators", path), encoding="utf-8") as h:
        return json.load(h)


class AttributionHasAPlace(unittest.TestCase):
    def test_a_section_declares_what_it_leans_on(self):
        found = indicator_texts.cited_claims(
            {"sections": [{"role": "dinamica", "claims": ["uno"]},
                          {"role": "limiti"}]})
        self.assertEqual(found, ["uno"])

    def test_the_old_entry_level_field_is_still_read(self):
        """Le entry scritte prima usavano `corpus` da solo: non si rompono."""
        self.assertEqual(
            indicator_texts.cited_claims({"corpus": ["vecchio"], "sections": []}),
            ["vecchio"])

    def test_the_two_are_merged_without_duplicates(self):
        found = indicator_texts.cited_claims(
            {"corpus": ["a"], "sections": [{"claims": ["a", "b"]}]})
        self.assertEqual(found, ["a", "b"])

    def test_junk_does_not_reach_the_page(self):
        self.assertEqual(indicator_texts.cited_claims(
            {"sections": [{"claims": [None, "", 7, "buono"]}]}), ["buono"])


class SourcesAreDerivedNotTranscribed(unittest.TestCase):
    def test_a_cited_claim_becomes_a_visible_source(self):
        entry = {"sections": [{"role": "dinamica",
                               "claims": ["eurostat-lunga-durata-ciclo"]}]}
        urls = [item["url"] for item in indicator_texts.visible_sources(entry)]
        self.assertTrue(any("eurostat" in url for url in urls),
                        "ciò che la prosa attribuisce non può restare invisibile")

    def test_the_authored_sources_survive(self):
        """Derivare non vuol dire sostituire: la fonte del dato resta."""
        entry = _entry()
        testi = [item["testo"] for item in indicator_texts.visible_sources(entry)]
        self.assertTrue(any("Istat" in testo for testo in testi))
        self.assertTrue(any("Eurostat" in testo for testo in testi))

    def test_the_same_url_is_not_listed_twice(self):
        entry = _entry()
        urls = [item["url"] for item in indicator_texts.visible_sources(entry)]
        self.assertEqual(len(urls), len(set(urls)))

    def test_the_derived_quote_is_typographically_clean(self):
        """Le pagine non portano i quattro caratteri vietati, citazioni comprese.

        L'invariante resta. Quello che cambia è **come** si tiene: prima la
        citazione veniva riscritta e mostrata lo stesso fra caporali, adesso o
        si mostra intera o non si mostra. Vedi
        `AQuoteIsShownWholeOrNotAtAll`."""
        entry = {"sections": [{"claims": ["eurostat-lunga-durata-ciclo"]}]}
        for item in indicator_texts.visible_sources(entry):
            for banned in lint.BANNED:
                self.assertNotIn(banned, item["testo"])


class AQuoteIsShownWholeOrNotAtAll(unittest.TestCase):
    """Fra caporali e attribuita a un'istituzione ci vanno le sue parole.

    `for_prose` esiste per **chi scrive**, che ci costruisce sopra senza far
    fallire il cancello tipografico, e il suo commento lo dice: cambia anche la
    punteggiatura. `app.indicator_texts` la usava per **rendere** la citazione,
    quindi la pagina attribuiva a un'istituzione una frase in cui un punto e
    virgola era diventato una virgola, mentre `fetch_corpus --verify` l'aveva
    controllata come stringa esatta.

    Le pagine però non portano i quattro caratteri di `content/STYLE.md`, ed è
    un invariante con dei test suoi. Le strade oneste sono perciò due, e questa
    è la seconda: mostrarla intera, oppure non mostrarla e lasciare
    l'istituzione con il proprio link, che è la provenienza vera. La terza,
    mostrare parole che l'istituzione non ha scritto, non è una strada.
    """

    def _fonti(self, quote):
        claim = {"id": "prova", "url": "https://example.org/x", "quote": quote,
                 "source_id": "istat", "themes": ["Lavoro e conciliazione"],
                 "fetched_at": "2026-08-07"}
        entry = {"sections": [{"claims": ["prova"]}]}
        with unittest.mock.patch.object(context, "claims", lambda: [claim]), \
             unittest.mock.patch.object(context, "sources",
                                        lambda: {"istat": {"institution": "Istat"}}):
            return indicator_texts.visible_sources(entry)

    def test_a_clean_quote_is_shown_verbatim(self):
        fonti = self._fonti("Il divario resta ampio nel Mezzogiorno.")
        self.assertEqual(fonti[0]["testo"],
                         "Istat. «Il divario resta ampio nel Mezzogiorno.»")

    def test_a_curly_apostrophe_is_only_a_glyph_and_is_straightened(self):
        """`’` e `'` sono lo stesso segno con due disegni: nessuna parola cambia,
        e non è fra i vietati."""
        fonti = self._fonti("L’accumulo degli inquinanti resta alto.")
        self.assertIn("L'accumulo", fonti[0]["testo"])
        self.assertIn("«", fonti[0]["testo"])

    def test_a_quote_with_a_semicolon_is_not_rewritten_into_one(self):
        """Il caso che faceva il danno: `;` diventava `,` e restava fra caporali."""
        fonti = self._fonti("Il dato sale al Nord; scende al Sud.")
        self.assertNotIn("«", fonti[0]["testo"],
                         "meglio nessuna citazione che una citazione cambiata")
        self.assertNotIn("Il dato sale al Nord, scende al Sud", fonti[0]["testo"])

    def test_and_the_institution_keeps_its_link(self):
        """Non si perde la provenienza: si perde solo la frase, che il lettore
        va a leggere alla fonte."""
        fonti = self._fonti("Il dato sale al Nord; scende al Sud.")
        self.assertEqual(fonti[0]["testo"], "Istat")
        self.assertEqual(fonti[0]["url"], "https://example.org/x")

    def test_the_writer_still_gets_the_copyable_version(self):
        """`for_prose` non cambia: chi scrive continua a ricevere una versione
        che, copiata, non fa fallire il cancello. Sono due mestieri diversi."""
        self.assertEqual(context.for_prose("Nord; Sud"), "Nord, Sud")
        self.assertEqual(context.for_quote("Nord; Sud"), "Nord; Sud")

    def test_the_banned_list_has_one_copy(self):
        """Tre copie della stessa riga erano due di troppo. `apply_curation` non
        può importare da `packs/`, quindi la sua la guarda un test."""
        from scripts import apply_curation
        self.assertEqual(lint.BANNED, context.BANNED)
        self.assertEqual(tuple(apply_curation.BANNED_CHARS), tuple(context.BANNED))


class TheDefectItselfCannotComeBack(unittest.TestCase):
    def test_naming_an_institution_without_showing_it_blocks(self):
        """La prova negativa: si toglie la citazione e il cancello parla."""
        entry = copy.deepcopy(_entry())
        entry.pop("corpus", None)
        for section in entry["sections"]:
            section.pop("claims", None)
        entry["fonti"] = [item for item in entry.get("fonti") or []
                          if "eurostat" not in (item.get("url") or "")]
        found = lint.check_named_institutions_are_visible(entry, key="176")
        self.assertEqual([f["rule"] for f in found], ["istituzione-senza-fonte"])
        self.assertEqual(found[0]["severity"], lint.BLOCKS)

    def test_the_repaired_article_passes(self):
        self.assertEqual(
            lint.check_named_institutions_are_visible(_entry(), key="176"), [])

    def test_the_source_of_the_data_is_not_an_attribution(self):
        """"Istat lo calcola come media annua" è definizione, non citazione.

        Senza questa esclusione la regola bocciava sei articoli veri: la fonte
        del dato la pagina la mostra sempre nella propria riga "Fonte".
        """
        entry = {"lead": "Istat lo calcola come media annua.", "sections": []}
        self.assertEqual(
            lint.check_named_institutions_are_visible(entry, key="15"), [])

    def test_the_whole_catalogue_is_clean(self):
        """Su una regola bloccante un falso positivo costa più di un falso
        negativo: se questo cade, la lista di `_institution_names` è troppo larga."""
        report = lint.lint_all()
        offenders = [key for key, found in report.items()
                     if any(f["rule"] == "istituzione-senza-fonte" for f in found)]
        self.assertEqual(offenders, [])


class ItReachesTheRenderedPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = app.test_client().get(
            "/indicatore/x/ter-176", follow_redirects=True).get_data(as_text=True)

    def test_the_institution_the_prose_names_is_linked_on_the_page(self):
        self.assertIn("Eurostat scrive", self.page)
        self.assertIn("ec.europa.eu/eurostat/statistics-explained", self.page)

    def test_the_data_source_is_still_there(self):
        self.assertIn("noi-italia.istat.it", self.page)


if __name__ == "__main__":
    unittest.main()
