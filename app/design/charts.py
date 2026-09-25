"""I grafici della 1.0, disegnati lato server in SVG.

Quattro disegni che tornano in piu' pagine:

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
- la sparkline: una serie in una linea e un punto, con l'asse per anno, in due
  taglie fisse accanto a una cifra scritta in testo.

I primi tre escono in tre tagli, molto largo, largo e stretto, cosi' il testo
resta a 12-13 pixel veri dallo schermo grande al telefono. La sparkline no: non
ha testo, e la sua misura e' quella dei pixel. I colori stanno nel CSS, per classe: niente
esadecimali qui. Accanto a ogni grafico la pagina tiene una tabella con gli
stessi dati.
"""

from __future__ import annotations

import math
import re
from functools import lru_cache
from html import escape
from itertools import pairwise

from app.design import numfmt as n

AREA_OF_REGION_AREA = {"Nord": "nord", "Centro": "centro", "Sud": "sud", "Isole": "sud"}

# Il terzo taglio, per gli schermi larghi: col contenitore a 1440 pixel il
# taglio da 920 lasciava vuoto un terzo della riga. Il CSS lo mostra da 1100
# pixel di grafico in su, cosi' il testo non scende mai sotto i 12 pixel veri.
XL_WIDTH = 1180
AREA_LABEL = {"nord": "Nord", "centro": "Centro", "sud": "Mezzogiorno"}


@lru_cache(maxsize=1)
def _area_map() -> tuple[tuple[str, str], ...]:
    from app import province_profile
    from app.data import REGION_GEO_AREA

    out = {k: AREA_OF_REGION_AREA[v] for k, v in REGION_GEO_AREA.items()}
    for region_key, provinces in province_profile.by_region().items():
        for p in provinces:
            key = p.get("key") or p.get("province_key") or p.get("chiave")
            if key and region_key in out:
                out[key] = out[region_key]
    return tuple(out.items())


