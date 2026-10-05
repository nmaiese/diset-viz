"""Le tre figure del pezzo sul numero medio di figli per donna.

Il pezzo segue ter-922 sulle venti regioni, 2002-2025. Nessun dossier: i valori
si leggono dal sito, `figures.py` non ha una forma per un conteggio per anno ne'
per un grafico a manubrio. Le figure hanno le classi `fig__*` di `site.css` e
`articolo.css` e un viewBox stretto (370), cosi' a 375 px il testo resta sopra
gli 11 px.

    bin/py scripts/trend_articles/figure_figli_per_donna.py
"""
from __future__ import annotations

import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app import data  # noqa: E402

SLUG = "figli-per-donna-regioni-italia"
OUT = ROOT / "content" / "figures" / SLUG
W = 370
SOGLIA = 1.30
SOURCE = ("Fonte: Istat, Indicatori demografici, tasso di", "fecondità totale. 2025 stimato. Elaborazione Divario Italia.")
BARS_ON = {2002, 2008, 2010, 2020, 2025}
DUMB_ON = {"Valle d'Aosta", "Lombardia", "Lazio", "Emilia-Romagna", "Basilicata", "Calabria", "Sicilia", "Campania", "Sardegna"}
MINUS = "−"


def source_lines(height: int) -> list[str]:
    return [f'<text class="fig__source" x="0" y="{height - 20 + 14 * i}">{escape(t)}</text>' for i, t in enumerate(SOURCE)]


def it(x: float, dec: int = 2) -> str:
    return f"{x:.{dec}f}".replace(".", ",")


def series() -> dict[str, dict[int, float]]:
    out: dict[str, dict[int, float]] = {}
    for r in data.get_indicator("922")["series"]:
        out.setdefault(r["region"], {})[r["year"]] = r["value"]
    return out


def head(fid: str, height: int, title_lines: list[str], sub_lines: list[str], title: str, desc: str) -> tuple[list[str], int]:
    parts = [
        f'<svg class="fig fig--narrow" viewBox="0 0 {W} {height}" width="{W}" height="{height}" role="img" aria-labelledby="{fid}-t {fid}-d" xmlns="http://www.w3.org/2000/svg">',
        f'<title id="{fid}-t">{escape(title)}</title>',
        f'<desc id="{fid}-d">{escape(desc)}</desc>',
    ]
    y = 18
    for line in title_lines:
        parts.append(f'<text class="fig__title" x="0" y="{y}">{escape(line)}</text>')
        y += 19
    y += 1
    for line in sub_lines:
        parts.append(f'<text class="fig__subtitle" x="0" y="{y}">{escape(line)}</text>')
        y += 15
    return parts, y


def counts(s) -> dict[int, int]:
    years = sorted({y for t in s for y in s[t]})
    # soglia inclusiva: la Calabria vale esattamente 1,30 nel 2012, nel 2014 e nel 2017
    return {y: sum(1 for t in s if s[t].get(y, 0) >= SOGLIA - 1e-9) for y in years}


def bars_figure(s) -> str:
    c = counts(s)
    assert (c[2002], c[2008], c[2010], c[2020], c[2025]) == (4, 16, 17, 3, 1), c
    title = "Da 17 regioni a 1,3 figli per donna o più nel 2010 a una sola nel 2025"
    desc = (f"Numero di regioni con almeno 1,30 figli per donna, anno per anno dal 2002 al 2025. "
            f"Quattro nel 2002, sedici nel 2008, diciassette nel 2010, tre nel 2020, una nel 2025, il Trentino Alto Adige. "
            f"Il 2025 è una stima.")
    top, step = 76, 17
    n = len(c)
    height = top + step * n + 70
    xl, xmax, vmax = 44, 300, 17
    parts, _ = head("fig-regioni-sopra-1-3", height,
                    ["Da 17 regioni a 1,3 figli per donna o più", "nel 2010 a una sola nel 2025"],
                    ["Regioni con almeno 1,30 figli per donna, su 20,", "per anno. 2002-2025."],
                    title, desc)
    for i, (yr, v) in enumerate(c.items()):
        y0 = top + i * step
        on = " is-on" if yr in BARS_ON else ""
        w = v / vmax * (xmax - xl)
        parts.append(f'<text class="fig__name{on}" x="{xl - 8}" y="{y0 + 12}" text-anchor="end">{yr}</text>')
        parts.append(f'<rect class="fig__bar{on}" x="{xl}" y="{y0 + 2}" width="{w:.1f}" height="{step - 5}"/>')
        parts.append(f'<text class="fig__value{on}" x="{xl + w + 6:.1f}" y="{y0 + 12}">{v}</text>')
    parts.append(f'<text class="fig__note" x="0" y="{height - 52}">In evidenza 2002, 2008, 2010, 2020 e 2025.</text>')
    parts.append(f'<text class="fig__note" x="0" y="{height - 38}">Il 2025 è una stima provvisoria.</text>')
    parts += source_lines(height)
    parts.append("</svg>")
    return "\n".join(parts)


