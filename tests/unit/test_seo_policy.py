import unittest
from collections import Counter
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


if __name__ == "__main__":
    unittest.main()
