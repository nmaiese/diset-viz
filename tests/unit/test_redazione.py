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
            elif output == "brief.md":
                text = brief_v4()
            else:
                text = f"prova {phase['name']}\n"
            path.write_text(text, encoding="utf-8")
        return {"success": True, "terminal_handle": "term-fake", "model": "gpt-6-luna"}


def brief_v4():
    """Brief v4 con le righe che Gate A rilegge: definizione specifica e registro."""
    return """# Brief editoriale: demo

Domanda: i servizi per l'infanzia sono cresciuti dove servivano?
Dopo questa pagina, il lettore deve aver capito che…: la crescita osservata non dimostra accesso per tutte le famiglie
Scheda editoriale:
Domanda: i servizi per l'infanzia sono cresciuti dove servivano?
Definizione: iscritti di 0-2 anni su residenti della stessa età
Risultato centrale: la quota cresce nelle regioni osservate
Confronto: regioni nel 2023, riferimento Italia ufficiale
Rilevanza: misura l'uso di un servizio per le famiglie
Spiegazione: evidenze descrittive, cause non identificate
Limite decisivo: uso non equivale ad accessibilità
Passo successivo: confrontare costi e liste di attesa
Definizione specifica: bambini di 0-2 anni iscritti ai servizi comunali e privati convenzionati su 100 residenti della stessa età
Unità: per 100 bambini
Denominatore: residenti di 0-2 anni al 1 gennaio
Popolazione: bambini di 0-2 anni
Territorio: 20 regioni su 20 previste
Periodo: anno educativo 2023/2024
Fonte e release: Istat, servizi educativi per l'infanzia, release 2026-09-12

Registro affermazioni:
| affermazione | tipo | dato o calcolo | ambito e periodo | fonte |
|---|---|---|---|---|
| La quota sale in tutte le regioni | dato | 20 regioni su 20 in aumento | regioni, 0-2 anni, 2019-2023 | https://istat.example/dato |
| Le rette pesano sull'accesso | interpretazione | quota famiglie che rinunciano per costo | Italia, 2024 | https://ministero.example/rapporto |
"""


# Il brief del caso della review: hash giusto, nessuna definizione e nessun registro.
BRIEF_SENZA_DEFINIZIONE_NE_REGISTRO = "# Brief editoriale: demo\n\nDomanda: i servizi per l'infanzia sono cresciuti?\n"


def gate_a(outcome):
    text = f"""Contratto: v4.1
Tipo pezzo: blog
SHA brief: abc
Hash brief: abc
Autore/modello: A
Giudice/modello: B
Domanda: i servizi per l'infanzia sono cresciuti dove servivano?
Risposta in una frase: la quota di bambini presi in carico sale ovunque, ma la distanza fra regioni resta
Dopo questa pagina, il lettore deve aver capito che…: la crescita osservata non dimostra accesso per tutte le famiglie
Scheda editoriale:
Domanda: i servizi per l'infanzia sono cresciuti dove servivano?
Definizione: iscritti di 0-2 anni su residenti della stessa età
Risultato centrale: la quota cresce nelle regioni osservate
Confronto: regioni nel 2023, riferimento Italia ufficiale
Rilevanza: misura l'uso di un servizio per le famiglie
Spiegazione: evidenze descrittive, cause non identificate
Limite decisivo: uso non equivale ad accessibilità
Passo successivo: confrontare costi e liste di attesa
Variante: D servizi
Schema del racconto: domanda delle famiglie > quadro delle misure > offerta > utilizzo > limiti
Angoli verificati: angolo sul cambiamento osservato; angolo sulle differenze territoriali
Definizione specifica: bambini di 0-2 anni iscritti ai servizi comunali e privati convenzionati su 100 residenti della stessa età
Unità: per 100 bambini
Denominatore: residenti di 0-2 anni al 1 gennaio
Popolazione: bambini di 0-2 anni
Territorio: 20 regioni su 20 previste
Periodo: anno educativo 2023/2024
Fonte e release: Istat, servizi educativi per l'infanzia, release 2026-09-12
Riferimento usato: Italia ufficiale (30,0, Istat)
Codici e confronto: x/y/z
Ultimo dato: 2025
Data fonte del dato: 2026-09-12
URL fonte del dato: https://istat.example/dato
Ruolo indicatori interni: base e un tassello del racconto
Fonti esterne verificate:
| istituzione | data fonte | URL aperto | dato o claim | verificata |
|---|---|---|---|---|
| Istat | 2026-09-12 | https://istat.example/dato | dato 2025 | sì |
| Ministero | 2026-08-10 | https://ministero.example/rapporto | rapporto servizi | sì |
| Eurostat | 2026-07-01 | https://ec.europa.example/serie | serie comparabile | sì |
Grafico con dati esterni: disponibilità servizi; serie 2025; https://istat.example/dato
Figure previste: punti per regione con riferimento Italia ufficiale; serie della fascia centrale
Limiti: la presa in carico non misura costi, orari e attese
Registro affermazioni:
| affermazione | tipo | dato o calcolo | ambito e periodo | fonte |
|---|---|---|---|---|
| La quota sale in tutte le regioni | dato | 20 regioni su 20 in aumento | regioni, 0-2 anni, 2019-2023 | https://istat.example/dato |
| Le rette pesano sull'accesso | interpretazione | quota famiglie che rinunciano per costo | Italia, 2024 | https://ministero.example/rapporto |
| criterio | esito | prova verificabile | limite |
|---|---|---|---|
| Misura definita | sì | definizione con numeratore e denominatore 0-2 anni | servizi privati non convenzionati esclusi |
| Confronti compatibili | sì | stessa fascia e stesso anno educativo per le regioni | Trentino-Alto Adige aggregato |
| Livello delle affermazioni | sì | rette attribuite al rapporto ministeriale, nessuna causa | fonti non causali |
| Prove e figure | sì | ogni riga del registro ha la sua figura prevista | figura dei costi solo nazionale |
| Fonti e freschezza | sì | dato 2025 con data e URL fonte verificata | ultimo rilascio |
Esito: {outcome}
Motivo: motivazione riferita alle prove e al limite temporale
Correzione: correzione
Destinatario: leader
Data: 2026-10-08
"""
    return text.replace("| Misura definita | sì |", "| Misura definita | no |") if outcome == "FERMO" else text


