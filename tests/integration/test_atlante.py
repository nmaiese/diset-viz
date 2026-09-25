"""L'atlante della 1.0 (`/atlante`), reso dal server.

Sorveglia cio' che, rompendosi, non fa fallire niente:
- l'elenco perde righe (un tema senza area, un filtro lasciato acceso) e la
  pagina resta un 200;
- la pagina esce dal ripiego della SPA (`app.html`), che e' anche lui un 200;
- un rimando della SPA di prima finisce nella cache e `/atlante` serve la
  risposta data a `/atlante?indicator=910`;
- la pagina ingrassa con seicento righe e nessuno se ne accorge;
- la sparkline si disegna su un gruppo di regioni diverso da quello che la
  riga dichiara;
- le province (`?livello=provincia`) perdono righe, un'area o il link alla
  loro pagina, o finiscono nella cache o nell'indice al posto delle regioni;
- il modulo che `/api/atlante/modulo` manda ad `atlante.js` smette di essere
  quello della pagina, o una coppia (indicatore, livello) dell'elenco non ha
  il suo.

Nessun numero del catalogo e' scritto qui: le righe si contano contro
`get_atlas_catalog()` e `bes_data.all_bes_indicators()`, che cambiano quando
cambiano i dati.
"""

import gzip
import html as html_lib
import re
import unittest
from unittest import mock

from app import app, config, design, indicator_universe, indicator_view, sources
from app.atlas_catalog import get_atlas_catalog
from app.bes_data import all_bes_indicators, bes_level_path
from app.cache import cache
from app.design.pages import atlante as atlas_page
from app.taxonomy import CATEGORY_NAME_TO_SLUG, MACRO_AREAS, PROVINCE_TWINS

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


