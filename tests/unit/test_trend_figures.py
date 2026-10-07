"""Contratti mirati del generatore standard di figure."""

import unittest

from scripts.trend_articles.figures import _cover_max, _should_label


class TestScatterLabels(unittest.TestCase):
    def test_default_preserves_previous_label_policy(self):
        self.assertTrue(_should_label("Campania", set(), None, True))
        self.assertFalse(_should_label("Campania", set(), None, False))

    def test_subset_includes_highlights_and_requested_extremes(self):
        highlight = {"Lombardia", "Molise", "Sardegna"}
        labels = {"Basilicata", "Calabria", "Valle d'Aosta"}
        self.assertTrue(_should_label("Lombardia", highlight, labels, True))
        self.assertTrue(_should_label("Calabria", highlight, labels, True))
        self.assertFalse(_should_label("Campania", highlight, labels, True))

    def test_scatter_ticks_cover_highest_point(self):
        self.assertEqual(_cover_max([0, 10, 20, 30], 32.6), [0, 10, 20, 30, 40])
        self.assertEqual(_cover_max([0, 10, 20, 30], 29), [0, 10, 20, 30])


if __name__ == "__main__":
    unittest.main()
