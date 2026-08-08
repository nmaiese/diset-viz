#!/usr/bin/env python3
"""Hook PostToolUseFailure: ogni fallimento di uno strumento lascia una riga.

Una run in cloud che inciampa su un comando non lascia niente da leggere: il
diario registra come è finita la run, non che cosa è andato storto a metà.
Questa riga locale (mai committata, vedi .gitignore) è il livello sotto il
diario: serve a diagnosticare una run bloccata senza doversela immaginare.

Best effort fino in fondo: un hook di diagnostica che fa fallire qualcosa
avrebbe invertito il proprio scopo, quindi ogni errore qui esce zero e zitto.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG = Path(__file__).resolve().parents[2] / "data" / "pipeline" / "tool_failures.jsonl"


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0
    tool_input = payload.get("tool_input") or {}
    row = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tool": payload.get("tool_name") or "?",
        "session": payload.get("session_id") or "",
        # Il comando o il file, troncati: serve a riconoscere il gesto, non a
        # riprodurlo per intero.
        "input": str(tool_input.get("command") or tool_input.get("file_path") or "")[:200],
        "error": str(payload.get("error") or payload.get("tool_response") or "")[:400],
    }
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
