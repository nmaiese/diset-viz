"""I grafici della 1.0, disegnati lato server in SVG.

Tre disegni che tornano in piu' pagine:

- la striscia del divario: ogni territorio e' un punto sulla stessa scala, nel
  colore della sua ripartizione (Nord, Centro, Mezzogiorno), con i due estremi
  nominati, la media semplice e la distanza fra primo e ultimo. E' il segno
  della 1.0: il divario si vede prima di leggerlo.
- la serie a fascia: la fascia fra il valore piu' alto e il piu' basso di ogni
  anno, la media semplice, i due territori agli estremi. La larghezza della
  fascia e' il divario nel tempo.
- i richiami sulla mappa: nome e valore dei due estremi, con un filo che parte
  dal baricentro del pezzo piu' grande della regione (non dal rettangolo che la
  contiene, che per la Campania o la Liguria cade in mare).

Ogni disegno esce in due tagli, largo e stretto, cosi' il testo resta a 12-13
pixel veri anche sul telefono. I colori stanno nel CSS, per classe: niente
esadecimali qui. Accanto a ogni grafico la pagina tiene una tabella con gli
stessi dati.
"""

from __future__ import annotations

import math
import re
from html import escape

import numfmt as n

AREA_OF_REGION_AREA = {"Nord": "nord", "Centro": "centro", "Sud": "sud", "Isole": "sud"}
AREA_LABEL = {"nord": "Nord", "centro": "Centro", "sud": "Mezzogiorno"}


def area_map() -> dict[str, str]:
    """{chiave di regione o provincia: nord | centro | sud}."""
    from app import province_profile
    from app.data import REGION_GEO_AREA

    out = {k: AREA_OF_REGION_AREA[v] for k, v in REGION_GEO_AREA.items()}
    for region_key, provinces in province_profile.by_region().items():
        for p in provinces:
            key = p.get("key") or p.get("province_key") or p.get("chiave")
            if key and region_key in out:
                out[key] = out[region_key]
    return out


SHORT_NAMES = {
    "Trentino Alto Adige": "Trentino A.A.", "Trentino-Alto Adige": "Trentino A.A.",
    "Friuli-Venezia Giulia": "Friuli V.G.", "Friuli Venezia Giulia": "Friuli V.G.",
    "Monza e della Brianza": "Monza Brianza", "Reggio Calabria": "Reggio Cal.",
    "Reggio nell'Emilia": "Reggio Emilia", "Barletta-Andria-Trani": "Barletta A.T.",
    "Verbano-Cusio-Ossola": "Verbano C.O.", "Pesaro e Urbino": "Pesaro Urbino",
    "Valle d'Aosta": "Valle d'Aosta", "Emilia-Romagna": "Emilia-Romagna",
}


def short_name(name: str, limit: int = 14) -> str:
    """Il nome per il taglio stretto: intero se ci sta, altrimenti l'abbreviazione
    d'uso, altrimenti le parole intere che ci stanno. Mai un taglio a meta' parola."""
    if len(name) <= limit:
        return name
    if name in SHORT_NAMES:
        return SHORT_NAMES[name]
    out = ""
    for word in re.split(r"(?<=[ -])", name):
        if len(out + word) > limit:
            break
        out += word
    return (out.strip(" -") or name[:limit]) + "."


def _nice(lo: float, hi: float, target: int = 4) -> list[float]:
    span = (hi - lo) or abs(hi) or 1
    raw = span / target
    mag = 10 ** math.floor(math.log10(raw))
    step = min((s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw), default=10 * mag)
    t = math.floor(lo / step) * step
    ticks = []
    while not ticks or ticks[-1] < hi:
        ticks.append(round(t, 10))
        t += step
    return ticks


def _tick(v: float, ticks: list[float]) -> str:
    step = abs(ticks[1] - ticks[0]) if len(ticks) > 1 else 1
    d = 0 if step >= 1 else min(2, max(1, -math.floor(math.log10(step))))
    return n.text(v, d)


# ---------------------------------------------------------------- striscia del divario

