"""Il riquadro "Dati e metodo": chi firma la pagina, da dove vengono i dati e
quanto sono freschi.

Una sola macro (`v1/_dati_metodo.html`) e una sola funzione che compone la
fonte (`app/dati_metodo.page_source`): nessuna pagina copia HTML e nessuna si
inventa una data. La data di aggiornamento della fonte compare solo se la
pipeline la registra (`publisher.dataset_updated`), altrimenti il riquadro non
la scrive.
"""

import unittest

from flask import render_template_string

from app import app, publisher
from app import publisher
from app.dati_metodo import page_source

# Il segno con cui le prove trovano il riquadro, e il nome di chi firma.
MARKER = 'class="dati-metodo" data-dati-metodo'


def _render(source_label, source_url=None, dataset_updated=None, limits=None):
    with app.test_request_context():
        return render_template_string(
            '{% import "v1/_dati_metodo.html" as dm with context %}'
            "{{ dm.box(source_label, source_url, dataset_updated, limits) }}",
            source_label=source_label, source_url=source_url,
            dataset_updated=dataset_updated, limits=limits)


class IlRiquadroDatiEMetodo(unittest.TestCase):
    def test_mostra_fonte_firma_e_link_alla_metodologia(self):
        reso = _render("Istat, indicatori territoriali", "https://www.istat.it/x")
        self.assertIn("Fonte:", reso)
        self.assertIn("Istat, indicatori territoriali", reso)
        self.assertIn("A cura di", reso)
        self.assertIn(publisher.editor_name(), reso)
        self.assertIn('href="/metodologia"', reso)

    def test_non_scrive_una_data_quando_la_fonte_non_la_registra(self):
        reso = _render("Istat, indicatori territoriali", "https://www.istat.it/x", None)
        self.assertNotIn("Fonte aggiornata il", reso)
        self.assertNotIn("<time", reso)

    def test_scrive_la_data_quando_c_e(self):
        reso = _render("Istat, indicatori territoriali", "https://www.istat.it/x", "2026-05-25")
        self.assertIn("Fonte aggiornata il", reso)
        self.assertIn('datetime="2026-05-25"', reso)
        self.assertIn("25 maggio 2026", reso)

    def test_la_fonte_ha_un_link_quando_c_e_un_indirizzo(self):
        reso = _render("Istat", "https://www.istat.it/x")
        self.assertIn('href="https://www.istat.it/x"', reso)

    def test_il_riquadro_e_solo_html_senza_javascript(self):
        reso = _render("Istat", "https://www.istat.it/x", "2026-05-25")
        self.assertIn("<aside", reso)
        self.assertNotIn("<script", reso)


class LaFontePrimaria(unittest.TestCase):
    def test_la_provincia_viene_dal_bes_dei_territori(self):
        fonte = page_source("province")
        self.assertTrue(fonte["label"].startswith("Istat"))
        self.assertTrue(fonte["url"])
        self.assertIn("bes-dei-territori", fonte["url"])

    def test_regione_e_tema_vengono_dagli_indicatori_territoriali(self):
        for page in ("region", "theme"):
            with self.subTest(page=page):
                fonte = page_source(page)
                self.assertIn("indicatori territoriali", fonte["label"])
                self.assertTrue(fonte["url"])

    def test_la_qualita_della_vita_viene_dal_bes(self):
        fonte = page_source("quality_of_life")
        self.assertIn("benessere", fonte["label"].lower())
        self.assertTrue(fonte["url"])

    def test_una_pagina_senza_fonte_primaria_torna_vuoto(self):
        fonte = page_source("home")
        self.assertIsNone(fonte["label"])
        self.assertIsNone(fonte["url"])

    def test_la_data_esiste_quando_la_registra_la_pipeline(self):
        # `data/source_state.json` e' committato: la data c'e', oppure la
        # funzione degrada a None senza fallire.
        fonte = page_source("region")
        self.assertIsNotNone(fonte["updated"])

    def test_la_data_manca_se_la_fonte_non_la_ha(self):
        # Una famiglia che la pipeline non registra: nessuna data inventata.
        self.assertIsNone(publisher.dataset_updated("eurostat"))


if __name__ == "__main__":
    unittest.main()
