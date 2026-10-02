"""CSV committato dell'estrazione Istat provinciale (`scripts/nuovi_dati/istat_prov.py`)."""

import csv
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATI = ROOT / "app" / "static" / "data" / "nuovi" / "istat_prov.csv"
MANIFEST = ROOT / "app" / "static" / "data" / "nuovi" / "istat_prov_manifest.csv"
PROVINCE = ROOT / "app" / "static" / "data" / "province_codes.csv"

COLONNE = ["indicator_id", "level", "territory_key", "year", "value"]
COLONNE_MANIFEST = [
    "indicator_id", "name", "institution", "unit", "decimals", "direction", "theme",
    "source_url", "method_url", "license", "license_quote", "year_min", "year_max",
    "n_provincia", "n_regione", "note",
]
REGIONI = {
    "piemonte", "valle-d-aosta", "liguria", "lombardia", "veneto",
    "friuli-venezia-giulia", "emilia-romagna", "trentino-alto-adige", "toscana",
    "umbria", "marche", "lazio", "abruzzo", "molise", "campania", "puglia",
    "basilicata", "calabria", "sicilia", "sardegna",
}
# Intervalli plausibili (min, max) per indicatore.
INTERVALLI = {
    "ISTATP_LIFEEXP65": (17, 25),
    "ISTATP_FECONDITA": (0.5, 2.2),
    "ISTATP_INDICE_VECCHIAIA": (80, 450),
    "ISTATP_SALDO_MIGRATORIO_INTERNO": (-15, 15),
    "ISTATP_ETA_MEDIA_MADRE": (28, 35),
    "ISTATP_NATALITA": (2, 12),
    "ISTATP_DISOCCUPAZIONE": (0, 40),
    "ISTATP_ATTIVITA": (35, 85),
}


def leggi(path):
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


class NuoviIstatProvTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.righe = leggi(DATI)
        cls.manifest = leggi(MANIFEST)
        cls.province = {r["province_key"] for r in leggi(PROVINCE)}
        cls.valori = {
            (r["indicator_id"], r["level"], r["territory_key"], int(r["year"])): float(r["value"])
            for r in cls.righe
        }

    def test_schema(self):
        with DATI.open(encoding="utf-8") as fh:
            self.assertEqual(fh.readline().rstrip("\n").split(";"), COLONNE)
        with MANIFEST.open(encoding="utf-8") as fh:
            self.assertEqual(fh.readline().rstrip("\n").split(";"), COLONNE_MANIFEST)
        self.assertEqual(len(self.province), 107)

    def test_manifest_coerente_con_i_dati(self):
        ids = {m["indicator_id"] for m in self.manifest}
        self.assertEqual(ids, set(INTERVALLI))
        self.assertEqual(ids, {r["indicator_id"] for r in self.righe})
        for m in self.manifest:
            self.assertRegex(m["indicator_id"], r"^ISTATP_[A-Z0-9_]+$")
            self.assertIn(m["direction"], {"higher_better", "lower_better", "contextual"})
            for campo in ("name", "institution", "unit", "license_quote", "source_url", "method_url"):
                self.assertTrue(m[campo], campo)
            for vietato in ("—", "–", ";"):
                self.assertNotIn(vietato, m["name"])
            anni = [int(r["year"]) for r in self.righe if r["indicator_id"] == m["indicator_id"]]
            self.assertEqual((min(anni), max(anni)), (int(m["year_min"]), int(m["year_max"])))
            self.assertGreaterEqual(int(m["year_max"]), 2025)
            self.assertEqual(int(m["n_provincia"]), 107)
            self.assertEqual(int(m["n_regione"]), 20)

    def test_territori_validi(self):
        for r in self.righe:
            if r["level"] == "provincia":
                self.assertIn(r["territory_key"], self.province)
            else:
                self.assertEqual(r["level"], "regione")
                self.assertIn(r["territory_key"], REGIONI)

    def test_nessun_duplicato(self):
        chiavi = [(r["indicator_id"], r["level"], r["territory_key"], r["year"]) for r in self.righe]
        self.assertEqual(len(chiavi), len(set(chiavi)))

    def test_anni_e_copertura_completa(self):
        per_anno = {}
        for r in self.righe:
            anno = int(r["year"])
            self.assertGreaterEqual(anno, 2015)
            per_anno.setdefault((r["indicator_id"], r["level"], anno), set()).add(r["territory_key"])
        for (_, livello, _), territori in per_anno.items():
            self.assertEqual(len(territori), 107 if livello == "provincia" else 20)

    def test_valori_in_intervalli_plausibili(self):
        for r in self.righe:
            lo, hi = INTERVALLI[r["indicator_id"]]
            self.assertTrue(lo <= float(r["value"]) <= hi, r)

    def test_valori_noti_dalla_fonte(self):
        v = self.valori
        # alto, medio, basso, letti dalla cache Istat (ultimo anno)
        self.assertAlmostEqual(v[("ISTATP_LIFEEXP65", "provincia", "rimini", 2025)], 22.5)
        self.assertAlmostEqual(v[("ISTATP_LIFEEXP65", "provincia", "grosseto", 2025)], 21.5)
        self.assertAlmostEqual(v[("ISTATP_LIFEEXP65", "provincia", "napoli", 2025)], 20.0)
        self.assertAlmostEqual(v[("ISTATP_FECONDITA", "provincia", "bolzano", 2025)], 1.55)
        self.assertAlmostEqual(v[("ISTATP_FECONDITA", "provincia", "cagliari", 2025)], 0.75)
        self.assertAlmostEqual(v[("ISTATP_FECONDITA", "regione", "trentino-alto-adige", 2025)], 1.4)
        self.assertAlmostEqual(v[("ISTATP_DISOCCUPAZIONE", "provincia", "agrigento", 2025)], 19.821, places=2)
        self.assertAlmostEqual(v[("ISTATP_DISOCCUPAZIONE", "provincia", "savona", 2025)], 5.192, places=2)
        self.assertAlmostEqual(v[("ISTATP_DISOCCUPAZIONE", "provincia", "bergamo", 2025)], 1.349, places=2)
        self.assertAlmostEqual(v[("ISTATP_ATTIVITA", "provincia", "bolzano", 2025)], 75.2, places=1)
        self.assertAlmostEqual(v[("ISTATP_ATTIVITA", "provincia", "trento", 2025)], 73.6, places=1)
        self.assertAlmostEqual(v[("ISTATP_ATTIVITA", "provincia", "reggio-calabria", 2025)], 46.1, places=1)
        self.assertAlmostEqual(v[("ISTATP_INDICE_VECCHIAIA", "provincia", "bolzano", 2026)], 145.2)
        self.assertAlmostEqual(v[("ISTATP_INDICE_VECCHIAIA", "provincia", "oristano", 2026)], 352.2)

    def test_bolzano_e_trento_non_scambiati(self):
        # nei flussi lavoro ITD1/ITD2 sono Bolzano/Trento, non regioni
        v = self.valori
        self.assertGreater(
            v[("ISTATP_ATTIVITA", "provincia", "bolzano", 2025)],
            v[("ISTATP_ATTIVITA", "provincia", "trento", 2025)],
        )
        self.assertNotIn(("ISTATP_ATTIVITA", "regione", "bolzano", 2025), v)


if __name__ == "__main__":
    unittest.main()