def dumbbell_figure(s) -> str:
    rows = sorted(((t, s[t][2010], s[t][2025], round(s[t][2025] - s[t][2010], 2)) for t in s), key=lambda r: (r[3], r[0]))
    first, last = rows[0], rows[-1]
    assert first[0] == "Valle d'Aosta" and last[0] == "Basilicata", (first, last)
    title = "Dal 2010 al 2025 il calo va da 0,50 figli per donna in Valle d'Aosta a 0,12 in Basilicata"
    desc = (f"Numero medio di figli per donna nel 2010 e nel 2025 in ciascuna regione, ordinate dal calo maggiore al minore. "
            f"Valle d'Aosta da {it(first[1])} a {it(first[2])}, Lombardia da {it(s['Lombardia'][2010])} a {it(s['Lombardia'][2025])}, "
            f"Lazio da {it(s['Lazio'][2010])} a {it(s['Lazio'][2025])}, Sicilia da {it(s['Sicilia'][2010])} a {it(s['Sicilia'][2025])}, "
            f"Campania da {it(s['Campania'][2010])} a {it(s['Campania'][2025])}, Sardegna da {it(s['Sardegna'][2010])} a {it(s['Sardegna'][2025])}, "
            f"Basilicata da {it(last[1])} a {it(last[2])}. Il valore scende in tutte e venti le regioni. Il 2025 è una stima.")
    top, step = 100, 22
    height = top + step * len(rows) + 68
    xn = 126                     # fine dei nomi
    lo, hi, x0, x1 = 0.6, 1.7, 142, 292

    def x(v):
        return x0 + (v - lo) / (hi - lo) * (x1 - x0)

    parts, _ = head("fig-variazione-2010-2025", height,
                    ["Dal 2010 al 2025 il calo va da 0,50 figli", "per donna in Valle d'Aosta a 0,12 in Basilicata"],
                    ["Figli per donna per regione, dal calo maggiore", "al minore. Cerchio vuoto 2010, pieno 2025."],
                    title, desc)
    parts.append(f'<text class="fig__axis-name" x="{W}" y="{top - 8}" text-anchor="end">Variazione</text>')
    for v in (0.8, 1.0, 1.2, 1.4, 1.6):
        parts.append(f'<line class="fig__grid" x1="{x(v):.1f}" y1="{top - 2}" x2="{x(v):.1f}" y2="{top + step * len(rows) - 4}"/>')
        parts.append(f'<text class="fig__axis" x="{x(v):.1f}" y="{top + step * len(rows) + 12}" text-anchor="middle">{it(v, 1)}</text>')
    order = sorted(range(len(rows)), key=lambda i: rows[i][0] in DUMB_ON)  # le evidenziate disegnate per ultime
    for i in order:
        t, a, b, d = rows[i]
        cy = top + i * step + 9
        on = " is-on" if t in DUMB_ON else ""
        parts.append(f'<text class="fig__name{on}" x="{xn}" y="{cy + 4}" text-anchor="end">{escape(t)}</text>')
        parts.append(f'<line class="fig__dumb{on}" x1="{x(b):.1f}" y1="{cy}" x2="{x(a):.1f}" y2="{cy}"/>')
        parts.append(f'<circle class="fig__pt-dot fig__pt-dot--old{on}" cx="{x(a):.1f}" cy="{cy}" r="3.5"/>')
        parts.append(f'<circle class="fig__pt-dot{on}" cx="{x(b):.1f}" cy="{cy}" r="3.5"/>')
        if on:
            parts.append(f'<text class="fig__value is-on" x="{x(b) - 8:.1f}" y="{cy + 4}" text-anchor="end">{it(b)}</text>')
            parts.append(f'<text class="fig__value is-on" x="{x(a) + 8:.1f}" y="{cy + 4}">{it(a)}</text>')
        parts.append(f'<text class="fig__value{on}" x="{W}" y="{cy + 4}" text-anchor="end">{MINUS}{it(-d)}</text>')
    parts.append(f'<text class="fig__note" x="0" y="{height - 38}">L\'asse parte da 0,6, non da zero.</text>')
    parts += source_lines(height)
    parts.append("</svg>")
    return "\n".join(parts)


