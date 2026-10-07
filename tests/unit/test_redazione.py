from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.editoriale import redazione


def fixture_config():
    output_names = {
        "scout": ["dossier.json", "copertura.csv", "numeri.md", "fonti.md"],
        "brief": ["brief.md"], "gate_a": ["gate-a.md"], "autore": ["bozza.md"],
        "grafico": ["grafici.md"], "guardia": ["guardia.json"],
        "gate_b": ["verifica.md", "gate-b.md"], "bozza": ["bozza.json"],
    }
    phases = []
    for name in redazione.DEFAULT_PHASES:
        phases.append({
            "name": name,
            "role": name,
            "choices": [{"agent": "codex", "model": "gpt-6-luna"}],
            "input": [],
            "output": output_names[name],
            "template": f"{name}.md",
            "timeout_seconds": 60,
            "blocking": True,
        })
    return {"memory_min_mb": 1500, "max_rewrites": 2, "phases": phases}


class FakeLauncher:
    def __init__(self, base: Path, failures=None, gates=None):
        self.base = base
        self.calls = []
        self.failures = list(failures or [])
        self.gates = list(gates or [])

    def __call__(self, phase, spec_path):
        self.calls.append(phase["name"])
        if self.failures and self.failures[0] == phase["name"]:
            self.failures.pop(0)
            return {"success": False, "terminal_handle": "term-fake"}
        for output in phase["output"]:
            path = self.base / output
            path.parent.mkdir(parents=True, exist_ok=True)
            if output == "gate-a.md":
                text = self.gates.pop(0) if self.gates else gate_a("PASSA")
                brief = self.base / "brief.md"
                if brief.exists():
                    text = text.replace("Hash brief: abc", f"Hash brief: {hashlib.sha256(brief.read_bytes()).hexdigest()}")
            elif output == "gate-b.md":
                text = self.gates.pop(0) if self.gates else gate_b("PASSA", 4)
                draft = self.base / "bozza.md"
                if draft.exists():
                    text = text.replace("Hash bozza: abc", f"Hash bozza: {hashlib.sha256(draft.read_bytes()).hexdigest()}")
            else:
                text = f"prova {phase['name']}\n"
            path.write_text(text, encoding="utf-8")
        return {"success": True, "terminal_handle": "term-fake", "model": "gpt-6-luna"}


def gate_a(outcome):
    text = f"""SHA brief: abc\nHash brief: abc\nAutore/modello: A\nGiudice/modello: B\nDomanda: domanda\nTesi: tesi\nCodici e confronto: x/y/z\n| criterio | sì/no | prova | limite |\n|---|---|---|---|\n| A | sì | prova | limite |\n| B | sì | prova | limite |\n| C | sì | prova | limite |\n| D | sì | prova | limite |\n| E | sì | prova | limite |\nEsito: {outcome}\nMotivo: motivo\nCorrezione: correzione\nDestinatario: leader\nData: 2026-10-07\n"""
    return text.replace("| A | sì |", "| A | no |") if outcome == "FERMO" else text


def gate_b(outcome, vote):
    return f"""SHA bozza: abc\nHash bozza: abc\nFamiglie autore/revisore: A/B\nT: sì — citazione\nR: sì — citazione\nL: sì — citazione\nN: sì — citazione\nControllo anti-invenzione: sì\nBloccanti: 0\nVoto: {vote}\nMotivo: motivo\nRilievi localizzati: nessuno\nGiri: 1\nEsito: {outcome}\n"""


