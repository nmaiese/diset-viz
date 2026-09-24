"""Gli articoli guidati dai trend: figure in linea, foto con credito, Dataset.

Tre promesse che `docs/WORKFLOW_ARTICOLI_TREND.md` fa al lettore e a Google,
e che si rompono in silenzio se nessuno le guarda:

- una foto con licenza CC BY o CC BY-SA esce **sempre** con autore, licenza e
  link all'originale, perche' e' la condizione per usarla;
- un marcatore `<!-- figura: nome -->` diventa la figura, e una figura che
  manca sparisce senza lasciare il commento o rompere la pagina;
- un articolo che dichiara `dataset:` pubblica lo schema `Dataset` con il
  CSV scaricabile, e il CSV esiste.
"""

import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import app, blog


class InlineFiguresTest(unittest.TestCase):
    def test_il_marcatore_diventa_la_figura_e_quella_che_manca_sparisce(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "pezzo").mkdir()
            (Path(tmp) / "pezzo" / "classifica.svg").write_text('<svg class="fig"></svg>', encoding="utf-8")
            with mock.patch.object(blog, "FIGURES_DIR", Path(tmp)):
                html = blog._inline_figures("<p>a</p>\n<!-- figura: classifica -->\n<!-- figura: assente -->", "pezzo")
        self.assertIn('<figure class="article-figure"><svg class="fig"></svg></figure>', html)
        self.assertNotIn("figura:", html)


class CoverCreditTest(unittest.TestCase):
    def test_credito_incompleto_non_esce(self):
        self.assertIsNone(blog._cover_credit({"cover_credit": {"author": "X"}}))
        self.assertIsNone(blog._cover_credit({}))

    def test_ogni_foto_registrata_ha_il_suo_credito_in_pagina(self):
        """Una scheda `.photo.json` accanto alla copertina vuol dire foto con licenza."""
        client = app.test_client()
        for post in blog.get_posts():
            cover = post.get("cover") or ""
            record_path = Path(blog.STATIC_DIR) / (cover.removeprefix("/static/").rsplit(".", 1)[0] + ".photo.json")
            if not cover or not record_path.is_file():
                continue
            with self.subTest(post=post["slug"]):
                record = json.loads(record_path.read_text(encoding="utf-8"))
                self.assertIsNotNone(post["cover_credit"], "foto registrata senza cover_credit")
                self.assertEqual(post["cover_credit"]["license"], record["cover_credit"]["license"])
                page = client.get(f"/blog/{post['slug']}").get_data(as_text=True)
                self.assertIn(record["cover_credit"]["source_url"], page)
                self.assertIn(record["cover_credit"]["license_url"], page)


class DatasetTest(unittest.TestCase):
    def test_il_dataset_dichiarato_esce_nello_schema_e_il_csv_esiste(self):
        client = app.test_client()
        for post in (p for p in blog.get_posts() if p.get("dataset")):
            with self.subTest(post=post["slug"]):
                ds = post["dataset"]
                self.assertTrue((Path(blog.STATIC_DIR) / ds["download"].removeprefix("/static/")).is_file())
                page = client.get(f"/blog/{post['slug']}").get_data(as_text=True)
                blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.DOTALL)
                datasets = [s for s in (json.loads(b) for b in blocks) if s.get("@type") == "Dataset"]
                self.assertEqual(len(datasets), 1)
                self.assertEqual(datasets[0]["distribution"][0]["encodingFormat"], "text/csv")
                self.assertTrue(datasets[0]["license"].startswith("https://creativecommons.org/"))

    def test_nessuna_figura_resta_come_commento(self):
        client = app.test_client()
        for post in blog.get_posts():
            with self.subTest(post=post["slug"]):
                page = client.get(f"/blog/{post['slug']}").get_data(as_text=True)
                self.assertNotIn("<!-- figura:", page)


if __name__ == "__main__":
    unittest.main()


class TerritoriNelleTabelleTest(unittest.TestCase):
    """L'articolo sulle province ne nominava 123 in tabella senza un link, e
    "Continua a esplorare" restava vuoto. Le colonne dei territori legano il
    nome alla sua pagina quando coincide esattamente, e solo allora."""

    def test_la_colonna_provincia_lega_i_nomi_che_esistono(self):
        from app.design.pages import articolo
        with app.app_context():
            html = articolo._table("Tasso", ["Provincia", "Tasso"],
                                   [["Arezzo", "20,3"], ["Italia", "11,0"], ["Mantova", "5,8"]], "Valori", {1})
        self.assertIn('<a href="/provincia/arezzo">Arezzo</a>', html)
        self.assertIn('<a href="/provincia/mantova">Mantova</a>', html)
        self.assertIn('<th scope="row">Italia</th>', html)

    def test_una_colonna_che_non_e_di_territori_resta_testo(self):
        from app.design.pages import articolo
        with app.app_context():
            html = articolo._table("Serie", ["Serie", "2018", "2022"], [["Milano", "1,0", "2,0"]], "Valori")
            regioni = articolo._table("Tasso", ["Regione", "Tasso"], [["Milano", "1,0"], ["Valle d'Aosta/Vallée d'Aoste", "2,0"]], "Valori")
        self.assertNotIn("href=", html)
        self.assertNotIn('href="/provincia/milano"', regioni)
        self.assertIn('href="/regione/valle-d-aosta"', regioni)

    def test_l_articolo_sulle_province_porta_alle_province(self):
        html = app.test_client().get("/blog/infortuni-lavoro-province").get_data(as_text=True)
        self.assertGreater(len(set(re.findall(r'href="(/provincia/[a-z-]+)"', html))), 50)
        corsia = html[html.index("<h3>Territori e confronti</h3>"):]
        corsia = corsia[:corsia.index("</ul>")]
        legati = re.findall(r'href="(/provincia/[a-z-]+)"', corsia)
        self.assertLessEqual(len(legati), 6)
        # Prima i territori della prosa, poi quelli delle tabelle.
        self.assertEqual(legati[0], "/provincia/arezzo")