def _strip(rows, avg, unit, width, short, ratio_text, highlight=None, avg_label=None, decimals=None):
    left, right = (16, 16)
    top = 74 if not short else 70
    r = 6.5 if len(rows) <= 30 else 4.2
    vals = [row["value"] for row in rows]
    lo, hi = min(vals), max(vals)
    ticks = _nice(lo, hi, 4 if not short else 3)
    x0, x1 = ticks[0], ticks[-1]
    plot = width - left - right

    def x(v):
        return left + (v - x0) / ((x1 - x0) or 1) * plot

    # Punti impilati quando si sovrappongono: il primo livello libero, sopra e sotto.
    placed = []
    for row in sorted(rows, key=lambda row: row["value"]):
        cx = x(row["value"])
        level = 0
        while any(abs(cx - px) < 2 * r + 1 and pl == level for px, pl, _ in placed):
            level = -level if level > 0 else -level + 1
        placed.append((cx, level, row))
    depth = max(abs(pl) for _, pl, _ in placed)
    mid = top + (depth + 1) * (2 * r + 1)
    height = int(mid + (depth + 1) * (2 * r + 1) + 34)
    parts = [f'<svg viewBox="0 0 {width} {height}" aria-hidden="true" focusable="false" class="strip">']
    parts.append(f'<line class="strip__axis" x1="{left}" x2="{width - right}" y1="{mid:.1f}" y2="{mid:.1f}"/>')
    for t in ticks:
        anchor = "start" if t == ticks[0] else ("end" if t == ticks[-1] else "middle")
        parts.append(f'<text class="strip__tick" x="{x(t):.1f}" y="{height - 6}" text-anchor="{anchor}">{escape(_tick(t, ticks))}</text>')
    if avg is not None:
        ax = x(avg)
        parts.append(f'<line class="strip__avg" x1="{ax:.1f}" x2="{ax:.1f}" y1="{top - 10}" y2="{height - 24}"/>')
        label = avg_label or (("Media " if short else "Media semplice ") + n.text(avg))
        anchor = "start" if ax < width * 0.7 else "end"
        dx = 5 if anchor == "start" else -5
        parts.append(f'<text class="strip__avglab" x="{ax + dx:.1f}" y="{height - 22}" text-anchor="{anchor}">{escape(label)}</text>')
    # La distanza fra primo e ultimo: una graffa sopra i punti.
    xa, xb = x(lo), x(hi)
    by = 22
    parts.append(f'<path class="strip__gap" d="M{xa:.1f},{by + 6} V{by} H{xb:.1f} V{by + 6}"/>')
    parts.append(f'<text class="strip__gaplab" x="{(xa + xb) / 2:.1f}" y="{by - 6}" text-anchor="middle">{escape(ratio_text)}</text>')
    for cx, level, row in placed:
        cy = mid + level * (2 * r + 1)
        area = row.get("area") or "none"
        on = " is-on" if highlight and row["key"] == highlight else ""
        parts.append(f'<circle class="strip__dot area--{area}{on}" data-key="{escape(row["key"])}" cx="{cx:.1f}" cy="{cy:.1f}" r="{r}"><title>{escape(row["name"])} {escape(n.text(row["value"], decimals))}</title></circle>')
    # Il territorio della pagina, se c'e', nominato sotto l'asse.
    low, high = min(rows, key=lambda q: q["value"]), max(rows, key=lambda q: q["value"])
    if highlight and highlight not in (low["key"], high["key"]):
        hit = next((q for q in placed if q[2]["key"] == highlight), None)
        if hit:
            hx, _, hrow = hit
            label_w = (len(hrow["name"]) + 6) * 7.2
            lx = min(max(hx, left + label_w / 2), width - right - label_w / 2)
            parts.append(f'<text class="strip__name strip__name--on" x="{lx:.1f}" y="{top - 3}" text-anchor="middle">'
                         f'<tspan class="strip__nm">{escape(hrow["name"])}</tspan> <tspan class="strip__v">{escape(n.text(hrow["value"], decimals))}</tspan></text>')
    # I due estremi con nome e valore, sotto la graffa.
    for row, anchor in ((low, "start"), (high, "end")):
        cx = x(row["value"])
        name = short_name(row["name"]) if short else row["name"]
        tx = cx - r if anchor == "start" else cx + r
        parts.append(f'<text class="strip__name" x="{tx:.1f}" y="{top - 20}" text-anchor="{anchor}" dy="0">'
                     f'<tspan class="strip__nm">{escape(name)}</tspan> <tspan class="strip__v">{escape(n.text(row["value"], decimals))}</tspan></text>')
    parts.append("</svg>")
    return "".join(parts)


