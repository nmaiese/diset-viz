import io
import unittest
import zipfile

from openpyxl import Workbook

from scripts.update_bes_regions import parse_archive
from scripts.update_data import SUPPORTED_REGIONS


class BesRegionalRefreshTest(unittest.TestCase):
    def _fixture_zip(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append([
            "DOMINIO", "CODICE", "INDICATORE", "SESSO", "TERRITORIO",
            "UNITA_MISURA", "FONTE", 2024, 2025, "NOTA",
        ])
        for index, region in enumerate(sorted(SUPPORTED_REGIONS), start=1):
            sheet.append([
                "Salute", "01SAL001", "Speranza di vita alla nascita", "Totale",
                region, "Numero medio di anni", "Istat", "80,0", f"{80 + index / 10:.1f}".replace(".", ","), "",
            ])
        # A gender detail and a non-regional aggregate must never enter output.
        sheet.append([
            "Salute", "01SAL001", "Speranza di vita alla nascita", "Maschi",
            "Piemonte", "Numero medio di anni", "Istat", "78,0", "79,0", "",
        ])
        sheet.append([
            "Salute", "01SAL001", "Speranza di vita alla nascita", "Totale",
            "Italia", "Numero medio di anni", "Istat", "81,0", "82,0", "",
        ])
        xlsx = io.BytesIO()
        workbook.save(xlsx)
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("APPENDICE/indicatori_regione_sesso.xlsx", xlsx.getvalue())
        return archive.getvalue()

    def test_parser_keeps_total_rows_and_builds_auditable_manifest(self):
        dataset, manifest = parse_archive(self._fixture_zip())
        self.assertEqual(len(dataset), 40)
        self.assertEqual({row["Territorio"] for row in dataset}, SUPPORTED_REGIONS)
        self.assertEqual(len(manifest), 1)
        item = manifest[0]
        self.assertEqual(item["id"], "01SAL001")
        self.assertEqual(item["year_max"], 2025)
        self.assertEqual(item["coverage_latest"], 1.0)
        self.assertEqual(item["proposed_category"], "salute_cura")
        self.assertEqual(item["proposed_direction"], "higher_better")


if __name__ == "__main__":
    unittest.main()
