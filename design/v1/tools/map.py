"""Alleggerisce la mappa delle regioni per i prototipi.

Legge i venti tracciati di `app/templates/_italy_map.html` (89 KB), arrotonda le
coordinate all'unita', toglie i punti ripetuti e i frammenti che dopo
l'arrotondamento non hanno piu' area, e scrive `src/partials/italy_paths.json`
({chiave della regione: attributo d}). Il viewBox resta 0 0 560 660.

    bin/py design/v1/tools/map.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "app" / "templates" / "_italy_map.html"
TARGET = ROOT / "design" / "v1" / "src" / "partials" / "italy_paths.json"


def simplify(d: str) -> str:
    parts = []
    for sub in re.findall(r"M[^M]*", d):
        points = []
        for x, y in re.findall(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", sub):
            p = (round(float(x)), round(float(y)))
            if not points or points[-1] != p:
                points.append(p)
        if len(points) > 1 and points[0] == points[-1]:
            points.pop()
        if len(set(points)) < 3:
            continue
        parts.append("M" + "L".join(f"{x},{y}" for x, y in points) + "Z")
    if not parts:
        raise ValueError("un tracciato e' rimasto vuoto dopo la semplificazione")
    return "".join(parts)


def main() -> None:
    html = SOURCE.read_text(encoding="utf-8")
    paths = dict(re.findall(r'data-key="([^"]+)" d="([^"]+)"', html))
    if len(paths) != 20:
        raise ValueError(f"attese 20 regioni, trovate {len(paths)}")
    out = {key: simplify(d) for key, d in paths.items()}
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(out, separators=(",", ":")) + "\n", encoding="utf-8")
    before = sum(len(d) for d in paths.values())
    after = sum(len(d) for d in out.values())
    print(f"tracciati da {before} a {after} byte")


if __name__ == "__main__":
    main()
