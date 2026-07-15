import csv
import tempfile
import unittest
from pathlib import Path

from scripts.update_data import OUTPUT_COLUMNS, read_preserved_rows, write_atomic


class UpdateDataPreserveTest(unittest.TestCase):
    def test_preserves_local_indicators_not_in_refresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Assoluti_Regione.csv"
            rows = [
                {
                    "idIndicatore": "12",
                    "Territorio": "Abruzzo",
                    "Tema": "Lavoro",
                    "Indicatore": "Tasso di disoccupazione",
                    "UDM": "percentuale",
                    "Fonte": "Istat",
                    "Archivio": "BDTPS",
                    "Anno": "2024",
                    "Livello/Variazione": "Livello",
                    "Dato": "7,1",
                    "Benchmark": "",
                    "Area": "Regione",
                },
                {
                    "idIndicatore": "910",
                    "Territorio": "Abruzzo",
                    "Tema": "Salute",
                    "Indicatore": "Speranza di vita alla nascita",
                    "UDM": "anni",
                    "Fonte": "Istat",
                    "Archivio": "Indicatori demografici Istat",
                    "Anno": "2025",
                    "Livello/Variazione": "Livello",
                    "Dato": "83,7",
                    "Benchmark": "",
                    "Area": "Regione",
                },
            ]
            write_atomic(rows, path)
            preserved = read_preserved_rows(path, {"12"})
        self.assertEqual(len(preserved), 1)
        self.assertEqual(preserved[0]["idIndicatore"], "910")
        self.assertEqual(list(preserved[0]), OUTPUT_COLUMNS)


if __name__ == "__main__":
    unittest.main()
