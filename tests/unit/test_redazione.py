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
    return f"""SHA brief: abc\nHash brief: abc\nAutore/modello: A\nGiudice/modello: B\nDomanda: domanda\nTesi: tesi\nCodici e confronto: x/y/z\n| criterio | sì/no | prova | limite |\n|---|---|---|---|\n| A | sì | prova | limite |\n| B | sì | prova | limite |\n| C | sì | prova | limite |\n| D | sì | prova | limite |\n| E | sì | prova | limite |\nEsito: {outcome}\nMotivo: motivo\nCorrezione: correzione\nDestinatario: leader\nData: 2026-10-07\n"""


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

    def test_aggiornamento_pr_conserva_testo_e_firma(self):
        seen = []

        def fake_run(command, **kwargs):
            if "view" in command:
                return redazione.subprocess.CompletedProcess(command, 0, "Testo PR esistente\n", "")
            seen.append(Path(command[-1]).read_text(encoding="utf-8"))
            return redazione.subprocess.CompletedProcess(command, 0, "", "")

        with patch.dict(redazione.os.environ, {"AGENT_ID": ""}), \
                patch.object(redazione.subprocess, "run", side_effect=fake_run):
            redazione._update_pr_preview(Path("/tmp/worktree"), 17, Path("/tmp/preview.html"),
                                         Path("/tmp/index.html"), "a" * 64, "b" * 64)
        self.assertIn("Testo PR esistente", seen[0])
        self.assertIn("Gate B: PASSA", seen[0])
        self.assertTrue(seen[0].rstrip().endswith("— codex-gpt-6-luna"))

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

    def test_gate_malformato_blocca(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            launcher = FakeLauncher(work / "lavoro" / "demo", gates=["Esito: PASSA\n"])
            result = self.run_case(root, work, cfg, launcher)
            self.assertEqual(result.exit_code, 1)
            self.assertEqual(launcher.calls, ["scout", "brief", "gate_a"])

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


class TemplateGateTests(unittest.TestCase):
    def test_i_template_dei_gate_riportano_tutti_i_campi_del_parser(self):
        radice = Path(__file__).resolve().parents[2] / "config" / "redazione"
        for fase, nome in (("gate_a", "gate_a.md"), ("gate_b", "gate_b.md")):
            testo = (radice / nome).read_text(encoding="utf-8")
            for campo in redazione.GATE_REQUIRED[fase]:
                self.assertIn(campo, testo, f"{nome}: manca {campo}")


if __name__ == "__main__":
    unittest.main()