def four_figure(s) -> str:
    keys = ["Trentino Alto Adige", "Sicilia", "Campania", "Sardegna"]
    names = {"Trentino Alto Adige": "Trentino-Alto Adige"}
    rows = [(names.get(k, k), s[k][2010], s[k][2025], round(s[k][2025] - s[k][2010], 2)) for k in keys]
    assert [(it(r[1]), it(r[2])) for r in rows] == [("1,63", "1,40"), ("1,42", "1,23"), ("1,44", "1,22"), ("1,18", "0,85")], rows
    title = "Dal 2010 al 2025 la Sardegna scende da 1,18 a 0,85 figli per donna, il Trentino-Alto Adige da 1,63 a 1,40"
    desc = ("Numero medio di figli per donna nel 2010 e nel 2025 in quattro regioni. "
            + " ".join(f"{n} da {it(a)} a {it(b)}." for n, a, b, _ in rows)
            + " Il 2025 è una stima.")
    top, step = 100, 30
    height = top + step * len(rows) + 68
    xn = 126
    lo, hi, x0, x1 = 0.6, 1.7, 142, 292

    def x(v):
        return x0 + (v - lo) / (hi - lo) * (x1 - x0)

    parts, _ = head("fig-quattro-regioni-2010-2025", height,
                    ["Dal 2010 al 2025 la Sardegna scende da 1,18", "a 0,85 figli per donna, il Trentino-Alto Adige", "da 1,63 a 1,40"],
                    ["Figli per donna in quattro regioni.", "Cerchio vuoto 2010, pieno 2025."],
                    title, desc)
    parts.append(f'<text class="fig__axis-name" x="{W}" y="{top - 8}" text-anchor="end">Variazione</text>')
    for v in (0.8, 1.0, 1.2, 1.4, 1.6):
        parts.append(f'<line class="fig__grid" x1="{x(v):.1f}" y1="{top - 2}" x2="{x(v):.1f}" y2="{top + step * len(rows) - 4}"/>')
        parts.append(f'<text class="fig__axis" x="{x(v):.1f}" y="{top + step * len(rows) + 12}" text-anchor="middle">{it(v, 1)}</text>')
    for i, (t, a, b, d) in enumerate(rows):
        cy = top + i * step + 12
        parts.append(f'<text class="fig__name is-on" x="{xn}" y="{cy + 4}" text-anchor="end">{escape(t)}</text>')
        parts.append(f'<line class="fig__dumb is-on" x1="{x(b):.1f}" y1="{cy}" x2="{x(a):.1f}" y2="{cy}"/>')
        parts.append(f'<circle class="fig__pt-dot fig__pt-dot--old is-on" cx="{x(a):.1f}" cy="{cy}" r="3.5"/>')
        parts.append(f'<circle class="fig__pt-dot is-on" cx="{x(b):.1f}" cy="{cy}" r="3.5"/>')
        parts.append(f'<text class="fig__value is-on" x="{x(b) - 8:.1f}" y="{cy + 4}" text-anchor="end">{it(b)}</text>')
        parts.append(f'<text class="fig__value is-on" x="{x(a) + 8:.1f}" y="{cy + 4}">{it(a)}</text>')
        parts.append(f'<text class="fig__value is-on" x="{W}" y="{cy + 4}" text-anchor="end">{MINUS}{it(-d)}</text>')
    parts.append(f'<text class="fig__note" x="0" y="{height - 38}">L\'asse parte da 0,6, non da zero.</text>')
    parts += source_lines(height)
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> int:
    s = series()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "regioni-sopra-1-3.svg").write_text(bars_figure(s) + "\n", encoding="utf-8")
    (OUT / "variazione-2010-2025.svg").write_text(dumbbell_figure(s) + "\n", encoding="utf-8")
    (OUT / "quattro-regioni-2010-2025.svg").write_text(four_figure(s) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
