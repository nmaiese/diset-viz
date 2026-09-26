"""Le mappe in primo piano: la testata della home, le regioni e le province
ingrandite, la mappa accanto all'analisi, la ricerca e l'indice delle province."""

import re
import unittest

from app import app
from app.design import maps


class IlRiquadro(unittest.TestCase):
    def test_il_riquadro_legge_i_tracciati_assoluti_e_relativi(self):
        self.assertEqual(maps.bbox("M0,0L10,5L4,20Z"), (0, 0, 10, 20))
        self.assertEqual(maps.bbox("M10 10l5 0 0 5-5 0z"), (10, 10, 15, 15))
        with self.assertRaises(ValueError):
            maps.bbox("M0 0C1 1 2 2 3 3")

    def test_ogni_tracciato_ha_un_riquadro_dentro_la_mappa(self):
        for level in ("regione", "provincia"):
            for key, d in maps.paths(level).items():
                x0, y0, x1, y1 = maps.bbox(d)
                with self.subTest(territorio=key):
                    self.assertTrue(-20 <= x0 < x1 <= 580 and -20 <= y0 < y1 <= 680)

    def test_lo_zoom_prende_le_province_della_regione(self):
        from app import province_profile

        with app.app_context():
            own = {p["key"] for p in province_profile.by_region()["campania"]}
        self.assertTrue(own <= set(maps.zoom("campania")["provinces"]))


class LePagine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def _get(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, path)
        return response.get_data(as_text=True)

    def test_la_testata_della_home_ha_la_mappa_coi_dati(self):
        html = self._get("/")
        head = html.split('class="doors"', 1)[0]
        self.assertIn("navmap--data", head)
        self.assertGreaterEqual(len(re.findall(r'<use href="#mr-[^"]+" class="q[1-6]"', head)), 20)
        self.assertIn('class="legend"', head)

    def test_regione_e_provincia_hanno_la_regione_ingrandita(self):
        for path, selected in (("/regione/campania", None), ("/provincia/lecce", "lecce")):
            with self.subTest(path=path):
                html = self._get(path)
                self.assertIn('class="regionmap"', html)
                self.assertIn("navmap--zoom", html)
                if selected:
                    self.assertRegex(html, rf'<a href="/provincia/{selected}"[^>]*class="is-on"')

    def test_la_scheda_ha_la_mappa_accanto_all_analisi(self):
        html = self._get("/indicatore/tasso-di-turisticita/ter-105")
        self.assertIn('class="analysis__map"', html)
        self.assertEqual(html.count('class="map-sprite"'), 1)

    def test_ricerca_e_province_hanno_la_mappa_nel_margine(self):
        self.assertRegex(self._get("/ricerca?q=lavoro"), r'class="ricerca-aside[ "]')
        self.assertIn("navmap--data", self._get("/province"))


if __name__ == "__main__":
    unittest.main()
