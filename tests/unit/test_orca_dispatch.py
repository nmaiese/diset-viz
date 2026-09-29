"""Test unitario per scripts/orca_dispatch.py (Orchestratore Multi-Agente Orca)."""
import contextlib
import io
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import orca_dispatch


def completed(stdout="", returncode=0):
    return subprocess.CompletedProcess([], returncode, stdout, "")


class OrcaDispatchTest(unittest.TestCase):
    def test_ruoli_mappati_sulle_attivita(self):
        self.assertEqual(
            orca_dispatch.ROLE_TO_ATTIVITA,
            {
                "worker": "implementazione",
                "architect": "architettura",
                "researcher": "ricerca",
            },
        )

    def test_attivita_esplicita_vince_sul_ruolo(self):
        self.assertEqual(orca_dispatch.resolve_attivita("worker", "revisione"), "revisione")
        self.assertEqual(orca_dispatch.resolve_attivita("researcher"), "ricerca")
        self.assertIsNone(orca_dispatch.resolve_attivita("boh"))

    def test_dry_run_stampa_il_comando_orca_lancia(self):
        out = io.StringIO()
        with (
            contextlib.redirect_stdout(out),
            mock.patch.object(orca_dispatch.subprocess, "run") as run,
        ):
            code = orca_dispatch.dispatch_task(
                slug="unit-test-task",
                title="T",
                objective="O",
                role="worker",
                dry_run=True,
            )
        self.assertEqual(code, 0)
        run.assert_not_called()
        line = out.getvalue()
        self.assertIn("orca-lancia.sh --attivita implementazione --worktree unit-test-task", line)
        self.assertIn("--spec-file", line)
        self.assertNotIn("--sola-lettura", line)

    def test_dry_run_sola_lettura(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            orca_dispatch.dispatch_task("x", "T", "O", dry_run=True, sola_lettura=True)
        self.assertIn("--sola-lettura", out.getvalue())

    def test_dispatch_chiama_orca_worktree_poi_orca_lancia(self):
        with tempfile.TemporaryDirectory() as tmp:
            wt = Path(tmp) / "prova"
            wt.mkdir()
            calls = [completed(stdout=f"{wt}\n"), completed()]
            with (
                contextlib.redirect_stdout(io.StringIO()),
                mock.patch.dict(os.environ, {"ORCA_LANCIA": "/x/orca-lancia.sh"}),
                mock.patch.object(orca_dispatch.subprocess, "run", side_effect=calls) as run,
            ):
                code = orca_dispatch.dispatch_task("prova", "T", "O", role="researcher")
            self.assertEqual(code, 0)
            first, second = (c.args[0] for c in run.call_args_list)
            self.assertTrue(first[0].endswith("orca-worktree.sh"))
            self.assertEqual(first[1], "prova")
            self.assertIn("origin/master", first)
            self.assertEqual(
                second,
                ["/x/orca-lancia.sh", "--attivita", "ricerca", "--worktree", "prova",
                 "--spec-file", str(wt / "TASK.md")],
            )
            self.assertEqual(run.call_args_list[1].kwargs["cwd"], orca_dispatch.MAIN_ROOT)
            self.assertNotIn("capture_output", run.call_args_list[1].kwargs)
            self.assertIn("> Assegnato a: ricerca", (wt / "TASK.md").read_text(encoding="utf-8"))

    def test_exit_di_orca_lancia_e_propagato(self):
        with tempfile.TemporaryDirectory() as tmp:
            wt = Path(tmp) / "prova"
            wt.mkdir()
            finto = Path(tmp) / "finto.sh"
            finto.write_text("#!/bin/sh\nexit 3\n")
            finto.chmod(finto.stat().st_mode | stat.S_IXUSR)
            worktree = completed(stdout=f"{wt}\n")
            real_run = subprocess.run
            with (
                contextlib.redirect_stdout(io.StringIO()),
                mock.patch.dict(os.environ, {"ORCA_LANCIA": str(finto)}),
                mock.patch.object(
                    orca_dispatch.subprocess,
                    "run",
                    side_effect=lambda cmd, **kw: worktree
                    if cmd[0].endswith("orca-worktree.sh")
                    else real_run(cmd, **kw),
                ),
            ):
                code = orca_dispatch.dispatch_task("prova", "T", "O")
        self.assertEqual(code, 3)

    def test_worktree_fallito_non_lancia(self):
        with (
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
            mock.patch.object(
                orca_dispatch.subprocess, "run", return_value=completed(returncode=1)
            ) as run,
        ):
            code = orca_dispatch.dispatch_task("prova", "T", "O")
        self.assertEqual(code, 1)
        self.assertEqual(run.call_count, 1)

    def test_task_template_formatting(self):
        content = orca_dispatch.build_task_content(
            slug="prova-slug",
            title="Titolo Prova",
            objective="Obiettivo di prova",
            attivita="implementazione",
        )
        self.assertIn("# Task: Titolo Prova", content)
        self.assertIn("> Assegnato a: implementazione", content)
        self.assertIn("DIVARIO_PYTHON=", content)
        self.assertIn(".venv/bin/python", content)
        self.assertIn("CLAUDE.md", content)


if __name__ == "__main__":
    unittest.main()
