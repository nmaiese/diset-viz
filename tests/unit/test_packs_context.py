"""Il corpus: la licenza di spiegare, e i modi in cui potrebbe diventare bugia.

Questo modulo da' agli articoli il diritto di dire perche' i numeri si muovono.
E' un potere che il progetto ha sempre negato, e per una buona ragione: da una
serie non si deduce una causa. Il diritto regge solo finche' le citazioni sono
vere e attribuite, quindi la maggior parte di questi test guarda i modi in cui
una citazione puo' smettere di esserlo.
"""
import unittest

from packs import build as build_module


class ThePackSaysWhatTheNumberMeasures(unittest.TestCase):
    """Il difetto che la prima misura ha trovato, e non era di prosa.

    Il pacchetto portava nome, unita', verso e anni: niente numeratore, niente
    denominatore. Su `ter-30` la fonte scrive "visitatori dei circuiti sul
    totale di musei e istituti similari appartenenti ai circuiti", e i due
    scrittori, non avendolo, hanno dedotto dal nome "domanda culturale" un
    rapporto per circuito. Prosa piu' fluida di prima, indicatore diverso.

    A un agente che non puo' cercare, cio' che non gli si da' non esiste: le
    righe erano gia' su disco e gia' lette da `packs/build.py`, che ne prendeva
    solo la colonna delle note.
    """

    def test_the_official_definition_reaches_the_pack(self):
        definizione = build_module.official_definition("territorial", "30")
        self.assertIsNotNone(definizione)
        self.assertIn("sul totale di musei", definizione["definizione"])
        self.assertIn("Visitatori dei circuiti", definizione["dati_di_base"])

    def test_a_family_without_metadata_says_nothing_instead_of_guessing(self):
        self.assertIsNone(build_module.official_definition("bes", "10AMB004"))

    def test_an_unknown_id_says_nothing(self):
        self.assertIsNone(build_module.official_definition("territorial", "999999"))

    def test_the_rendered_pack_carries_the_denominator(self):
        pack = build_module.build_pack("territorial", "30")
        testo = build_module.render(pack)
        self.assertIn("CHE COSA MISURA", testo)
        self.assertIn("sul totale di musei", testo)
        self.assertIn("e' un'etichetta, non una definizione", testo)

    def test_without_a_definition_the_pack_forbids_deducing_one(self):
        pack = dict(build_module.build_pack("territorial", "30"), definition=None)
        testo = build_module.render(pack)
        self.assertIn("Non dedurla dal nome", testo)

from packs import context


def claim(**overrides):
    base = {
        "id": "prova-1",
        "source_id": "istat-demografia",
        "url": "https://example.org/x",
        "fetched_at": "2026-08-07",
        "quote": "Una citazione abbastanza lunga da reggere un'attribuzione vera.",
        "themes": ["Salute, demografia e cura"],
        "indicators": [],
    }
    base.update(overrides)
    return base


class WhatMakesAClaimCitable(unittest.TestCase):
    def test_a_complete_claim_has_no_problems(self):
        self.assertEqual(context.problems(claim()), [])

    def test_without_a_url_it_is_indistinguishable_from_an_invention(self):
        self.assertIn("manca url", context.problems(claim(url="")))

    def test_without_a_reading_date_nobody_can_check_it_again(self):
        self.assertIn("manca fetched_at", context.problems(claim(fetched_at="")))

    def test_an_unknown_institution_is_refused(self):
        found = context.problems(claim(source_id="il-mio-blog"))
        self.assertTrue(any("fonte sconosciuta" in item for item in found))

    def test_a_claim_with_no_theme_reaches_nobody(self):
        self.assertIn("nessuno tema".replace("nessuno", "nessun"),
                      " ".join(context.problems(claim(themes=[]))))

    def test_a_fragment_cannot_carry_an_attribution(self):
        found = context.problems(claim(quote="cresce."))
        self.assertTrue(any("troppo corta" in item for item in found))


