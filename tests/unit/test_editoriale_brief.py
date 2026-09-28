"""Le funzioni pure del dossier di una scheda (`scripts.editoriale.brief`).

Forma della serie, arrotondamento e testo delle cifre, correlazione di rango:
niente dati, niente Flask, sotto il secondo.
"""

import unittest

from scripts.editoriale import brief


class SeriesShape(unittest.TestCase):
    def test_monotona_senza_svolte(self):
        shape = brief.series_shape([(2018, 11.0), (2019, 10.4), (2020, 9.7), (2025, 6.2)])
        self.assertEqual(shape["max"], {"year": 2018, "value": 11.0})
        self.assertEqual(shape["min"], {"year": 2025, "value": 6.2})
        self.assertEqual(shape["turns"], [])
        self.assertEqual(shape["runs"], [{"from": 2018, "to": 2025, "direction": "scende"}])

    def test_svolte_e_tratti(self):
        points = [(2015, 108), (2016, 112), (2019, 127), (2020, 111), (2024, 130)]
        shape = brief.series_shape(points)
        self.assertEqual(
            [(t["year"], t["kind"]) for t in shape["turns"]],
            [(2019, "massimo locale"), (2020, "minimo locale")],
        )
        self.assertEqual(
            [(r["from"], r["to"], r["direction"]) for r in shape["runs"]],
            [(2015, 2019, "sale"), (2019, 2020, "scende"), (2020, 2024, "sale")],
        )
        self.assertEqual(shape["max"]["year"], 2024)

    def test_un_piano_non_e_una_svolta_e_la_svolta_cade_alla_fine(self):
        shape = brief.series_shape([(1, 1.0), (2, 2.0), (3, 2.0), (4, 1.0)])
        self.assertEqual([(t["year"], t["kind"]) for t in shape["turns"]], [(3, "massimo locale")])
        self.assertEqual([r["direction"] for r in shape["runs"]], ["sale", "piatto", "scende"])

    def test_pari_prende_l_anno_piu_vecchio(self):
        shape = brief.series_shape([(2020, 5.0), (2021, 3.0), (2022, 5.0), (2023, 3.0)])
        self.assertEqual(shape["max"]["year"], 2020)
        self.assertEqual(shape["min"]["year"], 2021)

    def test_ordina_e_regge_i_casi_minimi(self):
        self.assertIsNone(brief.series_shape([]))
        shape = brief.series_shape([(2022, 4.0)])
        self.assertEqual(shape["turns"], [])
        self.assertEqual(shape["runs"], [])
        unordered = brief.series_shape([(2021, 2.0), (2020, 1.0)])
        self.assertEqual(unordered["runs"], [{"from": 2020, "to": 2021, "direction": "sale"}])


class Figures(unittest.TestCase):
    def test_cifra_con_unita(self):
        self.assertEqual(brief.figure(9.83, "%"), {"valore": 9.83, "testo": "9,8%"})
        self.assertEqual(brief.figure(54636.7, "euro"), {"valore": 54636.7, "testo": "54.637\u00a0euro"})
        self.assertIsNone(brief.figure(None, "%"))

    def test_arrotondamento_del_valore_e_del_testo(self):
        self.assertEqual(brief.rounded(6.2072959615833), 6.207296)
        # Mezzo per eccesso, come `it_numbers.number` e `Intl.NumberFormat`.
        self.assertEqual(brief.figure(26348.5, "euro")["testo"], "26.349\u00a0euro")
        # Sotto un centesimo i decimali crescono: 0,0042 non e' zero.
        self.assertEqual(brief.figure(0.0042, "%")["testo"], "0,004%")

    def test_variazione_col_segno_e_invariato(self):
        self.assertEqual(brief.change(-4.7955, "punti percentuali")["testo"], "-4,8 punti percentuali")
        self.assertEqual(brief.change(0.9399, "punti percentuali")["testo"], "+0,94 punti percentuali")
        self.assertEqual(brief.change(0.0, "punti percentuali")["testo"], "invariato")
        self.assertEqual(brief.change(1e-7, "punti percentuali")["testo"], "invariato")
        self.assertEqual(brief.change(19.2, "%")["testo"], "+19,2%")

    def test_conteggi_rapporti_coefficienti(self):
        self.assertEqual(brief.count(1234), {"valore": 1234, "testo": "1.234"})
        self.assertEqual(brief.ratio(6.9642)["testo"], "7,0 volte")
        self.assertEqual(brief.coefficient(-0.914286)["testo"], "-0,91")
        self.assertEqual(brief.coefficient(0.0004)["testo"], "0,00")


class RankCorrelation(unittest.TestCase):
    def test_monotone(self):
        self.assertAlmostEqual(brief.rank_correlation([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
        self.assertAlmostEqual(brief.rank_correlation([1, 2, 3, 4], [9, 7, 5, 1]), -1.0)

    def test_ranghi_medi_sui_pari(self):
        self.assertEqual(brief.average_ranks([10, 20, 20, 30]), [1.0, 2.5, 2.5, 4.0])
        # Valore di riferimento calcolato a mano: ranghi x = 1, 2.5, 2.5, 4 e y = 1, 2, 3, 4.
        self.assertAlmostEqual(brief.rank_correlation([10, 20, 20, 30], [1, 2, 3, 4]), 0.9486832980505138)

    def test_non_definita(self):
        self.assertIsNone(brief.rank_correlation([1, 2], [2, 1]))
        self.assertIsNone(brief.rank_correlation([5, 5, 5], [1, 2, 3]))
        with self.assertRaises(ValueError):
            brief.rank_correlation([1, 2, 3], [1, 2])


class Movers(unittest.TestCase):
    def test_solo_i_comuni_e_nell_ordine_giusto(self):
        start = {"a": 10, "b": 10, "c": 10, "d": 10, "solo-prima": 1}
        end = {"a": 15, "b": 8, "c": 13, "d": 2, "solo-dopo": 99}
        increases, decreases = brief.movers(start, end, k=3)
        self.assertEqual([m[0] for m in increases], ["a", "c"])
        self.assertEqual([m[0] for m in decreases], ["d", "b"])
        self.assertEqual(decreases[0], ("d", 10, 2, -8))


if __name__ == "__main__":
    unittest.main()
