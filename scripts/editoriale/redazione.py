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
GATE_A_CONTRACT_VERSION = "v4.1"
GATE_B_CONTRACT_VERSION = "v4.1"


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
    gates = {}
    for phase, name, digest in (("gate_a", "gate-a.md", brief_hash), ("gate_b", "gate-b.md", draft_hash)):
        try:
            gates[phase], _ = _parse_gate(workdir / name, phase, digest)
        except (OSError, RedazioneError) as exc:
            gates[phase] = f"non valido ({exc})"
    gate_a, gate_b = gates["gate_a"], gates["gate_b"]
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
# «Definizione specifica» e registro non stanno qui: se mancano, nel report o nel brief cui il
# report si riferisce, il report non è malformato ma vale FERMO, anche quando dice PASSA
# (REDAZIONE v4, §3).
GATE_REQUIRED = {
    "gate_a": ["Contratto:", "Tipo pezzo:", "SHA brief:", "Hash brief:", "Autore/modello:",
               "Giudice/modello:", "Domanda:", "Risposta in una frase:", "Variante:",
               "Dopo questa pagina, il lettore deve aver capito che…:", "Scheda editoriale:",
               "Schema del racconto:", "Angoli verificati:", "Riferimento usato:",
               "Codici e confronto:", "Ultimo dato:", "Data fonte del dato:", "URL fonte del dato:",
               "Ruolo indicatori interni:", "Fonti esterne verificate:", "Grafico con dati esterni:",
               "Figure previste:", "Limiti:", "| criterio |", "Esito:", "Motivo:", "Correzione:",
               "Destinatario:", "Data:"],
    "gate_b": ["Contratto:", "Tipo pagina:", "SHA bozza:", "Hash bozza:", "Famiglie autore/revisore:", "T:", "R:", "L:", "N:",
               "Oltre la tabella:", "Funzione paragrafi:",
               "Controllo anti-invenzione:", "Bloccanti:", "Voto:", "Motivo:",
               "Rilievi localizzati:", "Giri:", "Esito:"],
}


