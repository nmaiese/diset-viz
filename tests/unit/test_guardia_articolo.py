"""La guardia degli articoli del blog, su articoli finti.

Quattro articoli in una cartella temporanea, con il loro CSV e la loro figura:
uno pulito, uno con una cifra sbagliata, uno con un `—`, uno con un link rotto.
I link non aprono l'app di Flask: la guardia riceve una funzione che risponde
al posto del sito, con le rotte che "esistono".
"""
import contextlib
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts.editoriale import guardia_articolo as ga

CSV = """regione,chiave,pil_2024_euro,reddito_2024_euro
Lombardia,lombardia,50398.9,28154.3
Calabria,calabria,21702.1,16796.2
Valle d'Aosta,valle-d-aosta,47742.8,25751.0
"""

FRONTMATTER = """---
title: "Reddito per regione"
description: "Il reddito delle famiglie per regione, 2024."
slug: reddito-finto
date: 2026-10-05
draft: false
cover: /static/img/blog/reddito-finto.jpg
cover_alt: "Un portafoglio aperto."
cover_credit:
  author: "Una fotografa"
  license: "CC BY-SA 4.0"
  source_url: "https://commons.wikimedia.org/wiki/File:X.jpg"
indicator: 901
dataset:
  name: Reddito per regione
  creator: Istat
  source_url: https://www.istat.it/
  download: /static/data/articles/reddito-finto.csv
external_figures:
- value: "61,6"
  what: PIL per abitante di Bolzano, in migliaia di euro
  source: Istat
  url: https://www.istat.it/
---
"""

PULITO = FRONTMATTER + """
Nel 2024 il reddito era **28.154 euro in [Lombardia](/regione/lombardia)** e 16.796 in Calabria.

La differenza fra le due regioni e' di 11.358 euro. Bolzano produce [61,6 mila euro](https://www.istat.it/) a testa.

<!-- figura: reddito -->
"""

PAGINE = {"/regione/lombardia": (200, ""), "/regione/nessuna": (404, ""), "/vecchia": (301, "/nuova")}


def risposta(path):
    return PAGINE.get(path, (404, ""))


