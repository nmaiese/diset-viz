import re
import unittest

from app import app, editorial_state, indicator_universe


class AdsenseIndicatorIndexingTest(unittest.TestCase):
    CLASS_A = "/indicatore/adulti-che-partecipano-all-apprendimento-permanente-totale/ter-99"
    CLASS_B = "/indicatore/affollamento-degli-istituti-di-pena/bes-06POL012P"
    CLASS_B_PROVINCES = "/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001/province"
    PROVINCE_ZERO_WORDS_CODES = {
        "bes-12SER020", "bes-09PAE008", "bes-10AMB008", "bes-10AMB016",
        "bes-02IST006-N22", "bes-12SER007", "bes-11RIC025", "bes-01SAL005",
        "bes-02IST001", "bes-02IST007-N22", "bes-06POL001", "bes-02IST002-N22",
        "bes-12SER024", "bes-03LAV002-N22", "bes-03LAV001-N22",
    }

    @classmethod
    def setUpClass(cls):
        indicator_universe.cache_clear()
        editorial_state.build_queue.cache_clear()
        editorial_state.catalogo.cache_clear()
        from app.cache import cache
        cache.clear()
        cls.client = app.test_client()
        sitemap = cls.client.get("/sitemap.xml").get_data(as_text=True)
        cls.sitemap_paths = set(re.findall(r"https://divarioitalia\.it([^<]+)", sitemap))

    def test_classe_b_noindex_e_fuori_sitemap(self):
        html = self.client.get(self.CLASS_B).get_data(as_text=True)
        self.assertIn('<meta name="robots" content="noindex, follow">', html)
        self.assertNotIn("non ha ancora un commento scritto", html)
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

    def test_solo_le_19_schede_base_senza_prosa_sono_noindex(self):
        rows = [
            row for row in editorial_state.catalogo()["righe"]
            if row["predefinito"] and row["indicizzabile"] and row["parole"] == 0
        ]
        self.assertEqual(len(rows), 19)
        for row in rows:
            path = row["percorso"]
            with self.subTest(path=path):
                response = self.client.get(path)
                html = response.get_data(as_text=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn('<meta name="robots" content="noindex, follow">', html)
                self.assertEqual(response.headers.get("X-Robots-Tag"), "noindex, follow")
                self.assertNotIn(path, self.sitemap_paths)

    def test_quindici_viste_provinciali_a_zero_parole_restano_indicizzate(self):
        rows = [
            row for row in editorial_state.catalogo()["righe"]
            if not row["predefinito"] and row["livello"] == "provincia"
            and row["codice"] in self.PROVINCE_ZERO_WORDS_CODES and row["parole"] == 0
        ]
        self.assertEqual({row["codice"] for row in rows}, self.PROVINCE_ZERO_WORDS_CODES)
        self.assertEqual(len(rows), 15)
        for row in rows:
            path = row["percorso"] + "/province"
            with self.subTest(path=path):
                response = self.client.get(path)
                html = response.get_data(as_text=True)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn('<meta name="robots" content="noindex', html)
                self.assertNotEqual(response.headers.get("X-Robots-Tag"), "noindex, follow")
                self.assertIn(path, self.sitemap_paths)

    def test_schede_con_prosa_restano_indicizzabili(self):
        rows = [
            row for row in editorial_state.catalogo()["righe"]
            if row["predefinito"] and row["indicizzabile"] and row["parole"] > 0
            and row["codice"] in {"ter-12", "ter-104", "bes-04BEC002P"}
        ]
        self.assertEqual({row["codice"] for row in rows}, {"ter-12", "ter-104", "bes-04BEC002P"})
        for row in rows:
            with self.subTest(codice=row["codice"]):
                response = self.client.get(row["percorso"])
                html = response.get_data(as_text=True)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn('<meta name="robots" content="noindex', html)
                self.assertNotEqual(response.headers.get("X-Robots-Tag"), "noindex, follow")
                self.assertIn(row["percorso"], self.sitemap_paths)


if __name__ == "__main__":
    unittest.main()
