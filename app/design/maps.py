"""I tracciati delle mappe della 1.0, e lo sprite che li porta una volta sola.

Le regioni stanno in `italy_paths.json`, le province in `province_paths.json`
(`design/v1/tools/province_map.py`), nello stesso viewBox 560x660: i confini
regionali si disegnano sopra le province e combaciano.

La home ne disegna cinque, fra regioni e province. Con i tracciati scritti in
ogni mappa pesavano circa 67 KB compressi in piu', perche' il gzip non vede
due copie distanti piu' di 32 KB: lo sprite li scrive una volta in un `<svg>`
nascosto, e ogni mappa li richiama con `<use>`. Il colore lo prende l'`<use>`,
e il tracciato nello sprite non ne ha uno suo, cosi' lo eredita.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from markupsafe import Markup

HERE = Path(__file__).resolve().parent
REGION_PATHS: dict[str, str] = json.loads((HERE / "italy_paths.json").read_text(encoding="utf-8"))
PROVINCE_PATHS: dict[str, str] = json.loads((HERE / "province_paths.json").read_text(encoding="utf-8"))
PREFIX = {"regione": "mr-", "provincia": "mp-"}


def paths(level_key: str) -> dict[str, str]:
    return REGION_PATHS if level_key == "regione" else PROVINCE_PATHS


def sprite(level_key: str | None = None) -> Markup:
    """L'`<svg>` con i tracciati di un livello (o di tutti e due), da mettere
    una volta in pagina prima della prima mappa che li usa. La home mette le
    regioni prima della testata (la mappa accanto alla ricerca) e le province
    dopo: 41 KB di tracciati davanti al titolo ne ritardavano il testo."""
    levels = [level_key] if level_key else list(PREFIX)
    defs = "".join(f'<path id="{PREFIX[lv]}{k}" d="{d}"/>' for lv in levels for k, d in paths(lv).items())
    return Markup(f'<svg class="map-sprite" aria-hidden="true" focusable="false"><defs>{defs}</defs></svg>')


def bbox(d: str) -> tuple[float, float, float, float]:
    """(x0, y0, x1, y1) di un tracciato fatto di segmenti (M, L, H, V, Z,
    assoluti o relativi), come quelli di questi file: le regioni sono
    assolute, le province relative. Un comando diverso, o un tracciato senza
    punti, e' un errore."""
    xs, ys = [], []
    x = y = sx = sy = 0.0
    cmd = None
    for tok in re.findall(r"[A-Za-z]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?", d):
        if tok.isalpha():
            if tok not in "MmLlHhVvZz":
                raise ValueError(f"comando {tok!r} non gestito nel tracciato {d[:40]!r}")
            cmd = tok
            if cmd in "Zz":
                x, y = sx, sy
            pending = []
            continue
        pending.append(float(tok))
        need = 1 if cmd in "HhVv" else 2
        if len(pending) < need:
            continue
        if cmd in "Hh":
            x = pending[0] + (x if cmd == "h" else 0)
        elif cmd in "Vv":
            y = pending[0] + (y if cmd == "v" else 0)
        else:
            dx, dy = pending
            x, y = (x + dx, y + dy) if cmd in "ml" else (dx, dy)
            if cmd in "Mm":
                sx, sy = x, y
                cmd = "l" if cmd == "m" else "L"
        pending = []
        xs.append(x); ys.append(y)
    if not xs:
        raise ValueError(f"tracciato senza coordinate: {d[:40]!r}")
    return min(xs), min(ys), max(xs), max(ys)


def _overlaps(a: tuple, b: tuple) -> bool:
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


def zoom(region_key: str, pad: float = 0.12, min_side: float = 90.0) -> dict:
    """Il riquadro di una regione nel viewBox dell'Italia, con un margine, e i
    tracciati che ci cadono dentro: le province (anche delle regioni vicine,
    per il contesto) e i confini regionali. Solleva KeyError se la regione non
    ha un tracciato."""
    x0, y0, x1, y1 = bbox(REGION_PATHS[region_key])
    w, h = max(x1 - x0, min_side), max(y1 - y0, min_side)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = w * (1 + 2 * pad), h * (1 + 2 * pad)
    box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    return {
        "viewbox": " ".join(f"{v:g}" for v in (round(box[0], 1), round(box[1], 1), round(w, 1), round(h, 1))),
        "provinces": {k: d for k, d in PROVINCE_PATHS.items() if _overlaps(bbox(d), box)},
        "borders": {k: d for k, d in REGION_PATHS.items() if _overlaps(bbox(d), box)},
    }
