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

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "app" / "static" / "data" / "Assoluti_Regione.csv"

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


# Two indicators that publish the same numbers under two names, known and
# tolerated because the duplication is Istat's and not ours. Each entry carries
# the evidence, so a future reader can check whether it is still true rather
# than trusting a list.
KNOWN_DUPLICATE_SERIES = {
    ("167", "471"): (
        "Istat pubblica 167 'Intensità di accumulazione del capitalè "
        "(dati di base: investimenti fissi lordi) e 471 'Investimenti privati "
        "sul PIL' (dati di base: investimenti privati) con valori identici su "
        "tutte e 986 le righe dell'archivio, non solo sulle venti regioni. "
        "I due elenchi di dati di base sono diversi, quindi al massimo una "
        "delle due etichette descrive i numeri pubblicati. Verificato "
        "scaricando Archivio_unico_indicatori_regionali.zip il 27 luglio 2026: "
        "la duplicazione è a monte e un refresh non la toglie."
    ),
}


class NoTwoIndicatorsPublishTheSameSeries(unittest.TestCase):
    """Two pages, two names, one set of numbers: at least one of them lies.

    This is not a hypothetical. `ter-167` and `ter-471` carry byte-identical
    series over 29 years and 20 regions, both have a published article, and one
    of the two is signed off by a reviewer. Every guard in the repo passed them,
    because each page is internally consistent: the figures match the series,
    they just match the *wrong* series.

    It was found by hand, while a verifier was checking something else, and it
    is the cheapest defect in the catalogue to detect and the most expensive to
    notice. One pair in 393 indicators, so an exact-match test costs nothing and
    fires almost never, which is exactly the profile a hard guard should have.
    """

    def test_no_unknown_duplicate_series(self):
        by_indicator = {}
        names = {}
        with DATA_PATH.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter=";"):
                key = row["idIndicatore"]
                by_indicator.setdefault(key, {})[(row["Territorio"], row["Anno"])] = row["Dato"]
                names[key] = row["Indicatore"]

        signatures = {}
        for indicator, cells in by_indicator.items():
            # A handful of shared points is a coincidence, a whole series is not.
            if len(cells) < 20:
                continue
            signatures.setdefault(tuple(sorted(cells.items())), []).append(indicator)

        found = {
            tuple(sorted(group, key=int)) for group in signatures.values() if len(group) > 1
        }
        unknown = sorted(found - set(KNOWN_DUPLICATE_SERIES))
        self.assertEqual(
            unknown, [],
            "indicatori diversi con la stessa identica serie: "
            + "; ".join(
                " == ".join(f"{i} {names[i]}" for i in group) for group in unknown
            ),
        )

    def test_the_known_duplicate_is_still_duplicated(self):
        """An allow-list nobody rechecks is a way of forgetting.

        When Istat fixes the archive, the pair stops matching and this fails,
        which is the notice to delete the entry and to reread both articles.
        """
        with DATA_PATH.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter=";"))
        for group in KNOWN_DUPLICATE_SERIES:
            series = [
                {(r["Territorio"], r["Anno"]): r["Dato"] for r in rows
                 if r["idIndicatore"] == indicator}
                for indicator in group
            ]
            self.assertTrue(all(series), f"{group}: uno dei due id non è più nel CSV")
            for other in series[1:]:
                self.assertEqual(
                    series[0], other,
                    f"{group} non sono più identici: togli la voce da "
                    "KNOWN_DUPLICATE_SERIES e rimanda i due articoli in rilettura",
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
