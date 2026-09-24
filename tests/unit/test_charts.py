"""La dispersione dentro l'articolo, e la sparkline della 1.0.

Qui sta solo ciò che gira senza dati e senza app: il marcatore, le coordinate,
l'SVG. Il giro completo su un indicatore vero (`figure`, che legge il catalogo)
sta in `tests/integration/`, perché ha bisogno del dataset.

Quello che questi test devono garantire non è che la figura sia bella. È che
una figura che non si può disegnare **sparisca senza rompere il testo**: il
marcatore vive dentro il corpo di una sezione, e un errore lì non deve mai
arrivare in pagina come un commento HTML nudo o come una traccia.

La sparkline (`app.design.charts.spark`) ha le sue prove in fondo: l'asse per
anno, il pavimento sullo scarto interquartile, niente disegno sotto i due
punti, niente colori nell'SVG.
"""

import re
import unittest

from app import charts
from app.design import charts as design_charts


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

    def test_il_tipo_viaggia_con_la_richiesta(self):
        corpo = ("<!-- grafico: dispersione con=ter-401 -->\n"
                 "<!-- grafico: ritratto regione=Sardegna con=ter-401,ter-921 -->")
        chieste = charts.requested(corpo)
        self.assertEqual([c["tipo"] for c in chieste], ["dispersione", "ritratto"])
        self.assertEqual(chieste[1]["regione"], "Sardegna")


class Ritratto(unittest.TestCase):
    """Dove sta una regione fra il minimo e il massimo italiano, su piu' indicatori."""

    def righe(self, quante=4):
        return [(f"Indicatore {i}", i / max(1, quante - 1)) for i in range(quante)]

    def test_una_riga_per_indicatore(self):
        disegno = charts.portrait_svg(self.righe(4), "Sardegna")
        self.assertEqual(disegno.count("portrait__track"), 4)
        self.assertEqual(disegno.count("portrait__dot"), 4)

    def test_un_solo_indicatore_non_e_un_ritratto(self):
        self.assertEqual(charts.portrait_svg(self.righe(1), "Sardegna"), "")

    def test_i_due_capi_dicono_solo_la_posizione(self):
        # Nessun numero: le unita' di sei indicatori non si confrontano.
        disegno = charts.portrait_svg(self.righe(3), "Sardegna")
        self.assertIn("il valore più basso d'Italia", disegno)
        self.assertNotRegex(disegno, r">-?\d+[,.]\d+<")

    def test_la_quota_resta_dentro_la_tela(self):
        disegno = charts.portrait_svg([("A", -3.0), ("B", 9.0)], "Sardegna")
        cx = [float(v) for v in re.findall(r'portrait__dot" cx="([\d.]+)"', disegno)]
        self.assertTrue(all(8.0 <= v <= charts.WIDTH - 8.0 for v in cx), cx)

    def test_svg_nascosto_agli_screen_reader(self):
        self.assertIn('aria-hidden="true"', charts.portrait_svg(self.righe(3), "Sardegna"))


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


def _coords(svg):
    """I vertici della linea e il centro del punto finale, in pixel."""
    line = re.search(r'class="spark__line" points="([^"]+)"', svg).group(1)
    points = [tuple(float(v) for v in pair.split(",")) for pair in line.split()]
    dot = re.search(r'class="spark__dot" cx="([\d.]+)" cy="([\d.]+)"', svg)
    return points, (float(dot.group(1)), float(dot.group(2)))


def _serie(*pairs):
    return [{"year": year, "value": value} for year, value in pairs]


