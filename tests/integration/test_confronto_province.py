"""Il confronto fra province (`/confronto?livello=provincia`).

Sorveglia cio' che, rompendosi, non fa fallire niente:
- il livello provinciale offre un indicatore la cui `/province` non passa la
  regola dell'indice, o ne perde uno che la passa: gli indicatori si contano
  dalle funzioni (`indicator_universe.level_pages`), mai da un numero scritto;
- regioni e province finiscono nello stesso confronto;
- il selettore delle province perde il raggruppamento per regione, o i nomi e
  le chiavi delle pagine provincia;
- il riferimento diventa una "media nazionale", o una media che non e' quella
  semplice delle province con il dato;
- la variante provinciale si indicizza, o perde il canonical `/confronto`;
- la pagina servita e l'isola dicono cose diverse sulle province (API,
  territori di partenza, nomi brevi, nomi dei parametri);
- ogni stato si prende una voce di cache, o la pagina nuda del livello no.
"""

import gzip
import json
import re
import unittest
from unittest import mock
from urllib.parse import parse_qs

from werkzeug.datastructures import MultiDict

from app import app, design, indicator_universe, indicator_view, province_profile, sources
from app.atlas_catalog import get_atlas_indicator
from app.cache import cache
from app.design import charts, maps
from app.design.pages import confronto as page
from tests.integration.test_confronto import DATA, ISLAND, MAX_GZIP_BYTES, rows_of
from tests.integration.test_v1_pages import FUGHE, visible_text

NOINDEX = "noindex, follow"
PROV = "/confronto?livello=provincia"


def state_of(html):
    return json.loads(DATA.search(html).group(1))


def chosen(html):
    """Le chiavi delle province in tabella, nell'ordine."""
    return re.findall(r'href="/provincia/([^"]+)"', rows_of(html))


def rule_province_ids():
    """Gli indicatori la cui `/province` passa la regola, dalle funzioni del
    sito e non da un elenco."""
    return {str(p["meta"]["id"]) for p in indicator_universe.level_pages(listed=True)
            if not p["base"] and p["level"]["key"] == "provincia"}