def gate_a_v3(outcome):
    """Report Gate A v3 valido sotto il contratto v3, congelato: la v4 lo deve invalidare."""
    text = f"""Contratto: v3
Tipo pezzo: blog
SHA brief: abc
Hash brief: abc
Autore/modello: A
Giudice/modello: B
Domanda: domanda
Angoli verificati: angolo sul cambiamento osservato; angolo sulle differenze territoriali
Tesi: tesi
Codici e confronto: x/y/z
Ultimo dato: 2025
Data fonte del dato: 2026-09-12
URL fonte del dato: https://istat.example/dato
Ruolo indicatori interni: base e un tassello del racconto
Fonti esterne verificate:
| istituzione | data fonte | URL aperto | dato o claim | verificata |
|---|---|---|---|---|
| Istat | 2026-09-12 | https://istat.example/dato | dato 2025 | sì |
| Ministero | 2026-08-10 | https://ministero.example/rapporto | rapporto servizi | sì |
| Eurostat | 2026-07-01 | https://ec.europa.example/serie | serie comparabile | sì |
Grafico con dati esterni: disponibilità servizi; serie 2025; https://istat.example/dato
| criterio | esito | prova verificabile | limite |
|---|---|---|---|
| A | sì | angolo confrontato con fonti esterne datate | copertura regionale |
| B | sì | dato 2025 con data e URL fonte verificata | ultimo rilascio |
| C | sì | tre istituzioni con data, URL e claim distinti | fonti non causali |
| D | sì | grafico cita variabile esterna, periodo e URL | comparabilità |
| E | sì | indicatori interni dichiarati come base e tassello | ambito Italia |
Esito: {outcome}
Motivo: motivazione riferita alle prove e al limite temporale
Correzione: correzione
Destinatario: leader
Data: 2026-10-07
"""
    return text.replace("| A | sì |", "| A | no |") if outcome == "FERMO" else text


