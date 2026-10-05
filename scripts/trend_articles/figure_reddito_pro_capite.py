"""Le tre figure del pezzo sul reddito pro capite.

Il pezzo confronta PIL pro capite (ter-901) e reddito disponibile delle famiglie
per abitante (ter-902) sulle stesse venti regioni. Nessun dossier: i valori si
leggono dal sito, `figures.py` non ha una forma per il rapporto fra due
territori ne' per un grafico a pendenza. Le figure hanno le classi `fig__*` di
`site.css` e un viewBox stretto (370), cosi' a 375 px il testo resta sopra gli 11 px.

    bin/py scripts/trend_articles/figure_reddito_pro_capite.py
"""
from __future__ import annotations

import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app import data  # noqa: E402

SLUG = "reddito-pro-capite-regioni-non-e-il-pil"
OUT = ROOT / "content" / "figures" / SLUG
W = 370
SOURCE = ("Fonte: Istat, Conti economici territoriali,", "edizione dicembre 2025. Elaborazione Divario Italia.")


def source_lines(height: int) -> list[str]:
    return [f'<text class="fig__source" x="0" y="{height - 20 + 14 * i}">{escape(t)}</text>' for i, t in enumerate(SOURCE)]


def it(x: float, dec: int = 2) -> str:
    return f"{x:.{dec}f}".replace(".", ",")


