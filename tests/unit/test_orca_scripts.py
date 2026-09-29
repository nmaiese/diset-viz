"""Regressioni per gli helper Orca, senza operazioni reali sui worktree."""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from scripts import orca_clean, orca_dispatch, orca_review


def completed(stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


class DispatchTest(unittest.TestCase):
    def test_help_deriva_dalla_mappa_ruolo_attivita(self):
        output = io.StringIO()
        with self.assertRaises(SystemExit), redirect_stdout(output):
            orca_dispatch.main(["--help"])
        help_text = output.getvalue()
        for role, attivita in orca_dispatch.ROLE_TO_ATTIVITA.items():
            self.assertIn(f"{role}={attivita}", help_text)

    def test_ruolo_sconosciuto_restituisce_uno(self):
        self.assertEqual(orca_dispatch.dispatch_task("prova", "T", "O", role="boh"), 1)


class WorktreeResolutionTest(unittest.TestCase):
    def test_risolve_un_worktree_con_suffisso_numerico(self):
        porcelain = """worktree /repo
HEAD abc
branch refs/heads/master

worktree /repo/.orca/worktrees/divarioitalia/prova-3
HEAD def
branch refs/heads/nmaiese/prova-3
"""
        self.assertEqual(
            orca_review.find_worktree_path(porcelain, "prova"),
            Path("/repo/.orca/worktrees/divarioitalia/prova-3"),
        )


class ReviewTest(unittest.TestCase):
    def test_usa_ramo_reale_task_e_flag_della_draft_pr(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prova-2"
            path.mkdir()
            (path / "TASK.md").write_text("# Task: Prova\n", encoding="utf-8")
            results = [
                completed(),
                completed(stdout="2\n"),
                completed(),
                completed(stdout="https://example.test/pr/1\n"),
            ]
            with (
                mock.patch.object(
                    orca_review,
                    "resolve_worktree",
                    return_value=(path, "nmaiese/prova-2"),
                ),
                mock.patch.object(
                    orca_review, "_run_capture", side_effect=results
                ) as run,
                mock.patch("os.remove") as mock_remove,
            ):
                code = orca_review.run_review("prova", issue_id=42)

        self.assertEqual(code, 0)
        push = run.call_args_list[2].args[0]
        pull_request = run.call_args_list[3].args[0]
        self.assertEqual(push, ["git", "push", "-u", "origin", "nmaiese/prova-2"])
        self.assertIn("--draft", pull_request)
        self.assertEqual(pull_request[pull_request.index("--base") + 1], "master")
        self.assertEqual(
            pull_request[pull_request.index("--head") + 1], "nmaiese/prova-2"
        )
        body_file = pull_request[pull_request.index("--body-file") + 1]
        body = Path(body_file).read_text(encoding="utf-8")
        self.assertIn("# Task: Prova", body)
        self.assertIn("Closes #42", body)


class CleanTest(unittest.TestCase):
    def test_rifiuta_un_worktree_sporco(self):
        path = Path("/repo/.orca/worktrees/divarioitalia/prova-2")
        with (
            mock.patch.object(
                orca_clean,
                "resolve_worktree",
                return_value=(path, "nmaiese/prova-2"),
            ),
            mock.patch.object(
                orca_clean,
                "_run",
                return_value=completed(stdout=" M file.py\n"),
            ) as run,
            mock.patch.object(orca_clean, "_remove_worktree") as remove,
        ):
            code = orca_clean.run_clean("prova")

        self.assertEqual(code, 1)
        run.assert_called_once_with(["git", "status", "--porcelain"], cwd=path)
        remove.assert_not_called()

    def test_forza_il_ramo_solo_se_la_pr_e_fusa(self):
        path = Path("/repo/.orca/worktrees/divarioitalia/prova-2")
        results = [
            completed(),
            completed(stdout='{"ok": true}'),
            completed(stderr="error: branch is not fully merged", returncode=1),
            completed(stdout='{"state": "MERGED"}'),
            completed(),
        ]
        with (
            mock.patch.object(
                orca_clean,
                "resolve_worktree",
                return_value=(path, "nmaiese/prova-2"),
            ),
            mock.patch.object(orca_clean, "get_orca_cmd", return_value="orca-ide"),
            mock.patch.object(orca_clean, "_run", side_effect=results) as run,
        ):
            code = orca_clean.run_clean("prova")

        self.assertEqual(code, 0)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertIn(["git", "branch", "-d", "nmaiese/prova-2"], commands)
        self.assertIn(
            ["gh", "pr", "view", "nmaiese/prova-2", "--json", "state"],
            commands,
        )
        self.assertEqual(commands[-1], ["git", "branch", "-D", "nmaiese/prova-2"])
        self.assertNotIn("-f", commands[1])



@unittest.skipUnless(shutil.which("wslpath"), "serve WSL")
class OrcaPathTest(unittest.TestCase):
    def test_repo_path_diventa_unc(self):
        self.assertTrue(
            orca_dispatch.to_orca_repo_path(Path("/home")).startswith("\\\\")
        )

    def test_percorso_unc_di_orca_torna_wsl(self):
        unc = orca_dispatch.to_orca_repo_path(Path("/home"))
        self.assertEqual(orca_dispatch.from_orca_path(unc), Path("/home"))



class DryRunSenzaOrcaTest(unittest.TestCase):
    """In CI e in Cloud Build orca-ide non c'e': il dry-run deve passare lo stesso."""

    def test_dry_run_non_richiede_il_binario(self):
        with (
            mock.patch.object(
                orca_dispatch, "get_orca_cmd", side_effect=RuntimeError("orca-ide assente")
            ),
            redirect_stdout(io.StringIO()),
        ):
            code = orca_dispatch.dispatch_task("prova", "T", "O", dry_run=True)
        self.assertEqual(code, 0)


class ReviewNuoveOpzioniTest(unittest.TestCase):
    def test_base_usata_in_pr_e_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prova-2"
            path.mkdir()
            (path / "TASK.md").write_text("# Task: Prova\n", encoding="utf-8")
            results = [
                completed(),
                completed(stdout="2\n"),
                completed(),
                completed(stdout="https://example.test/pr/1\n"),
            ]
            with (
                mock.patch.object(
                    orca_review,
                    "resolve_worktree",
                    return_value=(path, "nmaiese/prova-2"),
                ),
                mock.patch.object(
                    orca_review, "_run_capture", side_effect=results
                ) as run,
            ):
                code = orca_review.run_review("prova", issue_id=42, base="develop")

        self.assertEqual(code, 0)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands[1], ["git", "rev-list", "--count", "origin/develop..HEAD"])
        pr_cmd = commands[3]
        self.assertIn("--base", pr_cmd)
        self.assertEqual(pr_cmd[pr_cmd.index("--base") + 1], "develop")

    def test_label_ripetibile_aggiunta_a_pr(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prova-2"
            path.mkdir()
            (path / "TASK.md").write_text("# Task: Prova\n", encoding="utf-8")
            results = [
                completed(),
                completed(stdout="2\n"),
                completed(),
                completed(stdout="https://example.test/pr/1\n"),
            ]
            with (
                mock.patch.object(
                    orca_review,
                    "resolve_worktree",
                    return_value=(path, "nmaiese/prova-2"),
                ),
                mock.patch.object(
                    orca_review, "_run_capture", side_effect=results
                ) as run,
            ):
                code = orca_review.run_review("prova", issue_id=42, labels=["run:team", "infra"])

        self.assertEqual(code, 0)
        pr_cmd = run.call_args_list[3].args[0]
        labels = [pr_cmd[i+1] for i, arg in enumerate(pr_cmd) if arg == "--label"]
        self.assertEqual(labels, ["run:team", "infra"])

    def test_scheda_compone_corpo(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prova-2"
            path.mkdir()
            (path / "TASK.md").write_text("Testo della issue\n", encoding="utf-8")
            fonti_dir = path / "lavoro" / "indicatore_1"
            fonti_dir.mkdir(parents=True)
            (fonti_dir / "fonti.md").write_text("Fonte: ISTAT\n", encoding="utf-8")

            def mock_run(command, cwd=None, **kwargs):
                if command[0:2] == ["git", "rev-parse"]:
                    return completed(stdout="abc123def\n")
                if command[0:2] == ["git", "show"]:
                    return completed(stdout="Vecchio file")
                return completed()

            with (
                mock.patch.object(orca_review, "_run_capture", side_effect=mock_run),
                mock.patch("scripts.indicator_store.filename_for", return_value="indicatore_1.yml", create=True),
                mock.patch("scripts.indicator_store.analizza", return_value={"vecchio": "si"}, create=True),
                mock.patch("scripts.indicator_store.read", return_value={"nuovo": "si"}, create=True),
                mock.patch("scripts.indicator_store.rendi", side_effect=lambda k, entry: "Reso vecchio" if "vecchio" in entry else "Reso nuovo", create=True),
            ):
                body = orca_review._task_body(path, 42, base="develop", scheda="indicatore_1", internal_key="indicatore_1", url_code="indicatore_1")

            self.assertIn("**Commit**: abc123def", body)
            self.assertIn("Testo della issue", body)
            self.assertIn("Closes #42", body)
            self.assertIn("Fonte: ISTAT", body)
            self.assertIn("Reso vecchio", body)
            self.assertIn("Reso nuovo", body)

    def test_scheda_accetta_il_codice_url_e_la_chiave_interna(self):
        """`--scheda` scrive i testi con la chiave interna e legge le fonti dal
        codice dell'URL, quindi `ter-12` e `12` compongono lo stesso corpo."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prova-2"
            path.mkdir()
            (path / "TASK.md").write_text("Testo della issue\n", encoding="utf-8")
            fonti_dir = path / "lavoro" / "ter-12"
            fonti_dir.mkdir(parents=True)
            (fonti_dir / "fonti.md").write_text("Fonte: ISTAT\n", encoding="utf-8")

            def mock_run(command, cwd=None, **kwargs):
                if command[0:2] == ["git", "rev-parse"]:
                    return completed(stdout="abc123def\n")
                if command[0:2] == ["git", "show"]:
                    return completed(stdout="Vecchio file")
                return completed()

            def mock_rendi(key, entry):
                return f"Reso {key}: " + ("vecchio" if "vecchio" in entry else "nuovo")

            corpi = {}
            for scheda in ("ter-12", "12"):
                output = io.StringIO()
                with (
                    mock.patch.object(orca_review, "_dry_run_identity", return_value=(path, "nmaiese/prova-2")),
                    mock.patch.object(orca_review, "_run_capture", side_effect=mock_run),
                    mock.patch("scripts.indicator_store.filename_for", return_value="12.yml", create=True),
                    mock.patch("scripts.indicator_store.analizza", return_value={"vecchio": "si"}, create=True),
                    mock.patch("scripts.indicator_store.read", return_value={"nuovo": "si"}, create=True),
                    mock.patch("scripts.indicator_store.rendi", side_effect=mock_rendi, create=True),
                    redirect_stdout(output),
                ):
                    code = orca_review.run_review("prova", issue_id=42, dry_run=True, scheda=scheda)
                self.assertEqual(code, 0)
                corpi[scheda] = output.getvalue().split("--- Corpo PR ---\n", 1)[1].rsplit("----------------", 1)[0]

            self.assertEqual(corpi["ter-12"], corpi["12"])

        corpo = corpi["ter-12"]
        self.assertIn("### Testo precedente", corpo)
        self.assertIn("Reso 12: vecchio", corpo)
        self.assertIn("### Testo nuovo", corpo)
        self.assertIn("Reso 12: nuovo", corpo)
        self.assertIn("### Fonti nuove", corpo)
        self.assertIn("Fonte: ISTAT", corpo)

    def test_dry_run_stampa_nuove_opzioni(self):
        output = io.StringIO()
        with (
            mock.patch.object(orca_review, "_dry_run_identity", return_value=(Path("/finto"), "nmaiese/finto")),
            redirect_stdout(output)
        ):
            code = orca_review.run_review("finto", issue_id=42, dry_run=True, base="develop", labels=["run:team"])

        self.assertEqual(code, 0)
        out = output.getvalue()
        self.assertIn("gh pr create", out)
        self.assertIn("--base develop", out)
        self.assertIn("--label run:team", out)
        self.assertIn("<corpo-della-pr>", out)

    def test_dry_run_non_crea_file_temporaneo(self):
        tmp_dir = tempfile.gettempdir()
        before = set(os.listdir(tmp_dir))

        output = io.StringIO()
        with (
            mock.patch.object(orca_review, "_dry_run_identity", return_value=(Path("/finto"), "nmaiese/finto")),
            redirect_stdout(output)
        ):
            orca_review.run_review("finto", issue_id=42, dry_run=True, scheda="indicatore")

        after = set(os.listdir(tmp_dir))
        self.assertEqual(before, after)

    def test_run_rimuove_file_corpo_anche_su_errore(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prova-2"
            path.mkdir()
            results = [
                completed(),
                completed(stdout="2\n"),
                completed(),
                completed(returncode=1, stderr="Errore gh pr create"),
            ]
            tmp_dir = tempfile.gettempdir()
            before = set(os.listdir(tmp_dir))

            with (
                mock.patch.object(orca_review, "resolve_worktree", return_value=(path, "nmaiese/prova-2")),
                mock.patch.object(orca_review, "_run_capture", side_effect=results),
                mock.patch("sys.stderr", new_callable=io.StringIO)
            ):
                code = orca_review.run_review("prova", issue_id=42)

            self.assertEqual(code, 1)
            after = set(os.listdir(tmp_dir))
            self.assertEqual(before, after)

    def test_scheda_invalida_rifiutata(self):
        with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            code = orca_review.run_review("prova", issue_id=42, scheda="../fuori")
            self.assertEqual(code, 1)
            self.assertIn("Chiave scheda non valida", err.getvalue())

        with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            code = orca_review.run_review("prova", issue_id=42, scheda="con / slash")
            self.assertEqual(code, 1)

    def test_scheda_store_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prova-2"
            path.mkdir()

            class DummyStoreError(Exception):
                pass

            with (
                mock.patch.object(orca_review, "resolve_worktree", return_value=(path, "nmaiese/prova-2")),
                mock.patch("scripts.editoriale.brief.resolve", return_value=("fam", "id"), create=True),
                mock.patch("app.sources.internal_id", return_value="errata", create=True),
                mock.patch("app.sources.indicator_code", return_value="errata", create=True),
                mock.patch("scripts.indicator_store.filename_for", side_effect=DummyStoreError("Chiave errata"), create=True),
                mock.patch("scripts.indicator_store.StoreError", DummyStoreError, create=True),
                mock.patch("sys.stderr", new_callable=io.StringIO) as err
            ):
                code = orca_review.run_review("prova", issue_id=42, scheda="errata")

            self.assertEqual(code, 1)
            self.assertIn("Chiave errata", err.getvalue())

    def test_scheda_che_non_risolve_esce_uno_prima_del_worktree(self):
        with (
            mock.patch.object(orca_review, "resolve_worktree", return_value=(Path("/finto"), "nmaiese/finto")) as resolve,
            mock.patch("sys.stderr", new_callable=io.StringIO) as err
        ):
            code = orca_review.run_review("finto", issue_id=42, scheda="ter-99999")

        self.assertEqual(code, 1)
        self.assertIn("[!]", err.getvalue())
        self.assertIn("ter-99999", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())
        resolve.assert_not_called()


if __name__ == "__main__":
    import os
    unittest.main()
