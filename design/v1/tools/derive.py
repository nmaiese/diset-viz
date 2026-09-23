"""Le frasi e le cifre nuove dei prototipi, composte dai dati veri.

Ogni funzione prende il contesto catturato da `extract.py` e restituisce cio' che
il template della 1.0 chiede in piu' rispetto a quello di oggi: tessere,
titoli-affermazione dei grafici, righe della classifica, classi della mappa,
la serie storica disegnata. I numeri passano da `seo_titles.format_number`, la
stessa funzione dei title, cosi' una cifra si scrive in un modo solo.

Una cifra che non si puo' calcolare non si inventa: diventa `PLACEHOLDER`, che
la pagina mostra cosi' com'e' e che `check_pages.py` elenca.
"""

from __future__ import annotations

import math
import re
from html import escape

from app.data import REGION_GEO_AREA
from app.seo_titles import format_number, of_region

PLACEHOLDER = "[dato da calcolare]"
MEZZOGIORNO = {key for key, area in REGION_GEO_AREA.items() if area in ("Sud", "Isole")}
LOWER_BETTER = ("lower_better", "higher_worse")
MONTHS = ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
          "agosto", "settembre", "ottobre", "novembre", "dicembre")


def num(value) -> str:
    """La cifra all'italiana con i decimali calibrati sulla grandezza."""
    text = format_number(value)
    return text if text is not None else PLACEHOLDER


def short_unit(unit: str | None) -> str | None:
    """L'unita' come si scrive accanto a una cifra.

    "euro" resta "euro", "Numero medio di anni" diventa "anni", "Per 10.000
    occupati" diventa "per 10.000 occupati", che accanto a "12,4" si legge. Le
    unita' piu' lunghe non si accorciano a occhio: restano nel sottotitolo.
    """
    unit = (unit or "").strip()
    if not unit:
        return None
    if unit == "%" or unit.startswith("%"):
        return "%"
    m = re.match(r"(?i)numero medio di (.+)", unit)
    if m:
        return m.group(1)
    lowered = unit[:1].lower() + unit[1:]
    if lowered.startswith("per "):
        return lowered
    if len(unit) <= 14:
        return unit
    if len(unit) <= 24:
        return lowered
    return None


def of_place(name: str, level_key: str) -> str:
    """"della Basilicata", "del Piemonte" per le regioni, "di Milano" per le province."""
    if level_key == "regione":
        return of_region(name)
    if name.startswith("L'"):
        return f"dell'{name[2:]}"
    if name.startswith("La "):
        return f"della {name[3:]}"
    return f"di {name}"


def the_place(name: str, level_key: str) -> str:
    """"il Trentino Alto Adige", "la Calabria", "l'Umbria" per le regioni, il nome nudo per le province."""
    if level_key != "regione":
        return name
    of = of_region(name)
    return {"del ": "il ", "dell'": "l'", "della ": "la ", "delle ": "le "}.get(
        next(p for p in ("delle ", "della ", "dell'", "del ") if of.startswith(p)), "") + name


def del_(text: str) -> str:
    """"del 3,6%" ma "dell'11,3%" e "dell'8%": l'articolo davanti a una cifra si
    elide quando la cifra si legge con una vocale."""
    return "dell'" if re.match(r"(8|11)|1(?![\d.])", text) else "del "


def with_unit(value, unit: str | None) -> str:
    """`54.637 euro`, `78,8%`: l'unita' corta accanto alla cifra, spazio insecabile."""
    text = num(value)
    u = short_unit(unit)
    if u == "%":
        return f"{text}%"
    return f"{text} {u}" if u else text