class RedazioneTests(unittest.TestCase):
    def setup_case(self, tmp, config=None):
        root = Path(tmp)
        work = root / "divario-demo"
        work.mkdir()
        (work / "lavoro" / "demo").mkdir(parents=True)
        cfg = config or fixture_config()
        return root, work, cfg

    def run_case(self, root, work, cfg, launcher, **kwargs):
        return redazione.run_redazione(
            "demo", root=root, worktree=work, config=cfg, launcher=launcher,
            ram_provider=lambda: 4096, bridge_dir=root / "ponte", **kwargs,
        )

    def test_sequenza_completa_felice(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            launcher = FakeLauncher(work / "lavoro" / "demo")
            result = self.run_case(root, work, cfg, launcher)
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(launcher.calls, list(redazione.DEFAULT_PHASES))

    def test_secondo_avvio_con_hash_invariati_non_rilancia_ruoli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            first = FakeLauncher(work / "lavoro" / "demo")
            self.assertEqual(self.run_case(root, work, cfg, first).exit_code, 0)
            second = FakeLauncher(work / "lavoro" / "demo")
            self.assertEqual(self.run_case(root, work, cfg, second).exit_code, 0)
            self.assertEqual(second.calls, [])

    def test_brief_iniziale_restà_stabile_dopo_brief_del_leader(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            work = root / "divario-demo"
            workdir = work / "lavoro" / "demo"
            workdir.mkdir(parents=True)
            (workdir / "brief.md").write_text("# Tema iniziale\n\nIssue: #123\n", encoding="utf-8")
            launch = FakeLauncher(workdir)
            kwargs = {"root": root, "worktree": work, "config_path": redazione.CONFIG,
                      "launcher": launch, "ram_provider": lambda: 4096,
                      "labeler": lambda *_args: None, "bridge_dir": root / "ponte"}
            self.assertEqual(redazione.run_redazione("demo", **kwargs).exit_code, 0)
            self.assertEqual((workdir / "brief_iniziale.md").read_text(encoding="utf-8"),
                             "# Tema iniziale\n\nIssue: #123\n")
            resumed = FakeLauncher(workdir)
            kwargs["launcher"] = resumed
            self.assertEqual(redazione.run_redazione("demo", **kwargs).exit_code, 0)
            self.assertEqual(resumed.calls, [])

    def test_gate_a_negativo_ferma_con_messaggio_ponte(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            launcher = FakeLauncher(work / "lavoro" / "demo", gates=[gate_a("FERMO")])
            result = self.run_case(root, work, cfg, launcher, max_gate_a_retries=0)
            self.assertEqual(result.exit_code, 3)
            self.assertTrue(list((root / "ponte").glob("*.md")))
            self.assertNotIn("autore", launcher.calls)
            message = next((root / "ponte").glob("*.md")).read_text(encoding="utf-8")
            self.assertEqual(message.splitlines()[0], "per: cowork-direzione | da: C-DIV | progetto: divarioitalia | tipo: info | priorita: normale")
            self.assertEqual(message.splitlines()[1], "")
            self.assertNotIn("---", message)

    def test_gate_a_concede_un_solo_ritorno_al_leader(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            launcher = FakeLauncher(work / "lavoro" / "demo", gates=[gate_a("FERMO"), gate_a("FERMO")])
            result = self.run_case(root, work, cfg, launcher)
            self.assertEqual(result.exit_code, 3)
            self.assertEqual(launcher.calls.count("brief"), 2)
            self.assertEqual(launcher.calls.count("gate_a"), 2)

    def test_solo_esegue_una_fase(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            launcher = FakeLauncher(work / "lavoro" / "demo")
            result = self.run_case(root, work, cfg, launcher, only="grafico")
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(launcher.calls, ["grafico"])

    def test_aggiornamento_pr_riporta_gate_attuali_e_omette_firma_assente(self):
        with tempfile.TemporaryDirectory() as tmp:
            worktree = Path(tmp)
            workdir = worktree / "lavoro/demo"
            workdir.mkdir(parents=True)
            brief = workdir / "brief.md"
            draft = workdir / "bozza.md"
            brief.write_text("brief", encoding="utf-8")
            draft.write_text("draft", encoding="utf-8")
            a_hash = hashlib.sha256(brief.read_bytes()).hexdigest()
            b_hash = hashlib.sha256(draft.read_bytes()).hexdigest()
            (workdir / "gate-a.md").write_text(gate_a("FERMO").replace("Hash brief: abc", f"Hash brief: {a_hash}"), encoding="utf-8")
            (workdir / "gate-b.md").write_text(gate_b("RISCRIVERE", 3).replace("Hash bozza: abc", f"Hash bozza: {b_hash}"), encoding="utf-8")
            seen = []

            def fake_run(command, **kwargs):
                if "view" in command:
                    return redazione.subprocess.CompletedProcess(command, 0, "Testo PR esistente\n", "")
                seen.append(Path(command[-1]).read_text(encoding="utf-8"))
                return redazione.subprocess.CompletedProcess(command, 0, "", "")

            with patch.dict(redazione.os.environ, {"AGENT_ID": ""}), \
                    patch.object(redazione.subprocess, "run", side_effect=fake_run):
                redazione._update_pr_preview(worktree, "demo", 17, Path("/tmp/preview.html"),
                                             Path("/tmp/index.html"), a_hash, b_hash)
            self.assertIn("Testo PR esistente", seen[0])
            self.assertIn("Gate A: FERMO", seen[0])
            self.assertIn("Gate B: RISCRIVERE", seen[0])
            self.assertNotIn("— codex-gpt-6-luna", seen[0])

    def test_gate_b_negativo_ferma_dopo_due_giri(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            launcher = FakeLauncher(work / "lavoro" / "demo", gates=[
                gate_a("PASSA"), gate_b("RISCRIVERE", 3), gate_b("FERMO", 2)])
            result = self.run_case(root, work, cfg, launcher)
            self.assertEqual(result.exit_code, 3)
            self.assertEqual(launcher.calls.count("autore"), 2)
            self.assertEqual(launcher.calls.count("gate_b"), 2)

    def test_ripresa_dopo_errore_non_rifà_fasi_riuscite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            first = FakeLauncher(work / "lavoro" / "demo", failures=["brief"])
            self.assertEqual(self.run_case(root, work, cfg, first).exit_code, 1)
            second = FakeLauncher(work / "lavoro" / "demo")
            self.assertEqual(self.run_case(root, work, cfg, second).exit_code, 0)
            self.assertNotIn("scout", second.calls)
            self.assertEqual(second.calls[0], "brief")

    def test_rifiuta_ram_sotto_soglia(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            launcher = FakeLauncher(work / "lavoro" / "demo")
            result = redazione.run_redazione("demo", root=root, worktree=work, config=cfg,
                launcher=launcher, ram_provider=lambda: 1499)
            self.assertEqual(result.exit_code, 1)
            self.assertEqual(launcher.calls, [])

    def test_rifiuta_doppio_lancio_se_terminale_vivo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            state = work / "lavoro" / "demo" / "stato.json"
            state.write_text(json.dumps({"current_phase": "scout", "phases": {
                "scout": {"status": "in corso", "handle": "term-live"}}}), encoding="utf-8")
            launcher = FakeLauncher(work / "lavoro" / "demo")
            result = self.run_case(root, work, cfg, launcher, terminal_alive=lambda _h: True)
            self.assertEqual(result.exit_code, 1)
            self.assertEqual(launcher.calls, [])

    def test_blocca_ripresa_se_stato_terminale_sconosciuto(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            (work / "lavoro/demo/stato.json").write_text(json.dumps({"current_phase": "scout", "phases": {
                "scout": {"status": "in corso", "handle": "term-unknown"}}}), encoding="utf-8")
            launcher = FakeLauncher(work / "lavoro/demo")
            result = self.run_case(root, work, cfg, launcher, terminal_alive=lambda _h: None)
            self.assertEqual(result.exit_code, 1)
            self.assertIn("sconosciuto", result.message)
            self.assertEqual(launcher.calls, [])

    def test_output_stale_non_consegna_ruolo_succeeded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            output = work / "lavoro/demo/brief.md"
            output.write_text("vecchio output", encoding="utf-8")

            def stale_launcher(*_args):
                return {"success": True, "worker_state": "succeeded"}

            result = self.run_case(root, work, cfg, stale_launcher, only="brief")
            self.assertEqual(result.exit_code, 1)
            self.assertIn("output non aggiornato", result.message)
            self.assertEqual(output.read_text(encoding="utf-8"), "vecchio output")

    def test_commit_nuovo_consegna_output_anche_se_hash_immutato(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            output = work / "lavoro/demo/brief.md"
            output.write_text("contenuto incluso nel commit", encoding="utf-8")
            with patch.object(redazione, "_head_sha", side_effect=["prima", "dopo", "dopo"]):
                result = self.run_case(root, work, cfg,
                    lambda *_args: {"success": True, "worker_state": "succeeded"}, only="brief")
            self.assertEqual(result.exit_code, 0)
            state = json.loads((work / "lavoro/demo/stato.json").read_text(encoding="utf-8"))
            record = state["phases"]["brief"]
            self.assertEqual(record["prelaunch_commit"], "prima")
            self.assertEqual(record["prelaunch_output_hashes"]["lavoro/demo/brief.md"],
                             hashlib.sha256(b"contenuto incluso nel commit").hexdigest())

    def test_prova_controlla_ingressi_di_tutte_le_fasi_selezionate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            cfg["phases"][0]["input"] = []
            cfg["phases"][1]["input"] = ["inesistente.md"]
            result = self.run_case(root, work, cfg, FakeLauncher(work / "lavoro/demo"), dry_run=True,
                                   from_phase="scout")
            self.assertEqual(result.exit_code, 1)
            self.assertIn("inesistente.md", result.message)

    def test_gate_b_aggiunge_label_gate_b(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            (work / "lavoro/demo/stato.json").write_text(json.dumps({"issue": "17"}), encoding="utf-8")
            calls = []
            result = self.run_case(root, work, cfg, FakeLauncher(work / "lavoro/demo"),
                                   labeler=lambda issue, label, add: calls.append((label, add)))
            self.assertEqual(result.exit_code, 0)
            self.assertIn(("gate-b", True), calls)

    def test_gate_malformato_blocca(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            launcher = FakeLauncher(work / "lavoro" / "demo", gates=["Esito: PASSA\n"])
            result = self.run_case(root, work, cfg, launcher)
            self.assertEqual(result.exit_code, 1)
            self.assertEqual(launcher.calls, ["scout", "brief", "gate_a"])

    def test_secondo_gate_malformato_scrive_ponte_e_blocca(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            for _ in range(2):
                launcher = FakeLauncher(work / "lavoro/demo", gates=["gate incompleto"])
                result = self.run_case(root, work, cfg, launcher, only="gate_a")
            self.assertEqual(result.exit_code, 3)
            self.assertIn("due volte", result.message)
            self.assertEqual(len(list((root / "ponte").glob("*.md"))), 1)

    def test_prova_non_scrive_e_non_lancia(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            launcher = FakeLauncher(work / "lavoro" / "demo")
            before = sorted(str(p.relative_to(work)) for p in work.rglob("*"))
            result = self.run_case(root, work, cfg, launcher, dry_run=True)
            after = sorted(str(p.relative_to(work)) for p in work.rglob("*"))
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(launcher.calls, [])
            self.assertEqual(before, after)


class GateParserTests(unittest.TestCase):
    def parse(self, text, phase="gate_a"):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ("gate-a.md" if phase == "gate_a" else "gate-b.md")
            target = "brief" if phase == "gate_a" else "bozza"
            digest = hashlib.sha256(b"current").hexdigest()
            text = text.replace(f"Hash {target}: abc", f"Hash {target}: {digest}")
            path.write_text(text, encoding="utf-8")
            return redazione._parse_gate(path, phase, digest)

    def test_esito_deve_essere_intera_riga_esatta(self):
        with self.assertRaisesRegex(redazione.RedazioneError, "esito"):
            self.parse(gate_a("PASSA oppure FERMO"))
        with self.assertRaisesRegex(redazione.RedazioneError, "esito"):
            self.parse(gate_a("passa"))

    def test_gate_a_passa_solo_con_tutti_i_criteri_si(self):
        text = gate_a("PASSA").replace("| E | sì |", "| E | no |")
        with self.assertRaisesRegex(redazione.RedazioneError, "incoerente"):
            self.parse(text)

    def test_gate_a_fermo_con_tutti_si_e_voto_pieno_e_incoerente(self):
        text = gate_a("FERMO").replace("| A | no |", "| A | sì |")
        with self.assertRaisesRegex(redazione.RedazioneError, "incoerente"):
            self.parse(text)

    def test_gate_b_passa_solo_con_tutti_i_controlli_si(self):
        text = gate_b("PASSA", 4).replace("T: sì", "T: no")
        with self.assertRaisesRegex(redazione.RedazioneError, "incoerente"):
            self.parse(text, "gate_b")

    def test_gate_b_fermo_con_tutti_si_e_voto_5_e_incoerente(self):
        with self.assertRaisesRegex(redazione.RedazioneError, "incoerente"):
            self.parse(gate_b("FERMO", 5), "gate_b")

    def test_campi_devono_iniziare_la_riga(self):
        text = gate_a("PASSA").replace("Domanda: domanda", "nota Domanda: domanda")
        with self.assertRaisesRegex(redazione.RedazioneError, "Domanda"):
            self.parse(text)


class LauncherTests(unittest.TestCase):
    def test_terminal_alive_distinguishes_unknown_from_closed(self):
        with patch.object(redazione.subprocess, "run", return_value=redazione.subprocess.CompletedProcess(
                [], 1, "", "runtime unavailable")):
            self.assertIsNone(redazione._terminal_alive("term-1"))
        with patch.object(redazione.subprocess, "run", return_value=redazione.subprocess.CompletedProcess(
                [], 0, json.dumps({"ok": True, "result": {"terminals": []}}), "")):
            self.assertFalse(redazione._terminal_alive("term-1"))

    def test_lancio_usa_timeout_minimo_330_secondi_e_recupera_handle(self):
        phase = {"name": "scout", "choices": [{"agent": "codex", "model": "gpt-6-luna"}],
                 "timeout_seconds": 900}
        class StillRunning:
            def __init__(self, *_args, **_kwargs):
                pass
            def poll(self):
                return None

        with patch.object(redazione.subprocess, "Popen", side_effect=StillRunning) as popen, \
             patch.object(redazione.subprocess, "run", side_effect=[
            redazione.subprocess.CompletedProcess([], 0, json.dumps({"result": {"terminals": [
                {"handle": "term-recovered", "worktreePath": r"\\wsl.localhost\Ubuntu\home\nilo\divario-demo", "connected": True}
            ]}}), ""),
        ]):
            ticks = iter(range(0, 100_000, 60))
            progress = []
            result = redazione._orca_launcher(phase, Path("/tmp/divario-demo/lavoro/demo/SPEC.md"),
                worktree=Path("/tmp/divario-demo"), timeout=900,
                clock=lambda: next(ticks), sleep=lambda _: None, progress=progress.append)
        self.assertEqual(popen.call_count, 1)
        self.assertEqual(result["terminal_handle"], "term-recovered")
        self.assertTrue(any("minuti" in message for message in progress))

    def test_fallback_una_volta_su_fallimento_lancio(self):
        phase = {"name": "gate_b", "choices": [
            {"agent": "antigravity", "model": "gemini-3.1-pro-high"},
            {"agent": "codex", "model": "gpt-6-luna"}], "timeout_seconds": 900}
        calls = []

        def run(command, **kwargs):
            calls.append(command)
            if "worker-show" in command:
                return redazione.subprocess.CompletedProcess(command, 0, '{"result":{"worker":{"state":"succeeded"}}}', "")
            return redazione.subprocess.CompletedProcess(command, 0, "", "")

        class FakeProcess:
            count = 0
            def __init__(self, command, **kwargs):
                FakeProcess.count += 1
                calls.append(command)
                self.returncode = 1 if FakeProcess.count == 1 else 0
                if self.returncode == 0:
                    kwargs["stdout"].write("dispatch: d1\nterminale: t1")
            def poll(self):
                return self.returncode

        with patch.object(redazione, "_antigravity_model_matches", return_value=True), \
             patch.object(redazione.subprocess, "Popen", side_effect=FakeProcess), \
             patch.object(redazione.subprocess, "run", side_effect=run):
            result = redazione._orca_launcher(phase, Path("/tmp/divario-demo/lavoro/demo/SPEC.md"),
                worktree=Path("/tmp/divario-demo"), timeout=900, sleep=lambda _: None)
        launch_calls = [c for c in calls if c[0].endswith("orca-lancia.sh")]
        self.assertEqual(len(launch_calls), 2)
        self.assertIn("codex", launch_calls[1])
        self.assertTrue(result["success"])

    def test_fase_bozza_lancia_export_e_aggiorna_solo_pr_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            worktree = Path(tmp) / "divario-demo"
            workdir = worktree / "lavoro/demo"
            (worktree / "content/posts").mkdir(parents=True)
            workdir.mkdir(parents=True)
            (worktree / "content/posts/2026-10-07-demo.md").write_text("---\ntitle: Demo\n---\n", encoding="utf-8")
            (workdir / "brief.md").write_text("brief", encoding="utf-8")
            (workdir / "bozza.md").write_text("draft", encoding="utf-8")
            a_hash = hashlib.sha256((workdir / "brief.md").read_bytes()).hexdigest()
            b_hash = hashlib.sha256((workdir / "bozza.md").read_bytes()).hexdigest()
            (workdir / "gate-a.md").write_text(gate_a("PASSA").replace("Hash brief: abc", f"Hash brief: {a_hash}"), encoding="utf-8")
            (workdir / "gate-b.md").write_text(gate_b("PASSA", 4).replace("Hash bozza: abc", f"Hash bozza: {b_hash}"), encoding="utf-8")
            out = worktree / "drafts"
            calls = []

            def fake_run(command, **kwargs):
                calls.append(command)
                if command[:3] == ["gh", "pr", "list"]:
                    return redazione.subprocess.CompletedProcess(command, 0,
                        '[{"number":41,"isDraft":false},{"number":42,"isDraft":true}]', "")
                out.mkdir(parents=True, exist_ok=True)
                for name in ("20261007-demo.html", "index.html", "indice.json"):
                    (out / name).write_text("output", encoding="utf-8")
                return redazione.subprocess.CompletedProcess(command, 0, "", "")

            with patch.object(redazione, "BOZZA_OUT", out), \
                    patch.object(redazione.subprocess, "run", side_effect=fake_run), \
                    patch.object(redazione, "_update_pr_preview") as update:
                result = redazione._orca_launcher({"name": "bozza", "choices": []},
                    workdir / "SPEC-bozza.md", worktree=worktree, timeout=300)
            self.assertTrue(result["success"])
            self.assertEqual(update.call_args.args[2], 42)
            self.assertIn("scripts.editoriale.bozza_html", calls[1])
            self.assertEqual(calls[1][calls[1].index("--pr") + 1], "42")


class TemplateGateTests(unittest.TestCase):
    def test_i_template_dei_gate_riportano_tutti_i_campi_del_parser(self):
        radice = Path(__file__).resolve().parents[2] / "config" / "redazione"
        for fase, nome in (("gate_a", "gate_a.md"), ("gate_b", "gate_b.md")):
            testo = (radice / nome).read_text(encoding="utf-8")
            for campo in redazione.GATE_REQUIRED[fase]:
                self.assertIn(campo, testo, f"{nome}: manca {campo}")


if __name__ == "__main__":
    unittest.main()
