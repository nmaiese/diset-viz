"""Gli indici dei territori, `/regioni` e `/province`, sono pagine della 1.0.

Guardano cio' che la migrazione del 26 settembre 2026 ha tolto e che, se
tornasse, non farebbe fallire niente: il "passa il mouse" su un telefono, un
colore che giudica ("Debole" in arancio), i temi troncati coi puntini, il
bottone "Apri", la nota sul numero accanto alla provincia messa in fondo
dopo l'elenco. E che il ripiego regga se la regia cede.
"""
import logging
import os
import re
import unittest
from unittest import mock

from app import app, profiles, province_profile
from app.cache import cache
from app.design.pages import regione
from tests.integration.test_v1_pages import FUGHE, PLACEHOLDER, visible_text


class GliIndiciDeiTerritori(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.regioni = cls.client.get("/regioni").get_data(as_text=True)
        cls.province = cls.client.get("/province").get_data(as_text=True)
        with app.app_context():
            cls.per_regione = province_profile.by_region()
            cls.panoramica = profiles.regions_overview()

    def test_sono_pagine_della_1_0_senza_ripiego(self):
        for pagina, html in (("regioni", self.regioni), ("province", self.province)):
            with self.subTest(pagina=pagina):
                self.assertIn(f'data-v1="{pagina}"', html)
                self.assertIn(f"css/ds/pages/{pagina}.css", html)
                self.assertNotIn("css/site.css", html)
                self.assertEqual(len(re.findall(r"<h1\b", html)), 1)
                self.assertNotIn(PLACEHOLDER, html)
                testo = visible_text(html)
                self.assertIsNone(FUGHE.search(testo))
                for segno in ("—", "–", "…", ";"):
                    self.assertNotIn(segno, testo, segno)

    def test_niente_mouse_niente_giudizio_niente_apri(self):
        for html in (self.regioni, self.province):
            testo = visible_text(html).lower()
            self.assertNotIn("passa il mouse", testo)
            self.assertNotIn("debole", testo)
            self.assertNotIn("is-weak", html)
            self.assertNotRegex(testo, r"\bapri\b")

    def test_la_risposta_delle_regioni_dice_prima_e_ultima(self):
        with app.app_context():
            qualita = regione._region_quality()
        risposta = re.search(r'<p class="answer">(.*?)</p>', self.regioni, re.S).group(1)
        self.assertIn(f'href="/regione/{qualita["rows"][0]["key"]}"', risposta)
        self.assertIn(f'href="/regione/{qualita["rows"][-1]["key"]}"', risposta)
        self.assertIn(f"Sono {len(self.panoramica)}:", re.sub(r"<[^>]+>", "", risposta))

    def test_ogni_regione_una_scheda_nella_sua_ripartizione(self):
        schede = re.findall(r'<h3 class="card__title"><a href="(/regione/[a-z-]+)">', self.regioni)
        self.assertEqual(sorted(schede), sorted(r["path"] for r in self.panoramica.values()))
        for gruppo in ("ripartizione-nord", "ripartizione-centro", "ripartizione-sud"):
            self.assertIn(f'id="{gruppo}"', self.regioni)
        self.assertIn('href="/province"', self.regioni)
        # I temi a capo, interi: la scheda porta i nomi, non un'ellissi.
        self.assertNotIn("text-overflow", self.regioni)

    def test_la_mappa_per_scegliere_c_e_e_porta_ai_profili(self):
        self.assertIn("data-navmap", self.regioni)
        self.assertEqual(set(re.findall(r'<a href="(/regione/[a-z-]+)" tabindex="-1"', self.regioni)),
                         {r["path"] for r in self.panoramica.values()})
        self.assertIn("data-navmap", self.province)

    def test_le_province_la_nota_viene_prima_dell_elenco(self):
        nota = self.province.index('id="province-nota"')
        elenco = self.province.index('id="province-per-regione"')
        campo = self.province.index('data-list-filter="#province-per-regione"')
        self.assertLess(campo, nota)
        self.assertLess(nota, elenco)
        self.assertIn('aria-describedby="province-nota"', self.province)

    def test_le_province_indice_di_salto_e_gruppi(self):
        for chiave, province in self.per_regione.items():
            if not province:
                continue
            with self.subTest(regione=chiave):
                self.assertIn(f'href="#regione-{chiave}"', self.province)
                self.assertIn(f'id="regione-{chiave}"', self.province)
                for p in province:
                    self.assertIn(f'<li data-filter-name="{p["name"]}"><a href="{p["path"]}">'.replace("'", "&#39;"),
                                  self.province)
        self.assertNotIn("theme-chips", self.province)


class IlRipiegoDegliIndiciTiene(unittest.TestCase):
    """Come `test_v1_pages.IlRipiegoTiene`: se `derive` cede, le due pagine
    rispondono 200 dal template di prima."""

    def test_ogni_indice_regge_senza_la_sua_regia(self):
        def cede(*_args, **_kwargs):
            raise RuntimeError("la regia della 1.0 cede")

        client = app.test_client()
        livello = app.logger.level
        app.logger.setLevel(logging.CRITICAL)
        cache.clear()
        try:
            with mock.patch.dict(os.environ, {"DIVARIO_V1_STRICT": ""}), \
                    mock.patch("app.design.derive", side_effect=cede):
                for percorso in ("/regioni", "/province"):
                    with self.subTest(percorso=percorso):
                        risposta = client.get(percorso)
                        html = risposta.get_data(as_text=True)
                        self.assertEqual(risposta.status_code, 200)
                        self.assertNotIn('data-v1="', html)
                        self.assertIn('<header class="hdr">', html)
                        self.assertIn('"@type": "ItemList"', html)
        finally:
            app.logger.setLevel(livello)
            cache.clear()


if __name__ == "__main__":
    unittest.main()
