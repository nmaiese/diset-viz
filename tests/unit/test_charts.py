"""La dispersione dentro l'articolo: parsing del marcatore e disegno.

Qui sta solo ciò che gira senza dati e senza app: il marcatore, le coordinate,
l'SVG. Il giro completo su un indicatore vero (`figure`, che legge il catalogo)
sta in `tests/integration/`, perché ha bisogno del dataset.

Quello che questi test devono garantire non è che la figura sia bella. È che
una figura che non si può disegnare **sparisca senza rompere il testo**: il
marcatore vive dentro il corpo di una sezione, e un errore lì non deve mai
arrivare in pagina come un commento HTML nudo o come una traccia.
"""

import unittest

from app import charts


class Marcatore(unittest.TestCase):
    def test_argomenti_semplici(self):
        letti = charts.parse_args("con=dem-BIRTHRATE evidenzia=Lazio,Sardegna")
        self.assertEqual(letti["con"], "dem-BIRTHRATE")
        self.assertEqual(letti["evidenzia"], "Lazio,Sardegna")

    def test_didascalia_fra_virgolette_tiene_gli_spazi(self):
        letti = charts.parse_args('con=ter-401 didascalia="Due regioni non seguono le altre."')
        self.assertEqual(letti["didascalia"], "Due regioni non seguono le altre.")

    def test_trova_i_marcatori_nel_corpo_anche_a_capo(self):
        corpo = ("Un paragrafo.\n\n<!-- grafico: dispersione con=ter-401\n"
                 '     didascalia="Sotto" -->\n\nUn altro paragrafo.\n'
                 "<!-- grafico: dispersione con=bes-12SER026 -->")
        chieste = charts.requested(corpo)
        self.assertEqual([c["con"] for c in chieste], ["ter-401", "bes-12SER026"])
        self.assertEqual(chieste[0]["didascalia"], "Sotto")

    def test_un_commento_qualsiasi_non_e_un_marcatore(self):
        self.assertEqual(charts.requested("<!-- sezione: quadro -->"), [])
        self.assertEqual(charts.requested("<!-- grafico: torta con=ter-401 -->"), [])


class Disegno(unittest.TestCase):
    def punti(self, quanti=12):
        return [(f"Regione {i}", float(i), float(quanti - i)) for i in range(quanti)]

    def test_niente_disegno_sotto_il_minimo_di_punti(self):
        self.assertEqual(charts.scatter_svg(self.punti(4), set(), "x", "y"), "")

    def test_un_punto_per_territorio(self):
        disegno = charts.scatter_svg(self.punti(12), set(), "x", "y")
        self.assertEqual(disegno.count("<circle"), 12)
        self.assertIn('viewBox="0 0 320 240"', disegno)

    def test_solo_gli_accesi_portano_il_nome(self):
        disegno = charts.scatter_svg(self.punti(12), {"Regione 3"}, "x", "y")
        self.assertEqual(disegno.count("scatter__name"), 1)
        self.assertIn("Regione 3", disegno)
        self.assertIn("is-on", disegno)

    def test_svg_nascosto_agli_screen_reader(self):
        # Una nuvola di punti non si legge ad alta voce: il testo sta nella
        # didascalia, e l'SVG deve dichiararsi decorativo.
        self.assertIn('aria-hidden="true"', charts.scatter_svg(self.punti(), set(), "x", "y"))

    def test_i_nomi_finiscono_dentro_la_tela(self):
        disegno = charts.scatter_svg(self.punti(12), {"Regione 0", "Regione 11"}, "x", "y")
        self.assertIn('text-anchor="end"', disegno)
        self.assertIn('text-anchor="start"', disegno)

    def test_serie_piatta_non_divide_per_zero(self):
        piatti = [(f"Regione {i}", 5.0, 7.0) for i in range(10)]
        self.assertEqual(charts.scatter_svg(piatti, set(), "x", "y").count("<circle"), 10)

    def test_nome_e_didascalia_sono_sfuggiti(self):
        cattivo = [("<script>", 1.0, 2.0)] + [(f"R{i}", float(i), float(i)) for i in range(10)]
        self.assertNotIn("<script>", charts.scatter_svg(cattivo, {"<script>"}, "x", "y"))


class Coppie(unittest.TestCase):
    def test_solo_i_territori_in_comune(self):
        coppie = charts.pairs({"A": 1.0, "B": 2.0, "C": 3.0}, {"A": 10.0, "C": 30.0})
        self.assertEqual(coppie, [("A", 10.0, 1.0), ("C", 30.0, 3.0)])

    def test_x_e_il_compagno_y_sono_io(self):
        # L'asse orizzontale porta l'altro indicatore: il pezzo parla del
        # proprio, e il proprio si legge in verticale come su ogni grafico
        # della pagina.
        (_, x, y), = charts.pairs({"A": 1.0}, {"A": 99.0})
        self.assertEqual((x, y), (99.0, 1.0))


class NomeCorto(unittest.TestCase):
    def test_toglie_la_fonte(self):
        self.assertEqual(charts.short_name("Tasso di natalità (Istat, regioni)"), "Tasso di natalità")

    def test_tiene_la_variante(self):
        self.assertEqual(charts.short_name("Imprenditorialità giovanile (totale)"),
                         "Imprenditorialità giovanile (totale)")


class Sostituzione(unittest.TestCase):
    """`render` non deve mai lasciare un marcatore in pagina, qualunque cosa vada storta."""

    def test_marcatore_rotto_sparisce_senza_rompere_il_testo(self):
        html = "<p>Prima.</p>\n<!-- grafico: dispersione con=ter-999999 -->\n<p>Dopo.</p>"
        reso = charts.render(html, "17", "regione")
        self.assertNotIn("grafico:", reso)
        self.assertIn("Prima.", reso)
        self.assertIn("Dopo.", reso)

    def test_un_errore_qualsiasi_non_arriva_in_pagina(self):
        def esplode(*_a, **_k):
            raise RuntimeError("il catalogo non risponde")

        vecchia, charts.figure = charts.figure, esplode
        try:
            reso = charts.render("<p>Testo.</p><!-- grafico: dispersione con=ter-401 -->", "17", "regione")
        finally:
            charts.figure = vecchia
        self.assertEqual(str(reso), "<p>Testo.</p>")

    def test_html_senza_marcatori_torna_identico(self):
        html = "<p>Un paragrafo qualunque.</p>"
        self.assertEqual(str(charts.render(html, "17", "regione")), html)


if __name__ == "__main__":
    unittest.main()
