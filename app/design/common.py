"""I pezzi comuni alle pagine della 1.0: frasi, cifre, classifiche, mappa.

Ogni pagina ha il suo modulo in `app/design/pages/`, che prende il contesto
della view e restituisce cio' che il template chiede in piu' rispetto ai dati:
tessere, titoli-affermazione dei grafici, righe della classifica, classi della
mappa, i grafici disegnati. Qui stanno i pezzi che ne usano piu' d'una. I
numeri passano da `numfmt`, cosi' una cifra si scrive in un modo solo.

Una cifra che non si puo' calcolare non si inventa. Le funzioni che compongono
una frase restituiscono None quando manca un dato, e la pagina toglie la
frase. `PLACEHOLDER` resta come segnale per le poche che scrivono una cifra
nuda: non deve mai arrivare in una pagina, e lo controlla
`tests/integration/test_v1_pages.py`.
"""

from __future__ import annotations

import json
import math
import re
from html import escape
from pathlib import Path

from app.data import REGION_GEO_AREA
from app.design import numfmt
from app.seo_titles import ARTICLED_PROVINCES, format_number, of_region

PLACEHOLDER = "[dato da calcolare]"
# I contorni delle regioni, quantizzati per la mappa della 1.0 (viewBox 560x660).
PATHS = json.loads((Path(__file__).resolve().parent / "italy_paths.json").read_text(encoding="utf-8"))
MEZZOGIORNO = {key for key, area in REGION_GEO_AREA.items() if area in ("Sud", "Isole")}
LOWER_BETTER = ("lower_better", "higher_worse")
MONTHS = ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
          "agosto", "settembre", "ottobre", "novembre", "dicembre")


def num(value) -> str:
    """La cifra all'italiana con i decimali calibrati sulla grandezza (numfmt)."""
    return PLACEHOLDER if value is None else numfmt.text(value)


def short_unit(unit: str | None) -> str | None:
    return numfmt.short_unit(unit)


# Le province che vogliono l'articolo: "del Verbano-Cusio-Ossola", "del Sud Sardegna".
PROVINCE_OF = {name: f"del {name}" for name in ARTICLED_PROVINCES}


def of_place(name: str, level_key: str) -> str:
    """"della Basilicata", "del Piemonte" per le regioni, "di Milano" per le province."""
    if level_key == "regione":
        return of_region(name)
    if name in PROVINCE_OF:
        return PROVINCE_OF[name]
    if name.startswith("L'"):
        return f"dell'{name[2:]}"
    if name.startswith("La "):
        return f"della {name[3:]}"
    return f"di {name}"


def the_place(name: str, level_key: str) -> str:
    """"il Trentino Alto Adige", "la Calabria", "l'Umbria" per le regioni, il nome nudo per le province
    (tranne quelle che vogliono l'articolo: "il Sud Sardegna")."""
    if level_key != "regione":
        return PROVINCE_OF[name].replace("del ", "il ", 1) if name in PROVINCE_OF else name
    of = of_region(name)
    return {"del ": "il ", "dell'": "l'", "della ": "la ", "delle ": "le "}.get(
        next(p for p in ("delle ", "della ", "dell'", "del ") if of.startswith(p)), "") + name


def del_(text: str) -> str:
    """"del 3,6%" ma "dell'11,3%", "dell'8%" e "dello 0,5%": l'articolo davanti a
    una cifra lo decide `numfmt.articulated`, la stessa regola dei title. Quella
    scritta qui vedeva "11" in testa a 116 e diceva "dell'116%"."""
    return numfmt.articulated("di", text)


GENERIC_UNITS = numfmt.GENERIC_UNITS
RATE_BASE = numfmt.RATE_BASE
phrase_unit = numfmt.phrase_unit


def unit_note(unit: str | None, name: str | None = None) -> str | None:
    """L'unita' come complemento dopo il nome della misura: "in euro", "in %",
    "per mille abitanti", "ogni cento abitanti", "valori per abitante". None
    quando l'etichetta non e' un'unita', o quando il nome dell'indicatore la
    dice gia' ("Ospiti ... per centomila anziani, ogni centomila anziani").
    Prima si scriveva "in" davanti a tutto, e usciva "valori in per mille
    abitanti". Una percentuale e' "in %" comunque la scriva la fonte
    ("percentuale", "Valori percentuali"), come la cifra accanto
    (`numfmt.phrase_unit`)."""
    raw = (unit or "").strip()
    if not raw:
        return None
    if numfmt.is_percent(raw):
        return "in %"
    u = numfmt.lower_first(raw)
    if name and u.lower() in name.lower():
        return None
    short = short_unit(raw)
    if (short and numfmt.lower_first(short) in GENERIC_UNITS) or u.startswith("numero puro"):
        return None
    if u.startswith(("per ", "ogni ", "valori ")):
        return u
    if RATE_BASE.match(u):
        return "ogni " + u
    return "in " + u


