#!/usr/bin/env python3
"""Audit current indicators against the 2025 external-source registry."""

from __future__ import annotations

import argparse
import csv
import os
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.bes_data import get_bes_manifest  # noqa: E402
from app.data import get_catalog  # noqa: E402
from app.external_data import MANIFEST_COLUMNS, get_external_rows, freshness_status  # noqa: E402
from app.profiles import SCOREABLE_DIRECTIONS, is_core  # noqa: E402
from scripts.external_sources import source_by_id  # noqa: E402


REPORTS_DIR = PROJECT_ROOT / "reports"
MANIFEST_PATH = PROJECT_ROOT / "app" / "static" / "data" / "external_indicator_manifest.csv"
FRESHNESS_CSV = REPORTS_DIR / "data_freshness_2025.csv"
FRESHNESS_MD = REPORTS_DIR / "data_freshness_2025.md"
INVENTORY_CSV = REPORTS_DIR / "indicator_inventory.csv"


PRIORITY_RULES = [
    ("movimprese", ("imprese", "impresa", "iscrizioni", "cessazioni", "tasso di crescita")),
    ("istat_lavoro", ("occupazione", "disoccupazione", "inattiv", "mancata partecipazione", "neet")),
    ("istat_demografia", ("speranza di vita", "mortal", "fecond", "figli per donna", "saldo naturale", "saldo migratorio", "indice di vecchiaia", "eta media")),
    ("invalsi", ("competenza alfabetica", "competenza numerica", "dispersione scolastica", "traguardi")),
    ("istat_turismo", ("turismo", "presenze", "arrivi", "permanenza")),
    ("terna", ("rinnovabili", "energia elettrica", "consumi elettrici", "produzione elettrica")),
    ("infratel", ("banda", "ftth", "gigabit", "internet", "ultra larga", "ultralarga")),
]


