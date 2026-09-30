"""I centroidi delle 107 province, per il gioco sulle province.

Legge `app/design/province_paths.json` ({chiave: attributo d}, comandi relativi
e coordinate proiettate nel viewBox 560x660, non lat/lon) e scrive
`app/static/data/province_centroidi.json`.

Per ogni provincia prende il poligono piu' grande (le isole minori non spostano
il punto: il centroide di Livorno sta sulla costa, non fra la costa e l'Elba) e
ne calcola il centroide pesato per area con la formula dei poligoni. Scrive
anche il riquadro di quel poligono (`w`, `h`, in unita' del viewBox): il gioco
lo usa per escludere dalle province "giocabili" quelle la cui sagoma sarebbe
illeggibile sulla mappa.

    bin/py design/v1/tools/centroidi_province.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "app" / "design" / "province_paths.json"
TARGET = ROOT / "app" / "static" / "data" / "province_centroidi.json"
VIEWBOX = (560, 660)

_TOKEN = re.compile(r"[A-Za-z]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?")


def poligoni(d: str) -> list[list[tuple[float, float]]]:
    """I sottotracciati di un attributo `d` fatto di M, L, H, V, Z (assoluti o
    relativi), come punti. Un comando diverso e' un errore: meglio fermarsi che
    calcolare un centroide su un tracciato letto male."""
    anelli: list[list[tuple[float, float]]] = []
    corrente: list[tuple[float, float]] = []
    x = y = sx = sy = 0.0
    cmd = None
    pending: list[float] = []
    for tok in _TOKEN.findall(d):
        if tok.isalpha():
            if tok not in "MmLlHhVvZz":
                raise ValueError(f"comando {tok!r} non gestito nel tracciato {d[:40]!r}")
            cmd = tok
            pending = []
            if cmd in "Zz":
                if corrente:
                    anelli.append(corrente)
                corrente = []
                x, y = sx, sy
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
                if corrente:
                    anelli.append(corrente)
                corrente = []
                sx, sy = x, y
                cmd = "l" if cmd == "m" else "L"
        pending = []
        corrente.append((x, y))
    if corrente:
        anelli.append(corrente)
    return [a for a in anelli if len(a) >= 3]


def area_e_centroide(anello: list[tuple[float, float]]) -> tuple[float, float, float]:
    """(area con segno, cx, cy) di un poligono. Area nulla: media dei vertici."""
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(anello, anello[1:] + anello[:1]):
        croce = x0 * y1 - x1 * y0
        a += croce
        cx += (x0 + x1) * croce
        cy += (y0 + y1) * croce
    a /= 2
    if abs(a) < 1e-9:
        return 0.0, sum(p[0] for p in anello) / len(anello), sum(p[1] for p in anello) / len(anello)
    return a, cx / (6 * a), cy / (6 * a)


def centroide_provincia(d: str) -> dict:
    anelli = poligoni(d)
    if not anelli:
        raise ValueError(f"tracciato senza poligoni: {d[:40]!r}")
    anello = max(anelli, key=lambda r: abs(area_e_centroide(r)[0]))
    area, cx, cy = area_e_centroide(anello)
    xs = [p[0] for p in anello]
    ys = [p[1] for p in anello]
    return {
        "x": round(cx, 2),
        "y": round(cy, 2),
        "w": round(max(xs) - min(xs), 2),
        "h": round(max(ys) - min(ys), 2),
        "area": round(abs(area), 2),
    }


def main() -> None:
    tracciati = json.loads(SOURCE.read_text(encoding="utf-8"))
    province = {chiave: centroide_provincia(d) for chiave, d in sorted(tracciati.items())}
    fuori = [c for c, p in province.items() if not (0 <= p["x"] <= VIEWBOX[0] and 0 <= p["y"] <= VIEWBOX[1])]
    if fuori:
        raise SystemExit(f"centroidi fuori dal viewBox: {fuori}")
    payload = {"viewBox": list(VIEWBOX), "province": province}
    TARGET.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8")
    print(f"{len(province)} centroidi scritti in {TARGET.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
