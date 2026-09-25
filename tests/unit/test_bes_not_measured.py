"""Le celle che la fonte scrive ma che non sono una misura (`bes_data.NOT_MEASURED`).

Macerata e Savona valgono 0 di affollamento carcerario dal 2016: non un carcere
vuoto, una provincia senza posti regolamentari da contare. Il loader le toglie,
e queste prove tengono onesto l'insieme in tutte e due le direzioni: non deve
nascondere un valore vero se Istat lo corregge, e non deve lasciar passare uno
zero nuovo se la prossima edizione ne porta un altro.
"""
import csv
import unittest

from app import bes_data

OVERCROWDING = "06POL012P"


def _raw_cells():
    """`{(indicatore, territorio, anno): Dato}` del CSV provinciale, com'e' scritto."""
    dataset, _ = bes_data._paths("provincia")
    with dataset.open(encoding="utf-8", newline="") as handle:
        return {
            (row["idIndicatore"], row["Territorio"], int(row["Anno"])): row["Dato"]
            for row in csv.DictReader(handle, delimiter=";")
        }


class NotMeasuredTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = _raw_cells()
        cls.rows = bes_data.get_bes_rows("provincia")

    def test_ogni_cella_e_uno_zero_nel_csv(self):
        """Se Istat corregge Macerata con un numero vero, l'insieme non lo
        deve nascondere: la prova si rompe e qualcuno toglie la cella."""
        for cell in sorted(bes_data.NOT_MEASURED):
            with self.subTest(cella=cell):
                self.assertIn(cell, self.raw)
                self.assertEqual(self.raw[cell], "0")

    def test_ogni_zero_dell_affollamento_e_nell_insieme(self):
        """Uno zero nuovo in una prossima edizione finirebbe primo in
        classifica senza che niente lo dica: qui si ferma la suite."""
        zeros = {cell for cell, value in self.raw.items()
                 if cell[0] == OVERCROWDING and bes_data._parse_number(value) == 0}
        self.assertTrue(zeros)
        self.assertEqual(zeros - bes_data.NOT_MEASURED, set())

    def test_il_loader_non_porta_le_celle(self):
        loaded = {(row["id"], row["territory"], row["year"]) for row in self.rows}
        self.assertEqual(loaded & bes_data.NOT_MEASURED, set())

    def test_il_2015_resta(self):
        """Prima dello zero la serie e' vera, e resta."""
        values = {(row["territory"], row["year"]): row["value"]
                  for row in self.rows if row["id"] == OVERCROWDING}
        self.assertEqual(values[("Macerata", 2015)], 126.8)
        self.assertEqual(values[("Savona", 2015)], 63.3)
        self.assertNotIn(("Macerata", 2016), values)
        self.assertNotIn(("Savona", 2024), values)
        self.assertEqual(values[("Fermo", 2024)], 358.1)

    def test_nessuno_zero_di_affollamento_arriva_ai_lettori(self):
        self.assertFalse([row for row in self.rows
                          if row["id"] == OVERCROWDING and row["value"] == 0])

    def test_gli_altri_zeri_restano(self):
        """Non ogni zero e' un n.d.: gli omicidi volontari a zero sono province
        senza omicidi, e il filtro non li deve toccare."""
        raw_zeros = {cell for cell, value in self.raw.items()
                     if cell[0] == "07SIC001P" and bes_data._parse_number(value) == 0}
        loaded_zeros = {(row["id"], row["territory"], row["year"]) for row in self.rows
                        if row["id"] == "07SIC001P" and row["value"] == 0}
        self.assertTrue(raw_zeros)
        self.assertEqual(loaded_zeros, raw_zeros)


if __name__ == "__main__":
    unittest.main()
