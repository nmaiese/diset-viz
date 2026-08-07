"""La guardia delle definizioni contro il **catalogo committato**.

Sta in `integration/` per la regola di `CLAUDE.md`: legge il CSV delle
definizioni su disco e tutti gli articoli pubblicati. Il comportamento lessicale
della guardia (che cosa conta come termine, che cosa no) e' sintetico e resta in
`tests/unit/test_definition_check.py`.

Il test che conta davvero e' `test_every_committed_article_has_a_source_definition`:
finche' e' verde, nessun articolo cita una definizione che la fonte non ha
scritto. E' un invariante sul catalogo, non sulla funzione, quindi non puo' che
girare sul catalogo.
"""

from __future__ import annotations

import csv
import io
import tempfile
import unittest
from pathlib import Path

from scripts import (
    definition_check,
    fetch_definitions,
    fetch_federated_definitions,
    prose_lint,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class AgainstTheRealCatalogue(unittest.TestCase):
    """Anchors on committed data; the lexical behavior stays synthetic."""

    @classmethod
    def setUpClass(cls):
        cls.definitions = fetch_definitions.load_definitions()

    def test_the_committed_csv_exists_and_carries_the_declared_columns(self):
        self.assertTrue(fetch_definitions.OUTPUT_PATH.exists(),
                        "run python3 scripts/fetch_definitions.py")
        with fetch_definitions.OUTPUT_PATH.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=";")
            self.assertEqual(reader.fieldnames, fetch_definitions.COLUMNS)

        self.assertTrue(fetch_definitions.FEDERATED_OUTPUT_PATH.exists(),
                        "run python3 scripts/fetch_federated_definitions.py")
        with fetch_definitions.FEDERATED_OUTPUT_PATH.open(
            encoding="utf-8", newline=""
        ) as handle:
            reader = csv.DictReader(handle, delimiter=";")
            self.assertEqual(
                reader.fieldnames, fetch_federated_definitions.FEDERATED_COLUMNS
            )

    def test_the_two_archives_have_disjoint_ids(self):
        native = fetch_definitions._load_csv(fetch_definitions.OUTPUT_PATH)
        federated = fetch_definitions._load_csv(
            fetch_definitions.FEDERATED_OUTPUT_PATH
        )
        self.assertEqual(set(native) & set(federated), set())

    def test_it_covers_most_of_the_territorial_archive(self):
        """A join that silently stops matching is the failure mode here.

        The uncovered ids are real: locally curated series (the 9xx block) and
        rows Istat has dropped from the sheet. What must not happen is the
        coverage falling off a cliff because the padding, the float suffix or
        the header lookup changed under us.
        """
        archive = PROJECT_ROOT / "app" / "static" / "data" / "Assoluti_Regione.csv"
        with archive.open(encoding="utf-8", newline="") as handle:
            ids = {row["idIndicatore"] for row in csv.DictReader(handle, delimiter=";")}
        covered = ids & set(self.definitions)
        self.assertGreater(len(covered) / len(ids), 0.85, "the join has come apart")

    def test_the_source_still_defines_imprenditorialita_femminile_the_narrow_way(self):
        """The one definition this whole guard was built around.

        If Istat ever broadens it to all female-led firms, the article that says
        so stops being wrong and this test is the place that finds out.
        """
        row = self.definitions.get("402")
        self.assertIsNotNone(row, "id 402 is not in the definitions CSV")
        self.assertIn("titolari di imprese individuali", row["definizione"].lower())

    def test_every_committed_article_has_a_source_definition(self):
        uncovered = sorted(
            code for code in prose_lint.load_texts()
            if definition_check.official_id(code) not in self.definitions
        )
        self.assertEqual(uncovered, [])

    def test_federated_definitions_keep_the_decisive_source_details(self):
        expected_fragments = {
            "76": "totale delle famiglie",
            "bes:01SAL002": "salute percepita",
            "bes:10AMB001P": "centraline fisse",
            "multiscopo:MULTI_REDD_MEDIANO": "fitti imputati",
            "dem:OLDAGEDEPR": "65",
            "eur:rd_p_persreg": "equivalenti a tempo pieno",
        }
        for key, fragment in expected_fragments.items():
            with self.subTest(key=key):
                self.assertIn(
                    fragment,
                    self.definitions[key]["definizione"].lower(),
                )


if __name__ == "__main__":
    unittest.main()
