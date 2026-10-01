import csv
import os
import unittest


class TestNuoviAGCOM(unittest.TestCase):
    """Test di validazione per il dataset AGCOM (Banda ultralarga FTTH 4T 2025)."""

    def setUp(self):
        self.csv_path = "app/static/data/nuovi/agcom.csv"
        self.manifest_path = "app/static/data/nuovi/agcom_manifest.csv"
        self.province_codes_path = "app/static/data/province_codes.csv"

        self.assertTrue(os.path.exists(self.csv_path), f"File non trovato: {self.csv_path}")
        self.assertTrue(os.path.exists(self.manifest_path), f"File non trovato: {self.manifest_path}")

        self.valid_province_keys = set()
        with open(self.province_codes_path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f, delimiter=";"):
                self.valid_province_keys.add(r["province_key"])

        self.valid_region_keys = {
            "piemonte", "valle-d-aosta", "lombardia", "trentino-alto-adige", "veneto",
            "friuli-venezia-giulia", "liguria", "emilia-romagna", "toscana", "umbria",
            "marche", "lazio", "abruzzo", "molise", "campania", "puglia",
            "basilicata", "calabria", "sicilia", "sardegna"
        }

    def test_schema_e_duplicati(self):
        seen = set()
        expected_cols = ["indicator_id", "level", "territory_key", "year", "value"]

        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            self.assertEqual(reader.fieldnames, expected_cols)

            rows = list(reader)
            self.assertEqual(len(rows), 125)

            for row in rows:
                ind = row["indicator_id"]
                level = row["level"]
                tkey = row["territory_key"]
                year = int(row["year"])
                val = float(row["value"])

                self.assertEqual(ind, "AGCOM_FTTH")
                self.assertIn(level, ["provincia", "regione"])

                if level == "provincia":
                    self.assertIn(tkey, self.valid_province_keys, f"Chiave provincia non valida: {tkey}")
                    self.assertNotIn(tkey, ["bolzano", "trento"], "Bolzano e Trento dovrebbero essere escluse")
                else:
                    self.assertIn(tkey, self.valid_region_keys, f"Chiave regione non valida: {tkey}")

                self.assertEqual(year, 2025)

                key = (ind, level, tkey, year)
                self.assertNotIn(key, seen, f"Duplicato trovato: {key}")
                seen.add(key)

                # Intervallo plausibile per percentuali (0% - 100%)
                self.assertGreaterEqual(val, 0.0)
                self.assertLessEqual(val, 100.0)

    def test_valori_noti(self):
        valori = {}
        with open(self.csv_path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f, delimiter=";"):
                key = (r["indicator_id"], r["level"], r["territory_key"], int(r["year"]))
                valori[key] = float(r["value"])

        # 1. Regioni: Valle d'Aosta 58.63% (basso), Piemonte 73.20% (medio), Sicilia 89.06% (alto)
        self.assertAlmostEqual(valori[("AGCOM_FTTH", "regione", "valle-d-aosta", 2025)], 58.63, delta=0.05)
        self.assertAlmostEqual(valori[("AGCOM_FTTH", "regione", "piemonte", 2025)], 73.20, delta=0.05)
        self.assertAlmostEqual(valori[("AGCOM_FTTH", "regione", "sicilia", 2025)], 89.06, delta=0.05)

        # 2. Province: Massa-Carrara ~73.51% (medio), Palermo ~95.14% (alto)
        self.assertAlmostEqual(valori[("AGCOM_FTTH", "provincia", "massa-carrara", 2025)], 73.51, delta=0.5)
        self.assertAlmostEqual(valori[("AGCOM_FTTH", "provincia", "palermo", 2025)], 95.14, delta=0.5)

    def test_manifest_schema(self):
        expected_manifest_cols = [
            "indicator_id", "name", "institution", "unit", "decimals", "direction", "theme",
            "source_url", "method_url", "license", "license_quote", "year_min", "year_max",
            "n_provincia", "n_regione", "note"
        ]
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            self.assertEqual(reader.fieldnames, expected_manifest_cols)
            rows = list(reader)
            self.assertEqual(len(rows), 1)
            r = rows[0]
            self.assertEqual(r["indicator_id"], "AGCOM_FTTH")
            self.assertEqual(r["direction"], "higher_better")


if __name__ == "__main__":
    unittest.main()
