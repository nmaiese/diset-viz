"""Indicator articles: structure, editorial style, vintage drift, and figures.

The article replaced the three loose analyst-note fields, so these guards are the
old ones re-aimed at the new schema, plus what the schema itself now needs
(known roles, no duplicate headings, a lead that can stand alone as a SERP
description).

The two numeric checks are the valuable ones and they exist because of real
mistakes that shipped: a claim that prison overcrowding exceeded capacity
"everywhere" while three regions were under it, and a note putting Sardegna above
78% of separate waste collection when it was at 76,6%. They are mechanical by
design. The interpretive half of an article still needs a human, and
docs/INDICATOR_PAGES.md lists what stays uncovered.
"""

import json
import re
import unittest
from pathlib import Path

from app import indicator_texts
from app.atlas_catalog import get_atlas_indicator

TEXTS_PATH = Path(indicator_texts.__file__).resolve().parent / "static" / "data" / "indicator_texts.json"
# STYLE.md bans these in prose: em-dash, en-dash, semicolon, ellipsis char.
BANNED = ("—", "–", ";", "…")
# The lead is also the meta description. Google truncates well before this, and a
# first sentence longer than this cannot work as one.
LEAD_FIRST_SENTENCE_MAX = 200


def _load():
    return json.loads(TEXTS_PATH.read_text(encoding="utf-8"))


def _prose(entry):
    """Every piece of hand-written prose in an entry, as (field, text)."""
    fields = []
    if entry.get("lead"):
        fields.append(("lead", entry["lead"]))
    for section in entry.get("sections") or []:
        if section.get("body"):
            fields.append((f"sections.{section.get('role')}", section["body"]))
    return fields


class ArticleStructure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts = _load()

    def test_entries_have_the_expected_shape(self):
        for key, entry in self.texts.items():
            with self.subTest(indicator=key):
                self.assertIsInstance(entry.get("sections", []), list)
                self.assertIsInstance(entry.get("fonti", []), list)
                for source in entry.get("fonti") or []:
                    self.assertIn("testo", source)
                    self.assertIn("url", source)

    def test_sections_use_known_roles_once_each(self):
        offenders = []
        for key, entry in self.texts.items():
            roles = [section.get("role") for section in entry.get("sections") or []]
            for role in roles:
                if role not in indicator_texts.DEFAULT_HEADINGS:
                    offenders.append((key, role, "unknown role"))
            duplicates = {role for role in roles if roles.count(role) > 1}
            for role in duplicates:
                offenders.append((key, role, "duplicated"))
        self.assertEqual(offenders, [], f"bad section roles: {offenders[:10]}")

    def test_sections_have_a_non_empty_body(self):
        """A role present with an empty body would render as a bare heading.

        Omitting the role is the supported way to say "not written yet": the page
        then composes that section from the data.
        """
        empty = [
            (key, section.get("role"))
            for key, entry in self.texts.items()
            for section in entry.get("sections") or []
            if not (section.get("body") or "").strip()
        ]
        self.assertEqual(empty, [], f"sections present but empty: {empty[:10]}")

    def test_authored_headings_are_not_reused_across_indicators(self):
        """Identical H2s across the catalogue read as a stamp (content/STYLE.md).

        The role defaults are shared on purpose and excluded; this only catches an
        author copying the same custom heading onto several indicators.
        """
        seen = {}
        clashes = []
        defaults = set(indicator_texts.DEFAULT_HEADINGS.values())
        for key, entry in self.texts.items():
            for section in entry.get("sections") or []:
                heading = (section.get("h") or "").strip()
                if not heading or heading in defaults:
                    continue
                if heading in seen:
                    clashes.append((heading, seen[heading], key))
                seen[heading] = key
        self.assertEqual(clashes, [], f"headings reused across indicators: {clashes[:10]}")

    def test_lead_opens_with_a_sentence_that_can_stand_alone(self):
        too_long = []
        for key, entry in self.texts.items():
            lead = (entry.get("lead") or "").strip()
            if not lead:
                continue
            first = re.split(r"(?<=[.!?])\s", lead)[0]
            if len(first) > LEAD_FIRST_SENTENCE_MAX:
                too_long.append((key, len(first)))
        self.assertEqual(too_long, [], f"lead first sentences too long for a SERP description: {too_long[:10]}")

    def test_prose_respects_editorial_style(self):
        offenders = [
            (key, field, char)
            for key, entry in self.texts.items()
            for field, text in _prose(entry)
            for char in BANNED
            if char in text
        ]
        self.assertEqual(offenders, [], f"style violations: {offenders[:10]}")


