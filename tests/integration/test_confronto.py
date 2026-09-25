"""Il confronto della 1.0 (`/confronto`), reso dal server.

Sorveglia cio' che, rompendosi, non fa fallire niente:
- la pagina esce da un ripiego invece che dal template della 1.0, o un link
  vecchio (la SPA non scriveva lo stato del confronto nell'URL, ma `?view=`,
  `?indicator=` e `?region=` erano suoi) apre una pagina diversa da quella
  che chiede;
- senza JavaScript la pagina non mostra un confronto con numeri veri;
- la pagina servita e quella che l'isola ridisegna dicono cose diverse: le
  cifre, la frase in testa e la serie hanno una regola sola, scritta due
  volte (Python e `static/js/confronto.js`);
- ogni stato si prende una voce di cache, o la pagina nuda non ce l'ha;
- la pagina ingrassa, o si indicizza una variante;
- la regia cede e la risposta resta un 200.
"""

import gzip
import json
import os
import re
import unittest
from pathlib import Path
from unittest import mock

from app import app, design
from app.atlas_catalog import get_atlas_catalog, get_atlas_indicator
from app.cache import cache
from app.design import charts, numfmt
from app.design.pages import confronto as page
from tests.integration.test_v1_pages import FUGHE, PERCENT_IN_WORDS, visible_text

INDEX_HEADER = "index, follow, max-snippet:-1, max-image-preview:large"
# La pagina nuda pesava 36 KB compressi il 25 settembre 2026: quasi tutto e'
# il selettore con le 597 serie del catalogo e i contorni delle regioni.
MAX_GZIP_BYTES = 45 * 1024
ISLAND = Path(app.root_path) / "static" / "js" / "confronto.js"
DATA = re.compile(r'<script type="application/json" data-cmp-data>(.*?)</script>', re.S)


def rows_of(html):
    return re.search(r"<tbody data-cmp-rows>(.*?)</tbody>", html, re.S).group(1)


def selected(html):
    """Le chiavi delle regioni in tabella, nell'ordine."""
    return re.findall(r'href="/regione/([^"]+)"', rows_of(html))