class Sparkline(unittest.TestCase):
    """La sparkline: per anno, in pixel veri, col pavimento, senza colori."""

    def test_l_asse_e_per_anno_non_per_posizione(self):
        # Un'indagine periodica: dal 2003 si salta al 2010. Per posizione il
        # 2010 cadeva a meta' (44 px), per anno cade a sette ottavi.
        svg = design_charts.spark(_serie((2003, 1.0), (2010, 2.0), (2011, 3.0)))
        (x0, _), (x1, _), (x2, _) = _coords(svg)[0]
        pad = design_charts.SPARK_PAD
        inner = 88 - 2 * pad
        self.assertAlmostEqual(x0, pad, places=1)
        self.assertAlmostEqual(x1, pad + inner * 7 / 8, places=1)
        self.assertAlmostEqual(x2, 88 - pad, places=1)

    def test_gli_anni_si_ordinano_e_il_punto_sta_sull_ultimo(self):
        svg = design_charts.spark(_serie((2020, 3.0), (2010, 1.0), (2015, 2.0)))
        points, dot = _coords(svg)
        self.assertEqual([x for x, _ in points], sorted(x for x, _ in points))
        self.assertEqual(points[-1], dot)

    def test_il_viewbox_e_la_misura_in_pixel(self):
        serie = _serie((2010, 1.0), (2020, 2.0))
        for size, (w, h) in (("s", (88, 28)), ("m", (120, 32))):
            svg = design_charts.spark(serie, size)
            self.assertIn(f'viewBox="0 0 {w} {h}" width="{w}" height="{h}"', svg)
            self.assertIn(f"spark--{size}", svg)
        self.assertIn('viewBox="0 0 88 28"', design_charts.spark(serie, "xl"))
        self.assertNotIn("preserveAspectRatio", design_charts.spark(serie))

    def test_niente_disegno_sotto_i_due_punti(self):
        self.assertEqual(design_charts.spark([]), "")
        self.assertEqual(design_charts.spark(None), "")
        self.assertEqual(design_charts.spark(_serie((2020, 5.0))), "")
        self.assertEqual(design_charts.spark(_serie((2019, None), (2020, 5.0))), "")

    def test_nessun_colore_nell_svg(self):
        # I colori stanno in components.css, per classe: un esadecimale qui
        # terrebbe la curva sulla palette chiara quando la pagina va scura.
        svg = design_charts.spark(_serie((2010, 1.0), (2015, 4.0), (2020, 2.0)), "m", 1.0)
        self.assertNotRegex(svg, r"#[0-9a-fA-F]{3,8}\b")
        self.assertNotIn("rgb", svg)
        self.assertNotRegex(svg, r"\b(fill|stroke)=")
        self.assertIn('aria-hidden="true"', svg)

    def test_serie_piatta_senza_pavimento_sta_a_meta_altezza(self):
        points, _ = _coords(design_charts.spark(_serie((2010, 5.0), (2015, 5.0), (2020, 5.0))))
        self.assertEqual({y for _, y in points}, {14.0})


class PavimentoDellaSparkline(unittest.TestCase):
    """Una media che si muove poco rispetto alla distanza fra i territori non
    si disegna come una salita: la scala verticale non scende sotto lo scarto
    interquartile dei territori nell'ultimo anno."""

    inner = 28 - 2 * design_charts.SPARK_PAD

    def extent(self, serie, floor=None):
        points, _ = _coords(design_charts.spark(serie, "s", floor))
        ys = [y for _, y in points]
        return max(ys) - min(ys), ys

    def test_sotto_il_pavimento_la_linea_resta_quasi_piatta(self):
        serie = _serie((2010, 10.0), (2020, 10.5))
        senza, _ = self.extent(serie)
        con, ys = self.extent(serie, floor=5.0)
        self.assertAlmostEqual(senza, self.inner, places=1)
        # Si muove di 0,5 su un pavimento di 5: un decimo dell'altezza utile.
        self.assertAlmostEqual(con, self.inner * 0.5 / 5.0, places=1)
        # E la scala si allarga attorno al centro, non da un bordo.
        self.assertAlmostEqual(sum(ys) / 2, 14.0, places=1)

    def test_sopra_il_pavimento_la_serie_riempie_l_altezza(self):
        con, _ = self.extent(_serie((2010, 0.0), (2015, 12.0), (2020, 10.0)), floor=5.0)
        self.assertAlmostEqual(con, self.inner, places=1)

    def test_un_pavimento_nullo_non_conta(self):
        serie = _serie((2010, 10.0), (2020, 10.5))
        for floor in (None, 0, 0.0):
            self.assertAlmostEqual(self.extent(serie, floor)[0], self.inner, places=1)

    def test_il_pavimento_e_lo_scarto_interquartile(self):
        self.assertEqual(design_charts.spark_floor([1, 2, 3, 4, 5]), 2.0)
        # Quartili per interpolazione: 1,75 e 3,25 su quattro valori.
        self.assertAlmostEqual(design_charts.spark_floor([4, 1, 3, 2]), 1.5)
        self.assertEqual(design_charts.spark_floor([7, 7, 7, 7]), 0.0)
        self.assertIsNone(design_charts.spark_floor([5]))
        self.assertIsNone(design_charts.spark_floor([None, 5]))
        self.assertIsNone(design_charts.spark_floor([]))


class IlFiltroEUnInvolucro(unittest.TestCase):
    """Il filtro `sparkline` dei template (anche di quelli di ripiego) disegna
    con `charts.spark`, non con una copia sua."""

    def test_stesso_disegno(self):
        from app import app

        serie = _serie((2003, 1.0), (2010, 2.0), (2011, 3.0))
        reso = app.jinja_env.from_string('{{ s | sparkline("m", 0.5) }}').render(s=serie)
        self.assertEqual(reso, design_charts.spark(serie, "m", 0.5))
        self.assertEqual(app.jinja_env.from_string("{{ s | sparkline }}").render(s=[]), "")


if __name__ == "__main__":
    unittest.main()