def divario_strip(rows: list[dict], avg: float | None, unit: str | None, gap_ratio: float | None = None,
                  highlight: str | None = None, gap_label: str | None = None, avg_label: str | None = None,
                  decimals: int | None = None) -> dict:
    """La striscia del divario in due tagli, piu' la legenda delle ripartizioni presenti.

    `highlight` e' la chiave del territorio della pagina: il suo punto prende
    l'anello dell'accento e il suo nome. `gap_label` sostituisce "2,5 volte"
    quando il rapporto non ha senso (un punteggio da 0 a 100 si legge in punti).
    """
    rows = [row for row in rows if row.get("value") is not None]
    if len(rows) < 2:
        return {"svg": "", "legend": []}
    lo, hi = min(r["value"] for r in rows), max(r["value"] for r in rows)
    if gap_label:
        ratio = gap_label
    elif gap_ratio and lo > 0:
        ratio = f"{n.text(gap_ratio, 1)} volte"
    else:
        ratio = f"distanza {n.text(hi - lo)}"
    wide = _strip(rows, avg, unit, 920, False, ratio, highlight, avg_label, decimals)
    narrow = _strip(rows, avg, unit, 360, True, ratio, highlight, avg_label, decimals)
    counts = {}
    for row in rows:
        counts[row.get("area")] = counts.get(row.get("area"), 0) + 1
    legend = [{"area": a, "label": AREA_LABEL[a], "count": counts[a]} for a in ("nord", "centro", "sud") if a in counts]
    return {"svg": f'<div class="chart__l">{wide}</div><div class="chart__s">{narrow}</div>', "legend": legend}


# ---------------------------------------------------------------- serie a fascia

def _band(level, areas, width, height, right, short):
    matrix = level.get("matrix") or {}
    years = sorted(int(y) for y in matrix)
    names = {t["key"]: t["name"] for t in level.get("territories") or []}
    means = {int(p["year"]): p["avg"] for p in level.get("annual_means") or [] if p.get("avg") is not None}
    per_year = {y: [v for v in (matrix[str(y)] or {}).values() if v is not None] for y in years}
    all_vals = [v for vs in per_year.values() for v in vs]
    ticks = _nice(min(all_vals), max(all_vals), 4)
    left = 46 if short else 60
    top, bottom = 16, 30
    pw, ph = width - left - right, height - top - bottom

    def x(yr):
        return left + (yr - years[0]) / ((years[-1] - years[0]) or 1) * pw

    def y(v):
        return top + (1 - (v - ticks[0]) / ((ticks[-1] - ticks[0]) or 1)) * ph

    def pts(series):
        return " ".join(f"{x(yr):.1f},{y(v):.1f}" for yr, v in series if v is not None)

    parts = [f'<svg viewBox="0 0 {width} {height}" aria-hidden="true" focusable="false" class="band">']
    for t in ticks:
        parts.append(f'<line class="band__grid" x1="{left}" x2="{left + pw}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>')
        parts.append(f'<text class="band__tick" x="{left - 8}" y="{y(t) + 4:.1f}" text-anchor="end">{escape(_tick(t, ticks))}</text>')
    span = years[-1] - years[0]
    step = (10 if short else 5) if span > 12 else (2 if span > 6 else 1)
    marks = [yr for yr in years if (yr - years[0]) % step == 0]
    if years[-1] not in marks:
        if marks and years[-1] - marks[-1] < step / 2:
            marks[-1] = years[-1]
        else:
            marks.append(years[-1])
    for yr in marks:
        anchor = "start" if yr == years[0] else ("end" if yr == years[-1] else "middle")
        parts.append(f'<text class="band__tick" x="{x(yr):.1f}" y="{height - 8}" text-anchor="{anchor}">{yr}</text>')
    usable = [yr for yr in years if per_year[yr]]
    upper = [(yr, max(per_year[yr])) for yr in usable]
    lower = [(yr, min(per_year[yr])) for yr in usable]
    poly = " ".join(f"{x(a):.1f},{y(b):.1f}" for a, b in upper + list(reversed(lower)))
    parts.append(f'<polygon class="band__area" points="{poly}"/>')
    # Tutte le serie, nascoste: il JavaScript ne copia i punti quando il lettore sceglie un territorio.
    for key in names:
        series = [(yr, (matrix[str(yr)] or {}).get(key)) for yr in years]
        if sum(v is not None for _, v in series) >= 2:
            parts.append(f'<polyline class="band__src" data-key="{escape(key)}" points="{pts(series)}"/>')
    last = years[-1]
    ends = {k: v for k, v in (matrix[str(last)] or {}).items() if v is not None}
    labels = []
    if ends:
        for key in (max(ends, key=ends.get), min(ends, key=ends.get)):
            series = [(yr, (matrix[str(yr)] or {}).get(key)) for yr in years]
            area = areas.get(key, "none")
            parts.append(f'<polyline class="band__ext area-line--{area}" points="{pts(series)}"/>')
            nm = names.get(key, key)
            nm = short_name(nm, 13) if short else nm
            labels.append((y(ends[key]), f"{nm} {n.text(ends[key])}", f"band__lab area-text--{area}"))
    avg_series = [(yr, means.get(yr)) for yr in years]
    parts.append(f'<polyline class="band__avg" points="{pts(avg_series)}"/>')
    last_avg = [v for _, v in avg_series if v is not None][-1]
    labels.append((y(last_avg), ("Media " if short else "Media semplice ") + n.text(last_avg), "band__lab band__lab--avg"))
    labels.sort()
    placed = []
    for ly, label, cls in labels:
        if placed and ly - placed[-1] < 16:
            ly = placed[-1] + 16
        placed.append(ly)
        parts.append(f'<text class="{cls}" x="{left + pw + 8}" y="{ly + 4:.1f}">{escape(label)}</text>')
    parts.append('<polyline class="band__hl" points="" data-hl/><circle class="band__dot" r="0" cx="0" cy="0" data-hl-dot/>'
                 f'<text class="band__hllab" x="{left + pw + 8}" y="-20" data-hl-lab></text>')
    parts.append("</svg>")
    return "".join(parts), years


