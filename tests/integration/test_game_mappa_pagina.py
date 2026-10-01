"""La pagina `/quiz/province-italiane`: struttura, SEO, testi, elenco, mappa muta.

Il gioco vero (API) lo prova `test_game_mappa.py`. Qui si guarda il markup che il server
scrive: un solo `h1`, un solo `BreadcrumbList`, il canonical, nessun carattere vietato nel
testo che si legge, l'elenco alfabetico con tutti i link, la frase sulla Sardegna, la riga
dei confini con i tre link, le sagome con l'etichetta neutra, e che la pagina risponda 200
anche senza `GAME_SEED_KEY`."""

import json
import os
import re
import unittest
from html.parser import HTMLParser
from unittest import mock

from app import app, game_daily, game_mappa, game_mappa_page, publisher

PATH = "/quiz/province-italiane"
VIETATI = "—–;…"


class _Testo(HTMLParser):
    """Il testo visibile di un elemento, entita' decodificate: Jinja scrive `Dov&#39;è`, e
    l'entita' contiene un `;` che nel testo letto non c'e'."""

    def __init__(self, radice):
        super().__init__(convert_charrefs=True)
        self.radice, self.dentro, self.salta, self.pezzi = radice, 0, 0, []

    def handle_starttag(self, tag, attrs):
        if tag == self.radice:
            self.dentro += 1
        if tag in ("script", "style"):
            self.salta += 1

    def handle_endtag(self, tag):
        if tag == self.radice:
            self.dentro -= 1
        if tag in ("script", "style"):
            self.salta -= 1

    def handle_data(self, data):
        if self.dentro and not self.salta:
            self.pezzi.append(data)


def _testo_visibile(html, radice="article"):
    parser = _Testo(radice)
    parser.feed(html)
    return " ".join(" ".join(parser.pezzi).split())


def _jsonld(html):
    return [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]


class PaginaMappaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        risposta = app.test_client().get(PATH)
        cls.status = risposta.status_code
        cls.html = risposta.get_data(as_text=True)
        cls.pool = game_daily.province_pool()

    def test_risponde_200(self):
        self.assertEqual(self.status, 200)

    def test_un_solo_h1(self):
        self.assertEqual(len(re.findall(r"<h1[\s>]", self.html)), 1)
        self.assertIn("<h1>Quiz sulle province italiane</h1>", self.html)

    def test_un_solo_breadcrumblist_e_una_sola_nav(self):
        tipi = [b.get("@type") for b in _jsonld(self.html)]
        self.assertEqual(tipi.count("BreadcrumbList"), 1)
        self.assertEqual(len(re.findall(r'<nav class="breadcrumb"', self.html)), 1)
        lista = next(b for b in _jsonld(self.html) if b.get("@type") == "BreadcrumbList")
        nomi = [e["name"] for e in lista["itemListElement"]]
        self.assertEqual(nomi, ["Home", "Sfida Italia", "Dov'è la provincia?"])

    def test_canonical_giusto(self):
        trovati = re.findall(r'<link rel="canonical" href="([^"]+)"', self.html)
        self.assertEqual(len(trovati), 1)
        self.assertTrue(trovati[0].endswith(PATH))
        self.assertNotIn("?", trovati[0])

    def test_titolo_e_descrizione(self):
        titolo = re.search(r"<title>(.*?)</title>", self.html, re.S).group(1)
        descrizione = re.search(r'<meta name="description" content="([^"]*)"', self.html).group(1)
        self.assertEqual(titolo, "Dov'è la provincia? Quiz province italiane | Divario Italia")
        self.assertLessEqual(len(titolo), 60)
        self.assertLessEqual(len(descrizione), 155)
        for carattere in VIETATI:
            self.assertNotIn(carattere, titolo)
            self.assertNotIn(carattere, descrizione)

    def test_game_jsonld(self):
        giochi = [b for b in _jsonld(self.html) if b.get("@type") == "Game"]
        self.assertEqual(len(giochi), 1)
        gioco = giochi[0]
        self.assertEqual(gioco["creator"], {"@id": publisher.ORGANIZATION_ID})
        self.assertTrue(gioco["isAccessibleForFree"])
        self.assertNotIn("isBasedOn", gioco)

    def test_nessun_carattere_vietato_nel_testo_visibile(self):
        testo = _testo_visibile(self.html)
        self.assertIn("Dov'è la provincia?", testo)
        for carattere in VIETATI:
            self.assertNotIn(carattere, testo, f"`{carattere}` nel testo visibile")

    def test_elenco_alfabetico_con_tutti_i_link_del_pool(self):
        elenco = re.search(r'<ul class="mappa-elenco">(.*?)</ul>', self.html, re.S).group(1)
        link = re.findall(r'<a href="/provincia/([^"]+)">([^<]+)</a>', elenco)
        self.assertEqual(sorted(k for k, _ in link), sorted(p["key"] for p in self.pool))
        self.assertEqual(len(link), len(self.pool))
        nomi = [n.casefold() for _, n in link]
        self.assertEqual(nomi, sorted(nomi))
        self.assertIn(f"<h2>Le {len(self.pool)} province della mappa</h2>", self.html)

    def test_forme_ufficiali_dove_cambiano(self):
        for ufficiale in game_mappa.OFFICIAL_NAMES.values():
            self.assertIn(ufficiale, _testo_visibile(self.html))

    def test_l_elenco_rimanda_a_province(self):
        sezione = re.search(r'<section class="prose" id="elenco-province">(.*?)</section>', self.html, re.S).group(1)
        self.assertIn('<a href="/province">', sezione)

    def test_la_frase_sulla_sardegna(self):
        self.assertIn(game_mappa_page.sardinia_note(len(self.pool)), _testo_visibile(self.html))

    def test_la_riga_dei_confini_con_tre_link(self):
        riga = re.search(r'<p class="source">(Confini delle province:.*?)</p>', self.html, re.S).group(1)
        self.assertEqual(riga, str(game_mappa_page.attribution("Divario Italia")))
        self.assertEqual(len(re.findall(r"<a ", riga)), 3)

    def test_la_riga_dei_confini_sta_dopo_la_mappa(self):
        self.assertLess(self.html.index('id="mappa-svg"'), self.html.index("Confini delle province:"))

    def test_le_sagome_hanno_etichetta_neutra_e_la_mappa_e_muta(self):
        sagome = re.findall(r'<use class="prov-tile"[^>]*>', self.html)
        self.assertEqual(len(sagome), len(self.pool))
        for sagoma in sagome:
            self.assertIn('aria-label="Provincia"', sagoma)
        mappa = re.search(r'<svg id="mappa-svg".*?</svg>', self.html, re.S).group(0)
        self.assertNotRegex(mappa, r"<title>|<text")
        self.assertEqual(len(re.findall(r'aria-label="([^"]*)"', mappa)),
                         len(self.pool) + 1)  # le sagome e l'etichetta della mappa

    def test_venti_regioni_ognuna_con_il_suo_riquadro(self):
        gruppi = re.findall(r'<g class="mappa-regione" data-region="([^"]+)" data-viewbox="([^"]+)"', self.html)
        self.assertEqual(len(gruppi), 20)
        for _, riquadro in gruppi:
            self.assertEqual(len(riquadro.split()), 4)

    def test_la_mappa_porta_lo_scopo_ma_non_la_risposta(self):
        etichetta = re.search(r'<svg id="mappa-svg"[^>]*aria-label="([^"]+)"', self.html).group(1)
        self.assertIn("Mappa muta", etichetta)
        for p in self.pool:
            self.assertNotIn(p["name"], etichetta)

    def test_senza_mappa_e_dichiarato_come_altro_esercizio(self):
        self.assertIn("Senza mappa: conta la regione", self.html)

    def test_i_tre_sprite_e_gli_asset_del_gioco(self):
        self.assertIn('id="mp-lecce"', self.html)
        self.assertIn('id="mr-puglia"', self.html)
        self.assertIn("dist/assets/quiz-mappa.js", self.html)
        self.assertNotIn("user-scalable", self.html)
        self.assertEqual(self.html.count('id="game-root"'), 1)
        self.assertEqual(self.html.count('id="mappa-azioni"'), 1)

    def test_nessuna_provincia_chiesta_nel_markup(self):
        """La pagina e' la stessa per tutti i giorni: niente che dipenda dalla sfida di oggi."""
        oggi = game_mappa.daily_provinces(game_daily.oggi_roma(), "italia")
        prima = app.test_client().get(PATH).get_data(as_text=True)
        con_altro_seed = None
        with mock.patch.dict(os.environ, {"GAME_SEED_KEY": "un-altra-chiave"}):
            con_altro_seed = app.test_client().get(PATH).get_data(as_text=True)
        self.assertEqual(prima, con_altro_seed)
        self.assertEqual(len(oggi), 10)


class SenzaChiaveTest(unittest.TestCase):
    def test_la_pagina_risponde_200_senza_seed_anche_su_cloud_run(self):
        """Un errore di deploy non deve togliere dall'indice la pagina che porta traffico."""
        ambiente = {k: v for k, v in os.environ.items() if k != "GAME_SEED_KEY"}
        ambiente["K_SERVICE"] = "divarioitalia"
        with mock.patch.dict(os.environ, ambiente, clear=True):
            risposta = app.test_client().get(PATH)
        self.assertEqual(risposta.status_code, 200)
        self.assertIn("Quiz sulle province italiane", risposta.get_data(as_text=True))

    def test_le_api_invece_rispondono_503(self):
        ambiente = {k: v for k, v in os.environ.items() if k != "GAME_SEED_KEY"}
        ambiente["K_SERVICE"] = "divarioitalia"
        with mock.patch.dict(os.environ, ambiente, clear=True):
            risposta = app.test_client().get("/api/game/map/daily/session?level=italia&mode=map")
        self.assertEqual(risposta.status_code, 503)


if __name__ == "__main__":
    unittest.main()
