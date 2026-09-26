"""La striscia che resta: la barra della scheda e la famiglia fra cui si ricompone."""

import html
import json
import re
import unittest

from app import app


class LaStrisciaCheResta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.maschi = cls.client.get("/indicatore/tasso-di-occupazione-maschi/ter-177").get_data(as_text=True)

    def _family(self, page):
        raw = re.search(r'class="lead-figure"[^>]*data-family="([^"]*)"', page)
        self.assertIsNotNone(raw, "la figura d'apertura non dichiara la sua famiglia")
        return json.loads(html.unescape(raw.group(1)))

    def test_la_famiglia_comprende_la_pagina_e_le_sue_sorelle(self):
        family = self._family(self.maschi)
        self.assertEqual(family[0], "/indicatore/tasso-di-occupazione-maschi/ter-177")
        self.assertIn("/indicatore/tasso-di-occupazione-femmine/ter-178", family)
        self.assertTrue(all(p.startswith("/indicatore/") and "?" not in p and "#" not in p for p in family))

    def test_la_barra_ha_un_punto_per_regione_e_la_frase_vuota(self):
        bar = re.search(r'<div class="stripbar" data-stripbar aria-hidden="true">(.*?)</div>\s*</div>', self.maschi, re.S)
        self.assertIsNotNone(bar)
        self.assertEqual(len(re.findall(r'class="strip__dot area--\w+" data-key="', bar.group(1))), 20)
        self.assertIn('data-empty="Tocca un punto per scegliere"', bar.group(1))

    def test_la_ricomposizione_sta_in_testa(self):
        head = self.maschi.split("</head>", 1)[0]
        self.assertIn('addEventListener("pagereveal"', head)
        self.assertIn('viewTransitionName = "dot-"', head)

    def test_una_scheda_senza_sorelle_ha_solo_se_stessa(self):
        page = self.client.get("/indicatore/tasso-di-turisticita/ter-105").get_data(as_text=True)
        self.assertEqual(self._family(page), ["/indicatore/tasso-di-turisticita/ter-105"])


if __name__ == "__main__":
    unittest.main()
