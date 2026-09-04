import io
import unittest
import zipfile

from openpyxl import Workbook

from scripts.update_bes_regions import parse_archive, parse_archive_by_sex
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


class BesRegionalSessoRefreshTest(unittest.TestCase):
    """parse_archive_by_sex non deve toccare il comportamento di
    parse_archive sopra (test separato, fixture separata): la stessa fonte
    letta due modi diversi, uno scarta Maschi/Femmine, l'altro no."""

    def _fixture_zip(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append([
            "DOMINIO", "CODICE", "INDICATORE", "SESSO", "TERRITORIO",
            "UNITA_MISURA", "FONTE", 2025, "NOTA",
        ])
        regions = sorted(SUPPORTED_REGIONS)
        # 01SAL001: copertura piena su Totale/Maschi/Femmine, tutte e 20 le regioni.
        for region in regions:
            for sesso in ("Totale", "Maschi", "Femmine"):
                sheet.append([
                    "Salute", "01SAL001", "Speranza di vita alla nascita", sesso,
                    region, "Numero medio di anni", "Istat", "80,0", "",
                ])
        # 10LAV001: Totale pieno, ma Maschi solo in due regioni: non e' copertura
        # completa anche se l'id "ha" righe Maschi (lo stesso bug del conteggio
        # 84 vs 65 in nmaiese/diset-viz#216, ora impedito da un test).
        for region in regions:
            sheet.append([
                "Lavoro", "10LAV001", "Tasso di occupazione", "Totale",
                region, "Percentuale", "Istat", "60,0", "",
            ])
        for region in regions[:2]:
            sheet.append([
                "Lavoro", "10LAV001", "Tasso di occupazione", "Maschi",
                region, "Percentuale", "Istat", "65,0", "",
            ])
        # Un aggregato non regionale non deve mai entrare, come sopra.
        sheet.append([
            "Salute", "01SAL001", "Speranza di vita alla nascita", "Totale",
            "Italia", "Numero medio di anni", "Istat", "81,0", "",
        ])
        xlsx = io.BytesIO()
        workbook.save(xlsx)
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("APPENDICE/indicatori_regione_sesso.xlsx", xlsx.getvalue())
        return archive.getvalue()

    def test_keeps_every_sesso_and_flags_full_coverage_per_indicator(self):
        dataset, manifest = parse_archive_by_sex(self._fixture_zip())

        # 20 regioni x 3 sesso per 01SAL001, 20 Totale + 2 Maschi per 10LAV001.
        self.assertEqual(len(dataset), 20 * 3 + 20 + 2)
        self.assertTrue(all("Sesso" in row for row in dataset))
        self.assertEqual(
            {row["Territorio"] for row in dataset if row["idIndicatore"] == "01SAL001"},
            SUPPORTED_REGIONS,
        )

        manifest_by_id = {row["id"]: row for row in manifest}
        self.assertEqual(set(manifest_by_id), {"01SAL001", "10LAV001"})

        full = manifest_by_id["01SAL001"]
        self.assertTrue(full["full_gender_coverage"])
        self.assertEqual(full["n_region_totale"], 20)
        self.assertEqual(full["n_region_maschi"], 20)
        self.assertEqual(full["n_region_femmine"], 20)
        self.assertEqual(full["coverage_maschi"], 1.0)

        partial = manifest_by_id["10LAV001"]
        self.assertFalse(partial["full_gender_coverage"])
        self.assertEqual(partial["n_region_totale"], 20)
        self.assertEqual(partial["n_region_maschi"], 2)
        self.assertEqual(partial["n_region_femmine"], 0)
        self.assertEqual(partial["coverage_maschi"], 0.1)

    def test_parse_archive_is_unaffected(self):
        """La stessa fonte, letta con parse_archive, si comporta come prima:
        solo Totale, 10LAV001 incluso con le sue 20 righe regionali."""
        dataset, manifest = parse_archive(self._fixture_zip())
        self.assertEqual({row["idIndicatore"] for row in dataset}, {"01SAL001", "10LAV001"})
        self.assertTrue(all("Sesso" not in row for row in dataset))


if __name__ == "__main__":
    unittest.main()
