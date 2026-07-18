import unittest
from html import unescape

from app import app
from app.bes_data import all_bes_indicators
from app.data import get_catalog
from app.profiles import indicator_path


class IndicatorDescriptionCoverageTest(unittest.TestCase):
    REQUIRED_FIELDS = ("plain", "example", "scope", "reading", "caveat", "direction")

    def _assert_explanation(self, item, family):
        explain = item.get("explain") or {}
        for field in self.REQUIRED_FIELDS:
            self.assertTrue(explain.get(field), f"{family} {item['id']} senza {field}")
        visible = " ".join(str(explain[field]) for field in self.REQUIRED_FIELDS[:-1])
        self.assertNotRegex(visible, r"[—–;…]", f"{family} {item['id']}")
        self.assertNotIn("È un indicatore del dominio BES", visible)
        self.assertGreaterEqual(len(explain["plain"]), 18, f"{family} {item['id']}")
        self.assertTrue(explain["plain"].endswith("."), f"{family} {item['id']}")

    def test_every_territorial_indicator_has_a_complete_explanation(self):
        indicators = get_catalog()["indicators"]
        self.assertEqual(len(indicators), 393)
        for item in indicators:
            self._assert_explanation(item, "territoriale")

    def test_every_public_bes_indicator_has_a_complete_explanation(self):
        indicators = all_bes_indicators()
        self.assertEqual(len(indicators), 178)
        for item in indicators:
            self._assert_explanation(item, "BES")
            plain = item["explain"]["plain"].lower()
            name = item["name"].lower()
            self.assertNotIn(
                plain,
                {f"misura la {name}.", f"misura il {name}.", f"misura l'{name}."},
                f"BES {item['id']} ripete soltanto il nome",
            )

    def test_indicator_page_exposes_the_explanation_in_visible_html_and_schema(self):
        item = get_catalog()["indicators"][0]
        response = app.test_client().get(indicator_path(item["id"], item["name"]))
        html = unescape(response.data.decode("utf-8"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Che cosa misura questo indicatore", html)
        self.assertIn(item["explain"]["plain"], html)
        self.assertIn(item["explain"]["example"], html)
        self.assertIn('"@type": "Dataset"', html)

    def test_blog_posts_with_an_indicator_show_the_same_explanation(self):
        response = app.test_client().get("/blog/divario-turistico-nord-sud-2024")
        html = response.data.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.assertIn("L'indicatore in parole semplici", html)
        self.assertIn('"about": {', html)

    def test_daily_game_clues_include_plain_language_descriptions(self):
        payload = app.test_client().get("/api/game/daily").get_json()
        self.assertTrue(payload["clue"]["description"])


if __name__ == "__main__":
    unittest.main()
