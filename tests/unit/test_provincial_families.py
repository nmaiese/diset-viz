import unittest
from unittest.mock import patch

from app import provincial_families
from tests.fixtures import external_mef


class ProvincialFamilies(unittest.TestCase):
    def setUp(self):
        provincial_families.cache_clear()

    def tearDown(self):
        provincial_families.cache_clear()

    def test_builds_one_cross_family_indicator_and_keeps_score_gate_closed(self):
        with patch("app.external_data.get_external_rows", return_value=external_mef.rows()), \
                patch("app.external_data.get_external_levels", return_value=external_mef.levels()):
            entries = provincial_families.all_indicators()
            self.assertEqual(len(entries), 1)
            entry = entries[0]
            self.assertEqual(entry["metadata"]["id"], external_mef.TARGET)
            self.assertEqual(entry["metadata"]["family"], "mef")
            self.assertEqual(entry["levels"]["provincia"]["count_latest"], 107)
            self.assertEqual(len(provincial_families.series("mef", "reddito-irpef-medio")), 214)
            self.assertEqual(provincial_families.scoreables(), [])

    def test_province_projection_has_value_rank_and_source(self):
        with patch("app.external_data.get_external_rows", return_value=external_mef.rows()), \
                patch("app.external_data.get_external_levels", return_value=external_mef.levels()):
            province_key = next(
                row["territory_code"] for row in external_mef.rows()
                if row["territory_level"] == "provincia"
            )
            rows = provincial_families.indicators_for_province(province_key)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], external_mef.TARGET)
            self.assertGreaterEqual(rows[0]["rank"], 1)
            self.assertLessEqual(rows[0]["rank"], 107)
            self.assertEqual(rows[0]["source"], "Ministero dell'Economia e delle Finanze, dichiarazioni fiscali")

    def test_unknown_province_fails_with_context(self):
        broken = external_mef.rows()
        index = next(index for index, row in enumerate(broken) if row["territory_level"] == "provincia")
        broken[index] = {**broken[index], "territory_code": "mai-esistita"}
        with patch("app.external_data.get_external_rows", return_value=broken), \
                patch("app.external_data.get_external_levels", return_value=external_mef.levels()), \
                self.assertRaisesRegex(ValueError, "provincia sconosciuta"):
            provincial_families.all_indicators()


if __name__ == "__main__":
    unittest.main()
