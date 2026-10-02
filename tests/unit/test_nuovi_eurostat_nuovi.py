"""Unittest per la verifica dei nuovi dati Eurostat estrai e normalizzati."""

import csv
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_CSV = PROJECT_ROOT / "app" / "static" / "data" / "nuovi" / "eurostat_nuovi.csv"
MANIFEST_CSV = PROJECT_ROOT / "app" / "static" / "data" / "nuovi" / "eurostat_nuovi_manifest.csv"
PROV_CODES_CSV = PROJECT_ROOT / "app" / "static" / "data" / "province_codes.csv"

EXPECTED_DATA_HEADERS = ["indicator_id", "level", "territory_key", "year", "value"]
EXPECTED_MANIFEST_HEADERS = [
    "indicator_id", "name", "institution", "unit", "decimals", "direction",
    "theme", "source_url", "method_url", "license", "license_quote",
    "year_min", "year_max", "n_provincia", "n_regione", "note"
]

EXPECTED_REGIONS = {
    "piemonte", "valle-d-aosta", "liguria", "lombardia", "trentino-alto-adige",
    "veneto", "friuli-venezia-giulia", "emilia-romagna", "toscana", "umbria",
    "marche", "lazio", "abruzzo", "molise", "campania", "puglia", "basilicata",
    "calabria", "sicilia", "sardegna"
}


