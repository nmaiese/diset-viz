from __future__ import annotations

import importlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


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

    def test_controllo_ramo_con_git_reale(self):
        subprocess.run(["git", "init", "-q", "--initial-branch=master", str(self.root)], check=True)
        subprocess.run(
            ["git", "-C", str(self.root), "-c", "user.name=Test",
             "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "Base"],
            check=True,
        )
        remote = self.root / "remote.git"
        subprocess.run(["git", "clone", "--bare", "-q", str(self.root), str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.root), "remote", "add", "origin", str(remote)], check=True)
        for esistente in (False, True):
            with self.subTest(esistente=esistente):
                if esistente:
                    subprocess.run(
                        ["git", "-C", str(self.root), "branch", "divario/tema-nuovo"], check=True,
                    )
                chiamate = []
                def comando(cmd):
                    chiamate.append(cmd)
                    if cmd[0] == "git":
                        return subprocess.check_output(cmd, cwd=self.root, text=True, stderr=subprocess.PIPE)
                    raise RuntimeError("passo 2 superato")
                errore = io.StringIO()
                with redirect_stderr(errore), redirect_stdout(io.StringIO()):
                    esito = pezzo.main(
                        ["apri", "blog", "tema-nuovo", "--titolo", "Tema nuovo"],
                        root=self.root, esegui_fn=comando,
                    )
                self.assertEqual(esito, 1)
                self.assertIn("ramo locale" if esistente else "passo 2 superato", errore.getvalue())
                if esistente:
                    self.assertEqual(len(chiamate), 1)
                else:
                    self.assertEqual(chiamate[-1][:3], ["gh", "issue", "list"])

    def test_errori_git_non_sono_assenza(self):
        for rc in (2, 128):
            with self.subTest(rc=rc):
                def errore(cmd):
                    raise subprocess.CalledProcessError(rc, cmd)
                with self.assertRaises(subprocess.CalledProcessError):
                    pezzo._esiste_ramo(["git", "show-ref", "--verify", "--quiet", "refs/heads/x"], errore)

    def run_open(self, runner):
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            result = pezzo.main(
                ["apri", "blog", "tema-nuovo", "--titolo", "Tema nuovo"],
                root=self.root, esegui_fn=runner,
            )
        return result, output.getvalue(), errors.getvalue()

    def opening_runner(self, calls, worktree, *, issues=(), fail=None):
        def runner(cmd):
            calls.append(cmd)
            if cmd[:2] == ["git", "show-ref"]:
                raise subprocess.CalledProcessError(1, cmd)
            if cmd[:3] == ["gh", "issue", "list"]:
                return json.dumps(list(issues))
            if cmd[:3] == ["gh", "issue", "create"]:
                return "https://github.com/example/repo/issues/342\n"
            if cmd[0].endswith("orca-worktree.sh"):
                if fail == "worktree":
                    raise RuntimeError("creazione worktree fallita")
                return str(worktree)
            if len(cmd) > 3 and cmd[3] == fail:
                raise RuntimeError(f"{fail} fallito")
            if cmd[:3] == ["gh", "pr", "create"]:
                return "https://github.com/example/repo/pull/343"
            return ""
        return runner

    def test_errore_worktree_segnala_issue_e_rimedio(self):
        calls = []
        result, output, errors = self.run_open(
            self.opening_runner(calls, self.root, fail="worktree")
        )
        self.assertEqual(result, 1)
        self.assertIn("Issue #342", output)
        self.assertIn("Issue #342", errors)
        self.assertIn("chiud", errors)
        self.assertFalse(any(cmd[:3] == ["gh", "pr", "create"] for cmd in calls))

    def test_errore_push_segnala_risorse_e_ripresa(self):
        worktree = self.root / "worktree"
        worktree.mkdir()
        calls = []
        result, output, errors = self.run_open(
            self.opening_runner(calls, worktree, fail="push")
        )
        self.assertEqual(result, 1)
        for value in ("Issue #342", str(worktree), "divario/tema-nuovo",
                      str(worktree / "lavoro/tema-nuovo"), "riprend"):
            self.assertIn(value, errors)
        self.assertIn("Commit", output)
        self.assertFalse(any(cmd[:3] == ["gh", "pr", "create"] for cmd in calls))

    def test_riusa_solo_issue_con_titolo_identico(self):
        for matching in (False, True):
            with self.subTest(matching=matching):
                worktree = self.root / str(matching)
                worktree.mkdir()
                calls = []
                issues = [{"number": 17, "title": "Tema nuovo" if matching else "Altro tema"}]
                result, output, _ = self.run_open(self.opening_runner(calls, worktree, issues=issues))
                self.assertEqual(result, 0)
                self.assertEqual(any(cmd[:3] == ["gh", "issue", "create"] for cmd in calls), not matching)
                if matching:
                    self.assertIn("riusata", output.lower())
                    self.assertIn("Issue: #17", (worktree / "lavoro/tema-nuovo/brief.md").read_text())
                search = next(cmd for cmd in calls if cmd[:3] == ["gh", "issue", "list"])
                self.assertIn("--search", search)
                self.assertEqual(search[search.index("--state") + 1], "open")
                self.assertEqual(search[search.index("--json") + 1], "number,title")

    def test_base_master_aggiornata_prima_del_worktree(self):
        calls = []
        result, _, _ = self.run_open(self.opening_runner(calls, self.root))
        self.assertEqual(result, 0)
        self.assertIn(["git", "fetch", "origin", "master"], calls)
        create = next(cmd for cmd in calls if cmd[0].endswith("orca-worktree.sh"))
        self.assertEqual(create[create.index("--base-branch") + 1], "master")
        self.assertLess(calls.index(["git", "fetch", "origin", "master"]), calls.index(create))
        switch = next(cmd for cmd in calls if len(cmd) > 3 and cmd[3] == "switch")
        self.assertEqual(switch[-1], "origin/master")

    def test_worktree_esistente_ferma_prima_di_github(self):
        calls = []
        base = self.opening_runner(calls, self.root)
        def runner(cmd):
            if cmd[:3] == ["git", "worktree", "list"]:
                calls.append(cmd)
                return f"worktree {self.root}/divario-tema-nuovo\0HEAD abc\0branch refs/heads/altro\0"
            return base(cmd)
        result, _, errors = self.run_open(runner)
        self.assertEqual(result, 1)
        self.assertIn("worktree", errors)
        self.assertFalse(any(cmd[0] == "gh" for cmd in calls))

    def test_esegui_separa_stderr(self):
        with patch.object(pezzo, "ROOT", self.root):
            output = pezzo.esegui(["sh", "-c", "printf percorso; printf avviso >&2"])
        self.assertEqual(output, "percorso")

    def test_numero_issue_con_rumore_dopo_url(self):
        self.assertEqual(pezzo._numero_issue("https://github.com/example/repo/issues/342\navviso"), 342)

    def test_percorso_esistente_con_rumore_dopo(self):
        self.assertEqual(pezzo._ultimo_percorso(f"{self.root}\navviso"), self.root)

    def test_percorso_inesistente_rifiutato(self):
        with self.assertRaisesRegex(ValueError, "percorso"):
            pezzo._ultimo_percorso(str(self.root / "inesistente"))

    def test_parole_generiche_non_trovano_pezzi(self):
        for index, topic in enumerate(("Turismo", "PIL", "Disoccupazione", "Occupazione")):
            self.scrivi_post(f"{index}-divario-nord.md", f"{topic}: il divario tra Nord e Sud")
        self.assertEqual(
            pezzo.trova_temi_esistenti("divario-nord-sud", "Il divario tra Nord e Sud in Italia",
                                       self.posts, self.indicators), []
        )
        self.assertEqual(
            pezzo.trova_temi_esistenti("divario", "Regioni regione italiano Italia dati",
                                       self.posts, self.indicators), []
        )

    def test_prefissi_competenze_e_scuola(self):
        self.scrivi_post("competenze.md", "Competenza scolastica in matematica")
        self.scrivi_post("abbandono.md", "Scuola media: risultati degli alunni")
        for key, title, filename in (
            ("competenze-matematica", "Competenze scolastiche in matematica", "competenze.md"),
            ("abbandono-scolastico", "Abbandono scolastico", "abbandono.md"),
        ):
            with self.subTest(key=key):
                found = pezzo.trova_temi_esistenti(key, title, self.posts, self.indicators)
                self.assertIn(filename, [item.percorso.name for item in found])

    def test_indicatori_usano_solo_title(self):
        (self.indicators / "12345.md").write_text("---\ntitle: Acqua potabile\n---\n")
        (self.indicators / "acqua-potabile.md").write_text("Testo senza titolo.")
        found = pezzo.trova_temi_esistenti("acqua-potabile", "Acqua potabile", self.posts, self.indicators)
        self.assertEqual([item.percorso.name for item in found], ["12345.md"])
        self.assertEqual(
            pezzo.trova_temi_esistenti("12345", "Tema nuovo", self.posts, self.indicators), []
        )

    def test_casa_affitti_esiste(self):
        self.scrivi_post("2026-09-29-casa-affitti-mercato.md", "Casa e affitti: il mercato")
        self.assertEqual(len(pezzo.trova_temi_esistenti(
            "casa-affitti", "Casa e affitti", self.posts, self.indicators)), 1)

    def test_ramo_remoto_esistente_ferma_prima_di_github(self):
        calls = []
        base = self.opening_runner(calls, self.root)
        def runner(cmd):
            if cmd[:2] == ["git", "ls-remote"]:
                calls.append(cmd)
                return "abc refs/heads/divario/tema-nuovo\n"
            return base(cmd)
        result, _, errors = self.run_open(runner)
        self.assertEqual(result, 1)
        self.assertIn("ramo remoto", errors)
        self.assertFalse(any(cmd[0] == "gh" for cmd in calls))

    def test_cartella_lavoro_esistente_ferma_prima_di_github(self):
        (self.root / "lavoro/tema-nuovo").mkdir(parents=True)
        calls = []
        result, _, errors = self.run_open(self.opening_runner(calls, self.root))
        self.assertEqual(result, 1)
        self.assertIn("cartella lavoro/tema-nuovo", errors)
        self.assertFalse(any(cmd[0] == "gh" for cmd in calls))

    def test_prova_tema_esistente_non_esegue_comandi(self):
        self.scrivi_post("istruzione-adulti.md", "Istruzione degli adulti")
        for force, expected in ((False, 3), (True, 0)):
            with self.subTest(force=force):
                calls = []
                args = ["apri", "blog", "istruzione-adulti", "--titolo", "Istruzione degli adulti", "--prova"]
                if force:
                    args.append("--forza-tema-esistente")
                with redirect_stdout(io.StringIO()):
                    result = pezzo.main(args, root=self.root, esegui_fn=lambda cmd: calls.append(cmd))
                self.assertEqual(result, expected)
                self.assertEqual(calls, [])
                self.assertFalse((self.root / "lavoro").exists())

    def test_commit_push_e_pr_rispettano_contratto(self):
        calls = []
        result, _, _ = self.run_open(self.opening_runner(calls, self.root))
        self.assertEqual(result, 0)
        self.assertIn(["git", "-C", str(self.root), "commit", "-m",
                       "Apre il lavoro editoriale su Tema nuovo"], calls)
        self.assertIn(["git", "-C", str(self.root), "push", "-u", "origin", "divario/tema-nuovo"], calls)
        pr = next(cmd for cmd in calls if cmd[:3] == ["gh", "pr", "create"])
        self.assertIn("--draft", pr)
        self.assertEqual(pr[pr.index("--base") + 1], "master")
        self.assertEqual(pr[pr.index("--head") + 1], "divario/tema-nuovo")
        self.assertIn("Closes #342", pr[pr.index("--body") + 1])
        self.assertNotIn("Co-Authored-By", " ".join(arg for cmd in calls for arg in cmd))

    def test_chiave_massimo_quaranta_caratteri(self):
        self.assertEqual(pezzo.valida_chiave("x" * 40), "x" * 40)
        with self.assertRaisesRegex(ValueError, "40"):
            pezzo.valida_chiave("x" * 41)

    def test_firma_solo_con_identita_reale(self):
        for identity in ("", "   ", "claude-prova"):
            with self.subTest(identity=identity), patch.dict(pezzo.os.environ, {"AGENT_ID": identity}):
                signature = pezzo.identita_agente()
                self.assertEqual(signature, identity.strip())
                for body in (pezzo.corpo_issue("blog", "tema", signature),
                             pezzo.corpo_pr(342, "blog", "tema", signature)):
                    if identity.strip():
                        self.assertTrue(body.endswith("— claude-prova"))
                    else:
                        self.assertNotIn("—", body)
        with patch.dict(pezzo.os.environ, {}, clear=True):
            self.assertEqual(pezzo.identita_agente(), "")

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
            "meteoriti-lunari", "Meteoriti lunari", self.posts, self.indicators
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
                raise subprocess.CalledProcessError(1, cmd)
            if cmd[:2] == ["git", "ls-remote"]:
                return ""
            if cmd[:3] == ["gh", "issue", "list"]:
                return "[]"
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
            if cmd[:2] == ["git", "show-ref"]:
                raise subprocess.CalledProcessError(1, cmd)
            if cmd[:3] == ["gh", "issue", "list"]:
                return "[]"
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
                ["git", "ls-remote", "--heads"],
                ["git", "worktree", "list"],
                ["git", "fetch", "origin"],
                ["gh", "issue", "list"],
                ["gh", "issue", "create"],
                [str(Path.home() / "dev/dev-tools/scripts/orca-worktree.sh"), "divario-casa-affitti", "--base-branch"],
                ["git", "-C", str(worktree)],
                ["git", "-C", str(worktree)],
                ["git", "-C", str(worktree)],
                ["git", "-C", str(worktree)],
                ["gh", "pr", "create"],
            ],
        )
        self.assertIn("--label", chiamate[5])
        self.assertIn("run:team", chiamate[5])
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