def eur(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def series(key: str) -> dict[str, dict[int, float]]:
    out: dict[str, dict[int, float]] = {}
    for r in data.get_indicator(key)["series"]:
        out.setdefault(r["region"], {})[r["year"]] = r["value"]
    return out


def head(fid: str, height: int, title_lines: list[str], sub_lines: list[str], title: str, desc: str) -> tuple[list[str], int]:
    parts = [
        f'<svg class="fig fig--narrow" viewBox="0 0 {W} {height}" role="img" aria-labelledby="{fid}-t {fid}-d" xmlns="http://www.w3.org/2000/svg">',
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


def lines_figure(pil, red) -> str:
    years = list(range(2004, 2025))
    rp = {y: pil["Lombardia"][y] / pil["Calabria"][y] for y in years}
    rr = {y: red["Lombardia"][y] / red["Calabria"][y] for y in years}
    title = "Sul PIL la distanza Lombardia-Calabria si riapre, sul reddito si chiude"
    desc = (f"Rapporto fra Lombardia e Calabria, Calabria uguale a 1. PIL per abitante: da {it(rp[2004])} nel 2004 a {it(rp[2024])} nel 2024. "
            f"Reddito disponibile delle famiglie per abitante: da {it(rr[2004])} nel 2004 a {it(rr[2024])} nel 2024.")
    parts = []
    top = 96
    height, bottom, left, right = 350, 82, 34, 92
    lo, hi = 1.5, 2.5
    ticks = [1.5, 2.0, 2.5]

    def x(yr):
        return left + (yr - 2004) / 20 * (W - left - right)

    def y(v):
        return height - bottom - (v - lo) / (hi - lo) * (height - top - bottom)

    head_parts, _ = head("fig-distanza-pil-reddito", height,
                         ["Sul PIL la distanza Lombardia-Calabria", "si riapre, sul reddito si chiude"],
                         ["Rapporto Lombardia/Calabria (Calabria = 1),", "valori correnti, 2004-2024."],
                         title, desc)
    parts += head_parts
    for v in ticks:
        parts.append(f'<line class="fig__grid" x1="{left}" y1="{y(v):.1f}" x2="{W - right}" y2="{y(v):.1f}"/>')
        parts.append(f'<text class="fig__axis" x="{left - 5}" y="{y(v) + 4:.1f}" text-anchor="end">{it(v, 1)}</text>')
    for yr in (2004, 2014, 2024):
        parts.append(f'<text class="fig__axis" x="{x(yr):.1f}" y="{height - bottom + 17}" text-anchor="middle">{yr}</text>')
    labels = []
    for name, css, s in (("PIL", "on", rp), ("Reddito", "ink", rr)):
        pts = " ".join(f"{x(yr):.1f},{y(v):.1f}" for yr, v in s.items())
        parts.append(f'<polyline class="fig__line fig__line--{css}" points="{pts}"/>')
        parts.append(f'<circle class="fig__dot fig__dot--{css}" cx="{x(2024):.1f}" cy="{y(s[2024]):.1f}" r="3.5"/>')
        parts.append(f'<circle class="fig__dot fig__dot--{css}" cx="{x(2004):.1f}" cy="{y(s[2004]):.1f}" r="3"/>')
        labels.append((y(s[2024]), f"{name} {it(s[2024])}", css))
        parts.append(f'<text class="fig__label fig__label--{css}" x="{x(2004) + 2:.1f}" y="{y(s[2004]) + (-9 if css == "on" else 17):.1f}">{it(s[2004])}</text>')
    for yy, text, css in labels:
        parts.append(f'<text class="fig__label fig__label--{css}" x="{x(2024) + 8:.1f}" y="{yy + 4:.1f}">{escape(text)}</text>')
    parts.append(f'<text class="fig__note" x="0" y="{height - 52}">Rapporti fra regioni nello stesso anno,</text>')
    parts.append(f'<text class="fig__note" x="0" y="{height - 38}">senza il costo della vita.</text>')
    parts += source_lines(height)
    parts.append("</svg>")
    return "\n".join(parts)


def slope_figure(pil, red) -> str:
    rank_p = {t: i + 1 for i, t in enumerate(sorted(pil, key=lambda t: -pil[t][2024]))}
    rank_r = {t: i + 1 for i, t in enumerate(sorted(red, key=lambda t: -red[t][2024]))}
    on = {"Lazio", "Piemonte", "Liguria"}
    moved = sum(1 for t in rank_p if rank_p[t] != rank_r[t])
    title = "Lazio, Piemonte e Liguria cambiano posto tra PIL e reddito"
    desc = (f"Posto delle venti regioni nel 2024 nella classifica del PIL per abitante e in quella del reddito disponibile delle famiglie per abitante. "
            f"Lazio da {rank_p['Lazio']} a {rank_r['Lazio']}, Piemonte da {rank_p['Piemonte']} a {rank_r['Piemonte']}, Liguria da {rank_p['Liguria']} a {rank_r['Liguria']}. "
            f"Trentino Alto Adige primo e Calabria ultima in entrambe. Cambiano posto {moved} regioni su 20.")
    top, step = 98, 20
    height = top + step * 20 + 66
    xl, xr = 146, 224  # estremi delle linee

    def y(rank):
        return top + (rank - 1) * step

    parts, _ = head("fig-posti-pil-reddito", height,
                    ["Lazio, Piemonte e Liguria cambiano", "posto tra PIL e reddito"],
                    ["Posto di ogni regione nella classifica per", "abitante, 2024. 1 = valore più alto."],
                    title, desc)
    parts.append(f'<text class="fig__axis-name" x="{xl}" y="{top - 14}" text-anchor="end">PIL</text>')
    parts.append(f'<text class="fig__axis-name" x="{xr}" y="{top - 14}">Reddito</text>')
    order = sorted(rank_p, key=lambda t: (t in on, rank_p[t]))  # le evidenziate sopra, disegnate per ultime
    for t in order:
        c = " is-on" if t in on else ""
        parts.append(f'<line class="fig__slope{c}" x1="{xl}" y1="{y(rank_p[t])}" x2="{xr}" y2="{y(rank_r[t])}"/>')
    for t in order:
        c = " is-on" if t in on else ""
        parts.append(f'<circle class="fig__pt-dot{c}" cx="{xl}" cy="{y(rank_p[t])}" r="3"/>')
        parts.append(f'<circle class="fig__pt-dot{c}" cx="{xr}" cy="{y(rank_r[t])}" r="3"/>')
        parts.append(f'<text class="fig__pt-name{c}" x="{xl - 8}" y="{y(rank_p[t]) + 4}" text-anchor="end">{escape(t)} {rank_p[t]}</text>')
        parts.append(f'<text class="fig__pt-name{c}" x="{xr + 8}" y="{y(rank_r[t]) + 4}">{rank_r[t]} {escape(t)}</text>')
    parts.append(f'<text class="fig__note" x="0" y="{height - 52}">Cambiano posto {moved} regioni su 20.</text>')
    parts.append(f'<text class="fig__note" x="0" y="{height - 38}">In evidenza Lazio, Piemonte e Liguria.</text>')
    parts += source_lines(height)
    parts.append("</svg>")
    return "\n".join(parts)


def bars_figure(pil, red) -> str:
    lom_p, cal_p = pil["Lombardia"][2024], pil["Calabria"][2024]
    lom_r, cal_r = red["Lombardia"][2024], red["Calabria"][2024]
    rp, rr = lom_p / cal_p, lom_r / cal_r
    title = f"Lombardia su Calabria: {it(rp, 1)} volte sul PIL, {it(rr, 1)} sul reddito"
    desc = (f"Lombardia e Calabria nel 2024, in euro per abitante. PIL: {eur(lom_p)} contro {eur(cal_p)}. "
            f"Reddito disponibile delle famiglie: {eur(lom_r)} contro {eur(cal_r)}.")
    height, left, right = 262, 70, 54
    scale = (W - left - right) / lom_p
    parts, _ = head("fig-lombardia-calabria-2024", height,
                    [f"Lombardia su Calabria: {it(rp, 1)} volte", f"sul PIL, {it(rr, 1)} sul reddito"],
                    ["Euro per abitante, valori correnti, 2024."],
                    title, desc)
    y = 98
    for label, rows, on in (("PIL per abitante", (("Lombardia", lom_p), ("Calabria", cal_p)), False),
                            ("Reddito disponibile delle famiglie", (("Lombardia", lom_r), ("Calabria", cal_r)), True)):
        c = " is-on" if on else ""
        parts.append(f'<text class="fig__subtitle" x="0" y="{y}">{escape(label)}</text>')
        y += 12
        for name, v in rows:
            w = v * scale
            parts.append(f'<text class="fig__name{c}" x="{left - 8}" y="{y + 12}" text-anchor="end">{name}</text>')
            parts.append(f'<rect class="fig__bar{c}" x="{left}" y="{y}" width="{w:.1f}" height="16"/>')
            parts.append(f'<text class="fig__value{c}" x="{left + w + 6:.1f}" y="{y + 12}">{eur(v)}</text>')
            y += 22
        y += 18
    parts += source_lines(height)
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> int:
    pil, red = series("901"), series("902")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "distanza-pil-reddito.svg").write_text(lines_figure(pil, red) + "\n", encoding="utf-8")
    (OUT / "posti-pil-reddito.svg").write_text(slope_figure(pil, red) + "\n", encoding="utf-8")
    (OUT / "lombardia-calabria-2024.svg").write_text(bars_figure(pil, red) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
