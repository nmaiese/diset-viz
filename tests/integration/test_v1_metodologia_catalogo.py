"""La metodologia e il catalogo dati nella 1.0.

Due pagine che prima erano una colonna centrata e un elenco piatto. Qui si
guarda che escano dal template della 1.0 (`data-v1`, e nessun ripiego:
`DIVARIO_V1_STRICT` da tests/conftest.py fa salire l'eccezione), che la
metodologia tenga tutte le ancore a cui il sito linka e che il catalogo
elenchi ogni voce del suo grafo, per tema, con i file che la voce ha.
"""

import json
import re
import unittest
from pathlib import Path

from app import app, views

APP = Path(__file__).resolve().parents[2] / "app"


def jsonld(html, kind):
    for block in re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', html, re.S):
        data = json.loads(block)
        if data.get("@type") == kind:
            return data
    return None


class LaMetodologia(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = app.test_client().get("/metodologia").get_data(as_text=True)

    def test_esce_dalla_1_0(self):
        self.assertIn('data-v1="metodologia"', self.html)
        self.assertIn("css/ds/pages/metodologia.css", self.html)
        self.assertEqual(self.html.count("<h1"), 1)

    def test_ogni_ancora_a_cui_il_sito_linka_esiste(self):
        """Le schede linkano #come-nasce-il-testo, la qualita' della vita
        #qualita-della-vita e #indicatori-usati: si leggono dai sorgenti, cosi'
        un'ancora nuova linkata da qualche parte entra da sola nella prova."""
        linked = set()
        for path in list(APP.rglob("*.py")) + list(APP.rglob("*.html")):
            linked |= set(re.findall(r"/metodologia#([a-z0-9-]+)", path.read_text(encoding="utf-8")))
        self.assertTrue({"come-nasce-il-testo", "qualita-della-vita", "indicatori-usati"} <= linked)
        for anchor in sorted(linked):
            with self.subTest(ancora=anchor):
                self.assertIn(f'id="{anchor}"', self.html)

    def test_l_indice_porta_a_sezioni_che_ci_sono(self):
        toc = re.search(r'<nav class="toc".*?</nav>', self.html, re.S)
        self.assertIsNotNone(toc)
        anchors = re.findall(r'href="#([^"]+)"', toc.group(0))
        self.assertGreaterEqual(len(anchors), 6)
        for anchor in anchors:
            self.assertIn(f'id="{anchor}"', self.html)

    def test_le_tabelle_diventano_blocchi_e_le_liste_lunghe_si_chiudono(self):
        self.assertIn("table--stack", self.html)
        self.assertIn("stackwrap", self.html)
        self.assertGreaterEqual(self.html.count('<details class="more'), 2)

    def test_chi_ne_risponde_resta_nel_testo(self):
        self.assertIn('href="/chi-siamo#chi-lo-cura"', self.html)

    def test_ogni_serie_del_punteggio_ha_il_suo_link(self):
        with app.test_request_context():
            items = views._quality_life_indicators()
        self.assertTrue(items)
        for item in items:
            self.assertIn(f'href="{item["path"]}"', self.html)


class IlCatalogoDati(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = app.test_client().get("/catalogo-dati").get_data(as_text=True)
        with app.test_request_context():
            cls.entries = views._listed_indicator_entries()

    def test_esce_dalla_1_0(self):
        self.assertIn('data-v1="catalogo-dati"', self.html)
        self.assertIn("js/catalogo-dati.js", self.html)
        self.assertEqual(self.html.count("<h1"), 1)

    def test_la_testata_dice_le_cifre_calcolate(self):
        total = len(self.entries)
        downloadable = sum(1 for e in self.entries if e["downloads"])
        answer = re.search(r'<p class="answer">(.*?)</p>', self.html, re.S)
        self.assertIsNotNone(answer)
        self.assertIn(f'<data class="n n--count" value="{total}">', answer.group(1))
        text = " ".join(re.sub(r"<[^>]+>", "", answer.group(1)).split())
        self.assertIn(f"collega {total} dataset indicizzabili, {downloadable} con la serie", text)

    def test_ogni_voce_del_grafo_sta_in_un_gruppo(self):
        catalog = jsonld(self.html, "DataCatalog")
        self.assertEqual(len(catalog["dataset"]), len(self.entries))
        items = re.findall(r'<li class="catalogo-item"', self.html)
        self.assertEqual(len(items), len(catalog["dataset"]))
        groups = re.findall(r'<details class="catalogo-group"[^>]*data-collapse-mobile open', self.html)
        self.assertGreater(len(groups), 1)

    def test_i_file_sono_link_veri_solo_dove_ci_sono(self):
        client = app.test_client()
        with_files = [e for e in self.entries if e["downloads"]]
        self.assertTrue(with_files)
        for entry in with_files:
            self.assertIn(f'href="{entry["downloads"]["csv"]}"', self.html)
            self.assertIn(f'href="{entry["downloads"]["json"]}"', self.html)
        sample = with_files[0]["downloads"]["csv"]
        self.assertEqual(client.get(sample).status_code, 200)
        self.assertEqual(self.html.count(">CSV</a>"), len(with_files))

    def test_il_filtro_resta_nascosto_senza_javascript(self):
        self.assertRegex(self.html, r'<form class="toolbar catalogo-filter" data-cat-controls hidden')


if __name__ == "__main__":
    unittest.main()
