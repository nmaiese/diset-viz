"""La calibrazione: la forza e' quanto e' raro, non quanto e' grande.

Il difetto che questa tabella corregge era misurabile, e i due test sul file
vero lo tengono corretto: prima della calibrazione un tipo solo apriva il
57,7% degli articoli, che e' l'uniformita' rientrata al livello dell'angolo.
"""
import json
import unittest

from packs import angles, calibration


class TheTable(unittest.TestCase):
    def test_quantiles_are_built_only_with_enough_samples(self):
        table = calibration.build_table({
            "abbondante": [index / 100 for index in range(200)],
            "scarso": [0.1, 0.9, 0.5],
        })
        self.assertIn("abbondante", table)
        self.assertNotIn("scarso", table,
                         "calibrare su tre osservazioni e' prendere il rumore "
                         "per una distribuzione")
        self.assertEqual(len(table["abbondante"]), calibration.QUANTILES + 1)

    def test_edges_are_sorted(self):
        table = calibration.build_table({"x": [0.9, 0.1, 0.5] * 20})
        self.assertEqual(table["x"], sorted(table["x"]))


class Calibrating(unittest.TestCase):
    def setUp(self):
        self.table = calibration._table
        calibration._table = {"tipo": [round(step / 10, 3) for step in range(11)]}

    def tearDown(self):
        calibration._table = self.table

    def test_the_middle_of_the_distribution_lands_in_the_middle(self):
        self.assertAlmostEqual(calibration.calibrate("tipo", 0.5), 0.5, places=2)

    def test_the_extremes_saturate(self):
        self.assertEqual(calibration.calibrate("tipo", 0.0), 0.0)
        self.assertEqual(calibration.calibrate("tipo", 5.0), 1.0)

    def test_it_is_monotone(self):
        values = [calibration.calibrate("tipo", step / 40) for step in range(41)]
        self.assertEqual(values, sorted(values))

    def test_an_uncalibrated_type_keeps_its_raw_size(self):
        """Meglio un ordine imperfetto che un ordine inventato."""
        self.assertEqual(calibration.calibrate("mai-visto", 0.42), 0.42)


class TheTableOnDisk(unittest.TestCase):
    def test_it_exists_and_covers_the_common_detectors(self):
        table = calibration.reload_table()
        self.assertTrue(table, "packs/calibration.json manca: rigenerala con "
                               "python3 -m scripts.calibrate_angles")
        for kind in ("graduatoria-spezzata", "controcorrente", "sorpasso",
                     "rottura-di-pendenza"):
            self.assertIn(kind, table)
            self.assertEqual(len(table[kind]), calibration.QUANTILES + 1)

    def test_every_calibrated_type_is_a_type_a_detector_can_emit(self):
        """Una tabella che calibra tipi inesistenti e' una tabella vecchia.

        L'elenco e' il registro dei nomi legali, e comprende anche i due tipi a
        forza fissa che nella tabella non entrano mai (`rottura-di-metodo`,
        `gruppi-che-si-sorpassano`): un tipo assente da qui e presente nella
        tabella e' il difetto che questo test cerca, e il verso opposto e'
        legittimo per costruzione."""
        emitted = {
            "rottura-di-pendenza", "accelerazione", "rallentamento",
            "ritorno-al-livello", "divario-che-si-allarga", "divario-che-si-chiude",
            "sorpasso", "valore-fuori-scala", "graduatoria-spezzata",
            "controcorrente", "gruppi-che-divergono", "gruppi-che-convergono",
            "gruppi-che-si-sorpassano", "rottura-di-metodo",
        }
        self.assertLessEqual(set(calibration.reload_table()), emitted)

    def test_it_is_valid_json_with_sorted_edges(self):
        with open(calibration.TABLE_PATH, encoding="utf-8") as handle:
            table = json.load(handle)
        for kind, edges in table.items():
            self.assertEqual(edges, sorted(edges), kind)


class ItChangesTheOrder(unittest.TestCase):
    def test_a_common_effect_ranks_below_a_rare_one_of_the_same_size(self):
        """Il punto di tutta la faccenda, in un test solo."""
        saved = calibration._table
        try:
            calibration._table = {
                # un tipo dove 0,8 e' ordinario
                "comune": [0.7 + step / 100 for step in range(21)],
                # e uno dove 0,8 e' fuori dal comune
                "raro": [step / 100 for step in range(21)],
            }
            self.assertLess(calibration.calibrate("comune", 0.8),
                            calibration.calibrate("raro", 0.8))
        finally:
            calibration._table = saved

    def test_find_uses_the_table_and_keeps_the_raw_size(self):
        series = {}
        for step, year in enumerate(range(2000, 2016)):
            series[year] = {f"t{i:02d}": float(i) * (1 + 0.1 * step) for i in range(20)}
        found = angles.find(series)
        self.assertTrue(found)
        for angle in found:
            self.assertIn("raw", angle)
            self.assertGreaterEqual(angle["raw"], 0.0)


if __name__ == "__main__":
    unittest.main()
