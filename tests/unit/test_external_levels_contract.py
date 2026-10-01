import csv
import unittest
from pathlib import Path

from app.external_data import EXTERNAL_COLUMNS, LEVEL_COLUMNS
from tests.fixtures import external_mef


ROOT = Path(__file__).resolve().parents[2]


class ExternalLevelsContract(unittest.TestCase):
    def test_production_manifest_has_only_declared_header(self):
        path = ROOT / "app/static/data/external/external_indicator_levels.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle, delimiter=";")
            self.assertEqual(next(reader), LEVEL_COLUMNS)
            self.assertEqual(list(reader), [])

    def test_fixture_exercises_both_levels_without_production_rows(self):
        self.assertEqual(len(external_mef.levels()), 2)
        self.assertEqual({row["territory_level"] for row in external_mef.levels()}, {"regione", "provincia"})
        rows = external_mef.rows()
        self.assertEqual({row["territory_level"] for row in rows}, {"regione", "provincia"})
        self.assertEqual(
            len({row["territory_code"] for row in rows if row["territory_level"] == "regione"}),
            20,
        )
        self.assertEqual(
            len({row["territory_code"] for row in rows if row["territory_level"] == "provincia"}),
            107,
        )

    def test_external_observation_contract_header_stays_unchanged(self):
        self.assertEqual(EXTERNAL_COLUMNS, [
            "source", "source_dataset", "source_indicator_id", "target_indicator_id",
            "name", "territory_level", "territory_code", "territory_name", "year",
            "value", "unit", "theme", "quality_life_category", "direction",
            "definition_match", "atlas_eligible", "profile_eligible", "score_eligible",
            "coverage", "retrieved_at", "source_url", "license", "notes",
        ])


if __name__ == "__main__":
    unittest.main()