def values_note(unit: str | None) -> str | None:
    """"valori in euro", "valori per mille abitanti": la nota sotto la striscia."""
    note = unit_note(unit)
    if note is None:
        return None
    return note if note.startswith("valori ") else f"valori {note}"


def with_unit(value, unit: str | None, decimals: int | None = None) -> str:
    """`54.637 euro`, `78,8%`: l'unita' accanto alla cifra, spazio insecabile.
    L'unita' e' quella che si scrive dentro una frase (`phrase_unit`), e manca
    quando l'etichetta della fonte non e' un'unita'. `decimals` quando la cifra
    deve coincidere con quella di una colonna (numfmt.column_decimals)."""
    text = num(value) if decimals is None or value is None else numfmt.text(value, decimals)
    u = phrase_unit(unit)
    if u == "%":
        return f"{text}%"
    return f"{text} {u}" if u else text


def signed(value, unit: str | None) -> str:
    if value is None:
        return PLACEHOLDER
    text = numfmt.text(value, sign=True)
    u = phrase_unit(unit)
    if u == "%":
        return text + "%"
    return f"{text}\u00a0{u}" if u else text


def figure(value, unit: str | None, sign: bool = False) -> dict:
    """La cifra di una tessera: numero e unita' separati, perche' l'unita' si
    compone piu' piccola. La percentuale resta attaccata al numero."""
    if value is None:
        return {"num": PLACEHOLDER, "unit": None}
    text = num(abs(value) if sign else value)
    if sign:
        text = ("+" if value > 0 else "-" if value < 0 else "") + text
    u = short_unit(unit)
    if u == "%":
        return {"num": text + "%", "unit": None}
    return {"num": text, "unit": u}


def date_it(iso: str | None) -> str | None:
    """`2026-07-17` -> `17 luglio 2026`."""
    if not iso:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(iso))
    if not m:
        return str(iso)
    y, mo, d = (int(x) for x in m.groups())
    return f"{d} {MONTHS[mo - 1]} {y}"


def ordinal(n: int) -> str:
    return f"{n}ª"


def count_word(n: int, feminine: bool = True) -> str:
    words = {1: "una" if feminine else "uno", 2: "due", 3: "tre", 4: "quattro", 5: "cinque",
             6: "sei", 7: "sette", 8: "otto", 9: "nove", 10: "dieci"}
    return words.get(n, str(n))


def ratio_text(r: float | None) -> str:
    if r is None or not math.isfinite(r):
        return PLACEHOLDER
    return format_number(round(r, 1)) if r < 10 else format_number(r)


# ---------------------------------------------------------------- mappa e classifica

def map_classes(level: dict) -> dict[str, str]:
    """{regione: "q1".."q6"} dalle stesse classi della mappa di oggi."""
    out = {}
    for key, color in (level.get("map_colors") or {}).items():
        m = re.search(r"--seq-(\d)", color)
        if m:
            out[key] = f"q{m.group(1)}"
    return out


def legend(values: list[float], unit: str | None) -> dict:
    """Soglie dei sei gradini a intervalli uguali, come ds_choropleth_colors."""
    lo, hi = min(values), max(values)
    mid = lo + (hi - lo) / 2
    return {"min": num(lo), "mid": num(mid), "max": num(hi), "unit": unit}


def ranking(level: dict, unit: str | None) -> list[dict]:
    """Le righe della classifica, con la riga della media semplice al suo posto."""
    obs = level.get("observations") or []
    avg = (level.get("stats") or {}).get("year_avg")
    bar_max = level.get("bar_max") or max((o["value"] for o in obs), default=0) or 1
    rows = []
    ref_done = avg is None
    descending = len(obs) < 2 or obs[0]["value"] >= obs[-1]["value"]
    for i, o in enumerate(obs, 1):
        crosses = (o["value"] < avg) if descending else (o["value"] > avg) if avg is not None else False
        if not ref_done and crosses:
            rows.append({"ref": True, "label": f"Media semplice delle {len(obs)} {level['plural']}",
                         "value": avg, "width": round(max(avg, 0) / bar_max * 100, 1)})
            ref_done = True
        rows.append({"rank": i, "key": o["key"], "name": o["name"], "value": o["value"],
                     "width": round(max(o["value"], 0) / bar_max * 100, 1)})
    return rows


# ---------------------------------------------------------------- serie storica

def _nice_ticks(lo: float, hi: float, target: int = 4) -> list[float]:
    span = hi - lo or abs(hi) or 1
    raw = span / target
    mag = 10 ** math.floor(math.log10(raw))
    step = min((s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw), default=10 * mag)
    start = math.floor(lo / step) * step
    ticks = []
    t = start
    while t <= hi + step * 0.5:
        ticks.append(round(t, 10))
        t += step
    return ticks


