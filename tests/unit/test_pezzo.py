from __future__ import annotations

import importlib
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


SPEC = importlib.util.find_spec("scripts.editoriale.pezzo")
pezzo = importlib.import_module("scripts.editoriale.pezzo") if SPEC else None


class PezzoDisponibileTest(unittest.TestCase):
    def test_modulo_disponibile(self):
        self.assertIsNotNone(SPEC, "manca scripts.editoriale.pezzo")


@unittest.skipUnless(SPEC, "modulo non ancora implementato")
class PezzoTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.posts = self.root / "content" / "posts"
        self.indicators = self.root / "content" / "indicators"
        self.posts.mkdir(parents=True)
        self.indicators.mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def scrivi_post(self, nome, titolo):
        titolo_yaml = json.dumps(titolo, ensure_ascii=False)
        (self.posts / nome).write_text(f"---\ntitle: {titolo_yaml}\n---\nTesto.\n", encoding="utf-8")

    def test_rifiuta_chiave_non_valida(self):
        with self.assertRaisesRegex(ValueError, "chiave"):
            pezzo.valida_chiave("Casa_Affitti")

    def test_trova_tema_istruzione_adulti_esistente(self):
        self.scrivi_post(
            "2026-06-30-istruzione-adulti-licenza-media-divario-2024.md",
            "Istruzione degli adulti: il divario sulla licenza media",
        )

        trovati = pezzo.trova_temi_esistenti(
            "istruzione-adulti", "Istruzione degli adulti", self.posts, self.indicators
        )

        self.assertEqual(len(trovati), 1)
        self.assertEqual(trovati[0].percorso.name, "2026-06-30-istruzione-adulti-licenza-media-divario-2024.md")
        self.assertEqual(trovati[0].titolo, "Istruzione degli adulti: il divario sulla licenza media")

    def test_tema_nuovo_non_trova_corrispondenze(self):
        self.scrivi_post("2026-06-30-istruzione-adulti.md", "Istruzione degli adulti")

        trovati = pezzo.trova_temi_esistenti(
            "casa-affitti", "Casa e affitti", self.posts, self.indicators
        )

        self.assertEqual(trovati, [])

    def test_tipo_sbagliato_esce_due_senza_comandi(self):
        chiamate = []
        with redirect_stderr(io.StringIO()):
            esito = pezzo.main(
                ["apri", "notizie", "casa-affitti", "--titolo", "Casa e affitti"],
                esegui_fn=lambda cmd: chiamate.append(cmd),
                root=self.root,
            )
        self.assertEqual(esito, 2)
        self.assertEqual(chiamate, [])

    def test_tema_esistente_esce_tre_prima_di_comandi(self):
        self.scrivi_post("2026-06-30-istruzione-adulti.md", "Istruzione degli adulti")
        chiamate = []
        output = io.StringIO()

        with redirect_stdout(output):
            esito = pezzo.main(
                ["apri", "blog", "istruzione-adulti", "--titolo", "Istruzione degli adulti"],
                esegui_fn=lambda cmd: chiamate.append(cmd),
                root=self.root,
            )

        self.assertEqual(esito, 3)
        self.assertEqual(chiamate, [])
        self.assertIn("content/posts/2026-06-30-istruzione-adulti.md", output.getvalue())

    def test_prova_non_chiama_comandi_e_non_scrive(self):
        chiamate = []
        output = io.StringIO()

        with redirect_stdout(output):
            esito = pezzo.main(
                ["apri", "blog", "casa-affitti", "--titolo", "Casa e affitti", "--prova"],
                esegui_fn=lambda cmd: chiamate.append(cmd),
                root=self.root,
            )

        self.assertEqual(esito, 0)
        self.assertEqual(chiamate, [])
        self.assertFalse((self.root / "lavoro" / "casa-affitti").exists())
        self.assertIn("Creerei l'issue", output.getvalue())

    def test_forza_tema_esistente_prosegue(self):
        self.scrivi_post("2026-06-30-istruzione-adulti.md", "Istruzione degli adulti")
        chiamate = []
        worktree = self.root / "worktree-forzato"
        worktree.mkdir()

        def finto(cmd):
            chiamate.append(cmd)
            if cmd[:3] == ["git", "show-ref", "--verify"]:
                return ""
            if cmd[:2] == ["git", "ls-remote"]:
                return ""
            if cmd[:3] == ["gh", "issue", "create"]:
                return "https://github.com/nmaiese/divarioitalia/issues/342\n"
            if cmd[0].endswith("orca-worktree.sh"):
                return f"{worktree}\n"
            if cmd[:3] == ["gh", "pr", "create"]:
                return "https://github.com/nmaiese/divarioitalia/pull/343\n"
            return ""

        esito = pezzo.main(
            [
                "apri", "blog", "istruzione-adulti", "--titolo", "Istruzione degli adulti",
                "--forza-tema-esistente",
            ],
            esegui_fn=finto,
            root=self.root,
        )

        self.assertEqual(esito, 0)
        self.assertTrue(any(cmd[:3] == ["gh", "issue", "create"] for cmd in chiamate))

    def test_ramo_locale_esistente_ferma_prima_di_github(self):
        chiamate = []

        def finto(cmd):
            chiamate.append(cmd)
            if cmd[:3] == ["git", "show-ref", "--verify"]:
                return "refs/heads/divario/casa-affitti\n"
            return ""

        with redirect_stderr(io.StringIO()):
            esito = pezzo.main(
                ["apri", "blog", "casa-affitti", "--titolo", "Casa e affitti"],
                esegui_fn=finto,
                root=self.root,
            )

        self.assertEqual(esito, 1)
        self.assertEqual(len(chiamate), 1)

    def test_sequenza_comandi_e_file_creati(self):
        chiamate = []
        worktree = self.root / "nuovo-worktree"
        worktree.mkdir()

        def finto(cmd):
            chiamate.append(cmd)
            if cmd[:3] == ["gh", "issue", "create"]:
                return "https://github.com/nmaiese/divarioitalia/issues/342\n"
            if cmd[0].endswith("orca-worktree.sh"):
                return f"{worktree}\n"
            if cmd[:3] == ["gh", "pr", "create"]:
                return "https://github.com/nmaiese/divarioitalia/pull/343\n"
            return ""

        output = io.StringIO()
        with redirect_stdout(output):
            esito = pezzo.main(
                ["apri", "team", "casa-affitti", "--titolo", "Casa e affitti"],
                esegui_fn=finto,
                root=self.root,
            )

        self.assertEqual(esito, 0)
        self.assertEqual(
            [cmd[:3] for cmd in chiamate],
            [
                ["git", "show-ref", "--verify"],
                ["git", "ls-remote", "--exit-code"],
                ["gh", "issue", "create"],
                [str(Path.home() / "dev/dev-tools/scripts/orca-worktree.sh"), "divario-casa-affitti"],
                ["git", "-C", str(worktree)],
                ["git", "-C", str(worktree)],
                ["git", "-C", str(worktree)],
                ["git", "-C", str(worktree)],
                ["gh", "pr", "create"],
            ],
        )
        self.assertIn("--label", chiamate[2])
        self.assertIn("run:team", chiamate[2])
        self.assertTrue(any("Closes #342" in arg for arg in chiamate[-1]))
        self.assertIn("run:team", chiamate[-1])
        brief = (worktree / "lavoro" / "casa-affitti" / "brief.md").read_text(encoding="utf-8")
        self.assertIn("# Casa e affitti", brief)
        self.assertIn("Issue: #342", brief)
        self.assertIn("700-1100", brief)
        self.assertIn("1400-2000", brief)
        self.assertTrue((worktree / "lavoro" / "casa-affitti" / "numeri.md").exists())
        self.assertTrue((worktree / "lavoro" / "casa-affitti" / "fonti.md").exists())
        self.assertIn("Issue #342", output.getvalue())
        self.assertIn("pull/343", output.getvalue())

    def test_compositori_restituiscono_testo_operativo(self):
        issue = pezzo.corpo_issue("blog", "casa-affitti", "codex-prova")
        pr = pezzo.corpo_pr(342, "blog", "casa-affitti", "codex-prova")
        brief = pezzo.contenuto_brief("Casa e affitti", "blog", 342, [])

        self.assertIn("docs/WORKFLOW_ORCA.md", issue)
        self.assertIn("Closes #342", pr)
        self.assertTrue(issue.endswith("— codex-prova"))
        self.assertTrue(pr.endswith("— codex-prova"))
        self.assertIn("content/STYLE.md", brief)


if __name__ == "__main__":
    unittest.main()
