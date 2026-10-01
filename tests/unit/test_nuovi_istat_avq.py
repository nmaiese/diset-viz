"""Guardie sul CSV regionale Istat AVQ (`app/static/data/nuovi/istat_avq.csv`)."""

import csv
import re
import unittest
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "app" / "static" / "data" / "nuovi"
REGIONS = {
    "piemonte", "valle-d-aosta", "lombardia", "trentino-alto-adige", "veneto",
    "friuli-venezia-giulia", "liguria", "emilia-romagna", "toscana", "umbria",
    "marche", "lazio", "abruzzo", "molise", "campania", "puglia", "basilicata",
    "calabria", "sicilia", "sardegna",
}
COLUMNS = ["indicator_id", "level", "territory_key", "year", "value"]


def _read(name):
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


class NuoviIstatAvqTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = _read("istat_avq.csv")
        cls.manifest = {r["indicator_id"]: r for r in _read("istat_avq_manifest.csv")}
        cls.values = {
            (r["indicator_id"], r["territory_key"], int(r["year"])): float(r["value"])
            for r in cls.rows
        }

    def test_schema(self):
        with (DATA / "istat_avq.csv").open(encoding="utf-8") as handle:
            self.assertEqual(handle.readline().rstrip("\n").split(";"), COLUMNS)
        self.assertTrue(self.rows)

    def test_territori_e_livello(self):
        self.assertEqual({r["level"] for r in self.rows}, {"regione"})
        self.assertLessEqual({r["territory_key"] for r in self.rows}, REGIONS)

    def test_nessun_duplicato(self):
        chiavi = Counter((r["indicator_id"], r["level"], r["territory_key"], r["year"])
                         for r in self.rows)
        self.assertEqual([k for k, n in chiavi.items() if n > 1], [])

    def test_id_e_manifest_coincidono(self):
        self.assertEqual({r["indicator_id"] for r in self.rows}, set(self.manifest))
        for ind in self.manifest:
            self.assertRegex(ind, r"^AVQ_[A-Z0-9_]+$")

    def test_valori_in_intervalli_plausibili(self):
        for ind, riga in self.manifest.items():
            limite = 1000.0 if riga["unit"] == "per 1000 persone" else 100.0
            for (i, territorio, anno), valore in self.values.items():
                if i == ind:
                    self.assertTrue(0 <= valore <= limite, (ind, territorio, anno, valore))
                    self.assertGreaterEqual(anno, 2001)

    def test_ultimo_anno_2025_con_tutte_le_regioni(self):
        for ind, riga in self.manifest.items():
            self.assertEqual(riga["year_max"], "2025", ind)
            regioni = {t for (i, t, a) in self.values if i == ind and a == 2025}
            self.assertEqual(regioni, REGIONS, ind)
            self.assertEqual(int(riga["n_regione"]), 20, ind)
            self.assertEqual(int(riga["n_provincia"]), 0, ind)

    def test_manifest_campi_e_testi(self):
        for ind, riga in self.manifest.items():
            self.assertIn(riga["direction"], {"higher_better", "lower_better", "contextual"})
            self.assertTrue(riga["theme"] and riga["license_quote"] and riga["method_url"])
            self.assertEqual(riga["license"], "CC BY 4.0")
            for campo in ("name", "note"):
                self.assertNotRegex(riga[campo], r"[—–;]", (ind, campo))
            self.assertNotRegex(riga["name"], r"^[A-Z]{2,6}$")
            self.assertTrue(re.search(r"Istat", riga["institution"]))

    def test_valori_noti_dalla_fonte_2025(self):
        # alto, basso e medio letti dai flussi Istat in cache (anno 2025)
        noti = [
            ("AVQ_PRONTO_SOCCORSO", "campania", 42.5),
            ("AVQ_PRONTO_SOCCORSO", "toscana", 71.5),
            ("AVQ_PRONTO_SOCCORSO", "emilia-romagna", 100.5),
            ("AVQ_ASL_FILA_OLTRE_20_MIN", "calabria", 71.5),
            ("AVQ_ASL_FILA_OLTRE_20_MIN", "piemonte", 50.8),
            ("AVQ_BUS_FREQUENZA_CORSE", "lazio", 37.0),
            ("AVQ_BUS_FREQUENZA_CORSE", "sardegna", 68.1),
            ("AVQ_CONDIZIONATORI", "valle-d-aosta", 6.6),
            ("AVQ_CONDIZIONATORI", "sicilia", 72.2),
            ("AVQ_GIOVANI_CON_GENITORI", "sardegna", 71.0),
            ("AVQ_INCIDENTI_DOMESTICI", "molise", 4.4),
        ]
        for ind, territorio, atteso in noti:
            self.assertAlmostEqual(self.values[(ind, territorio, 2025)], atteso, places=6)

    def test_trentino_e_media_ponderata_tra_bolzano_e_trento(self):
        # Valore ricalcolato a mano dalle due parti Istat in cache (ITD1, ITD2 al 2025)
        # con i pesi del repo 535.8 e 544.1: non e' la media semplice.
        v = self.values[("AVQ_PRONTO_SOCCORSO", "trentino-alto-adige", 2025)]
        self.assertAlmostEqual(v, 86.389582, places=5)


if __name__ == "__main__":
    unittest.main()
