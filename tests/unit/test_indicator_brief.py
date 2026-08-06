"""La serie annuale della media, la parte del brief che il brief calcola da se'.

Viste pure su matrici sintetiche: nessun dato committato, nessun giro reale,
quindi stanno qui e non fra le integration. Il resto del brief (le correlazioni
sul catalogo vero, il registro errori) resta in `tests/integration/`.
"""

import unittest

from scripts import indicator_brief


class AnnualMeansBase(unittest.TestCase):
    """La serie annuale della media e la sua base territoriale.

    Il brief e' la sola fonte dei numeri di un articolo, quindi una media annuale
    senza il suo denominatore e' un invito a scrivere "il fondo del 2021" quando
    a cambiare e' stato il campione. Vista pura su una matrice sintetica.
    """

    COSTANTE = {
        "2020": {"a": 10.0, "b": 20.0},
        "2021": {"a": 12.0, "b": 22.0},
        "2022": {"a": 14.0, "b": 24.0},
    }
    VARIABILE = {
        "2020": {"a": 10.0, "b": 20.0, "c": 30.0},
        "2021": {"a": 12.0},
        "2022": {"a": 14.0, "b": 24.0},
    }
    # Stesso numero di territori a ogni anno, ma non gli stessi: il caso reale e'
    # `bes-06POL007`, 19 regioni nel 2012 e 19 nel 2025, con il Veneto solo nel
    # primo e la Calabria solo nell'ultimo.
    SCAMBIO = {
        "2020": {"a": 10.0, "b": 20.0},
        "2021": {"a": 12.0, "b": 22.0},
        "2022": {"a": 14.0, "c": 24.0},
    }

    def test_every_year_carries_the_number_of_territories(self):
        means = indicator_brief._annual_means(self.VARIABILE)
        self.assertEqual([m["year"] for m in means], [2020, 2021, 2022])
        self.assertEqual([m["n"] for m in means], [3, 1, 2])
        self.assertAlmostEqual(means[0]["avg"], 20.0)

    def test_empty_cells_do_not_count_as_zero(self):
        means = indicator_brief._annual_means({
            "2020": {"a": 10.0, "b": None, "c": ""},
            "2021": {"a": None},
        })
        self.assertEqual(len(means), 1)          # il 2021 non ha valori: niente riga
        self.assertEqual(means[0]["n"], 1)
        self.assertAlmostEqual(means[0]["avg"], 10.0)

    def test_a_constant_base_is_declared_once_and_the_cells_stay_clean(self):
        lines = indicator_brief._means_lines(indicator_brief._annual_means(self.COSTANTE))
        self.assertIn("base costante: 2 territori ogni anno", lines[0])
        self.assertNotIn("VARIABILE", " ".join(lines))
        self.assertIn("2021: 17,00", " ".join(lines[1:]))
        self.assertNotIn("(2)", " ".join(lines[1:]))

    def test_a_moving_base_warns_and_prints_a_denominator_per_cell(self):
        lines = indicator_brief._means_lines(indicator_brief._annual_means(self.VARIABILE))
        body = " ".join(lines)
        self.assertIn("BASE TERRITORIALE VARIABILE", body)
        self.assertIn("non chiamare picco o fondo", body)
        self.assertIn("2021: 12,00 (1)", body)

    def test_two_years_are_the_extremes_already_printed_above(self):
        self.assertEqual(indicator_brief._means_lines(
            indicator_brief._annual_means({"2020": {"a": 1.0}, "2021": {"a": 2.0}})), [])

    def test_the_first_to_last_comparison_says_when_the_base_moved(self):
        varied = indicator_brief._annual_means(self.VARIABILE)
        self.assertIn("base 3 territori -> 2",
                      indicator_brief._base_note(varied, 2020, 2022))
        stable = indicator_brief._annual_means(self.COSTANTE)
        self.assertEqual(indicator_brief._base_note(stable, 2020, 2022), "")

    def test_every_year_carries_which_territories_answered(self):
        means = indicator_brief._annual_means(self.SCAMBIO)
        self.assertEqual(means[0]["territories"], ["a", "b"])
        self.assertEqual(means[-1]["territories"], ["a", "c"])

    def test_the_same_count_is_not_the_same_base(self):
        """Il caso che un controllo sui soli numeri dichiarava confrontabile: due
        estremi con lo stesso `n` ma con un territorio entrato e uno uscito."""
        means = indicator_brief._annual_means(self.SCAMBIO)
        lines = indicator_brief._means_lines(means)
        self.assertIn("BASE TERRITORIALE VARIABILE", lines[0])
        note = indicator_brief._base_note(means, 2020, 2022)
        self.assertIn("a entrambi gli estremi ma non gli stessi", note)
        self.assertIn("b, c", note)


if __name__ == "__main__":
    unittest.main()