def _parse_gate(path: Path, phase: str, expected_hash: str | None = None,
                expected_rounds: int | None = None) -> tuple[str, str]:
    """Esito e voto del gate. Per Gate A legge anche `brief.md` accanto al report."""
    text = path.read_text(encoding="utf-8")
    # La versione si guarda prima dei campi: un report di un contratto precedente è invalido
    # in quanto tale, anche quando brief o bozza non sono cambiati.
    contract = GATE_A_CONTRACT_VERSION if phase == "gate_a" else GATE_B_CONTRACT_VERSION
    if _field(text, "Contratto") != contract:
        raise RedazioneError(f"{path.name} usa contratto diverso da {contract}")
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
        if gate_a_formal_gaps(path):
            return "FERMO", ""
        _validate_gate_a(text)
        lines = text.splitlines()
        header = next((i for i, line in enumerate(lines) if line.strip().lower() == "| criterio | esito | prova verificabile | limite |"), None)
        if header is None:
            raise RedazioneError("gate-a.md malformato: intestazione tabella criteri assente")
        rows = []
        for line in lines[header + 1:]:
            if not line.startswith("|"):
                if rows:
                    break
                continue
            if re.match(r"^\|\s*:?-{2,}", line):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) == 4:
                rows.append(cells)
        if len(rows) != 5:
            raise RedazioneError("gate-a.md malformato: servono esattamente cinque criteri valutati")
        if [row[0].casefold() for row in rows] != [name.casefold() for name in GATE_A_CRITERIA]:
            raise RedazioneError("gate-a.md malformato: i cinque criteri v4 sono fissi: "
                                 + ", ".join(GATE_A_CRITERIA))
        for criterion, result, evidence, limit in rows:
            if result.lower() not in {"sì", "no"} or len(evidence) < 18 or evidence.lower() in {"prova", "ok", "sì", "no", "dato verificato"}:
                raise RedazioneError(f"gate-a.md malformato: prova non verificabile per criterio {criterion}")
            if len(limit) < 5:
                raise RedazioneError(f"gate-a.md malformato: limite assente per criterio {criterion}")
        all_yes = all(row[1].lower() == "sì" for row in rows)
        if (outcome == "PASSA") != all_yes:
            raise RedazioneError("gate-a.md incoerente: esito non corrisponde ai cinque criteri")
    else:
        page_type = _field(text, "Tipo pagina")
        if page_type not in PAGE_TYPES:
            raise RedazioneError("gate-b.md malformato: Tipo pagina non valido")
        controls = {}
        for control in "TRLN":
            match = re.search(rf"^{control}:\s*(?:sì|no)\s*[—-]\s*(\S.+)$", text, re.MULTILINE | re.IGNORECASE)
            if not match:
                raise RedazioneError(f"gate-b.md malformato: controllo {control} senza esito e citazione")
            controls[control] = re.search(rf"^{control}:\s*(sì|no)", text, re.MULTILINE | re.IGNORECASE).group(1).lower()
        blockers = re.search(r"^Bloccanti:\s*(\d+)\s*$", text, re.MULTILINE)
        if not blockers:
            raise RedazioneError("gate-b.md malformato: conteggio bloccanti assente")
        rounds = re.search(r"^Giri:\s*([12])\s*$", text, re.MULTILINE)
        if not rounds:
            raise RedazioneError("gate-b.md malformato: Giri deve essere 1 o 2")
        if expected_rounds and int(rounds.group(1)) != expected_rounds:
            raise RedazioneError(f"gate-b.md incoerente: Giri {rounds.group(1)} nel report, "
                                 f"{expected_rounds} in stato.json")
        all_yes = all(value == "sì" for value in controls.values())
        editorial_yes = True
        for label in ("Oltre la tabella", "Funzione paragrafi"):
            evidence = re.search(rf"^{label}:[ \t]*(sì|no)[ \t]*[—-][ \t]*(\S.+)$", text, re.MULTILINE | re.I)
            if outcome == "PASSA" and (not evidence or evidence.group(1).lower() != "sì"
                                        or len(evidence.group(2).strip()) < 20):
                raise RedazioneError(f"gate-b.md incoerente: {label} assente o negativo")
            editorial_yes &= bool(evidence and evidence.group(1).lower() == "sì")
        vote_value = int(vote.group(1))
        pass_conditions = all_yes and editorial_yes and vote_value >= 4 and int(blockers.group(1)) == 0
        # Al secondo giro non c'è un terzo: sotto 4 l'esito è FERMO, non RISCRIVERE.
        if ((outcome == "PASSA") != pass_conditions
                or (outcome in {"RISCRIVERE", "FERMO"} and pass_conditions and vote_value == 5)
                or (outcome == "RISCRIVERE" and rounds.group(1) == "2")):
            raise RedazioneError("gate-b.md incoerente: esito non corrisponde a controlli, voto e bloccanti")
        if outcome == "PASSA":
            try:
                gate_a_text = path.with_name("gate-a.md").read_text(encoding="utf-8")
                approved_type = _field(gate_a_text, "Tipo pezzo").casefold()
                gate_a_outcome, _ = _parse_gate(path.with_name("gate-a.md"), "gate_a",
                                                _hash(path.with_name("brief.md")))
            except (OSError, RedazioneError):
                return "FERMO", vote.group(1)
            page_for_piece = {"blog": "articolo", "scheda indicatore": "indicatore",
                              "profilo territoriale": "profilo territoriale",
                              "confronto territoriale": "confronto territoriale"}
            if gate_a_outcome != "PASSA" or page_for_piece.get(approved_type) != page_type:
                return "FERMO", vote.group(1)
            try:
                brief_text = path.with_name("brief.md").read_text(encoding="utf-8")
            except OSError:
                return "FERMO", vote.group(1)
            claims = _claims(brief_text)
            complete = [row for row in claims if len(row) == 5 and len(row[0]) >= 10
                        and (row[1].casefold().split() or [""])[0] in CLAIM_TYPES
                        and all(_filled(cell) for cell in row[2:])]
            t_evidence = re.search(r"^T:\s*sì\s*[—-]\s*(.+)$", text, re.MULTILINE | re.I)
            if (not claims or len(complete) != len(claims) or not t_evidence
                    or not any(row[0].casefold() in t_evidence.group(1).casefold() for row in claims)):
                return "FERMO", vote.group(1)
    return outcome, vote.group(1) if vote else ""


