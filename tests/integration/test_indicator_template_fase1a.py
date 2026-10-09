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

    def test_missing_source_definition_is_explicit_in_both_renderers(self):
        client = app.test_client()
        with patch("app.indicator_view._official_definition", return_value=None):
            response = client.get(NO_DEFINITION)
        page = response.get_data(as_text=True)
        self.assertIn("La fonte non fornisce una definizione specifica", page)
        self.assertIn("Non ricostruiamo numeratore o denominatore", page, "limite definizione assente non visibile")
        dataset_json = re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
        self.assertIn("Non ricostruiamo numeratore o denominatore", json.loads(dataset_json.group(1))["variableMeasured"]["description"])

        with patch.dict(os.environ, {"DIVARIO_V1_STRICT": ""}), \
             patch("app.design.derive", side_effect=RuntimeError("force fallback")), \
             patch("app.indicator_view._official_definition", return_value=None):
            fallback = client.get(NO_DEFINITION).get_data(as_text=True)
        self.assertNotIn('data-v1="indicatore"', fallback)
        self.assertIn("La fonte non fornisce una definizione specifica", fallback)
        self.assertIn('data-kpi="central-band"', fallback)

    def test_selected_province_has_denominated_comparison_and_series(self):
        family, raw_id = sources.parse_indicator_code("bes-06POL001P")
        view = build_indicator_view(family, raw_id)
        level = next(item for item in view["levels"] if item["key"] == "provincia")
        self.assertGreater(len(level["annual_means"]), 1)
        page = app.test_client().get(PROVINCIAL).get_data(as_text=True)
        self.assertIn("confronto con la media semplice delle province", page.lower(), "confronto provinciale non denominato")
        self.assertIn("serie storica", page.lower(), "serie storica provinciale assente")


if __name__ == "__main__":
    unittest.main()
