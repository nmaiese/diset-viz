#!/usr/bin/env python3
"""Hook PreCompact: lo stato della run, ridetto prima che il contesto si accorci.

Quando la conversazione viene compattata, quello che sta solo nella
conversazione può perdersi. Le cose che una run della catena non può
permettersi di dimenticare però stanno tutte in file committati o in git:
questo hook le rilegge da lì e le ristampa, così il riassunto che entra nel
nuovo contesto le porta con sé. Non inventa stato, lo cita.

Best effort: stampare meno è sempre meglio che fallire.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "data" / "pipeline" / "runs"


def main():
    try:
        json.load(sys.stdin)
    except Exception:
        pass
    lines = ["Promemoria per la compattazione (stato letto dai file, non dalla chat):"]
    try:
        branch = subprocess.run(
            ("git", "rev-parse", "--abbrev-ref", "HEAD"),
            cwd=str(ROOT), capture_output=True, text=True,
        ).stdout.strip()
        if branch:
            lines.append(f"- branch corrente: {branch}")
    except OSError:
        pass
    try:
        shards = sorted(RUNS.glob("*.json"))[-3:]
        for shard in shards:
            try:
                row = json.loads(shard.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            lines.append(
                f"- run {row.get('run_id', shard.stem)}: stadio {row.get('stage', '?')}, "
                f"esito {row.get('outcome', '?')}, {row.get('summary', '')}"
            )
    except OSError:
        pass
    lines.append("- contratto e chiusura run: docs/AGENT_CONTRACT.md; "
                 "stato code: python3 scripts/pipeline_status.py")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
