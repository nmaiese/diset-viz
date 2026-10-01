import csv
import os
import unittest


class TestNuoviACI(unittest.TestCase):
    """Test di validazione per il dataset ACI (Autovetture ante-2009 ed alimentazione alternativa)."""

    def setUp(self):
        self.csv_path = "app/static/data/nuovi/aci.csv"
        self.manifest_path = "app/static/data/nuovi/aci_manifest.csv"
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

            for row in reader:
                ind = row["indicator_id"]
                level = row["level"]
                tkey = row["territory_key"]
                year = int(row["year"])
                val = float(row["value"])

                self.assertIn(level, ["provincia", "regione"])

                if level == "provincia":
                    self.assertIn(tkey, self.valid_province_keys, f"Chiave provincia non valida: {tkey}")
                else:
                    self.assertIn(tkey, self.valid_region_keys, f"Chiave regione non valida: {tkey}")

                self.assertGreaterEqual(year, 2015)

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

        # 1. ACI_AUTO_ANTE_2009
        # Trento 13.9% (basso), Biella 39.6% (medio), Catania 60.0% (alto)
        self.assertAlmostEqual(valori[("ACI_AUTO_ANTE_2009", "provincia", "trento", 2025)], 13.9, delta=0.2)
        self.assertAlmostEqual(valori[("ACI_AUTO_ANTE_2009", "provincia", "biella", 2025)], 39.6, delta=0.2)
        self.assertAlmostEqual(valori[("ACI_AUTO_ANTE_2009", "provincia", "catania", 2025)], 60.0, delta=0.2)

        # 2. ACI_AUTO_ALIMENTAZIONE_ALTERNATIVA
        # Nuoro 5.5% (basso), Siena 18.0% (medio), Firenze 34.6% (alto)
        self.assertAlmostEqual(valori[("ACI_AUTO_ALIMENTAZIONE_ALTERNATIVA", "provincia", "nuoro", 2025)], 5.5, delta=0.2)
        self.assertAlmostEqual(valori[("ACI_AUTO_ALIMENTAZIONE_ALTERNATIVA", "provincia", "siena", 2025)], 18.0, delta=0.2)
        self.assertAlmostEqual(valori[("ACI_AUTO_ALIMENTAZIONE_ALTERNATIVA", "provincia", "firenze", 2025)], 34.6, delta=0.2)

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
            self.assertEqual(len(rows), 2)
            for r in rows:
                self.assertTrue(r["indicator_id"].startswith("ACI_"))
                self.assertIn(r["direction"], ["higher_better", "lower_better", "contextual"])


if __name__ == "__main__":
    unittest.main()
