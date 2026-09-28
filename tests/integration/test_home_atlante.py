"""L'atlante in home: la fascia "Gli indicatori, tema per tema" (`#temi`).

Sorveglia cio' che, rompendosi, non fa fallire niente:
- il bottone dice un numero di indicatori diverso da quello che l'atlante
  mostra all'apertura;
- il conteggio di un'area porta a un atlante che non applica il filtro
  (`atlante.js` accetta `?area=` solo se e' il nome intero di un bottone
  d'area del livello) o che mostra un altro numero di righe;
- l'indicatore "cambiato di piu'" disegna una media diversa da quella della
  scheda quando il gruppo e' intero;
- il gemello Markdown racconta cifre diverse dalla pagina;
- le province prendono la regione "in testa" e "in coda", una classifica che
  il sito non ha;
- un guasto nelle righe dell'atlante manda tutta la home nel ripiego.

Nessuna cifra e' scritta qui: tutto si confronta con `atlante.rows` e con la
scheda (`indicator_view.build_indicator_view`).
"""

import html as html_lib
import os
import re
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from app import app, indicator_view, sources
from app.bes_data import bes_level_path
from app.design.pages import atlante as atlas_page
from app.design.pages import home as home_page
from tests.integration.test_v1_pages import FUGHE, visible_text


def band_html(page):
    start = page.index('id="temi"')
    return page[start:page.index("</section>", start)]


def level_html(band, key):
    start = band.index(f'id="temi-lv-{key}"')
    end = band.find('<div class="home-temi__level"', start + 1)
    return band[start:end if end > 0 else len(band)]


def atlas_area_rows(page, area):
    """Le righe dell'atlante dentro il blocco di un'area."""
    marker = f'<div class="atlante-area" data-area="{html_lib.escape(area)}">'
    start = page.index(marker)
    end = page.find('<div class="atlante-area"', start + 1)
    return len(re.findall(r'<tr data-id="', page[start:end if end > 0 else len(page)]))