class GuardiaArticolo(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.static = root / "static"
        (self.static / "data" / "articles").mkdir(parents=True)
        (self.static / "data" / "articles" / "reddito-finto.csv").write_text(CSV, encoding="utf-8")
        self.figures = root / "figures"
        (self.figures / "reddito-finto").mkdir(parents=True)
        self.posts = root / "posts"
        self.posts.mkdir()
        self.svg("reddito", "<title>Lombardia su Calabria</title><desc>Due regioni nel 2024.</desc>")

    def svg(self, name, inner):
        (self.figures / "reddito-finto" / f"{name}.svg").write_text(f"<svg>{inner}</svg>", encoding="utf-8")

    def check(self, text, name="2026-10-05-reddito-finto.md", cap=ga.WORD_CAP):
        path = self.posts / name
        path.write_text(text, encoding="utf-8")
        return ga.check_article(path, link_status=risposta, cap=cap, static_dir=self.static, figures_dir=self.figures)

    def kinds(self, report, severity):
        return [f for f in report["rilievi"] if f.severity == severity]

    def test_articolo_pulito(self):
        report = self.check(PULITO)
        self.assertEqual(self.kinds(report, ga.ERROR), [])
        self.assertEqual(self.kinds(report, ga.WARNING), [])
        # 11.358 e' una differenza che il CSV non porta: si elenca, non fa fallire.
        unverifiable = self.kinds(report, ga.UNVERIFIABLE)
        self.assertEqual([f.message.split()[0] for f in unverifiable], ["'11.358'"])

    def test_g2_blocca_e_g4_avvisa_con_righe(self):
        report = self.check(PULITO.replace(
            "Nel 2024 il reddito", "Nel 2024 la priorità di indicizzazione riguarda il reddito"
        ) + "\nIl valore era 17.\n")
        self.assertTrue(any(f.check == "G2" and f.severity == ga.ERROR for f in report["rilievi"]))
        self.assertTrue(any(f.check == "G4" and f.severity == ga.WARNING for f in report["rilievi"]))
        self.assertTrue(all(f.line > 0 for f in report["rilievi"] if f.check in {"G2", "G4"}))

    def test_g8_avvisa_con_riga_senza_provare_causalita(self):
        sentence = "Il divario cresce perché mancano servizi."
        report = self.check(PULITO + "\n" + sentence + "\n")
        hits = [f for f in report["rilievi"] if f.check == "G8"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].severity, ga.WARNING)
        self.assertEqual((PULITO + "\n" + sentence + "\n").splitlines()[hits[0].line - 1], sentence)
        self.assertIn("registro", hits[0].message)

    def test_g8_non_avvisa_domanda_o_limite_causale(self):
        report = self.check(PULITO + "\nPerché il divario cresce?\n"
                            "La correlazione non prova che il divario sia dovuto ai servizi.\n")
        self.assertFalse(any(f.check == "G8" for f in report["rilievi"]))

    def test_g1_csv_documentato_e_anno_ambiguo(self):
        csv_file = self.static / "data" / "articles" / "reddito-finto.csv"
        csv_file.write_text("regione,anno,valore\nLombardia,2024,8.8\nCalabria,2024,9.0\n", encoding="utf-8")
        report = self.check(PULITO + "\nIn Italia nel 2024 il valore è 8,9%.\n")
        self.assertTrue(any(f.check == "G1" and f.severity == ga.ERROR for f in report["rilievi"]))
        report = self.check(PULITO + "\nIn Italia nel 2023 il valore è 8,9%.\n")
        self.assertTrue(any(f.check == "G1" and f.severity == ga.UNVERIFIABLE for f in report["rilievi"]))

    def test_g7_csv_lungo_stessa_geografia(self):
        csv_file = self.static / "data" / "articles" / "reddito-finto.csv"
        csv_file.write_text("livello,territorio,anno,valore\nprovincia,Arezzo,2022,3.0\nprovincia,Mantova,2022,1.0\nregione,Lombardia,2022,2.0\n", encoding="utf-8")
        report = self.check(PULITO + "\nNel 2022 le 3 province sono osservate.\n")
        self.assertTrue(any(f.check == "G7" and f.severity == ga.ERROR and "2 osservate" in f.message for f in report["rilievi"]))

    def test_g1_csv_con_misure_conflittuali_non_inventa_media(self):
        csv_file = self.static / "data" / "articles" / "reddito-finto.csv"
        csv_file.write_text("livello,territorio,anno,valore\nregione,Lombardia,2024,8.8\nregione,Lombardia,2024,18.8\nregione,Calabria,2024,9.0\n", encoding="utf-8")
        report = self.check(PULITO + "\nIn Italia nel 2024 il valore è 8,9%.\n")
        self.assertTrue(any(f.check == "G1" and f.severity == ga.UNVERIFIABLE for f in report["rilievi"]))

    def test_g7_campione_sintetico_infortuni_107_su_103(self):
        csv_file = self.static / "data" / "articles" / "reddito-finto.csv"
        with (ga.STATIC / "data" / "province_codes.csv").open(encoding="utf-8", newline="") as source:
            names = [row["name"] for row in csv.DictReader(source, delimiter=";")][:103]
        csv_file.write_text("livello,territorio,anno,valore\n" + "".join(
            f"provincia,{name},2022,1.0\n" for name in names
        ), encoding="utf-8")
        report = self.check(PULITO + "\nNel 2022 i dati coprono 107 province.\n")
        self.assertTrue(any(f.check == "G7" and f.severity == ga.ERROR and "103 osservate" in f.message for f in report["rilievi"]))

    def test_g3_blocca_confronto_diretto_e_avvisa_fasce_in_sezioni(self):
        direct = self.check(PULITO + "\nIl tasso 15-34 anni è superiore a quello dei 35-64 anni.\n")
        self.assertTrue(any(f.check == "G3" and f.severity == ga.ERROR for f in direct["rilievi"]))
        separate = self.check(PULITO + "\n## Giovani\n15-34 anni.\n## Adulti\n35 anni e più.\n")
        self.assertTrue(any(f.check == "G3" and f.severity == ga.WARNING for f in separate["rilievi"]))

    def test_cifra_sbagliata_e_errore_con_la_riga(self):
        report = self.check(PULITO.replace("28.154 euro", "28.145 euro"))
        errors = self.kinds(report, ga.ERROR)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].check, "cifre")
        self.assertIn("'28.145'", errors[0].message)
        self.assertIn("28.154", errors[0].message)
        lines = PULITO.splitlines()
        self.assertIn("28.145", PULITO.replace("28.154", "28.145").splitlines()[errors[0].line - 1])
        self.assertEqual(errors[0].line, next(i for i, row in enumerate(lines, 1) if "28.154" in row))

    def test_cifra_con_arrotondamento_dichiarato_coincide(self):
        report = self.check(PULITO.replace("28.154 euro", "28.154,3 euro"))
        self.assertEqual(self.kinds(report, ga.ERROR), [])

    def test_cifra_senza_ancora_non_fa_fallire(self):
        report = self.check(PULITO + "\nIl rapporto fra le due e' 1,7 volte, e nel 2019 era 1,9.\n")
        self.assertEqual(self.kinds(report, ga.ERROR), [])
        self.assertEqual(len(self.kinds(report, ga.UNVERIFIABLE)), 3)

    def test_anno_fuori_dal_csv_rende_ambigua_la_frase(self):
        report = self.check(PULITO + "\nNel 2019 la Lombardia aveva 27.000 euro, nel 2024 28.154.\n")
        self.assertEqual(self.kinds(report, ga.ERROR), [])

    def test_punto_decimale_all_inglese(self):
        report = self.check(PULITO + "\nIl rapporto e' 1.7 volte.\n")
        errors = self.kinds(report, ga.ERROR)
        self.assertEqual(len(errors), 1)
        self.assertIn("virgola", errors[0].message)

    def test_segno_sbagliato(self):
        report = self.check(PULITO + "\nLa Calabria ha -16.796 euro.\n")
        self.assertIn("segno", self.kinds(report, ga.ERROR)[0].message)

    def test_trattino_lungo(self):
        report = self.check(PULITO.replace("e' di 11.358", "e' — di 11.358"))
        errors = self.kinds(report, ga.ERROR)
        self.assertEqual([f.check for f in errors], ["tipografia"])
        self.assertIn("—", errors[0].message)

    def test_punto_e_virgola_nel_frontmatter(self):
        report = self.check(PULITO.replace("per regione, 2024.", "per regione; 2024."))
        errors = self.kinds(report, ga.ERROR)
        self.assertEqual([f.check for f in errors], ["tipografia"])
        self.assertEqual(errors[0].line, 3)

    def test_link_rotto_e_redirect(self):
        report = self.check(PULITO + "\nVedi [la Puglia](/regione/nessuna) e [un vecchio](/vecchia).\n")
        errors = self.kinds(report, ga.ERROR)
        self.assertEqual([f.check for f in errors], ["link", "link"])
        self.assertIn("404", errors[0].message)
        self.assertIn("301", errors[1].message)
        self.assertIn("/nuova", errors[1].message)

    def test_i_link_esterni_non_si_aprono(self):
        report = self.check(PULITO)
        self.assertEqual(self.kinds(report, ga.ERROR), [])

    def test_frontmatter_incompleto(self):
        text = PULITO.replace("cover_alt: \"Un portafoglio aperto.\"\n", "").replace("  creator: Istat\n", "")
        errors = self.kinds(self.check(text), ga.ERROR)
        messages = " ".join(f.message for f in errors)
        self.assertIn("`cover_alt`", messages)
        self.assertIn("`dataset.creator`", messages)

    def test_csv_dichiarato_ma_assente(self):
        report = self.check(PULITO.replace("reddito-finto.csv", "assente.csv"))
        self.assertTrue(any("non esiste" in f.message for f in self.kinds(report, ga.ERROR)))

    def test_figura_senza_alt_e_senza_file(self):
        self.svg("reddito", "<title></title><desc>Due regioni.</desc>")
        errors = self.kinds(self.check(PULITO + "\n<!-- figura: altra -->\n"), ga.ERROR)
        messages = " ".join(f.message for f in errors)
        self.assertIn("`<title>` (alt)", messages)
        self.assertIn("non ha il suo SVG", messages)

    def test_tetto_di_parole_e_un_avviso(self):
        report = self.check(PULITO, cap=10)
        self.assertEqual([f.check for f in self.kinds(report, ga.WARNING)], ["lunghezza"])
        self.assertEqual(self.kinds(report, ga.ERROR), [])

    def test_tetto_predefinito_1100(self):
        for words, warns in ((1050, False), (1150, True)):
            with self.subTest(words=words):
                text = FRONTMATTER + "\n" + "parola " * words
                report = self.check(text)
                self.assertEqual(report["parole"], words)
                self.assertEqual(bool(self.kinds(report, ga.WARNING)), warns)

    def test_cli_lunga_usa_tetto_2000(self):
        path = self.posts / "lunga.md"
        path.write_text(FRONTMATTER + "\n" + "parola " * 1500, encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = ga.main([str(path), "--json", "--lunga"], link_status=risposta,
                           static_dir=self.static, figures_dir=self.figures)
        report = json.loads(out.getvalue())[0]
        self.assertEqual((code, report["tetto"], report["parole"], report["avvisi"]), (0, 2000, 1500, 0))

    def test_cli_tetto_prevale_su_lunga(self):
        path = self.posts / "lunga.md"
        path.write_text(FRONTMATTER + "\n" + "parola " * 1500, encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = ga.main([str(path), "--json", "--lunga", "--tetto", "1200"],
                           link_status=risposta, static_dir=self.static, figures_dir=self.figures)
        report = json.loads(out.getvalue())[0]
        self.assertEqual((code, report["tetto"], report["parole"], report["avvisi"]), (0, 1200, 1500, 1))

    def test_cli_esito_e_json(self):
        buono = self.posts / "pulito.md"
        buono.write_text(PULITO, encoding="utf-8")
        rotto = self.posts / "rotto.md"
        rotto.write_text(PULITO + "\nVedi [x](/regione/nessuna).\n", encoding="utf-8")

        def run(*args):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = ga.main([str(a) for a in args], link_status=risposta,
                               static_dir=self.static, figures_dir=self.figures)
            return code, out.getvalue()

        code, text = run(buono, "--json")
        report = json.loads(text)[0]
        self.assertEqual(report["file"], str(buono))
        self.assertEqual((code, report["esito"], report["errori"]), (0, 0, 0))
        self.assertEqual(report["non_verificabili"], 1)
        code, text = run(rotto)
        self.assertEqual(code, 1)
        self.assertIn(f"{rotto}:", text)
        self.assertIn("1. ", text)
        self.assertIn("[errore/link]", text)


if __name__ == "__main__":
    unittest.main()
