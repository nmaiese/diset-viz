"""Structured data on one page per template: valid JSON, schema.org, and
consistent with the canonical and with the visible page.

These are tests on the shared templates, one instance per family: every
block must be JSON that parses (a stray comma in a Jinja loop breaks the
whole block without any error), a `Dataset` or a `CollectionPage` must have
the page's canonical as its URL, and the last item of the breadcrumb must be
the page itself. On regions and provinces the name in the JSON-LD is the
name of the territory in the H1.
"""

import html as html_lib
import json
import re
import unittest

from app import app

PAGES = (
    "/",
    "/indicatore/pil-pro-capite/ter-901",
    "/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001/province",
    "/regione/lombardia",
    "/regione/calabria",
    "/provincia/milano",
    "/provincia/lecce",
    "/province",
    "/regioni",
    "/qualita-della-vita",
    "/atlante",
)

LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def _blocks(page):
    return [json.loads(block) for block in LD.findall(page)]


def _nodes(block):
    if isinstance(block, list):
        for item in block:
            yield from _nodes(item)
    elif isinstance(block, dict):
        if "@graph" in block:
            yield from _nodes(block["@graph"])
        else:
            yield block


class TestDatiStrutturati(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        client = app.test_client()
        cls.pages = {}
        for path in PAGES:
            response = client.get(path)
            cls.pages[path] = (response.status_code, response.get_data(as_text=True))

    def test_ogni_blocco_e_json_valido_di_schema_org(self):
        for path, (status, page) in self.pages.items():
            with self.subTest(path=path):
                self.assertEqual(status, 200)
                blocks = _blocks(page)
                self.assertTrue(blocks, "no JSON-LD")
                for block in blocks:
                    context = block.get("@context") if isinstance(block, dict) else None
                    self.assertIn("schema.org", str(context))

    def test_dataset_e_collectionpage_hanno_l_url_canonico(self):
        for path, (_, page) in self.pages.items():
            canonical = re.search(r'<link rel="canonical" href="([^"]+)"', page).group(1)
            for node in (n for b in _blocks(page) for n in _nodes(b)):
                if node.get("@type") in ("Dataset", "CollectionPage") and "url" in node:
                    with self.subTest(path=path, type=node["@type"]):
                        self.assertEqual(node["url"], canonical)

    def test_la_briciola_finisce_sulla_pagina(self):
        for path, (_, page) in self.pages.items():
            if path == "/":
                continue
            canonical = re.search(r'<link rel="canonical" href="([^"]+)"', page).group(1)
            crumbs = [n for b in _blocks(page) for n in _nodes(b) if n.get("@type") == "BreadcrumbList"]
            with self.subTest(path=path):
                self.assertEqual(len(crumbs), 1)
                items = crumbs[0]["itemListElement"]
                self.assertEqual([i["position"] for i in items], list(range(1, len(items) + 1)))
                last = items[-1].get("item")
                last_url = last.get("@id") if isinstance(last, dict) else last
                self.assertEqual(last_url, canonical)

    def test_il_territorio_del_json_ld_e_quello_dell_h1(self):
        for path in ("/regione/lombardia", "/regione/calabria", "/provincia/milano", "/provincia/lecce"):
            page = self.pages[path][1]
            h1 = html_lib.unescape(re.sub(r"<[^>]+>", "", re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S).group(1)))
            places = [n.get("spatialCoverage", {}).get("name") for b in _blocks(page) for n in _nodes(b)
                      if n.get("@type") == "Dataset"]
            with self.subTest(path=path):
                self.assertTrue(places and places[0])
                self.assertIn(places[0], h1)


if __name__ == "__main__":
    unittest.main()
