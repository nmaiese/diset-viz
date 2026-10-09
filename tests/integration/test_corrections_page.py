import re
import unittest

from app import app, nav


class CorrectionsPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def test_page_is_indexable_canonical_and_in_sitemap(self):
        response = self.client.get("/correzioni")
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('data-v1="correzioni"', html)
        self.assertIn('<link rel="canonical" href="https://divarioitalia.it/correzioni">', html)
        self.assertIn('<meta name="robots" content="index, follow', html)
        self.assertIn("Registro iniziato l'8 ottobre 2026", html)
        self.assertIn("Link a documenti Istat ed Eurostat non più raggiungibili", html)
        self.assertIn("Sostituiti con le pagine attuali o rimossi", html)
        self.assertIsNone(re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", html))
        self.assertIn("https://divarioitalia.it/correzioni", self.client.get("/sitemap.xml").get_data(as_text=True))

    def test_footer_entry_and_links_from_trust_pages(self):
        voce = next(item for item in nav.FOOTER if item["path"] == "/correzioni")
        self.assertEqual(voce["label"], "Errori e correzioni")
        for path in ("/", "/indicatore/pil-pro-capite/ter-901"):
            html = self.client.get(path).get_data(as_text=True)
            self.assertIn('href="/correzioni"', html)
        self.assertIn('href="/correzioni"', self.client.get("/contatti").get_data(as_text=True))
        self.assertIn('href="/correzioni"', self.client.get("/metodologia").get_data(as_text=True))

    def test_five_pages_show_review_date(self):
        paths = ("/chi-siamo", "/metodologia", "/privacy", "/termini", "/correzioni")
        for path in paths:
            with self.subTest(path=path):
                html = self.client.get(path).get_data(as_text=True)
                self.assertIn("Ultima revisione:", html)
                self.assertRegex(html, r'<time datetime="2026-10-\d{2}">')