class Matching(unittest.TestCase):
    def setUp(self):
        self.saved = context.claims
        self.fixtures = [
            claim(id="tema-vecchia", fetched_at="2020-01-01"),
            claim(id="tema-nuova", fetched_at="2026-01-01"),
            claim(id="indicatore", indicators=["ter:920"], fetched_at="2019-01-01"),
            claim(id="rotta", url="", indicators=["ter:920"]),
        ]
        context.claims = lambda: self.fixtures

    def tearDown(self):
        context.claims = self.saved

    def test_a_claim_about_the_indicator_beats_one_about_the_theme(self):
        """Anche se e' piu' vecchia: e' piu' pertinente, e la pertinenza vince."""
        found = context.for_indicator("ter:920", "Salute, demografia e cura")
        self.assertEqual(found[0]["id"], "indicatore")

    def test_within_the_same_relevance_the_newest_wins(self):
        found = context.for_theme("Salute, demografia e cura")
        self.assertEqual([item["id"] for item in found][:2],
                         ["tema-nuova", "tema-vecchia"])

    def test_a_broken_claim_is_never_offered(self):
        ids = [item["id"] for item in
               context.for_indicator("ter:920", "Salute, demografia e cura")]
        self.assertNotIn("rotta", ids)

    def test_an_unknown_theme_gets_nothing_rather_than_something_close(self):
        self.assertEqual(context.for_theme("Tema che non esiste"), [])
        self.assertEqual(context.for_theme(None), [])


class TheContextBlock(unittest.TestCase):
    def setUp(self):
        self.saved = context.claims
        context.claims = lambda: [claim(id="uno")]

    def tearDown(self):
        context.claims = self.saved

    def test_it_names_the_ids_a_dinamica_section_may_carry(self):
        block = context.as_context("ter:920", "Salute, demografia e cura", "scala")
        self.assertEqual(block["citabili"], ["uno"])
        self.assertFalse(block["senza_contesto"])
        self.assertEqual(block["scala_umana"], "scala")

    def test_an_empty_corpus_says_so_instead_of_staying_quiet(self):
        """Il silenzio qui sarebbe un invito a dedurre la causa dai dati."""
        context.claims = lambda: []
        block = context.as_context("ter:920", "Salute, demografia e cura")
        self.assertTrue(block["senza_contesto"])
        self.assertEqual(block["citabili"], [])


class TypographyTrap(unittest.TestCase):
    """La citazione verbatim puo' contenere cio' che la prosa vieta."""

    def test_the_verbatim_is_kept_and_a_prose_version_is_offered(self):
        context_claim = claim(
            quote="Come noto l’accumulo degli inquinanti in atmosfera cresce; d’inverno.")
        saved = context.claims
        context.claims = lambda: [context_claim]
        try:
            block = context.as_context("ter:920", "Salute, demografia e cura")
            spoken = block["affermazioni"][0]
            self.assertIn("’", spoken["citazione"], "il verbatim deve restare intatto")
            for banned in ("’", ";", "—", "…"):
                self.assertNotIn(banned, spoken["citazione_per_prosa"])
        finally:
            context.claims = saved


class TheRealCorpus(unittest.TestCase):
    def test_every_claim_on_disk_is_citable(self):
        broken = {item.get("id", "?"): context.problems(item)
                  for item in context.reload_corpus()
                  if context.problems(item)}
        self.assertEqual(broken, {})

    def test_the_registry_of_institutions_is_loaded(self):
        self.assertIn("ispra-snpa", context.sources())
        self.assertIn("istat-demografia", context.sources())

    def test_there_is_something_in_it(self):
        self.assertTrue(context.reload_corpus(),
                        "corpus vuoto: nessun articolo potra' spiegare niente")

    def test_the_registry_is_not_also_listed_in_the_documentation(self):
        """Due copie di un elenco sono due elenchi che divergono.

        `docs/SECONDARY_SOURCES.md` teneva la stessa tabella, e questa e' la
        deriva che il progetto ha gia' pagato una volta. Il documento adesso
        punta al JSON: se qualcuno rimette la tabella, questo test lo dice.
        """
        import os

        doc = os.path.join(os.path.dirname(context.ROOT), "..", "docs",
                           "SECONDARY_SOURCES.md")
        with open(os.path.normpath(doc), encoding="utf-8") as handle:
            text = handle.read()
        listed = [item["institution"] for item in context.sources().values()
                  if item["institution"] in text]
        self.assertLessEqual(
            len(listed), 2,
            f"il documento rielenca {len(listed)} istituzioni: {listed[:5]}")


if __name__ == "__main__":
    unittest.main()
