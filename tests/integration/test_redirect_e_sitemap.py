"""Redirects, canonical and sitemap: every old URL reaches the canonical one
in a single permanent hop, and the sitemap lists only final URLs.

The audit of 26 September 2026 found the rules mostly right, with three
holes that these tests now guard:
- the pre-migration numeric URL (`/indicatore/901-pil-pro-capite`) dropped
  `anno` and `regione` from the 301;
- the same URL on `www.` took two hops, one to the apex and one to the
  canonical;
- a trailing slash (`/regione/lazio/`) returned 404 on pages that exist
  without it.
The sitemap tests work from the generator, over every URL it lists.
"""

import re
import unittest
from urllib.parse import urlsplit

from app import app, config

APEX = "https://divarioitalia.it"
WWW = "https://www.divarioitalia.it"
LEGACY = "/indicatore/901-pil-pro-capite"
CANONICAL = "/indicatore/pil-pro-capite/ter-901"


def _hops(client, url, base_url, limit=5):
    """The chain of (status, Location) up to the first non-redirect."""
    chain = []
    for _ in range(limit):
        response = client.get(url, base_url=base_url)
        chain.append((response.status_code, response.headers.get("Location")))
        if response.status_code not in (301, 302, 307, 308):
            return chain
        location = response.headers["Location"]
        parts = urlsplit(location)
        if parts.netloc:
            base_url = f"{parts.scheme}://{parts.netloc}"
        url = parts.path + (f"?{parts.query}" if parts.query else "")
    return chain


class TestLegacyRedirects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def test_numeric_legacy_url_is_one_permanent_hop(self):
        for path in (LEGACY, "/indicatore/901"):
            with self.subTest(path=path):
                chain = _hops(self.client, path, APEX)
                self.assertEqual(chain, [(301, CANONICAL), (200, None)])

    def test_numeric_legacy_url_keeps_year_and_region(self):
        response = self.client.get(f"{LEGACY}?anno=2020&regione=lazio", base_url=APEX)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.headers["Location"], f"{CANONICAL}?anno=2020&regione=lazio")

    def test_atlante_indicator_link_keeps_year(self):
        response = self.client.get("/atlante?indicator=901&anno=2020", base_url=APEX)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.headers["Location"], f"{CANONICAL}?anno=2020")

    def test_www_plus_legacy_is_one_hop(self):
        chain = _hops(self.client, f"{LEGACY}?anno=2019", WWW)
        self.assertEqual(chain[0], (301, f"{APEX}{CANONICAL}?anno=2019"))
        self.assertEqual(chain[1], (200, None))

    def test_www_is_one_hop_to_the_apex_for_every_other_path(self):
        for path in ("/regione/lazio", "/provincia/milano", CANONICAL, "/"):
            with self.subTest(path=path):
                response = self.client.get(path, base_url=WWW)
                self.assertEqual(response.status_code, 301)
                self.assertEqual(response.headers["Location"], f"{APEX}{path}")

    def test_trailing_slash_redirects_to_the_page_without_it(self):
        for path in ("/regione/lazio/", "/blog/", f"{CANONICAL}/", "/regioni/"):
            with self.subTest(path=path):
                chain = _hops(self.client, path, APEX)
                self.assertEqual(chain, [(301, path.rstrip("/")), (200, None)])

    def test_trailing_slash_on_a_missing_page_stays_404_or_reaches_it(self):
        self.assertEqual(self.client.get("/pagina-che-non-esiste/", base_url=APEX).status_code, 404)
        self.assertEqual(self.client.get("/api/nope/", base_url=APEX).status_code, 404)


class TestSitemapFinalUrls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        client = app.test_client()
        sitemap = client.get("/sitemap.xml", base_url=APEX).get_data(as_text=True)
        cls.locs = re.findall(r"<loc>(.*?)</loc>", sitemap)
        cls.client = client

    def test_only_apex_https_and_no_legacy_form(self):
        self.assertGreater(len(self.locs), 400)
        self.assertEqual(len(self.locs), len(set(self.locs)))
        for loc in self.locs:
            self.assertTrue(loc.startswith(config.SITE_URL + "/") or loc == config.SITE_URL, loc)
            self.assertNotIn("www.", loc)
            path = urlsplit(loc).path
            self.assertNotRegex(path, r"^/indicatore/\d")
            # The quality-of-life rankings list their profiles on purpose
            # (`?profilo=`), each a page of its own. Territories and cards never.
            if path.startswith(("/indicatore/", "/regione/", "/provincia/")):
                self.assertNotIn("?", loc)
            self.assertFalse(path != "/" and path.endswith("/"), loc)

    def test_every_indicator_loc_is_final_and_self_canonical(self):
        """Every indicator URL in the sitemap answers 200 with itself as
        canonical: no redirect, no canonical elsewhere."""
        for loc in (loc for loc in self.locs if "/indicatore/" in loc):
            with self.subTest(loc=loc):
                response = self.client.get(urlsplit(loc).path, base_url=APEX)
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                canonical = re.search(r'<link rel="canonical" href="([^"]+)"', html)
                self.assertIsNotNone(canonical)
                self.assertEqual(canonical.group(1), loc)


if __name__ == "__main__":
    unittest.main()