def band_series(level: dict, areas: dict) -> dict:
    matrix = level.get("matrix") or {}
    if len(matrix) < 2:
        return {"svg": "", "single_year": True}
    wide, years = _band(level, areas, 920, 340, 200, False)
    narrow, _ = _band(level, areas, 360, 280, 112, True)
    return {"svg": f'<div class="chart__l">{wide}</div><div class="chart__s">{narrow}</div>',
            "single_year": False, "first": years[0], "last": years[-1]}


# ---------------------------------------------------------------- richiami sulla mappa

def _largest_subpath_centroid(d: str) -> tuple[float, float]:
    """Il baricentro del poligono piu' grande del tracciato (formula del laccio)."""
    best = (0.0, (0.0, 0.0))
    for sub in re.findall(r"M[^M]*", d):
        pts = [(float(a), float(b)) for a, b in re.findall(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", sub)]
        if len(pts) < 3:
            continue
        area = cx = cy = 0.0
        for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
            cross = x0 * y1 - x1 * y0
            area += cross
            cx += (x0 + x1) * cross
            cy += (y0 + y1) * cross
        if abs(area) > abs(best[0]):
            best = (area, (cx / (3 * area), cy / (3 * area)))
    return best[1]


def map_callouts(paths: dict[str, str], items: list[tuple[str, str, str]]) -> str:
    """Nome e valore di alcuni territori sulla mappa, con un filo dal baricentro.

    `items` e' una lista di (chiave, nome, valore gia' scritto). Le etichette
    stanno ai bordi del disegno, verso il mare: a destra per chi sta a est o
    al nord, a sinistra per le isole e il Tirreno. Il filo corre in orizzontale
    dal baricentro all'etichetta, e il testo ha un alone del colore di fondo.
    """
    out = []
    for key, name, value in items:
        if key not in paths:
            continue
        cx, cy = _largest_subpath_centroid(paths[key])
        east = cx > 200 or cy < 200
        # La mappa si disegna a 340-400 pixel su 560 di viewBox: il testo sta a
        # 21 unita' per uscire a 13-15 pixel veri.
        width = max(len(name), len(value)) * 11 + 10
        if east:
            tx, anchor, lx = 552, "end", 552 - width
        else:
            tx, anchor, lx = 8, "start", 8 + width
        out.append(f'<g class="callout"><line x1="{cx:.1f}" y1="{cy:.1f}" x2="{lx:.1f}" y2="{cy:.1f}"/>'
                   f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5"/>'
                   f'<text x="{tx}" y="{cy - 4:.1f}" text-anchor="{anchor}"><tspan class="callout__nm">{escape(name)}</tspan>'
                   f'<tspan x="{tx}" dy="24" class="callout__v">{escape(value)}</tspan></text></g>')
    return "".join(out)