class IlConfrontoNellaV1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cache.clear()
        cls.response = cls.client.get("/confronto")
        cls.html = cls.response.get_data(as_text=True)

    def test_esce_dal_template_della_1_0(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertIn('data-v1="confronto"', self.html)
        self.assertEqual(len(re.findall(r"<h1\b", self.html)), 1)
        self.assertNotIn("dist/assets/index.", self.html)
        self.assertIn("js/confronto.js", self.html)
        self.assertIn("css/ds/pages/confronto.css", self.html)

    def test_senza_javascript_e_un_confronto_con_i_numeri(self):
        """La tabella ha tre regioni con valore, unita' e posizione, la media
        semplice come riferimento, la mappa dipinta e la serie disegnata."""
        state = page.resolve_state({})
        self.assertEqual(selected(self.html), list(state["regions"]))
        self.assertEqual(len(state["regions"]), 3)
        rows = rows_of(self.html)
        self.assertEqual(rows.count('<data class="n n--cell"'), 4)
        self.assertEqual(len(re.findall(r'<span class="n__u"> su 20</span>', rows)), 3)
        self.assertIn("Media semplice delle 20 regioni", rows)
        # la frase in testa porta le stesse cifre
        answer = re.search(r"<p data-cmp-answer>(.*?)</p>", self.html).group(1)
        for value in re.findall(r'<data class="n n--cell" value="[^"]+">([^<]+)<', rows):
            self.assertIn(value, answer)
        # la mappa ha le venti regioni sulla rampa, e le tre scelte contornate
        classes = re.findall(r'<path d="[^"]+" data-key="([^"]+)"[^>]*class="(q[1-6])?( is-on)?"', self.html)
        self.assertEqual(len([c for c in classes if c[1]]), 20)
        self.assertEqual(sorted(k for k, _, on in classes if on), sorted(state["regions"]))
        # la serie: tre linee, la media tratteggiata, due tagli
        chart = re.search(r'<div class="chart" data-cmp-chart>(.*?)</div>\s*<p', self.html, re.S).group(1)
        self.assertEqual(chart.count('<svg viewBox="0 0 '), 2)
        for cls in page.SERIES_CLASSES:
            self.assertEqual(chart.count(f'class="cmpchart__line {cls}"'), 2)
        self.assertEqual(chart.count('class="band__avg"'), 2)
        self.assertNotRegex(chart, r"#[0-9a-fA-F]{3,8}\b|rgba?\(")

    def test_il_form_funziona_senza_javascript(self):
        form = re.search(r'<form class="toolbar confronto-form"[^>]*>(.*?)</form>', self.html, re.S)
        self.assertIsNotNone(form)
        self.assertIn('action="/confronto" method="get"', self.html)
        body = form.group(1)
        self.assertEqual(len(re.findall(r'<select id="cmp-region-\d" name="region"', body)), page.MAX_TERRITORIES)
        self.assertIn('name="indicator"', body)
        self.assertIn('name="year"', body)
        self.assertIn('name="livello" value="regione"', body)
        self.assertIn('type="submit"', body)
        # il selettore ha tutte le serie del catalogo regionale, una volta
        options = re.findall(r'<option value="([^"]+)"(?: data-u="[^"]*")?(?: selected)?>', re.search(
            r'<select id="cmp-indicator".*?</select>', body, re.S).group(0))
        self.assertEqual(sorted(options), sorted(str(i["id"]) for i in get_atlas_catalog()["indicators"]))

    def test_canonical_e_robots_come_prima(self):
        self.assertIn('<link rel="canonical" href="https://divarioitalia.it/confronto">', self.html)
        self.assertEqual(self.response.headers["X-Robots-Tag"], INDEX_HEADER)
        for path in ("/confronto?indicator=ter-901&region=sicilia", "/confronto?view=confronto"):
            with self.subTest(path=path):
                response = self.client.get(path)
                html = response.get_data(as_text=True)
                self.assertEqual(response.headers["X-Robots-Tag"], INDEX_HEADER)
                self.assertIn('<link rel="canonical" href="https://divarioitalia.it/confronto">', html)
                self.assertIn('property="og:url" content="https://divarioitalia.it/confronto"', html)

    def test_il_testo_visibile_segue_le_regole_della_voce(self):
        for path in ("/confronto", "/confronto?indicator=ter-901&region=sicilia&region=veneto&year=2010"):
            text = visible_text(self.client.get(path).get_data(as_text=True))
            for forbidden in ("—", "–", ";", "…", "...", "media nazionale", "Media nazionale"):
                with self.subTest(path=path, forbidden=forbidden):
                    self.assertNotIn(forbidden, text)
            self.assertIsNone(FUGHE.search(text))

    def test_il_peso_resta_sotto_i_45_kb_compressi(self):
        body = gzip.compress(self.html.encode("utf-8"), 6)
        self.assertLess(len(body), MAX_GZIP_BYTES, f"{len(body)} byte compressi")


class GliIndirizziDiPrima(unittest.TestCase):
    """Lo stato nell'URL, con i nomi della SPA, e ogni valore sbagliato che
    torna al confronto di partenza invece di un errore."""

    def setUp(self):
        self.client = app.test_client()

    def _page(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, path)
        html = response.get_data(as_text=True)
        self.assertIn('data-v1="confronto"', html, path)
        return html

    def _state(self, html):
        return json.loads(DATA.search(html).group(1))

    def test_i_link_della_spa_aprono_la_pagina_di_partenza(self):
        plain = self._state(self._page("/confronto"))
        for path in ("/confronto?view=confronto", "/confronto?view=confronto&from=atlas",
                     "/confronto?indicator=non-esiste&region=atlantide&year=1066", "/confronto?livello=luna"):
            with self.subTest(path=path):
                self.assertEqual(self._state(self._page(path)), plain)

    def test_id_codice_nome_e_chiave_dicono_la_stessa_cosa(self):
        forms = (
            "/confronto?indicator=901&region=sicilia&region=veneto&year=2010",
            "/confronto?indicator=ter-901&region=Sicilia&region=Veneto&year=2010",
            "/confronto?indicatore=ter-901&regione=sicilia&regione=veneto&anno=2010",
            "/confronto?indicator=901&region=sicilia&region=Sicilia&region=veneto&year=2010",
        )
        pages = [self._page(path) for path in forms]
        states = [self._state(html) for html in pages]
        for path, state in zip(forms, states):
            with self.subTest(path=path):
                self.assertEqual(state["indicator"], "901")
                self.assertEqual(state["regions"], ["sicilia", "veneto"])
                self.assertEqual(state["year"], 2010)
        self.assertEqual(selected(pages[0]), ["sicilia", "veneto"])
        self.assertIn("PIL pro capite, 2010: Sicilia", pages[0])

    def test_le_famiglie_del_catalogo(self):
        for indicator in ("bes:10AMB014", "bes-10AMB014", "multiscopo:MULTI_ZONA_RUMORI"):
            with self.subTest(indicator=indicator):
                state = self._state(self._page(f"/confronto?indicator={indicator}"))
                self.assertEqual(state["indicator"], indicator.replace("bes-", "bes:"))

    def test_al_massimo_tre_regioni(self):
        html = self._page("/confronto?region=piemonte&region=lazio&region=puglia&region=sardegna")
        self.assertEqual(selected(html), ["piemonte", "lazio", "puglia"])

    def test_la_query_dello_stato_torna_lo_stesso_stato(self):
        """`query` scrive l'URL che scrive anche l'isola: rileggerlo da' lo
        stesso stato, e la pagina nuda non ha query."""
        from urllib.parse import parse_qs
        from werkzeug.datastructures import MultiDict

        self.assertEqual(page.query(page.resolve_state({})), "")
        for args in ({"indicator": "901", "region": ["sicilia", "veneto"], "year": "2010"},
                     {"indicator": "bes:10AMB014"},
                     {"region": ["lazio"]}):
            with self.subTest(args=args):
                state = page.resolve_state(MultiDict(args))
                query = page.query(state)
                again = page.resolve_state(MultiDict(parse_qs(query.lstrip("?"))))
                self.assertEqual(again, state)
                self.assertEqual(self._state(self._page("/confronto" + query))["regions"], list(state["regions"]))


class LaCacheSoloSullaPaginaNuda(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_la_pagina_nuda_in_cache_gli_altri_confronti_no(self):
        other = "/confronto?indicator=ter-901&region=sicilia"
        with mock.patch.object(design, "render", wraps=design.render) as render:
            plain = self.client.get("/confronto").get_data()
            self.client.get("/confronto")
            self.client.get("/confronto?view=confronto")
            self.assertEqual(render.call_count, 1)
            first = self.client.get(other).get_data()
            self.client.get(other)
            self.assertEqual(render.call_count, 3)
        self.assertNotEqual(plain, first)


class LaPaginaELIsolaDiconoLaStessaCosa(unittest.TestCase):
    """Le regole scritte due volte: in Python per la pagina servita, in
    `confronto.js` per quella ridisegnata. Qui si guarda che i numeri che le
    reggono siano gli stessi, e che l'API dia all'isola cio' che le serve."""

    @classmethod
    def setUpClass(cls):
        cls.island = ISLAND.read_text(encoding="utf-8")

    def test_gli_stessi_tagli_della_serie(self):
        cuts = re.search(r"var CUTS = (\[.*?\]);", self.island).group(1)
        parsed = json.loads(cuts)
        self.assertEqual([tuple(c) for c in parsed], [tuple(c) for c in charts.COMPARE_CUTS])

    def test_le_stesse_regioni_di_partenza_e_lo_stesso_tetto(self):
        default = re.search(r"var DEFAULT_REGIONS = (\[.*?\]);", self.island).group(1)
        self.assertEqual(tuple(json.loads(default)), page.DEFAULT_REGIONS)
        html = app.test_client().get("/confronto").get_data(as_text=True)
        state = json.loads(DATA.search(html).group(1))
        self.assertEqual(state["max"], page.MAX_TERRITORIES)
        self.assertEqual(state["classes"], list(page.SERIES_CLASSES))
        self.assertEqual(state["default"]["regions"], list(page.resolve_state({})["regions"]))

    def test_la_frase_ha_la_stessa_forma(self):
        """Il "%" attaccato a ogni cifra, le altre unita' una volta sola."""
        pct = page.answer_text("Aree protette", 2022, [("Lombardia", 16.1), ("Lazio", 27.9)], 23.2, 20,
                               "regioni", "%", 1)
        self.assertEqual(pct, "Aree protette, 2022: Lombardia 16,1% e Lazio 27,9%, "
                              "contro una media semplice delle 20 regioni di 23,2%.")
        euro = page.answer_text("PIL pro capite", 2010, [("Sicilia", 17290.4), ("Lazio", None), ("Veneto", 29545)],
                                26109, 20, "regioni", "euro", 0)
        self.assertEqual(euro, "PIL pro capite, 2010: Sicilia 17.290 e Veneto 29.545 euro, "
                               "contro una media semplice delle 20 regioni di 26.109 euro.")
        for piece in ('unit === "%" || last', '" e "', '", contro una media semplice delle "'):
            self.assertIn(piece, self.island)

    def test_l_api_da_all_isola_cio_che_le_serve(self):
        response = app.test_client().get("/api/indicator/901")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        meta = payload["metadata"]
        for key in ("id", "name", "theme", "path", "source_url", "source_label"):
            self.assertIn(key, meta)
        self.assertIn("direction", meta["explain"])
        self.assertTrue({"region", "region_key", "year", "value"} <= set(payload["series"][0]))

    def test_l_unita_dell_isola_e_quella_della_pagina(self):
        """L'API da' l'etichetta della fonte ("Valori percentuali"): l'unita'
        come si scrive accanto a una cifra l'isola la legge da `data-u`."""
        html = app.test_client().get("/confronto").get_data(as_text=True)
        for item in get_atlas_catalog()["indicators"][:60]:
            unit = numfmt.phrase_unit(item.get("unit"))
            tag = re.search(rf'<option value="{re.escape(str(item["id"]))}"([^>]*)>', html).group(1)
            with self.subTest(indicator=item["id"]):
                if unit:
                    self.assertIn(f'data-u="{unit}"', tag.replace("&#39;", "'"))
                else:
                    self.assertNotIn("data-u", tag)

    def test_i_confronti_salvati_restano_leggibili(self):
        """La SPA salvava `{indId, regionNames, year}`: l'isola scrive gli
        stessi nomi, e ricarica anche quelli di allora."""
        for piece in ("indId:", "regionNames:", "c.indId", "c.regionNames", "window.diAuth",
                      '"/api/comparisons"', 'method: "DELETE"'):
            self.assertIn(piece, self.island)


class OgniIndicatoreSiConfronta(unittest.TestCase):
    """Un campione del catalogo, di ogni famiglia: ogni confronto esce dal
    template della 1.0, senza `None`, con un `<h1>` solo e il "%" scritto
    come "%"."""

    def test_un_campione_del_catalogo(self):
        client = app.test_client()
        items = get_atlas_catalog()["indicators"]
        by_family = {}
        for item in items:
            by_family.setdefault(item["catalog_family"], []).append(item)
        sample = [item for family in by_family.values() for item in family[::max(1, len(family) // 6)]]
        self.assertGreater(len(sample), 20)
        for item in sample:
            path = f"/confronto?indicator={item['id']}"
            with self.subTest(path=path):
                response = client.get(path)
                html = response.get_data(as_text=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn('data-v1="confronto"', html)
                self.assertEqual(json.loads(DATA.search(html).group(1))["indicator"], str(item["id"]))
                self.assertIsNone(FUGHE.search(visible_text(html)))
                self.assertIsNone(PERCENT_IN_WORDS.search(html))
                self.assertEqual(len(re.findall(r"<h1\b", html)), 1)
                payload = get_atlas_indicator(item["id"])
                years = sorted({r["year"] for r in payload["series"] if r["value"] is not None})
                self.assertIn(f"<option selected>{years[-1]}</option>", html)


class SenzaRipiego(unittest.TestCase):
    """Il ripiego dell'atlante e del confronto era la SPA, che se n'e' andata.
    Se la regia cede, la risposta e' un 500 onesto, non un 200 senza dati."""

    def test_se_la_regia_cede_la_risposta_e_un_500(self):
        import logging

        def cede(*_args, **_kwargs):
            raise RuntimeError("la regia della 1.0 cede")

        client = app.test_client()
        livello = app.logger.level
        app.logger.setLevel(logging.CRITICAL)
        propagate = app.config.get("PROPAGATE_EXCEPTIONS")
        app.config["PROPAGATE_EXCEPTIONS"] = False
        cache.clear()
        try:
            with mock.patch.dict(os.environ, {"DIVARIO_V1_STRICT": ""}), \
                    mock.patch("app.design.derive", side_effect=cede):
                for path in ("/confronto", "/confronto?indicator=ter-901", "/atlante", "/atlante?livello=provincia"):
                    with self.subTest(path=path):
                        self.assertEqual(client.get(path).status_code, 500)
        finally:
            app.config["PROPAGATE_EXCEPTIONS"] = propagate
            app.logger.setLevel(livello)
            cache.clear()


if __name__ == "__main__":
    unittest.main()
