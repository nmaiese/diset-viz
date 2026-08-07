"""La catena delle fonti, dal corpus fino alla pagina che il lettore vede.

Il difetto che questo file esiste per impedire, trovato leggendo `ter-176` e
non da nessuna guardia: **l'articolo scriveva "Eurostat scrive che quando
l'economia riparte..." e il blocco fonti visibile portava solo Istat.**

Perche' nessun controllo lo vedeva. L'identificatore stava nel campo `corpus`
a livello di entry; il lint validava quel campo; la pagina rendeva `fonti`, un
altro campo, trascritto a mano. Due liste che parlavano della stessa cosa e non
si parlavano fra loro, con in mezzo un passaggio manuale che in una catena a
zero tempo umano non esiste.

Cosa vedeva il lettore: un'attribuzione a un'istituzione **senza un modo per
controllarla**. Su un sito di dati pubblici e' peggio di un errore, perche' un
errore si corregge e questa somiglia a una fonte inventata.

La riparazione ha tre pezzi, e questo file li tiene insieme:

1. l'attribuzione ha un posto, `sections[].claims`, non una lista in coda;
2. le fonti visibili si **derivano** da li' (`visible_sources`), non si
   trascrivono;
3. il lint blocca chi nomina un'istituzione che la pagina non mostra.
"""
import copy
import json
import os
import unittest

from app import app, indicator_texts
from officina import lint

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
                        "cio' che la prosa attribuisce non puo' restare invisibile")

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
        """Le citazioni vere portano caratteri che `content/STYLE.md` vieta."""
        entry = {"sections": [{"claims": ["eurostat-lunga-durata-ciclo"]}]}
        for item in indicator_texts.visible_sources(entry):
            for banned in lint.BANNED:
                self.assertNotIn(banned, item["testo"])


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
        """"Istat lo calcola come media annua" e' definizione, non citazione.

        Senza questa esclusione la regola bocciava sei articoli veri: la fonte
        del dato la pagina la mostra sempre nella propria riga "Fonte".
        """
        entry = {"lead": "Istat lo calcola come media annua.", "sections": []}
        self.assertEqual(
            lint.check_named_institutions_are_visible(entry, key="15"), [])

    def test_the_whole_catalogue_is_clean(self):
        """Su una regola bloccante un falso positivo costa piu' di un falso
        negativo: se questo cade, la lista di `_institution_names` e' troppo larga."""
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