def _field(text: str, name: str) -> str:
    match = re.search(rf"^{re.escape(name)}:[ \t]*([^\r\n]*)$", text, re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else ""


GATE_A_CRITERIA = ("Misura definita", "Confronti compatibili", "Livello delle affermazioni",
                   "Prove e figure", "Fonti e freschezza")
GATE_A_DEFINITION_FIELDS = ("Definizione specifica", "Unità", "Denominatore", "Popolazione",
                            "Territorio", "Periodo", "Fonte e release")
# Definizioni che ripetono il nome invece di dire che cosa si conta: il caso della bozza pensioni.
GENERIC_DEFINITIONS = ("definito dalla fonte", "definita dalla fonte", "gruppo di riferimento",
                       "definizione della fonte", "come da fonte", "vedi fonte", "si veda la fonte",
                       "indicatore che misura")
CLAIM_HEADER = "| affermazione | tipo | dato o calcolo | ambito e periodo | fonte |"
# Conta la prima parola: «interpretazione documentata» (REV) e «interpretazione attribuita» valgono uguale.
CLAIM_TYPES = {"dato", "calcolo", "interpretazione", "ipotesi", "limite"}
BLOG_VARIANTS = ("orientamento", "cambiamento", "verifica", "servizi", "differenze interne",
                 "gruppi demografici", "confronto tra misure")
SHEET_VARIANTS = ("regionale", "provinciale", "multilivello", "per sesso", "per età", "con incroci",
                  "serie breve", "misura complessa", "facile da fraintendere")
PAGE_TYPES = {"articolo", "indicatore", "profilo territoriale", "confronto territoriale"}
EDITORIAL_FIELDS = ("Domanda", "Definizione", "Risultato centrale", "Confronto", "Rilevanza",
                    "Spiegazione", "Limite decisivo", "Passo successivo")
REFERENCES = ("italia ufficiale", "media semplice", "mediana", "obiettivo", "nessuno")


def _filled(value: str) -> bool:
    value = value.strip()
    return len(value) >= 3 and not value.startswith("<") and value.casefold() not in {"n/d", "nd", "-", "nessuno", "nessuna"}


def gate_a_formal_gaps(report: Path) -> list[str]:
    """Lacune formali di un Gate A v4, nel brief corrente e nel report, in italiano.

    È la validazione formale (REDAZIONE v4, §3): rende FERMO il gate qualunque esito dichiari
    il giudice, e non entra nel merito, che resta ai cinque criteri. Lista vuota: niente manca.
    """
    brief = report.with_name("brief.md")
    try:
        brief_text = brief.read_text(encoding="utf-8")
    except OSError as exc:
        raise RedazioneError(f"{report.name} senza brief.md leggibile accanto: {exc}") from exc
    report_text = report.read_text(encoding="utf-8")
    gaps = [f"brief: {GAP_LABELS[gap]}" for gap in _gate_a_core_gaps(brief_text)]
    gaps += [f"report: {GAP_LABELS[gap]}" for gap in _gate_a_core_gaps(report_text)]
    brief_claims = {row[0].casefold() for row in _claims(brief_text)}
    foreign = [row[0] for row in _claims(report_text) if row[0].casefold() not in brief_claims]
    if brief_claims and foreign:
        gaps.append("report: registro con affermazioni assenti dal brief ("
                    + ", ".join(f"«{claim}»" for claim in foreign) + ")")
    brief_rows = {row[0].casefold(): row for row in _claims(brief_text)}
    for row in _claims(report_text):
        original = brief_rows.get(row[0].casefold())
        if original and len(row) == len(original) == 5:
            changed = [name for name, left, right in zip(("affermazione", "tipo", "dato o calcolo",
                                                          "ambito e periodo", "fonte"), original, row)
                       if " ".join(left.split()).casefold() != " ".join(right.split()).casefold()]
            if changed:
                gaps.append(f"report: registro diverso dal brief per «{row[0]}» ({', '.join(changed)})")
    for name in GATE_A_DEFINITION_FIELDS:
        brief_value = " ".join(_field(brief_text, name).split()).casefold()
        report_value = " ".join(_field(report_text, name).split()).casefold()
        if brief_value and report_value and brief_value != report_value:
            gaps.append(f"report: «{name}» diverso dal brief")
    label = "Dopo questa pagina, il lettore deve aver capito che…"
    if (_field(brief_text, label) and _field(report_text, label)
            and _field(brief_text, label).casefold() != _field(report_text, label).casefold()):
        gaps.append("report: comprensione diversa dal brief")
    if _editorial_rows(brief_text) and _editorial_rows(report_text) and _editorial_rows(brief_text) != _editorial_rows(report_text):
        gaps.append("report: scheda editoriale diversa dal brief")
    return gaps


def gate_a_stop_reason(gaps: list[str]) -> str:
    """Motivo su una riga per ponte e risultato quando la validazione formale ferma Gate A."""
    return ("validazione formale, non giudizio di merito: vale FERMO qualunque esito dichiari il giudice; "
            + "; ".join(gaps))


# Le chiavi sono quelle di `_gate_a_core_gaps`; le etichette finiscono nel ponte.
GAP_LABELS = {name: f"manca «{name}»" for name in GATE_A_DEFINITION_FIELDS} | {
    "Definizione specifica generica": "«Definizione specifica» generica o ricavata dal nome, non dice che cosa si conta",
    "Registro affermazioni": "registro delle affermazioni assente o con righe incomplete",
    "Comprensione ulteriore": "manca una comprensione oltre la classifica",
    "Scheda editoriale": "scheda editoriale assente o incompleta",
}


def _claims(text: str) -> list[list[str]]:
    lines = text.splitlines()
    header = next((i for i, line in enumerate(lines)
                   if re.sub(r"\s+", " ", line.strip()).casefold() == CLAIM_HEADER), None)
    claims = []
    if header is not None:
        for line in lines[header + 1:]:
            if not line.startswith("|") or line.strip().casefold().startswith("| criterio |"):
                break
            if re.match(r"^\|\s*:?-{2,}", line):
                continue
            claims.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return claims


def _editorial_rows(text: str) -> list[str]:
    section = text.split("Scheda editoriale:\n", 1)
    return section[1].splitlines()[:8] if len(section) == 2 else []


def _gate_a_core_gaps(text: str) -> list[str]:
    """Ciò che rende FERMO un Gate A v4 qualunque esito dichiari: definizione e registro."""
    gaps = [name for name in GATE_A_DEFINITION_FIELDS if not _filled(_field(text, name))]
    definition = _field(text, "Definizione specifica").casefold()
    if "Definizione specifica" not in gaps and (
            len(definition) < 30 or any(phrase in definition for phrase in GENERIC_DEFINITIONS)):
        gaps.append("Definizione specifica generica")
    claims = _claims(text)
    complete = [row for row in claims
                if len(row) == 5 and len(row[0]) >= 10 and (row[1].casefold().split() or [''])[0] in CLAIM_TYPES
                and all(_filled(cell) for cell in row[2:])]
    if not claims or len(complete) != len(claims):
        gaps.append("Registro affermazioni")
    understanding = _field(text, "Dopo questa pagina, il lettore deve aver capito che…")
    # Riconosce solo la classifica ovvia; il giudice valuta il merito degli altri casi.
    only_ranking = re.fullmatch(
        r"\s*\S+\s+(?:è|sono)\s+(?:prima|primo|ultima|ultimo)\s+e\s+\S+\s+(?:è|sono)\s+(?:prima|primo|ultima|ultimo)\s*[.!]?",
        understanding, re.I)
    if not _filled(understanding) or only_ranking:
        gaps.append("Comprensione ulteriore")
    rows = _editorial_rows(text)
    if len(rows) != 8 or any(not row.startswith(name + ":") or not _filled(row.partition(":")[2])
                              for row, name in zip(rows, EDITORIAL_FIELDS)):
        gaps.append("Scheda editoriale")
    return gaps


def _validate_gate_a(text: str) -> None:
    piece_type = _field(text, "Tipo pezzo").lower()
    if piece_type not in {"blog", "scheda indicatore", "profilo territoriale", "confronto territoriale"}:
        raise RedazioneError("gate-a.md malformato: Tipo pezzo non valido")
    variant = re.sub(r"^(?:[a-g][.)]?\s+|scheda\s+)", "", _field(text, "Variante").casefold())
    allowed = (BLOG_VARIANTS if piece_type == "blog" else SHEET_VARIANTS if piece_type == "scheda indicatore"
               else ("profilo",) if piece_type == "profilo territoriale" else ("confronto",))
    if not any(variant.startswith(name) for name in allowed):
        raise RedazioneError(f"gate-a.md malformato: Variante non valida per {piece_type}")
    steps = [step.strip() for step in re.split(r"\s*(?:>|→)\s*", _field(text, "Schema del racconto"))]
    if len([step for step in steps if len(step) >= 3]) < 3:
        raise RedazioneError("gate-a.md malformato: Schema del racconto richiede almeno tre passaggi")
    if len(_field(text, "Risposta in una frase")) < 15:
        raise RedazioneError("gate-a.md malformato: Risposta in una frase assente")
    if not _field(text, "Riferimento usato").casefold().startswith(REFERENCES):
        raise RedazioneError("gate-a.md malformato: Riferimento usato non denominato")
    if piece_type in {"blog", "scheda indicatore"} and not _filled(_field(text, "Figure previste")):
        raise RedazioneError("gate-a.md malformato: Figure previste assenti")
    if not _filled(_field(text, "Limiti")):
        raise RedazioneError("gate-a.md malformato: Limiti assenti")
    latest = _field(text, "Ultimo dato")
    if not re.search(r"\b(?:19|20)\d{2}\b", latest):
        raise RedazioneError("gate-a.md malformato: Ultimo dato deve indicare anno o periodo")
    source_date = _field(text, "Data fonte del dato")
    try:
        datetime.strptime(source_date, "%Y-%m-%d")
    except ValueError as exc:
        raise RedazioneError("gate-a.md malformato: Data fonte del dato deve essere YYYY-MM-DD") from exc
    source_url = _field(text, "URL fonte del dato")
    if not source_url.startswith("https://"):
        raise RedazioneError("gate-a.md malformato: URL fonte del dato deve essere HTTPS")
    angles = [angle.strip() for angle in _field(text, "Angoli verificati").split(";") if len(angle.strip()) >= 12]
    if piece_type == "blog" and len(angles) < 2:
        raise RedazioneError("gate-a.md malformato: blog richiede almeno due angoli verificati")
    internal_role = _field(text, "Ruolo indicatori interni").lower()
    role_ok = (("base" in internal_role and "tassello" in internal_role) if piece_type == "blog" else
               ("spieg" in internal_role and "contesto" in internal_role) if piece_type == "scheda indicatore" else
               _filled(internal_role))
    if not role_ok:
        raise RedazioneError("gate-a.md malformato: ruolo indicatori interni non rispetta il tipo pezzo")

    lines = text.splitlines()
    heading = next((i for i, line in enumerate(lines)
                    if line.strip().lower() == "| istituzione | data fonte | url aperto | dato o claim | verificata |"), None)
    if heading is None and piece_type in {"blog", "scheda indicatore"}:
        raise RedazioneError("gate-a.md malformato: tabella fonti esterne assente")
    sources = []
    for line in lines[heading + 1:] if heading is not None else []:
        if not line.startswith("|"):
            if sources:
                break
            continue
        if re.match(r"^\|\s*:?-{2,}", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 5:
            sources.append(cells)
    minimum = 3 if piece_type == "blog" else 1 if piece_type == "scheda indicatore" else 0
    valid_urls = set()
    source_dates = {}
    for institution, published, url, claim, verified in sources:
        try:
            datetime.strptime(published, "%Y-%m-%d")
        except ValueError as exc:
            raise RedazioneError("gate-a.md malformato: ogni fonte esterna richiede data YYYY-MM-DD") from exc
        if (len(institution) < 3 or not url.startswith("https://") or not claim.strip()
                or verified.lower() not in {"sì", "si"}):
            raise RedazioneError("gate-a.md malformato: fonte esterna senza istituzione, URL aperto, claim e verifica")
        valid_urls.add(url)
        source_dates[url] = published
    if len(valid_urls) < minimum:
        raise RedazioneError(f"gate-a.md malformato: {piece_type} richiede almeno {minimum} fonti esterne verificate")
    if piece_type in {"blog", "scheda indicatore"} and (source_url not in valid_urls or source_dates.get(source_url) != source_date):
        raise RedazioneError("gate-a.md malformato: data e URL fonte del dato devono corrispondere alla fonte verificata")
    chart = _field(text, "Grafico con dati esterni")
    if piece_type == "blog":
        chart_parts = [part.strip() for part in chart.split(";")]
        if (len(chart_parts) < 3 or any(len(part) < 8 for part in chart_parts[:2])
                or chart_parts[-1] not in valid_urls):
            raise RedazioneError("gate-a.md malformato: grafico deve indicare variabile, periodo e URL fonte verificata")
        if len({row[0].casefold() for row in sources}) < 3:
            raise RedazioneError("gate-a.md malformato: le tre fonti blog devono provenire da istituzioni distinte")


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
    selected["choices"] = choices[min(index, len(choices) - 1):]
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
    gate_a_record = state.setdefault("phases", {}).setdefault("gate_a", {})
    if (gate_a_record.get("status") == "riuscita"
            and state.get("gate_a_contract_version") != GATE_A_CONTRACT_VERSION):
        if issue != "non registrata" and state.get("gate_a_sha"):
            try:
                labeler(issue, "gate-a", False)
            except RedazioneError as exc:
                return Result(1, str(exc))
        state["gate_a_sha"] = None
        gate_a_record["status"] = "da rifare"
    gate_b_record = state.setdefault("phases", {}).setdefault("gate_b", {})
    if (gate_b_record.get("status") == "riuscita"
            and state.get("gate_b_contract_version") != GATE_B_CONTRACT_VERSION):
        if issue != "non registrata" and state.get("gate_b_sha"):
            try:
                labeler(issue, "gate-b", False)
            except RedazioneError as exc:
                return Result(1, str(exc))
        state["gate_b_sha"] = None
        gate_b_record["status"] = "da rifare"
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
        if name == "autore":
            current_brief_sha = _hash(workdir / "brief.md")
            gate_record = state.get("phases", {}).get("gate_a", {})
            if (state.get("gate_a_contract_version") != GATE_A_CONTRACT_VERSION
                    or state.get("gate_a_sha") != current_brief_sha
                    or gate_record.get("status") != "riuscita"):
                return Result(1, f"Gate A {GATE_A_CONTRACT_VERSION} PASSA sul brief corrente richiesto prima della scrittura")
            try:
                gate_outcome, _ = _parse_gate(workdir / "gate-a.md", "gate_a", current_brief_sha)
            except (OSError, RedazioneError) as exc:
                return Result(1, f"Gate A non valido per l'autore: {exc}")
            if gate_outcome != "PASSA":
                gaps = gate_a_formal_gaps(workdir / "gate-a.md")
                reason = f": {'; '.join(gaps)}" if gaps else ""
                return Result(1, f"Gate A {GATE_A_CONTRACT_VERSION} non è PASSA sul brief corrente{reason}; autore fermo")
        if name == "autore" and state.get("rewrite_rounds", 0) >= int(config.get("max_rewrites", 2)):
            break
        input_files = [workdir / str(item) for item in phase.get("input", [])]
        missing = [str(p) for p in input_files if not p.is_file()]
        if missing:
            return Result(1, f"{name}: ingressi mancanti: {', '.join(missing)}")
        input_hashes = {p.relative_to(worktree).as_posix(): _hash(p) for p in input_files}
        output_files = [workdir / str(item) for item in phase.get("output", [])]
        output_hashes = {p.relative_to(worktree).as_posix(): _hash(p) for p in output_files}
        output_dates = {p.relative_to(worktree).as_posix(): p.stat().st_mtime_ns if p.is_file() else None
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
                    outcome, vote = _parse_gate(_gate_file(workdir, name), name, _hash(target),
                                                int(state.get("rewrite_rounds", 0)) if name == "gate_b" else None)
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
        record.pop("motivo", None)
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
                _hash(p) != output_hashes[p.relative_to(worktree).as_posix()]
                or p.stat().st_mtime_ns != output_dates[p.relative_to(worktree).as_posix()]
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
        record.update({"status": "riuscita", "output_hashes": {p.relative_to(worktree).as_posix(): _hash(p) for p in output_files},
                       "commit_sha": _head_sha(worktree),
                       "finished_at": datetime.now().astimezone().isoformat()})
        _atomic_json(state_path, state)

        if name in {"gate_a", "gate_b"}:
            try:
                target = workdir / ("brief.md" if name == "gate_a" else "bozza.md")
                outcome, vote = _parse_gate(_gate_file(workdir, name), name, _hash(target),
                                            int(state.get("rewrite_rounds", 0)) if name == "gate_b" else None)
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
            reason = f"{outcome}, voto {vote or 'n/d'}"
            if negative and name == "gate_a":
                gaps = gate_a_formal_gaps(_gate_file(workdir, name))
                if gaps:
                    reason += f" per {gate_a_stop_reason(gaps)}"
                else:
                    reason += f": {_field(_gate_file(workdir, name).read_text(encoding='utf-8'), 'Motivo')}"
                record["motivo"] = reason
                _atomic_json(state_path, state)
                progress(f"Gate A: {reason}")
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
                if name == "gate_a":
                    record["status"] = "fermo"
                    _atomic_json(state_path, state)
                files = [p.name for p in output_files]
                _bridge(bridge_dir, key, PHASE_LABEL[name], reason, files,
                        f"bin/py -m scripts.editoriale.redazione {key} --da {name}", datetime.now().astimezone())
                return Result(3, f"gate {PHASE_LABEL[name]} negativo ({reason}); messaggio scritto nel ponte")
            if name == "gate_a":
                state["gate_a_sha"] = _hash(workdir / "brief.md")
                state["gate_a_contract_version"] = GATE_A_CONTRACT_VERSION
                if issue != "non registrata":
                    try:
                        labeler(issue, "gate-a", True)
                    except RedazioneError as exc:
                        record["status"] = "fallita"
                        _atomic_json(state_path, state)
                        return Result(1, str(exc))
            else:
                state["gate_b_sha"] = _hash(workdir / "bozza.md")
                state["gate_b_contract_version"] = GATE_B_CONTRACT_VERSION
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
