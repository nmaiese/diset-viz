"""G9: un indice, pari merito e dato assente nelle schede dei due livelli."""

import csv
import html
import io
import re
import unittest
from unittest.mock import patch

from flask import render_template_string

from app import app
from app.design.common import ranking


REGIONAL = "/indicatore/eta-media-della-popolazione/ter-920"
PROVINCIAL = "/indicatore/partecipazione-elettorale-elezioni-regionali/bes-06POL001P"


class IndicatorTemplateG9(unittest.TestCase):
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
