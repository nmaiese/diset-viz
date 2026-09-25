"""L'atlante della 1.0 (`/atlante`), reso dal server.

Sorveglia cio' che, rompendosi, non fa fallire niente:
- l'elenco perde righe (un tema senza area, un filtro lasciato acceso) e la
  pagina resta un 200;
- la pagina esce dal ripiego della SPA (`app.html`), che e' anche lui un 200;
- un rimando della SPA di prima finisce nella cache e `/atlante` serve la
  risposta data a `/atlante?indicator=910`;
- la pagina ingrassa con seicento righe e nessuno se ne accorge;
- la sparkline si disegna su un gruppo di regioni diverso da quello che la
  riga dichiara.

Nessun numero del catalogo e' scritto qui: le righe si contano contro
`get_atlas_catalog()`, che cambia quando cambia il catalogo.
"""

import gzip
import html as html_lib
import re
import unittest

from app import app, config, indicator_universe, indicator_view, sources
from app.atlas_catalog import get_atlas_catalog
from app.bes_data import bes_level_path
from app.cache import cache
from app.design.pages import atlante as atlas_page

# Il peso massimo della pagina, compressa come la serve il sito.
MAX_GZIP_BYTES = 90 * 1024
ROW = re.compile(r'<tr data-id="([^"]+)"[^>]*>(.*?)</tr>', re.DOTALL)
SPARK = re.compile(r'<svg\b[^>]*\bclass="spark\b[^"]*"[^>]*>.*?</svg>', re.DOTALL)


def visible_text(page):
    page = re.sub(r"<(script|style)\b.*?</\1>", " ", page, flags=re.DOTALL)
    page = re.sub(r"<[^>]+>", " ", page)
    return " ".join(html_lib.unescape(page).split())


