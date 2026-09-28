"""Regressioni per gli helper Orca, senza operazioni reali sui worktree."""

from __future__ import annotations

import io
import json
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
    def test_prompt_e_su_una_sola_riga_e_task_segue_la_create(self):
        with tempfile.TemporaryDirectory() as tmp:
            worktree = Path(tmp) / "prova-2"
            worktree.mkdir()
            payload = json.dumps(
                {
                    "ok": True,
                    "data": {
                        "worktree": {
                            "path": str(worktree),
                            "branch": "nmaiese/prova-2",
                        }
                    },
                }
            )
            with (
                mock.patch.object(orca_dispatch, "get_orca_cmd", return_value="orca-ide"),
                mock.patch.object(
                    orca_dispatch.subprocess,
                    "run",
                    return_value=completed(stdout=payload),
                ) as run,
            ):
                code = orca_dispatch.dispatch_task(
                    "prova", "Titolo\nsu due righe", "Obiettivo\ncompleto"
                )

            self.assertEqual(code, 0)
            command = run.call_args.args[0]
            prompt = command[command.index("--prompt") + 1]
            self.assertNotIn("\n", prompt)
            self.assertIn("# Task: Titolo | su due righe", prompt)
            self.assertIn("R1.", prompt)
            self.assertIn("Criteri di Accettazione", prompt)
            task = (worktree / "TASK.md").read_text(encoding="utf-8")
            self.assertIn("> Branch: nmaiese/prova-2", task)
            self.assertEqual(run.call_args.kwargs["timeout"], 180)

    def test_help_deriva_dalla_mappa_di_routing(self):
        output = io.StringIO()
        with self.assertRaises(SystemExit), redirect_stdout(output):
            orca_dispatch.main(["--help"])
        help_text = output.getvalue()
        for role, agent in orca_dispatch.AGENT_ROUTING.items():
            self.assertIn(f"{role}={agent}", help_text)

    def test_ok_false_restituisce_uno(self):
        with (
            mock.patch.object(orca_dispatch, "get_orca_cmd", return_value="orca-ide"),
            mock.patch.object(
                orca_dispatch.subprocess,
                "run",
                return_value=completed(stdout='{"ok": false, "error": "no"}'),
            ),
        ):
            code = orca_dispatch.dispatch_task("prova", "T", "O")
        self.assertEqual(code, 1)

    def test_runtime_unavailable_verifica_la_lista_e_restituisce_due(self):
        create = completed(
            stdout='{"ok": false, "error": {"code": "runtime_unavailable"}}',
            returncode=1,
        )
        listing = completed(stdout='{"ok": true, "worktrees": [{"name": "prova"}]}')
        with (
            mock.patch.object(orca_dispatch, "get_orca_cmd", return_value="orca-ide"),
            mock.patch.object(
                orca_dispatch.subprocess, "run", side_effect=[create, listing]
            ) as run,
        ):
            code = orca_dispatch.dispatch_task("prova", "T", "O")
        self.assertEqual(code, 2)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[1].args[0][1:3], ["worktree", "list"])


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
        with mock.patch.object(
            orca_dispatch, "get_orca_cmd", side_effect=RuntimeError("orca-ide assente")
        ):
            code = orca_dispatch.dispatch_task("prova", "T", "O", dry_run=True)
        self.assertEqual(code, 0)

    def test_senza_binario_la_create_reale_esce_uno(self):
        with mock.patch.object(
            orca_dispatch, "get_orca_cmd", side_effect=RuntimeError("orca-ide assente")
        ):
            code = orca_dispatch.dispatch_task("prova", "T", "O")
        self.assertEqual(code, 1)

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
                body = orca_review._task_body(path, 42, base="develop", scheda="indicatore_1")

            self.assertIn("**Commit**: abc123def", body)
            self.assertIn("Testo della issue", body)
            self.assertIn("Closes #42", body)
            self.assertIn("Fonte: ISTAT", body)
            self.assertIn("Reso vecchio", body)
            self.assertIn("Reso nuovo", body)

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

if __name__ == "__main__":
    unittest.main()
