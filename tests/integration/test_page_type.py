"""Il page_view di ogni famiglia di pagine porta il suo `page_type`, una volta.

Fino al 26 settembre 2026 tutto cio' che non era atlante, confronto o blog
diceva "server", e in GA4 la dimensione `page_type` non separava la home dalle
schede, le regioni dalle province, la qualita' della vita dal quiz. La
classificazione e' una sola (`app/page_types.py`); qui si guarda che arrivi nel
page_view di una pagina vera per ogni famiglia, anche quando la pagina esce dal
ripiego o non passa dalla regia della 1.0, e che il page_view resti uno.
"""

import re
import unittest

from app import app, config
from app.page_types import PAGE_TYPES, page_type

CASES = {
    "/": "home",
    "/indicatore/pil-pro-capite/ter-901": "indicator",
    "/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001/province": "indicator",
    "/regione/lombardia": "region",
    "/regioni": "region",
    "/provincia/milano": "province",
    "/province": "province",
    "/atlante": "atlas",
    "/confronto": "atlas",
    "/temi": "theme",
    "/blog": "blog",
    "/qualita-della-vita": "quality_of_life",
    "/qualita-della-vita/classifica/province": "quality_of_life",
    "/quiz": "game",
    "/ricerca?q=lavoro": "search",
    "/divari-regionali": "hub",
    "/metodologia": "info",
    "/chi-siamo": "info",
}

PAGE_VIEW = re.compile(r"event: 'page_view',.*?page_type: (\"[a-z_]+\")", re.S)


class TestPageTypeClassification(unittest.TestCase):
    def test_i_prefissi_valgono_per_segmento_intero(self):
        self.assertEqual(page_type("/blog/un-articolo"), "blog")
        self.assertEqual(page_type("/blogxyz"), "other")
        self.assertEqual(page_type("/regione/lazio"), "region")
        self.assertEqual(page_type("/regionale"), "other")
        self.assertEqual(page_type("/legacy-reddito"), "legacy")
        self.assertEqual(page_type("/tema/lavoro"), "theme")

    def test_ogni_tipo_e_dichiarato(self):
        for path, kind in CASES.items():
            self.assertIn(kind, PAGE_TYPES)
            self.assertEqual(page_type(path.split("?")[0]), kind, path)


class TestPageTypeInPagina(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = config.GOOGLE_TAG_MANAGER_ID
        config.GOOGLE_TAG_MANAGER_ID = "GTM-TEST"
        cls.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        config.GOOGLE_TAG_MANAGER_ID = cls.original

    def test_un_page_view_col_tipo_della_famiglia(self):
        for path, kind in CASES.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertEqual(html.count("event: 'page_view'"), 1)
                self.assertEqual(PAGE_VIEW.findall(html), [f'"{kind}"'])
                self.assertNotIn('"server"', html)

    def test_la_404_dice_error_anche_sotto_un_prefisso_classificato(self):
        for path in ("/indicatore/non-esiste/ter-999999", "/regione/atlantide", "/pagina-che-non-ce"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(PAGE_VIEW.findall(response.get_data(as_text=True)), ['"error"'])

    def test_il_page_view_toglie_i_parametri_del_login(self):
        html = self.client.get("/").get_data(as_text=True)
        head = html[html.index("event: 'page_view'") - 800:html.index("event: 'page_view'")]
        for param in ("'code'", "'state'", "'access_token'"):
            self.assertIn(param, head)
        self.assertIn("url.hash = ''", head)
        self.assertNotIn("window.location.href,", html[html.index("event: 'page_view'"):][:400])


if __name__ == "__main__":
    unittest.main()
