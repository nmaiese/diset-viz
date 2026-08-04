import csv
import unittest
from pathlib import Path

from app import app
from app.external_data import EXTERNAL_COLUMNS, MANIFEST_COLUMNS, freshness_status


ROOT = Path(__file__).resolve().parents[2]
LEGACY_COLUMNS = [
    "idIndicatore",
    "Territorio",
    "Tema",
    "Indicatore",
    "UDM",
    "Fonte",
    "Archivio",
    "Anno",
    "Livello/Variazione",
    "Dato",
    "Benchmark",
    "Area",
]


class ExternalDataTest(unittest.TestCase):
    def _header(self, path):
        with (ROOT / path).open(encoding="utf-8", newline="") as handle:
            return next(csv.reader(handle, delimiter=";"))

    def test_legacy_csv_schema_is_unchanged(self):
        for path in (
            "app/static/data/Assoluti_Regione.csv",
            "app/static/data/Assoluti_Provincia.csv",
        ):
            self.assertEqual(self._header(path), LEGACY_COLUMNS, path)

    def test_external_dataset_schema_and_demography_coverage(self):
        path = ROOT / "app/static/data/external/normalized_external_indicators.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter=";"))
        self.assertEqual(list(rows[0]), EXTERNAL_COLUMNS)
        self.assertTrue(rows)
        sources = {row["source"] for row in rows}
        self.assertIn("istat_demografia", sources)
        self.assertIn("istat_lavoro", sources)
        by_indicator = {}
        for row in rows:
            by_indicator.setdefault(row["target_indicator_id"], set()).add(row["territory_code"])
            self.assertIn(row["definition_match"], {"exact", "compatible", "proxy", "different", "new"})
            self.assertIn(row["score_eligible"], {"true", "false"})
        self.assertEqual(len(by_indicator["910"]), 20)
        self.assertEqual(len(by_indicator["922"]), 20)
        self.assertEqual(len(by_indicator["345"]), 20)

    def test_manifest_vocabulary_and_conservative_scoring(self):
        path = ROOT / "app/static/data/external_indicator_manifest.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter=";"))
        self.assertEqual(list(rows[0]), MANIFEST_COLUMNS)
        statuses = {row["status"] for row in rows}
        self.assertIn("integrated", statuses)
        self.assertIn("needs_review", statuses)
        for row in rows:
            # "new" = a discovered indicator with no Istat counterpart (Eurostat
            # standalone); "proposed" = staged by the discovery integrator, live
            # only once the PR merges.
            self.assertIn(row["definition_match"], {"exact", "compatible", "proxy", "different", "new"})
            self.assertIn(row["status"], {"integrated", "candidate", "rejected", "needs_review", "unavailable", "proposed"})
        candidates = [
            row for row in rows
            if row["score_eligible"] == "true"
            and row["status"] in {"candidate", "needs_review"}
        ]
        replacements = [
            row for row in rows
            if row["score_eligible"] == "true"
            and row["status"] == "integrated"
            and ":" not in row["target_indicator_id"]
        ]
        self.assertFalse(candidates)
        self.assertTrue(all(row["definition_match"] == "exact" for row in replacements))

    def test_freshness_status(self):
        self.assertEqual(freshness_status(2025), "current")
        self.assertEqual(freshness_status(2023), "recent")
        self.assertEqual(freshness_status(2020), "dated")
        self.assertEqual(freshness_status(2019), "stale")

    def test_freshness_api_payloads(self):
        client = app.test_client()
        catalog = client.get("/api/catalog").get_json()
        sample = next(item for item in catalog["indicators"] if item["id"] == "910")
        self.assertEqual(sample["freshness_status"], "current")
        self.assertIn("istat_demografia", sample["external_sources"])

        indicator = client.get("/api/indicator/910").get_json()
        self.assertEqual(indicator["metadata"]["freshness_status"], "current")

        region = client.get("/api/region/lombardia").get_json()
        self.assertIn("data_freshness", region)
        self.assertGreater(region["data_freshness"]["current"], 0)

        ranking = client.get("/api/quality-life/regioni/rankings").get_json()
        self.assertIn("data_freshness", ranking)

        manifest = client.get("/api/external-indicators/manifest")
        self.assertEqual(manifest.status_code, 200)
        self.assertGreater(len(manifest.get_json()["manifest"]), 0)


if __name__ == "__main__":
    unittest.main()
