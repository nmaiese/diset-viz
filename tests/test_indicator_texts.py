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
import unittest.mock
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


def _level_of(entry):
    return entry.get("level") or indicator_texts.DEFAULT_LEVEL


def _view_level(key, entry):
    """The view model of the level an entry was written for, or None.

    Everything level-specific has to come from `levels`, never from `meta`:
    `meta.year_min/year_max` and `meta.explain` span all levels at once, which is
    exactly how a provincial article ended up judged against regional years.
    """
    from app import sources
    from app.indicator_view import build_indicator_view

    family, raw_id = sources.split_internal_id(key)
    view = build_indicator_view(family, raw_id)
    if view is None:
        return None
    wanted = _level_of(entry)
    return next((lv for lv in view["levels"] if lv["key"] == wanted), None)


def _level_year_max(key, entry):
    level = _view_level(key, entry)
    return level["year_max"] if level else None


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

    def test_declared_level_is_one_the_indicator_actually_has(self):
        """A typo in `level` does not fail loudly, it hides the article.

        An entry is used only on the level it declares, so `"level": "provincie"`
        renders nowhere and the page silently falls back to the composed
        skeleton, looking exactly like an article nobody has written.
        """
        from app.indicator_view import build_indicator_view

        wrong = []
        for key, entry in self.texts.items():
            declared = entry.get("level")
            if not declared:
                continue
            family, raw_id = __import__("app.sources", fromlist=["x"]).split_internal_id(key)
            view = build_indicator_view(family, raw_id)
            if view is None:
                continue
            available = [level["key"] for level in view["levels"]]
            if declared not in available:
                wrong.append((key, declared, available))
        self.assertEqual(wrong, [], f"level declared but not available: {wrong[:10]}")

    def test_reviewed_at_is_a_date_when_present(self):
        """`reviewed_at` takes an article out of the review queue, so a value the
        queue cannot read would silently mark it as never reviewed."""
        bad = [
            (key, entry["reviewed_at"])
            for key, entry in self.texts.items()
            if entry.get("reviewed_at") is not None
            and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(entry.get("reviewed_at")))
        ]
        self.assertEqual(bad, [], f"reviewed_at must be YYYY-MM-DD: {bad[:10]}")

    def test_reviewed_vintage_is_an_integer_when_present(self):
        """`reviewed_vintage` records the data year a reviewer actually read, and
        `scripts/review_queue.py` compares it to the article's current `vintage`
        to decide whether the signature has expired. A string "2023" would never
        equal the integer 2023, so a typed slip would re-open every signed
        article forever and make the reading order meaningless.
        """
        bad = [
            (key, entry.get("reviewed_vintage"))
            for key, entry in self.texts.items()
            if entry.get("reviewed_vintage") is not None
            and not isinstance(entry.get("reviewed_vintage"), int)
        ]
        self.assertEqual(bad, [], f"reviewed_vintage must be an integer: {bad[:10]}")

    def test_a_signed_article_records_what_it_was_signed_against(self):
        """A signature with no vintage is one the re-entry rule cannot trust, so
        it re-opens. That is the safe direction, but it is also silent: an agent
        that keeps forgetting the field would rewrite the same article every run
        and never notice. Fail loudly instead."""
        unsigned = [
            key
            for key, entry in self.texts.items()
            if (entry.get("reviewed_at") or "").strip()
            and entry.get("reviewed_vintage") is None
        ]
        self.assertEqual(
            unsigned, [], f"reviewed_at without reviewed_vintage: {unsigned[:10]}"
        )

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


class ParagraphsSurviveRendering(unittest.TestCase):
    """A section written in paragraphs must render in paragraphs.

    The body goes through `analyst_html`, which is Markdown, where a single `\\n`
    is a soft wrap and not a paragraph break. So a section separated by single
    newlines produces exactly one `<p>`, which the filter then strips (it strips
    the wrapper only when there is one), and the whole section lands on the page
    as an unbroken wall of text. Three of ten freshly written articles had it.

    It is invisible in the JSON, invisible in the diff, and invisible to a render
    check that strips the tags and splits on newlines, because that rebuilds the
    paragraphs the browser would never show. The only honest check counts the
    `<p>` the filter actually emits, which is what this does.
    """

    @classmethod
    def setUpClass(cls):
        cls.texts = _load()

    def test_a_body_written_in_paragraphs_produces_more_than_one(self):
        from app.views import analyst_html

        collapsed = []
        for key, entry in self.texts.items():
            for section in entry.get("sections") or []:
                body = section.get("body") or ""
                if "\n" not in body:
                    continue
                paragraphs = str(analyst_html(body)).count("<p>")
                if paragraphs < 2:
                    collapsed.append((key, section.get("role"), body.count("\n")))
        self.assertEqual(
            collapsed, [],
            "sections whose newlines do not survive rendering, so they show as one "
            f"block (id, role, newlines): {collapsed[:10]}",
        )


