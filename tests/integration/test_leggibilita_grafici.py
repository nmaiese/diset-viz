"""The charts do not repeat their numbers in the text an extractor reads, and
the page keeps its tables, downloads and responsive cuts.

The audit of 26 September 2026 (Firecrawl) found the Markdown of the cards
full of repeated numeric sequences. The cause: every dot of the gap strip
carried a `<title>` ("Calabria 21.702"), and the strip is rendered in three
cuts (XL, large, small), so 80 `<title>` elements on a regional card and 321
on each province page, all read as text by an extractor that ignores CSS
and ARIA. Now the text sits in `data-tip`, and v1.js puts the tooltip back
on hover. Screen readers were already fine (the SVG is `aria-hidden`), and
they still are.
"""

import re
import unittest

from app import app

PAGES = (
    "/indicatore/pil-pro-capite/ter-901",
    "/indicatore/tasso-di-disoccupazione/ter-12",
    "/provincia/milano",
    "/regione/lombardia",
)


class TestGraficiLeggibili(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        client = app.test_client()
        cls.html = {path: client.get(path).get_data(as_text=True) for path in PAGES}

    def test_nessun_title_dentro_i_grafici_della_pagina(self):
        for path, html in self.html.items():
            with self.subTest(path=path):
                main = html[html.index("<main"):html.index("</main>")]
                self.assertEqual(main.count("<title>"), 0)

    def test_ogni_punto_della_striscia_porta_il_suo_suggerimento(self):
        for path, html in self.html.items():
            with self.subTest(path=path):
                dots = re.findall(r"<circle class=\"strip__dot[^>]*>", html)
                self.assertTrue(dots)
                for dot in dots:
                    self.assertRegex(dot, r'data-tip="[^"]+"')

    def test_le_strisce_restano_nascoste_agli_screen_reader_e_nei_tre_tagli(self):
        html = self.html["/indicatore/pil-pro-capite/ter-901"]
        for cut in ("chart__xl", "chart__l", "chart__s"):
            self.assertIn(f'class="{cut}"', html)
        for svg in re.findall(r"<svg[^>]*class=\"strip[^\"]*\"[^>]*>", html):
            self.assertIn('aria-hidden="true"', svg)

    def test_tabelle_e_download_restano(self):
        html = self.html["/indicatore/pil-pro-capite/ter-901"]
        self.assertGreaterEqual(html.count("<table"), 2)
        self.assertIn('href="/download/indicator/901.csv"', html)
        self.assertIn('href="/download/indicator/901.json"', html)

    def test_v1_js_rimette_il_suggerimento(self):
        with open("app/static/js/v1.js", encoding="utf-8") as fh:
            js = fh.read()
        self.assertIn('.strip__dot[data-tip]', js)
        self.assertIn('createElementNS("http://www.w3.org/2000/svg", "title")', js)


if __name__ == "__main__":
    unittest.main()
