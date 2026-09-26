"""/divari-regionali nella 1.0: l'hub sul divario fra Nord, Centro e Mezzogiorno.

La vista passa gia' tutto cio' che la pagina argomenta: `divari`, da
`divari.build_divari_view` (il conto su tutto il catalogo, i tre divari
d'apertura, le ripartizioni, gli altri divari), e `map_hero`, da `_map_hero`
in `app/views.py` (l'indicatore della mappa scelto con `?indicator=`, i suoi
colori sulla rampa, l'anno). Qui si mette in forma, non si ricalcola: i
decimali di ogni gruppo di cifre (`numfmt.column_decimals`, come le correzioni
del template di prima), la frase-risposta con le tre distanze vere, le
tessere, e per la mappa le classi della rampa, la legenda con le soglie, i due
estremi nominati e la classifica delle venti regioni.

La classifica della mappa legge i valori dell'anno che `_map_hero` ha gia'
chiesto (`get_atlas_indicator_year`, in cache di processo), ordinati secondo
il verso dell'indicatore, con la media semplice delle regioni al suo posto
(`common.ranking`, la stessa riga della scheda).
"""

from __future__ import annotations

import re

from app import indicator_notes
from app.atlas_catalog import get_atlas_indicator, get_atlas_indicator_year
from app.design import charts, numfmt
from app.design.common import LOWER_BETTER, PATHS, legend, map_classes, ranking, with_unit
from app.design.pages.home import level_names

AREAS = ("Nord", "Centro", "Mezzogiorno")
# La chiave `area-*` dei token di ciascuna ripartizione della pagina.
AREA_KEY = {"Nord": "nord", "Centro": "centro", "Mezzogiorno": "sud"}


def short_name(name: str) -> str:
    """Il nome dentro una frase: "tasso di occupazione", non "Tasso di
    occupazione (totale)". La parentesi finale della fonte (il sesso, il
    totale, la classificazione) resta nel link e nella scheda."""
    bare = re.sub(r"\s*\([^)]*\)\s*$", "", name or "").strip()
    return numfmt.lower_first(bare) if not re.match(r"^[A-Z]{2,}", bare) else bare


def _decimals(divario: dict) -> int:
    """I decimali delle tre medie, gli stessi per il divario fra di loro: il
    Gini esce 0,29 / 0,30 / 0,32 con divario 0,02, il PIL senza decimali."""
    return numfmt.column_decimals([divario["areas"][a]["mean"] for a in AREAS])


def _core(divario: dict) -> dict:
    dec = _decimals(divario)
    bars = [{
        "area": area, "key": AREA_KEY[area], "mean": divario["areas"][area]["mean"],
        "width": round(max(divario["areas"][area]["mean"], 0) / divario["bar_max"] * 100, 1)
        if divario["bar_max"] else 0,
    } for area in AREAS]
    return {**divario, "dec": dec, "bars": bars, "short": short_name(divario["name"])}


def _answer(core: list[dict]) -> list[dict]:
    """Le distanze della frase-risposta, una per divario d'apertura. Quando
    la ripartizione in testa e quella in coda sono le stesse per tutte, la
    frase le nomina una volta sola (`pair`)."""
    return [{"gap": c["gap"], "unit": c["change_unit"], "dec": c["dec"], "short": c["short"],
             "leader": c["leader"], "last": c["last"]} for c in core]


def _map(hero: dict) -> dict:
    """La mappa dell'indicatore scelto: classi della rampa, legenda con le
    soglie, i due estremi nominati sulla mappa e la classifica accanto."""
    meta = (get_atlas_indicator(hero["selected_id"]) or {}).get("metadata") or {}
    payload = get_atlas_indicator_year(hero["selected_id"], hero["year"]) or {}
    rows = [r for r in payload.get("values") or [] if r.get("value") is not None]
    if not rows:
        raise LookupError(f"divari-regionali: l'indicatore {hero['selected_id']} non ha valori nel {hero['year']}")
    direction = (meta.get("explain") or {}).get("direction")
    lower_better = direction in LOWER_BETTER
    unit = indicator_notes.value_unit_label(meta.get("name") or hero["indicator_name"], meta.get("unit"))
    ordered = sorted(rows, key=lambda r: r["value"], reverse=not lower_better)
    obs = [{"key": r["region_key"], "name": r["region"], "value": r["value"]} for r in ordered]
    values = [o["value"] for o in obs]
    decimals = numfmt.column_decimals(values)
    mean = sum(values) / len(values)
    best, worst = obs[0], obs[-1]
    areas = charts.area_map()
    callouts = charts.map_callouts(PATHS, [
        (best["key"], best["name"], with_unit(best["value"], unit, decimals)),
        (worst["key"], worst["name"], with_unit(worst["value"], unit, decimals)),
    ])
    # Sulla mappa ci sono anche le regioni senza dato: il suggerimento ne dice
    # il nome, non la chiave.
    names = {**level_names("regione"), **{o["key"]: o["name"] for o in obs}}
    return {
        "id": hero["selected_id"], "name": hero["indicator_name"], "short": short_name(hero["indicator_name"]),
        "path": hero["indicator_path"], "theme": hero["theme"], "year": hero["year"],
        "options": hero["options"], "unit": unit, "short_unit": numfmt.short_unit(unit),
        "unit_note": numfmt.phrase_unit(unit), "lower_better": lower_better,
        "classes": map_classes({"map_colors": hero["colors"]}),
        "names": names, "tips": {o["key"]: with_unit(o["value"], unit, decimals) for o in obs},
        "callouts": callouts, "legend": legend(values, unit), "missing": len(obs) < len(PATHS),
        "best": best, "worst": worst, "decimals": decimals, "n": len(obs),
        "rows": ranking({"observations": obs, "stats": {"year_avg": mean}, "plural": "regioni"}, unit),
        "areas": {o["key"]: areas.get(o["key"]) for o in obs},
        "area_legend": [{"area": key, "label": label, "count": sum(1 for o in obs if areas.get(o["key"]) == key)}
                        for key, label in charts.AREA_LABEL.items()],
        "source_label": meta.get("catalog_family_label") or meta.get("source_label") or "Istat",
        "source_url": meta.get("source_url"),
    }


def derive(ctx: dict) -> dict:
    view = ctx["divari"]
    core = [_core(d) for d in view["core"]]
    others = [{**d, "dec": _decimals(d), "unit_label": numfmt.lower_first(d["unit"] or "")} for d in view["others"]]
    answer = _answer(core)
    pairs = {(a["leader"], a["last"]) for a in answer}
    regions = sum(len(a["regions"]) for a in view["areas"])
    years = str(view["year_min"]) if view["year_min"] == view["year_max"] else f"{view['year_min']}-{view['year_max']}"
    tiles = [
        {"label": "Indicatori confrontati", "value": view["scanned"], "role": "count",
         "sub": "con un verso dichiarato e le venti regioni"},
        {"label": "Regioni", "value": regions, "role": "count", "sub": "medie semplici, non pesate"},
        {"label": "Ripartizioni", "value": len(view["areas"]), "role": "count",
         "sub": "Sud e Isole insieme nel Mezzogiorno"},
        {"label": "Anni dei dati", "num": years, "sub": "l'ultimo con tutte le regioni"},
    ]
    return {
        "core": core, "others": others, "answer": answer,
        "pair": next(iter(pairs)) if len(pairs) == 1 else None,
        "tiles": tiles, "regions": regions, "years": years,
        "area_key": AREA_KEY, "area_label": charts.AREA_LABEL,
        "map": _map(ctx["map_hero"]),
    }
