"""Unified /indicatore/ URL scheme and source naming.

Every family now lives under /indicatore/<acronym>-<raw_id>/<slug> and the
pre-migration URLs 301 to it. User-facing labels are institution-first plain
names, never internal jargon on its own.
"""

import unittest

from app import app, sources
from app.atlas_catalog import get_atlas_catalog


class SourceRegistryTest(unittest.TestCase):
    def test_labels_are_plain_and_institution_first(self):
        self.assertEqual(sources.family_label("territorial"), "Istat, indicatori territoriali")
        self.assertEqual(sources.family_label("eurostat"), "Eurostat, statistiche regionali")
        # No family is labelled with a bare internal acronym.
        for family in sources.SOURCES:
            self.assertNotIn(sources.family_label(family).lower(), {"bes", "multiscopo", "multifonte"})

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


if __name__ == "__main__":
    unittest.main()
