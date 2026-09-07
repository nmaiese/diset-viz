"""La dispersione sui dati veri: il giro che i test unitari non possono fare.

`app/charts.py` disegna da coordinate, e quello si prova senza dati. Qui si
prova l'altra metà: che i due indicatori si risolvano davvero dal catalogo,
che le regioni in comune siano quelle, e soprattutto che la figura **entri in
pagina** passando per il filtro del template.

La garanzia che conta è la seconda: il marcatore vive dentro il corpo di una
sezione, e fra il Markdown dell'articolo e l'HTML della pagina ci sono due
passaggi (`prose_html`, poi `figures`). Se l'ordine si inverte, la figura esce
spezzata fra i paragrafi e nessun test unitario se ne accorge.
"""

import unittest

from app import app, charts

# Due indicatori regionali con serie piena, di due famiglie diverse: il numero
# medio di figli per donna (territoriale) e l'imprenditorialità giovanile.
MIO = "922"
COMPAGNO = "ter-401"


class FiguraSuiDatiVeri(unittest.TestCase):
    def test_una_regione_per_punto(self):
        figura = charts.figure(MIO, {"con": COMPAGNO}, "regione")
        self.assertTrue(figura)
        # Venti regioni: se il dataset ne perde una, il conto qui lo dice.
        self.assertEqual(figura.count("<circle"), 20)
        self.assertIn("<figcaption>", figura)

    def test_la_didascalia_nomina_i_due_indicatori_e_i_due_anni(self):
        figura = charts.figure(MIO, {"con": COMPAGNO}, "regione")
        self.assertIn("Numero medio di figli per donna", figura)
        self.assertIn("Imprenditorialità giovanile", figura)
        self.assertIn("in orizzontale", figura)
        self.assertIn("in verticale", figura)

    def test_le_regioni_evidenziate_arrivano_nella_didascalia(self):
        figura = charts.figure(MIO, {"con": COMPAGNO, "evidenzia": "Lazio"}, "regione")
        self.assertIn("In evidenza: Lazio.", figura)
        self.assertIn("is-on", figura)

    def test_un_compagno_che_non_esiste_non_disegna_niente(self):
        self.assertEqual(charts.figure(MIO, {"con": "ter-999999"}, "regione"), "")
        self.assertEqual(charts.figure(MIO, {"con": ""}, "regione"), "")


class DentroLaPagina(unittest.TestCase):
    def test_il_filtro_del_template_mette_la_figura_dopo_il_markdown(self):
        """Il marcatore attraversa la conversione Markdown e diventa figura, in quest'ordine."""
        corpo = ("Un paragrafo che regge da solo.\n\n"
                 f"<!-- grafico: dispersione con={COMPAGNO} evidenzia=Lazio -->\n\n"
                 "Un altro paragrafo.")
        with app.test_request_context():
            html = app.jinja_env.filters["prose_html"](corpo)
            reso = str(app.jinja_env.filters["figures"](html, MIO, "regione"))
        self.assertIn("<figure", reso)
        self.assertNotIn("grafico:", reso)
        # I due paragrafi restano paragrafi, e la figura non è finita dentro uno di loro.
        self.assertIn("<p>Un paragrafo che regge da solo.</p>", reso)
        self.assertIn("<p>Un altro paragrafo.</p>", reso)
        self.assertNotIn("<p><figure", reso)


if __name__ == "__main__":
    unittest.main()
