"""G9: un indice, pari merito e dato assente nelle schede dei due livelli."""

import csv
import html
import io
import json
import re
import unittest
from unittest.mock import patch

from flask import render_template_string

from app import app
from app.design.common import ranking


REGIONAL = "/indicatore/eta-media-della-popolazione/ter-920"
PROVINCIAL = "/indicatore/partecipazione-elettorale-elezioni-regionali/bes-06POL001P"


class IndicatorTemplateG9(unittest.TestCase):
    def test_initial_focus_rank_excludes_simple_mean_reference(self):
        client = app.test_client()
        for path, expected in ((REGIONAL, "su 20 regioni"), (PROVINCIAL, "su 29 province"),
                               ("/indicatore/retribuzione-media-annua-dei-lavoratori-dipendenti/bes-04BEC002P", "su 107 province")):
            with self.subTest(path=path):
                page = client.get(path).get_data(as_text=True)
                summary = re.search(r'<p[^>]*data-focus-summary[^>]*>(.*?)</p>', page, re.S)
                self.assertIsNotNone(summary)
                self.assertIn(expected, html.unescape(re.sub(r"<[^>]+>", "", summary.group(1))))
                self.assertIn(f'Media semplice delle {expected.split("su ")[1]}', page)

    def test_definition_and_generated_example_use_verified_source_or_absence(self):
        client = app.test_client()
        for path in (PROVINCIAL, "/indicatore/densita-popolazione-a-rischio-frane/ter-531"):
            with self.subTest(path=path):
                page = client.get(path).get_data(as_text=True)
                markdown = client.get(path, headers={"Accept": "text/markdown"}).get_data(as_text=True)
                if path == PROVINCIAL:
                    self.assertIn("Percentuale di persone che hanno partecipato al voto", page)
                    self.assertIn("Percentuale di persone che hanno partecipato al voto", markdown)
                    self.assertNotIn("unità ogni 100", page)
                    self.assertNotIn("unità ogni 100", markdown)
                    self.assertNotIn(".zip", page)
                    dataset = json.loads(re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)[0])
                    self.assertIn("Percentuale di persone che hanno partecipato al voto",
                                  dataset["variableMeasured"]["description"])
                else:
                    self.assertIn("Non ricostruiamo numeratore o denominatore", page)
                    self.assertIn("Non ricostruiamo numeratore o denominatore", markdown)
                    dataset = json.loads(re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)[0])
                    self.assertNotIn("description", dataset["variableMeasured"])
                self.assertNotIn("Ministero dell'Interno, .", page)

    def test_generated_reading_and_apparatus_avoid_merit_and_gap_claims(self):
        page = app.test_client().get(PROVINCIAL).get_data(as_text=True)
        self.assertNotIn("posizione migliore", page)
        self.assertNotIn("situazione migliore", page)
        self.assertIn("distanza fra gli estremi", page)
        self.assertNotIn("Il divario è la distanza", page)
        from pathlib import Path
        fallback = (Path(app.root_path) / "templates" / "indicator_page.html").read_text(encoding="utf-8")
        self.assertIn("dal primo al terzo quartile", fallback)

    def test_annual_comparison_discloses_incomplete_overlap(self):
        page = app.test_client().get(PROVINCIAL).get_data(as_text=True)
        self.assertIn("campioni differiscono (17 e 29 territori)", page)
        self.assertIn("non consentono di attribuire la variazione", page)

    def test_js_year_rebuild_uses_only_observed_rows_for_rank(self):
        source = (app.root_path + "/static/js/v1.js")
        from pathlib import Path
        js = Path(source).read_text(encoding="utf-8")
        self.assertIn('function rows(year)', js)
        self.assertIn('filter(function (k) { return m[k] !== null; })', js)
        self.assertIn('var rank = list.findIndex', js)
        self.assertIn('"ª su " + list.length', js)
        self.assertIn("distribution.hidden = median === null", js)
        page = app.test_client().get(PROVINCIAL).get_data(as_text=True)
        payload = json.loads(re.search(
            r'<script type="application/json" data-explore-data>(.*?)</script>', page, re.S
        ).group(1))
        self.assertEqual(sum(value is not None for value in payload["matrix"]["2015"].values()), 17)
        self.assertEqual(sum(value is not None for value in payload["matrix"]["2024"].values()), 29)

    def test_one_keyboard_navigation_with_valid_targets_on_both_levels(self):
        client = app.test_client()
        for path in (REGIONAL, PROVINCIAL):
            with self.subTest(path=path):
                page = client.get(path).get_data(as_text=True)
                self.assertEqual(page.count('<nav class="toc" aria-label="In questa pagina">'), 1)
                self.assertNotIn("Le domande di questo indicatore", page)
                nav = re.search(r'<nav class="toc"[^>]*>(.*?)</nav>', page, re.S).group(1)
                targets = re.findall(r'href="#([^"]+)"', nav)
                self.assertEqual(len(targets), len(set(targets)))
                self.assertTrue(all(f'id="{target}"' in page for target in targets))
                self.assertIn('data-query-intent="classifica"', nav)

    def test_equal_values_share_rank_and_missing_is_not_zero(self):
        for level_key in ("regione", "provincia"):
            with self.subTest(level=level_key):
                level = {
                    "plural": "regioni" if level_key == "regione" else "province",
                    "observations": [
                        {"key": "a", "name": "A", "value": 2},
                        {"key": "b", "name": "B", "value": 2},
                        {"key": "c", "name": "C", "value": 0},
                    ],
                    "territories": [
                        {"key": key, "name": key.upper()} for key in ("a", "b", "c", "d")
                    ],
                    "stats": {"year_avg": 4 / 3},
                }
                rows = ranking(level, None, include_missing=True)
                self.assertEqual([(row["rank"], row["value"]) for row in rows if not row.get("ref")],
                                 [(1, 2), (1, 2), (3, 0), (None, None)])
                module = {
                    "areas": {}, "area_label": {}, "profile_path": None,
                    "row_id": "p-" if level_key == "provincia" else None,
                    "decimals": 0,
                }
                with app.test_request_context():
                    markup = render_template_string(
                        '{% import "v1/_ui.html" as ui %}{{ ui.rank_body(m, rows) }}',
                        m=module, rows=rows,
                    )
                cells = re.findall(r'<tr data-key="([^"]+)"[^>]*><td class="rank">(.*?)</td>.*?<td class="val">(.*?)</td>', markup, re.S)
                self.assertEqual([key for key, _, _ in cells], ["a", "b", "c", "d"])
                self.assertEqual([html.unescape(re.sub(r"<[^>]+>", "", rank)) for _, rank, _ in cells],
                                 ["1ª", "1ª", "3ª", "n.d."])
                self.assertIn('value="0"', cells[2][2])
                self.assertIn("n.d.", cells[3][2])
                self.assertNotIn('id="p-d"', markup)

    def test_provincial_missing_value_is_explicit_in_table_and_map(self):
        page = app.test_client().get(PROVINCIAL).get_data(as_text=True)
        self.assertRegex(page, r'<tr data-key="pavia"><td class="rank">n\.d\.</td>.*?n\.d\.</span></td></tr>')
        self.assertIn('data-key="pavia" data-name="Pavia" data-value="n.d."', page)

    def test_regional_csv_and_json_keep_missing_distinct_from_zero(self):
        payload = {
            "metadata": {"name": "Prova", "theme": "Prova", "unit": "%",
                         "source_label": "Istat", "source": "Istat", "source_url": "https://www.istat.it/"},
            "series": [
                {"region": "A", "region_key": "a", "year": 2024, "value": None},
                {"region": "B", "region_key": "b", "year": 2024, "value": 0},
            ],
        }
        with patch("app.views.get_atlas_indicator", return_value=payload):
            csv_response = app.test_client().get("/download/indicator/prova.csv")
            json_response = app.test_client().get("/download/indicator/prova.json")
        rows = list(csv.DictReader(io.StringIO(csv_response.get_data(as_text=True))))
        self.assertEqual([row["value"] for row in rows], ["", "0"])
        self.assertEqual([row["value"] for row in json_response.json["series"]], [None, 0])


if __name__ == "__main__":
    unittest.main()