class TestNuoviEurostatNuovi(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.prov_keys = set()
        with PROV_CODES_CSV.open("r", encoding="utf-8") as f:
            r = csv.DictReader(f, delimiter=";")
            for row in r:
                cls.prov_keys.add(row["province_key"])

        cls.data_rows = []
        with DATA_CSV.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            cls.data_headers = reader.fieldnames
            for row in reader:
                cls.data_rows.append(row)

        cls.manifest_rows = []
        with MANIFEST_CSV.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            cls.manifest_headers = reader.fieldnames
            for row in reader:
                cls.manifest_rows.append(row)

    def test_headers(self):
        self.assertEqual(self.data_headers, EXPECTED_DATA_HEADERS)
        self.assertEqual(self.manifest_headers, EXPECTED_MANIFEST_HEADERS)

    def test_manifest_entries(self):
        self.assertGreaterEqual(len(self.manifest_rows), 7)
        for row in self.manifest_rows:
            self.assertTrue(row["indicator_id"].startswith("EUROSTAT_"))
            self.assertIn(row["direction"], {"higher_better", "lower_better", "contextual"})
            self.assertIn("Eurostat", row["institution"])
            self.assertGreater(int(row["year_max"]), 2023)

    def test_valid_territories(self):
        for row in self.data_rows:
            level = row["level"]
            tkey = row["territory_key"]
            if level == "regione":
                self.assertIn(tkey, EXPECTED_REGIONS, f"Invalid region key: {tkey}")
            elif level == "provincia":
                self.assertIn(tkey, self.prov_keys, f"Invalid province key: {tkey}")
            else:
                self.fail(f"Invalid level: {level}")

    def test_no_duplicates(self):
        seen = set()
        for row in self.data_rows:
            key = (row["indicator_id"], row["level"], row["territory_key"], row["year"])
            self.assertNotIn(key, seen, f"Duplicate entry found: {key}")
            seen.add(key)

    def test_plausible_ranges(self):
        for row in self.data_rows:
            val = float(row["value"])
            ind = row["indicator_id"]
            if ind == "EUROSTAT_CASA_NON_RISCALDATA":
                self.assertTrue(0.0 <= val <= 50.0, f"{ind} value out of range: {val}")
            elif ind == "EUROSTAT_SCIENZIATI_INGEGNERI":
                self.assertTrue(0.0 <= val <= 30.0, f"{ind} value out of range: {val}")
            elif ind == "EUROSTAT_MADRI_MINORI_20":
                self.assertTrue(0.0 <= val <= 15.0, f"{ind} value out of range: {val}")
            elif ind == "EUROSTAT_ORE_LAVORATE":
                self.assertTrue(20.0 <= val <= 60.0, f"{ind} value out of range: {val}")
            elif ind == "EUROSTAT_NOTTI_ESTERO":
                self.assertTrue(0.0 <= val <= 100.0, f"{ind} value out of range: {val}")
            elif ind == "EUROSTAT_AUTOVETTURE_1000":
                self.assertTrue(300.0 <= val <= 3000.0, f"{ind} value out of range: {val}")
            elif ind == "EUROSTAT_OCCUPAZIONE_POSTI_LETTO":
                self.assertTrue(0.0 <= val <= 100.0, f"{ind} value out of range: {val}")

    def test_known_values(self):
        lookup = {
            (r["indicator_id"], r["level"], r["territory_key"], r["year"]): float(r["value"])
            for r in self.data_rows
        }

        # 1. EUROSTAT_CASA_NON_RISCALDATA (2025)
        self.assertAlmostEqual(lookup[("EUROSTAT_CASA_NON_RISCALDATA", "regione", "trentino-alto-adige", "2025")], 2.3, delta=0.1)
        self.assertAlmostEqual(lookup[("EUROSTAT_CASA_NON_RISCALDATA", "regione", "piemonte", "2025")], 7.0, delta=0.1)
        self.assertAlmostEqual(lookup[("EUROSTAT_CASA_NON_RISCALDATA", "regione", "sicilia", "2025")], 18.5, delta=0.1)

        # 2. EUROSTAT_SCIENZIATI_INGEGNERI (2025)
        self.assertAlmostEqual(lookup[("EUROSTAT_SCIENZIATI_INGEGNERI", "regione", "valle-d-aosta", "2025")], 3.0, delta=0.1)
        self.assertAlmostEqual(lookup[("EUROSTAT_SCIENZIATI_INGEGNERI", "regione", "umbria", "2025")], 4.4, delta=0.1)
        self.assertAlmostEqual(lookup[("EUROSTAT_SCIENZIATI_INGEGNERI", "regione", "lazio", "2025")], 6.3, delta=0.1)

        # 3. EUROSTAT_MADRI_MINORI_20 (2024, provincia)
        self.assertAlmostEqual(lookup[("EUROSTAT_MADRI_MINORI_20", "provincia", "sondrio", "2024")], 0.26, delta=0.05)
        self.assertAlmostEqual(lookup[("EUROSTAT_MADRI_MINORI_20", "provincia", "l-aquila", "2024")], 0.77, delta=0.05)
        self.assertAlmostEqual(lookup[("EUROSTAT_MADRI_MINORI_20", "provincia", "siracusa", "2024")], 3.05, delta=0.05)

        # 4. EUROSTAT_ORE_LAVORATE (2025)
        self.assertAlmostEqual(lookup[("EUROSTAT_ORE_LAVORATE", "regione", "sardegna", "2025")], 35.9, delta=0.1)
        self.assertAlmostEqual(lookup[("EUROSTAT_ORE_LAVORATE", "regione", "lazio", "2025")], 37.0, delta=0.1)
        self.assertAlmostEqual(lookup[("EUROSTAT_ORE_LAVORATE", "regione", "emilia-romagna", "2025")], 38.2, delta=0.1)

        # 5. EUROSTAT_NOTTI_ESTERO (2025)
        self.assertAlmostEqual(lookup[("EUROSTAT_NOTTI_ESTERO", "regione", "molise", "2025")], 11.34, delta=0.1)
        self.assertAlmostEqual(lookup[("EUROSTAT_NOTTI_ESTERO", "regione", "liguria", "2025")], 45.88, delta=0.1)
        self.assertAlmostEqual(lookup[("EUROSTAT_NOTTI_ESTERO", "regione", "trentino-alto-adige", "2025")], 61.69, delta=0.1)

        # 6. EUROSTAT_AUTOVETTURE_1000 (2024)
        self.assertAlmostEqual(lookup[("EUROSTAT_AUTOVETTURE_1000", "regione", "liguria", "2024")], 563.0, delta=1.0)
        self.assertAlmostEqual(lookup[("EUROSTAT_AUTOVETTURE_1000", "regione", "piemonte", "2024")], 723.0, delta=1.0)
        self.assertAlmostEqual(lookup[("EUROSTAT_AUTOVETTURE_1000", "regione", "valle-d-aosta", "2024")], 1936.0, delta=1.0)

        # 7. EUROSTAT_OCCUPAZIONE_POSTI_LETTO (2025)
        self.assertAlmostEqual(lookup[("EUROSTAT_OCCUPAZIONE_POSTI_LETTO", "regione", "calabria", "2025")], 37.2, delta=0.1)
        self.assertAlmostEqual(lookup[("EUROSTAT_OCCUPAZIONE_POSTI_LETTO", "regione", "abruzzo", "2025")], 49.0, delta=0.1)
        self.assertAlmostEqual(lookup[("EUROSTAT_OCCUPAZIONE_POSTI_LETTO", "regione", "veneto", "2025")], 53.9, delta=0.1)


if __name__ == "__main__":
    unittest.main()
