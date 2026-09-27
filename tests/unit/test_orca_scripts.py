"""Regressioni per gli helper Orca, senza operazioni reali sui worktree."""

from __future__ import annotations

import io
import json
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
        body = pull_request[pull_request.index("--body") + 1]
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


if __name__ == "__main__":
    unittest.main()
