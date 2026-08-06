"""La fixture di una eval non deve regalare la risposta.

Il gold del reader-editor nomina i casi per verdetto (`p01`-`p04` sono i `pass`,
`r01`-`rc04` i `revise`), che e' comodo per chi legge il gold e fatale per chi
misura: un giudice che vede quegli id prende 8/8 senza leggere una riga di prosa,
e una baseline centrabile cosi' non vede piu' nessuna regressione. E' gia'
successo una volta su questa eval, con il blocco `_` che descriveva i casi.
"""

import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "evals"))

import run_eval  # noqa: E402
import score_eval  # noqa: E402


class TheReaderEditorFixtureIsBlind(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gold = json.loads(
            (PROJECT_ROOT / "evals" / "reader-editor" / "cases.json").read_text(encoding="utf-8"))
        cls.prepared = json.loads(
            (run_eval.prepare("reader-editor") / "cases.json").read_text(encoding="utf-8"))

    def test_the_case_carries_prose_and_nothing_that_answers_for_it(self):
        for case in self.prepared["cases"]:
            self.assertEqual(set(case), {"id", "prose", "verdict"})
            self.assertEqual(case["verdict"], "")
        self.assertNotIn("_", self.prepared)

    def test_no_id_of_the_gold_survives_into_the_fixture(self):
        gold_ids = {case["id"] for case in self.gold["cases"]}
        prepared_ids = {case["id"] for case in self.prepared["cases"]}
        self.assertEqual(gold_ids & prepared_ids, set())
        self.assertEqual(len(prepared_ids), len(gold_ids))

    def test_the_order_does_not_answer_either(self):
        """In fila i quattro pass e poi i quattro revise sarebbe la stessa
        risposta travestita da posizione."""
        by_gold_id = {score_eval.blind_id(c["id"]): c["label"] for c in self.gold["cases"]}
        order = [by_gold_id[case["id"]] for case in self.prepared["cases"]]
        self.assertNotEqual(order, sorted(order))

    def test_the_scorer_finds_the_cases_again(self):
        """Cieco per l'agente, non per il metro: se la corrispondenza si rompe la
        eval smette di sommare, e il modo in cui lo direbbe e' un punteggio a
        zero che sembra una regressione del giudizio."""
        import tempfile

        answers = {score_eval.blind_id(c["id"]): c["label"] for c in self.gold["cases"]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "verdetti.json"
            path.write_text(json.dumps(answers), encoding="utf-8")
            result = score_eval.score_reader_editor(path)
        self.assertEqual(result["accuratezza"], f"{len(answers)}/{len(answers)}")

    def test_a_baseline_recorded_on_the_old_ids_still_scores(self):
        """La baseline gia' annotata in docs/CANARY.md e' stata prodotta sugli id
        vecchi: riscriverla per un cambio di etichette sarebbe riscrivere una
        misura invece di conservarla."""
        import tempfile

        answers = {c["id"]: c["label"] for c in self.gold["cases"]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "verdetti.json"
            path.write_text(json.dumps(answers), encoding="utf-8")
            result = score_eval.score_reader_editor(path)
        self.assertEqual(result["accuratezza"], f"{len(answers)}/{len(answers)}")


if __name__ == "__main__":
    unittest.main()