def tick_label(value: float, ticks: list[float]) -> str:
    """Le tacche di un asse con i decimali del passo, non della grandezza: lo
    zero si scrive 0, non 0,00."""
    step = abs(ticks[1] - ticks[0]) if len(ticks) > 1 else 1
    decimals = 0 if step >= 1 else min(2, max(1, -math.floor(math.log10(step))))
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def series_svg(level: dict, unit: str | None) -> dict:
    """La serie in due tagli: largo per lo schermo grande, stretto per il telefono.

    Stesso disegno e stessi dati: cambiano la tela e lo spazio per le etichette,
    cosi' il testo resta a 12-13 pixel veri a ogni larghezza.
    """
    wide = _series_svg(level, 760, 300, right=176, short=False)
    if wide.get("single_year"):
        return wide
    narrow = _series_svg(level, 360, 280, right=104, short=True)
    wide["svg"] = (f'<div class="chart__l">{wide["svg"]}</div>'
                   f'<div class="chart__s">{narrow["svg"]}</div>')
    return wide


def _short_name(name: str) -> str:
    return name if len(name) <= 13 else name[:12].rstrip() + "."


def _series_svg(level: dict, width: int, height: int, right: int, short: bool) -> dict:
    """La serie di tutti i territori in grigio, la media semplice tratteggiata.

    La linea in evidenza e' vuota: la riempie il JavaScript quando il lettore
    sceglie un territorio, copiando i punti della linea grigia corrispondente.
    """
    matrix = level.get("matrix") or {}
    years = sorted(int(y) for y in matrix)
    names = {t["key"]: t["name"] for t in level.get("territories") or []}
    means = {int(p["year"]): p["avg"] for p in level.get("annual_means") or [] if p.get("avg") is not None}
    if len(years) < 2:
        return {"svg": "", "single_year": True}
    values = [v for y in years for v in (matrix[str(y)] or {}).values() if v is not None]
    ticks = _nice_ticks(min(values), max(values))
    left, top, bottom = (48 if short else 64), 14, 30
    plot_w, plot_h = width - left - right, height - top - bottom
    y0, y1 = ticks[0], ticks[-1]

    def x(year):
        return left + (year - years[0]) / (years[-1] - years[0]) * plot_w

    def y(value):
        return top + (1 - (value - y0) / ((y1 - y0) or 1)) * plot_h

    def pts(series):
        return " ".join(f"{x(yr):.1f},{y(v):.1f}" for yr, v in series if v is not None)

    parts = [f'<svg viewBox="0 0 {width} {height}" aria-hidden="true" focusable="false">', '<g class="grid">']
    for t in ticks:
        parts.append(f'<line x1="{left}" x2="{left + plot_w}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>')
    parts.append("</g><g class=\"axis\">")
    for t in ticks:
        parts.append(f'<text x="{left - 8}" y="{y(t) + 4:.1f}" text-anchor="end">{escape(tick_label(t, ticks))}</text>')
    span_years = years[-1] - years[0]
    step = (10 if short else 5) if span_years > 12 else (2 if span_years > 6 else 1)
    marks = [yr for yr in years if (yr - years[0]) % step == 0]
    if years[-1] not in marks:
        if marks and years[-1] - marks[-1] < step / 2:
            marks[-1] = years[-1]
        else:
            marks.append(years[-1])
    for yr in marks:
        anchor = "start" if yr == years[0] else ("end" if yr == years[-1] else "middle")
        parts.append(f'<text x="{x(yr):.1f}" y="{height - 8}" text-anchor="{anchor}">{yr}</text>')
    parts.append("</g><g class=\"ctxlines\">")
    ends = {}
    for key in names:
        series = [(yr, (matrix[str(yr)] or {}).get(key)) for yr in years]
        if sum(v is not None for _, v in series) < 2:
            continue
        parts.append(f'<polyline class="ctx" data-key="{escape(key)}" points="{pts(series)}"/>')
        last = [v for _, v in series if v is not None][-1]
        ends[key] = last
    parts.append("</g>")
    avg_series = [(yr, means.get(yr)) for yr in years]
    parts.append(f'<polyline class="avg" points="{pts(avg_series)}"/>')
    last_avg = [v for _, v in avg_series if v is not None][-1]
    labels = []
    if ends:
        top_key = max(ends, key=ends.get)
        low_key = min(ends, key=ends.get)
        shorten = _short_name if short else (lambda n: n)
        labels.append((y(ends[top_key]), shorten(names[top_key]), "lab"))
        labels.append((y(ends[low_key]), shorten(names[low_key]), "lab"))
    labels.append((y(last_avg), ("Media " if short else "Media semplice ") + num(last_avg), "lab lab--strong"))
    labels.sort()
    placed = []
    for ly, text, cls in labels:
        if placed and ly - placed[-1] < 16:
            ly = placed[-1] + 16
        placed.append(ly)
        parts.append(f'<text class="{cls}" x="{left + plot_w + 8}" y="{ly + 4:.1f}">{escape(text)}</text>')
    parts.append(f'<polyline class="hl" points="" data-hl/><circle class="dot" r="0" cx="0" cy="0" data-hl-dot/>'
                 f'<text class="hl-lab" x="{left + plot_w + 8}" y="-10" data-hl-lab></text>')
    parts.append("</svg>")
    return {"svg": "".join(parts), "single_year": False, "first": years[0], "last": years[-1]}


