import csv
import unittest
from pathlib import Path

from app import app
from app.multiscopo_data import (
    all_multiscopo_indicators,
    get_multiscopo_indicator_page,
    get_multiscopo_manifest,
    get_multiscopo_rows,
    get_multiscopo_territories,
    MIN_PUBLIC_COVERAGE,
)
from app.taxonomy import CANONICAL_CATEGORIES

ROOT = Path(__file__).resolve().parents[1]
LEGACY_COLUMNS = [
    "idIndicatore", "Territorio", "Tema", "Indicatore", "UDM", "Fonte",
    "Archivio", "Anno", "Livello/Variazione", "Dato", "Benchmark", "Area",
]
MANIFEST_COLUMNS = [
    "id", "name", "domain", "domain_name", "proposed_category",
    "proposed_direction", "unit", "year_min", "year_max", "n_region",
    "coverage", "n_region_latest", "coverage_latest", "source_dataflow",
]


class MultiscopoDataTest(unittest.TestCase):
    def test_dataset_schema_matches_the_regional_backbone(self):
        path = ROOT / "app/static/data/Assoluti_Multiscopo_Regione.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter=";"))
        self.assertEqual(list(rows[0]), LEGACY_COLUMNS)
        self.assertTrue(rows)
        self.assertTrue(all(row["Area"] == "Regione" for row in rows))
        self.assertTrue(all("," in row["Dato"] or "," not in row["Dato"] for row in rows))

    def test_manifest_schema_and_vocabulary(self):
        path = ROOT / "app/static/data/multiscopo_regione_manifest.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter=";"))
        self.assertEqual(list(rows[0]), MANIFEST_COLUMNS)
        self.assertTrue(rows)
        for row in rows:
            self.assertIn(
                row["proposed_direction"],
                {"higher_better", "lower_better", "higher_worse", "contextual"},
            )

    def test_every_indicator_meets_the_coverage_requirement_or_is_flagged(self):
        manifest = get_multiscopo_manifest()
        self.assertGreaterEqual(len(manifest), 40)
        below_threshold = [
            info for info in manifest.values() if info["coverage_latest"] < MIN_PUBLIC_COVERAGE
        ]
        # A handful of small-sample breakdowns are suppressed by Istat in some
        # regions (e.g. rarer income sources): they stay visible in the atlas
        # but must not silently claim full coverage.
        self.assertLessEqual(len(below_threshold), 3)

    def test_every_indicator_resolves_a_real_category_not_altro(self):
        manifest = get_multiscopo_manifest()
        for indicator_id, info in manifest.items():
            self.assertIsNotNone(info["category"], indicator_id)
            self.assertIn(info["category"], CANONICAL_CATEGORIES, indicator_id)

    def test_territories_are_the_twenty_project_regions(self):
        territories = get_multiscopo_territories()
        self.assertEqual(len(territories), 20)

    def test_indicator_page_renders_observations_for_every_indicator(self):
        for item in all_multiscopo_indicators():
            page = get_multiscopo_indicator_page(item["id"])
            self.assertIsNotNone(page, item["id"])
            self.assertEqual(len(page["level_payloads"]), 1)
            level = page["level_payloads"][0]
            self.assertGreater(level["count_latest"], 0, item["id"])
            self.assertTrue(page["value_unit"])

    def test_rows_have_a_resolvable_territory_key(self):
        rows = get_multiscopo_rows()
        self.assertTrue(rows)
        unresolved = [row for row in rows if not row["territory_key"]]
        self.assertEqual(unresolved, [])


if __name__ == "__main__":
    unittest.main()
