"""Orchestrazione sequenziale della redazione, con stato riprendibile."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "redazione.yaml"
BOZZA_OUT = Path("/mnt/c/Users/Nilo/orca/divario/bozze")
DEFAULT_PHASES = ("scout", "brief", "gate_a", "autore", "grafico", "guardia", "gate_b", "bozza")
PHASE_LABEL = {"gate_a": "a", "gate_b": "b"}
KEY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass
class Result:
    exit_code: int
    message: str


class RedazioneError(RuntimeError):
    pass


def _hash(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _head_sha(worktree: Path) -> str | None:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=worktree, capture_output=True,
                            text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def _set_issue_label(issue: str, label: str, *, add: bool) -> None:
    action = "--add-label" if add else "--remove-label"
    result = subprocess.run(["gh", "issue", "edit", issue, action, label], cwd=ROOT,
                            capture_output=True, text=True, check=False)
    if result.returncode:
        verb = "aggiungere" if add else "rimuovere"
        raise RedazioneError(f"impossibile {verb} label {label}: {result.stderr.strip()}")


def _update_pr_preview(worktree: Path, key: str, pr: int, html_path: Path, index_path: Path,
                       brief_hash: str, draft_hash: str) -> None:
    current = subprocess.run(["gh", "pr", "view", str(pr), "--json", "body", "--jq", ".body"],
                             cwd=worktree, capture_output=True, text=True, check=True)
    marker = "<!-- divario-redazione-preview -->"
    body = current.stdout.rstrip()
    if marker in body:
        body = body.split(marker, 1)[0].rstrip()
    workdir = worktree / "lavoro" / key
    gate_a, _ = _parse_gate(workdir / "gate-a.md", "gate_a", brief_hash)
    gate_b, _ = _parse_gate(workdir / "gate-b.md", "gate_b", draft_hash)
    signature = os.environ.get("AGENT_ID", "").strip()
    block = (f"{marker}\n## Anteprima editoriale\nStato: da leggere\n"
             f"Gate A: {gate_a} (SHA-256 `{brief_hash}`)\nGate B: {gate_b} (SHA-256 `{draft_hash}`)\n"
             f"HTML locale: `{html_path}`\nIndice locale: `{index_path}`"
             + (f"\n\n— {signature}" if signature else ""))
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as handle:
        handle.write((body + "\n\n" if body else "") + block + "\n")
        body_file = Path(handle.name)
    try:
        subprocess.run(["gh", "pr", "edit", str(pr), "--body-file", str(body_file)],
                       cwd=worktree, capture_output=True, text=True, check=True)
    finally:
        body_file.unlink(missing_ok=True)


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def _memory_available_mb() -> int:
    result = subprocess.run(["free", "-m"], capture_output=True, text=True, check=True)
    for line in result.stdout.splitlines():
        if line.lower().startswith("mem:"):
            fields = line.split()
            return int(fields[6] if len(fields) > 6 else fields[3])
    raise RedazioneError("free -m non ha restituito la riga Mem:")


def _terminal_alive(handle: str) -> bool | None:
    try:
        result = subprocess.run(["orca-ide", "terminal", "list", "--json"], capture_output=True,
                                text=True, timeout=15, check=False)
        payload = json.loads(result.stdout or "{}")
        terminals = payload.get("result", {}).get("terminals")
        if result.returncode != 0 or payload.get("ok") is not True or not isinstance(terminals, list):
            return None
        return any(t.get("handle") == handle and t.get("state") not in {"closed", "exited"}
                   for t in terminals)
    except (OSError, ValueError, TypeError, AttributeError, subprocess.TimeoutExpired):
        return None


def _parse_output(stdout: str, marker: str) -> str | None:
    match = re.search(rf"^{re.escape(marker)}:\s*(\S+)\s*$", stdout, re.MULTILINE)
    return match.group(1) if match else None


def _antigravity_model_matches(model: str) -> bool:
    settings = Path.home() / ".gemini/antigravity-cli/settings.json"
    try:
        value = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    wanted = re.sub(r"[^a-z0-9]", "", model.lower())
    stack = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for key, item in current.items():
                if key.lower() in {"model", "modelname", "model_name", "selectedmodel"} and isinstance(item, str):
                    normalized = re.sub(r"[^a-z0-9]", "", item.lower())
                    if wanted in normalized or normalized in wanted:
                        return True
                elif isinstance(item, (dict, list)):
                    stack.append(item)
        elif isinstance(current, list):
            stack.extend(current)
    return False


def _orca_launcher(phase: dict, spec_path: Path, *, worktree: Path, timeout: int,
                   clock: Callable[[], float] = time.monotonic,
                   sleep: Callable[[float], None] = time.sleep,
                   progress: Callable[[str], None] = print) -> dict:
    """Avvia via orca-lancia e attende worker_done, con battito ogni 20 secondi."""
    if phase["name"] == "bozza":
        if importlib.util.find_spec("scripts.editoriale.bozza_html") is None:
            raise RedazioneError("manca scripts/editoriale/bozza_html.py; export e PR draft non eseguibili in questo worktree")
        pr = subprocess.run(["gh", "pr", "list", "--head", f"divario/{spec_path.parent.name}",
                             "--state", "open", "--json", "number,isDraft"], cwd=worktree,
                            capture_output=True, text=True, timeout=20, check=True)
        drafts = [item for item in json.loads(pr.stdout) if item.get("isDraft")]
        if len(drafts) != 1:
            raise RedazioneError(f"serve una sola PR draft aperta del pezzo, trovate {len(drafts)}")
        posts = sorted((worktree / "content" / "posts").glob(f"*-{spec_path.parent.name}.md"))
        dated = next((re.match(r"(\d{4}-\d{2}-\d{2})-", post.name) for post in posts
                      if re.match(r"\d{4}-\d{2}-\d{2}-", post.name)), None)
        if not dated:
            raise RedazioneError(f"nessun articolo blog datato per {spec_path.parent.name}")
        day = dated.group(1).replace("-", "")
        output_dir = BOZZA_OUT
        html_path = output_dir / f"{day}-{spec_path.parent.name}.html"
        index_path = output_dir / "index.html"
        registry_path = output_dir / "indice.json"
        command = [str(worktree / "bin" / "py"), "-m", "scripts.editoriale.bozza_html",
                   spec_path.parent.name, "--radice", str(worktree), "--pr",
                   str(drafts[0]["number"]), "--stato", "da leggere"]
        completed = subprocess.run(command, cwd=worktree, capture_output=True, text=True,
                                   timeout=timeout, check=False)
        artifacts_ready = all(path.is_file() for path in (html_path, index_path, registry_path))
        if completed.returncode == 0 and artifacts_ready:
            gate_a_hash = _hash(worktree / "lavoro" / spec_path.parent.name / "brief.md") or ""
            gate_b_hash = _hash(worktree / "lavoro" / spec_path.parent.name / "bozza.md") or ""
            _update_pr_preview(worktree, spec_path.parent.name, int(drafts[0]["number"]), html_path, index_path,
                               gate_a_hash, gate_b_hash)
            receipt = {"html": str(html_path), "html_sha256": _hash(html_path),
                       "index": str(index_path), "registry": str(registry_path),
                       "pr": drafts[0]["number"], "stato": "da leggere"}
            (worktree / "lavoro" / spec_path.parent.name / "bozza.json").write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"success": completed.returncode == 0 and artifacts_ready, "model": None,
                "output": (completed.stdout + completed.stderr)[-2000:]}
    if phase["name"] == "guardia":
        output = worktree / "lavoro" / spec_path.parent.name / "guardia.json"
        article = worktree / "lavoro" / spec_path.parent.name / "bozza.md"
        cmd = [sys.executable, "-m", "scripts.editoriale.guardia_articolo", str(article), "--json"]
        checked = subprocess.run(cmd, cwd=worktree, capture_output=True, text=True, timeout=timeout, check=False)
        output.write_text(checked.stdout or checked.stderr, encoding="utf-8")
        return {"success": checked.returncode == 0, "model": None}

    choices = phase.get("choices", [])
    if not choices:
        raise RedazioneError(f"config senza modello per {phase['name']}")
    choice = choices[0]
    if choice["agent"] == "antigravity" and choice.get("model") and not _antigravity_model_matches(choice["model"]):
        if len(choices) > 1:
            fallback = dict(phase)
            fallback["choices"] = choices[1:2]
            progress(f"{phase['name']}: modello antigravity assente; provo seconda scelta una volta")
            return _orca_launcher(fallback, spec_path, worktree=worktree, timeout=timeout,
                                  clock=clock, sleep=sleep, progress=progress)
        raise RedazioneError("modello Antigravity della fase non coincide con settings.json; configurarlo prima del rilancio")
    launcher = os.environ.get("ORCA_LANCIA", str(Path.home() / "dev/dev-tools/scripts/orca-lancia.sh"))
    command = [launcher, "--agent", choice["agent"], "--worktree", worktree.name,
               "--spec-file", str(spec_path)]
    if choice.get("model") and choice["agent"] != "antigravity":
        command.extend(["--model", choice["model"]])
    started = clock()
    launch_timeout = max(330, min(timeout, 330))
    try:
        completed = _run_launch_command(command, cwd=worktree, timeout=launch_timeout,
                                        clock=clock, sleep=sleep, progress=progress,
                                        phase_name=phase["name"])
    except OSError:
        if len(choices) > 1:
            fallback = dict(phase)
            fallback["choices"] = choices[1:2]
            progress(f"{phase['name']}: prima scelta non disponibile; provo seconda scelta una volta")
            return _orca_launcher(fallback, spec_path, worktree=worktree, timeout=timeout,
                                  clock=clock, sleep=sleep, progress=progress)
        raise
    if completed is None:
        progress(f"{phase['name']}: lancio ancora in attesa dopo {launch_timeout} secondi")
        recovered = subprocess.run(["orca-ide", "terminal", "list", "--json"],
                                   capture_output=True, text=True, timeout=20, check=False)
        handle = _recover_terminal_handle(recovered.stdout, worktree.name)
        return {"success": False, "terminal_handle": handle, "dispatch_id": None,
                "model": choice.get("model"), "worker_state": "in corso" if handle else None,
                "output": "timeout del lancio; verificato elenco terminali"}
    transcript = completed.stdout + "\n" + completed.stderr
    handle = _parse_output(transcript, "terminale")
    dispatch = _parse_output(transcript, "dispatch")
    if completed.returncode != 0 and len(choices) > 1:
        fallback = dict(phase)
        fallback["choices"] = choices[1:2]
        return _orca_launcher(fallback, spec_path, worktree=worktree, timeout=timeout,
                              clock=clock, sleep=sleep, progress=progress)
    worker_state = None
    while dispatch and clock() - started < timeout:
        worker = subprocess.run(["orca-ide", "orchestration", "worker-show", "--dispatch", dispatch,
                                 "--json"], capture_output=True, text=True, timeout=20, check=False)
        try:
            worker_state = json.loads(worker.stdout).get("result", {}).get("worker", {}).get("state")
        except (ValueError, AttributeError):
            worker_state = None
        if worker_state in {"succeeded", "failed", "stopped", "stop_unknown"}:
            break
        progress(f"{phase['name']}: worker ancora attivo ({worker_state or 'stato non letto'})")
        sleep(min(20, max(0, timeout - (clock() - started))))
    success = completed.returncode == 0 and worker_state == "succeeded"
    terminal_state = worker_state in {"succeeded", "failed", "stopped", "stop_unknown"}
    if handle and terminal_state:
        subprocess.run(["orca-ide", "terminal", "close", "--terminal", handle, "--json"],
                       capture_output=True, text=True, timeout=20, check=False)
    return {"success": success, "terminal_handle": handle, "dispatch_id": dispatch,
            "model": choice.get("model"), "worker_state": worker_state,
            "output": transcript[-2000:]}


def _run_launch_command(command: list[str], *, cwd: Path, timeout: int,
                        clock: Callable[[], float], sleep: Callable[[float], None],
                        progress: Callable[[str], None], phase_name: str):
    """Attende orca-lancia senza terminarlo e mostra avanzamento ogni minuto."""
    started = clock()
    next_update = 60
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as stdout, \
            tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as stderr:
        process = subprocess.Popen(command, cwd=cwd, stdout=stdout, stderr=stderr, text=True)
        while process.poll() is None:
            elapsed = clock() - started
            if elapsed >= timeout:
                return None
            if elapsed >= next_update:
                progress(f"{phase_name}: lanciatore in corso da {int(elapsed // 60)} minuti")
                next_update = (int(elapsed // 60) + 1) * 60
            wait = min(1.0, timeout - elapsed, max(0.05, next_update - elapsed))
            sleep(wait)
        stdout.seek(0)
        stderr.seek(0)
        return subprocess.CompletedProcess(command, process.returncode, stdout.read(), stderr.read())


def _recover_terminal_handle(payload_text: str, worktree_name: str) -> str | None:
    try:
        terminals = json.loads(payload_text).get("result", {}).get("terminals", [])
    except (ValueError, AttributeError):
        return None
    def belongs(terminal: dict) -> bool:
        values = (terminal.get("worktree"), terminal.get("worktree_name"), terminal.get("worktreePath"))
        return any(isinstance(value, str) and value.replace("\\", "/").rstrip("/").split("/")[-1] == worktree_name
                   for value in values)

    matches = [t for t in terminals if isinstance(t, dict) and belongs(t)
               and t.get("state") not in {"closed", "exited"} and t.get("connected") is not False
               and t.get("handle")]
    return matches[-1].get("handle") if matches else None


def _template(phase: dict, key: str, issue: str, worktree: Path, input_files: list[Path],
              output_files: list[Path], config_root: Path) -> str:
    template_path = config_root / "redazione" / phase["template"]
    if not template_path.is_file():
        raise RedazioneError(f"template assente: {template_path}")
    values = {"chiave": key, "issue": issue, "worktree": str(worktree),
              "input": "\n".join(str(p) for p in input_files),
              "output": "\n".join(str(p) for p in output_files)}
    return template_path.read_text(encoding="utf-8").format(**values)


# I campi che il parser pretende. I template in `config/redazione/gate_*.md` li riportano
# tutti, in forma di scheletro da compilare: un test tiene allineati i due elenchi.
GATE_REQUIRED = {
    "gate_a": ["SHA brief:", "Hash brief:", "Autore/modello:", "Giudice/modello:",
               "Domanda:", "Tesi:", "Codici e confronto:", "| criterio |", "Esito:",
               "Motivo:", "Correzione:", "Destinatario:", "Data:"],
    "gate_b": ["SHA bozza:", "Hash bozza:", "Famiglie autore/revisore:", "T:", "R:", "L:", "N:",
               "Controllo anti-invenzione:", "Bloccanti:", "Voto:", "Motivo:",
               "Rilievi localizzati:", "Giri:", "Esito:"],
}


def _parse_gate(path: Path, phase: str, expected_hash: str | None = None) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    required = GATE_REQUIRED[phase]
    missing = [field for field in required
               if not any(re.match(rf"^{re.escape(field)}", line) for line in text.splitlines())]
    if missing:
        raise RedazioneError(f"{path.name} malformato: campi mancanti {', '.join(missing)}")
    hash_field = "Hash brief:" if phase == "gate_a" else "Hash bozza:"
    recorded_hash = re.search(rf"^{re.escape(hash_field)}\s*([a-fA-F0-9]{{64}})\s*$", text, re.MULTILINE)
    if not recorded_hash:
        raise RedazioneError(f"{path.name} malformato: {hash_field} deve contenere SHA-256")
    if expected_hash and recorded_hash.group(1).lower() != expected_hash.lower():
        raise RedazioneError(f"{path.name} non riferito al file corrente ({hash_field})")
    outcome_match = re.search(r"^Esito:\s*(\S+)\s*$", text, re.MULTILINE)
    if not outcome_match:
        raise RedazioneError(f"{path.name} malformato: esito assente")
    outcome = outcome_match.group(1)
    if phase == "gate_a" and outcome not in {"PASSA", "FERMO"}:
        raise RedazioneError(f"{path.name} malformato: esito {outcome}")
    if phase == "gate_b" and outcome not in {"PASSA", "RISCRIVERE", "FERMO"}:
        raise RedazioneError(f"{path.name} malformato: esito {outcome}")
    vote = re.search(r"^Voto:\s*([1-5])(?:\s|$)", text, re.MULTILINE) if phase == "gate_b" else None
    if phase == "gate_b" and not vote:
        raise RedazioneError("gate-b.md malformato: voto 1-5 assente")
    if phase == "gate_a":
        rows = [line for line in text.splitlines() if line.startswith("|") and line.count("|") >= 4
                and not re.match(r"^\|\s*:?-{2,}", line)]
        if len(rows) < 6 or not any(re.search(r"\|\s*(sì|no)\s*\|", row, re.IGNORECASE) for row in rows[1:]):
            raise RedazioneError("gate-a.md malformato: tabella criteri senza almeno cinque righe di prova")
        criteria = [re.search(r"\|\s*(sì|no)\s*\|", row, re.IGNORECASE).group(1).lower()
                    for row in rows[1:] if re.search(r"\|\s*(sì|no)\s*\|", row, re.IGNORECASE)]
        if len(criteria) != 5:
            raise RedazioneError("gate-a.md malformato: servono esattamente cinque criteri valutati")
        all_yes = all(value == "sì" for value in criteria)
        if (outcome == "PASSA") != all_yes:
            raise RedazioneError("gate-a.md incoerente: esito non corrisponde ai cinque criteri")
    else:
        controls = {}
        for control in "TRLN":
            match = re.search(rf"^{control}:\s*(?:sì|no)\s*[—-]\s*(\S.+)$", text, re.MULTILINE | re.IGNORECASE)
            if not match:
                raise RedazioneError(f"gate-b.md malformato: controllo {control} senza esito e citazione")
            controls[control] = re.search(rf"^{control}:\s*(sì|no)", text, re.MULTILINE | re.IGNORECASE).group(1).lower()
        blockers = re.search(r"^Bloccanti:\s*(\d+)\s*$", text, re.MULTILINE)
        if not blockers:
            raise RedazioneError("gate-b.md malformato: conteggio bloccanti assente")
        all_yes = all(value == "sì" for value in controls.values())
        vote_value = int(vote.group(1))
        pass_conditions = all_yes and vote_value >= 4 and int(blockers.group(1)) == 0
        if ((outcome == "PASSA") != pass_conditions
                or (outcome in {"RISCRIVERE", "FERMO"} and all_yes and vote_value == 5)):
            raise RedazioneError("gate-b.md incoerente: esito non corrisponde a controlli, voto e bloccanti")
    return outcome, vote.group(1) if vote else ""


def _gate_file(workdir: Path, phase: str) -> Path:
    return workdir / ("gate-a.md" if phase == "gate_a" else "gate-b.md")


def _phase_choice(phase: dict, state: dict) -> dict:
    choices = phase.get("choices", [])
    if not choices:
        return phase
    index = 0
    if ((phase["name"] == "gate_a" and state.get("gate_a_returns", 0))
            or (phase["name"] == "gate_b" and state.get("rewrite_rounds", 0) > 1)):
        index = 1
    selected = dict(phase)
    selected["choices"] = [choices[min(index, len(choices) - 1)]]
    return selected


def _bridge(bridge_dir: Path, key: str, gate: str, reason: str, files: list[str], command: str,
            now: datetime) -> Path:
    bridge_dir.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime("%Y%m%d-%H%M%S")
    path = bridge_dir / f"{stamp}-cdiv-a-cowork-gate-{gate}-{key}.md"
    path.write_text(
        "per: cowork-direzione | da: C-DIV | progetto: divarioitalia | tipo: info | priorita: normale\n\n"
        f"Gate {gate.upper()} bloccato per {key}.\n\nMotivo: {reason}\n\n"
        f"File: {', '.join(files)}\n\nRipresa: `{command}`\n", encoding="utf-8")
    return path


def run_redazione(key: str, *, root: Path | None = None, worktree: Path | None = None,
                  config: dict | None = None, config_path: Path | None = None,
                  launcher: Callable | None = None, ram_provider: Callable[[], int] | None = None,
                  terminal_alive: Callable[[str], bool] | None = None,
                  bridge_dir: Path | None = None, from_phase: str | None = None,
                  only: str | None = None, dry_run: bool = False,
                  max_gate_a_retries: int = 1,
                  labeler: Callable[[str, str, bool], None] | None = None,
                  progress: Callable[[str], None] = print,
                  clock: Callable[[], float] = time.monotonic,
                  sleep: Callable[[float], None] = time.sleep) -> Result:
    root = Path(root or ROOT)
    if not KEY_RE.fullmatch(key):
        return Result(2, "chiave non valida")
    config_path = Path(config_path or CONFIG)
    if config is None:
        try:
            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            return Result(1, f"config redazione non leggibile: {exc}")
    phases = config.get("phases", [])
    names = [p["name"] for p in phases]
    if names != list(DEFAULT_PHASES):
        return Result(1, "config redazione deve dichiarare fasi nell'ordine previsto")
    if only and only not in names or from_phase and from_phase not in names:
        return Result(2, "fase sconosciuta")
    worktree = Path(worktree or root)
    workdir = worktree / "lavoro" / key
    state_path = workdir / "stato.json"
    if dry_run and not workdir.is_dir():
        return Result(1, f"pezzo non aperto: manca {workdir}")
    if not dry_run:
        workdir.mkdir(parents=True, exist_ok=True)
    if bridge_dir is None:
        bridge_dir = Path("/mnt/c/Users/Nilo/dev/trade5/ponte/fatti")
    labeler = labeler or (lambda issue, label, add: _set_issue_label(issue, label, add=add))
    ram_provider = ram_provider or _memory_available_mb
    terminal_alive = terminal_alive or _terminal_alive
    launcher = launcher or (lambda phase, spec: _orca_launcher(
        phase, spec, worktree=worktree, timeout=int(phase["timeout_seconds"]),
        clock=clock, sleep=sleep, progress=progress))
    try:
        memory = int(ram_provider())
    except (OSError, RedazioneError, ValueError, subprocess.SubprocessError) as exc:
        return Result(1, f"RAM non verificata: {exc}")
    if memory < int(config.get("memory_min_mb", 1500)):
        return Result(1, f"RAM disponibile {memory} MB, richiesti almeno {config.get('memory_min_mb', 1500)} MB")

    try:
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {
            "key": key, "current_phase": None, "phases": {}, "rewrite_rounds": 0}
    except (OSError, ValueError) as exc:
        return Result(1, f"stato.json non valido: {exc}")
    for record in state.get("phases", {}).values():
        if record.get("status") != "in corso":
            continue
        if not record.get("handle"):
            return Result(1, f"fase {state.get('current_phase')} in corso senza handle; verificare Orca prima di riprendere")
        alive = terminal_alive(record["handle"])
        if alive is None:
            return Result(1, f"fase {state.get('current_phase')} in corso; stato terminale sconosciuto, Orca non interrogabile: verificare prima di riprendere")
        if alive:
            return Result(1, f"fase {state.get('current_phase')} già in corso sul terminale {record['handle']}")

    selected = [only] if only else names[names.index(from_phase):] if from_phase else names[:]
    if dry_run:
        absent = []
        for selected_name in selected:
            phase = phases[names.index(selected_name)]
            inputs = [workdir / str(p) for p in phase.get("input", [])]
            absent.extend(str(p) for p in inputs if not p.is_file()
                          and not (p.name == "brief_iniziale.md" and (workdir / "brief.md").is_file()))
        plan = [f"{p['name']}: {p.get('role')} {p.get('choices', [])} input={p.get('input', [])} output={p.get('output', [])}"
                for p in phases if p["name"] in selected]
        progress("\n".join(plan))
        if absent:
            return Result(1, "ingressi mancanti: " + ", ".join(absent))
        return Result(0, "piano controllato; nessun lancio o file scritto")

    issue_value = state.get("issue")
    if not issue_value:
        issue_text = (workdir / "brief.md").read_text(encoding="utf-8") if (workdir / "brief.md").is_file() else ""
        match = re.search(r"^Issue:\s*#?(\d+)\s*$", issue_text, re.MULTILINE | re.IGNORECASE)
        issue_value = match.group(1) if match else None
        if issue_value:
            state["issue"] = str(issue_value)
    issue = str(issue_value or "non registrata")
    seed_brief = workdir / "brief_iniziale.md"
    needs_seed_brief = any("brief_iniziale.md" in phase.get("input", []) for phase in phases)
    if needs_seed_brief and not dry_run and not seed_brief.exists():
        starter = workdir / "brief.md"
        if not starter.is_file():
            return Result(1, f"pezzo non aperto: manca {starter}")
        seed_brief.write_bytes(starter.read_bytes())
    initial_brief_sha = _hash(workdir / "brief.md")
    if state.get("gate_a_sha") and initial_brief_sha and state["gate_a_sha"] != initial_brief_sha:
        if issue != "non registrata":
            try:
                labeler(issue, "gate-a", False)
            except RedazioneError as exc:
                return Result(1, str(exc))
        state["gate_a_sha"] = None
        state.setdefault("phases", {}).setdefault("gate_a", {})["status"] = "da rifare"
    current_draft_sha = _hash(workdir / "bozza.md")
    if state.get("gate_b_sha") and current_draft_sha and state["gate_b_sha"] != current_draft_sha:
        if issue != "non registrata":
            try:
                labeler(issue, "gate-b", False)
            except RedazioneError as exc:
                return Result(1, str(exc))
        state["gate_b_sha"] = None
        state.setdefault("phases", {}).setdefault("gate_b", {})["status"] = "da rifare"
    config_root = config_path.parent
    i = 0
    while i < len(selected):
        name = selected[i]
        phase = phases[names.index(name)]
        current_brief_sha = _hash(workdir / "brief.md")
        if name == "gate_a" and state.get("gate_a_sha") and current_brief_sha != state["gate_a_sha"]:
            if issue != "non registrata":
                try:
                    labeler(issue, "gate-a", False)
                except RedazioneError as exc:
                    return Result(1, str(exc))
            state["gate_a_sha"] = None
            _atomic_json(state_path, state)
        record = state.setdefault("phases", {}).setdefault(name, {})
        if name == "autore" and state.get("rewrite_rounds", 0) >= int(config.get("max_rewrites", 2)):
            break
        input_files = [workdir / str(item) for item in phase.get("input", [])]
        missing = [str(p) for p in input_files if not p.is_file()]
        if missing:
            return Result(1, f"{name}: ingressi mancanti: {', '.join(missing)}")
        input_hashes = {str(p.relative_to(worktree)): _hash(p) for p in input_files}
        output_files = [workdir / str(item) for item in phase.get("output", [])]
        output_hashes = {str(p.relative_to(worktree)): _hash(p) for p in output_files}
        output_dates = {str(p.relative_to(worktree)): p.stat().st_mtime_ns if p.is_file() else None
                        for p in output_files}
        head_before = _head_sha(worktree)
        record["prelaunch_output_hashes"] = output_hashes
        record["prelaunch_output_dates"] = output_dates
        record["prelaunch_commit"] = head_before
        gate_sha_changed = ((name == "gate_a" and state.get("gate_a_sha") != _hash(workdir / "brief.md"))
                            or (name == "gate_b" and state.get("gate_b_sha") != _hash(workdir / "bozza.md")))
        if (record.get("status") == "riuscita"
                and record.get("input_hashes") == input_hashes
                and all(output_hashes.values())
                and record.get("output_hashes") == output_hashes
                and not gate_sha_changed):
            if name in {"gate_a", "gate_b"}:
                try:
                    target = workdir / ("brief.md" if name == "gate_a" else "bozza.md")
                    outcome, vote = _parse_gate(_gate_file(workdir, name), name, _hash(target))
                except (OSError, RedazioneError) as exc:
                    record["status"] = "fallita"
                    _atomic_json(state_path, state)
                    return Result(1, str(exc))
                failed_gate = outcome == "FERMO" if name == "gate_a" else outcome != "PASSA" or int(vote) < 4
                if failed_gate:
                    record["status"] = "da rifare"
                else:
                    i += 1
                    continue
            else:
                i += 1
                continue
        if name == "autore" and record.get("status") != "riuscita":
            state["rewrite_rounds"] = int(state.get("rewrite_rounds", 0)) + 1
        try:
            content = _template(phase, key, issue, worktree, input_files, output_files, config_root)
        except (OSError, KeyError, ValueError, RedazioneError) as exc:
            return Result(1, str(exc))
        spec_path = workdir / f"SPEC-{name}.md"
        spec_path.write_text(content, encoding="utf-8")
        record.update({"status": "in corso", "input_hashes": input_hashes,
                       "started_at": datetime.now().astimezone().isoformat(), "handle": None,
                       "giri": int(state.get("rewrite_rounds", 0))})
        state["current_phase"] = name
        _atomic_json(state_path, state)
        progress(f"Avvio fase {name} ({phase['role']})")
        try:
            result = launcher(_phase_choice(phase, state), spec_path)
        except (OSError, RedazioneError, ValueError, subprocess.SubprocessError) as exc:
            uncertain = isinstance(exc, subprocess.TimeoutExpired)
            record.update({"status": "in corso" if uncertain else "fallita", "error": str(exc),
                           "finished_at": datetime.now().astimezone().isoformat()})
            _atomic_json(state_path, state)
            return Result(1, f"{name}: lancio fallito: {exc}")
        record.update({"handle": result.get("terminal_handle"), "dispatch_id": result.get("dispatch_id"),
                       "model_effective": result.get("model"), "result": result.get("worker_state"),
                       "output": result.get("output")})
        output_changed = any(
            p.is_file() and (
                _hash(p) != output_hashes[str(p.relative_to(worktree))]
                or p.stat().st_mtime_ns != output_dates[str(p.relative_to(worktree))]
            ) for p in output_files
        )
        head_after = _head_sha(worktree)
        if not result.get("success") or any(not p.is_file() for p in output_files):
            active = bool(result.get("terminal_handle") and result.get("worker_state") not in
                          {"succeeded", "failed", "stopped", "stop_unknown"})
            record.update({"status": "in corso" if active else "fallita",
                           "finished_at": datetime.now().astimezone().isoformat()})
            _atomic_json(state_path, state)
            return Result(1, f"{name}: fase {'ancora attiva' if active else 'fallita o file di uscita mancante'}")
        if not output_changed and head_after == head_before:
            record.update({"status": "fallita", "finished_at": datetime.now().astimezone().isoformat()})
            _atomic_json(state_path, state)
            return Result(1, f"{name}: fallita: output non aggiornato")
        record.update({"status": "riuscita", "output_hashes": {str(p.relative_to(worktree)): _hash(p) for p in output_files},
                       "commit_sha": _head_sha(worktree),
                       "finished_at": datetime.now().astimezone().isoformat()})
        _atomic_json(state_path, state)

        if name in {"gate_a", "gate_b"}:
            try:
                target = workdir / ("brief.md" if name == "gate_a" else "bozza.md")
                outcome, vote = _parse_gate(_gate_file(workdir, name), name, _hash(target))
            except (OSError, RedazioneError) as exc:
                attempts = int(record.get("malformed_attempts", 0)) + 1
                record["malformed_attempts"] = attempts
                record["status"] = "fallita"
                _atomic_json(state_path, state)
                if attempts >= 2:
                    _bridge(bridge_dir, key, PHASE_LABEL[name], f"gate malformato al tentativo {attempts}: {exc}",
                            [p.name for p in output_files],
                            f"bin/py -m scripts.editoriale.redazione {key} --da {name}",
                            datetime.now().astimezone())
                    return Result(3, f"gate malformato due volte; messaggio scritto nel ponte: {exc}")
                return Result(1, str(exc))
            negative = (outcome == "FERMO") if name == "gate_a" else (outcome != "PASSA" or int(vote) < 4)
            if negative:
                if name == "gate_a" and int(state.get("gate_a_returns", 0)) < max_gate_a_retries:
                    state["gate_a_returns"] = int(state.get("gate_a_returns", 0)) + 1
                    state["phases"]["brief"]["status"] = "da rifare"
                    state["phases"]["gate_a"]["status"] = "da rifare"
                    i = selected.index("brief") if "brief" in selected else len(selected)
                    _atomic_json(state_path, state)
                    continue
                if name == "gate_b" and outcome == "RISCRIVERE" and int(state.get("rewrite_rounds", 0)) < int(config.get("max_rewrites", 2)):
                    for downstream in ("autore", "grafico", "guardia", "gate_b", "bozza"):
                        state["phases"].setdefault(downstream, {})["status"] = "da rifare"
                    i = selected.index("autore") if "autore" in selected else len(selected)
                    _atomic_json(state_path, state)
                    continue
                files = [p.name for p in output_files]
                _bridge(bridge_dir, key, PHASE_LABEL[name], f"{outcome}, voto {vote or 'n/d'}", files,
                        f"bin/py -m scripts.editoriale.redazione {key} --da {name}", datetime.now().astimezone())
                return Result(3, f"gate {PHASE_LABEL[name]} negativo; messaggio scritto nel ponte")
            if name == "gate_a":
                state["gate_a_sha"] = _hash(workdir / "brief.md")
                if issue != "non registrata":
                    try:
                        labeler(issue, "gate-a", True)
                    except RedazioneError as exc:
                        record["status"] = "fallita"
                        _atomic_json(state_path, state)
                        return Result(1, str(exc))
            else:
                state["gate_b_sha"] = _hash(workdir / "bozza.md")
                if issue != "non registrata":
                    try:
                        labeler(issue, "gate-b", True)
                    except RedazioneError as exc:
                        record["status"] = "fallita"
                        _atomic_json(state_path, state)
                        return Result(1, str(exc))
        i += 1
    state["current_phase"] = None
    _atomic_json(state_path, state)
    return Result(0, "sequenza completata")


def _resolve_worktree(key: str) -> Path:
    target = f"divario-{key}"
    if ROOT.name == target:
        branch = subprocess.run(["git", "branch", "--show-current"], cwd=ROOT,
                                capture_output=True, text=True, check=False).stdout.strip()
        if branch != f"divario/{key}":
            raise RedazioneError(f"branch errato in {target}: atteso divario/{key}, trovato {branch or 'detached'}")
        return ROOT
    result = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=ROOT,
                            capture_output=True, text=True, check=True)
    matches = []
    path = None
    branch = None
    for line in result.stdout.splitlines() + [""]:
        if line.startswith("worktree "):
            path, branch = Path(line[9:]), None
        elif line.startswith("branch "):
            branch = line[7:]
        elif not line:
            if path and path.name == target and branch == f"refs/heads/divario/{key}":
                matches.append(path)
            path, branch = None, None
    if len(matches) != 1:
        raise RedazioneError(f"worktree {target} non trovato in modo univoco")
    return matches[0]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Orchestra in sequenza il lavoro editoriale già aperto")
    parser.add_argument("chiave")
    parser.add_argument("--da", dest="from_phase", choices=DEFAULT_PHASES)
    parser.add_argument("--prova", action="store_true")
    parser.add_argument("--solo", choices=DEFAULT_PHASES)
    args = parser.parse_args(argv)
    try:
        worktree = _resolve_worktree(args.chiave)
        result = run_redazione(args.chiave, worktree=worktree, root=ROOT, from_phase=args.from_phase,
                               only=args.solo, dry_run=args.prova)
    except (OSError, subprocess.SubprocessError, RedazioneError) as exc:
        print(f"redazione: {exc}", file=sys.stderr)
        return 1
    print(result.message)
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
