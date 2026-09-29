"""Test unitari per scripts/orca_review.py e scripts/orca_clean.py."""
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from scripts import orca_clean, orca_review


class OrcaReviewAndCleanTest(unittest.TestCase):
    def test_review_dry_run_executes(self):
        res = orca_review.run_review(slug="105-test-slug", issue_id=105, dry_run=True)
        self.assertEqual(res, 0)

    def test_clean_dry_run_executes(self):
        res = orca_clean.run_clean(slug="105-test-slug", dry_run=True)
        self.assertEqual(res, 0)

    def _corpo_dry_run(self, **kwargs) -> str:
        """Corpo della PR come lo stampa `--dry-run`, con un worktree finto."""
        with tempfile.TemporaryDirectory() as tmp:
            worktree = Path(tmp) / "prova-2"
            worktree.mkdir()
            (worktree / "TASK.md").write_text("Testo della issue\n", encoding="utf-8")

            output = io.StringIO()
            with (
                mock.patch.object(
                    orca_review,
                    "_dry_run_identity",
                    return_value=(worktree, "nmaiese/prova-2"),
                ),
                redirect_stdout(output),
            ):
                code = orca_review.run_review(
                    "prova", issue_id=42, dry_run=True, **kwargs
                )
        self.assertEqual(code, 0)
        return output.getvalue().split("--- Corpo PR ---\n", 1)[1].rsplit(
            "----------------", 1
        )[0]

    def test_agent_id_firma_il_corpo(self):
        """Con `AGENT_ID` valorizzata la riga di firma chiude il corpo."""
        with mock.patch.dict(os.environ, {"AGENT_ID": "codex-gpt-5.6-sol"}):
            corpo = self._corpo_dry_run()
        self.assertTrue(corpo.rstrip().endswith("— codex-gpt-5.6-sol"), corpo)

    def test_firma_prevale_su_agent_id(self):
        """`--firma` vince su `AGENT_ID`: l'agente dichiarato al comando è l'ultima parola."""
        with mock.patch.dict(os.environ, {"AGENT_ID": "codex-gpt-5.6-sol"}):
            corpo = self._corpo_dry_run(firma="claude-sonnet-4.5")
        self.assertTrue(corpo.rstrip().endswith("— claude-sonnet-4.5"), corpo)
        self.assertNotIn("codex-gpt-5.6-sol", corpo)

    def test_senza_firma_il_corpo_resta_come_prima(self):
        """Né `--firma` né `AGENT_ID`: il corpo è identico a quello di oggi."""
        with mock.patch.dict(os.environ):
            os.environ.pop("AGENT_ID", None)
            corpo = self._corpo_dry_run()
        self.assertEqual(corpo, "Testo della issue\n\nCloses #42\n")
        self.assertNotIn("—", corpo)


if __name__ == "__main__":
    unittest.main()