class ArticleVintageDrift(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts = _load()

    def test_every_entry_declares_an_integer_vintage(self):
        missing = [key for key, entry in self.texts.items() if not isinstance(entry.get("vintage"), int)]
        self.assertEqual(missing, [], f"entries without an integer vintage: {missing[:10]}")

    def test_articles_are_not_stale_against_current_data(self):
        """The vintage must be >= the indicator's latest year.

        When the data moves forward this fails, flagging the hand-written figures
        for review before the page shows prose that contradicts the cockpit
        directly above it.
        """
        stale = []
        for key, entry in self.texts.items():
            payload = get_atlas_indicator(key)
            if payload is None:
                continue  # orphaned key: separate cleanup, not a drift signal
            year_max = payload["metadata"].get("year_max")
            vintage = entry.get("vintage")
            if isinstance(year_max, int) and isinstance(vintage, int) and year_max > vintage:
                stale.append((key, vintage, year_max))
        self.assertEqual(
            stale, [],
            f"articles older than the data they describe (id, vintage, data year): {stale[:10]}",
        )

    def test_every_key_resolves_to_an_indicator(self):
        orphans = [key for key in self.texts if get_atlas_indicator(key) is None]
        self.assertEqual(orphans, [], f"articles for missing indicators: {orphans[:10]}")


class ArticleAgainstTheData(unittest.TestCase):
    """Figures and threshold claims, checked against the series they describe.

    The vintage guard catches an article that fell behind the data. It says
    nothing about one that was wrong when written, which is what these two cover.
    Only figures carrying a decimal are checked: a bare integer in this prose is
    almost always an approximation ("circa 27%", "quasi 78%").

    Known gap, unchanged from the previous guard and worth stating: REGIONS knows
    only the twenty regions, so a figure attributed to a *province* in a BES
    article is verified by nothing here.
    """

    REGIONS = (
        "Trentino Alto Adige|Friuli-Venezia Giulia|Emilia-Romagna|Valle d'Aosta|Lombardia|"
        "Piemonte|Liguria|Veneto|Toscana|Umbria|Marche|Lazio|Abruzzo|Molise|Campania|Puglia|"
        "Basilicata|Calabria|Sicilia|Sardegna"
    )
    NUMBER = r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?)"
    # "il 24,3% del Molise": the number is bound to the region that follows it.
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
        cls.texts = _load()

    @staticmethod
    def _number(raw):
        return float(raw.replace(".", "").replace(",", "."))

    def _values(self, key, entry):
        """{region: value} for the year the article was written against."""
        payload = get_atlas_indicator(key)
        if payload is None:
            return {}
        year = entry.get("vintage") or payload["metadata"]["year_max"]
        return {
            row.get("region") or row.get("territory"): row["value"]
            for row in payload["series"]
            if row["year"] == year and row["value"] is not None
        }

    def test_figures_attributed_to_a_region_match_that_region(self):
        wrong = []
        for key, entry in self.texts.items():
            values = self._values(key, entry)
            if not values:
                continue
            for field, text in _prose(entry):
                for match in self.VALUE_OF_REGION.finditer(text):
                    raw, region = match.group(1), match.group(2)
                    if "," not in raw or region not in values:
                        continue
                    actual = values[region]
                    if abs(self._number(raw) - actual) > max(0.06, abs(actual) * 0.011):
                        wrong.append((key, field, region, raw, round(actual, 2)))
        self.assertEqual(wrong, [], f"figures that contradict the data: {wrong[:10]}")

    def test_thresholds_hold_for_every_region_they_name(self):
        wrong = []
        for key, entry in self.texts.items():
            values = self._values(key, entry)
            if not values:
                continue
            for field, text in _prose(entry):
                for match in self.THRESHOLD_OVER_REGIONS.finditer(text):
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