def signed(value, unit: str | None) -> str:
    if value is None:
        return PLACEHOLDER
    sign = "+" if value > 0 else ("-" if value < 0 else "")
    return sign + with_unit(abs(value), unit)


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
                         "value": num(avg), "width": round(max(avg, 0) / bar_max * 100, 1)})
            ref_done = True
        rows.append({"rank": i, "key": o["key"], "name": o["name"], "value": num(o["value"]),
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


# ---------------------------------------------------------------- scheda indicatore

def indicator(ctx: dict) -> dict:
    meta, level = ctx["meta"], ctx["level"]
    stats = level.get("stats") or {}
    annual = level.get("annual_change") or None
    unit = meta.get("value_unit") or meta.get("unit")
    change_unit = meta.get("change_unit") or unit
    plural, n = level["plural"], len(level.get("observations") or [])
    lede = ctx.get("page_lead") or ""
    best, worst = level.get("best"), level.get("worst")
    year = level.get("year_max")

    tiles = []
    if best and best["name"] not in lede:
        tiles.append({"label": f"In testa nel {year}", **figure(best["value"], unit),
                      "sub": best["name"], "href": (level.get("profile_path") or "") + best["key"] if level.get("profile_path") else None})
    if worst and worst["name"] not in lede:
        tiles.append({"label": f"In coda nel {year}", **figure(worst["value"], unit),
                      "sub": worst["name"], "href": (level.get("profile_path") or "") + worst["key"] if level.get("profile_path") else None})
    if stats.get("year_avg") is not None:
        tiles.append({"label": f"Media semplice delle {stats.get('year_count', n)} {plural}", **figure(stats["year_avg"], unit),
                      "sub": "non pesata per popolazione"})
    if stats.get("gap_ratio"):
        tiles.append({"label": "Fra prima e ultima", "num": ratio_text(stats["gap_ratio"]), "unit": "volte",
                      "sub": f"una distanza di {with_unit(stats['gap_abs'], unit)}"})
    if annual:
        more, less = annual.get("increase_count", 0), annual.get("decrease_count", 0)
        trend = f"in aumento in {more} {plural} su {annual['common_count']}" if more >= less else f"in calo in {less} {plural} su {annual['common_count']}"
        tiles.append({"label": f"Dal {annual['previous_year']} al {annual['year']}", **figure(annual["average_delta"], change_unit, sign=True),
                      "sub": f"di media semplice, {trend}"})
    tiles = tiles[:4]

    direction = meta.get("direction")
    verso = {"higher_better": "Meglio se alto", "lower_better": "Meglio se basso", "higher_worse": "Meglio se basso"}.get(direction, "Senza un verso")

    # Il titolo-affermazione della classifica: un fatto verificato sul Mezzogiorno.
    claim = None
    if level["key"] == "regione" and stats.get("year_avg") is not None:
        south = [o for o in level["observations"] if o["key"] in MEZZOGIORNO]
        below = [o for o in south if o["value"] < stats["year_avg"]]
        if south and len(below) == len(south):
            claim = f"Nel {year} tutte le {count_word(len(south))} regioni del Mezzogiorno stanno sotto la media semplice"
        elif south and not below:
            claim = f"Nel {year} tutte le {count_word(len(south))} regioni del Mezzogiorno stanno sopra la media semplice"
        elif south:
            claim = f"Nel {year} {count_word(len(below))} regioni del Mezzogiorno su {count_word(len(south))} stanno sotto la media semplice"
    if claim is None and stats.get("above_avg_count") is not None:
        claim = f"Nel {year} {stats['above_avg_count']} {plural} stanno sopra la media semplice e {stats['below_avg_count']} sotto"

    series = series_svg(level, unit)
    series_claim = None
    if stats.get("has_multi_year") and stats.get("avg_change_pct") is not None:
        r = 1 + stats["avg_change_pct"] / 100
        if r >= 3:
            what = "più che triplicata"
        elif r >= 2:
            what = "più che raddoppiata"
        elif stats["avg_change_pct"] > 0:
            pct = num(stats["avg_change_pct"]) + "%"
            what = f"cresciuta {del_(pct)}{pct}"
        else:
            pct = num(abs(stats["avg_change_pct"])) + "%"
            what = f"scesa {del_(pct)}{pct}"
        gap = stats.get("gap_trend")
        gap_text = ""
        if gap is not None and stats.get("year_min_gap_abs"):
            if abs(gap) < 0.01 * abs(stats["year_min_gap_abs"]):
                gap_text = ", e la distanza fra prima e ultima è rimasta la stessa"
            elif gap > 0:
                gap_text = f", e la distanza fra prima e ultima è cresciuta di {with_unit(gap, change_unit)}"
            else:
                gap_text = f", e la distanza fra prima e ultima si è ridotta di {with_unit(abs(gap), change_unit)}"
        series_claim = f"Dal {stats['year_min']} al {stats['year_max']} la media semplice è {what}{gap_text}"
    series_note = None
    hd, ld = stats.get("highest_delta"), stats.get("lowest_delta")
    lk = level["key"]
    if hd and ld and hd.get("kind") == "aumento" and ld.get("kind") == "aumento":
        series_note = (f"Su tutto il periodo cresce di più {the_place(hd['name'], lk)} ({signed(hd['delta'], change_unit)}), "
                       f"di meno {the_place(ld['name'], lk)} ({signed(ld['delta'], change_unit)}).")
    elif hd and ld:
        series_note = (f"Su tutto il periodo la variazione va da {signed(ld['delta'], change_unit)} {of_place(ld['name'], lk)} "
                       f"a {signed(hd['delta'], change_unit)} {of_place(hd['name'], lk)}.")

    values = [o["value"] for o in level.get("observations") or [] if o.get("value") is not None]
    explore_js = {
        "years": [int(y) for y in sorted(level.get("matrix") or {}, key=int)],
        "matrix": level.get("matrix") or {},
        "names": {t["key"]: t["name"] for t in level.get("territories") or []},
        "unit": short_unit(unit), "direction": direction, "plural": plural,
        "profile": level.get("profile_path"), "south": sorted(MEZZOGIORNO) if level["key"] == "regione" else [],
    }
    citation = (f"Divario Italia, «{meta['name']}», elaborazione su dati {meta.get('source_label') or meta.get('source')} "
                f"({year}). {ctx.get('canonical')}")
    return {
        "fmt": num, "fmt_unit": with_unit, "date_it": date_it, "citation": citation,
        "map_values": {o["key"]: with_unit(o["value"], unit) for o in level.get("observations") or []},
        "unit": unit, "short_unit": short_unit(unit), "tiles": tiles, "verso": verso,
        "claim": claim, "map_classes": map_classes(level),
        "legend": legend(values, unit) if values else None,
        "ranking": ranking(level, unit), "series": series, "series_claim": series_claim, "series_note": series_note,
        "updated": date_it(ctx.get("dataset_updated")), "explore_js": explore_js,
        "subtitle": f"{meta['name']}, {('in ' + unit) if unit else ''}, {year}. {n} {plural} dal valore più alto al più basso.".replace(", ,", ","),
    }
