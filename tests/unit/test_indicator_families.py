"""config/indicator_families.csv è un file curato, come
config/theme_categories.csv: nessuno lo rigenera in automatico a ogni
aggiornamento dati (deciso il 4 settembre notte, docs/FAMIGLIE_INDICATORI.md
punto aperto 2). Questi test girano sul file committato, cioè su quello che
la sessione che l'ha scritto ha rivisto davvero, non su un fixture.

Che cosa può andare storto senza che niente si rompa in modo rumoroso:

1. Un id che finisce in due famiglie diverse: la pagina indicatore non
   saprebbe più dire di quale famiglia far parte quell'id.
2. Due righe della stessa famiglia con lo stesso valore (due "maschi"):
   il selettore di dimensione non saprebbe quale delle due mostrare.
3. Un valore fuori da {maschi, femmine, totale}: rimasto da un refuso o da
   una dimensione nuova non ancora gestita da nessun consumatore.

Non testa BES: un indicatore BES ha un solo id con la dimensione già in una
colonna della fonte (docs/FAMIGLIE_INDICATORI.md sezione 3), non una
famiglia di id da collegare, quindi questo file non lo riguarda.
"""

import csv
import unittest
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = PROJECT_ROOT / "config" / "indicator_families.csv"

REQUIRED_COLUMNS = {
    "family_key", "source", "indicator_id", "dimension", "value",
    "added_by", "added_at", "note",
}
KNOWN_VALUES = {"maschi", "femmine", "totale"}


def rows():
    with CSV_PATH.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


class IndicatorFamiliesFile(unittest.TestCase):
    """Gira su config/indicator_families.csv committato."""

    def setUp(self):
        self.rows = rows()

    def test_there_is_something_to_check(self):
        self.assertTrue(self.rows, "config/indicator_families.csv è vuoto")

    def test_no_required_column_is_missing(self):
        for row in self.rows:
            for column in REQUIRED_COLUMNS:
                self.assertTrue(
                    (row.get(column) or "").strip(),
                    f"riga con indicator_id={row.get('indicator_id')!r} non "
                    f"ha '{column}'",
                )

    def test_values_are_known(self):
        for row in self.rows:
            self.assertIn(
                row["value"], KNOWN_VALUES,
                f"valore {row['value']!r} sconosciuto per indicator_id="
                f"{row['indicator_id']!r} (famiglia {row['family_key']!r})",
            )

    def test_no_indicator_id_in_two_families(self):
        family_by_id = {}
        for row in self.rows:
            key = (row["source"], row["indicator_id"])
            if key in family_by_id:
                self.fail(
                    f"indicator_id={row['indicator_id']!r} (source="
                    f"{row['source']!r}) compare sia in "
                    f"{family_by_id[key]!r} che in {row['family_key']!r}"
                )
            family_by_id[key] = row["family_key"]

    def test_every_family_has_at_least_two_members_and_no_duplicate_value(self):
        members = defaultdict(list)
        for row in self.rows:
            members[row["family_key"]].append(row)
        for family_key, family_rows in members.items():
            self.assertGreaterEqual(
                len(family_rows), 2,
                f"famiglia {family_key!r} ha un solo membro: non è una famiglia",
            )
            values = [row["value"] for row in family_rows]
            self.assertEqual(
                len(values), len(set(values)),
                f"famiglia {family_key!r} ha un valore ripetuto: {values}",
            )

    def test_at_least_the_families_mapped_on_4_september(self):
        """Non un tetto: una soglia sotto la quale il file ha perso righe.

        30 famiglie/89 righe è il numero verificato il 4 settembre notte
        (analisi/audit_famiglie_fonti.py in nmaiese/redazione-ai, incrociato
        con DESCRIZIONE_ASSE_QCS). Curare il file può solo aggiungere o
        correggere famiglie, mai farne sparire senza che qualcuno se ne
        accorga qui.
        """
        family_keys = {row["family_key"] for row in self.rows}
        self.assertGreaterEqual(len(family_keys), 30)
        self.assertGreaterEqual(len(self.rows), 89)


if __name__ == "__main__":
    unittest.main()
