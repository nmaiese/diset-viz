"""La figura del pezzo sui medici di famiglia con piu' di 1500 assistiti.

Il pezzo segue bes-12SER027: Nord, Centro e Mezzogiorno dal 2004 al 2023, valori
ufficiali Istat (`data/derived/bes_areas_12SER027.csv`, pesati, non medie delle
regioni). `figures.py lines` stampa sette linee su 680 px e a 375 px il testo
scende sotto gli 11 px, quindi qui un viewBox stretto (370) e tre linee.

    bin/py scripts/trend_articles/figure_medici_famiglia.py
"""
from __future__ import annotations

import csv
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SLUG = "medici-di-famiglia-regioni"
OUT = ROOT / "content" / "figures" / SLUG
W, H = 370, 330
SOURCE = ("Fonte: Istat, Bes, elaborazione su dati Ministero della Salute.", "Valori Istat di ripartizione. Elaborazione Divario Italia.")
AREAS = (("Nord", "north"), ("Centro", "centre"), ("Mezzogiorno", "south"))


def it(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def read() -> dict[str, dict[int, float]]:
    out: dict[str, dict[int, float]] = {}
    with open(ROOT / "data" / "derived" / "bes_areas_12SER027.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out.setdefault(r["territory"], {})[int(r["year"])] = float(r["value"])
    return out


def figure(s: dict[str, dict[int, float]]) -> str:
    n, c, m = s["Nord"], s["Centro"], s["Mezzogiorno"]
    assert round(n[2004] - m[2004]) == 2 and round(n[2023] - m[2023]) == 24
    assert (n[2004], n[2023], c[2023], m[2004], m[2023]) == (17.6, 63.8, 48.7, 15.6, 39.6)
    title = "Fra Nord e Mezzogiorno la distanza passa da 2 punti nel 2004 a 24 nel 2023"
    desc = ("Quota di medici di famiglia con più di 1500 assistiti, per ripartizione, dal 2004 al 2023. "
            f"Nord da {it(n[2004])} a {it(n[2023])}, Centro da {it(c[2004])} a {it(c[2023])}, "
            f"Mezzogiorno da {it(m[2004])} a {it(m[2023])}. Nel 2004 il Nord stava a {it(n[2004] - m[2004])} punti dal Mezzogiorno, nel 2023 a {it(n[2023] - m[2023])}.")
    x0, x1, yt, yb, vmax = 30, 282, 84, 270, 70
    years = list(range(2004, 2024))

    def x(y: int) -> float:
        return x0 + (y - 2004) / 19 * (x1 - x0)

    def y(v: float) -> float:
        return yb - v / vmax * (yb - yt)

    p = [f'<svg class="fig fig--narrow" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="fig-serie-t fig-serie-d" xmlns="http://www.w3.org/2000/svg">',
         f'<title id="fig-serie-t">{escape(title)}</title>', f'<desc id="fig-serie-d">{escape(desc)}</desc>']
    ty = 18
    for line in ("Fra Nord e Mezzogiorno la distanza passa", "da 2 punti nel 2004 a 24 nel 2023"):
        p.append(f'<text class="fig__title" x="0" y="{ty}">{escape(line)}</text>')
        ty += 19
    for i, line in enumerate(("Medici di famiglia con più di 1500", "assistiti, ogni 100. 2004-2023.")):
        p.append(f'<text class="fig__subtitle" x="0" y="{ty + 1 + 15 * i}">{escape(line)}</text>')
    for v in (0, 20, 40, 60):
        p.append(f'<line class="fig__grid" x1="{x0}" y1="{y(v):.1f}" x2="{x1}" y2="{y(v):.1f}"/>')
        p.append(f'<text class="fig__axis" x="{x0 - 5}" y="{y(v) + 4:.1f}" text-anchor="end">{v}</text>')
    for yr in (2004, 2010, 2016, 2023):
        p.append(f'<text class="fig__axis" x="{x(yr):.1f}" y="{yb + 16}" text-anchor="middle">{yr}</text>')
    for name, cls in AREAS:
        pts = " ".join(f"{x(yr):.1f},{y(s[name][yr]):.1f}" for yr in years)
        p.append(f'<polyline class="fig__line fig__line--{cls}" points="{pts}"/>')
        p.append(f'<circle class="fig__dot fig__dot--{cls}" cx="{x(2023):.1f}" cy="{y(s[name][2023]):.1f}" r="3.5"/>')
        p.append(f'<text class="fig__label fig__label--{cls}" x="{x1 + 8}" y="{y(s[name][2023]) + 4:.1f}">{name} {it(s[name][2023])}</text>')
    p.append(f'<text class="fig__note" x="0" y="{H - 48}">Valori Istat per ripartizione, pesati. Ultimo anno 2023.</text>')
    for i, t in enumerate(SOURCE):
        p.append(f'<text class="fig__source" x="0" y="{H - 34 + 14 * i}">{escape(t)}</text>')
    p.append("</svg>")
    return "\n".join(p)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "serie-ripartizioni.svg").write_text(figure(read()) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
