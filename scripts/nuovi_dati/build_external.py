#!/usr/bin/env python3
"""Porta le estrazioni di `app/static/data/nuovi/` nello strato esterno.

Legge i CSV lunghi (`indicator_id;level;territory_key;year;value`) e i manifest
scritti dagli script di estrazione, e li scrive in:

- `app/static/data/external/normalized_external_indicators.csv` (osservazioni);
- `app/static/data/external/external_indicator_levels.csv` (una riga per
  indicatore e livello, con le decisioni umane: verso, scoreable, tema).

Idempotente: prima toglie dai due file le righe degli id che governa, poi le
riscrive. Le righe degli altri id non si toccano. Nessuna rete.

La tabella `PUBBLICATI` e' la decisione editoriale: quali serie entrano, con
quale id pubblico, famiglia (feed), tema e livelli. Un indicatore estratto ma
non elencato qui non va in produzione (e' il caso di MEF e ISPRA, fermi al
2024, e delle serie Eurostat che si fermano al 2024).
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

DATA = PROJECT_ROOT / "app" / "static" / "data"
NUOVI = DATA / "nuovi"
EXTERNAL = DATA / "external"
OBS_PATH = EXTERNAL / "normalized_external_indicators.csv"
LEVELS_PATH = EXTERNAL / "external_indicator_levels.csv"
PROVINCE_CODES = DATA / "province_codes.csv"

OBS_COLUMNS = [
    "source", "source_dataset", "source_indicator_id", "target_indicator_id", "name",
    "territory_level", "territory_code", "territory_name", "year", "value", "unit",
    "theme", "quality_life_category", "direction", "definition_match",
    "atlas_eligible", "profile_eligible", "score_eligible", "coverage",
    "retrieved_at", "source_url", "license", "notes",
]
LEVEL_COLUMNS = [
    "target_indicator_id", "territory_level", "name", "theme", "quality_life_category",
    "direction", "scoreable", "sample_survey", "year_min", "year_max",
    "territory_count_latest", "coverage_latest", "source_dataset", "source_indicator_id",
    "source_url", "license", "definition_match", "reviewed_at", "notes",
]

# file di estrazione -> (feed del registro `app/sources.py`)
# id di estrazione -> (id pubblico, feed, tema, categoria, livelli ammessi)
# Le categorie sono quelle di `app/taxonomy.py:CANONICAL_CATEGORIES`.
PUBBLICATI = {
    "istat_prov": {
        "feed": "istat_provinciale",
        "serie": {
            "ISTATP_LIFEEXP65": ("ipr:speranza-di-vita-65", "Salute", "salute_cura", ("provincia",)),
            "ISTATP_FECONDITA": ("ipr:figli-per-donna", "Demografia e popolazione", "salute_cura", ("provincia",)),
            "ISTATP_INDICE_VECCHIAIA": ("ipr:indice-di-vecchiaia", "Demografia e popolazione", "salute_cura", ("provincia",)),
            "ISTATP_SALDO_MIGRATORIO_INTERNO": ("ipr:saldo-migratorio-interno", "Demografia e popolazione", "salute_cura", ("provincia",)),
            "ISTATP_ETA_MEDIA_MADRE": ("ipr:eta-media-madre-al-parto", "Demografia e popolazione", "salute_cura", ("provincia",)),
            "ISTATP_NATALITA": ("ipr:tasso-di-natalita", "Demografia e popolazione", "salute_cura", ("provincia",)),
            "ISTATP_DISOCCUPAZIONE": ("ipr:tasso-di-disoccupazione", "Lavoro", "lavoro_opportunita", ("provincia",)),
            "ISTATP_ATTIVITA": ("ipr:tasso-di-attivita", "Lavoro", "lavoro_opportunita", ("provincia",)),
        },
    },
    "eurostat_nuovi": {
        "feed": "eurostat_regional",
        "serie": {
            "EUROSTAT_CASA_NON_RISCALDATA": ("eur:ilc_mdes01_r", "Abitazione", "reddito_accessibilita", ("regione",)),
            "EUROSTAT_SCIENZIATI_INGEGNERI": ("eur:hrst_st_rcat", "Ricerca e sviluppo (Eurostat)", "ricerca_innovazione_digitale", ("regione",)),
            "EUROSTAT_ORE_LAVORATE": ("eur:lfst_r_lfe2ehour", "Lavoro e conciliazione dei tempi di vita", "lavoro_opportunita", ("regione",)),
            "EUROSTAT_NOTTI_ESTERO": ("eur:tour_occ_nin2", "Turismo", "cultura_patrimonio_turismo", ("regione",)),
            "EUROSTAT_OCCUPAZIONE_POSTI_LETTO": ("eur:tour_occ_anor2", "Turismo", "cultura_patrimonio_turismo", ("regione",)),
        },
    },
    "aci": {
        "feed": "aci_statistiche",
        "serie": {
            "ACI_AUTO_ANTE_2009": ("aci:autovetture-ante-2009", "Trasporti e mobilità", "mobilita_servizi_territoriali", ("provincia", "regione")),
            "ACI_AUTO_ALIMENTAZIONE_ALTERNATIVA": ("aci:autovetture-alimentazione-alternativa", "Trasporti e mobilità", "mobilita_servizi_territoriali", ("provincia", "regione")),
        },
    },
    "agcom": {
        "feed": "agcom_bbmap",
        "serie": {
            "AGCOM_FTTH": ("agcom:copertura-ftth", "Società dell'informazione", "ricerca_innovazione_digitale", ("provincia", "regione")),
        },
    },
}


def _read(path, delimiter=";"):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def _fmt(value):
    """Decimali con la virgola, come le altre righe dello strato esterno."""
    number = float(value)
    if number == int(number) and abs(number) < 1e12:
        return str(int(number))
    return repr(round(number, 6)).replace(".", ",")


def _names():
    from app.data import REGION_ORDER
    from app.profiles import region_key_for

    regions = {region_key_for(r): r for r in REGION_ORDER}
    provinces = {r["province_key"]: r["name"] for r in _read(PROVINCE_CODES)}
    return regions, provinces


def build(only=None):
    regions, provinces = _names()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    reviewed = now[:10]
    new_obs, new_levels, owned = [], [], set()

    for fonte, cfg in PUBBLICATI.items():
        if only and fonte not in only:
            continue
        manifest = {r["indicator_id"]: r for r in _read(NUOVI / f"{fonte}_manifest.csv")}
        values = defaultdict(dict)  # (id, level) -> {(territorio, anno): valore}
        for r in _read(NUOVI / f"{fonte}.csv"):
            values[(r["indicator_id"], r["level"])][(r["territory_key"], int(r["year"]))] = r["value"]

        for ext_id, (public_id, theme, category, levels) in cfg["serie"].items():
            m = manifest[ext_id]
            owned.add(public_id)
            for level in levels:
                cells = values.get((ext_id, level))
                if not cells:
                    raise SystemExit(f"{ext_id}: nessun valore al livello {level}")
                names = provinces if level == "provincia" else regions
                years = sorted({y for _, y in cells})
                last = years[-1]
                n_last = sum(1 for (_, y) in cells if y == last)
                universe = len(names)
                for (key, year), value in sorted(cells.items()):
                    if key not in names:
                        raise SystemExit(f"{ext_id}: territorio ignoto {level}/{key}")
                    new_obs.append({
                        "source": cfg["feed"], "source_dataset": fonte, "source_indicator_id": ext_id,
                        "target_indicator_id": public_id, "name": m["name"], "territory_level": level,
                        "territory_code": key, "territory_name": names[key], "year": year,
                        "value": _fmt(value), "unit": m["unit"], "theme": theme,
                        "quality_life_category": category, "direction": m["direction"],
                        "definition_match": "new", "atlas_eligible": "true",
                        "profile_eligible": "true", "score_eligible": "false",
                        "coverage": f"{n_last / universe:.4f}".rstrip("0").rstrip("."),
                        "retrieved_at": now, "source_url": m["source_url"], "license": m["license"],
                        "notes": m["note"],
                    })
                new_levels.append({
                    "target_indicator_id": public_id, "territory_level": level, "name": m["name"],
                    "theme": theme, "quality_life_category": category, "direction": m["direction"],
                    "scoreable": "false", "sample_survey": "false", "year_min": years[0],
                    "year_max": last, "territory_count_latest": n_last,
                    "coverage_latest": f"{n_last / universe:.4f}".rstrip("0").rstrip("."),
                    "source_dataset": fonte, "source_indicator_id": ext_id,
                    "source_url": m["source_url"], "license": m["license"],
                    "definition_match": "new", "reviewed_at": reviewed, "notes": m["note"],
                })

    keep_obs = [r for r in _read(OBS_PATH) if r["target_indicator_id"] not in owned]
    keep_levels = [r for r in _read(LEVELS_PATH) if r["target_indicator_id"] not in owned]
    _write(OBS_PATH, OBS_COLUMNS, keep_obs + new_obs)
    _write(LEVELS_PATH, LEVEL_COLUMNS, keep_levels + new_levels)
    print(f"{len(owned)} indicatori, {len(new_obs)} osservazioni, {len(new_levels)} righe di livello")


def _write(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter=";", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solo", nargs="*", help="limita a queste estrazioni (es. aci agcom)")
    args = parser.parse_args()
    build(set(args.solo) if args.solo else None)