def _write_atomic(rows, columns, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="", delete=False, dir=output_path.parent
    ) as tmp:
        writer = csv.DictWriter(tmp, fieldnames=columns, delimiter=";", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        temp_name = tmp.name
    os.replace(temp_name, output_path)
    os.chmod(output_path, 0o644)


def _source_for_name(name):
    lowered = (name or "").lower()
    for source, needles in PRIORITY_RULES:
        if any(needle in lowered for needle in needles):
            return source
    return ""


def _source_url(source_id):
    source = source_by_id(source_id) if source_id else None
    return source.get("landing_page", "") if source else ""


def _manifest_status(item, source_id, external_year):
    if not source_id:
        return "unavailable"
    if external_year and external_year >= 2025:
        return "integrated"
    if item["year_max"] >= 2025:
        return "integrated"
    if source_id in {"istat_lavoro", "invalsi", "terna", "infratel", "movimprese", "istat_turismo"}:
        return "needs_review"
    return "candidate"


def _definition_match(item, source_id):
    if source_id == "istat_demografia" and str(item["id"]) in {"910", "911", "912", "913"}:
        return "exact"
    if source_id == "istat_demografia":
        return "compatible"
    if source_id == "istat_lavoro":
        return "exact"
    if source_id == "invalsi" and item["year_max"] >= 2025:
        return "exact"
    if source_id:
        return "proxy"
    return "different"


def _score_eligible(item, source_id, status):
    direction = item.get("direction") or (item.get("explain") or {}).get("direction")
    if status != "integrated":
        return False
    if source_id in {"movimprese", "istat_turismo", "infratel"}:
        return False
    return direction in SCOREABLE_DIRECTIONS and item.get("complete") and item.get("year_max", 0) >= 2025


def _external_years():
    years = defaultdict(int)
    for row in get_external_rows():
        try:
            year = int(row.get("year") or 0)
        except ValueError:
            year = 0
        target = row.get("target_indicator_id")
        if target and year > years[target]:
            years[target] = year
    return years


def _inventory_rows():
    rows = []
    for item in get_catalog()["indicators"]:
        direction = (item.get("explain") or {}).get("direction")
        rows.append({
            "id": item["id"],
            "nome": item["name"],
            "livello_territoriale": "regione",
            "categoria": item["theme"],
            "direzione": direction,
            "unita": item["unit"],
            "ultimo_anno_disponibile": item["year_max"],
            "fonte_attuale": item["source_label"],
            "uso_in_atlante": "true",
            "uso_nei_profili": "true" if is_core(item) else "false",
            "uso_nello_scoring": "false",
        })
    for level in ("regione", "provincia"):
        for item in get_bes_manifest(level).values():
            rows.append({
                "id": item["id"],
                "nome": item["name"],
                "livello_territoriale": level,
                "categoria": item["category"] or "",
                "direzione": item["direction"],
                "unita": item["unit"],
                "ultimo_anno_disponibile": item["year_max"],
                "fonte_attuale": "Istat, BES dei Territori",
                "uso_in_atlante": "false",
                "uso_nei_profili": "false",
                "uso_nello_scoring": "true" if item["direction"] in SCOREABLE_DIRECTIONS and item["category"] else "false",
            })
    rows.sort(key=lambda r: (r["livello_territoriale"], r["categoria"], r["nome"], r["id"]))
    return rows


def _audit_rows():
    external_year = _external_years()
    rows = []
    for item in get_catalog()["indicators"]:
        source_id = _source_for_name(item["name"])
        new_year = external_year.get(str(item["id"])) or (item["year_max"] if item["year_max"] >= 2025 and source_id == "istat_demografia" else "")
        status = _manifest_status(item, source_id, int(new_year) if new_year else None)
        definition = _definition_match(item, source_id)
        direction = (item.get("explain") or {}).get("direction")
        rows.append({
            "target_indicator_id": item["id"],
            "target_indicator_name": item["name"],
            "source": source_id,
            "source_indicator_id": item["id"] if source_id else "",
            "definition_match": definition,
            "current_year": item["year_max"],
            "new_year": new_year,
            "territory_level": "regione",
            "unit_match": "true" if source_id else "false",
            "coverage": item["completeness"],
            "direction": direction,
            "score_eligible": "true" if _score_eligible(item, source_id, status) else "false",
            "status": status,
            "review_notes": _review_notes(item, source_id, status, definition),
        })
    rows.sort(key=lambda r: (r["status"], r["source"], r["target_indicator_name"]))
    return rows


def _review_notes(item, source_id, status, definition):
    if status == "integrated":
        return "Dato normalizzato nel layer esterno. Lo schema legacy non viene modificato."
    if not source_id:
        return "Nessuna fonte prioritaria 2025 mappata automaticamente sul nome indicatore."
    if definition == "proxy":
        return "Fonte candidata. Servono verifica di definizione, unita, popolazione, sesso totale e copertura prima di integrare."
    return "Richiede revisione manuale prima di uso in scoring."


def _freshness_report_rows(audit_rows):
    source_url = {row["source"]: _source_url(row["source"]) for row in audit_rows}
    return [
        {
            "id": row["target_indicator_id"],
            "nome": row["target_indicator_name"],
            "ultimo_anno_attuale": row["current_year"],
            "freshness_status": freshness_status(row["current_year"]),
            "fonte_alternativa": row["source"],
            "anno_disponibile": row["new_year"],
            "compatibilita_definizione": row["definition_match"],
            "copertura_territoriale": row["coverage"],
            "decisione": row["status"],
            "motivazione": row["review_notes"],
            "problemi": "" if row["status"] == "integrated" else "parser o compatibilita da verificare",
            "url_ufficiale": source_url.get(row["source"], ""),
        }
        for row in audit_rows
    ]


def _write_markdown(rows, output_path):
    counts = defaultdict(int)
    for row in rows:
        counts[row["decisione"]] += 1
    bes_region = get_bes_manifest("regione")
    bes_current = [item for item in bes_region.values() if item["year_max"] >= 2025]
    bes_scoreable = [
        item for item in bes_current
        if item["direction"] in SCOREABLE_DIRECTIONS
        and item["category"]
        and item["coverage_latest"] >= 0.8
    ]
    lines = [
        "# Audit freschezza dati",
        "",
        f"Generato: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Riepilogo",
        "",
        f"- indicatori aggiornati direttamente: {counts['integrated']}",
        f"- indicatori BES regionali disponibili: {len(bes_region)}",
        f"- indicatori BES regionali al 2025: {len(bes_current)}",
        f"- indicatori BES 2025 ammessi allo scoring regionale: {len(bes_scoreable)}",
        f"- indicatori non aggiornabili: {counts['unavailable']}",
        f"- indicatori da revisionare manualmente: {counts['needs_review'] + counts['candidate']}",
        "- INVALSI regionale 2025 è acquisito tramite il BES nazionale; Movimprese, Terna e Infratel restano in attesa di un parser e di un match di definizione verificati.",
        "",
        "## Decisioni metodologiche",
        "",
        "- I CSV legacy a 12 colonne restano invariati.",
        "- Le fonti esterne entrano in un dataset normalizzato separato.",
        "- Nessun nuovo indicatore entra nello scoring senza match esatto e direzione revisionata.",
        "- Indicatori demografici di struttura, fecondità e saldo migratorio restano contestuali o profilo descrittivo.",
        "- I dati assoluti non sono eleggibili per lo scoring.",
        "",
        "## Fonti ufficiali configurate",
        "",
    ]
    bes_source = source_by_id("istat_bes_regioni")
    if bes_source:
        lines.append(f"- istat_bes_regioni: {bes_source['landing_page']}")
    for source_id in sorted({row["fonte_alternativa"] for row in rows if row["fonte_alternativa"]}):
        lines.append(f"- {source_id}: {_source_url(source_id)}")
    lines.extend(["", "## Dettaglio", ""])
    lines.append("| id | indicatore | anno attuale | fonte alternativa | anno disponibile | decisione |")
    lines.append("|---|---|---:|---|---:|---|")
    for row in rows:
        lines.append(
            f"| {row['id']} | {row['nome']} | {row['ultimo_anno_attuale']} | "
            f"{row['fonte_alternativa'] or '-'} | {row['anno_disponibile'] or '-'} | {row['decisione']} |"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    inventory = _inventory_rows()
    audit = _audit_rows()
    freshness = _freshness_report_rows(audit)

    if args.dry_run:
        print(f"inventory={len(inventory)} manifest={len(audit)} freshness={len(freshness)}")
        return

    _write_atomic(inventory, list(inventory[0]), INVENTORY_CSV)
    _write_atomic(audit, MANIFEST_COLUMNS, MANIFEST_PATH)
    _write_atomic(freshness, list(freshness[0]), FRESHNESS_CSV)
    _write_markdown(freshness, FRESHNESS_MD)
    print(f"Wrote {INVENTORY_CSV}")
    print(f"Wrote {MANIFEST_PATH}")
    print(f"Wrote {FRESHNESS_CSV}")
    print(f"Wrote {FRESHNESS_MD}")


if __name__ == "__main__":
    main()
