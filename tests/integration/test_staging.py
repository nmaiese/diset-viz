"""Lo stage deve comportarsi da stage.

Il rischio che questi test sorvegliano non e' "il deploy fallisce", che si vede
subito, ma "il deploy riesce e Google indicizza un duplicato completo del sito
su un secondo dominio", che non si vede affatto finche' non e' successo. La SEO
tecnica di divarioitalia.it questo repo se l'e' gia' dovuta riprendere una volta
(il default-deny in `add_security_headers` esiste per quello), quindi la
modalita' stage viene verificata invece che dedotta.

`STAGING` si legge come attributo del modulo a ogni richiesta, non alla
importazione, ed e' per questo che si puo' accendere e spegnere qui.
"""
import unittest

from app import app, config
from app.cache import cache


class StagingModeTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self._staging = config.STAGING
        # La home e' cachata per 300s: senza svuotare, questi test leggerebbero
        # la risposta prodotta da un altro test nell'altra modalita'.
        cache.clear()

    def tearDown(self):
        config.STAGING = self._staging
        cache.clear()

    # --- stage acceso -----------------------------------------------------
    def test_every_response_is_noindex(self):
        config.STAGING = True
        for path in ("/", "/blog", "/atlante", "/metodologia", "/ricerca?q=lavoro"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200, path)
                self.assertIn("noindex", response.headers.get("X-Robots-Tag", ""), path)

    def test_robots_txt_forbids_everything(self):
        config.STAGING = True
        body = self.client.get("/robots.txt").get_data(as_text=True)
        self.assertIn("Disallow: /", body)
        # Il robots di produzione dice il contrario e pubblica la sitemap del
        # dominio vero: nessuna delle due cose deve uscire da qui.
        self.assertNotIn("Allow: /", body)
        self.assertNotIn("Sitemap:", body)

    def test_pages_carry_the_staging_meta_and_banner(self):
        config.STAGING = True
        for path in ("/", "/blog"):
            with self.subTest(path=path):
                html = self.client.get(path).get_data(as_text=True)
                self.assertIn('<meta name="robots" content="noindex, nofollow, noarchive">', html)
                # Senza la fascia la copia e' indistinguibile dal sito vero, che
                # e' l'errore che uno stage identico all'originale invita a fare.
                self.assertIn("Ambiente di stage", html)

    def test_staging_does_not_serve_an_index_signal_anywhere(self):
        config.STAGING = True
        for path in ("/", "/blog", "/sitemap.xml", "/llms.txt"):
            with self.subTest(path=path):
                header = self.client.get(path).headers.get("X-Robots-Tag", "")
                self.assertNotIn("index, follow", header, path)

    # --- stage spento: la produzione non cambia ---------------------------
    def test_production_still_indexes(self):
        config.STAGING = False
        response = self.client.get("/")
        self.assertIn("index, follow", response.headers.get("X-Robots-Tag", ""))
        html = response.get_data(as_text=True)
        self.assertNotIn("Ambiente di stage", html)
        self.assertIn('content="index, follow', html)

    def test_production_robots_is_unchanged(self):
        config.STAGING = False
        body = self.client.get("/robots.txt").get_data(as_text=True)
        self.assertIn("Allow: /", body)
        self.assertIn("Sitemap:", body)

    def test_noindex_paths_stay_noindex_in_production(self):
        # La modalita' stage aggiunge un ramo prima di questa logica: va
        # verificato che non l'abbia scavalcata.
        config.STAGING = False
        header = self.client.get("/account").headers.get("X-Robots-Tag", "")
        self.assertIn("noindex", header)


if __name__ == "__main__":
    unittest.main()
