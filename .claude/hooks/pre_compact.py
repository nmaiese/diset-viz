#!/usr/bin/env python3
"""Hook PreCompact: ricorda le fonti locali senza duplicarne lo stato.

Quando la conversazione viene compattata, il contesto può perdersi. Il branch
corrente e ``STATUS.md`` bastano per riprendere il lavoro senza ricostruire una
pipeline dismessa o dipendere da un altro repository.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

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
    lines.append("- stato, obiettivi e prossimi passi: STATUS.md di questo repository")
    lines.append("- la vecchia pipeline editoriale esterna e' dismessa")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
