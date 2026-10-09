import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.figure_contract import missing_fields, visible_svg_fields
from app.design.pages import articolo
from scripts import figure_g5
from scripts.trend_articles import figures


VALID = dict(title="Confronto territoriale", subtitle="Tasso (unità: %; denominatore: residenti) · 20-64 anni · regioni · 2024",
             axis_labels=("Tasso (%)",), source="Fonte: Istat, BES. Release: 2025-09. Elaborazione Divario Italia.")


class FigureG5Test(unittest.TestCase):
    def test_each_missing_public_field_is_reported(self):
        self.assertEqual(missing_fields(**VALID), [])
        cases = (("title", "", "titolo"), ("subtitle", "Tasso (unità: %; denominatore: residenti) · 20-64 anni · regioni", "periodo"),
                 ("subtitle", "Tasso (unità: %; denominatore: residenti) · 20-64 anni ·  · 2024", "territorio"),
                 ("subtitle", "Tasso (unità: %; denominatore: residenti) ·  · regioni · 2024", "popolazione"),
                 ("subtitle", " · 20-64 anni · regioni · 2024", "misura"),
                 ("subtitle", "Tasso (denominatore: residenti) · 20-64 anni · regioni · 2024", "unità"),
                 ("subtitle", "Tasso (unità: %) · 20-64 anni · regioni · 2024", "denominatore"),
                 ("axis_labels", ("valore",), "asse"), ("source", "Release: 2025", "fonte"),
                 ("source", "Fonte: Istat, BES.", "release"))
        for key, value, field in cases:
            with self.subTest(field=field):
                self.assertIn(field, missing_fields(**{**VALID, key: value}))

    def test_trend_cli_validates_visible_svg_before_writing(self):
        entry = {"meta": {"name": "Tasso", "unit": "%", "source": "Istat", "archive": "BES",
                          "years": [2023, 2024], "decimals": 1}, "last_year": 2024,
                 "series": {"Lazio": {"2024": 2.0}, "Sicilia": {"2024": 1.0}},
                 "means": {"2024": {"simple_mean": 1.5}}}
        with tempfile.TemporaryDirectory() as directory, patch.object(figures, "_dossier_entry", return_value=entry), \
                patch.object(figures.common, "FIGURES_DIR", Path(directory)), \
                patch.object(figures.common, "ROOT", Path(directory)):
            args = ["pezzo", "bars", "bes:x", "--name", "figura", "--title", "Titolo",
                    "--population", "20-64 anni", "--territory", "regioni", "--denominator", "residenti",
                    "--dataset", "BES", "--release", "2025-09"]
            self.assertEqual(figures.main(args), 0)
            output = (Path(directory) / "pezzo" / "figura.svg").read_text()
            self.assertEqual(missing_fields(**visible_svg_fields(output)), [])
            self.assertIn("residenti", output)
            rendered = articolo._figure(output)
            self.assertIn("20-64 anni", rendered)
            self.assertIn("Release: 2025-09", rendered)
            with self.assertRaises(SystemExit):
                figures.main([*args[:-1], ""])

    def test_indicator_component_sweep_reads_public_caption(self):
        html = ('<figure class="module"><figcaption class="module__head">'
                '<h3 class="h-sub">Distribuzione</h3><p class="subline">Tasso (unità: %; denominatore: residenti) · adulti · province · 2024</p>'
                '</figcaption><p class="source">Fonte: Istat, BES. Release: 2025-09.</p></figure>')
        self.assertEqual(figure_g5.page_findings(html), [])
        self.assertEqual(figure_g5.page_findings(html.replace("Release: 2025-09.", ""))[0][1], ["release"])
        self.assertIn("asse", figure_g5.page_findings(html.replace(
            '</figcaption>', '</figcaption><svg><text>Valore</text></svg>'))[0][1])

    def test_rendered_indicator_component_reports_missing_release(self):
        from app import app, sources

        response = app.test_client().get(sources.indicator_url("territorial", "920", "x"),
                                         follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        findings = figure_g5.page_findings(response.get_data(as_text=True))
        self.assertTrue(findings)
        self.assertTrue(any("release" in fields for _, fields in findings))


if __name__ == "__main__":
    unittest.main()
