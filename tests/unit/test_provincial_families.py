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
            self.assertTrue(rows[0]["path"].endswith("/mef-reddito-irpef-medio/province"))

    def test_base_level_is_regional_and_its_rule_is_its_own(self):
        with patch("app.external_data.get_external_rows", return_value=external_mef.rows()), \
                patch("app.external_data.get_external_levels", return_value=external_mef.levels()):
            meta = provincial_families.all_indicators()[0]["metadata"]
            levels = provincial_families.all_indicators()[0]["levels"]
            self.assertEqual(meta["base_level"], "regione")
            self.assertEqual(levels["regione"]["count_latest"], 20)
            self.assertTrue(levels["regione"]["indexable"])
            self.assertTrue(meta["indexable"])

    def test_province_only_series_has_province_base(self):
        rows = [row for row in external_mef.rows() if row["territory_level"] == "provincia"]
        levels = [level for level in external_mef.levels() if level["territory_level"] == "provincia"]
        with patch("app.external_data.get_external_rows", return_value=rows), \
                patch("app.external_data.get_external_levels", return_value=levels):
            meta = provincial_families.all_indicators()[0]["metadata"]
            self.assertEqual(meta["base_level"], "provincia")
            self.assertTrue(meta["indexable"])

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