class InternalLinksInProse(unittest.TestCase):
    """Cross-references in an article, checked the way the blog's already are.

    The prose is rendered through `analyst_html`, so a markdown link in a body
    becomes a real anchor on a real page. Two ways that goes wrong and nothing
    else catches it: a path shape that does not resolve (the atlas link forms
    `/?indicator=` and `/atlante?indicator=` reach the indicator only through
    JavaScript, which is why `tests/test_url_migration.py` bans them in the blog),
    and a path that is canonical in shape but points at an indicator that does
    not exist, because the slug was hand-built instead of copied from the brief.

    The anchor text is checked too, and that one is editorial rather than
    mechanical: Google's own guidance is that the linked words should say where
    they lead, and "clicca qui" in the middle of a paragraph is both worse for a
    reader and worse for the internal-linking model the theme hubs rest on.
    """

    LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    BANNED_FORMS = ("/?indicator=", "/atlante?indicator=", "?indicator=")
    GENERIC_ANCHORS = {
        "qui", "clicca qui", "clicca", "leggi", "leggi di più", "leggi di piu",
        "leggi tutto", "questa pagina", "la pagina", "questo link", "link",
        "vedi", "vedi qui", "scopri di più", "scopri di piu", "approfondisci",
    }

    @classmethod
    def setUpClass(cls):
        from app.atlas_catalog import get_atlas_catalog

        cls.texts = _load()
        cls.canonical = {item["path"] for item in get_atlas_catalog()["indicators"]}

    def _internal_links(self):
        for key, entry in self.texts.items():
            for field, text in _prose(entry):
                for match in self.LINK.finditer(text):
                    anchor, url = match.group(1).strip(), match.group(2).strip()
                    if url.startswith(("http://", "https://", "mailto:")):
                        continue
                    yield key, field, anchor, url

    def test_no_prose_link_uses_a_form_that_needs_javascript(self):
        wrong = [
            (key, field, url)
            for key, field, _, url in self._internal_links()
            if any(form in url for form in self.BANNED_FORMS)
        ]
        self.assertEqual(wrong, [], f"non-canonical indicator links: {wrong[:10]}")

    def test_every_indicator_link_resolves_to_an_indicator_that_exists(self):
        broken = [
            (key, field, url)
            for key, field, _, url in self._internal_links()
            if url.startswith("/indicatore/") and url.split("#")[0].split("?")[0] not in self.canonical
        ]
        self.assertEqual(broken, [], f"links to indicators that do not exist: {broken[:10]}")

    def test_internal_links_point_somewhere_the_site_actually_serves(self):
        """Anything internal that is not an indicator must at least be a path we
        publish, so a theme hub link cannot rot into a 404 unnoticed."""
        from app import app

        client = app.test_client()
        dead = []
        for key, field, _, url in self._internal_links():
            if url.startswith("/indicatore/") or not url.startswith("/"):
                continue
            if client.get(url).status_code not in (200, 301, 308):
                dead.append((key, field, url))
        self.assertEqual(dead, [], f"internal links that do not resolve: {dead[:10]}")

    def test_anchor_text_says_where_it_leads(self):
        generic = [
            (key, field, anchor)
            for key, field, anchor, _ in self._internal_links()
            if anchor.lower().strip(" .,:") in self.GENERIC_ANCHORS
        ]
        self.assertEqual(generic, [], f"anchors that could be any link: {generic[:10]}")


