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


class FiguraTest(unittest.TestCase):
    def test_il_marcatore_diventa_la_figura_e_quella_che_manca_sparisce(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "pezzo").mkdir()
            (Path(tmp) / "pezzo" / "classifica.svg").write_text('<svg class="fig"></svg>', encoding="utf-8")
            with mock.patch.object(blog, "FIGURE_DIR", Path(tmp)):
                html = blog._figure("<p>a</p>\n<!-- figura: classifica -->\n<!-- figura: assente -->", "pezzo")
        self.assertIn('<figure class="fig-articolo"><svg class="fig"></svg></figure>', html)
        self.assertNotIn("figura:", html)


class CreditoFotoTest(unittest.TestCase):
    def test_credito_incompleto_non_esce(self):
        self.assertIsNone(blog._cover_credit({"cover_credit": {"autore": "X"}}))
        self.assertIsNone(blog._cover_credit({}))

    def test_ogni_foto_registrata_ha_il_suo_credito_in_pagina(self):
        """Una scheda `.foto.json` accanto alla copertina vuol dire foto con licenza."""
        client = app.test_client()
        for post in blog.get_posts():
            cover = post.get("cover") or ""
            scheda = Path(blog.STATIC_DIR) / (cover.removeprefix("/static/").rsplit(".", 1)[0] + ".foto.json")
            if not cover or not scheda.is_file():
                continue
            with self.subTest(post=post["slug"]):
                dati = json.loads(scheda.read_text(encoding="utf-8"))
                self.assertIsNotNone(post["cover_credit"], "foto registrata senza cover_credit")
                self.assertEqual(post["cover_credit"]["licenza"], dati["cover_credit"]["licenza"])
                pagina = client.get(f"/blog/{post['slug']}").get_data(as_text=True)
                self.assertIn(dati["cover_credit"]["fonte_url"], pagina)
                self.assertIn(dati["cover_credit"]["licenza_url"], pagina)


class DatasetTest(unittest.TestCase):
    def test_il_dataset_dichiarato_esce_nello_schema_e_il_csv_esiste(self):
        client = app.test_client()
        con_dataset = [p for p in blog.get_posts() if p.get("dataset")]
        for post in con_dataset:
            with self.subTest(post=post["slug"]):
                ds = post["dataset"]
                self.assertTrue((Path(blog.STATIC_DIR) / ds["download"].removeprefix("/static/")).is_file())
                pagina = client.get(f"/blog/{post['slug']}").get_data(as_text=True)
                blocchi = re.findall(r'<script type="application/ld\+json">(.*?)</script>', pagina, re.DOTALL)
                schemi = [json.loads(b) for b in blocchi]
                dataset = [s for s in schemi if s.get("@type") == "Dataset"]
                self.assertEqual(len(dataset), 1)
                self.assertEqual(dataset[0]["distribution"][0]["encodingFormat"], "text/csv")
                self.assertTrue(dataset[0]["license"].startswith("https://creativecommons.org/"))

    def test_nessuna_figura_resta_come_commento(self):
        client = app.test_client()
        for post in blog.get_posts():
            with self.subTest(post=post["slug"]):
                pagina = client.get(f"/blog/{post['slug']}").get_data(as_text=True)
                self.assertNotIn("<!-- figura:", pagina)


if __name__ == "__main__":
    unittest.main()
