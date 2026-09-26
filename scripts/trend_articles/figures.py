"""Fase 5: le figure del pezzo, disegnate dai numeri del dossier.

Ogni figura e' un SVG in `content/figures/<slug>/<nome>.svg` che l'articolo
richiama su una riga sua:

    <!-- figura: classifica-2024 -->

e che `app/blog.py` inserisce nella pagina al render, dentro un `<figure>`.
L'SVG e' in linea, non un `<img>`, per tre ragioni: i colori sono classi CSS
che leggono i token del design system (quindi la figura segue il tema scuro,
e nessun colore e' cotto nel file), i nomi e i valori sono testo che un
motore legge, e lo screen reader trova `<title>` e `<desc>`.

Regole di disegno, le stesse del sito:
- le barre sono neutre (`--cmp-2`), l'accento corallo va solo ai territori
  di cui il testo parla;
- nelle linee le aree si distinguono per colore **e** per tratto e sono
  etichettate in fondo alla linea: la figura si legge anche senza colori;
- titolo, unita', anno e fonte stanno dentro la figura: una figura copiata
  altrove si porta dietro da dove viene;
- niente giudizio nel colore: il corallo evidenzia, non dice "male".

    bin/py -m scripts.trend_articles.figures <slug> bars bes:03LAV007 --title "..." --name classifica-2022
    bin/py -m scripts.trend_articles.figures <slug> extremes prov:03LAV007 --count 10 ...
    bin/py -m scripts.trend_articles.figures <slug> lines ext:bes_areas_03LAV007 --with bes:03LAV007 --territories Umbria ...
    bin/py -m scripts.trend_articles.figures <slug> scatter ext:X --with bes:Y --years-x 2018,2025 --years-y 2018,2025 ...
"""

from __future__ import annotations

import argparse
import re
import statistics
import sys
from html import escape

from app.design.common import _nice_ticks, tick_label
from scripts.trend_articles import common

WIDTH = 680
AREA_CLASSES = {"Nord": "north", "Centro": "centre", "Mezzogiorno": "south", "Italia": "italy"}


def _dossier_entry(slug: str, key: str) -> dict:
    dossier = common.read_json(common.ARTICLES_DIR / slug / "dossier.json")
    for entry in dossier["indicators"]:
        if entry["meta"]["key"] == key:
            return entry
    raise KeyError(f"{key} non e' nel dossier di {slug}: rifai il dossier con quell'indicatore")


def _source_line(meta: dict) -> str:
    """Una riga che entra nella figura: istituzione e archivio, senza il dettaglio.

    La provenienza completa (rilevazione, dataflow, file) sta nel dossier, nel
    CSV scaricabile e nella sezione "Dati usati" del pezzo.
    """
    institution = meta["source"].split(" -")[0].split(",")[0].strip()
    archive = meta["archive"].split(",")[0].replace(" (Bes at local level)", "").strip()
    if archive.startswith("Benessere equo"):
        archive = "Benessere equo e sostenibile"
    return f"Fonte: {institution}, {archive}. Elaborazione Divario Italia."


def _head(title: str, subtitle: str, height: int, description: str) -> list[str]:
    return [
        # @ID@ diventa il nome della figura: due figure nella stessa pagina
        # non devono condividere gli id a cui punta aria-labelledby.
        f'<svg class="fig" viewBox="0 0 {WIDTH} {height}" role="img" aria-labelledby="@ID@-t @ID@-d" xmlns="http://www.w3.org/2000/svg">',
        f'<title id="@ID@-t">{escape(title)}</title>',
        f'<desc id="@ID@-d">{escape(description)}</desc>',
        f'<text class="fig__title" x="0" y="20">{escape(title)}</text>',
        f'<text class="fig__subtitle" x="0" y="40">{escape(subtitle)}</text>',
    ]


def _subtitle(name: str, period: str, unit: str, extra: str = "") -> str:
    """Il sottotitolo sta su una riga: nome corto, periodo, unita' (se non e' gia' nel nome)."""
    name = name.replace(", Italia e ripartizioni", "")
    unit = "" if unit.lower() in name.lower() else f" {unit[:1].upper()}{unit[1:]}."
    text = f"{name}, {period}.{extra}{unit}"
    if len(text) > 105:
        bare = re.sub(r"\s*\([^)]*\)", "", name)
        text = f"{bare}, {period}.{extra}{unit}"
    return text


def _footer(meta: dict, y: int) -> str:
    return f'<text class="fig__source" x="0" y="{y}">{escape(_source_line(meta))}</text>'


