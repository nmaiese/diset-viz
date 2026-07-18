import re
import unittest
from html import unescape

from app import app
from app import profiles
from app import quiz
from app.bes_data import all_bes_indicators
from app.data import get_catalog
from app.profiles import indicator_path


class IndicatorDescriptionCoverageTest(unittest.TestCase):
    REQUIRED_FIELDS = ("plain", "example", "scope", "reading", "caveat", "direction")

    def _assert_explanation(self, item, family):
        explain = item.get("explain") or {}
        unit = item.get("unit", "")
        for bad_token in (
            "standadizzato",
            "Gwh",
            "Ula",
            "Km/ora",
            "M2",
            "M3",
            "Km2",
            "m2",
            "m3",
            "km2",
        ):
            self.assertNotIn(bad_token, unit, item["id"])
        for field in self.REQUIRED_FIELDS:
            self.assertTrue(explain.get(field), f"{family} {item['id']} senza {field}")
        visible = " ".join(str(explain[field]) for field in self.REQUIRED_FIELDS[:-1])
        self.assertNotRegex(visible, r"[—–;…]", f"{family} {item['id']}")
        self.assertNotRegex(
            visible,
            r"\b(?:tutti i|tra i|per i) (?:regioni|province)\b",
            f"{family} {item['id']} usa un articolo territoriale errato",
        )
        self.assertNotRegex(visible, r"\b(?:de settore|fecondita|standadizzat\w*)\b", f"{family} {item['id']}")
        self.assertNotIn("È un indicatore del dominio BES", visible)
        self.assertNotIn("La fonte esprime il dato in", explain["example"])
        if re.search(r"\b(?:GWh|tonnellate|chilometro) per\b", item.get("unit", ""), re.I):
            self.assertNotIn("casi ogni", explain["example"], item["id"])
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
            levels = set(item["levels"])
            expected_scope = (
                "in tutte le regioni e le province"
                if levels == {"regione", "provincia"}
                else "in tutte le province" if levels == {"provincia"} else "in tutte le regioni"
            )
            self.assertIn(expected_scope, item["explain"]["scope"], item["id"])
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
        self.assertTrue(payload["clue"]["value_explanation"])
        self.assertTrue(payload["clue"]["reading"])

    def test_every_quiz_indicator_explains_both_metric_and_value(self):
        indicators = quiz._quiz_indicators()
        self.assertGreater(len(indicators), 100)
        for item in indicators:
            self.assertTrue(item["description"], item["id"])
            self.assertTrue(item["value_explanation"], item["id"])
            self.assertLessEqual(len(item["description"]), 180, item["id"])
            visible = f"{item['description']} {item['value_explanation']}"
            self.assertNotRegex(visible, r"[—–;…]", item["id"])
            self.assertNotRegex(
                visible,
                r"\b(?:tutti i|tra i|per i) (?:regioni|province)\b",
                item["id"],
            )

    def test_every_possible_region_game_clue_is_clear_and_compact(self):
        candidates = {}
        for region in profiles.REGION_ORDER:
            profile = profiles.region_profile(profiles.region_key_for(region))
            for item in profile["all_indicators"]:
                if item["score"] is not None:
                    candidates[item["id"]] = item
        self.assertGreater(len(candidates), 100)
        for item in candidates.values():
            self.assertTrue(item["description"], item["id"])
            self.assertTrue(item["value_explanation"], item["id"])
            self.assertTrue(item["reading"], item["id"])
            self.assertLessEqual(len(item["description"]), 180, item["id"])


if __name__ == "__main__":
    unittest.main()
