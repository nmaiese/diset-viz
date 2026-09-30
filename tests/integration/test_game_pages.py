"""Le pagine /quiz*: briciole, dati strutturati e script per pagina.

Una `<nav>` di briciole e un `BreadcrumbList` per pagina, dalla stessa macro
`_breadcrumb.html`. Prima c'erano due `<nav class="breadcrumb">` sovrapposte
(una scritta a mano) e, sul confronto, un `BreadcrumbList` scritto a mano."""
import json
import re
import unittest

from app import app, publisher

PAGINE = {
    "/quiz": "quiz-hub.js",
    "/quiz/indovina-la-regione": "quiz-indovina.js",
    "/quiz/chi-e-maggiore": "quiz-compare.js",
    "/quiz/ordina": "quiz-order.js",
    "/quiz/classifica": "quiz-leaderboard.js",
}
GIOCHI = ("/quiz/indovina-la-regione", "/quiz/chi-e-maggiore", "/quiz/ordina")


def _jsonld(html):
    blocchi = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    return [json.loads(b) for b in blocchi]


class GamePagesTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def _html(self, path):
        risposta = self.client.get(path)
        self.assertEqual(risposta.status_code, 200, path)
        return risposta.get_data(as_text=True)

    def test_una_sola_nav_di_briciole(self):
        for path in PAGINE:
            with self.subTest(path=path):
                html = self._html(path)
                self.assertEqual(len(re.findall(r'<nav class="breadcrumb"', html)), 1)
                self.assertEqual(len(re.findall(r'<nav[^>]*aria-label="Percorso"', html)), 1)

    def test_un_solo_breadcrumblist_nelle_pagine_indicizzate(self):
        for path in PAGINE:
            if path == "/quiz/classifica":
                continue
            with self.subTest(path=path):
                tipi = [b.get("@type") for b in _jsonld(self._html(path))]
                self.assertEqual(tipi.count("BreadcrumbList"), 1)

    def test_classifica_noindex_e_senza_jsonld(self):
        html = self._html("/quiz/classifica")
        self.assertIn("noindex", html)
        self.assertEqual(_jsonld(html), [])

    def test_game_ha_creator_divario_e_fonte_dataset(self):
        for path in GIOCHI:
            with self.subTest(path=path):
                giochi = [b for b in _jsonld(self._html(path)) if b.get("@type") == "Game"]
                self.assertEqual(len(giochi), 1)
                gioco = giochi[0]
                self.assertEqual(gioco["creator"], {"@id": publisher.ORGANIZATION_ID})
                base = gioco["isBasedOn"]
                self.assertEqual(base["@type"], "Dataset")
                self.assertEqual(base["creator"]["name"], "Istat")
                self.assertTrue(base["license"].startswith("http"))

    def test_hub_ha_itemlist_dei_tre_giochi(self):
        liste = [b for b in _jsonld(self._html("/quiz")) if b.get("@type") == "ItemList"]
        self.assertEqual(len(liste), 1)
        elementi = liste[0]["itemListElement"]
        self.assertEqual(len(elementi), 3)
        percorsi = [e["url"][e["url"].index("/quiz"):] for e in elementi]
        self.assertEqual(percorsi, list(GIOCHI))

    def test_ogni_pagina_carica_il_suo_entry_e_non_game_js(self):
        for path, entry in PAGINE.items():
            with self.subTest(path=path):
                html = self._html(path)
                self.assertIn(f"dist/assets/{entry}", html)
                self.assertNotIn("dist/assets/game.js", html)


if __name__ == "__main__":
    unittest.main()
