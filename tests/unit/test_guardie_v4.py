import unittest
import contextlib
import io
import tempfile
from pathlib import Path

from scripts.editoriale import guardie_v4


class G2Test(unittest.TestCase):
    def test_blocca_messaggi_interni_e_non_google_fonte(self):
        self.assertTrue(guardie_v4.g2("La priorità di indicizzazione è alta."))
        self.assertTrue(guardie_v4.g2("La pagina non ha ricevuto impressioni da Google."))
        self.assertTrue(guardie_v4.g2("Questa parola chiave porta traffico da Google."))
        self.assertTrue(guardie_v4.g2("La sitemap esclude la pagina noindex."))
        self.assertFalse(guardie_v4.g2("Google pubblica i dati nella pagina del servizio."))
        self.assertFalse(guardie_v4.g2("Google è la fonte dei dati pubblicati."))
        self.assertFalse(guardie_v4.g2("I dati di Google Trends sono una fonte di ricerca."))


class G4Test(unittest.TestCase):
    def test_avvisa_numero_nudo_escludendo_anno_e_riferimenti(self):
        hits = guardie_v4.g4_text("Nel campione il valore era 17. La fonte è [Istat](https://istat.it/).")
        self.assertEqual([hit[0] for hit in hits], ["17"])

    def test_anno_nella_frase_precedente_e_unita_spengono_avviso(self):
        text = "Nel 2024 il valore è cresciuto. Ora è 17 anni e 3,2 punti."
        self.assertEqual(guardie_v4.g4_text(text), [])

    def test_titolo_figura_o_tabella_con_numero_nudo_blocca(self):
        self.assertEqual(guardie_v4.g4_title("Figura 3 regioni"), ["3"])
        self.assertEqual(guardie_v4.g4_title("Tabella 2024"), [])

    def test_sweep_markdown_stampa_file_riga_severita_e_blocca(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "esempio.md"
            path.write_text("## Risultato\nIl valore è 17.\nLa priorità di indicizzazione è alta.\n", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = guardie_v4.main([str(path)])
        self.assertEqual(status, 1)
        self.assertIn(f"BLOCCO {path}:3: G2", output.getvalue())
        self.assertIn(f"AVVISO {path}:2: G4", output.getvalue())


class G3Test(unittest.TestCase):
    def test_stessa_fascia_non_segnalata(self):
        self.assertEqual(guardie_v4.g3_page([(1, "Occupati 15–34 anni."), (2, "Ancora 15-34 anni.")]), [])

    def test_fasce_diverse_in_sezioni_distinte_avviso_con_posizione(self):
        findings = guardie_v4.g3_page([(4, "## Giovani 15-34 anni"), (9, "## Adulti 35–64 anni")])
        self.assertEqual([(item[0], item[1]) for item in findings], [("avviso", 4), ("avviso", 9)])

    def test_confronto_diretto_nella_stessa_frase_blocca(self):
        findings = guardie_v4.g3_page([(7, "Il tasso 15-34 anni è superiore a quello dei 35-64 anni.")])
        self.assertTrue(any(severity == "errore" and line == 7 for severity, line, *_ in findings))

    def test_lista_definitoria_non_e_confronto_ne_avviso(self):
        self.assertEqual(guardie_v4.g3_page([(3, "Le fasce d'età sono: 15-34 anni e 35-64 anni.")]), [])

    def test_varianti_eta_aperta_e_trattini_tipografici(self):
        self.assertEqual([item[0] for item in guardie_v4.age_cohorts("15 anni e più; 15—34 anni")],
                         [(15, None), (15, 34)])


if __name__ == "__main__":
    unittest.main()
