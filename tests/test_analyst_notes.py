"""Analyst notes: structure, editorial style, vintage and drift guard.

The notes carry hand-written figures, so the risk is drift: the atlas is
data-derived and updates with Istat/Eurostat, while a note is static. Each note
records the data `vintage` it was written against; this test fails when the
indicator's current year has moved past that vintage, forcing a review before
the page shows a note that contradicts the numbers beside it.
"""

import json
import re
import unittest
from pathlib import Path

from app import analyst_notes, indicator_notes
from app.atlas_catalog import get_atlas_indicator

NOTES_PATH = Path(analyst_notes.__file__).resolve().parent / "static" / "data" / "analyst_notes.json"
PROSE_FIELDS = ("attacco", "spunto", "limite")
# STYLE.md bans these in prose: em-dash, en-dash, semicolon, ellipsis char.
BANNED = ("—", "–", ";", "…")


class AnalystNotesStructure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notes = json.loads(NOTES_PATH.read_text(encoding="utf-8"))

    def test_every_note_has_prose_and_sources_shape(self):
        for key, note in self.notes.items():
            for field in PROSE_FIELDS:
                self.assertIsInstance(note.get(field), str, f"{key}:{field}")
                self.assertTrue(note[field].strip(), f"{key}:{field} empty")
            self.assertIsInstance(note.get("fonti", []), list, key)
            for source in note.get("fonti", []):
                self.assertIn("testo", source, key)
                self.assertIn("url", source, key)

    def test_prose_respects_editorial_style(self):
        offenders = [
            (key, field, ch)
            for key, note in self.notes.items()
            for field in PROSE_FIELDS
            for ch in BANNED
            if ch in note.get(field, "")
        ]
        self.assertEqual(offenders, [], f"style violations: {offenders[:10]}")


