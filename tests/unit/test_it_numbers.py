"""I numeri all'italiana e la preposizione davanti a un luogo, in un posto solo."""
import unittest

from app import it_numbers
from app.seo_titles import at_place


class ItalianNumbers(unittest.TestCase):
    def test_migliaia_col_punto_decimali_con_la_virgola(self):
        self.assertEqual(it_numbers.number(25871.8), "25.871,8")
        self.assertEqual(it_numbers.number(0.02, 2), "0,02")
        self.assertEqual(it_numbers.number(1022, 0), "1.022")
        self.assertEqual(it_numbers.number(None), "n.d.")

    def test_la_variazione_porta_il_segno_e_lo_zero_no(self):
        self.assertEqual(it_numbers.change(3.9), "+3,9")
        self.assertEqual(it_numbers.change(-1.25, 2), "-1,25")
        # 0,03 con un decimale non e' "+0,0": non si e' mosso.
        self.assertEqual(it_numbers.change(0.03), "invariato")
        self.assertEqual(it_numbers.change(-0.04), "invariato")
        self.assertEqual(it_numbers.change(0.03, 2), "+0,03")
        self.assertIsNone(it_numbers.change(None))


class AtPlace(unittest.TestCase):
    def test_la_preposizione_segue_il_nome(self):
        self.assertEqual(at_place("Milano"), "a Milano")
        self.assertEqual(at_place("Aosta"), "ad Aosta")
        self.assertEqual(at_place("Ascoli Piceno"), "ad Ascoli Piceno")
        self.assertEqual(at_place("L'Aquila"), "all'Aquila")
        self.assertEqual(at_place("La Spezia"), "alla Spezia")


if __name__ == "__main__":
    unittest.main()
