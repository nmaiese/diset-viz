"""La striscia che diventa Italia e il tuo territorio: cio' che il server scrive.

Il volo dalla striscia alle tessere e la memoria del territorio li fa v1.js;
qui si guarda che la pagina porti tutto quello che serve, e niente di piu'
senza JavaScript (il comando e il bottone restano nascosti)."""

import re
import unittest

from app import app
from app.data import REGION_GEO_AREA
from app.design import tiles


class LaGriglia(unittest.TestCase):
    def test_venti_caselle_senza_sovrapposizioni(self):
        self.assertEqual(set(tiles.GRID), set(REGION_GEO_AREA))
        self.assertEqual(len(set(tiles.GRID.values())), 20)
        for col, row in tiles.GRID.values():
            self.assertTrue(0 <= col < tiles.COLUMNS and 0 <= row < tiles.ROWS)


class LaScheda(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        client = app.test_client()
        cls.regioni = client.get("/indicatore/tasso-di-turisticita/ter-105").get_data(as_text=True)
        cls.province = client.get("/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001/province").get_data(as_text=True)

    def test_le_tessere_sono_venti_bottoni_con_nome_e_valore(self):
        grid = re.search(r'<div class="tilemap" data-tilemap hidden>(.*?)</div>\s*</div>', self.regioni, re.S)
        self.assertIsNotNone(grid)
        buttons = re.findall(r'<button type="button" class="tile (q[1-6]|is-nd)"[^>]*data-key="([^"]+)" aria-label="([^"]+)"', grid.group(1))
        self.assertEqual(len(buttons), 20)
        self.assertTrue(all("," in label for _, _, label in buttons), "ogni tessera dice nome e valore")

    def test_il_comando_parte_nascosto(self):
        self.assertRegex(self.regioni, r'<div class="seg lead-figure__view"[^>]*data-view-toggle hidden>')

    def test_le_province_non_hanno_la_griglia(self):
        self.assertNotIn("data-tilemap", self.province)

    def test_regione_per_regione_venti_riquadri_sulla_stessa_scala(self):
        items = re.findall(r'<li class="sm__item" data-key="([^"]+)">.*?<svg class="sm__chart" viewBox="0 0 (\d+) (\d+)"', self.regioni, re.S)
        self.assertEqual(len(items), 20)
        self.assertEqual({(w, h) for _, w, h in items}, {("132", "44")})
        self.assertIn("Regione per regione", self.regioni)
        self.assertNotIn('class="sm__item"', self.province)

    def test_la_riga_del_tuo_territorio_c_e_ma_vuota(self):
        for html in (self.regioni, self.province):
            self.assertIn('<p class="mine-note" data-mine-note hidden></p>', html)


class IlProfilo(unittest.TestCase):
    def test_l_anteprima_social_e_quella_del_territorio(self):
        client = app.test_client()
        for path, image in (("/regione/molise", "regione-molise.png"), ("/provincia/lecce", "provincia-lecce.png")):
            with self.subTest(path=path):
                html = client.get(path).get_data(as_text=True)
                self.assertRegex(html, rf'<meta property="og:image" content="https://[^"]+/static/img/og/territori/{image}">')
        self.assertIn("og-divario-italia.png", client.get("/regioni").get_data(as_text=True))

    def test_la_cifra_d_apertura_e_gia_giusta_nell_html(self):
        html = app.test_client().get("/provincia/lecce").get_data(as_text=True)
        self.assertRegex(html, r'<h1 data-count>Lecce è <span class="n n--rank"><data value="\d+">\d+</data>')

    def test_regione_e_provincia_hanno_il_bottone_nascosto(self):
        client = app.test_client()
        regione = client.get("/regione/campania").get_data(as_text=True)
        provincia = client.get("/provincia/lecce").get_data(as_text=True)
        self.assertRegex(regione, r'data-mine-set data-level="regione" data-key="campania" data-name="Campania" aria-pressed="false" hidden>')
        self.assertRegex(provincia, r'data-mine-set data-level="provincia" data-key="lecce" data-name="Lecce" data-region="puglia" data-region-name="Puglia" aria-pressed="false" hidden>')


if __name__ == "__main__":
    unittest.main()
