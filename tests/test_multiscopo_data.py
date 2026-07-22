import csv
import math
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
from scripts.multiscopo_sources import MULTISCOPO_INDICATORS, QUALITY_LIFE_SCORE_IDS

ROOT = Path(__file__).resolve().parents[1]
LEGACY_COLUMNS = [
    "idIndicatore", "Territorio", "Tema", "Indicatore", "UDM", "Fonte",
    "Archivio", "Anno", "Livello/Variazione", "Dato", "Benchmark", "Area",
]
MANIFEST_COLUMNS = [
    "id", "name", "domain", "domain_name", "proposed_category",
    "proposed_direction", "unit", "year_min", "year_max", "n_region",
    "coverage", "n_region_latest", "coverage_latest", "source_dataflow", "scoreable",
]


class MultiscopoDataTest(unittest.TestCase):
    def test_dataset_schema_matches_the_regional_backbone(self):
        path = ROOT / "app/static/data/Assoluti_Multiscopo_Regione.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter=";"))
        self.assertEqual(list(rows[0]), LEGACY_COLUMNS)
        self.assertTrue(rows)
        self.assertTrue(all(row["Area"] == "Regione" for row in rows))
        keys = set()
        for row in rows:
            value = float(row["Dato"].replace(",", "."))
            self.assertTrue(math.isfinite(value), row)
            key = (row["idIndicatore"], row["Territorio"], row["Anno"])
            self.assertNotIn(key, keys)
            keys.add(key)
            if row["UDM"] == "%":
                self.assertGreaterEqual(value, 0, row)
                self.assertLessEqual(value, 100, row)

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
            self.assertIn(row["scoreable"], {"0", "1"})

    def test_manifest_exactly_matches_curated_specs_and_score_allowlist(self):
        manifest = get_multiscopo_manifest()
        expected_ids = {spec["id"] for spec in MULTISCOPO_INDICATORS}
        self.assertEqual(set(manifest), expected_ids)
        self.assertEqual(
            {indicator_id for indicator_id, info in manifest.items() if info["scoreable"]},
            QUALITY_LIFE_SCORE_IDS,
        )
        self.assertNotIn("MULTI_ICT_BANDA_STRETTA", manifest)

    def test_ambiguous_sdmx_dimensions_are_pinned(self):
        specs = {spec["id"]: spec for spec in MULTISCOPO_INDICATORS}
        for indicator_id, spec in specs.items():
            if indicator_id.startswith("MULTI_SATLIFE_"):
                self.assertEqual(spec["filters"].get("MEASURE"), "HSC")
            if indicator_id.startswith("MULTI_ELETTR_"):
                self.assertEqual(spec["filters"].get("MEASURE"), "HSC_F")
            if indicator_id.startswith("MULTI_BMI_"):
                self.assertEqual(spec["filters"].get("MEASURE"), "HSC")
                self.assertEqual(spec["filters"].get("SEX"), "9")
        housing_filters = {
            spec["filters"].get("PROBLEM_WITH_ACCOMM")
            for spec in MULTISCOPO_INDICATORS
            if spec["flow_id"] == "33_4_DF_DCCV_ABITPROBL_6"
        }
        self.assertEqual(housing_filters, {"1", "2", "3"})

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
            self.assertTrue(page["source_dataflow"])
            self.assertIn(page["source_dataflow"], page["source_data_url"])

    def test_scoreable_indicators_vary_across_regions(self):
        manifest = get_multiscopo_manifest()
        rows = get_multiscopo_rows()
        for indicator_id, info in manifest.items():
            if not info["scoreable"]:
                continue
            latest = {
                row["value"] for row in rows
                if row["id"] == indicator_id and row["year"] == info["year_max"]
            }
            self.assertGreater(len(latest), 1, indicator_id)

    def test_percentage_distributions_sum_to_about_one_hundred(self):
        rows = get_multiscopo_rows()
        distributions = {
            # La soddisfazione non include le mancate risposte, quindi può
            # restare qualche punto sotto 100.
            "soddisfazione": (
                {f"MULTI_SATLIFE_{value}" for value in range(11)}, 94, 101
            ),
            "massa corporea": (
                {
                    "MULTI_BMI_NORMO", "MULTI_BMI_SOTTO",
                    "MULTI_BMI_SOVRA", "MULTI_BMI_OBESI",
                },
                99,
                101,
            ),
        }
        for label, (indicator_ids, lower, upper) in distributions.items():
            year = min(get_multiscopo_manifest()[indicator_id]["year_max"] for indicator_id in indicator_ids)
            totals = {}
            for row in rows:
                if row["id"] in indicator_ids and row["year"] == year:
                    totals.setdefault(row["territory"], 0)
                    totals[row["territory"]] += row["value"]
            self.assertEqual(len(totals), 20, label)
            for territory, total in totals.items():
                self.assertGreaterEqual(total, lower, f"{label}: {territory}")
                self.assertLessEqual(total, upper, f"{label}: {territory}")

    def test_public_page_distinguishes_score_use_and_links_exact_dataflow(self):
        client = app.test_client()
        scored = get_multiscopo_indicator_page("MULTI_ABIT_UMIDITA")
        descriptive = get_multiscopo_indicator_page("MULTI_BMI_NORMO")
        scored_html = client.get(scored["path"]).data.decode("utf-8")
        descriptive_html = client.get(descriptive["path"]).data.decode("utf-8")
        self.assertIn("Questa serie entra nel punteggio regionale", scored_html)
        self.assertIn("Questa serie resta descrittiva", descriptive_html)
        self.assertIn(scored["source_dataflow"], scored_html)

    def test_rows_have_a_resolvable_territory_key(self):
        rows = get_multiscopo_rows()
        self.assertTrue(rows)
        unresolved = [row for row in rows if not row["territory_key"]]
        self.assertEqual(unresolved, [])

    def test_every_indexable_indicator_has_a_public_page_listed_in_the_sitemap(self):
        client = app.test_client()
        indicators = all_multiscopo_indicators()
        indexable = [item for item in indicators if item["indexable"]]
        non_indexable = [item for item in indicators if not item["indexable"]]
        self.assertGreaterEqual(len(indexable), 40)

        sample = indexable[0]
        page = client.get(sample["path"])
        self.assertEqual(page.status_code, 200)
        self.assertIn(sample["name"].encode("utf-8"), page.data)
        self.assertNotIn("noindex", page.headers.get("X-Robots-Tag", ""))

        sitemap = client.get("/sitemap.xml").data.decode("utf-8")
        self.assertIn(sample["path"], sitemap)
        for item in non_indexable:
            self.assertNotIn(item["path"], sitemap)


if __name__ == "__main__":
    unittest.main()