class ArticleVintageDrift(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts = _load()

    def test_every_entry_declares_an_integer_vintage(self):
        missing = [key for key, entry in self.texts.items() if not isinstance(entry.get("vintage"), int)]
        self.assertEqual(missing, [], f"entries without an integer vintage: {missing[:10]}")

    def test_articles_are_not_stale_against_current_data(self):
        """The vintage must be >= the latest year of the level it describes.

        When the data moves forward this fails, flagging the hand-written figures
        for review before the page shows prose that contradicts the cockpit
        directly above it.

        Against the *level*, not against `metadata.year_max`, which spans every
        level at once. 10AMB011 is 2017-2020 by province and 2015-2024 by region,
        so a correct provincial article with vintage 2020 was reported stale
        against the regional 2024. The only way to make the suite green was to
        declare a vintage the provincial series never reaches, and that in turn
        pointed the figure guards at the wrong year.
        """
        stale = []
        for key, entry in self.texts.items():
            year_max = _level_year_max(key, entry)
            vintage = entry.get("vintage")
            if isinstance(year_max, int) and isinstance(vintage, int) and year_max > vintage:
                stale.append((key, entry.get("level", indicator_texts.DEFAULT_LEVEL), vintage, year_max))
        self.assertEqual(
            stale, [],
            f"articles older than the data they describe (id, level, vintage, data year): {stale[:10]}",
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
        """{territory: value} for the year and level the article describes.

        Read from the level's own matrix rather than `payload["series"]`. On a
        two-level BES that series carries the twenty regions only, so a
        provincial article was being compared against a regional table in which
        no province name exists: the two guards below did not fail, they simply
        matched nothing. Now a provincial figure is checked against provinces,
        and the REGIONS regex is the only thing still limiting the coverage.
        """
        level = _view_level(key, entry)
        if level is None:
            return {}
        year = entry.get("vintage") or level["year_max"]
        matrix = level["matrix"].get(str(year)) or {}
        names = {row["key"]: row["name"] for row in level["observations"]}
        return {
            names.get(territory_key, territory_key): value
            for territory_key, value in matrix.items()
            if value is not None
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
        """Structural, and deliberately not pinned to one indicator's content.

        This used to assert that id 178 showed the *default* heading on
        `definizione`, which was true only while nobody had written that section.
        But 178 is the worked example in every doc and every command, so it is
        the first article an editor completes, and the moment the writer did the
        thing it is told to do (write its own h2) the suite went red on correct
        work. The writer's own contract says to run the guards and read the
        result, so it would have removed the heading to make the test pass.
        """
        key, entry = next(
            (key, entry) for key, entry in sorted(_load().items())
            if any((s.get("body") or "").strip() for s in entry.get("sections") or [])
        )
        authored_roles = {
            s["role"] for s in entry["sections"] if (s.get("body") or "").strip()
        }
        article = indicator_texts.build_article(key, entry.get("level", indicator_texts.DEFAULT_LEVEL))
        for section in article["sections"]:
            with self.subTest(indicator=key, role=section["role"]):
                self.assertTrue(section["heading"], "every section renders a heading")
                if section["role"] in authored_roles:
                    self.assertTrue(section["authored"])
                    self.assertTrue(section["body"])
                else:
                    # Not written: the template composes it, so body stays None.
                    self.assertFalse(section["authored"])
                    self.assertIsNone(section["body"])

    def test_an_authored_heading_wins_over_the_default(self):
        """The `h` an author writes must reach the page. Synthetic on purpose."""
        entry = {"sections": [{"role": "quadro", "h": "Un titolo scritto a mano", "body": "Corpo."}]}
        with unittest.mock.patch.object(indicator_texts, "get_text", return_value=entry):
            article = indicator_texts.build_article("__synthetic__")
        by_role = {section["role"]: section for section in article["sections"]}
        self.assertEqual(by_role["quadro"]["heading"], "Un titolo scritto a mano")
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

    def test_a_single_level_indicator_is_left_exactly_as_it_was(self):
        """Nothing to retarget, so nothing may change.

        The first version of the level scoping substituted the bare noun, which
        turned the territorial "in tutti i territori regionali" into "in tutti i
        regioni" on 393 pages that never had the bug. This is the invariant that
        would have caught it, and it costs one comparison.
        """
        from app.indicator_view import build_indicator_view

        for family, raw_id in (("territorial", "178"), ("bes", "01SAL003")):
            view = build_indicator_view(family, raw_id)
            if view is None or len(view["levels"]) != 1:
                continue
            with self.subTest(indicator=f"{family}:{raw_id}"):
                self.assertEqual(view["levels"][0]["explain"], view["meta"]["explain"])

    def test_the_composed_article_names_the_level_it_is_rendered_at(self):
        """The composed text is level-scoped too, not just the authored one.

        `meta.explain` is built once per indicator with a fixed level, and two of
        its sentences name that level. On the provincial view of all 34 two-level
        BES indicators the definizione said "in tutte le regioni" and the limiti
        said "il confronto tra regioni", above 103 provinces. It is the only
        article those pages can show, since every authored one is regional.
        """
        from app.indicator_view import build_indicator_view

        checked = 0
        for raw_id in self.two_level:
            view = build_indicator_view("bes", raw_id)
            levels = {level["key"]: level for level in view["levels"]}
            if "provincia" not in levels:
                continue
            checked += 1
            explain = levels["provincia"]["explain"]
            for field in ("scope", "caveat"):
                with self.subTest(indicator=raw_id, field=field):
                    self.assertNotIn("regioni", (explain.get(field) or "").lower())
        self.assertGreater(checked, 20)

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
