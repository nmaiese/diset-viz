"""Traduce gli hook nativi degli Agent Team nel contratto del cruscotto.

I task editoriali hanno un prefisso stabile:

    [redazione:<ruolo>:<fase>] <indicatore> - <titolo>

Il monitoraggio resta best effort: un errore non blocca mai un task. Il task
sentinella ``lead:chiusura`` chiude il run nel cruscotto.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
sys.path.insert(0, str(PROJECT_ROOT))

from lab.cruscotto import Postino, RINFRESCO_BATTITO  # noqa: E402


RUOLI = {
    "lead",
    "data-editor",
    "source-researcher",
    "search-strategist",
    "data-journalist",
    "skeptical-editor",
}
FASI = {
    "dossier": "Dossier",
    "ricerca": "Ricerca",
    "angolo": "Angolo",
    "scrittura": "Scrittura",
    "verifica": "Verifica",
    "pubblicazione": "Pubblicazione",
    "chiusura": "Chiusura",
}
PREFISSO = re.compile(
    r"^\[redazione:(?P<ruolo>[a-z0-9-]+):(?P<fase>[a-z0-9-]+)\]\s+"
    r"(?P<indicatore>(?:ter|bes|ims|eur|dem)-[0-9A-Za-z_.:-]+)\s+-\s+"
    r"(?P<titolo>.+)$"
)


def _ora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _run_id(evento):
    """Un id stabile per il team corrente, nel formato già accettato dall'API."""
    seme = evento.get("team_name") or evento.get("session_id") or ""
    slug = re.sub(r"[^a-z0-9-]+", "-", str(seme).lower()).strip("-")
    return f"wf_team-{slug}" if len(slug) >= 3 else ""


def _task(evento):
    trovato = PREFISSO.match(evento.get("task_subject") or "")
    if not trovato:
        return None
    task = trovato.groupdict()
    if task["ruolo"] not in RUOLI or task["fase"] not in FASI:
        return None
    task["fase_titolo"] = FASI[task["fase"]]
    return task


def _sentinella(evento, nome=None):
    task = _task(evento)
    return bool(
        task
        and task["ruolo"] == "lead"
        and task["fase"] == "chiusura"
        and (nome is None or evento.get("hook_event_name") == nome)
    )


def _stop_path(run_id):
    radice = Path(tempfile.gettempdir()) / "divario-team-monitor"
    radice.mkdir(parents=True, exist_ok=True)
    return radice / f"{run_id}.stop"


def _esito(evento, task):
    """L'esito per-indicatore dichiarato dal lead nella sentinella."""
    try:
        dichiarato = json.loads(evento.get("task_description") or "")
    except (TypeError, json.JSONDecodeError):
        dichiarato = {}
    articoli = [dict(v) for v in dichiarato.get("articoli") or [] if isinstance(v, dict)]
    fermati = [dict(v) for v in dichiarato.get("fermati") or [] if isinstance(v, dict)]
    for voce in articoli + fermati:
        voce.setdefault("codice", task["indicatore"])
    if not articoli and not fermati:
        fermati = [{
            "codice": task["indicatore"],
            "motivo": "sentinella completata senza esito articoli/fermati",
        }]
    return {"articoli": articoli, "fermati": fermati, "team": True}


def payload(evento, now=None):
    """Restituisce i POST da inviare per un singolo hook Claude Code."""
    nome = evento.get("hook_event_name")
    if nome not in {"TaskCreated", "TaskCompleted"}:
        return []
    task = _task(evento)
    run_id = _run_id(evento)
    task_id = evento.get("task_id")
    if not task or not run_id or not task_id:
        return []

    istante = now or _ora()
    fase_run = None if task["fase"] == "chiusura" else task["fase_titolo"]
    battito = {
        "action": "run",
        "run_id": run_id,
        "sessione": evento.get("session_id") or "",
        "progetto": Path(evento.get("cwd") or PROJECT_ROOT).name,
    }
    if fase_run:
        battito["fase_stimata"] = fase_run

    agente = {
        "action": "agente",
        "run_id": run_id,
        "agent_id": str(task_id),
        "agent_type": task["ruolo"],
        "fase_stimata": task["fase_titolo"],
        "indicatore": task["indicatore"],
        "stato_vivo": "aperto" if nome == "TaskCreated" else "chiuso",
    }
    if nome == "TaskCreated":
        agente["avviato_il"] = istante
    else:
        agente["chiuso_il"] = istante

    uscita = [battito, agente]
    if nome == "TaskCompleted" and task["ruolo"] == "lead" and task["fase"] == "chiusura":
        uscita.append({
            "action": "consuntivo",
            "run_id": run_id,
            "run": {
                "workflow": "editorial-agent-team",
                "args": [task["indicatore"]],
                "stato": "completed",
                "fasi": ["Dossier", "Ricerca", "Angolo", "Scrittura", "Verifica", "Pubblicazione"],
                "esito": _esito(evento, task),
            },
            "agenti": [],
        })
    return uscita


def segui_battito(evento, postino, intervallo=RINFRESCO_BATTITO, per=7200,
                   pausa=time.sleep, orologio=time.monotonic):
    """Rinfresca il run mentre la sentinella resta aperta, senza turni LLM."""
    if not _sentinella(evento, "TaskCreated"):
        return 0
    run_id = _run_id(evento)
    stop = _stop_path(run_id)
    try:
        stop.unlink()
    except FileNotFoundError:
        pass
    battiti = payload(evento)
    if not battiti:
        return 0
    run = battiti[0]
    scadenza = orologio() + per
    inviati = 0
    while not stop.exists() and orologio() < scadenza:
        postino.manda(run)
        inviati += 1
        attesa = 0
        while attesa < intervallo and not stop.exists():
            passo = min(5, intervallo - attesa)
            pausa(passo)
            attesa += passo
    return inviati


def main(argv=None):
    try:
        evento = json.load(sys.stdin)
        postino = Postino(stampa=os.environ.get("TEAM_MONITOR_STDOUT") == "1")
        if "--follow" in (argv if argv is not None else sys.argv[1:]):
            segui_battito(evento, postino)
            return 0
        for voce in payload(evento):
            postino.manda(voce)
        if _sentinella(evento, "TaskCompleted"):
            _stop_path(_run_id(evento)).touch()
    except Exception as errore:  # noqa: BLE001 - la telemetria non blocca il team
        print(f"team-monitor: {errore}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
