"""Genera il grafico sugli erogatori delle cure ricevute fuori regione.

Legge soltanto le sei celle GIMBE 2023 dichiarate nel CSV dell'articolo. La
selezione fallisce se una cella manca, compare due volte o appartiene a una
combinazione inattesa di territorio e settore.

    bin/py scripts/trend_articles/figure_cure_fuori_regione.py
"""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "app" / "static" / "data" / "articles" / "chi-eroga-cure-fuori-regione.csv"
OUT = ROOT / "content" / "figures" / "chi-eroga-cure-fuori-regione" / "erogatori-cure-fuori-regione.svg"

YEAR = "2023"
UNIT = "percentuale del valore"
SOURCE = "Fondazione GIMBE, Rapporto Osservatorio 1/2026, tabella 4.5"
HOSPITAL = "Quota del valore dei ricoveri ordinari e day hospital ricevuti in mobilita attiva erogata dal privato convenzionato"
OUTPATIENT = "Quota del valore della specialistica ambulatoriale ricevuta in mobilita attiva erogata dal privato convenzionato"
CELL_SPECS = (
    ("Lombardia", HOSPITAL, "Ricoveri"),
    ("Lombardia", OUTPATIENT, "Specialistica"),
    ("Emilia-Romagna", HOSPITAL, "Ricoveri"),
    ("Emilia-Romagna", OUTPATIENT, "Specialistica"),
    ("Toscana", HOSPITAL, "Ricoveri"),
    ("Toscana", OUTPATIENT, "Specialistica"),
)
EXPECTED = {(territory, measure): sector for territory, measure, sector in CELL_SPECS}

W, H = 370, 386
PLOT_LEFT, PLOT_RIGHT = 166, 346
BAR_Y = (133, 155, 185, 207, 237, 259)
BAR_HEIGHT = 14


def load_values(path: Path = CSV_PATH) -> list[tuple[str, str, Decimal]]:
    """Restituisce le sei quote GIMBE nell'ordine della figura."""
    found: dict[tuple[str, str], Decimal] = {}
    with Path(path).open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        required = {"misura", "unita", "anno", "territorio", "valore", "fonte"}
        missing_columns = required - set(reader.fieldnames or ())
        if missing_columns:
            raise ValueError(f"colonne mancanti nel CSV: {', '.join(sorted(missing_columns))}")
        for line_number, row in enumerate(reader, start=2):
            if row["fonte"] != SOURCE:
                continue
            key = (row["territorio"], row["misura"])
            if key not in EXPECTED or row["anno"] != YEAR or row["unita"] != UNIT:
                raise ValueError(f"cella GIMBE inattesa alla riga {line_number}: {key!r}, anno {row['anno']!r}, unita {row['unita']!r}")
            if key in found:
                raise ValueError(f"cella GIMBE duplicata alla riga {line_number}: {key!r}")
            try:
                value = Decimal(row["valore"])
            except InvalidOperation as error:
                raise ValueError(f"valore GIMBE non numerico alla riga {line_number}: {row['valore']!r}") from error
            if not value.is_finite() or not Decimal("0") <= value <= Decimal("100"):
                raise ValueError(f"valore GIMBE fuori scala alla riga {line_number}: {row['valore']!r}")
            found[key] = value

    missing = [f"{territory} / {sector}" for territory, measure, sector in CELL_SPECS if (territory, measure) not in found]
    if missing:
        raise ValueError(f"celle GIMBE mancanti: {', '.join(missing)}")
    return [(territory, sector, found[(territory, measure)]) for territory, measure, sector in CELL_SPECS]


def _it(value: Decimal) -> str:
    return f"{value:.1f}".replace(".", ",")