def gate_b(outcome, vote):
    return f"""Contratto: v4.1\nTipo pagina: articolo\nSHA bozza: abc\nHash bozza: abc\nFamiglie autore/revisore: A/B\nT: sì — La quota sale in tutte le regioni, registro: dato, regioni 0-2 anni 2019-2023, 20 regioni su 20, fonte Istat\nR: sì — citazione\nL: sì — citazione\nN: sì — citazione\nOltre la tabella: sì — la crescita non dimostra accessibilità; prova: confronto con costi e attese\nFunzione paragrafi: sì — ogni paragrafo risponde alla domanda o sostiene il passaggio; prova: apertura definisce, confronto misura, limite circoscrive\nControllo anti-invenzione: sì\nBloccanti: 0\nVoto: {vote}\nMotivo: motivo\nRilievi localizzati: nessuno\nGiri: 1\nEsito: {outcome}\n"""


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

    def test_gate_a_formalmente_fermo_salva_stato_e_motivo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            report = gate_a("PASSA").replace("Denominatore: residenti di 0-2 anni al 1 gennaio\n", "")
            launcher = FakeLauncher(work / "lavoro/demo", gates=[report])
            result = self.run_case(root, work, cfg, launcher, max_gate_a_retries=0)
            saved = json.loads((work / "lavoro/demo/stato.json").read_text(encoding="utf-8"))
            self.assertEqual(result.exit_code, 3)
            self.assertEqual(saved["phases"]["gate_a"]["status"], "fermo")
            self.assertIn("report: manca «Denominatore»", saved["phases"]["gate_a"]["motivo"])
            self.assertNotIn("autore", launcher.calls)

    def test_gate_a_concede_un_solo_ritorno_al_leader(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            launcher = FakeLauncher(work / "lavoro" / "demo", gates=[gate_a("FERMO"), gate_a("FERMO")])
            result = self.run_case(root, work, cfg, launcher)
            self.assertEqual(result.exit_code, 3)
            self.assertEqual(launcher.calls.count("brief"), 2)
            self.assertEqual(launcher.calls.count("gate_a"), 2)

    def test_motivo_del_fermo_non_resta_dopo_un_gate_a_passa(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            launcher = FakeLauncher(work / "lavoro" / "demo", gates=[gate_a("FERMO")])
            result = self.run_case(root, work, cfg, launcher)
            self.assertEqual(result.exit_code, 0, result.message)
            saved = json.loads((work / "lavoro/demo/stato.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["phases"]["gate_a"]["status"], "riuscita")
            self.assertNotIn("motivo", saved["phases"]["gate_a"])

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
                gate_a("PASSA"), gate_b("RISCRIVERE", 3),
                gate_b("FERMO", 2).replace("Giri: 1", "Giri: 2")])
            result = self.run_case(root, work, cfg, launcher)
            self.assertEqual(result.exit_code, 3)
            self.assertEqual(launcher.calls.count("autore"), 2)
            self.assertEqual(launcher.calls.count("gate_b"), 2)

    def test_gate_b_giri_report_devono_corrispondere_alla_seconda_bozza(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            workdir = work / "lavoro/demo"
            (workdir / "bozza.md").write_text("seconda bozza\n", encoding="utf-8")
            (workdir / "stato.json").write_text(json.dumps({"rewrite_rounds": 2}), encoding="utf-8")
            launcher = FakeLauncher(workdir, gates=[gate_b("PASSA", 4)])
            result = self.run_case(root, work, cfg, launcher, only="gate_b")
            saved = json.loads((workdir / "stato.json").read_text(encoding="utf-8"))
            self.assertEqual(result.exit_code, 1)
            self.assertIn("Giri", result.message)
            self.assertEqual(saved["phases"]["gate_b"]["status"], "fallita")
            self.assertEqual(launcher.calls, ["gate_b"])

    def test_ripresa_dopo_errore_non_rifà_fasi_riuscite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            first = FakeLauncher(work / "lavoro" / "demo", failures=["brief"])
            self.assertEqual(self.run_case(root, work, cfg, first).exit_code, 1)
            second = FakeLauncher(work / "lavoro" / "demo")
            self.assertEqual(self.run_case(root, work, cfg, second,
                                           terminal_alive=lambda _handle: False).exit_code, 0)
            self.assertNotIn("scout", second.calls)
            self.assertEqual(second.calls[0], "brief")

    def test_run_redazione_passa_ripiego_al_launcher(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = self.setup_case(tmp)
            cfg["phases"][0]["choices"] = [
                {"agent": "codex", "model": "gpt-6-luna"},
                {"agent": "claude", "model": "haiku"},
            ]
            actual = FakeLauncher(work / "lavoro" / "demo")
            choices_seen = []

            def launcher(phase, spec_path):
                choices_seen.append(phase["choices"])
                return actual(phase, spec_path)

            self.assertEqual(self.run_case(root, work, cfg, launcher, only="scout").exit_code, 0)
            self.assertEqual(choices_seen, [cfg["phases"][0]["choices"]])

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
            for attempt in range(2):
                launcher = FakeLauncher(work / "lavoro/demo", gates=[f"gate incompleto {attempt}"])
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
    def test_gate_a_ferma_frase_vuota_senza_leggere_scheda_editoriale(self):
        for target in ("brief", "report"):
            with self.subTest(target=target):
                brief, report = brief_v4(), gate_a("PASSA")
                if target == "brief":
                    brief = brief.replace("la crescita osservata non dimostra accesso per tutte le famiglie\nScheda editoriale:", "\nScheda editoriale:", 1)
                    self.assertEqual(redazione._field(brief, "Dopo questa pagina, il lettore deve aver capito che…"), "")
                else:
                    report = report.replace("la crescita osservata non dimostra accesso per tutte le famiglie\nScheda editoriale:", "\nScheda editoriale:", 1)
                    self.assertEqual(redazione._field(report, "Dopo questa pagina, il lettore deve aver capito che…"), "")
                self.assertEqual(self.parse(report, brief=brief), ("FERMO", ""))
        self.assertEqual(redazione._field(brief_v4(), "Definizione specifica"),
                         "bambini di 0-2 anni iscritti ai servizi comunali e privati convenzionati su 100 residenti della stessa età")

    def test_gate_a_ferma_frase_assente_o_sola_classifica(self):
        for value in (None, "X è prima e Y è ultima"):
            for target in ("brief", "report"):
                with self.subTest(value=value, target=target):
                    brief, report = brief_v4(), gate_a("PASSA")
                    if target == "brief":
                        brief = self.change_understanding(brief, value)
                    else:
                        report = self.change_understanding(report, value)
                    if value is None and target == "report":
                        with self.assertRaisesRegex(redazione.RedazioneError, "campi mancanti"):
                            self.parse(report, brief=brief)
                    else:
                        self.assertEqual(self.parse(report, brief=brief), ("FERMO", ""))

    @staticmethod
    def change_understanding(text, value):
        lines = text.splitlines()
        lines = [line for line in lines if not line.startswith("Dopo questa pagina, il lettore deve aver capito che…:")]
        if value is not None:
            lines.append("Dopo questa pagina, il lettore deve aver capito che…: " + value)
        return "\n".join(lines) + "\n"

    def test_gate_a_ferma_ogni_campo_della_scheda_editoriale_assente(self):
        for name in ("Domanda", "Definizione", "Risultato centrale", "Confronto", "Rilevanza",
                     "Spiegazione", "Limite decisivo", "Passo successivo"):
            for target in ("brief", "report"):
                with self.subTest(name=name, target=target):
                    brief, report = brief_v4(), gate_a("PASSA")
                    source = brief if target == "brief" else report
                    lines = source.splitlines()
                    start = lines.index("Scheda editoriale:")
                    idx = next(i for i in range(start + 1, start + 9) if lines[i].startswith(name + ":"))
                    del lines[idx]
                    if target == "brief":
                        brief = "\n".join(lines) + "\n"
                    else:
                        report = "\n".join(lines) + "\n"
                    self.assertEqual(self.parse(report, brief=brief), ("FERMO", ""))

    def test_gate_a_ferma_se_comprensione_o_scheda_divergono_dal_brief(self):
        changes = (
            ("la crescita osservata non dimostra accesso per tutte le famiglie", "il confronto da solo non spiega i costi"),
            ("Passo successivo: confrontare costi e liste di attesa", "Passo successivo: leggere altre classifiche"),
        )
        for before, after in changes:
            with self.subTest(before=before):
                self.assertEqual(self.parse(gate_a("PASSA").replace(before, after)), ("FERMO", ""))

    def test_gate_b_non_passa_senza_risposta_positiva_e_funzione_paragrafi(self):
        for prefix in ("Oltre la tabella:", "Funzione paragrafi:"):
            for replacement in (None, "no — prova insufficiente"):
                with self.subTest(prefix=prefix, replacement=replacement):
                    lines = gate_b("PASSA", 4).splitlines()
                    lines = [line if not line.startswith(prefix) else (prefix + " " + replacement if replacement else "") for line in lines]
                    with self.assertRaises(redazione.RedazioneError):
                        self.parse("\n".join(lines) + "\n", "gate_b")

    def test_gate_b_controlli_editoriali_negativi_ammettono_ciclo(self):
        for label in ("Oltre la tabella", "Funzione paragrafi"):
            for round_number, outcome in ((1, "RISCRIVERE"), (2, "FERMO")):
                with self.subTest(label=label, round_number=round_number):
                    text = gate_b(outcome, 4).replace(f"{label}: sì —", f"{label}: no —")
                    text = text.replace("Giri: 1", f"Giri: {round_number}")
                    self.assertEqual(self.parse(text, "gate_b"), (outcome, "4"))

    def test_gate_b_tipo_pagina_coerente_con_gate_a(self):
        text = gate_b("PASSA", 4).replace("Tipo pagina: articolo", "Tipo pagina: indicatore")
        self.assertEqual(self.parse(text, "gate_b"), ("FERMO", "4"))
        self.assertEqual(self.parse(gate_b("PASSA", 4), "gate_b", gate_a_type="scheda indicatore"),
                         ("FERMO", "4"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gate-b.md"
            path.write_text(gate_b("PASSA", 4).replace("Hash bozza: abc", f"Hash bozza: {hashlib.sha256(b'current').hexdigest()}"), encoding="utf-8")
            (Path(tmp) / "brief.md").write_text(brief_v4(), encoding="utf-8")
            self.assertEqual(redazione._parse_gate(path, "gate_b", hashlib.sha256(b"current").hexdigest()),
                             ("FERMO", "4"))

    def test_gate_a_tipi_territoriali_senza_obblighi_blog_o_scheda(self):
        for kind, variant in (("profilo territoriale", "profilo"), ("confronto territoriale", "confronto")):
            with self.subTest(kind=kind):
                report = gate_a("PASSA").replace("Tipo pezzo: blog", "Tipo pezzo: " + kind).replace("Variante: D servizi", "Variante: " + variant)
                report = report.replace("Angoli verificati: angolo sul cambiamento osservato; angolo sulle differenze territoriali", "Angoli verificati: non applicabile")
                report = report.replace("Ruolo indicatori interni: base e un tassello del racconto", "Ruolo indicatori interni: misure pertinenti alla domanda")
                report = report.replace("Grafico con dati esterni: disponibilità servizi; serie 2025; https://istat.example/dato", "Grafico con dati esterni: non richiesto")
                start = report.index("| istituzione | data fonte | URL aperto | dato o claim | verificata |")
                end = report.index("Grafico con dati esterni:", start)
                report = report[:start] + report[end:]
                report = report.replace("Figure previste: punti per regione con riferimento Italia ufficiale; serie della fascia centrale", "Figure previste: non applicabile")
                self.assertEqual(self.parse(report), ("PASSA", ""))

    def test_gate_a_v4_precedente_non_vale_anche_con_hash_invariato(self):
        with self.assertRaisesRegex(redazione.RedazioneError, "contratto"):
            self.parse(gate_a("PASSA").replace("Contratto: v4.1", "Contratto: v4"))

    def test_gate_b_tipi_territoriali_e_v4_precedente(self):
        for kind in ("profilo territoriale", "confronto territoriale"):
            with self.subTest(kind=kind):
                self.assertEqual(self.parse(gate_b("PASSA", 4).replace("Tipo pagina: articolo", "Tipo pagina: " + kind), "gate_b", gate_a_type=kind),
                                 ("PASSA", "4"))
        with self.assertRaisesRegex(redazione.RedazioneError, "contratto"):
            self.parse(gate_b("PASSA", 4).replace("Contratto: v4.1", "Contratto: v4"), "gate_b")

    def parse(self, text, phase="gate_a", brief=None, gate_a_type="blog"):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ("gate-a.md" if phase == "gate_a" else "gate-b.md")
            brief_path = Path(tmp) / "brief.md"
            brief_path.write_text(brief_v4() if brief is None else brief, encoding="utf-8")
            if phase == "gate_b":
                gate_a_text = gate_a("PASSA").replace("Hash brief: abc", f"Hash brief: {hashlib.sha256(brief_path.read_bytes()).hexdigest()}")
                if gate_a_type == "scheda indicatore":
                    gate_a_text = gate_a_text.replace("Tipo pezzo: blog", "Tipo pezzo: scheda indicatore")
                    gate_a_text = gate_a_text.replace("Variante: D servizi", "Variante: scheda provinciale")
                    gate_a_text = gate_a_text.replace("Ruolo indicatori interni: base e un tassello del racconto",
                                                     "Ruolo indicatori interni: indicatore spiegato e contesto")
                if gate_a_type in {"profilo territoriale", "confronto territoriale"}:
                    variant = "profilo" if gate_a_type == "profilo territoriale" else "confronto"
                    gate_a_text = gate_a_text.replace("Tipo pezzo: blog", f"Tipo pezzo: {gate_a_type}").replace("Variante: D servizi", f"Variante: {variant}")
                (Path(tmp) / "gate-a.md").write_text(gate_a_text, encoding="utf-8")
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
        text = gate_a("PASSA").replace("| Fonti e freschezza | sì |", "| Fonti e freschezza | no |")
        with self.assertRaisesRegex(redazione.RedazioneError, "incoerente"):
            self.parse(text)

    def test_gate_a_fermo_con_tutti_si_e_voto_pieno_e_incoerente(self):
        text = gate_a("FERMO").replace("| Misura definita | no |", "| Misura definita | sì |")
        with self.assertRaisesRegex(redazione.RedazioneError, "incoerente"):
            self.parse(text)

    def test_gate_a_v4_passa_con_definizione_registro_fonti_e_grafico(self):
        esito, _ = self.parse(gate_a("PASSA"))
        self.assertEqual(esito, "PASSA")

    def test_gate_a_rifiuta_limite_vuoto(self):
        text = gate_a("PASSA").replace("| servizi privati non convenzionati esclusi |", "| |")
        with self.assertRaisesRegex(redazione.RedazioneError, "limite"):
            self.parse(text)

    def test_gate_a_rifiuta_istituzioni_duplicate_con_maiuscole_diverse(self):
        text = gate_a("PASSA").replace("| Eurostat |", "| ISTAT |")
        with self.assertRaisesRegex(redazione.RedazioneError, "istituzioni distinte"):
            self.parse(text)

    def test_gate_a_ferma_se_mancano_fonti_grafico_o_date(self):
        casi = (
            gate_a("PASSA").replace("| Istat | 2026-09-12 | https://istat.example/dato | dato 2025 | sì |\n| Ministero | 2026-08-10 | https://ministero.example/rapporto | rapporto servizi | sì |\n| Eurostat | 2026-07-01 | https://ec.europa.example/serie | serie comparabile | sì |\n", ""),
            gate_a("PASSA").replace("Grafico con dati esterni: disponibilità servizi; serie 2025; https://istat.example/dato\n", ""),
            gate_a("PASSA").replace("| Istat | 2026-09-12 |", "| Istat | non trovata |"),
        )
        for text in casi:
            with self.subTest(text=text[:80]), self.assertRaises(redazione.RedazioneError):
                self.parse(text)

    def test_gate_a_v3_non_vale_per_contratto_v4(self):
        with self.assertRaisesRegex(redazione.RedazioneError, "contratto"):
            self.parse(gate_a_v3("PASSA"))
        text = gate_a("PASSA").replace("Contratto: v4", "Contratto: v3")
        with self.assertRaisesRegex(redazione.RedazioneError, "contratto"):
            self.parse(text)

    def test_gate_a_v4_passa_ferma_senza_definizione_specifica(self):
        senza = "\n".join(line for line in gate_a("PASSA").splitlines()
                          if not line.startswith("Definizione specifica:")) + "\n"
        casi = (
            senza,
            gate_a("PASSA").replace("Denominatore: residenti di 0-2 anni al 1 gennaio", "Denominatore: <denominatore>"),
            gate_a("PASSA").replace("Fonte e release: Istat, servizi educativi per l'infanzia, release 2026-09-12\n", ""),
            gate_a("PASSA").replace(
                "Definizione specifica: bambini di 0-2 anni iscritti ai servizi comunali e privati convenzionati su 100 residenti della stessa età",
                "Definizione specifica: esprime come percentuale il fenomeno nel gruppo di riferimento definito dalla fonte"),
        )
        for text in casi:
            with self.subTest(text=text[-120:]):
                self.assertEqual(self.parse(text), ("FERMO", ""))

    def test_gate_a_v4_passa_ferma_senza_registro(self):
        registro = gate_a("PASSA")
        inizio = registro.index("Registro affermazioni:")
        fine = registro.index("| criterio |")
        casi = (
            registro[:inizio] + registro[fine:],
            registro[:inizio] + "Registro affermazioni:\n| affermazione | tipo | dato o calcolo | ambito e periodo | fonte |\n|---|---|---|---|---|\n" + registro[fine:],
            registro.replace("| regioni, 0-2 anni, 2019-2023 |", "| |"),
            registro.replace("| La quota sale in tutte le regioni | dato |", "| La quota sale in tutte le regioni | opinione |"),
        )
        for text in casi:
            with self.subTest(text=text[inizio:inizio + 160]):
                self.assertEqual(self.parse(text), ("FERMO", ""))

    def test_gate_a_passa_ferma_se_il_brief_non_ha_definizione_ne_registro(self):
        # Riproduzione della review 1: hash del brief corrente giusto, report completo, PASSA.
        self.assertEqual(self.parse(gate_a("PASSA"), brief=BRIEF_SENZA_DEFINIZIONE_NE_REGISTRO), ("FERMO", ""))

    def test_gate_a_ferma_per_brief_con_definizione_generica_o_registro_incompleto(self):
        casi = (
            brief_v4().replace(
                "Definizione specifica: bambini di 0-2 anni iscritti ai servizi comunali e privati convenzionati su 100 residenti della stessa età",
                "Definizione specifica: esprime come percentuale il fenomeno nel gruppo di riferimento definito dalla fonte"),
            brief_v4().replace("Definizione specifica: bambini", "Definizione specifica: <bambini"),
            brief_v4().replace("| regioni, 0-2 anni, 2019-2023 |", "| |"),
            brief_v4().replace("Popolazione: bambini di 0-2 anni\n", ""),
        )
        for brief in casi:
            with self.subTest(brief=brief[60:200]):
                self.assertEqual(self.parse(gate_a("PASSA"), brief=brief), ("FERMO", ""))

    def test_gate_a_ferma_se_il_report_registra_affermazioni_assenti_dal_brief(self):
        text = gate_a("PASSA").replace("| La quota sale in tutte le regioni |", "| La quota raddoppia al Sud |")
        self.assertEqual(self.parse(text), ("FERMO", ""))

    def test_lacune_formali_distinte_per_brief_e_report_in_italiano(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "brief.md").write_text(BRIEF_SENZA_DEFINIZIONE_NE_REGISTRO, encoding="utf-8")
            report = Path(tmp) / "gate-a.md"
            report.write_text(gate_a("PASSA").replace("Unità: per 100 bambini\n", ""), encoding="utf-8")
            gaps = redazione.gate_a_formal_gaps(report)
            self.assertIn("brief: manca «Definizione specifica»", gaps)
            self.assertIn("brief: registro delle affermazioni assente o con righe incomplete", gaps)
            self.assertIn("report: manca «Unità»", gaps)
            self.assertNotIn("report: manca «Definizione specifica»", gaps)
            (Path(tmp) / "brief.md").write_text(brief_v4(), encoding="utf-8")
            report.write_text(gate_a("PASSA"), encoding="utf-8")
            self.assertEqual(redazione.gate_a_formal_gaps(report), [])

    def test_gate_a_senza_brief_accanto_non_vale(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "gate-a.md"
            report.write_text(gate_a("PASSA").replace("Hash brief: abc", f"Hash brief: {'0' * 64}"), encoding="utf-8")
            with self.assertRaisesRegex(redazione.RedazioneError, "brief.md"):
                redazione._parse_gate(report, "gate_a")

    def test_gate_a_v4_registro_accetta_le_diciture_del_tipo(self):
        for tipo in ("interpretazione documentata", "interpretazione attribuita", "dato o calcolo", "Limite"):
            text = gate_a("PASSA").replace("| Le rette pesano sull'accesso | interpretazione |",
                                           f"| Le rette pesano sull'accesso | {tipo} |")
            brief = brief_v4().replace("| Le rette pesano sull'accesso | interpretazione |",
                                       f"| Le rette pesano sull'accesso | {tipo} |")
            with self.subTest(tipo=tipo):
                self.assertEqual(self.parse(text, brief=brief), ("PASSA", ""))

    def test_gate_a_v4_criteri_fissi_e_variante_coerente(self):
        casi = (
            (gate_a("PASSA").replace("| Prove e figure |", "| Racconto |"), "criteri v4"),
            (gate_a("PASSA").replace("Variante: D servizi", "Variante: scheda provinciale"), "Variante"),
            (gate_a("PASSA").replace("Schema del racconto: domanda delle famiglie > quadro delle misure > offerta > utilizzo > limiti",
                                     "Schema del racconto: racconto libero"), "Schema"),
            (gate_a("PASSA").replace("Riferimento usato: Italia ufficiale (30,0, Istat)", "Riferimento usato: Italia"), "Riferimento"),
        )
        for text, errore in casi:
            with self.subTest(errore=errore), self.assertRaisesRegex(redazione.RedazioneError, errore):
                self.parse(text)

    def test_run_invalida_gate_a_v3_passa_anche_se_brief_non_cambia(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = RedazioneTests().setup_case(tmp)
            workdir = work / "lavoro/demo"
            brief = workdir / "brief.md"
            brief.write_text(brief_v4(), encoding="utf-8")
            digest = hashlib.sha256(brief.read_bytes()).hexdigest()
            old_gate = workdir / "gate-a.md"
            old_gate.write_text(gate_a_v3("PASSA").replace("Hash brief: abc", f"Hash brief: {digest}"),
                                encoding="utf-8")
            state = {
                "key": "demo", "current_phase": "autore", "gate_a_sha": digest,
                "gate_a_contract_version": "v3", "phases": {"gate_a": {
                    "status": "riuscita", "input_hashes": {},
                    "output_hashes": {"lavoro/demo/gate-a.md": hashlib.sha256(old_gate.read_bytes()).hexdigest()},
                }},
            }
            (workdir / "stato.json").write_text(json.dumps(state), encoding="utf-8")
            blocked = FakeLauncher(workdir)
            result = RedazioneTests().run_case(root, work, cfg, blocked, only="autore")
            self.assertEqual(result.exit_code, 1)
            self.assertIn("Gate A v4", result.message)
            self.assertEqual(blocked.calls, [])

            (workdir / "stato.json").write_text(json.dumps(state), encoding="utf-8")
            launcher = FakeLauncher(workdir)
            result = RedazioneTests().run_case(root, work, cfg, launcher, only="gate_a")
            self.assertEqual(result.exit_code, 0, result.message)
            self.assertEqual(launcher.calls, ["gate_a"])
            saved = json.loads((workdir / "stato.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["gate_a_contract_version"], "v4.1")
            self.assertEqual(saved["gate_a_sha"], digest)

    def test_run_invalida_gate_a_v4_passa_sullo_stesso_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = RedazioneTests().setup_case(tmp)
            workdir = work / "lavoro/demo"
            brief = workdir / "brief.md"
            brief.write_text(brief_v4(), encoding="utf-8")
            digest = hashlib.sha256(brief.read_bytes()).hexdigest()
            old_gate = workdir / "gate-a.md"
            old_gate.write_text(gate_a("PASSA").replace("Contratto: v4.1", "Contratto: v4")
                                .replace("Hash brief: abc", f"Hash brief: {digest}"), encoding="utf-8")
            (workdir / "stato.json").write_text(json.dumps({
                "gate_a_sha": digest, "gate_a_contract_version": "v4",
                "phases": {"gate_a": {"status": "riuscita"}},
            }), encoding="utf-8")
            blocked = FakeLauncher(workdir)
            result = RedazioneTests().run_case(root, work, cfg, blocked, only="autore")
            self.assertEqual(result.exit_code, 1)
            self.assertEqual(blocked.calls, [])
            launcher = FakeLauncher(workdir)
            result = RedazioneTests().run_case(root, work, cfg, launcher, only="gate_a")
            self.assertEqual(result.exit_code, 0, result.message)
            self.assertEqual(launcher.calls, ["gate_a"])
            saved = json.loads((workdir / "stato.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["gate_a_sha"], digest)
            self.assertEqual(saved["gate_a_contract_version"], "v4.1")

    def test_autore_non_parte_se_gate_a_v4_dice_passa_senza_definizione(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = RedazioneTests().setup_case(tmp)
            workdir = work / "lavoro/demo"
            senza = "\n".join(line for line in gate_a("PASSA").splitlines()
                              if not line.startswith("Definizione specifica:")) + "\n"
            launcher = FakeLauncher(workdir, gates=[senza, senza])
            result = RedazioneTests().run_case(root, work, cfg, launcher)
            self.assertEqual(result.exit_code, 3)
            self.assertNotIn("autore", launcher.calls)
            self.assertEqual(launcher.calls.count("gate_a"), 2)

    def test_autore_non_parte_se_gate_a_cambia_dato_o_definizione_del_brief(self):
        changes = (
            ("| 20 regioni su 20 in aumento |", "| 10 regioni su 20 in aumento |", "dato o calcolo"),
            ("Definizione specifica: bambini di 0-2 anni iscritti", "Definizione specifica: posti disponibili", "Definizione specifica"),
        )
        for before, after, reason in changes:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as tmp:
                root, work, cfg = RedazioneTests().setup_case(tmp)
                workdir = work / "lavoro/demo"
                brief = workdir / "brief.md"
                brief.write_text(brief_v4().replace(before, after), encoding="utf-8")
                digest = hashlib.sha256(brief.read_bytes()).hexdigest()
                gate = workdir / "gate-a.md"
                gate.write_text(gate_a("PASSA").replace("Hash brief: abc", f"Hash brief: {digest}"), encoding="utf-8")
                state = {"gate_a_sha": digest, "gate_a_contract_version": "v4.1",
                         "phases": {"gate_a": {"status": "riuscita"}}}
                (workdir / "stato.json").write_text(json.dumps(state), encoding="utf-8")
                launcher = FakeLauncher(workdir)
                result = RedazioneTests().run_case(root, work, cfg, launcher, only="autore")
                self.assertEqual(result.exit_code, 1, result.message)
                self.assertIn(reason, result.message)
                self.assertEqual(launcher.calls, [])

    def test_autore_non_parte_se_il_brief_corrente_non_ha_definizione_ne_registro(self):
        # Riproduzione della review 1 sulla sequenza: il ponte dice che cosa manca e dove.
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = RedazioneTests().setup_case(tmp)
            workdir = work / "lavoro/demo"

            launcher = FakeLauncher(workdir)
            original = launcher.__call__

            def call(phase, spec_path):
                if phase["name"] == "brief":
                    launcher.calls.append("brief")
                    (workdir / "brief.md").write_text(BRIEF_SENZA_DEFINIZIONE_NE_REGISTRO, encoding="utf-8")
                    return {"success": True, "terminal_handle": "term-fake", "model": "gpt-6-luna"}
                return original(phase, spec_path)

            result = RedazioneTests().run_case(root, work, cfg, call)
            self.assertEqual(result.exit_code, 3)
            self.assertNotIn("autore", launcher.calls)
            self.assertEqual(launcher.calls.count("gate_a"), 2)
            self.assertIn("validazione formale", result.message)
            message = next((root / "ponte").glob("*.md")).read_text(encoding="utf-8")
            motivo = next(line for line in message.splitlines() if line.startswith("Motivo:"))
            self.assertIn("FERMO, voto n/d per validazione formale, non giudizio di merito", motivo)
            self.assertIn("brief: manca «Definizione specifica»", motivo)
            self.assertIn("brief: registro delle affermazioni assente o con righe incomplete", motivo)
            self.assertNotIn("report:", motivo)
            saved = json.loads((workdir / "stato.json").read_text(encoding="utf-8"))
            self.assertIn("brief: manca «Definizione specifica»", saved["phases"]["gate_a"]["motivo"])

    def test_autore_non_parte_se_gate_a_non_e_v4_corrente(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = RedazioneTests().setup_case(tmp)
            workdir = work / "lavoro/demo"
            (workdir / "brief.md").write_text("brief stabile\n", encoding="utf-8")
            (workdir / "gate-a.md").write_text("Contratto: v3\nEsito: PASSA\n", encoding="utf-8")
            launcher = FakeLauncher(workdir)
            result = RedazioneTests().run_case(root, work, cfg, launcher, only="autore")
            self.assertEqual(result.exit_code, 1)
            self.assertIn("Gate A", result.message)
            self.assertEqual(launcher.calls, [])

    def test_gate_b_sotto_4_non_passa(self):
        with self.assertRaisesRegex(redazione.RedazioneError, "incoerente"):
            self.parse(gate_b("PASSA", 3), "gate_b")
        self.assertEqual(self.parse(gate_b("RISCRIVERE", 3), "gate_b"), ("RISCRIVERE", "3"))

    def test_gate_b_senza_contratto_v4_non_vale(self):
        text = gate_b("PASSA", 4).replace("Contratto: v4.1\n", "")
        with self.assertRaisesRegex(redazione.RedazioneError, "contratto"):
            self.parse(text, "gate_b")
        with self.assertRaisesRegex(redazione.RedazioneError, "contratto"):
            self.parse(gate_b("PASSA", 4).replace("Contratto: v4.1", "Contratto: v2"), "gate_b")

    def test_run_rifà_gate_b_scritto_prima_della_v4(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = RedazioneTests().setup_case(tmp)
            workdir = work / "lavoro/demo"
            draft = workdir / "bozza.md"
            draft.write_text("bozza stabile\n", encoding="utf-8")
            (workdir / "brief.md").write_text(brief_v4(), encoding="utf-8")
            brief_digest = hashlib.sha256((workdir / "brief.md").read_bytes()).hexdigest()
            (workdir / "gate-a.md").write_text(gate_a("PASSA").replace("Hash brief: abc", f"Hash brief: {brief_digest}"), encoding="utf-8")
            digest = hashlib.sha256(draft.read_bytes()).hexdigest()
            (workdir / "stato.json").write_text(json.dumps({
                "key": "demo", "gate_b_sha": digest, "phases": {"gate_b": {"status": "riuscita"}},
            }), encoding="utf-8")
            launcher = FakeLauncher(workdir)
            result = RedazioneTests().run_case(root, work, cfg, launcher, only="gate_b")
            self.assertEqual(result.exit_code, 0, result.message)
            self.assertEqual(launcher.calls, ["gate_b"])
            saved = json.loads((workdir / "stato.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["gate_b_contract_version"], "v4.1")

    def test_run_invalida_gate_b_v4_passa_sullo_stesso_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, work, cfg = RedazioneTests().setup_case(tmp)
            workdir = work / "lavoro/demo"
            brief = workdir / "brief.md"
            brief.write_text(brief_v4(), encoding="utf-8")
            brief_digest = hashlib.sha256(brief.read_bytes()).hexdigest()
            (workdir / "gate-a.md").write_text(gate_a("PASSA").replace("Hash brief: abc", f"Hash brief: {brief_digest}"), encoding="utf-8")
            draft = workdir / "bozza.md"
            draft.write_text("bozza stabile\n", encoding="utf-8")
            digest = hashlib.sha256(draft.read_bytes()).hexdigest()
            (workdir / "gate-b.md").write_text(gate_b("PASSA", 4).replace("Contratto: v4.1", "Contratto: v4")
                                                 .replace("Hash bozza: abc", f"Hash bozza: {digest}"), encoding="utf-8")
            (workdir / "stato.json").write_text(json.dumps({
                "gate_b_sha": digest, "gate_b_contract_version": "v4",
                "phases": {"gate_b": {"status": "riuscita"}},
            }), encoding="utf-8")
            launcher = FakeLauncher(workdir)
            result = RedazioneTests().run_case(root, work, cfg, launcher, only="gate_b")
            self.assertEqual(result.exit_code, 0, result.message)
            self.assertEqual(launcher.calls, ["gate_b"])
            saved = json.loads((workdir / "stato.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["gate_b_sha"], digest)
            self.assertEqual(saved["gate_b_contract_version"], "v4.1")

    def test_gate_b_accetta_solo_giri_uno_o_due(self):
        # Riproduzione della review 1: PASSA con «Giri: 3» passava benché il massimo sia due.
        for giri in ("3", "0", "<1 o 2>", "1 o 2", ""):
            text = gate_b("PASSA", 4).replace("Giri: 1", f"Giri: {giri}")
            with self.subTest(giri=giri), self.assertRaisesRegex(redazione.RedazioneError, "Giri"):
                self.parse(text, "gate_b")
        self.assertEqual(self.parse(gate_b("PASSA", 4).replace("Giri: 1", "Giri: 2"), "gate_b"), ("PASSA", "4"))

    def test_gate_b_riscrivere_al_secondo_giro_e_incoerente(self):
        text = gate_b("RISCRIVERE", 3).replace("Giri: 1", "Giri: 2")
        with self.assertRaisesRegex(redazione.RedazioneError, "incoerente"):
            self.parse(text, "gate_b")
        self.assertEqual(self.parse(gate_b("FERMO", 3).replace("Giri: 1", "Giri: 2"), "gate_b"), ("FERMO", "3"))

    def test_gate_b_passa_solo_con_tutti_i_controlli_si(self):
        text = gate_b("PASSA", 4).replace("T: sì", "T: no")
        with self.assertRaisesRegex(redazione.RedazioneError, "incoerente"):
            self.parse(text, "gate_b")

    def test_gate_b_ferma_se_registro_manca_o_citazione_non_corrisponde(self):
        self.assertEqual(self.parse(gate_b("PASSA", 4), "gate_b", brief="brief senza registro"),
                         ("FERMO", "4"))
        without_match = gate_b("PASSA", 4).replace("La quota sale in tutte le regioni", "Una frase non nel registro")
        self.assertEqual(self.parse(without_match, "gate_b"), ("FERMO", "4"))

    def test_gate_b_fermo_con_tutti_si_e_voto_5_e_incoerente(self):
        with self.assertRaisesRegex(redazione.RedazioneError, "incoerente"):
            self.parse(gate_b("FERMO", 5), "gate_b")

    def test_campi_devono_iniziare_la_riga(self):
        text = gate_a("PASSA").replace("Domanda: i servizi", "nota Domanda: i servizi")
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
            self.assertIn("REDAZIONE-divario-v4.md", testo)
            self.assertNotIn("REDAZIONE-divario-v3.md", testo)
            if fase == "gate_b":
                for campo in redazione.GATE_REQUIRED[fase]:
                    self.assertIn(campo, testo, f"{nome}: manca {campo}")

    def test_il_template_del_brief_riporta_le_righe_che_gate_a_rilegge(self):
        testo = (Path(__file__).resolve().parents[2] / "config" / "redazione" / "brief.md").read_text(encoding="utf-8")
        for campo in redazione.GATE_A_DEFINITION_FIELDS:
            self.assertIn(f"\n{campo}: <", testo, f"brief.md: manca {campo}")
        self.assertIn(redazione.CLAIM_HEADER, testo)


if __name__ == "__main__":
    unittest.main()
