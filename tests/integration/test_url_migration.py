"""Unified /indicatore/ URL scheme and source naming.

Every family now lives under /indicatore/<acronym>-<raw_id>/<slug> and the
pre-migration URLs 301 to it. User-facing labels are institution-first plain
names, never internal jargon on its own.
"""

import re
import unittest
from pathlib import Path

from app import app, sources
from app.atlas_catalog import get_atlas_catalog


class SourceRegistryTest(unittest.TestCase):
    def test_labels_are_plain_and_institution_first(self):
        self.assertEqual(sources.family_label("territorial"), "Istat, indicatori territoriali")
        self.assertEqual(sources.family_label("eurostat"), "Eurostat, statistiche regionali")
        # No family is labelled with a bare internal acronym.
        for family in sources.SOURCES:
            self.assertNotIn(sources.family_label(family).lower(), {"bes", "multiscopo", "multifonte"})

    def test_score_breakdown_labels_come_from_the_registry(self):
        """The visible score breakdown used to carry a second, hand-written set
        of names ("BES", "Multiscopo"), the bare internal acronyms the naming
        rules keep out of user-facing copy."""
        from app.quality_life_bes import build_bes_ranking

        breakdown = build_bes_ranking("regione", "standard")["methodology"]["source_breakdown"]
        self.assertTrue(breakdown)
        for entry in breakdown:
            expected = sources.family_short_label(entry["family"])
            self.assertEqual(entry["label"].lower(), expected.lower())
            self.assertNotIn(entry["label"].lower(), {"bes", "multiscopo"})

    def test_url_round_trip_handles_dashed_ids(self):
        # Keyword-first: the slug leads, the resolving code is the last segment.
        # BES variant ids contain dashes; they must survive the round trip.
        url = sources.indicator_url("bes", "09PAE009-N25", "verde-storico")
        self.assertEqual(url, "/indicatore/verde-storico/bes-09PAE009-N25")
        code = url.split("/")[-1]
        self.assertEqual(sources.parse_indicator_code(code), ("bes", "09PAE009-N25"))

    def test_parse_rejects_unknown_and_legacy(self):
        self.assertIsNone(sources.parse_indicator_code("105-something"))
        self.assertEqual(sources.legacy_territorial_id("105-something"), "105")
        self.assertIsNone(sources.legacy_territorial_id("bes-10AMB014"))


class UnifiedUrlRoutingTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.catalog = get_atlas_catalog()["indicators"]

    def _one(self, family):
        return next((i for i in self.catalog if i["catalog_family"] == family), None)

    def test_all_catalog_paths_are_unified(self):
        for item in self.catalog:
            self.assertTrue(item["path"].startswith("/indicatore/"), item["path"])

    def test_new_urls_resolve(self):
        for family in ("territorial", "bes", "multiscopo"):
            item = self._one(family)
            if item is None:
                continue
            self.assertEqual(self.client.get(item["path"]).status_code, 200, family)

    def test_legacy_territorial_redirects(self):
        ter = self._one("territorial")
        response = self.client.get(f"/indicatore/{ter['id']}-x")
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response.headers["Location"].endswith(ter["path"]))

    def test_legacy_bes_redirects(self):
        bes = self._one("bes")
        raw = bes["id"].split(":", 1)[1]
        response = self.client.get(f"/qualita-della-vita/indicatore/{raw}/qualcosa")
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response.headers["Location"].endswith(bes["path"]))

    def test_legacy_multiscopo_redirects(self):
        mul = self._one("multiscopo")
        if mul is None:
            self.skipTest("no multiscopo data present")
        raw = mul["id"].split(":", 1)[1]
        response = self.client.get(f"/qualita-della-vita/indicatore/multiscopo-{raw}/x")
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response.headers["Location"].endswith(mul["path"]))


class EditorialLinksAreCanonicalTest(unittest.TestCase):
    """Articles must link to the canonical indicator page.

    `/?indicator=...` now opens the home page, and `/atlante?indicator=...`
    lands on the atlas and only reaches the indicator through JavaScript. Both
    are broken destinations for a reader without JS and for a crawler."""

    LEGACY = re.compile(r"\((/(?:atlante)?\?indicator=[^)]*)\)")

    def test_no_post_links_to_a_query_string_indicator(self):
        posts = Path(__file__).resolve().parent.parent.parent / "content" / "posts"
        offenders = [
            (md.name, match)
            for md in sorted(posts.glob("*.md"))
            for match in self.LEGACY.findall(md.read_text(encoding="utf-8"))
        ]
        self.assertEqual(offenders, [], f"legacy atlas links in posts: {offenders[:10]}")

    def test_every_indicator_link_in_posts_resolves(self):
        posts = Path(__file__).resolve().parent.parent.parent / "content" / "posts"
        client = app.test_client()
        link_re = re.compile(r"\((/indicatore/[^)\s]+)\)")
        seen = set()
        for md in sorted(posts.glob("*.md")):
            for href in link_re.findall(md.read_text(encoding="utf-8")):
                if href in seen:
                    continue
                seen.add(href)
                self.assertEqual(
                    client.get(href).status_code, 200, f"{md.name} -> {href}"
                )
        self.assertTrue(seen, "no canonical indicator links found in the posts")


if __name__ == "__main__":
    unittest.main()