class AnalystNotesVintageDrift(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notes = json.loads(NOTES_PATH.read_text(encoding="utf-8"))

    def test_every_note_declares_an_integer_vintage(self):
        missing = [k for k, n in self.notes.items() if not isinstance(n.get("vintage"), int)]
        self.assertEqual(missing, [], f"notes without an integer vintage: {missing[:10]}")

    def test_notes_are_not_stale_against_current_data(self):
        """A note's vintage must be >= the indicator's current latest year. When
        the data moves forward this fails, flagging the note (and its hand-written
        figures) for review."""
        stale = []
        for key, note in self.notes.items():
            payload = get_atlas_indicator(key)
            if payload is None:
                continue  # orphaned key: separate cleanup, not a drift signal
            year_max = payload["metadata"].get("year_max")
            vintage = note.get("vintage")
            if isinstance(year_max, int) and isinstance(vintage, int) and year_max > vintage:
                stale.append((key, vintage, year_max))
        self.assertEqual(
            stale, [],
            "analyst notes older than the data they describe "
            f"(id, note vintage, data year): {stale[:10]}",
        )

    def test_every_note_key_resolves_to_an_indicator(self):
        orphans = [k for k in self.notes if get_atlas_indicator(k) is None]
        self.assertEqual(orphans, [], f"notes for missing indicators: {orphans[:10]}")


class AnalystNotesAgainstTheData(unittest.TestCase):
    """The figures and the claims in a note, checked against the series it
    describes.

    The vintage guard above catches a note that has fallen *behind* the data. It
    says nothing about a note that was wrong when written, which is how a claim
    like "supera il 78% in Emilia-Romagna, Veneto e Sardegna" survived with
    Sardegna at 76,6%. These two checks cover the mechanical part of that: a
    figure attributed to a named region, and a threshold asserted over a list of
    regions. The interpretive part of a note still needs a human.
    """

    REGIONS = (
        "Trentino Alto Adige|Friuli-Venezia Giulia|Emilia-Romagna|Valle d'Aosta|Lombardia|"
        "Piemonte|Liguria|Veneto|Toscana|Umbria|Marche|Lazio|Abruzzo|Molise|Campania|Puglia|"
        "Basilicata|Calabria|Sicilia|Sardegna"
    )
    NUMBER = r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?)"
    # "il 24,3% del Molise": the number is bound to the region that follows it.
    # Only figures carrying a decimal are checked, because a bare integer is
    # normally an approximation in this prose ("circa 27%", "quasi 78%").
    VALUE_OF_REGION = re.compile(
        NUMBER + r"\s*(?:%|per cento|punti|anni|euro)?\s+"
        r"(?:di|del|della|dell'|degli|delle|in|a|ad|nel|nella)\s+(" + REGIONS + r")"
    )
    ABOVE = r"(?:supera(?:no)?|sopra|oltre|più di|almeno|maggiore di)"
    BELOW = r"(?:scende|scendono|sotto|meno di|inferiore a|non arriva)"
    THRESHOLD_OVER_REGIONS = re.compile(
        rf"\b({ABOVE}|{BELOW})\s+(?:il|lo|la|i|gli|le|a|ai|al)?\s*{NUMBER}\s*(?:%|per cento)?\s*"
        rf"(?:in|a|nel|nella|per)\s+((?:{REGIONS})(?:\s*(?:,|e)\s*(?:{REGIONS}))*)",
        re.I,
    )

    @classmethod
    def setUpClass(cls):
        cls.notes = json.loads(NOTES_PATH.read_text(encoding="utf-8"))

    @staticmethod
    def _number(raw):
        return float(raw.replace(".", "").replace(",", "."))

    def _values(self, key, note):
        """{region: value} for the year the note was written against."""
        payload = get_atlas_indicator(key)
        if payload is None:
            return {}
        year = note.get("vintage") or payload["metadata"]["year_max"]
        return {
            row.get("region") or row.get("territory"): row["value"]
            for row in payload["series"]
            if row["year"] == year and row["value"] is not None
        }

    def test_figures_attributed_to_a_region_match_that_region(self):
        wrong = []
        for key, note in self.notes.items():
            values = self._values(key, note)
            if not values:
                continue
            for field in PROSE_FIELDS:
                for match in self.VALUE_OF_REGION.finditer(note.get(field) or ""):
                    raw, region = match.group(1), match.group(2)
                    if "," not in raw or region not in values:
                        continue
                    actual = values[region]
                    if abs(self._number(raw) - actual) > max(0.06, abs(actual) * 0.011):
                        wrong.append((key, field, region, raw, round(actual, 2)))
        self.assertEqual(wrong, [], f"figures that contradict the data: {wrong[:10]}")

    def test_thresholds_hold_for_every_region_they_name(self):
        wrong = []
        for key, note in self.notes.items():
            values = self._values(key, note)
            if not values:
                continue
            for field in PROSE_FIELDS:
                for match in self.THRESHOLD_OVER_REGIONS.finditer(note.get(field) or ""):
                    verb, raw, listed = match.group(1), match.group(2), match.group(3)
                    threshold = self._number(raw)
                    above = bool(re.match(self.ABOVE, verb, re.I))
                    for region in re.findall(self.REGIONS, listed):
                        if region not in values:
                            continue
                        actual = values[region]
                        ok = (actual >= threshold - 0.06) if above else (actual <= threshold + 0.06)
                        if not ok:
                            wrong.append((key, field, region, verb, raw, round(actual, 2)))
        self.assertEqual(wrong, [], f"claims the data contradicts: {wrong[:10]}")


class MetaDescriptionFromAttacco(unittest.TestCase):
    def test_truncates_to_budget_and_strips_markdown_links(self):
        attacco = (
            "In [Valle d'Aosta](https://x) lavora quasi il 69% delle donne, "
            "in Campania poco meno del 34%. " + "coda " * 60
        )
        out = indicator_notes.meta_description_from_attacco(attacco)
        self.assertLessEqual(len(out), 155)
        self.assertNotIn("](", out)
        self.assertNotIn("http", out)
        self.assertIn("Valle d'Aosta", out)

    def test_indicator_page_uses_the_attacco_as_meta_description(self):
        from app import app

        notes = json.loads(NOTES_PATH.read_text(encoding="utf-8"))
        # A note whose indicator has a canonical, indexable page.
        for key, note in notes.items():
            payload = get_atlas_indicator(key)
            if payload is None or ":" in key:
                continue
            meta = payload["metadata"]
            expected = indicator_notes.meta_description_from_attacco(note["attacco"])
            html = app.test_client().get(meta["path"]).data.decode("utf-8")
            match = re.search(r'<meta name="description" content="([^"]*)"', html)
            self.assertIsNotNone(match, key)
            # The rendered description is the attacco-derived text (HTML-escaped).
            self.assertEqual(match.group(1), expected.replace("'", "&#39;"))
            return
        self.skipTest("no eligible note-backed indicator found")


if __name__ == "__main__":
    unittest.main()