def render(values: list[tuple[str, str, Decimal]]) -> str:
    by_key = {(territory, sector): value for territory, sector, value in values}
    expected_keys = {(territory, sector) for territory, _, sector in CELL_SPECS}
    if len(values) != len(CELL_SPECS) or set(by_key) != expected_keys:
        raise ValueError("la figura richiede esattamente le sei celle GIMBE attese")
    title = "Chi eroga le cure ricevute da fuori regione"
    description = (
        "Quota del valore economico della mobilità sanitaria attiva erogata dal privato convenzionato nelle regioni di destinazione. "
        f"Lombardia: ricoveri {_it(by_key[('Lombardia', 'Ricoveri')])}% e specialistica {_it(by_key[('Lombardia', 'Specialistica')])}%. "
        f"Emilia-Romagna: ricoveri {_it(by_key[('Emilia-Romagna', 'Ricoveri')])}% e specialistica {_it(by_key[('Emilia-Romagna', 'Specialistica')])}%. "
        f"Toscana: ricoveri {_it(by_key[('Toscana', 'Ricoveri')])}% e specialistica {_it(by_key[('Toscana', 'Specialistica')])}%. "
        "Dati 2023. Fonte Fondazione GIMBE, tabella 4.5, pubblicata il 4 marzo 2026."
    )
    parts = [
        f'<svg class="fig fig--narrow" viewBox="0 0 {W} {H}" role="img" aria-labelledby="fig-erogatori-cure-t fig-erogatori-cure-d" xmlns="http://www.w3.org/2000/svg">',
        f'<title id="fig-erogatori-cure-t">{escape(title)}</title>',
        f'<desc id="fig-erogatori-cure-d">{escape(description)}</desc>',
        f'<text class="fig__title" x="2" y="18">{escape(title)}</text>',
        '<text class="fig__subtitle" x="2" y="41"><tspan x="2">Quota del valore erogata dal privato convenzionato.</tspan><tspan x="2" dy="15">Anno 2023, percentuale. Scala comune 0-100%.</tspan></text>',
        '<circle class="fig__dot is-on" cx="7" cy="77" r="5"/>',
        '<text class="fig__axis-name" x="18" y="81">Ricoveri ordinari e day hospital</text>',
        '<circle class="fig__dot" cx="7" cy="95" r="5"/>',
        '<text class="fig__axis-name" x="18" y="99">Specialistica ambulatoriale</text>',
    ]

    for tick in (0, 25, 50, 75, 100):
        x = PLOT_LEFT + (PLOT_RIGHT - PLOT_LEFT) * tick / 100
        parts.append(f'<line class="fig__grid" x1="{x:.1f}" y1="126" x2="{x:.1f}" y2="276"/>')
        parts.append(f'<text class="fig__axis" x="{x:.1f}" y="120" text-anchor="middle">{tick}</text>')

    plot_width = Decimal(PLOT_RIGHT - PLOT_LEFT)
    for (territory, sector, value), y in zip(values, BAR_Y, strict=True):
        width = value * plot_width / Decimal("100")
        highlighted = " is-on" if sector == "Ricoveri" else ""
        short_sector = "ric." if sector == "Ricoveri" else "spec."
        name = f"{territory} · {short_sector}"
        parts.append(f'<text class="fig__name" x="158" y="{y + 11}" text-anchor="end">{escape(name)}</text>')
        parts.append(f'<rect class="fig__bar{highlighted}" x="{PLOT_LEFT}" y="{y}" width="{width:.1f}" height="{BAR_HEIGHT}"/>')
        parts.append(f'<text class="fig__value" x="{Decimal(PLOT_LEFT) + width + Decimal("5"):.1f}" y="{y + 11}">{_it(value)}%</text>')

    parts.extend(
        (
            '<text class="fig__note" x="2" y="296"><tspan x="2">Denominatore: valore pubblico più privato,</tspan><tspan x="2" dy="14">nello stesso settore e nella stessa destinazione.</tspan><tspan x="2" dy="14">Limite: tre destinazioni, confronto descrittivo.</tspan><tspan x="2" dy="14">Non sono quote di pazienti, ricoveri o prestazioni.</tspan></text>',
            '<text class="fig__source" x="2" y="362"><tspan x="2">Fonte: Fondazione GIMBE, tabella 4.5, dati 2023.</tspan><tspan x="2" dy="14">Pubblicata il 4 marzo 2026. Elaborazione Divario Italia.</tspan></text>',
            "</svg>",
        )
    )
    return "\n".join(parts) + "\n"


def main(csv_path: Path = CSV_PATH, output_path: Path = OUT) -> int:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render(load_values(Path(csv_path))), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