def _bars(rows: list[tuple[str, float, str]], highlight: set[str], reference: tuple[str, float] | None,
          title: str, subtitle: str, meta: dict, description: str, gaps: frozenset[int] = frozenset()) -> str:
    step, top, left, right = 22, 60, 190, 60
    height = top + step * len(rows) + 22 * len(gaps) + 50
    scale = (WIDTH - left - right) / (max(v for _, v, _ in rows) or 1)
    parts = _head(title, subtitle, height, description)
    y = top
    for i, (name, value, text) in enumerate(rows):
        if i in gaps:
            parts.append(f'<text class="fig__gap" x="{left}" y="{y + 14}">· · ·</text>')
            y += 22
        on = " is-on" if name in highlight else ""
        w = max(1.0, value * scale)
        parts.append(f'<text class="fig__name{on}" x="{left - 8}" y="{y + 14}" text-anchor="end">{escape(name)}</text>')
        parts.append(f'<rect class="fig__bar{on}" x="{left}" y="{y + 3}" width="{w:.1f}" height="{step - 7}"/>')
        parts.append(f'<text class="fig__value{on}" x="{left + w + 6:.1f}" y="{y + 14}">{escape(text)}</text>')
        y += step
    if reference:
        label, value = reference
        x = left + value * scale
        parts.append(f'<line class="fig__ref" x1="{x:.1f}" y1="{top - 4}" x2="{x:.1f}" y2="{y}"/>')
        parts.append(f'<text class="fig__ref-label" x="{x + 4:.1f}" y="{y + 14}">{escape(label)}</text>')
    parts.append(_footer(meta, height - 6))
    parts.append("</svg>")
    return "\n".join(parts)


def _reference(slug: str, entry: dict, year, decimals: int, reference_key: str | None) -> tuple[str, float]:
    """La linea di riferimento: il valore Italia ufficiale se c'e', se no la media semplice dichiarata."""
    if reference_key:
        value = _dossier_entry(slug, reference_key)["series"].get("Italia", {}).get(str(year))
        if value is not None:
            return (f"Italia {common.fmt(value, decimals)}", value)
    mean = entry["means"][str(year)]["simple_mean"]
    return (f"media semplice {common.fmt(mean, decimals + 1)}", mean)


def _sorted_year(entry: dict, year) -> list[tuple[str, float]]:
    return sorted(((t, per[str(year)]) for t, per in entry["series"].items() if str(year) in per), key=lambda kv: -kv[1])


def bars(slug, key, highlight, title, year=None, reference_key=None):
    entry = _dossier_entry(slug, key)
    meta = entry["meta"]
    year = year or entry["last_year"]
    decimals = meta["decimals"]
    ordered = _sorted_year(entry, year)
    if ordered and ordered[0][1] >= 100:
        decimals = 0  # sopra 100 i decimali sono rumore, come nel dossier
    data = [(t, v, common.fmt(v, decimals)) for t, v in ordered]
    subtitle = _subtitle(meta["name"], str(year), meta["unit"])
    description = f"Classifica di {len(data)} territori nel {year}: primo {data[0][0]} con {data[0][2]}, ultimo {data[-1][0]} con {data[-1][2]}."
    return _bars(data, set(highlight), _reference(slug, entry, year, decimals, reference_key), title, subtitle, meta, description)


def extremes(slug, key, count, highlight, title, year=None, reference_key=None):
    entry = _dossier_entry(slug, key)
    meta = entry["meta"]
    year = year or entry["last_year"]
    decimals = meta["decimals"]
    ordered = _sorted_year(entry, year)
    data = [(t, v, common.fmt(v, decimals)) for t, v in ordered[:count] + ordered[-count:]]
    subtitle = _subtitle(meta["name"], str(year), meta["unit"], f" Le {count} province più alte e le {count} più basse su {len(ordered)}.")
    description = (f"Le {count} province con il valore più alto e le {count} con il più basso nel {year}: "
                   f"prima {data[0][0]} con {data[0][2]}, ultima {data[-1][0]} con {data[-1][2]}.")
    return _bars(data, set(highlight), _reference(slug, entry, year, decimals, reference_key), title, subtitle, meta,
                 description, frozenset({count}))


