import re
import unittest
from unittest.mock import patch

from app import app, atlas_catalog, external_atlas, indicator_universe, indicator_view, provincial_families
from tests.fixtures import external_mef


class ExternalPlatformVerticalSlice(unittest.TestCase):
    def setUp(self):
        self.rows = external_mef.rows()
        self.levels = external_mef.levels()
        self.row_patch = patch("app.external_data.get_external_rows", return_value=self.rows)
        self.atlas_row_patch = patch("app.external_atlas.get_external_rows", return_value=self.rows)
        self.level_patch = patch("app.external_data.get_external_levels", return_value=self.levels)
        self.row_patch.start()
        self.atlas_row_patch.start()
        self.level_patch.start()
        self._clear_caches()
        self.client = app.test_client()

    def tearDown(self):
        self._clear_caches()
        self.level_patch.stop()
        self.atlas_row_patch.stop()
        self.row_patch.stop()

    @staticmethod
    def _clear_caches():
        for module in (external_atlas, provincial_families, indicator_view, atlas_catalog, indicator_universe):
            for name in ("_rows_by_target", "all_external_indicators", "_curated_descriptions",
                         "_index", "all_indicators", "get_atlas_catalog", "_theme_siblings",
                         "_dimension_siblings", "projection", "indexable_catalog", "_rule_level_pages",
                         "_records_by_id", "province_indicators_by_theme"):
                function = getattr(module, name, None)
                if hasattr(function, "cache_clear"):
                    function.cache_clear()
        indicator_universe.cache_clear()

    def test_scheda_province_api_sitemap_e_jsonld(self):
        code = "mef-reddito-irpef-medio"
        path = "/indicatore/reddito-imponibile-medio-per-contribuente/" + code
        view = indicator_view.build_indicator_view("mef", "reddito-irpef-medio")
        self.assertIsNotNone(view)
        self.assertEqual({level["key"] for level in view["levels"]}, {"regione", "provincia"})

        html = self.client.get(path).get_data(as_text=True)
        self.assertEqual(self.client.get(path).status_code, 200)
        self.assertIn("Ministero dell'Economia e delle Finanze", html)
        self.assertIn("https://creativecommons.org/licenses/by/3.0/it/", html)
        self.assertIn('"creator": { "@type": "Organization", "name": "Ministero dell\\u0027Economia', html)
        self.assertNotIn('"name": "Istat"', html[html.find('"creator"'):html.find('"creator"') + 180])
        canonical = re.search(r'<link rel="canonical" href="([^"]+)"', html)
        self.assertEqual(canonical.group(1), "https://divarioitalia.it" + path)

        province_path = path + "/province"
        province_html = self.client.get(province_path).get_data(as_text=True)
        self.assertEqual(self.client.get(province_path).status_code, 200)
        self.assertIn("107 province", province_html)
        self.assertIn("<link rel=\"canonical\" href=\"https://divarioitalia.it" + province_path + "\">", province_html)

        regional_api = self.client.get("/api/indicator/mef:reddito-irpef-medio")
        province_api = self.client.get("/api/indicator/mef:reddito-irpef-medio?livello=provincia")
        self.assertEqual(regional_api.status_code, 200)
        self.assertEqual(province_api.status_code, 200)
        self.assertEqual(len(province_api.get_json()["series"]), 214)
        self.assertEqual(province_api.get_json()["metadata"]["source_label"],
                         "Ministero dell'Economia e delle Finanze, dichiarazioni fiscali")

        record = next(r for r in indicator_universe.projection() if r["meta"]["id"] == "mef:reddito-irpef-medio")
        self.assertEqual({level["key"] for level in record["levels"]}, {"regione", "provincia"})
        self.assertTrue(record["meta"]["indexable"])
        self.assertIsNotNone(indicator_universe.province_payload("mef:reddito-irpef-medio"))

        sitemap = self.client.get("/sitemap.xml").get_data(as_text=True)
        self.assertIn("https://divarioitalia.it" + path, sitemap)
        self.assertIn("https://divarioitalia.it" + province_path, sitemap)


    def test_serie_solo_provinciale_ha_la_sua_scheda(self):
        rows = [row for row in self.rows if row["territory_level"] == "provincia"]
        levels = [level for level in self.levels if level["territory_level"] == "provincia"]
        with patch("app.external_data.get_external_rows", return_value=rows), \
                patch("app.external_atlas.get_external_rows", return_value=rows), \
                patch("app.external_data.get_external_levels", return_value=levels):
            self._clear_caches()
            view = indicator_view.build_indicator_view("mef", "reddito-irpef-medio")
            self.assertEqual([level["key"] for level in view["levels"]], ["provincia"])
            path = "/indicatore/reddito-imponibile-medio-per-contribuente/mef-reddito-irpef-medio"
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)
            self.assertIn("Ministero dell'Economia e delle Finanze", html)
            self.assertIn(("mef", "reddito-irpef-medio"), indicator_universe.all_indicator_refs())
            # Senza regioni la base e' gia' provinciale: la /province torna alla
            # base in un salto, come per le serie BES solo provinciali.
            redirect = self.client.get(path + "/province")
            self.assertEqual(redirect.status_code, 301)
            self.assertTrue(redirect.headers["Location"].endswith(path))


if __name__ == "__main__":
    unittest.main()
