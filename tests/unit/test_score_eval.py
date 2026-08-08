"""Il falso negativo del 2026-08-06 (CANARY.md): `score_reviewer` contava un
errore piantato come sopravvissuto anche quando compariva solo dentro una
confutazione esplicita ("Non è X: ..."), perché il match era una sola
sottostringa. Rilievo Codex: lo scorer va corretto e riprovato, non solo
annotato come limite noto.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "evals"))

import score_eval  # noqa: E402


def _score(text, pattern="quota di donne sul totale degli occupati"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_root = Path(tmp_dir)
        expected_path = tmp_root / "expected.json"
        expected_path.write_text(json.dumps({
            "errors": [{"id": "e01", "file": "article.json", "class": "definizione", "pattern": pattern}],
        }), encoding="utf-8")
        (tmp_root / "article.json").write_text(
            json.dumps({"lead": text, "sections": []}), encoding="utf-8")
        return score_eval.score_reviewer(tmp_root, expected_path=expected_path)


class ANegatedPatternIsACorrectionNotASurvival(unittest.TestCase):
    def test_an_unqualified_survivor_is_still_missed(self):
        result = _score("La quota di donne sul totale degli occupati è alta.")
        self.assertEqual(result["mancati"], ["e01"])
        self.assertEqual(result["trovati"], [])

    def test_an_explicit_refutation_counts_as_found(self):
        result = _score(
            "Non è la quota di donne sul totale degli occupati: al denominatore "
            "c'è la popolazione femminile."
        )
        self.assertEqual(result["trovati"], ["e01"])
        self.assertEqual(result["mancati"], [])

    def test_the_accented_negation_cue_is_recognized_too(self):
        result = _score(
            "Non è la quota di donne sul totale degli occupati: altro."
        )
        self.assertEqual(result["trovati"], ["e01"])

    def test_a_pattern_absent_entirely_is_found(self):
        result = _score("Un testo che non nomina affatto l'errore piantato.")
        self.assertEqual(result["trovati"], ["e01"])

    def test_one_bare_occurrence_among_negated_ones_is_still_missed(self):
        """Una sola comparsa non confutata basta a considerare l'errore vivo:
        la tolleranza vale caso per caso, non per il testo intero."""
        result = _score(
            "Non è la quota di donne sul totale degli occupati. Ma poi il "
            "testo scrive di nuovo la quota di donne sul totale degli occupati "
            "come se fosse vera."
        )
        self.assertEqual(result["mancati"], ["e01"])


if __name__ == "__main__":
    unittest.main()