class IlBottoneSullaMappa(unittest.TestCase):
    """Il bottone "Sulla mappa" di ogni riga porta quell'indicatore nel modulo dato."""

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cache.clear()
        cls.html = cls.client.get("/atlante").get_data(as_text=True)

    def test_un_bottone_per_ogni_riga_col_dato_delle_regioni(self):
        self.assertIn('<form id="atl-map" action="/atlante#mappa"', self.html)
        rows = ROW.findall(self.html)
        with_n = [body for _, body in rows if re.search(r"<small>\d+ regioni</small>", body)]
        buttons = re.findall(r'<button form="atl-map" name="mappa" value="([^"]+)">Sulla mappa</button>', self.html)
        self.assertEqual(len(buttons), len(with_n))
        for code in buttons:
            self.assertIsNotNone(atlas_page.map_choice(code, "regione"), code)

    def test_la_mappa_scelta_e_quella_della_riga(self):
        catalog = get_atlas_catalog()
        item = next(i for i in catalog["indicators"]
                    if str(i["id"]) != str(catalog["featured_indicator_id"]) and i["catalog_family"] == "bes")
        family, raw_id = sources.split_internal_id(item["id"])
        code = sources.indicator_code(family, raw_id)
        self.assertEqual(atlas_page.map_choice(code, "regione"), (family, raw_id))
        response = self.client.get(f"/atlante?mappa={code}")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn('data-v1="atlante"', page)
        section = page[page.index('id="mappa"'):page.index('id="indicatori"')]
        self.assertIn(f'href="{item["path"]}"', section)
        # la canonica resta l'atlante
        self.assertIn(f'<link rel="canonical" href="{config.SITE_URL}/atlante"', page)


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
        one_code = sources.indicator_code(*sources.split_internal_id(one["id"]))
        two_level = next(i for i in catalog["indicators"]
                         if i["catalog_family"] == "bes" and bes_level_path(i["id"], "provincia") != i["path"])
        cases = {
            f"/atlante?indicator={one['id']}": one["path"],
            f"/atlante?view=detail&indicator={one['id']}": one["path"],
            "/atlante?view=detail": featured["path"],
            f"/atlante?indicator={two_level['id']}&livello=provincia": bes_level_path(two_level["id"], "provincia"),
            "/atlante?indicator=non-esiste": "/atlante",
            # un BES che l'atlante non elenca ha comunque la sua scheda
            "/atlante?indicator=bes:01SAL001": bes_level_path("bes:01SAL001", "regione"),
            "/atlante?indicator=bes:01SAL001&livello=provincia": bes_level_path("bes:01SAL001", "provincia"),
            "/atlante?indicator=bes:ZZZ999": "/atlante",
            "/atlante?view=regioni&rk=lombardia": "/regione/lombardia",
            "/atlante?view=regioni&rk=atlantide": "/regioni",
            "/atlante?view=regioni": "/regioni",
            "/atlante?view=confronto": "/confronto",
            # la vista decide prima dell'indicatore, come in activeView di main.jsx
            "/atlante?view=confronto&indicator=105": "/confronto",
            "/atlante?view=regioni&rk=lombardia&indicator=105": "/regione/lombardia",
            f"/atlante?view=atlas&indicator={one['id']}": f"/atlante?mappa={one_code}#mappa",
            "/atlante?view=atlas&indicator=non-esiste": "/atlante",
            # un `mappa` che non e' una riga dell'elenco torna all'atlante nudo
            "/atlante?mappa=non-esiste": "/atlante",
            "/atlante?mappa=ter-999999999": "/atlante",
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
        pagina per ogni query string, dalla stessa voce di cache. Si contano
        le rese: la seconda richiesta non ne fa una nuova."""
        with mock.patch.object(design, "render", wraps=design.render) as render:
            plain = self.client.get("/atlante").get_data()
            filtered = self.client.get("/atlante?theme=Ambiente%20ed%20energia&partial=1&q=rifiuti").get_data()
            self.assertEqual(render.call_count, 1)
        self.assertEqual(plain, filtered)

    def test_le_altre_mappe_si_rendono_senza_cache(self):
        """Seicento varianti da 600 KB non entrano nella cache del sito: la
        pagina con un'altra mappa si rende ogni volta."""
        other = "/atlante?mappa=bes-10AMB014"
        with mock.patch.object(design, "render", wraps=design.render) as render:
            self.client.get("/atlante")
            self.client.get(other)
            self.client.get(other)
            self.client.get("/atlante")
            self.assertEqual(render.call_count, 3)

    def test_il_gemello_markdown_viene_prima_di_tutto(self):
        response = self.client.get("/atlante?indicator=910", headers={"Accept": "text/markdown"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("# Atlante degli indicatori territoriali italiani", response.get_data(as_text=True))


PROVINCE = "/atlante?livello=provincia"
ALSO = re.compile(r'<a href="([^"]+)">anche per provincia</a>')


def _provincial(record):
    return next((lv for lv in record["levels"] if lv["key"] == "provincia"), None)


class LeProvinceNellAtlante(unittest.TestCase):
    """`/atlante?livello=provincia`: le schede BES con le province, con gli
    stessi componenti delle regioni (selettore, mappa, righe)."""

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cache.clear()
        response = cls.client.get(PROVINCE)
        cls.status = response.status_code
        cls.headers = response.headers
        cls.html = response.get_data(as_text=True)
        # Dalla funzione sorgente, non dal filtro della pagina: se il filtro
        # cambiasse, la prova non deve cambiare con lui.
        cls.items = [item for item in all_bes_indicators() if "provincia" in item["levels"]]
        cls.records = {(r["family"], r["raw_id"]): r for r in indicator_universe.projection()}

    def test_e_la_pagina_della_1_0_sulle_province(self):
        self.assertEqual(self.status, 200)
        self.assertIn('data-v1="atlante"', self.html, "e' uscito il ripiego della SPA")
        self.assertEqual(len(re.findall(r"<h1\b", self.html)), 1)
        self.assertIn("serie provinciali", self.html)

    def test_una_riga_per_ogni_scheda_con_le_province(self):
        """Il numero viene dalla funzione sorgente, mai scritto qui."""
        rows = ROW.findall(self.html)
        expected = {sources.internal_id("bes", item["id"]) for item in self.items}
        self.assertTrue(expected)
        self.assertEqual(len(rows), len(self.items))
        self.assertEqual({row_id for row_id, _ in rows}, expected)
        self.assertEqual(len(rows), atlas_page.rows("provincia")["total"])

    def test_il_link_e_quello_di_bes_level_path(self):
        """La `/province` per le due livelli, la base per le solo provinciali,
        mai un `?livello=` composto a mano."""
        for row_id, body in ROW.findall(self.html):
            with self.subTest(row=row_id):
                href = re.search(r'<a href="([^"]+)"', body).group(1)
                self.assertEqual(href, bes_level_path(row_id, "provincia"))
                self.assertNotIn("livello=", href)

    def test_nessuna_riga_senza_area(self):
        """Le 33 solo provinciali non hanno una `macro_area`: l'area viene dal
        tema. Una riga senza area sparirebbe da ogni filtro."""
        blocks = re.findall(r'<div class="atlante-area" data-area="([^"]*)">(.*?)(?=<div class="atlante-area"|<p class="atlante-empty")',
                            self.html, re.DOTALL)
        self.assertEqual(sum(len(ROW.findall(body)) for _, body in blocks), len(self.items))
        only = {sources.internal_id("bes", i["id"]) for i in self.items if "regione" not in i["levels"]}
        seen = set()
        for area, body in blocks:
            self.assertIn(area, MACRO_AREAS)
            for theme, group in re.findall(r'<section class="atlante-group" data-theme="([^"]*)"(.*?)</section>', body, re.DOTALL):
                slug = CATEGORY_NAME_TO_SLUG[theme]
                self.assertIn(slug, MACRO_AREAS[area], f"{theme} non sta in {area}")
                seen |= {row_id for row_id, _ in ROW.findall(group)}
        self.assertTrue(only)
        self.assertLessEqual(only, seen)

    def test_la_linea_e_quella_del_pannello_fisso_delle_province(self):
        rows = dict(ROW.findall(self.html))
        for item in self.items:
            level = _provincial(self.records[("bes", item["id"])])
            panel, body = level["panel"], rows[sources.internal_id("bes", item["id"])]
            with self.subTest(row=item["id"]):
                self.assertEqual(panel is not None, SPARK.search(body) is not None)
                if panel is None:
                    self.assertIn("Copertura variabile", body)
                elif panel["members"] < panel["total"]:
                    self.assertIn(f"media di {panel['members']} province presenti in tutti gli anni", body)
                else:
                    self.assertNotIn("presenti in tutti gli anni", body)
                self.assertIn(f"<small>{level['territory_count']} province</small>", body)

    def test_i_temi_hanno_slug_e_percorso_delle_regioni(self):
        """A parita' di tema, l'ancora `t-<slug>` e il percorso del tema sono
        gli stessi sui due livelli: lo slug e' quello della categoria."""
        def themes(level_key):
            return {g["name"]: (g["slug"], g["path"])
                    for area in atlas_page.rows(level_key)["areas"] for g in area["groups"]}
        regions, provinces = themes("regione"), themes("provincia")
        shared = set(regions) & set(provinces)
        self.assertTrue(shared)
        for name in shared:
            with self.subTest(tema=name):
                self.assertEqual(provinces[name], regions[name])
        for name, (slug, _) in provinces.items():
            with self.subTest(tema=name):
                self.assertEqual(slug, CATEGORY_NAME_TO_SLUG[name])

    def test_fuori_dall_indice_con_il_canonical_sull_atlante(self):
        self.assertEqual(self.headers.get("X-Robots-Tag"), "noindex, follow")
        self.assertIn('<meta name="robots" content="noindex, follow">', self.html)
        self.assertIn(f'<link rel="canonical" href="{config.SITE_URL}/atlante"', self.html)
        self.assertNotIn('"CollectionPage"', self.html, "la lista la dichiara solo la pagina canonica")
        sitemap = self.client.get("/sitemap.xml").get_data(as_text=True)
        self.assertNotIn("livello=", sitemap)
        self.assertIn(f"<loc>{config.SITE_URL}/atlante</loc>", sitemap)

    def test_il_selettore_e_l_unico_controllo_del_livello(self):
        regional = self.client.get("/atlante").get_data(as_text=True)
        for page, current in ((regional, "/atlante"), (self.html, PROVINCE)):
            nav = re.search(r'<nav class="seg atlante-level"[^>]*>(.*?)</nav>', page, re.DOTALL).group(1)
            links = re.findall(r'<a href="([^"]+)"( aria-current="page")?>', nav)
            self.assertEqual([href.replace("&amp;", "&") for href, _ in links], ["/atlante", PROVINCE])
            self.assertEqual([href.replace("&amp;", "&") for href, cur in links if cur], [current])
        n = re.search(r'href="/atlante\?livello=provincia">Province <span[^>]*>(\d+)</span>', regional).group(1)
        self.assertEqual(int(n), len(self.items))

    def test_la_mappa_porta_alle_province(self):
        section = self.html[self.html.index('id="mappa"'):self.html.index('id="indicatori"')]
        self.assertEqual(section.count("data-explore-data"), 1)
        raw_id = atlas_page.MAP_INDICATOR_PROVINCE[1]
        self.assertIn(f'href="{bes_level_path(raw_id, "provincia")}"', section)
        profiles = re.findall(r'href="(/(?:provincia|regione)/[^"#]+)"', section)
        self.assertTrue(profiles)
        self.assertTrue(all(p.startswith("/provincia/") for p in profiles), profiles[:5])
        # il bottone "Sulla mappa" resta sulle province anche senza JavaScript
        self.assertIn('<input type="hidden" name="livello" value="provincia">', section)

    def test_il_testo_visibile_segue_le_regole_della_voce(self):
        text = visible_text(self.html)
        for forbidden in ("—", "–", ";", "…", "...", "media nazionale"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)
        self.assertIsNone(re.search(r"\bNone\b|\bnan\b|\bundefined\b", text))

    def test_il_peso_resta_sotto_i_90_kb_compressi(self):
        body = self.html.encode()
        self.assertLess(len(gzip.compress(body, 6)), MAX_GZIP_BYTES, f"{len(gzip.compress(body, 6))} byte compressi")

    # Che ogni link della pagina risponda 200 senza rimandi lo guarda
    # tests/integration/test_link_interni.py, che la ha in PAGINE_PER_TIPO.


class AnchePerProvincia(unittest.TestCase):
    """La riga regionale di una misura che ha anche le province porta alla
    loro pagina, dalla scheda stessa o dalla gemella."""

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cache.clear()
        cls.html = cls.client.get("/atlante").get_data(as_text=True)
        cls.rows = dict(ROW.findall(cls.html))

    def test_ter_910_porta_alla_speranza_di_vita_delle_province(self):
        """La riga regionale della speranza di vita e' ter-910: bes-01SAL001
        regionale non e' in elenco, e le sue province si raggiungono da qui."""
        body = self.rows[sources.internal_id("territorial", "910")]
        self.assertEqual(PROVINCE_TWINS["ter-910"], "bes-01SAL001")
        self.assertEqual(ALSO.findall(body), [bes_level_path("01SAL001", "provincia")])
        self.assertTrue(bes_level_path("01SAL001", "provincia").endswith("/province"))
        self.assertNotIn(sources.internal_id("bes", "01SAL001"), self.rows)

    def test_ogni_link_e_quello_della_funzione_e_risponde_200(self):
        records = {str(r["meta"]["id"]): r for r in indicator_universe.projection()}
        found = set()
        for row_id, body in self.rows.items():
            expected = atlas_page.province_path(records[row_id])
            with self.subTest(row=row_id):
                self.assertEqual(ALSO.findall(body), [expected] if expected else [])
            if expected:
                found.add(expected)
        self.assertTrue(found)
        for href in sorted(found):
            with self.subTest(href=href):
                self.assertEqual(self.client.get(href).status_code, 200)

    def test_una_scheda_a_due_livelli_porta_alla_sua_province(self):
        catalog = get_atlas_catalog()
        two = [i for i in catalog["indicators"]
               if i["catalog_family"] == "bes" and bes_level_path(i["id"], "provincia") != i["path"]]
        self.assertTrue(two)
        for item in two:
            with self.subTest(row=item["id"]):
                self.assertEqual(ALSO.findall(self.rows[str(item["id"])]), [bes_level_path(item["id"], "provincia")])


class LaMappaFissaDelleProvince(unittest.TestCase):
    """La costante della mappa delle province: si guarda il livello, non `meta`."""

    def test_regge_la_regola_sul_livello_provinciale(self):
        family, raw_id = atlas_page.MAP_INDICATOR_PROVINCE
        view = indicator_view.build_indicator_view(family, raw_id)
        level = next(lv for lv in view["levels"] if lv["key"] == "provincia")
        self.assertTrue(level["indexable"], "la /province della mappa deve essere indicizzabile")
        self.assertEqual(len(level["observations"]), indicator_view.PANEL_TOTALS["provincia"])
        self.assertEqual(level["year_max"], max(int(y) for y in level["matrix"]))
        info = next(i for i in all_bes_indicators() if i["id"] == raw_id)["levels"]["provincia"]
        self.assertIn(info["direction"], ("higher_better", "lower_better"))
        # e' una riga dell'elenco delle province, con il bottone "Sulla mappa"
        self.assertEqual(atlas_page.map_choice(sources.indicator_code(family, raw_id), "provincia"), (family, raw_id))

    def test_la_mappa_delle_regioni_non_si_sceglie_sulle_province(self):
        self.assertIsNone(atlas_page.map_choice("ter-105", "provincia"))
        self.assertIsNone(atlas_page.map_choice("bes-02IST003P-N22", "regione"))


class LaCacheSuDueLivelli(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _page(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, path)
        return response.get_data(as_text=True)

    def test_i_rimandi_non_finiscono_nella_cache_di_nessun_livello(self):
        self.assertEqual(self.client.get("/atlante?indicator=910").status_code, 301)
        self.assertIn("serie regionali", self._page("/atlante"))
        self.assertIn("serie provinciali", self._page(PROVINCE))
        two_level = next(i for i in get_atlas_catalog()["indicators"]
                         if i["catalog_family"] == "bes" and bes_level_path(i["id"], "provincia") != i["path"])
        response = self.client.get(f"/atlante?indicator={two_level['id']}&livello=provincia")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.headers["Location"], bes_level_path(two_level["id"], "provincia"))
        self.assertIn("serie provinciali", self._page(PROVINCE))
        self.assertIn("serie regionali", self._page("/atlante"))
        self.assertEqual(self.client.get("/atlante?indicator=910").status_code, 301)

    def test_una_voce_per_livello(self):
        with mock.patch.object(design, "render", wraps=design.render) as render:
            regional = self.client.get("/atlante").get_data()
            provincial = self.client.get(PROVINCE).get_data()
            self.client.get("/atlante?theme=Ambiente%20ed%20energia")
            self.client.get(PROVINCE + "&q=rifiuti&area=Territorio%20e%20servizi")
            self.assertEqual(render.call_count, 2)
        self.assertNotEqual(regional, provincial)
        self.assertEqual([c.kwargs["level"] for c in render.call_args_list], ["regione", "provincia"])

    def test_le_altre_mappe_delle_province_si_rendono_senza_cache(self):
        other = PROVINCE + "&mappa=bes-02IST003P-N22"
        with mock.patch.object(design, "render", wraps=design.render) as render:
            self.client.get(PROVINCE)
            page = self._page(other)
            self.client.get(other)
            self.client.get(PROVINCE)
            self.assertEqual(render.call_count, 3)
        self.assertIn("serie provinciali", page)
        # un codice che non e' una riga delle province torna alle province nude
        response = self.client.get(PROVINCE + "&mappa=ter-105")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.headers["Location"], PROVINCE)

    def test_un_livello_sconosciuto_e_l_atlante_delle_regioni(self):
        response = self.client.get("/atlante?livello=comune")
        self.assertEqual(response.status_code, 200)
        self.assertIn("serie regionali", response.get_data(as_text=True))
        self.assertNotIn("noindex", response.headers.get("X-Robots-Tag") or "")

    def test_header_e_meta_dicono_la_stessa_cosa(self):
        """Robots lo decide il livello e nient'altro: il meta sta nel corpo in
        cache, e un header deciso da `?anno=` gli direbbe il contrario."""
        meta = re.compile(r'<meta name="robots" content="([^"]+)"')
        for url, noindex in (("/atlante", False), ("/atlante?anno=2020", False),
                             ("/atlante?regione=Lazio", False), ("/atlante?livello=comune", False),
                             ("/atlante?livello=regione", False), (PROVINCE, True),
                             (PROVINCE + "&anno=2020", True)):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                header = response.headers.get("X-Robots-Tag") or ""
                content = meta.search(response.get_data(as_text=True)).group(1)
                self.assertEqual("noindex" in header, noindex)
                self.assertEqual(content.startswith("noindex"), noindex)


class IlPannelloFissoDelleProvince(unittest.TestCase):
    """La regola del pannello sulle province: 86 su 107, in assoluto."""

    @staticmethod
    def _level(matrix):
        return {"key": "provincia", "matrix": matrix, "observations": []}

    def test_anni_con_copertura_diversa_gruppo_che_cambia_e_buchi(self):
        total = indicator_view.PANEL_TOTALS["provincia"]
        need = indicator_view.panel_need("provincia")
        self.assertEqual(need, 86)
        keys = [f"p{i}" for i in range(total)]
        matrix = {
            "2010": {k: 10.0 for k in keys},
            # 85 province: sotto la soglia, l'anno si scarta
            "2011": {k: 50.0 for k in keys[:need - 1]},
            "2012": {k: 11.0 for k in keys[:need]},
            # 2013 e 2014 non ci sono nella fonte
            "2015": {k: 13.0 for k in keys[5:]},
        }
        panel = indicator_view.fixed_panel(self._level(matrix))
        # il gruppo e' chi c'e' in tutti gli anni tenuti: p5..p85
        self.assertEqual(panel["members"], need - 5)
        self.assertEqual(panel["total"], total)
        self.assertEqual(panel["dropped"], 1)
        self.assertEqual([p["year"] for p in panel["points"]], [2010, 2012, 2015])
        self.assertEqual([p["value"] for p in panel["points"]], [10.0, 11.0, 13.0])
        # l'anno scartato e quelli che mancano nella fonte si uniscono allo
        # stesso modo: una linea sola, un tratto lungo fra 2012 e 2015
        from app.design import charts

        svg = charts.spark(panel["points"], "m", compact=True)
        path = re.search(r'<path class="spark__line" d="([^"]+)"', svg).group(1)
        self.assertEqual(path.count("M"), 1)
        steps = [int(n) for n in re.findall(r"-?\d+", path.split("l", 1)[1])][0::2]
        self.assertEqual(len(steps), 2)
        self.assertGreater(steps[1], steps[0], "il salto di tre anni e' piu' lungo di quello di due")


if __name__ == "__main__":
    unittest.main()


class IlModuloSenzaRicarica(unittest.TestCase):
    """`/api/atlante/modulo`: il modulo "Sulla mappa" per un altro indicatore,
    che `atlante.js` mette al posto di quello in pagina. Le coppie si contano
    dalle righe di ogni livello, mai scritte qui."""

    def setUp(self):
        self.client = app.test_client()
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _codes(self, level):
        return [row["code"] for area in atlas_page.rows(level)["areas"]
                for group in area["groups"] for row in group["rows"] if row["n"]]

    def _query(self, code, level):
        return f"/api/atlante/modulo?indicatore={code}" + ("&livello=provincia" if level == "provincia" else "")

    def test_ogni_coppia_dell_elenco_ha_il_suo_modulo(self):
        for level in ("regione", "provincia"):
            codes = self._codes(level)
            self.assertTrue(codes, level)
            for code in codes:
                with self.subTest(level=level, code=code):
                    response = self.client.get(self._query(code, level))
                    self.assertEqual(response.status_code, 200)
                    data = response.get_json()
                    self.assertEqual(data["code"], code)
                    self.assertIn("data-explore", data["html"])
                    self.assertIn("data-explore-data", data["html"])
                    family, raw_id = sources.parse_indicator_code(code)
                    level_view = atlas_page.map_view((family, raw_id), level)["level"]
                    self.assertEqual(data["href"], level_view["preferred_path"])

    def test_e_lo_stesso_modulo_della_pagina(self):
        code = self._codes("regione")[len(self._codes("regione")) // 2]
        page = self.client.get(f"/atlante?mappa={code}").get_data(as_text=True)
        module = self.client.get(self._query(code, "regione")).get_json()["html"].strip()
        self.assertIn(module, page)

    def test_noindex_e_404(self):
        ok = self.client.get(self._query(self._codes("regione")[0], "regione"))
        self.assertEqual(ok.status_code, 200)
        self.assertIn("noindex", ok.headers["X-Robots-Tag"])
        for path in ("/api/atlante/modulo", "/api/atlante/modulo?indicatore=non-esiste",
                     "/api/atlante/modulo?indicatore=ter-999999999",
                     f"/api/atlante/modulo?indicatore={self._codes('regione')[0]}&livello=comune"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertIn("noindex", response.headers["X-Robots-Tag"])

    def test_non_sta_nell_openapi(self):
        spec = self.client.get("/openapi.json").get_json()
        self.assertFalse([p for p in spec["paths"] if p.startswith("/api/atlante")])
