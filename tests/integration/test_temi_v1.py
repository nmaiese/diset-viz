"""/temi e /tema/<slug> sono pagine della 1.0 (`data-v1="temi"`, `data-v1="tema"`).

Ogni tema, non un campione: due temi non hanno la classifica e la pagina deve
reggere anche li'. La modalita' stretta (`DIVARIO_V1_STRICT`, da
tests/conftest.py) fa uscire l'eccezione invece del ripiego sui template di
prima, quindi un guasto qui ha il suo traceback.
"""

import re
import unittest
from pathlib import Path

from app import app, atlas_catalog, views
from tests.integration.test_v1_pages import FUGHE, PERCENT_IN_WORDS, spark_faults, visible_text

CSS = Path(__file__).resolve().parents[2] / "app" / "static" / "css" / "ds" / "pages"
FORBIDDEN = ("—", "–", ";", "…")


class LePagineDeiTemiSonoDellaV1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()
        cls.temi = cls.client.get("/temi").get_data(as_text=True)
        with app.app_context():
            cls.voci = atlas_catalog.all_atlas_themes_index()
        cls.pagine = {v["path"]: cls.client.get(v["path"]).get_data(as_text=True) for v in cls.voci}

    def _sane(self, html, pagina):
        self.assertIn(f'data-v1="{pagina}"', html, "non e' il template della 1.0")
        self.assertEqual(len(re.findall(r"<h1\b", html)), 1)
        testo = visible_text(html)
        self.assertIsNone(FUGHE.search(testo))
        self.assertIsNone(PERCENT_IN_WORDS.search(html))
        for vietato in FORBIDDEN:
            self.assertNotIn(vietato, testo, f"tipografia vietata: {vietato!r}")
        self.assertIn("css/ds/components.css", html)
        self.assertNotIn("css/ds/theme.css", html)

    def test_l_indice_e_della_v1(self):
        self._sane(self.temi, "temi")

    def test_ogni_tema_e_della_v1(self):
        viste = 0
        for percorso, html in self.pagine.items():
            with self.subTest(tema=percorso):
                self._sane(html, "tema")
                found, faults = spark_faults(html)
                viste += found
                self.assertEqual(faults, [])
        self.assertGreater(viste, 0, "nessuna sparkline nei temi: la prova non guarda niente")

    def test_le_ancore_delle_aree_restano(self):
        """La home e la briciola della pagina tema portano a `/temi#area-<slug>`."""
        with app.test_request_context():
            for area in views._themes_index_areas():
                with self.subTest(area=area["area"]):
                    self.assertIn(f'id="{views._area_anchor(area["area"]).split("#")[1]}"', self.temi)

    def test_gli_esempi_sono_quelli_da_cui_parte_il_tema_e_sono_link_veri(self):
        """Erano i primi cinque in ordine alfabetico, dentro un `<a>` che
        prendeva tutta la scheda."""
        self.assertNotIn('class="theme-index-card"', self.temi)
        with app.test_request_context():
            areas = views._themes_index_areas()
        for area in areas:
            for tema in area["themes"]:
                profilo = atlas_catalog.get_atlas_theme_profile(tema["path"].rsplit("/", 1)[-1])
                attesi = [i["path"] for i in views._theme_featured(profilo)][:3]
                scheda = re.search(r'<li class="temi-card" data-temi-theme="[^"]*">\s*<h3 class="temi-card__title">'
                                   rf'<a href="{re.escape(tema["path"])}">.*?</li>\s*(?=<li class="temi-card"|</ul>\s*</section>)',
                                   self.temi, re.S)
                with self.subTest(tema=tema["theme"]):
                    self.assertIsNotNone(scheda)
                    esempi = re.findall(r'<ul class="temi-card__examples"[^>]*>(.*?)</ul>', scheda.group(0), re.S)
                    self.assertEqual(re.findall(r'<li><a href="([^"#]+)">', esempi[0]), attesi)

    def test_testa_e_coda_le_dicono_le_frecce_e_portano_al_profilo(self):
        self.assertNotIn("dot--lead", self.temi)
        self.assertNotIn("dot--lag", self.temi)
        estremi = re.findall(r'<dl class="temi-card__ends">(.*?)</dl>', self.temi, re.S)
        self.assertGreaterEqual(len(estremi), 10)
        for blocco in estremi:
            self.assertIn("In testa", blocco)
            self.assertIn("In coda", blocco)
            self.assertEqual(len(re.findall(r'href="/regione/[^"]+"', blocco)), 2)
            self.assertEqual(blocco.count("<svg"), 2)

    def test_la_classifica_e_una_tabella_che_diventa_blocchi(self):
        html = self.pagine["/tema/lavoro-e-conciliazione"]
        self.assertIn('class="table table--rank"', html)
        self.assertIn('class="tablewrap rankwrap"', html)
        # La nota del metodo sta sotto il titolo della sezione, prima della tabella.
        sezione = html[html.index('id="classifica"'):]
        self.assertLess(sezione.index("Non è una classifica ufficiale"), sezione.index("table--rank"))

    def test_l_elenco_di_tutti_ha_un_filtro_che_senza_javascript_non_si_vede(self):
        html = self.pagine["/tema/lavoro-e-conciliazione"]
        self.assertRegex(html, r"<form[^>]*data-tema-filter[^>]*hidden")
        self.assertIn("js/tema.js", html)
        self.assertRegex(self.temi, r"<form[^>]*data-temi-filter[^>]*hidden")
        self.assertIn("js/temi.js", self.temi)
        # raggruppato per sottotema della fonte, quando ce n'e' piu' d'uno
        self.assertIn('<tr class="group">', html)

    def test_il_css_delle_pagine_non_cuoce_colori(self):
        for nome in ("temi.css", "tema.css"):
            css = (CSS / nome).read_text(encoding="utf-8")
            with self.subTest(foglio=nome):
                self.assertNotRegex(css, r"#[0-9a-fA-F]{3,8}\b|rgba?\(")
                self.assertNotIn("text-transform: uppercase", css)


if __name__ == "__main__":
    unittest.main()
