import unittest

from app.data import indicator_trend_stats


def stats_for(name, unit, numbers):
    rows = [{"key": str(i), "name": str(i), "value": value} for i, value in enumerate(numbers)]
    payload = {"metadata": {"name": name, "unit": unit, "year_min": 2024, "year_max": 2024}, "series": {}}
    return indicator_trend_stats(payload, 2024, rows, best=rows[-1], worst=rows[0])


class IndicatorTrendStatsFase1a(unittest.TestCase):
    def test_median_and_quartiles_are_independently_recomputed(self):
        stats = stats_for("Valore", "unità", [0, 1, 2, 3, 100])
        self.assertAlmostEqual(stats["median"], 2)
        self.assertAlmostEqual(stats["q1"], 1)
        self.assertAlmostEqual(stats["q3"], 3)
        self.assertAlmostEqual(stats["gap_abs"], 100)

    def test_duration_detection_uses_words_not_substrings(self):
        for name, unit in (("Partecipazione elettorale", "%"), ("Valore aggiunto", "euro")):
            with self.subTest(name=name):
                self.assertIsNotNone(stats_for(name, unit, [1, 2, 5])["gap_ratio"])
        for name, unit, values in (("Durata media", "anni", [1, 2, 5]),
                                   ("Età media", "anni", [1, 2, 5]),
                                   ("Indicatore", "%", [0, 2, 5]),
                                   ("Indicatore", "%", [-2, 1, 5])):
            with self.subTest(name=name, values=values):
                self.assertIsNone(stats_for(name, unit, values)["gap_ratio"])


if __name__ == "__main__":
    unittest.main()