def area_map() -> dict[str, str]:
    """{chiave di regione o provincia: nord | centro | sud}.

    Si calcola una volta per processo, come i loader dei dati: le province non
    cambiano ripartizione fra una richiesta e l'altra. Esce una copia, cosi'
    chi la modifica non sporca quella degli altri."""
    return dict(_area_map())


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
                  decimals: int | None = None, xl_width: int = XL_WIDTH) -> dict:
    """La striscia del divario in due tagli, piu' la legenda delle ripartizioni presenti.

    `highlight` e' la chiave del territorio della pagina: il suo punto prende
    l'anello dell'accento e il suo nome. `gap_label` sostituisce "2,5 volte"
    quando il rapporto non ha senso (un punteggio da 0 a 100 si legge in punti).
    `xl_width` e' la larghezza del taglio largo: la home stende la striscia su
    tutto il contenitore, la scheda la tiene a XL_WIDTH accanto al testo.
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
    xl = _strip(rows, avg, unit, xl_width, False, ratio, highlight, avg_label, decimals)
    wide = _strip(rows, avg, unit, 920, False, ratio, highlight, avg_label, decimals)
    narrow = _strip(rows, avg, unit, 360, True, ratio, highlight, avg_label, decimals)
    counts = {}
    for row in rows:
        counts[row.get("area")] = counts.get(row.get("area"), 0) + 1
    legend = [{"area": a, "label": AREA_LABEL[a], "count": counts[a]} for a in ("nord", "centro", "sud") if a in counts]
    return {"svg": f'<div class="chart__xl">{xl}</div><div class="chart__l">{wide}</div><div class="chart__s">{narrow}</div>',
            "legend": legend}


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
    xl, _ = _band(level, areas, XL_WIDTH, 380, 220, False)
    wide, years = _band(level, areas, 920, 340, 200, False)
    narrow, _ = _band(level, areas, 360, 280, 112, True)
    return {"svg": f'<div class="chart__xl">{xl}</div><div class="chart__l">{wide}</div><div class="chart__s">{narrow}</div>',
            "single_year": False, "first": years[0], "last": years[-1]}


# ---------------------------------------------------------------- sparkline

# Le due taglie, in pixel veri: il viewBox e' la misura in cui la curva si
# disegna, e nessun CSS la stira. Prima il filtro disegnava in 140x36 e il CSS
# lo schiacciava in 88x28 con `preserveAspectRatio="none"`: il tratto e il
# punto finale uscivano ovali e la pendenza non era quella dei dati.
SPARK_SIZES = {"s": (88, 28), "m": (120, 32)}
# Il margine tiene dentro la tela il punto finale (raggio 2,5) e il tratto.
SPARK_PAD = 3.0
SPARK_DOT_R = 2.5


def spark_floor(values) -> float | None:
    """Il pavimento della sparkline: lo scarto interquartile dei valori dei
    territori nell'ultimo anno, con i quartili per interpolazione lineare.

    La regola sta qui, in un posto solo, e chi disegna una sparkline le passa
    i valori, non un numero calcolato altrove. None sotto i due valori, e zero
    quando i territori del quartile centrale sono pari: in tutti e due i casi
    la sparkline si disegna senza pavimento."""
    vals = sorted(float(v) for v in values if v is not None)
    if len(vals) < 2:
        return None

    def quartile(p):
        k = (len(vals) - 1) * p
        f = int(k)
        c = min(f + 1, len(vals) - 1)
        return vals[f] + (vals[c] - vals[f]) * (k - f)

    return quartile(0.75) - quartile(0.25)


def spark(points, size: str = "s", floor: float | None = None, compact: bool = False) -> str:
    """La sparkline: una serie `{year, value}` in una linea e un punto finale.

    - L'asse x e' per anno, non per posizione. Le indagini periodiche saltano
      degli anni ("Aree terrestri protette" passa dal 2003 al 2010): la linea
      unisce i due punti e il salto si vede come un tratto lungo, invece di
      valere quanto un anno solo.
    - `floor` e' il pavimento della scala verticale, nell'unita' della serie.
      Quando la serie si muove meno del pavimento la scala si allarga al
      pavimento attorno al centro, e la linea resta quasi piatta: chi chiama
      passa lo scarto interquartile dei territori nell'ultimo anno, cosi' una
      variazione piccola rispetto alla distanza fra i territori non si disegna
      come una salita. Senza pavimento la serie riempie l'altezza.
    - Sotto i due punti non c'e' niente da disegnare, ed esce una stringa vuota.
    - Colori solo per classe (`.spark__line`, `.spark__dot`), niente
      esadecimali. `aria-hidden` sempre: le cifre stanno in testo accanto.
    - `compact` scrive la stessa linea con le coordinate al pixel intero e in
      passi relativi (`M3 20l16 2 17-6`): e' per le pagine che ne mettono
      centinaia, come l'atlante con le sue 594 righe, dove la forma lunga
      pesava da sola 32 KB compressi. Il disegno e' lo stesso, al mezzo pixel.
    """
    if size not in SPARK_SIZES:
        size = "s"
    width, height = SPARK_SIZES[size]
    pts = sorted(
        (int(p["year"]), float(p["value"]))
        for p in (points or [])
        if p.get("value") is not None and p.get("year") is not None
    )
    if len(pts) < 2:
        return ""
    y0, y1 = pts[0][0], pts[-1][0]
    vals = [v for _, v in pts]
    lo, hi = min(vals), max(vals)
    if floor and hi - lo < floor:
        mid = (lo + hi) / 2
        lo, hi = mid - floor / 2, mid + floor / 2
    inner_w, inner_h = width - 2 * SPARK_PAD, height - 2 * SPARK_PAD

    def x(yr):
        return SPARK_PAD + (yr - y0) / ((y1 - y0) or 1) * inner_w

    def y(v):
        # Una serie piatta e senza pavimento si disegna a meta' altezza.
        if hi == lo:
            return height / 2
        return SPARK_PAD + (hi - v) / (hi - lo) * inner_h

    coords = [(x(yr), y(v)) for yr, v in pts]
    if compact:
        whole = [(round(cx), round(cy)) for cx, cy in coords]
        steps = " ".join(f"{bx - ax} {by - ay}" for (ax, ay), (bx, by) in pairwise(whole)).replace(" -", "-")
        lx, ly = whole[-1]
        return (f'<svg class="spark spark--{size}" '
                f'viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
                f'aria-hidden="true" focusable="false">'
                f'<path class="spark__line" d="M{whole[0][0]} {whole[0][1]}l{steps}"/>'
                f'<circle class="spark__dot" cx="{lx}" cy="{ly}" r="{SPARK_DOT_R}"/>'
                f"</svg>")
    line = " ".join(f"{cx:.1f},{cy:.1f}" for cx, cy in coords)
    lx, ly = coords[-1]
    return (f'<svg class="spark spark--{size}" '
            f'viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
            f'aria-hidden="true" focusable="false">'
            f'<polyline class="spark__line" points="{line}"/>'
            f'<circle class="spark__dot" cx="{lx:.1f}" cy="{ly:.1f}" r="{SPARK_DOT_R}"/>'
            f'</svg>')


# ---------------------------------------------------------------- richiami sulla mappa

def path_rings(d: str) -> list[list[tuple[float, float]]]:
    """Gli anelli di un tracciato, in coordinate assolute. Le regioni sono
    scritte con `M` e `L` assoluti, le province con `m`/`l` relativi (piu'
    leggeri): qui si leggono tutti e due."""
    rings: list[list[tuple[float, float]]] = []
    x = y = 0.0
    cmd = "M"
    tokens = re.findall(r"[MmLlZz]|-?\d*\.?\d+", d)
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in "MmLlZz":
            cmd = tok
            i += 1
            if tok in "Zz":
                # Dopo z il punto corrente torna all'inizio del sottotracciato
                # (specifica SVG): una m relativa che segue parte da li'.
                cmd = "L"
                if rings:
                    x, y = rings[-1][0]
            continue
        dx, dy = float(tok), float(tokens[i + 1])
        i += 2
        if cmd in "Mm":
            x, y = (x + dx, y + dy) if cmd == "m" and rings else (dx, dy)
            rings.append([(x, y)])
            cmd = "l" if cmd == "m" else "L"
        elif cmd == "l":
            x, y = x + dx, y + dy
            rings[-1].append((x, y))
        else:
            x, y = dx, dy
            rings[-1].append((x, y))
    return rings


def _largest_subpath_centroid(d: str) -> tuple[float, float]:
    """Il baricentro del poligono piu' grande del tracciato (formula del laccio)."""
    best = (0.0, (0.0, 0.0))
    for pts in path_rings(d):
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


