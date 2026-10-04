import csv
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

from app import seo_policy


class IndicatorContentPolicyTest(unittest.TestCase):
    def test_fotografia_gsc_ha_i_conteggi_misurati(self):
        metrics = seo_policy.indicator_search_metrics()
        classes = Counter(
            label
            for row in metrics.values()
            for label in row["class"].split(",")
            if label != "-"
        )
        self.assertEqual(len(metrics), 411)
        self.assertEqual(classes, Counter({"a": 229, "b": 57, "c": 30}))

    def test_senza_impressioni_esce_solo_finche_non_arriva_la_prosa(self):
        item = {
            "id": "06POL012P",
            "region_count": 20,
            "completeness": 1.0,
            "year_max": 2025,
        }
        baseline = lambda _item: True

        with mock.patch("app.indicator_texts.get_text", return_value=None):
            self.assertFalse(seo_policy.is_search_indexable_indicator(baseline, item))

        authored = {"lead": "Un commento scritto.", "sections": []}
        with mock.patch("app.indicator_texts.get_text", return_value=authored):
            self.assertTrue(seo_policy.is_search_indexable_indicator(baseline, item))

    def test_impressioni_positive_tengono_la_scheda_senza_prosa(self):
        item = {
            "id": "07SIC007P",
            "region_count": 20,
            "completeness": 1.0,
            "year_max": 2025,
        }
        with mock.patch("app.indicator_texts.get_text", return_value=None):
            self.assertTrue(seo_policy.is_search_indexable_indicator(lambda _item: True, item))

    def test_file_di_config_esiste_con_forma_e_conteggi(self):
        path = seo_policy.INDICATOR_CLASSIFICATION
        self.assertTrue(path.exists(), f"{path} manca: la regola fallirebbe aperta")
        with path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertGreaterEqual(len(rows), 400)
        for row in rows:
            int(row["impressioni"])
            int(row["clic"])
            self.assertLessEqual(
                set(row["classe"].split(",")), {"a", "b", "c", "-"},
            )

    def test_file_mancante_falla_aperta_con_warning_una_sola_volta(self):
        item = {
            "id": "06POL012P",
            "region_count": 20,
            "completeness": 1.0,
            "year_max": 2025,
        }
        missing = Path(__file__).resolve().parents[2] / "config" / "inesistente.csv"
        seo_policy.indicator_search_metrics.cache_clear()
        seo_policy._warned_missing_classification = False
        with mock.patch.object(seo_policy, "INDICATOR_CLASSIFICATION", missing):
            with self.assertLogs("app.seo_policy", level="WARNING") as captured:
                self.assertTrue(seo_policy.indicator_passes_content_rule(item))
        self.assertTrue(any("metriche GSC" in message for message in captured.output))
        seo_policy.indicator_search_metrics.cache_clear()


if __name__ == "__main__":
    unittest.main()
