#!/usr/bin/env python3
"""Genera config/indicator_families.csv dal catalogo storico committato.

Passo (a) di docs/FAMIGLIE_INDICATORI.md (RIPARTENZA.md §4.3). Non fa parte
della pipeline automatica di scripts/update_data.py: come
config/theme_categories.csv, il file che produce è curato, non rigenerato a
ogni aggiornamento dati (deciso da Nello il 4 settembre notte). Si rilancia
a mano quando si sospettano nuove famiglie nel catalogo, e il diff si rivede
prima del commit.

Solo il catalogo storico (app/static/data/Assoluti_Regione.csv): qui la
dimensione è nel titolo e Istat assegna un id diverso per ogni valore
(maschi/femmine/totale sono tre righe separate), quindi serve davvero una
mappatura che li colleghi. BES è strutturalmente diverso e non entra qui: un
indicatore BES ha un solo id con una colonna SESSO già nella fonte, non tre
id da collegare (docs/FAMIGLIE_INDICATORI.md, sezione 3) — il suo problema è
uno smettere di scartare quella colonna nel convertitore (passo b), non una
mappatura di famiglie.

Uso:
    .venv/bin/python scripts/generate_indicator_families.py
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = PROJECT_ROOT / "app" / "static" / "data" / "Assoluti_Regione.csv"
OUTPUT_PATH = PROJECT_ROOT / "config" / "indicator_families.csv"

OUTPUT_COLUMNS = [
    "family_key", "source", "indicator_id", "dimension", "value",
    "added_by", "added_at", "note",
]

SOURCE = "territorial"  # come app/indicator_universe.py:all_indicator_refs
DIMENSION = "sesso"
ADDED_BY = "scripts/generate_indicator_families.py"

GENDER_SUFFIX_RE = re.compile(
    r"""(?:\s*\(\s*(?P<g1>maschi|femmine|totale)\s*\)\s*$
          |\s*[-,]\s*(?P<g2>maschi|femmine|totale)\s*$
          |\s+(?P<g3>maschi|femmine|totale)\s*$)""",
    re.IGNORECASE | re.VERBOSE,
)


def _split_gender_suffix(title: str) -> tuple[str, str | None]:
    """(base, valore) se il titolo termina con maschi/femmine/totale, altrimenti (titolo, None)."""
    match = GENDER_SUFFIX_RE.search(title)
    if not match:
        return title.strip(), None
    value = (match.group("g1") or match.group("g2") or match.group("g3")).lower()
    return title[: match.start()].strip(), value


def _slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_")
    return slug


def _load_titles() -> dict[str, str]:
    title_by_id = {}
    with CATALOG_PATH.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            title_by_id[row["idIndicatore"]] = row["Indicatore"].strip()
    return title_by_id


def find_families(title_by_id: dict[str, str]) -> dict[str, dict[str, str]]:
    """base normalizzata -> {valore: indicator_id}, solo basi con >= 2 valori.

    Stessa logica (con lo stesso trattamento del totale implicito) di
    analisi/famiglie_conta.py in nmaiese/redazione-ai, verificata contro il
    campo ufficiale Istat DESCRIZIONE_ASSE_QCS il 4 settembre notte (0 falsi
    positivi, 0 falsi negativi su 377 indicatori).
    """
    groups: dict[str, dict[str, str]] = defaultdict(dict)
    bare_titles: dict[str, str] = {}
    for indicator_id, title in title_by_id.items():
        base, value = _split_gender_suffix(title)
        if value is None:
            bare_titles[title] = indicator_id
        else:
            groups[base][value] = indicator_id

    for title, indicator_id in bare_titles.items():
        if title in groups and "totale" not in groups[title]:
            groups[title]["totale"] = indicator_id

    return {base: values for base, values in groups.items() if len(values) >= 2}


def build_rows(families: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    added_at = date.today().isoformat()
    rows = []
    seen_keys: dict[str, int] = {}
    for base, values in sorted(families.items()):
        slug = _slugify(base)
        seen_keys[slug] = seen_keys.get(slug, 0) + 1
        family_key = slug if seen_keys[slug] == 1 else f"{slug}_{seen_keys[slug]}"
        for value, indicator_id in sorted(values.items()):
            rows.append({
                "family_key": family_key,
                "source": SOURCE,
                "indicator_id": indicator_id,
                "dimension": DIMENSION,
                "value": value,
                "added_by": ADDED_BY,
                "added_at": added_at,
                "note": base,
            })
    return rows


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, delimiter=";", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    title_by_id = _load_titles()
    families = find_families(title_by_id)
    rows = build_rows(families)
    write_csv(rows, OUTPUT_PATH)
    print(f"{len(families)} famiglie, {len(rows)} righe scritte in {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
