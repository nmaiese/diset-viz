"""Genera figura del rapporto tra Mezzogiorno e Nord per l'articolo ter-104.

    bin/py scripts/trend_articles/figure_istruzione.py
"""
from __future__ import annotations

import csv
from collections import defaultdict
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SLUG = "istruzione-adulti-licenza-media-divario-2024"
OUT = ROOT / "content" / "figures" / SLUG / "rapporto-mezzogiorno-nord.svg"
CSV_PATH = ROOT / "app" / "static" / "data" / "Assoluti_Regione.csv"
AREAS = {
    "Nord": {"Piemonte", "Valle d'Aosta", "Lombardia", "Trentino Alto Adige", "Veneto", "Friuli-Venezia Giulia", "Liguria", "Emilia-Romagna"},
    "Centro": {"Toscana", "Umbria", "Marche", "Lazio"},
    "Mezzogiorno": {"Abruzzo", "Molise", "Campania", "Puglia", "Basilicata", "Calabria", "Sicilia", "Sardegna"},
}
W, H = 370, 240


def values() -> dict[str, dict[int, float]]:
    totals: dict[str, dict[int, list[float]]] = {area: defaultdict(list) for area in AREAS}
    with CSV_PATH.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source, delimiter=";"):
            if row["idIndicatore"] != "104" or row["Territorio"] not in set.union(*AREAS.values()):
                continue
            for area, regions in AREAS.items():
                if row["Territorio"] in regions and row["Anno"] in {"2018", "2024"}:
                    totals[area][int(row["Anno"])].append(float(row["Dato"].replace(",", ".")))
    means = {area: {year: sum(nums) / len(nums) for year, nums in years.items()} for area, years in totals.items()}
    return {str(year): means["Mezzogiorno"][year] / means["Nord"][year] for year in (2018, 2024)}


def render(ratios: dict[str, float]) -> str:
    left, right, top, bottom = 58, 56, 91, 56
    lo, hi = 1.0, 1.4

    def x(year: int) -> float:
        return left + (year - 2018) / 6 * (W - left - right)

    def y(ratio: float) -> float:
        return H - bottom - (ratio - lo) / (hi - lo) * (H - top - bottom)

    p1, p2 = (x(2018), y(ratios["2018"])), (x(2024), y(ratios["2024"]))
    title = "Il rapporto Mezzogiorno-Nord resta circa 1,27"
    desc = f"Rapporto tra la media semplice delle regioni del Mezzogiorno e quella del Nord: {ratios['2018']:.3f} nel 2018 e {ratios['2024']:.3f} nel 2024."
    parts = [
        f'<svg class="fig fig--narrow" viewBox="0 0 {W} {H}" role="img" aria-labelledby="rapporto-t rapporto-d" xmlns="http://www.w3.org/2000/svg">',
        f'<title id="rapporto-t">{escape(title)}</title>',
        f'<desc id="rapporto-d">{escape(desc)}</desc>',
        '<text class="fig__title" x="0" y="20">Il rapporto Mezzogiorno-Nord</text>',
        '<text class="fig__title" x="0" y="39">resta circa 1,27</text>',
        '<text class="fig__subtitle" x="0" y="61">Rapporto tra medie semplici regionali, 2018 e 2024.</text>',
    ]
    for tick in (1.0, 1.1, 1.2, 1.3, 1.4):
        yy = y(tick)
        parts.extend((f'<line class="fig__grid" x1="{left}" y1="{yy:.1f}" x2="{W-right}" y2="{yy:.1f}"/>',
                      f'<text class="fig__axis" x="{left-7}" y="{yy+4:.1f}" text-anchor="end">{tick:.1f}</text>'))
    parts.extend((f'<line class="fig__line fig__line--on" x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" y2="{p2[1]:.1f}"/>',
                  f'<circle class="fig__dot is-on" cx="{p1[0]:.1f}" cy="{p1[1]:.1f}" r="4"/>',
                  f'<circle class="fig__dot is-on" cx="{p2[0]:.1f}" cy="{p2[1]:.1f}" r="4"/>'))
    for year, point in ((2018, p1), (2024, p2)):
        parts.extend((f'<text class="fig__label fig__label--on" x="{point[0]:.1f}" y="{point[1]-9:.1f}" text-anchor="middle">{ratios[str(year)]:.3f}</text>',
                      f'<text class="fig__axis" x="{point[0]:.1f}" y="{H-bottom+19}" text-anchor="middle">{year}</text>'))
    parts.extend(('<text class="fig__source" x="0" y="205">Fonte: Istat, Banca dati territoriale, anni 2018 e 2024.</text>',
                  '<text class="fig__source" x="0" y="220">Elaborazione: medie semplici delle regioni.</text>', '</svg>'))
    return "\n".join(parts) + "\n"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(values()), encoding="utf-8")


if __name__ == "__main__":
    main()
