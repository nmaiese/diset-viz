import re
import unittest

from app import app


class AdsenseIndicatorIndexingTest(unittest.TestCase):
    CLASS_A = "/indicatore/adulti-che-partecipano-all-apprendimento-permanente-totale/ter-99"
    CLASS_B = "/indicatore/affollamento-degli-istituti-di-pena/bes-06POL012P"
    CLASS_B_PROVINCES = "/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001/province"

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        sitemap = cls.client.get("/sitemap.xml").get_data(as_text=True)
        cls.sitemap_paths = set(re.findall(r"https://divarioitalia\.it([^<]+)", sitemap))

    def test_classe_b_noindex_e_fuori_sitemap(self):
        html = self.client.get(self.CLASS_B).get_data(as_text=True)
        self.assertIn('<meta name="robots" content="noindex, follow">', html)
        self.assertIn("non ha ancora un commento scritto", html)
        self.assertNotIn(self.CLASS_B, self.sitemap_paths)

    def test_classe_a_index_e_in_sitemap(self):
        html = self.client.get(self.CLASS_A).get_data(as_text=True)
        self.assertNotIn('<meta name="robots" content="noindex', html)
        self.assertIn(self.CLASS_A, self.sitemap_paths)

    def test_classe_b_esclude_anche_la_sua_vista_provinciale(self):
        response = self.client.get(self.CLASS_B_PROVINCES)
        self.assertEqual(response.headers.get("X-Robots-Tag"), "noindex, follow")
        self.assertNotIn(self.CLASS_B_PROVINCES, self.sitemap_paths)

    def test_csv_di_approfondimento_noindex_fuori_sitemap(self):
        path = "/static/data/articles/giovani-morti-in-strada-nord-sud.csv"
        response = self.client.get(path)
        response.close()
        self.assertEqual(response.status_code, 200)
        self.assertIn("noindex", response.headers.get("X-Robots-Tag", ""))
        self.assertNotIn(path, self.sitemap_paths)


if __name__ == "__main__":
    unittest.main()