class ArticleRendering(unittest.TestCase):
    def test_a_missing_role_is_composed_not_blank(self):
        """The fallback contract: an unwritten role still produces a section.

        This is what keeps 621 pages structurally identical while only some of
        them have been through an editor.
        """
        article = indicator_texts.build_article("__does-not-exist__")
        self.assertEqual([s["role"] for s in article["sections"]], list(indicator_texts.ROLE_ORDER))
        for section in article["sections"]:
            self.assertFalse(section["authored"])
            self.assertIsNone(section["body"])
            self.assertTrue(section["heading"])

    def test_an_authored_section_keeps_its_heading_and_body(self):
        article = indicator_texts.build_article("178")
        by_role = {section["role"]: section for section in article["sections"]}
        self.assertTrue(by_role["quadro"]["authored"])
        self.assertTrue(by_role["quadro"]["body"])
        # No custom heading yet on the migrated entries, so the default shows.
        self.assertEqual(
            by_role["definizione"]["heading"],
            indicator_texts.DEFAULT_HEADINGS["definizione"],
        )


class ProseStaysOnTheLevelItWasWrittenFor(unittest.TestCase):
    """An article cites one level's figures and must not travel to the other.

    Every article that exists was written against the regions. 31 BES indicators
    also have a provincial level, and on those the regional lead named Umbria and
    Piemonte and gave the mean of the regions above a cockpit of provinces. The
    fix is the composed fallback, which reads whichever level it is handed.
    """

    @classmethod
    def setUpClass(cls):
        from app.bes_data import all_bes_indicators

        cls.two_level = [
            item["id"] for item in all_bes_indicators()
            if len(item.get("levels") or {}) > 1
        ]

    def test_a_regional_article_does_not_render_on_the_provincial_view(self):
        checked = 0
        for raw_id in self.two_level:
            regional = indicator_texts.build_article(f"bes:{raw_id}", "regione")
            if not regional["lead"] and not regional["authored_count"]:
                continue
            checked += 1
            provincial = indicator_texts.build_article(f"bes:{raw_id}", "provincia")
            self.assertIsNone(provincial["lead"], raw_id)
            self.assertEqual(provincial["authored_count"], 0, raw_id)
            for section in provincial["sections"]:
                self.assertFalse(section["authored"], f"{raw_id} {section['role']}")
        self.assertGreater(checked, 20, "expected the two-level BES articles to still exist")

    def test_the_page_reports_the_rendered_levels_own_coverage(self):
        """meta.year_min/year_max span every level at once, level's do not.

        10AMB011 is 2017-2020 by province and 2015-2024 by region, so the
        apparatus used to announce a period the provincial series never covered.
        """
        from app import app
        from app.indicator_view import build_indicator_view

        client = app.test_client()
        pattern = re.compile(r"Dato più recente: (\d+).*?periodo (\d+)-(\d+)", re.S)
        for raw_id in self.two_level:
            view = build_indicator_view("bes", raw_id)
            levels = {level["key"]: level for level in view["levels"]}
            if "provincia" not in levels:
                continue
            level = levels["provincia"]
            if level["year_min"] == level["year_max"]:
                continue
            url = f"{view['meta']['canonical_path']}?livello=provincia"
            found = pattern.search(client.get(url).get_data(as_text=True))
            self.assertIsNotNone(found, url)
            self.assertEqual(
                [int(value) for value in found.groups()],
                [level["year_max"], level["year_min"], level["year_max"]],
                url,
            )


if __name__ == "__main__":
    unittest.main()
