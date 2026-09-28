"""Test unitari per scripts/orca_review.py e scripts/orca_clean.py."""
import io
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


def _corpo_dry_run(tmp_path: Path, monkeypatch, **kwargs) -> str:
    """Corpo della PR come lo stampa `--dry-run`, con un worktree finto."""
    worktree = tmp_path / "prova-2"
    worktree.mkdir()
    (worktree / "TASK.md").write_text("Testo della issue\n", encoding="utf-8")

    output = io.StringIO()
    with (
        mock.patch.object(
            orca_review, "_dry_run_identity", return_value=(worktree, "nmaiese/prova-2")
        ),
        redirect_stdout(output),
    ):
        code = orca_review.run_review("prova", issue_id=42, dry_run=True, **kwargs)
    assert code == 0
    return output.getvalue().split("--- Corpo PR ---\n", 1)[1].rsplit("----------------", 1)[0]


def test_agent_id_firma_il_corpo(tmp_path, monkeypatch):
    """Con `AGENT_ID` valorizzata la riga di firma chiude il corpo."""
    monkeypatch.setenv("AGENT_ID", "codex-gpt-5.6-sol")
    corpo = _corpo_dry_run(tmp_path, monkeypatch)
    assert corpo.rstrip().endswith("— codex-gpt-5.6-sol")


def test_firma_prevale_su_agent_id(tmp_path, monkeypatch):
    """`--firma` vince su `AGENT_ID`: l'agente dichiarato al comando è l'ultima parola."""
    monkeypatch.setenv("AGENT_ID", "codex-gpt-5.6-sol")
    corpo = _corpo_dry_run(tmp_path, monkeypatch, firma="claude-sonnet-4.5")
    assert corpo.rstrip().endswith("— claude-sonnet-4.5")
    assert "codex-gpt-5.6-sol" not in corpo


def test_senza_firma_il_corpo_resta_come_prima(tmp_path, monkeypatch):
    """Né `--firma` né `AGENT_ID`: il corpo è identico a quello di oggi."""
    monkeypatch.delenv("AGENT_ID", raising=False)
    corpo = _corpo_dry_run(tmp_path, monkeypatch)
    assert corpo == "Testo della issue\n\nCloses #42\n"
    assert "—" not in corpo


if __name__ == "__main__":
    unittest.main()