class LaFascia(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.page = cls.client.get("/").get_data(as_text=True)
        cls.band = band_html(cls.page)
        with app.app_context():
            cls.data = home_page.atlas_band()

    def test_la_home_e_quella_della_v1(self):
        self.assertIn('data-v1="home"', self.page)
        self.assertIn("Gli indicatori, tema per tema", self.band)

    def test_un_solo_bottone_primario_col_totale_dell_atlante(self):
        buttons = re.findall(r'<a class="btn btn--primary" href="([^"]+)">(.*?)</a>', self.band, re.DOTALL)
        self.assertEqual(len(buttons), 1)
        self.assertEqual(len(re.findall(r"btn--primary", self.band)), 1)
        href, label = buttons[0]
        total = atlas_page.rows("regione")["total"]
        self.assertEqual(href, "/atlante")
        self.assertEqual(visible_text(label), f"Esplora i {sources_count(total)} indicatori nell'atlante")

    def test_ogni_link_d_area_apre_l_atlante_filtrato_con_quel_numero(self):
        checked = 0
        for level in self.data["levels"]:
            block = level_html(self.band, level["key"])
            for area in level["areas"]:
                with self.subTest(livello=level["key"], area=area["area"]):
                    self.assertIn(f'href="{html_lib.escape(area["href"])}"', block)
                    query = parse_qs(urlsplit(area["href"]).query)
                    self.assertEqual(urlsplit(area["href"]).path, "/atlante")
                    self.assertEqual(query["area"], [area["area"]])
                    self.assertEqual(query.get("livello"), None if level["key"] == "regione" else ["provincia"])
                    response = self.client.get(area["href"])
                    self.assertEqual(response.status_code, 200)
                    atlas = response.get_data(as_text=True)
                    # Il valore che atlante.js confronta con i bottoni d'area.
                    self.assertIn(f'data-atlas-area="{html_lib.escape(area["area"])}"', atlas)
                    self.assertIn(f'<a href="{html_lib.escape(atlas_page.LEVEL_PATHS[level["key"]])}" aria-current="page">', atlas)
                    self.assertEqual(atlas_area_rows(atlas, area["area"]), area["count"])
                    checked += 1
        self.assertGreaterEqual(checked, 8)

    def test_i_conteggi_sono_quelli_dell_atlante(self):
        for level in self.data["levels"]:
            self.assertEqual(level["n"], atlas_page.rows(level["key"])["total"])
            self.assertEqual(sum(area["count"] for area in level["areas"]), level["n"])

    def test_ogni_area_ha_il_suo_indicatore_e_la_sua_sparkline(self):
        for level in self.data["levels"]:
            block = level_html(self.band, level["key"])
            for area in level["areas"]:
                with self.subTest(livello=level["key"], area=area["area"]):
                    mover = area["mover"]
                    self.assertIsNotNone(mover)
                    self.assertIn(f'href="{mover["path"]}"', block)
                    self.assertIn(mover["spark"], block)
                    self.assertIn(html_lib.escape(mover["change"]["tail"]), block)

    def test_le_province_non_hanno_testa_e_coda(self):
        self.assertIn("In testa", level_html(self.band, "regione"))
        self.assertNotIn("In testa", level_html(self.band, "provincia"))
        self.assertNotIn("In coda", level_html(self.band, "provincia"))
        self.assertIn(' id="temi-lv-provincia" hidden', self.band)

    def test_i_link_delle_province_portano_alla_vista_provinciale(self):
        for area in self.data["levels"][1]["areas"]:
            mover = area["mover"]
            family, raw_id = sources.parse_indicator_code(mover["code"])
            self.assertEqual(family, "bes")
            self.assertEqual(mover["path"], bes_level_path(raw_id, "provincia"))

    def test_nessun_id_ripetuto_nella_pagina(self):
        ids = re.findall(r'\sid="([^"]+)"', self.page)
        doubles = sorted({i for i in ids if ids.count(i) > 1})
        self.assertEqual(doubles, [])

    def test_il_testo_visibile_rispetta_le_regole(self):
        text = visible_text(self.band)
        for bad in ("—", "–", ";", "…", "media nazionale", "anno per anno"):
            self.assertNotIn(bad, text)
        self.assertIsNone(FUGHE.search(text))
        # La regola della scelta sta scritta nella riga fonte.
        self.assertIn("scarto interquartile", text)
        self.assertNotIn("anno per anno", visible_text(self.page))


def sources_count(value):
    """Come `num(None, 'count')` scrive un conteggio: il punto delle migliaia."""
    return f"{value:,}".replace(",", ".")


class LaScelta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with app.app_context():
            cls.data = home_page.atlas_band()

    def test_col_gruppo_intero_i_valori_sono_quelli_della_scheda(self):
        """Primo e ultimo punto della scelta uguali ad `annual_means` della
        scheda quando il gruppo e' intero e nessun anno e' scartato (i punti di
        mezzo il pannello li puo' diradare, gli estremi mai)."""
        checked = 0
        for level in self.data["levels"]:
            for area in level["areas"]:
                mover = area["mover"]
                if mover["members"] < mover["total"] or mover["dropped"]:
                    continue
                view = indicator_view.build_indicator_view(*sources.parse_indicator_code(mover["code"]))
                card = next(lv for lv in view["levels"] if lv["key"] == level["key"])
                means = card["annual_means"]
                with self.subTest(livello=level["key"], codice=mover["code"]):
                    for point, mean in ((mover["points"][0], means[0]), (mover["points"][-1], means[-1])):
                        self.assertEqual(point["year"], mean["year"])
                        self.assertAlmostEqual(point["value"], mean["avg"], places=9)
                checked += 1
        self.assertGreater(checked, 0)

    def test_la_regola_sceglie_il_piu_cambiato_fra_le_schede_indicizzabili(self):
        def row(ident, name, indexable=True, spark="<svg/>"):
            return {"id": ident, "name": name, "path": f"/{ident}", "code": ident, "indexable": indexable,
                    "spark": spark, "change": {"head": "", "tail": ""}}

        def record(first, last, floor):
            panel = {"points": [{"year": 2000, "value": first}, {"year": 2010, "value": last}],
                     "members": 20, "total": 20, "dropped": 0, "floor": floor}
            return {"levels": [{"key": "regione", "panel": panel}]}

        rows = [row("a", "Alfa"), row("b", "Beta"), row("c", "Gamma", indexable=False),
                row("d", "Delta", spark=""), row("e", "Epsilon")]
        records = {
            "a": record(10, 20, 5),     # 2 scarti
            "b": record(10, 40, 10),    # 3 scarti
            "c": record(0, 100, 1),     # non indicizzabile
            "d": record(0, 100, 1),     # senza sparkline
            "e": record(0, 100, 0),     # scarto nullo: non si confronta
        }
        self.assertEqual(home_page._mover("regione", rows, records)["code"], "b")
        # A pari punteggio vince l'ordine alfabetico.
        records["a"] = record(10, 40, 10)
        self.assertEqual(home_page._mover("regione", rows, records)["code"], "a")
        self.assertIsNone(home_page._mover("regione", [rows[2], rows[3]], records))


class IlGemelloMarkdown(unittest.TestCase):
    def test_le_stesse_cifre_della_pagina(self):
        client = app.test_client()
        text = client.get("/", headers={"Accept": "text/markdown"}).get_data(as_text=True)
        with app.app_context():
            data = home_page.atlas_band()
        self.assertIn(f"Esplora i {data['total']} indicatori nell'atlante", text)
        for level in data["levels"]:
            for area in level["areas"]:
                with self.subTest(livello=level["key"], area=area["area"]):
                    self.assertIn(f"[{area['area']}, {area['count']} indicatori](", text)
                    self.assertIn(area["href"], text)
                    mover = area["mover"]
                    self.assertIn(f"{mover['change']['head']} {mover['change']['tail']}", text)
                    self.assertIn(mover["path"], text)


class UnGuastoNonPortaNelRipiego(unittest.TestCase):
    def test_senza_righe_la_home_resta_della_v1(self):
        env = {k: v for k, v in os.environ.items() if k != "DIVARIO_V1_STRICT"}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(home_page, "atlas_band", side_effect=LookupError("prova")), \
                mock.patch.object(app.logger, "exception"):
            page = app.test_client().get("/").get_data(as_text=True)
        self.assertIn('data-v1="home"', page)
        band = band_html(page)
        self.assertNotIn("btn--primary", band)
        self.assertIn('class="home-area"', band)
        self.assertNotIn("temi-lv-provincia", band)


if __name__ == "__main__":
    unittest.main()