class LaPaginaDelleProvince(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cache.clear()
        cls.response = cls.client.get(PROV)
        cls.html = cls.response.get_data(as_text=True)
        cls.state = page.nude_state("provincia")
        cls.payload = indicator_universe.province_payload(cls.state["indicator"])

    def test_esce_dal_template_della_1_0_sulle_province(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertIn('data-v1="confronto"', self.html)
        self.assertEqual(len(re.findall(r"<h1\b", self.html)), 1)
        self.assertIn("Confronta le province italiane", self.html)
        self.assertEqual(state_of(self.html)["level"], "provincia")

    def test_senza_javascript_e_un_confronto_fra_province_con_i_numeri(self):
        year = self.state["year"]
        now = {r["region_key"]: r["value"] for r in self.payload["series"]
               if r["year"] == year and r["value"] is not None}
        self.assertEqual(chosen(self.html), list(self.state["regions"]))
        self.assertEqual(len(self.state["regions"]), 3)
        rows = rows_of(self.html)
        self.assertEqual(rows.count('<data class="n n--cell"'), 4)
        self.assertEqual(len(re.findall(rf'<span class="n__u">\u2009su {len(now)}</span>', rows)), 3)
        self.assertIn(f"Media semplice delle {len(now)} province", rows)
        self.assertNotIn("/regione/", rows)
        # la mappa e' quella delle province, con i confini regionali sopra
        self.assertIn('class="map map--province"', self.html)
        painted = re.findall(r'<path d="[^"]+" data-key="([^"]+)"[^>]*class="(q[1-6])?( is-on)?', self.html)
        self.assertEqual({k for k, _, _ in painted}, set(maps.PROVINCE_PATHS))
        self.assertEqual(len([c for c in painted if c[1]]), len(now))
        self.assertEqual(sorted(k for k, _, on in painted if on), sorted(self.state["regions"]))
        self.assertIn('<g class="map__borders">', self.html)
        # la serie: tre linee e la media, due tagli
        chart = re.search(r'<div class="chart" data-cmp-chart>(.*?)</div>\s*<p', self.html, re.S).group(1)
        self.assertEqual(chart.count('<svg viewBox="0 0 '), 2)
        for cls in page.SERIES_CLASSES:
            self.assertEqual(chart.count(f'class="cmpchart__line {cls}"'), 2)
        self.assertNotRegex(chart, r"#[0-9a-fA-F]{3,8}\b|rgba?\(")

    def test_la_media_semplice_delle_province(self):
        year = self.state["year"]
        values = [r["value"] for r in self.payload["series"] if r["year"] == year and r["value"] is not None]
        mean = sum(values) / len(values)
        rows = rows_of(self.html)
        ref = re.search(r'<tr class="ref"><th scope="row">Media semplice delle (\d+) province</th>'
                        r'<td class="val"><data class="n n--cell" value="([^"]+)"', rows)
        self.assertIsNotNone(ref)
        self.assertEqual(int(ref.group(1)), len(values))
        self.assertAlmostEqual(float(ref.group(2)), float(f"{mean:.6g}"), places=6)
        answer = re.search(r"<p data-cmp-answer>(.*?)</p>", self.html).group(1)
        self.assertIn(f"contro una media semplice delle {len(values)} province di", answer)
        # la media si disegna con la regola del pannello del livello provinciale
        self.assertEqual(state_of(self.html)["need"], indicator_view.panel_need("provincia"))
        self.assertIn(f"almeno {indicator_view.panel_need('provincia')} province hanno il dato", self.html)

    def test_il_selettore_delle_province_e_per_regione(self):
        form = re.search(r'<form class="toolbar confronto-form"[^>]*>(.*?)</form>', self.html, re.S).group(1)
        self.assertIn('name="livello" value="provincia"', form)
        selects = re.findall(r'<select id="cmp-region-\d" name="provincia" data-cmp-region>(.*?)</select>', form, re.S)
        self.assertEqual(len(selects), page.MAX_TERRITORIES)
        self.assertNotIn('name="region"', form)
        have = {r["region_key"] for r in self.payload["series"] if r["value"] is not None}
        expected = [(g["label"], [e["key"] for e in g["entries"]]) for g in page.province_groups(
            {k: k for k in have})]
        by_region = province_profile.by_region()
        names = {p["key"]: p["name"] for provinces in by_region.values() for p in provinces}
        for body in selects:
            groups = re.findall(r'<optgroup label="([^"]+)">(.*?)</optgroup>', body, re.S)
            got = [(label.replace("&#39;", "'"), re.findall(r'<option value="([^"]+)"', inner))
                   for label, inner in groups]
            self.assertEqual(got, expected)
            # ogni provincia sta nel gruppo della sua regione, col nome della sua pagina
            for region_key, (label, keys) in zip([k for k in by_region if any(
                    p["key"] in have for p in by_region[k])], got):
                self.assertEqual(set(keys), {p["key"] for p in by_region[region_key] if p["key"] in have})
            for key, name in re.findall(r'<option value="([^"]+)"(?: selected)?>([^<]+)</option>', body):
                if key:
                    self.assertEqual(name.replace("&#39;", "'"), names[key])
        # tutte le province misurate, quando l'indicatore le ha tutte
        self.assertEqual(sum(len(k) for _, k in expected), len(have))
        self.assertEqual(len(have & set(names)), len(have))

    def test_ogni_provincia_linka_la_sua_pagina(self):
        for key in chosen(self.html):
            with self.subTest(key=key):
                self.assertEqual(self.client.get(f"/provincia/{key}").status_code, 200)

    def test_robots_e_canonical(self):
        self.assertEqual(self.response.headers["X-Robots-Tag"], NOINDEX)
        self.assertIn('<meta name="robots" content="noindex, follow">', self.html)
        self.assertIn('<link rel="canonical" href="https://divarioitalia.it/confronto">', self.html)
        other = self.client.get(PROV + "&indicator=bes:12SER020&provincia=lecce")
        html = other.get_data(as_text=True)
        self.assertEqual(other.headers["X-Robots-Tag"], NOINDEX)
        self.assertIn('<meta name="robots" content="noindex, follow">', html)
        self.assertIn('<link rel="canonical" href="https://divarioitalia.it/confronto">', html)
        # le regioni restano indicizzabili, anche con un livello sconosciuto
        for path in ("/confronto", "/confronto?livello=luna"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertTrue(response.headers["X-Robots-Tag"].startswith("index, follow"))
                self.assertNotIn('<meta name="robots" content="noindex', response.get_data(as_text=True))

    def test_il_testo_visibile_segue_le_regole_della_voce(self):
        for path in (PROV, PROV + "&indicator=bes:12SER020&provincia=lecce&provincia=bolzano&year=2022"):
            text = visible_text(self.client.get(path).get_data(as_text=True))
            for forbidden in ("—", "–", ";", "…", "...", "media nazionale", "Media nazionale"):
                with self.subTest(path=path, forbidden=forbidden):
                    self.assertNotIn(forbidden, text)
            self.assertIsNone(FUGHE.search(text))

    def test_il_peso_resta_sotto_il_tetto_del_confronto(self):
        body = gzip.compress(self.html.encode("utf-8"), 6)
        self.assertLess(len(body), MAX_GZIP_BYTES, f"{len(body)} byte compressi")


class GliIndicatoriDelleProvince(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_solo_le_schede_con_la_province_che_passa_la_regola(self):
        expected = rule_province_ids()
        self.assertTrue(expected)
        self.assertEqual(page.province_ids(), expected)
        html = self.client.get(PROV).get_data(as_text=True)
        select = re.search(r'<select id="cmp-indicator".*?</select>', html, re.S).group(0)
        offered = re.findall(r'<option value="([^"]+)"', select)
        self.assertEqual(sorted(offered), sorted(expected))
        # ogni offerta passa la regola del suo livello, a conti fatti
        for record in indicator_universe.projection():
            if str(record["meta"]["id"]) in expected:
                self.assertTrue(indicator_view.level_passes_rule(record["meta"], "provincia", record["levels"][0]["key"]))

    def test_un_indicatore_che_non_regge_torna_a_quello_di_partenza(self):
        plain = state_of(self.client.get(PROV).get_data(as_text=True))
        outside = [r for r in indicator_universe.projection()
                   if r["family"] == "bes" and [lv["key"] for lv in r["levels"]] == ["regione", "provincia"]
                   and str(r["meta"]["id"]) not in rule_province_ids()]
        only_province = [r for r in indicator_universe.projection()
                         if [lv["key"] for lv in r["levels"]] == ["provincia"]]
        wanted = ["105", "non-esiste"]
        if outside:
            wanted.append(str(outside[0]["meta"]["id"]))
        if only_province:
            wanted.append(str(only_province[0]["meta"]["id"]))
        for indicator in wanted:
            with self.subTest(indicator=indicator):
                html = self.client.get(f"{PROV}&indicator={indicator}").get_data(as_text=True)
                self.assertEqual(state_of(html), plain)

    def test_mai_regioni_con_province(self):
        plain = state_of(self.client.get(PROV).get_data(as_text=True))
        for path in (PROV + "&region=lombardia&region=lazio", PROV + "&provincia=lombardia",
                     PROV + "&provincia=atlantide&year=1066"):
            with self.subTest(path=path):
                self.assertEqual(state_of(self.client.get(path).get_data(as_text=True)), plain)
        # e sulle regioni le province non entrano
        regional = state_of(self.client.get("/confronto").get_data(as_text=True))
        self.assertEqual(state_of(self.client.get("/confronto?provincia=lecce&region=lecce").get_data(as_text=True)),
                         regional)

    def test_chiave_e_nome_al_massimo_tre(self):
        html = self.client.get(PROV + "&provincia=Lecce&provincia=bolzano&provincia=lecce"
                                      "&provincia=Trapani&provincia=milano").get_data(as_text=True)
        self.assertEqual(chosen(html), ["lecce", "bolzano", "trapani"])

    def test_la_query_dello_stato_torna_lo_stesso_stato(self):
        self.assertEqual(page.query(page.nude_state("provincia")), "?livello=provincia")
        for args in ({"livello": "provincia", "indicator": "bes:12SER020", "provincia": ["lecce", "bolzano"],
                      "year": "2022"},
                     {"livello": "provincia", "provincia": ["trapani"]}):
            with self.subTest(args=args):
                state = page.resolve_state(MultiDict(args))
                query = page.query(state)
                again = page.resolve_state(MultiDict(parse_qs(query.lstrip("?"))))
                self.assertEqual(again, state)


class IlSelettoreDelLivello(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def _tabs(self, html):
        nav = re.search(r'<nav class="seg confronto-level"[^>]*>(.*?)</nav>', html, re.S).group(1)
        return {key: (href.replace("&amp;", "&"), bool(cur)) for href, key, cur in
                re.findall(r'<a href="([^"]+)" data-cmp-switch="([^"]+)"( aria-current="page")?>', nav)}

    def test_tiene_l_indicatore_se_l_altro_livello_lo_offre(self):
        shared = sorted(page.province_ids() & page.catalog_ids() - {page.default_indicator("provincia"),
                                                                     page.default_indicator("regione")})
        self.assertTrue(shared)
        ind = shared[0]
        tabs = self._tabs(self.client.get(f"/confronto?indicator={ind}").get_data(as_text=True))
        self.assertEqual(tabs["regione"], ("/confronto", True))
        self.assertEqual(tabs["provincia"], (f"/confronto?indicator={ind}&livello=provincia", False))
        tabs = self._tabs(self.client.get(f"{PROV}&indicator={ind}").get_data(as_text=True))
        self.assertEqual(tabs["provincia"], (PROV, True))
        self.assertEqual(tabs["regione"], (f"/confronto?indicator={ind}", False))
        # e ogni link apre l'indicatore sull'altro livello
        state = state_of(self.client.get(f"/confronto?indicator={ind}&livello=provincia").get_data(as_text=True))
        self.assertEqual((state["level"], state["indicator"]), ("provincia", ind))

    def test_senza_l_indicatore_porta_alla_pagina_nuda(self):
        tabs = self._tabs(self.client.get("/confronto").get_data(as_text=True))
        self.assertEqual(tabs["provincia"], (PROV, False))
        not_regional = sorted(page.province_ids() - page.catalog_ids())
        for ind in not_regional[:1]:
            tabs = self._tabs(self.client.get(f"{PROV}&indicator={ind}").get_data(as_text=True))
            self.assertEqual(tabs["regione"], ("/confronto", False))


class LaPaginaELIsolaSulleProvince(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.island = ISLAND.read_text(encoding="utf-8")
        cls.client = app.test_client()

    def test_l_api_da_le_serie_provinciali_della_pagina(self):
        for ind in sorted(page.province_ids())[:4]:
            with self.subTest(indicator=ind):
                response = self.client.get(f"/api/indicator/{ind}?livello=provincia")
                self.assertEqual(response.status_code, 200)
                payload = response.get_json()
                self.assertEqual(payload, json.loads(json.dumps(indicator_universe.province_payload(ind))))
                meta = payload["metadata"]
                for key in ("id", "name", "theme", "path", "source_url", "source_label"):
                    self.assertIn(key, meta)
                self.assertIn("direction", meta["explain"])
                self.assertTrue(meta["path"].endswith("/province"))
                keys = {r["region_key"] for r in payload["series"]}
                self.assertTrue(keys <= set(maps.PROVINCE_PATHS))
                self.assertEqual(payload["series"], sorted(payload["series"], key=lambda r: (r["year"], r["region"])))
                # la pagina scrive gli stessi numeri
                html = self.client.get(f"{PROV}&indicator={ind}").get_data(as_text=True)
                state = state_of(html)
                year = state["year"]
                values = {r["region_key"]: r["value"] for r in payload["series"] if r["year"] == year}
                cells = re.findall(r'<data class="n n--cell" value="([^"]+)"', rows_of(html))[:len(state["regions"])]
                for key, cell in zip(state["regions"], cells):
                    self.assertAlmostEqual(float(cell), float(f"{values[key]:.6g}"))

    def test_l_api_di_prima_non_cambia(self):
        for path in ("/api/indicator/901", "/api/indicator/901?livello=regione"):
            with self.subTest(path=path):
                payload = self.client.get(path).get_json()
                self.assertEqual(payload, json.loads(json.dumps(get_atlas_indicator("901"))))
        self.assertEqual(self.client.get("/api/indicator/901?livello=provincia").status_code, 404)
        self.assertEqual(self.client.get("/api/indicator/bes:01SAL001?livello=luna").status_code, 404)
        self.assertEqual(self.client.get("/api/indicator/non-esiste?livello=provincia").status_code, 404)

    def test_l_isola_sa_dove_leggere_le_province(self):
        self.assertIn('"?livello=" + cfg.level', self.island)
        default = re.search(r"var DEFAULT_PROVINCES = (\[.*?\]);", self.island).group(1)
        self.assertEqual(tuple(json.loads(default)), page.DEFAULT_PROVINCES)
        params = re.search(r"var PARAMS = (\{.*?\});", self.island).group(1)
        self.assertEqual(json.loads(re.sub(r"(\w+):", r'"\1":', params)),
                         {k: v["param"] for k, v in page.LEVELS.items()})
        html = self.client.get(PROV).get_data(as_text=True)
        state = state_of(html)
        self.assertEqual(state["param"], "provincia")
        self.assertEqual(state["profile"], "/provincia/")
        self.assertEqual(state["plural"], "province")
        self.assertEqual(state["default"]["regions"], list(page.nude_state("provincia")["regions"]))
        self.assertEqual(state["default"]["level"], "provincia")
        payload = indicator_universe.province_payload(state["indicator"])
        have = {r["region_key"] for r in payload["series"] if r["value"] is not None}
        self.assertEqual(state["groups"], [[g["label"], [e["key"] for e in g["entries"]]]
                                           for g in page.province_groups({k: k for k in have})])

    def test_gli_stessi_nomi_brevi(self):
        short = re.search(r"var SHORT = (\{.*?\});", self.island, re.S).group(1)
        parsed = dict(re.findall(r'"([^"]+)": "([^"]+)"', short))
        self.assertEqual(parsed, charts.SHORT_NAMES)


class LaCacheSoloSullePagineNude(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_una_voce_per_livello_nudo_e_nessuna_per_gli_altri(self):
        other = PROV + "&indicator=bes:12SER020&provincia=lecce"
        with mock.patch.object(design, "render", wraps=design.render) as render:
            regional = self.client.get("/confronto").get_data()
            self.client.get("/confronto")
            self.assertEqual(render.call_count, 1)
            nude = self.client.get(PROV).get_data()
            self.client.get(PROV)
            self.client.get(PROV + "&provincia=atlantide")
            self.assertEqual(render.call_count, 2)
            first = self.client.get(other).get_data()
            self.client.get(other)
            self.assertEqual(render.call_count, 4)
        self.assertNotEqual(regional, nude)
        self.assertNotEqual(nude, first)


class LaSchedaAlleProvincePortaAlConfronto(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_solo_dalle_province_che_il_confronto_offre(self):
        pages = [p for p in indicator_universe.level_pages(listed=True)
                 if not p["base"] and p["level"]["key"] == "provincia"]
        for entry in pages[:3]:
            with self.subTest(path=entry["path"]):
                html = self.client.get(entry["path"]).get_data(as_text=True)
                target = page.compare_path(entry["meta"], "provincia")
                self.assertIn(f'<a href="{target.replace("&", "&amp;")}">Metti a confronto le province</a>', html)
                state = state_of(self.client.get(target).get_data(as_text=True))
                self.assertEqual((state["level"], state["indicator"]), ("provincia", str(entry["meta"]["id"])))
        # una `/province` che non passa la regola non lo propone
        outside = next((r for r in indicator_universe.projection()
                        if r["family"] == "bes" and [lv["key"] for lv in r["levels"]] == ["regione", "provincia"]
                        and str(r["meta"]["id"]) not in rule_province_ids()), None)
        if outside is not None:
            path = sources.level_path(outside["meta"]["canonical_path"], "provincia", "regione")
            html = self.client.get(path).get_data(as_text=True)
            self.assertNotIn("Metti a confronto le province", html)
        # e la vista regionale resta com'era
        html = self.client.get(pages[0]["meta"]["canonical_path"]).get_data(as_text=True)
        if 'data-v1="indicatore"' in html:
            self.assertNotIn("Metti a confronto le province", html)


if __name__ == "__main__":
    unittest.main()