def lines(slug, key, territories, title, simple_areas=True, with_key=None):
    """Serie nel tempo.

    Se `key` e' un'elaborazione di ripartizioni ufficiali (ext:bes_areas_*),
    le linee sono Nord, Centro, Mezzogiorno e Italia come le calcola l'Istat, e
    `territories` si prendono da `with_key` (l'indicatore regionale). Altrimenti
    si disegnano le medie semplici di Centro-Nord e Mezzogiorno, dichiarate tali.
    """
    entry = _dossier_entry(slug, key)
    meta = entry["meta"]
    decimals = meta["decimals"]
    official = meta["level"] == "ripartizione"
    drawn: list[tuple[str, str, dict[int, float]]] = []
    if official:
        for area, css in AREA_CLASSES.items():
            if area in entry["series"]:
                drawn.append((area, css, {int(y): v for y, v in entry["series"][area].items()}))
        territory_source = _dossier_entry(slug, with_key) if with_key else entry
    else:
        if simple_areas:
            drawn.append(("Centro-Nord", "cn", {int(y): m["mean_centro_nord"] for y, m in entry["means"].items() if "mean_centro_nord" in m}))
            drawn.append(("Mezzogiorno", "south", {int(y): m["mean_mezzogiorno"] for y, m in entry["means"].items() if "mean_mezzogiorno" in m}))
        territory_source = entry
    for t in territories:
        drawn.append((t, "on", {int(y): v for y, v in territory_source["series"][t].items()}))
    years = sorted({y for _, _, s in drawn for y in s})
    simple_areas = simple_areas and not official

    top, bottom, left, right = 60, 70, 48, 150
    height = 360
    every = [v for _, _, s in drawn for v in s.values()]
    lo, hi = min(every), max(every)
    margin = (hi - lo) * 0.08 or 1
    lo, hi = max(0, lo - margin), hi + margin
    # Tacche tonde (5, 10, 15), e il disegno va da una all'altra: dividere in
    # quarti il dominio grezzo scriveva 9,2 / 10,6 / 12,1 sull'asse.
    y_ticks = _nice_ticks(lo, hi)
    lo, hi = y_ticks[0], y_ticks[-1]

    def x(year):
        return left + (year - years[0]) / max(1, years[-1] - years[0]) * (WIDTH - left - right)

    def y(value):
        return height - bottom - (value - lo) / (hi - lo) * (height - top - bottom)

    subtitle = _subtitle(meta["name"], f"{years[0]}-{years[-1]}", meta["unit"])
    description = "; ".join(
        f"{name}: da {common.fmt(s[min(s)], decimals)} nel {min(s)} a {common.fmt(s[max(s)], decimals)} nel {max(s)}"
        for name, _, s in drawn if s
    )
    parts = _head(title, subtitle, height, description)
    for v in y_ticks:
        parts.append(f'<line class="fig__grid" x1="{left}" y1="{y(v):.1f}" x2="{WIDTH - right}" y2="{y(v):.1f}"/>')
        parts.append(f'<text class="fig__axis" x="{left - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{escape(tick_label(v, y_ticks))}</text>')
    for year in years:
        if len(years) <= 12 or year % 2 == years[-1] % 2:
            parts.append(f'<text class="fig__axis" x="{x(year):.1f}" y="{height - bottom + 18}" text-anchor="middle">{year}</text>')
    labels = []
    for name, css, s in drawn:
        points = " ".join(f"{x(yr):.1f},{y(v):.1f}" for yr, v in sorted(s.items()))
        parts.append(f'<polyline class="fig__line fig__line--{css}" points="{points}"/>')
        last = max(s)
        parts.append(f'<circle class="fig__dot fig__dot--{css}" cx="{x(last):.1f}" cy="{y(s[last]):.1f}" r="3.5"/>')
        # le medie semplici portano un decimale in piu' dei dati, come nel dossier
        digits = decimals + 1 if css in ("cn", "south") and not official else decimals
        labels.append([y(s[last]), f"{name} {common.fmt(s[last], digits)}", css, x(last)])
    labels.sort()
    for i in range(1, len(labels)):  # le etichette non si sovrappongono
        labels[i][0] = max(labels[i][0], labels[i - 1][0] + 14)
    for yy, text, css, xx in labels:
        parts.append(f'<text class="fig__label fig__label--{css}" x="{xx + 8:.1f}" y="{yy + 4:.1f}">{escape(text)}</text>')
    if simple_areas:
        parts.append(f'<text class="fig__note" x="0" y="{height - 26}">Centro-Nord e Mezzogiorno: medie semplici dei territori, non pesate per popolazione.</text>')
    elif official:
        parts.append(f'<text class="fig__note" x="0" y="{height - 26}">Italia, Nord, Centro e Mezzogiorno: valori calcolati dall\'Istat.</text>')
    parts.append(_footer(meta, height - 6))
    parts.append("</svg>")
    return "\n".join(parts)


