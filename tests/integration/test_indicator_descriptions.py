import re
import unittest
from html import unescape

from app import app
from app import indicator_notes
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
        # La spiegazione vive nella sezione "definizione" oppure, con le sezioni
        # variabili, nel blocco "Come leggere il dato": in entrambi i casi deve
        # essere testo visibile, non solo dati strutturati.
        self.assertTrue('id="sezione-definizione"' in html or 'id="come-leggere"' in html)
        self.assertIn(item["explain"]["plain"], html)
        self.assertIn(item["explain"]["example"], html)
        self.assertIn('"@type": "Dataset"', html)
        # The Dataset description has to be something the reader can also see:
        # it is the page lead, not a sentence written only for crawlers.
        lead = re.search(r'<p class="page-lead">(.*?)</p>', html, re.S)
        self.assertIsNotNone(lead)
        description = re.search(r'"description": "(.*?)(?<!\\)"', html, re.S)
        self.assertIsNotNone(description)
        self.assertTrue(description.group(1)[:40] in unescape(re.sub(r"<[^>]+>", "", lead.group(1))))

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


class PercentageUnitsAreNotRates(unittest.TestCase):
    """"per cento" vive dentro "per centomila", e la differenza si vede in pagina.

    Da `is_percentage_unit` esce l'etichetta stampata accanto a ogni cifra e la
    parola usata per ogni variazione. Cercando la sottostringa, "numero per
    centomila abitanti" passava per percentuale e la pagina del tasso di omicidi
    diceva "0,54%" e "0,93 punti percentuali" su un tasso ogni centomila.
    """

    def test_a_rate_per_hundred_thousand_is_not_a_percentage(self):
        self.assertFalse(indicator_notes.is_percentage_unit("numero per centomila abitanti"))
        self.assertEqual(
            indicator_notes.change_unit_label("Tasso di omicidi", "numero per centomila abitanti"),
            "ogni centomila abitanti",
            "e l'etichetta si legge accanto a una cifra, non è la descrizione del CSV",
        )

    def test_a_quantity_per_hundred_people_is_not_a_percentage(self):
        """"tonnellate per cento abitanti" non è una percentuale in nessun senso:
        misura tonnellate, non una quota."""
        for unit in ("tonnellate per cento abitanti", "numero per cento abitanti",
                     "chilometro per cento chilometri quadrati"):
            self.assertFalse(indicator_notes.is_percentage_unit(unit), unit)

    def test_a_rate_reads_as_italian_next_to_a_figure(self):
        """"0,54 numero per centomila abitanti" è corretto e non è italiano."""
        for unit, label in (
            ("numero per centomila abitanti", "ogni centomila abitanti"),
            ("numero per cento abitanti", "ogni cento abitanti"),
            ("tonnellate per cento abitanti", "tonnellate ogni cento abitanti"),
        ):
            self.assertEqual(indicator_notes.value_unit_label("x", unit), label)

    def test_units_that_already_read_well_are_left_alone(self):
        for unit in ("euro per abitante", "punteggio", "centomila abitanti"):
            self.assertEqual(indicator_notes.value_unit_label("x", unit), unit)

    def test_real_percentages_still_are(self):
        for unit in ("%", "% del PIL", "% della popolazione attiva",
                     "percentuale", "Valori percentuali", "per cento"):
            self.assertTrue(indicator_notes.is_percentage_unit(unit), unit)
            self.assertEqual(indicator_notes.change_unit_label("x", unit), "punti percentuali")

    def test_no_catalogue_unit_is_misread(self):
        """La guardia sul catalogo vero: se una fonte introduce un'unità nuova
        che finisce nella trappola, il test lo dice subito."""
        from app.atlas_catalog import get_atlas_catalog

        catalogue = get_atlas_catalog()
        items = catalogue["indicators"] if isinstance(catalogue, dict) and "indicators" in catalogue else catalogue
        wrong = [
            (item["id"], item.get("unit"))
            for item in items
            if indicator_notes.is_percentage_unit(item.get("unit"))
            and "%" not in (item.get("unit") or "")
            and "percentual" not in (item.get("unit") or "").lower()
            and not (item.get("unit") or "").strip().lower().endswith("per cento")
        ]
        self.assertEqual(wrong, [], f"unità scambiate per percentuali: {wrong[:8]}")
