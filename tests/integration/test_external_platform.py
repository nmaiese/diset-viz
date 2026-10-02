import inspect
import json
import re
import sys
import unittest
from unittest.mock import patch

from app import app, indicator_universe, indicator_view
from tests.fixtures import external_mef


JSONLD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def _robots(html):
    """Le prime due direttive del meta robots: `max-snippet` e simili non contano qui."""
    content = re.search(r'<meta name="robots" content="([^"]+)"', html).group(1)
    return ", ".join(part.strip() for part in content.split(",")[:2])


def _walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


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
        """Svuota ogni cache di processo in `app.*` che puo' aver visto la
        fixture, prima e dopo: altrimenti un modulo che gira dopo questo legge
        un catalogo con la serie MEF finta dentro. Restano fuori i loader dei
        CSV che la fixture non tocca, costosi da rileggere."""
        untouched = {"app.data", "app.bes_data", "app.indicator_texts", "app.blog"}
        for name, module in list(sys.modules.items()):
            if not (name == "app" or name.startswith("app.")) or name in untouched or module is None:
                continue
            for attr in list(vars(module).values()):
                if not (inspect.isfunction(attr) or type(attr).__name__ == "_lru_cache_wrapper"):
                    continue  # niente proxy di Flask, che fuori contesto sollevano
                if callable(getattr(attr, "cache_clear", None)) and attr.__module__ == name:
                    attr.cache_clear()
        indicator_universe.cache_clear()
        # Anche la cache delle pagine (Flask-Caching): in una suite intera un
        # `/atlante` reso prima, con i dati veri, restava servito alla fixture.
        from app.cache import cache

        cache.clear()

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
        self._assert_jsonld_mef(html)
        self.assertEqual(_robots(html), "index, follow")
        canonical = re.search(r'<link rel="canonical" href="([^"]+)"', html)
        self.assertEqual(canonical.group(1), "https://divarioitalia.it" + path)

        province_path = path + "/province"
        province_html = self.client.get(province_path).get_data(as_text=True)
        self.assertEqual(self.client.get(province_path).status_code, 200)
        self.assertIn("107 province", province_html)
        self.assertIn("<link rel=\"canonical\" href=\"https://divarioitalia.it" + province_path + "\">", province_html)
        self._assert_jsonld_mef(province_html)
        self.assertEqual(_robots(province_html), "index, follow")

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


    def _assert_jsonld_mef(self, html):
        blocks = [json.loads(block) for block in JSONLD.findall(html)]
        self.assertTrue(blocks)
        dataset = next(block for block in _walk(blocks) if block.get("@type") == "Dataset")
        self.assertEqual(dataset["license"], "https://creativecommons.org/licenses/by/3.0/it/")
        self.assertIn("Ministero dell'Economia e delle Finanze", json.dumps(dataset["creator"], ensure_ascii=False))
        self.assertNotIn("Istat", json.dumps(blocks, ensure_ascii=False))

    def test_province_fuori_regola_restano_noindex_e_fuori_sitemap(self):
        levels = [{**level, "year_max": "2022"} if level["territory_level"] == "provincia" else level
                  for level in self.levels]
        rows = [row for row in self.rows if not (row["territory_level"] == "provincia" and row["year"] == "2024")]
        path = "/indicatore/reddito-imponibile-medio-per-contribuente/mef-reddito-irpef-medio"
        province_path = path + "/province"
        with patch("app.external_data.get_external_rows", return_value=rows), \
                patch("app.external_atlas.get_external_rows", return_value=rows), \
                patch("app.external_data.get_external_levels", return_value=levels):
            self._clear_caches()
            base = self.client.get(path)
            self.assertEqual(base.status_code, 200)
            self.assertEqual(_robots(base.get_data(as_text=True)), "index, follow")
            province = self.client.get(province_path)
            self.assertEqual(province.status_code, 200)
            self.assertEqual(_robots(province.get_data(as_text=True)), "noindex, follow")
            sitemap = self.client.get("/sitemap.xml").get_data(as_text=True)
            self.assertIn("https://divarioitalia.it" + path + "<", sitemap)
            self.assertNotIn("https://divarioitalia.it" + province_path, sitemap)
            themed = [item["path"] for items in indicator_view.province_indicators_by_theme().values()
                      for item in items]
            self.assertNotIn(province_path, themed)

    def test_atlante_confronto_temi_e_ricerca(self):
        name = "Reddito imponibile medio per contribuente"
        province_path = "/indicatore/reddito-imponibile-medio-per-contribuente/mef-reddito-irpef-medio/province"
        regional = self.client.get("/atlante").get_data(as_text=True)
        self.assertIn(name, regional)
        atlas = self.client.get("/atlante?livello=provincia", follow_redirects=True)
        self.assertEqual(atlas.status_code, 200)
        html = atlas.get_data(as_text=True)
        self.assertIn(name, html)
        self.assertIn(province_path, html)
        self.assertIn("Ministero dell&#39;Economia e delle Finanze", html)

        compare = self.client.get("/confronto?indicator=mef:reddito-irpef-medio&livello=provincia",
                                  follow_redirects=True)
        self.assertEqual(compare.status_code, 200)
        self.assertIn(name, compare.get_data(as_text=True))

        by_theme = indicator_view.province_indicators_by_theme()
        theme_path = next(path for path, items in by_theme.items()
                          if any(item["path"] == province_path for item in items))
        theme = self.client.get(theme_path)
        self.assertEqual(theme.status_code, 200)
        self.assertIn(province_path, theme.get_data(as_text=True))

        search = self.client.get("/ricerca?q=reddito+imponibile+medio").get_data(as_text=True)
        self.assertIn("mef-reddito-irpef-medio", search)

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