class LAtlanteNellaV1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cache.clear()
        response = cls.client.get("/atlante")
        cls.status = response.status_code
        cls.html = response.get_data(as_text=True)
        cls.catalog = get_atlas_catalog()

    def test_e_la_pagina_della_1_0_con_un_solo_h1(self):
        self.assertEqual(self.status, 200)
        self.assertIn('data-v1="atlante"', self.html, "e' uscito il ripiego della SPA")
        self.assertEqual(len(re.findall(r"<h1\b", self.html)), 1)
        self.assertIn("Atlante degli indicatori territoriali italiani", self.html)
        self.assertNotIn("dist/assets/index.js", self.html, "l'atlante non monta piu' il bundle React")

    def test_una_riga_per_ogni_serie_del_catalogo_con_il_link_canonico(self):
        rows = ROW.findall(self.html)
        expected = {str(item["id"]): item["path"] for item in self.catalog["indicators"]}
        self.assertEqual(len(rows), len(expected))
        self.assertEqual({row_id for row_id, _ in rows}, set(expected))
        canonical = {str(r["meta"]["id"]): r["meta"]["canonical_path"] for r in indicator_universe.projection()}
        for row_id, body in rows:
            with self.subTest(row=row_id):
                href = re.search(r'<a href="([^"]+)"', body).group(1)
                self.assertEqual(href, expected[row_id])
                self.assertEqual(href, canonical[row_id])

    def test_il_json_ld_dichiara_solo_cio_che_la_pagina_mostra(self):
        """Ogni voce della lista e' una riga in pagina, e una scheda indicizzabile."""
        import json

        documents = [json.loads(block) for block in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', self.html, re.DOTALL)]
        self.assertIn("BreadcrumbList", [d.get("@type") for d in documents])
        page = next(d for d in documents if d.get("@type") == "CollectionPage")
        hrefs = {re.search(r'<a href="([^"]+)"', body).group(1) for _, body in ROW.findall(self.html)}
        indexable = {r["meta"]["canonical_path"] for r in indicator_universe.projection() if r["meta"]["indexable"]}
        items = page["mainEntity"]["itemListElement"]
        self.assertTrue(items)
        for item in items:
            path = item["url"].removeprefix(config.SITE_URL)
            self.assertIn(path, hrefs)
            self.assertIn(path, indexable)

    def test_nessuna_riga_senza_tema_e_senza_area(self):
        """Il guasto silenzioso di CLAUDE.md: un tema non mappato perde le sue
        righe senza che niente fallisca."""
        blocks = re.findall(r'<div class="atlante-area" data-area="([^"]*)">(.*?)(?=<div class="atlante-area"|<p class="atlante-empty")',
                            self.html, re.DOTALL)
        self.assertEqual(sum(len(ROW.findall(body)) for _, body in blocks), len(self.catalog["indicators"]))
        for area, body in blocks:
            self.assertTrue(area)
            for theme in re.findall(r'<section class="atlante-group" data-theme="([^"]*)"', body):
                self.assertTrue(theme)

    def test_le_parziali_sono_in_elenco_con_l_etichetta(self):
        """All'apertura si vedono tutte le serie: le parziali con l'etichetta di stato."""
        partial = {str(i["id"]) for i in self.catalog["indicators"] if not i["complete"]}
        labelled = {row_id for row_id, body in ROW.findall(self.html) if "Serie parziale" in body}
        self.assertEqual(labelled, partial)
        flagged = set(re.findall(r'<tr data-id="([^"]+)"[^>]*\bdata-p\b', self.html))
        self.assertEqual(flagged, partial)

    def test_il_testo_visibile_segue_le_regole_della_voce(self):
        text = visible_text(self.html)
        for forbidden in ("—", "–", ";", "…", "...", "media nazionale"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)
        self.assertIsNone(re.search(r"\bNone\b|\bnan\b|\bundefined\b", text))

    def test_il_peso_resta_sotto_i_90_kb_compressi(self):
        response = self.client.get("/atlante", headers={"Accept-Encoding": "gzip"})
        body = response.get_data()
        if response.headers.get("Content-Encoding") != "gzip":
            body = gzip.compress(body, 6)
        self.assertLess(len(body), MAX_GZIP_BYTES, f"{len(body)} byte compressi")

    def test_ogni_sparkline_e_nascosta_e_ha_le_cifre_accanto(self):
        found = 0
        for row_id, body in ROW.findall(self.html):
            cell = re.search(r'<td class="trendcell"[^>]*>(.*?)</td>', body, re.DOTALL).group(1)
            svg = SPARK.search(cell)
            if svg is None:
                self.assertIn("Copertura variabile", cell, row_id)
                continue
            found += 1
            self.assertIn('aria-hidden="true"', svg.group(0))
            self.assertNotRegex(svg.group(0), r"#[0-9a-fA-F]{3,8}\b|preserveAspectRatio")
            self.assertRegex(visible_text(cell), r"\d{4}.*\d{4}", "la variazione e i suoi anni in testo")
        self.assertGreater(found, 0)

    def test_la_linea_e_quella_del_pannello_fisso(self):
        """Una riga ha la linea se e solo se il pannello fisso ne ha una, e
        quando il gruppo e' piu' piccolo delle 20 regioni la riga lo dice."""
        records = {str(r["meta"]["id"]): r for r in indicator_universe.projection()}
        rows = dict(ROW.findall(self.html))
        for item in self.catalog["indicators"]:
            row_id = str(item["id"])
            level = next(lv for lv in records[row_id]["levels"] if lv["key"] == "regione")
            panel, body = level["panel"], rows[row_id]
            with self.subTest(row=row_id):
                self.assertEqual(panel is not None, SPARK.search(body) is not None)
                if panel and panel["members"] < panel["total"]:
                    self.assertIn(f"media di {panel['members']} regioni presenti in tutti gli anni", body)
                elif panel:
                    self.assertNotIn("presenti in tutti gli anni", body)
                if panel:
                    self.assertLessEqual(len(panel["points"]), indicator_view.PANEL_MAX_POINTS)

    def test_la_mappa_e_il_modulo_dato_della_scheda(self):
        self.assertIn('id="mappa"', self.html)
        self.assertEqual(self.html.count("data-explore-data"), 1)
        self.assertEqual(len(re.findall(r'data-key="[a-z-]+" data-name="[^"]*" data-value="[^"]*" class="q[1-6]', self.html)), 20)
        family, raw_id = atlas_page.MAP_INDICATOR
        meta = indicator_view.build_indicator_view(family, raw_id)["meta"]
        self.assertIn(f'href="{meta["canonical_path"]}"', self.html)

    def test_il_server_manda_il_page_view_come_atlas(self):
        original = config.GOOGLE_TAG_MANAGER_ID
        try:
            config.GOOGLE_TAG_MANAGER_ID = "GTM-TEST"
            cache.clear()
            html = self.client.get("/atlante").get_data(as_text=True)
        finally:
            config.GOOGLE_TAG_MANAGER_ID = original
            cache.clear()
        self.assertEqual(html.count("event: 'page_view'"), 1)
        self.assertIn('page_type: "atlas"', html)


class LaMappaFissa(unittest.TestCase):
    """L'indicatore della mappa e' una costante: la prova dice che regge ancora."""

    def test_e_l_indicatore_in_evidenza_del_catalogo_e_regge_la_regola(self):
        family, raw_id = atlas_page.MAP_INDICATOR
        catalog = get_atlas_catalog()
        self.assertEqual(sources.internal_id(family, raw_id), str(catalog["featured_indicator_id"]))
        view = indicator_view.build_indicator_view(family, raw_id)
        self.assertTrue(view["meta"]["indexable"])
        # Il verso non si chiede: l'indicatore in evidenza del catalogo, il
        # tasso di turisticita', descrive senza giudicare ("contextual"), e la
        # mappa colora la grandezza, non un giudizio. La regola col verso e'
        # quella della mappa delle province (bes-01SAL001), che arriva dopo.
        level = next(lv for lv in view["levels"] if lv["key"] == "regione")
        self.assertEqual(len(level["observations"]), indicator_view.PANEL_TOTALS["regione"])


class IlPannelloFisso(unittest.TestCase):
    """`indicator_view.fixed_panel`: la regola della media delle sparkline."""

    @staticmethod
    def _level(matrix, key="regione", observations=()):
        return {"key": key, "matrix": matrix, "observations": list(observations)}

    def test_con_il_gruppo_intero_coincide_con_la_media_della_scheda(self):
        checked = 0
        for record in indicator_universe.projection()[:120]:
            view = indicator_view.build_indicator_view(record["family"], record["raw_id"])
            for level in view["levels"]:
                panel = indicator_view.fixed_panel(level)
                if not panel or panel["members"] < panel["total"] or panel["dropped"]:
                    continue
                checked += 1
                means = [(p["year"], round(p["avg"], 9)) for p in level["annual_means"]]
                self.assertEqual(means, [(p["year"], round(p["value"], 9)) for p in panel["points"]])
        self.assertGreater(checked, 10)

    def test_gruppo_fisso_anni_scartati_e_soglia_assoluta(self):
        regions = [f"r{i}" for i in range(20)]
        full = {r: 10.0 for r in regions}
        # 2001: solo 15 regioni, sotto le 16 della soglia: l'anno si scarta.
        # 2003: manca r0, che esce dal gruppo di tutti gli anni.
        matrix = {
            "2000": dict(full), "2001": {r: 99.0 for r in regions[:15]},
            "2002": {**full, "r0": 40.0}, "2003": {r: 12.0 for r in regions[1:]},
        }
        panel = indicator_view.fixed_panel(self._level(matrix))
        self.assertEqual(panel["members"], 19)
        self.assertEqual(panel["dropped"], 1)
        self.assertEqual([p["year"] for p in panel["points"]], [2000, 2002, 2003])
        # r0 non e' nel gruppo: il suo 40 del 2002 non entra nella media.
        self.assertEqual([p["value"] for p in panel["points"]], [10.0, 10.0, 12.0])

    def test_sotto_i_tre_anni_non_c_e_linea(self):
        full = {f"r{i}": 1.0 for i in range(20)}
        self.assertIsNone(indicator_view.fixed_panel(self._level({"2000": full, "2001": full})))
        # Una serie con 15 regioni su 20 in ogni anno non arriva mai alla soglia.
        few = {f"r{i}": 1.0 for i in range(15)}
        self.assertIsNone(indicator_view.fixed_panel(self._level({str(y): few for y in range(2000, 2010)})))


class IRimandiStannoFuoriDallaCache(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_gli_stati_della_spa_di_prima_fanno_301(self):
        catalog = get_atlas_catalog()
        featured = next(i for i in catalog["indicators"] if str(i["id"]) == str(catalog["featured_indicator_id"]))
        one = catalog["indicators"][len(catalog["indicators"]) // 2]
        two_level = next(i for i in catalog["indicators"]
                         if i["catalog_family"] == "bes" and "?livello=" in bes_level_path(i["id"], "provincia"))
        cases = {
            f"/atlante?indicator={one['id']}": one["path"],
            f"/atlante?view=detail&indicator={one['id']}": one["path"],
            "/atlante?view=detail": featured["path"],
            f"/atlante?indicator={two_level['id']}&livello=provincia": bes_level_path(two_level["id"], "provincia"),
            "/atlante?indicator=non-esiste": "/atlante",
            "/atlante?view=regioni&rk=lombardia": "/regione/lombardia",
            "/atlante?view=regioni&rk=atlantide": "/regioni",
            "/atlante?view=regioni": "/regioni",
            "/atlante?view=confronto": "/confronto",
        }
        for path, target in cases.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 301)
                self.assertEqual(response.headers["Location"], target)

    def test_un_rimando_non_finisce_nella_cache_della_pagina(self):
        self.assertEqual(self.client.get("/atlante?indicator=910").status_code, 301)
        response = self.client.get("/atlante")
        self.assertEqual(response.status_code, 200)
        self.assertIn('data-v1="atlante"', response.get_data(as_text=True))
        # e al contrario: la pagina in cache non si serve a chi chiede un rimando
        self.assertEqual(self.client.get("/atlante?indicator=910").status_code, 301)

    def test_i_filtri_non_moltiplicano_la_cache(self):
        """Filtri e ricerca li applica il JavaScript: il server rende la stessa
        pagina per ogni query string, dalla stessa voce di cache."""
        plain = self.client.get("/atlante").get_data()
        filtered = self.client.get("/atlante?theme=Ambiente%20ed%20energia&partial=1&q=rifiuti").get_data()
        self.assertEqual(plain, filtered)

    def test_il_gemello_markdown_viene_prima_di_tutto(self):
        response = self.client.get("/atlante?indicator=910", headers={"Accept": "text/markdown"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("# Atlante degli indicatori territoriali italiani", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
