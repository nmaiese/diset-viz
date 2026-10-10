"""Fase 1a: significato, confronti e riepilogo delle schede indicatore."""

import json
import os
import re
import unittest
from unittest.mock import patch

from app import app, design, sources
from app.indicator_view import build_indicator_view
from scripts.fetch_definitions import load_definitions


REGIONAL = "/indicatore/eta-media-della-popolazione/ter-920"
PROVINCIAL = "/indicatore/partecipazione-elettorale-elezioni-regionali/bes-06POL001P"
COMPLEX = "/indicatore/energia-elettrica-da-fonti-rinnovabili/bes-10AMB016"
NO_DEFINITION = "/indicatore/retribuzione-media-annua-dei-lavoratori-dipendenti/bes-04BEC002P"


class IndicatorTemplateFase1a(unittest.TestCase):
    def test_model_carries_verified_source_definitions_and_no_guess_for_missing(self):
        definitions = load_definitions()
        for code in ("ter-920", "bes-06POL001P", "bes-10AMB016", "eur-rd_e_gerdreg",
                     "dem-BIRTHRATE", "ipr-pil-per-abitante"):
            with self.subTest(code=code):
                family, raw_id = sources.parse_indicator_code(code)
                view = build_indicator_view(family, raw_id)
                definition_id = sources.SOURCES[family]["internal_prefix"] + raw_id
                if family == "territorial":
                    definition_id = raw_id
                expected = definitions.get(definition_id)
                self.assertEqual(view["meta"].get("official_definition"), expected["definizione"])
        family, raw_id = sources.parse_indicator_code("bes-04BEC002P")
        with patch("app.indicator_view._official_definition", return_value=None):
            view = build_indicator_view(family, raw_id)
        self.assertIsNone(view["meta"].get("official_definition"))

    def test_definition_id_uses_source_prefix_for_each_internal_family(self):
        cases = {
            "territorial": ("920", "920"),
            "bes": ("06POL001P", "bes:06POL001P"),
            "eurostat": ("rd_e_gerdreg", "eur:rd_e_gerdreg"),
            "istat_demografia": ("BIRTHRATE", "dem:BIRTHRATE"),
            "istat_provinciale": ("pil-per-abitante", "ipr:pil-per-abitante"),
        }
        for family, (raw_id, expected) in cases.items():
            with self.subTest(family=family):
                source_id = sources.SOURCES[family]["internal_prefix"] + raw_id
                self.assertEqual(source_id or raw_id, expected)

    def test_regional_provincial_and_complex_pages_show_measure_without_generic_definition(self):
        client = app.test_client()
        for path in (REGIONAL, PROVINCIAL, COMPLEX):
            with self.subTest(path=path):
                response = client.get(path)
                page = response.get_data(as_text=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn("data-v1=\"indicatore\"", page)
                self.assertIn("Definizione della fonte", page)
                self.assertNotIn("gruppo di riferimento definito dalla fonte", page)
                self.assertNotRegex(page, r"\d[,.]\d\s*(?:×|volte)\b")
                self.assertNotIn("sopra la media semplice e", page)
                self.assertNotRegex(page, r"\d+ sopra e \d+ sotto")
                self.assertNotIn('data-kpi="gap-ratio"', page)
                self.assertIn('data-kpi="focus-comparison"', page)
                self.assertIn('data-kpi="median-value"', page)
                self.assertIn('data-kpi="central-band"', page)

    def test_source_definition_matches_visible_markdown_and_jsonld(self):
        family, raw_id = sources.parse_indicator_code("ter-920")
        definition = build_indicator_view(family, raw_id)["meta"]["official_definition"]
        client = app.test_client()
        html = client.get(REGIONAL).get_data(as_text=True)
        self.assertIn(definition, html)
        block = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        dataset = json.loads(block.group(1))
        self.assertEqual(dataset["variableMeasured"]["description"], definition)
        markdown = client.get(REGIONAL, headers={"Accept": "text/markdown"}).get_data(as_text=True)
        self.assertIn("## Definizione della fonte", markdown)
        self.assertIn(definition, markdown)

    def test_initial_distribution_and_filter_payload_keep_distinct_units(self):
        page = app.test_client().get(COMPLEX).get_data(as_text=True)
        for key in ("median-value", "central-band"):
            with self.subTest(key=key):
                value = re.search(r'data-kpi="' + key + r'"[^>]*>(.*?)</dd>', page, re.S)
                self.assertIsNotNone(value)
                self.assertTrue(value.group(1).strip().endswith("%"), value.group(1))
        gap = re.search(r'data-kpi="gap-value"[^>]*>(.*?)</dd>', page, re.S)
        self.assertIsNotNone(gap)
        self.assertTrue(gap.group(1).strip().endswith("punti percentuali"), gap.group(1))
        payload = re.search(r'<script type="application/json" data-explore-data>(.*?)</script>', page, re.S)
        self.assertIsNotNone(payload)
        self.assertEqual(json.loads(payload.group(1))["changeUnit"], "punti percentuali")

    def test_missing_source_definition_is_explicit_in_both_renderers(self):
        client = app.test_client()
        no_definition = "/indicatore/densita-popolazione-a-rischio-frane/ter-531"
        with patch("app.indicator_view._official_definition", return_value=None):
            response = client.get(no_definition)
        page = response.get_data(as_text=True)
        markdown = client.get(no_definition, headers={"Accept": "text/markdown"}).get_data(as_text=True)
        self.assertIn("La fonte non fornisce una definizione specifica", page)
        self.assertIn("Non ricostruiamo numeratore o denominatore", page, "limite definizione assente non visibile")
        self.assertIn("Non ricostruiamo numeratore o denominatore", markdown)
        dataset_json = re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
        dataset = json.loads(dataset_json.group(1))
        self.assertNotIn("description", dataset["variableMeasured"])

        with patch.dict(os.environ, {"DIVARIO_V1_STRICT": ""}), \
             patch("app.design.derive", side_effect=RuntimeError("force fallback")), \
             patch("app.indicator_view._official_definition", return_value=None):
            fallback = client.get(no_definition).get_data(as_text=True)
        self.assertNotIn('data-v1="indicatore"', fallback)
        self.assertIn("La fonte non fornisce una definizione specifica", fallback)
        self.assertIn("Non ricostruiamo numeratore o denominatore", fallback)
        self.assertIn('data-kpi="central-band"', fallback)

    def test_selected_province_has_denominated_comparison_and_series(self):
        family, raw_id = sources.parse_indicator_code("bes-06POL001P")
        view = build_indicator_view(family, raw_id)
        level = next(item for item in view["levels"] if item["key"] == "provincia")
        self.assertGreater(len(level["annual_means"]), 1)
        page = app.test_client().get(PROVINCIAL).get_data(as_text=True)
        self.assertIn("confronto con la media semplice delle province", page.lower(), "confronto provinciale non denominato")
        self.assertIn("serie storica", page.lower(), "serie storica provinciale assente")


class TitoloEnergiaRinnovabile(unittest.TestCase):
    """Il `<title>` di bes-10AMB016 non fa una forbice fra rapporti di regioni diverse."""

    @staticmethod
    def _head(path):
        html = app.test_client().get(path).get_data(as_text=True)
        title = re.search(r"<title>(.*?)</title>", html, re.S).group(1)
        canonical = re.search(r'rel="canonical" href="([^"]*)"', html).group(1)
        description = re.search(r'name="description" content="([^"]*)"', html).group(1)
        return title, canonical, description

    def test_title_senza_intervallo_con_denominatore(self):
        title, canonical, description = self._head(COMPLEX)
        self.assertEqual(title, "Energia elettrica da rinnovabili sul consumo interno lordo")
        self.assertNotIn("328", title)
        self.assertNotRegex(title, r"\bdal\b.*\bal\b")
        self.assertLessEqual(len(title), 60)
        self.assertEqual(canonical, "https://divarioitalia.it" + COMPLEX)
        self.assertTrue(description.startswith("Il dato BES sull&#39;elettricità da rinnovabili"))

    def test_vista_province_senza_intervallo(self):
        title, canonical, description = self._head(COMPLEX + "/province")
        self.assertEqual(title, "Elettricità da rinnovabili per provincia")
        self.assertEqual(canonical, "https://divarioitalia.it" + COMPLEX + "/province")
        self.assertIn("da 450% (Sondrio) a 4,5% (Genova)", description)

    def test_schede_gemelle_senza_intervallo(self):
        attesi = {
            "/indicatore/consumi-di-energia-elettrica-coperti-da-fonti-rinnovabili-incluso-idro/ter-85":
                "Elettricità rinnovabile con idro sui consumi interni lordi",
            "/indicatore/consumi-di-energia-elettrica-coperti-da-fonti-rinnovabili-escluso-idro/ter-86":
                "Elettricità rinnovabile senza idro sui consumi interni lordi",
            "/indicatore/quantita-di-frazione-umida-trattata-in-impianti-di-compostaggio-per-la-produzion/ter-53":
                "Umido a compostaggio sull'umido dei rifiuti urbani",
        }
        for path, atteso in attesi.items():
            with self.subTest(path=path):
                title, canonical, description = self._head(path)
                self.assertEqual(title.replace("&#39;", "'"), atteso)
                self.assertNotIn("%", title)
                self.assertLessEqual(len(title), 60)
                self.assertEqual(canonical, "https://divarioitalia.it" + path)
                self.assertGreater(len(description), 40)

    def test_scheda_quota_vera_tiene_l_intervallo(self):
        title, _, _ = self._head(
            "/indicatore/potenza-efficiente-lorda-delle-fonti-rinnovabili/ter-81")
        self.assertIn("dal 207% al 33,9%", title)


if __name__ == "__main__":
    unittest.main()
