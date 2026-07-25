"""Data-quality guards on the committed territorial dataset.

A bounded rate is a share of a reference population or labour force, so it cannot
exceed 100. The Istat archive we mirror (`update_data.py`) once shipped
`328,803168570214` for one cell (id 476, Trentino-Alto Adige, 2022) and that
impossible value reached the atlas. This guard catches that class of upstream
corruption on any future refresh, before it ships.

Deliberately scoped to the employment/unemployment/activity families: a
`Tasso di partecipazione nell'istruzione` is a gross enrolment ratio that
legitimately exceeds 100, so it is not a bounded rate and is excluded.
"""

import csv
import unittest
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "app" / "static" / "data" / "Assoluti_Regione.csv"

BOUNDED_RATE_PREFIXES = (
    "Tasso di occupazione",
    "Tasso di disoccupazione",
    "Tasso di attività",
)


def _parse(value):
    value = (value or "").strip().replace(".", "").replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return None


class BoundedRatesStayWithinRange(unittest.TestCase):
    def test_no_employment_family_rate_exceeds_100(self):
        offenders = []
        with DATA_PATH.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter=";"):
                if row["UDM"] != "percentuale":
                    continue
                if not row["Indicatore"].startswith(BOUNDED_RATE_PREFIXES):
                    continue
                value = _parse(row["Dato"])
                if value is not None and value > 100:
                    offenders.append(
                        (row["idIndicatore"], row["Indicatore"], row["Territorio"], row["Anno"], row["Dato"])
                    )
        self.assertEqual(
            offenders, [],
            "bounded rates (occupazione/disoccupazione/attività) over 100 are impossible "
            f"and signal upstream corruption: {offenders[:10]}",
        )


class KnownArchiveCorrectionHealsOnRefresh(unittest.TestCase):
    """`update_data.convert_row` heals the known-bad upstream cell during a refresh,
    but only while the archive still ships the exact bad value."""

    def _archive_row(self, valore):
        # Minimal set of columns convert_row reads, for id 476 / Trentino / 2022.
        return {
            "DESCRIZIONE_RIPARTIZIONE": "Trentino-Alto Adige/Südtirol",
            "DESCRIZIONE_TEMA1": "Lavoro",
            "OC_TEMA_SINTETICO": "Lavoro",
            "SOTTOTITOLO": "Occupazione",
            " 1° OBIETTIVO": "",
            "COD_INDICATORE": "476",
            "TITOLO": "Tasso di occupazione giovanile (femmine)",
            "UNITA_MISURA": "percentuale",
            "ANNO_RIFERIMENTO": "2022",
            "VALORE": valore,
        }

    def test_bad_value_is_healed(self):
        from scripts import update_data
        out = update_data.convert_row(self._archive_row("328,803168570214"))
        self.assertEqual(out["Dato"], "43,16288")

    def test_other_value_is_left_untouched(self):
        from scripts import update_data
        # If Istat fixes the archive, we keep their value rather than force ours.
        out = update_data.convert_row(self._archive_row("42,9"))
        self.assertEqual(out["Dato"], "42,9")


if __name__ == "__main__":
    unittest.main()
