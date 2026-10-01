"""Le pagine /quiz*: briciole, dati strutturati e script per pagina.

Una `<nav>` di briciole e un `BreadcrumbList` per pagina, dalla stessa macro
`_breadcrumb.html`. Prima c'erano due `<nav class="breadcrumb">` sovrapposte
(una scritta a mano) e, sul confronto, un `BreadcrumbList` scritto a mano."""
import json
import re
import unittest

from app import app, publisher, quiz, sources

PAGINE = {
    "/quiz": "quiz-hub.js",
    "/quiz/indovina-la-regione": "quiz-indovina.js",
    "/quiz/chi-e-maggiore": "quiz-compare.js",
    "/quiz/ordina": "quiz-order.js",
    "/quiz/province-italiane": "quiz-mappa.js",
    "/quiz/classifica": "quiz-leaderboard.js",
}
GIOCHI = ("/quiz/indovina-la-regione", "/quiz/chi-e-maggiore", "/quiz/ordina")


def _jsonld(html):
    blocchi = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    return [json.loads(b) for b in blocchi]


def _lista(valore):
    return valore if isinstance(valore, list) else [valore]


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
                self.assertTrue(all(url.startswith("http") for url in _lista(base["license"])))

    def _famiglie_nel_pool(self, path):
        """Le famiglie realmente presenti nel pool del gioco, dai prefissi degli id
        (un calcolo indipendente da quello dell'app)."""
        if path == "/quiz/indovina-la-regione":
            return {"territorial"}
        if path == "/quiz/indovina-la-provincia":
            return {"bes"}
        prefissi = {meta["internal_prefix"]: famiglia for famiglia, meta in sources.SOURCES.items()}
        famiglie = set()
        for voce in quiz._quiz_indicators():
            prefisso = voce["id"].split(":")[0] + ":" if ":" in voce["id"] else ""
            famiglie.add(prefissi[prefisso])
        return famiglie | {"bes"}

    def test_fonte_e_licenza_del_json_ld_vengono_da_sources(self):
        """R1 punto 12: nome e licenza dell'istituzione si compongono da app/sources.py
        sulle famiglie che il pool del gioco ha davvero, mai la stringa "Istat" da sola."""
        for path in GIOCHI + ("/quiz/indovina-la-provincia",):
            with self.subTest(path=path):
                famiglie = self._famiglie_nel_pool(path)
                base = [b for b in _jsonld(self._html(path)) if b.get("@type") == "Game"][0]["isBasedOn"]
                attesi = sources.institutions_label(famiglie)
                nomi = [c["name"] for c in _lista(base["creator"])]
                self.assertEqual(len(nomi), len(set(nomi)))
                self.assertIn(attesi, base["description"])
                gioco = [b for b in _jsonld(self._html(path)) if b.get("@type") == "Game"][0]
                if path in ("/quiz/chi-e-maggiore", "/quiz/ordina"):
                    self.assertIn(attesi, gioco["description"])
                self.assertEqual(
                    sorted(_lista(base["license"])),
                    sorted({sources.family_license_url(f) for f in famiglie if sources.family_license_url(f)}))
                self.assertEqual(set(nomi), {sources.SOURCES[f]["institution"] for f in famiglie})

    def test_chi_e_maggiore_e_ordina_dicono_anche_eurostat(self):
        for path in ("/quiz/chi-e-maggiore", "/quiz/ordina"):
            with self.subTest(path=path):
                base = [b for b in _jsonld(self._html(path)) if b.get("@type") == "Game"][0]["isBasedOn"]
                self.assertIn("Eurostat", [c["name"] for c in _lista(base["creator"])])
                self.assertIn("Eurostat", base["description"])
                self.assertNotIn("pubblicati da Istat.", base["description"])

    def test_hub_ha_itemlist_dei_cinque_giochi(self):
        liste = [b for b in _jsonld(self._html("/quiz")) if b.get("@type") == "ItemList"]
        self.assertEqual(len(liste), 1)
        elementi = liste[0]["itemListElement"]
        self.assertEqual(len(elementi), 5)
        percorsi = [e["url"][e["url"].index("/quiz"):] for e in elementi]
        self.assertEqual(percorsi, list(GIOCHI) + ["/quiz/indovina-la-provincia", "/quiz/province-italiane"])

    def test_ogni_pagina_carica_il_suo_entry_e_non_game_js(self):
        for path, entry in PAGINE.items():
            with self.subTest(path=path):
                html = self._html(path)
                self.assertIn(f"dist/assets/{entry}", html)
                self.assertNotIn("dist/assets/game.js", html)


if __name__ == "__main__":
    unittest.main()