# L'altezza di un richiamo (nome piu' valore) in unita' del viewBox.
CALLOUT_GAP = 50


def map_callouts(paths: dict[str, str], items: list[tuple[str, str, str]]) -> str:
    """Nome e valore di alcuni territori sulla mappa, con un filo dal baricentro.

    `items` e' una lista di (chiave, nome, valore gia' scritto). Le etichette
    stanno ai bordi del disegno, verso il mare: a destra per chi sta a est o
    al nord, a sinistra per le isole e il Tirreno. Il filo corre in orizzontale
    dal baricentro all'etichetta, e il testo ha un alone del colore di fondo.
    """
    out = []
    placed: list[tuple[bool, float]] = []
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
        # Due estremi vicini sullo stesso bordo (con le province succede:
        # Fermo e Macerata) avevano i testi uno sopra l'altro. Il secondo si
        # sposta di un'etichetta, e il filo va in obliquo fino a lui.
        ty = cy
        for side, other in placed:
            if side == east and abs(ty - other) < CALLOUT_GAP:
                ty = other + CALLOUT_GAP if cy >= other else other - CALLOUT_GAP
        ty = min(max(ty, 24.0), 636.0)
        placed.append((east, ty))
        out.append(f'<g class="callout"><line x1="{cx:.1f}" y1="{cy:.1f}" x2="{lx:.1f}" y2="{ty:.1f}"/>'
                   f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5"/>'
                   f'<text x="{tx}" y="{ty - 4:.1f}" text-anchor="{anchor}"><tspan class="callout__nm">{escape(name)}</tspan>'
                   f'<tspan x="{tx}" dy="24" class="callout__v">{escape(value)}</tspan></text></g>')
    return "".join(out)