def scatter(slug, key_x, key_y, years_x, years_y, highlight, title, name_x, name_y, subtitle=None):
    """Un territorio per punto: un indicatore contro un altro.

    Due anni: la variazione fra i due. Un anno solo: il livello. Serve a
    mettere alla prova un'ipotesi ("dove e' cresciuto X e' peggiorato Y?"),
    non a dimostrarla: i punti sono territori, non persone. Mezzogiorno e
    Centro-Nord hanno due forme diverse, e le correlazioni si salvano anche
    dentro ciascun gruppo in `data/articles/<slug>/link_<x>_<y>.json`: un
    legame che esiste solo fra Nord e Sud puo' dipendere da qualunque cosa
    distingua le due aree.
    """
    ex, ey = _dossier_entry(slug, key_x), _dossier_entry(slug, key_y)

    def value(s, years):
        return s[str(years[1])] - s[str(years[0])] if len(years) == 2 else s[str(years[0])]

    points = []
    for t in sorted(set(ex["series"]) & set(ey["series"])):
        sx, sy = ex["series"][t], ey["series"][t]
        if all(str(yr) in sx for yr in years_x) and all(str(yr) in sy for yr in years_y):
            points.append((t, value(sx, years_x), value(sy, years_y)))

    provinces = common.province_regions()
    group = {t: common.macro_area(t, "provincia" if t in provinces else "regione") for t, _, _ in points}
    links = {}
    for label, chosen in (("tutti", points), ("Centro-Nord", [p for p in points if group[p[0]] == "Centro-Nord"]),
                          ("Mezzogiorno", [p for p in points if group[p[0]] == "Mezzogiorno"])):
        if len(chosen) >= 4:
            links[label] = {"points": len(chosen),
                            "correlation": round(statistics.correlation([p[1] for p in chosen], [p[2] for p in chosen]), 2)}
    common.write_json(common.ARTICLES_DIR / slug / f"link_{key_x.split(':')[1]}_{key_y.split(':')[1]}.json", {
        "x": key_x, "y": key_y, "years_x": years_x, "years_y": years_y, "links": links,
        "note": "Correlazione di Pearson fra territori. Misura se due grandezze si muovono insieme, non una causa.",
    })
    print("legami:", links)

    top, bottom, left, right = 60, 86, 56, 24
    height = 440
    xs, ys = [p[1] for p in points], [p[2] for p in points]
    changes = len(years_x) == 2
    # Con le variazioni lo zero deve stare nel disegno: separa chi e' salito da chi e' sceso.
    x0, x1 = (min([*xs, 0]) if changes else min(xs)), max(xs)
    y0, y1 = (min([*ys, 0]) if len(years_y) == 2 else min(ys)), max(ys)
    mx, my = (x1 - x0) * 0.08, (y1 - y0) * 0.08
    x0, x1, y0, y1 = x0 - mx, x1 + mx, y0 - my, y1 + my
    x_ticks, y_ticks = _nice_ticks(x0, x1), _nice_ticks(y0, y1)
    x0, x1, y0, y1 = x_ticks[0], x_ticks[-1], y_ticks[0], y_ticks[-1]

    def px(v):
        return left + (v - x0) / (x1 - x0) * (WIDTH - left - right)

    def py(v):
        return height - bottom - (v - y0) / (y1 - y0) * (height - top - bottom)

    if not subtitle:
        if not changes:
            subtitle = "Una regione per punto."
        elif years_x == years_y:
            subtitle = f"Variazione {years_x[0]}-{years_x[1]}, in punti percentuali."
        else:
            subtitle = f"Variazione {years_x[0]}-{years_x[1]} e {years_y[0]}-{years_y[1]}, in punti percentuali."
    description = "; ".join(f"{t}: {common.fmt(dx, 1)} e {common.fmt(dy, 1)}" for t, dx, dy in points)
    parts = _head(title, subtitle, height, description)
    if x0 < 0 < x1:
        parts.append(f'<line class="fig__grid" x1="{px(0):.1f}" y1="{top}" x2="{px(0):.1f}" y2="{height - bottom}"/>')
    if y0 < 0 < y1:
        parts.append(f'<line class="fig__grid" x1="{left}" y1="{py(0):.1f}" x2="{WIDTH - right}" y2="{py(0):.1f}"/>')
    for v in x_ticks:
        parts.append(f'<text class="fig__axis" x="{px(v):.1f}" y="{height - bottom + 16}" text-anchor="middle">{escape(tick_label(v, x_ticks))}</text>')
    for w in y_ticks:
        parts.append(f'<text class="fig__axis" x="{left - 6}" y="{py(w) + 4:.1f}" text-anchor="end">{escape(tick_label(w, y_ticks))}</text>')
    parts.append(f'<text class="fig__axis-name" x="{WIDTH - right}" y="{height - bottom + 34}" text-anchor="end">{escape(name_x)} →</text>')
    parts.append(f'<text class="fig__axis-name" x="{left}" y="{top - 8}">↑ {escape(name_y)}</text>')
    name_all = len(points) <= 25  # con 100 province si nominano solo quelle di cui il testo parla
    labels = []
    for t, dx, dy in points:
        on = " is-on" if t in highlight else ""
        if group[t] == "Mezzogiorno":
            parts.append(f'<rect class="fig__pt fig__pt--south{on}" x="{px(dx) - 4:.1f}" y="{py(dy) - 4:.1f}" width="8" height="8"/>')
        else:
            parts.append(f'<circle class="fig__pt fig__pt--cn{on}" cx="{px(dx):.1f}" cy="{py(dy):.1f}" r="4.5"/>')
        if name_all or on:
            to_right = px(dx) < WIDTH - 140
            width = 6.2 * len(t)
            x_text = px(dx) + (7 if to_right else -7)
            labels.append([py(dy) + 4, x_text if to_right else x_text - width, width, x_text, to_right, on, t])
    # Le etichette che si toccano scivolano in basso di una riga, una dopo l'altra.
    labels.sort()
    placed: list[list] = []
    for lab in labels:
        while any(abs(lab[0] - p[0]) < 12 and lab[1] < p[1] + p[2] and p[1] < lab[1] + lab[2] for p in placed):
            lab[0] += 12
        placed.append(lab)
        yy, _, _, x_text, to_right, on, t = lab
        anchor = "" if to_right else ' text-anchor="end"'
        parts.append(f'<text class="fig__pt-name{on}" x="{x_text:.1f}" y="{yy:.1f}"{anchor}>{escape(t)}</text>')
    unit = "Una regione" if name_all else "Una provincia"
    lit = " In evidenza quelle di cui parla il testo." if highlight else ""
    parts.append(f'<text class="fig__note" x="0" y="{height - 26}">{unit} per punto. Cerchi: Centro-Nord. Quadrati: Mezzogiorno.{lit}</text>')
    institutions = []
    for m in (ex["meta"], ey["meta"]):
        name = m["source"].split(" -")[0].split(",")[0].strip()
        if name not in institutions:
            institutions.append(name)
    parts.append(f'<text class="fig__source" x="0" y="{height - 6}">{escape("Fonte: " + " e ".join(institutions) + ". Elaborazione Divario Italia.")}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("slug")
    parser.add_argument("kind", choices=["bars", "extremes", "lines", "scatter"])
    parser.add_argument("indicator")
    parser.add_argument("--title", required=True, help="il titolo dice la notizia, non il nome dell'indicatore")
    parser.add_argument("--name", required=True, help="nome del file, e del marcatore nell'articolo")
    parser.add_argument("--with", dest="with_key", help="lines: indicatore regionale per --territories; scatter: indicatore sull'asse y")
    parser.add_argument("--years-x", help="scatter: uno o due anni, es. 2018,2025")
    parser.add_argument("--years-y", help="scatter: uno o due anni, es. 2018,2025")
    parser.add_argument("--name-x", default="")
    parser.add_argument("--name-y", default="")
    parser.add_argument("--subtitle")
    parser.add_argument("--reference", help="bars/extremes: ext:bes_areas_* da cui prendere il valore Italia")
    parser.add_argument("--highlight", default="")
    parser.add_argument("--territories", default="")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--year", type=int)
    parser.add_argument("--no-simple-areas", action="store_true")
    args = parser.parse_args(argv)

    def split(text):
        return [p.strip() for p in (text or "").split(",") if p.strip()]

    if args.kind == "bars":
        svg = bars(args.slug, args.indicator, split(args.highlight), args.title, args.year, args.reference)
    elif args.kind == "extremes":
        svg = extremes(args.slug, args.indicator, args.count, split(args.highlight), args.title, args.year, args.reference)
    elif args.kind == "scatter":
        svg = scatter(args.slug, args.indicator, args.with_key, [int(y) for y in split(args.years_x)],
                      [int(y) for y in split(args.years_y)], set(split(args.highlight)), args.title,
                      args.name_x, args.name_y, args.subtitle)
    else:
        svg = lines(args.slug, args.indicator, split(args.territories), args.title, not args.no_simple_areas, args.with_key)

    out = common.FIGURES_DIR / args.slug / f"{args.name}.svg"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg.replace("@ID@", f"fig-{args.name}") + "\n", encoding="utf-8")
    print(f"-> {out.relative_to(common.ROOT)}   marcatore: <!-- figura: {args.name} -->")
    return 0


if __name__ == "__main__":
    sys.exit(main())
