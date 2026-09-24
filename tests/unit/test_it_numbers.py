"""I numeri all'italiana, le loro unita' e la preposizione davanti a un luogo, in un posto solo."""
import unittest

from app import it_numbers
from app.design import common, numfmt
from app.indicator_notes import change_unit_label, figure_unit
from app.seo_titles import at_place, to_place


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


class LeUnitaPercentuali(unittest.TestCase):
    """Accanto a una cifra ogni percentuale si scrive "%", attaccato.

    La fonte scrive l'unita' in tre modi ("%", "percentuale", "Valori
    percentuali") e le card correlate dicevano "79,9 valori percentuali" e
    "60,3 percentuale". Le variazioni di una percentuale sono punti
    percentuali, e restano per intero: "punti percentuali" contiene
    "percentual", e una regola che guardasse solo quello li scriverebbe "%"."""

    def test_ogni_percentuale_diventa_il_segno(self):
        for unit in ("%", "percentuale", "Valori percentuali", "valori percentuali",
                     "% del PIL", "% della popolazione attiva"):
            with self.subTest(unit=unit):
                self.assertEqual(numfmt.phrase_unit(unit), "%")
                self.assertTrue(numfmt.is_percent(unit))
                self.assertEqual(common.unit_note(unit), "in %")

    def test_i_punti_percentuali_restano_per_intero(self):
        for unit in ("punti percentuali", "Punti percentuali"):
            with self.subTest(unit=unit):
                self.assertEqual(numfmt.phrase_unit(unit), "punti percentuali")
                self.assertFalse(numfmt.is_percent(unit))
        self.assertEqual(common.unit_note("punti percentuali"), "in punti percentuali")

    def test_un_tasso_su_base_cento_non_e_una_percentuale(self):
        for unit in ("numero per centomila abitanti", "tonnellate per cento abitanti",
                     "numero per cento abitanti", "chilometro per cento chilometri quadrati"):
            with self.subTest(unit=unit):
                self.assertNotEqual(numfmt.phrase_unit(unit), "%")
                self.assertFalse(numfmt.is_percent(unit))

    def test_la_cifra_col_segno_attaccato(self):
        """Il "%" resta attaccato alla cifra (design/v1/SISTEMA.md), in ogni
        via: il `<data>` dei template, le frasi composte in Python."""
        for unit in ("Valori percentuali", "percentuale", "%"):
            with self.subTest(unit=unit):
                self.assertIn('79,9<span class="n__u n__u--pct">%</span>', str(numfmt.num(79.9, unit)))
                self.assertEqual(common.with_unit(79.9, unit), "79,9%")
                self.assertEqual(common.signed(1.04, unit), "+1,0%")

    def test_la_variazione_di_una_percentuale_e_in_punti(self):
        for unit in ("Valori percentuali", "percentuale", "%"):
            with self.subTest(unit=unit):
                points = change_unit_label("Aree protette", unit)
                self.assertEqual(points, "punti percentuali")
                self.assertEqual(common.signed(0.89, points), "+0,89\u00a0punti percentuali")
                self.assertEqual(common.with_unit(0.89, points), "0,89\u00a0punti percentuali")
                self.assertIn('+0,89<span class="n__u">\u2009punti percentuali</span>',
                              str(numfmt.delta(0.89, points)))

    def test_la_differenza_fra_due_tassi_e_in_punti(self):
        """Chi ha solo il nome e l'unita' della fonte (le card correlate, la
        scheda in un articolo, le righe della regione) passa da `figure_unit`:
        la differenza fra due tassi e' in "percentuale" per la fonte, ma il
        valore e' una distanza in punti."""
        gap = "Differenza tra tasso di occupazione maschile e femminile"
        self.assertEqual(figure_unit(gap, "percentuale"), "punti percentuali")
        self.assertEqual(numfmt.phrase_unit(figure_unit(gap, "percentuale")), "punti percentuali")
        self.assertEqual(figure_unit("Aree protette", "Valori percentuali"), "%")
        self.assertEqual(figure_unit("Aree protette", "punti percentuali"), "punti percentuali")
        # Le altre unita' restano come le scrive la fonte.
        self.assertEqual(figure_unit("Medici", "numero per mille abitanti"), "numero per mille abitanti")
        self.assertIsNone(figure_unit("Senza unita'", None))


class AtPlace(unittest.TestCase):
    def test_la_preposizione_segue_il_nome(self):
        self.assertEqual(at_place("Milano"), "a Milano")
        self.assertEqual(at_place("Aosta"), "ad Aosta")
        self.assertEqual(at_place("Ascoli Piceno"), "ad Ascoli Piceno")
        self.assertEqual(at_place("L'Aquila"), "all'Aquila")
        self.assertEqual(at_place("La Spezia"), "alla Spezia")

    def test_le_province_con_l_articolo(self):
        """"Qualita' della vita a Sud Sardegna" stava nella description."""
        self.assertEqual(at_place("Sud Sardegna"), "nel Sud Sardegna")
        self.assertEqual(at_place("Verbano-Cusio-Ossola"), "nel Verbano-Cusio-Ossola")
        # "davanti a": il complemento di termine non e' lo stato in luogo.
        self.assertEqual(to_place("Sud Sardegna"), "al Sud Sardegna")
        self.assertEqual(to_place("Aosta"), "ad Aosta")
        self.assertEqual(to_place("L'Aquila"), "all'Aquila")


if __name__ == "__main__":
    unittest.main()
