"""L'atlante della 1.0: la mappa di un indicatore e tutte le serie del catalogo.

La pagina e' resa dal server con i componenti della 1.0. In alto "Sulla mappa",
il modulo dato della scheda (`indicatore.explore_module`, la stessa macro
`ui.explore`) su un indicatore fisso. Sotto "Tutti gli indicatori": una
tabella per tema, una riga per ogni serie del catalogo regionale
(`get_atlas_catalog`), con il link alla scheda, la sparkline della media
semplice sul pannello fisso (`indicator_view.fixed_panel`, letta dalla
proiezione), la variazione in chiaro e l'etichetta di stato sulle parziali.
All'apertura si vedono tutte: filtri, ricerca e ordine li fa `atlante.js` sui
`data-*` delle righe, con gli stessi parametri dell'atlante di prima.

Le righe si compongono una volta per processo (`rows`, `synchronized_cache`):
leggono la proiezione, che a freddo costa circa tre secondi, e la pagina sta
comunque nella cache di Flask per cinque minuti.
"""

from __future__ import annotations

from app import indicator_universe, indicator_view, sources
from app.atlas_catalog import catalog_summary, get_atlas_catalog
from app.cache_util import synchronized_cache
from app.design import charts, numfmt
from app.design.common import signed, with_unit
from app.design.pages.indicatore import explore_module, ranking_claim
from app.profiles import slugify

# L'indicatore della mappa sulle regioni: `featured_indicator_id` del catalogo
# (oggi 105). La prova in tests/integration/test_atlante.py controlla che sia
# ancora quello, indicizzabile e con il dato di tutte le regioni nell'ultimo
# anno: se cade, si sceglie con la stessa regola. Il verso non si chiede, il
# tasso di turisticita' descrive senza giudicare. Fisso e non estratto,
# perche' la pagina sta in cache.
MAP_INDICATOR = ("territorial", "105")

# Gli ordini dell'elenco, gli stessi della SPA (`SORTS` in main.jsx).
SORTS = (("complete", "Completezza"), ("recent", "Più recente"), ("az", "A-Z"), ("theme", "Tema"))


def _change(meta: dict, panel: dict, plural: str) -> dict:
    """La variazione di una riga, in chiaro: la differenza nell'unita' delle
    variazioni ("+54,3 punti percentuali" per una percentuale,
    `change_unit_label`), poi i due valori e i due anni. Quando il gruppo del
    pannello non e' intero la riga dice su quante regioni e' la media."""
    first, last = panel["points"][0], panel["points"][-1]
    unit = meta.get("value_unit") or meta.get("unit")
    change_unit = meta.get("change_unit") or unit
    delta = last["value"] - first["value"]
    shown = numfmt.change_text(delta)
    if shown == numfmt.UNCHANGED:
        head = "invariata"
    else:
        head = signed(delta, change_unit)
    tail = (f"da {with_unit(first['value'], unit)} a {with_unit(last['value'], unit)}, "
            f"dal {first['year']} al {last['year']}")
    if panel["members"] < panel["total"]:
        tail += f", media di {panel['members']} {plural} presenti in tutti gli anni"
    return {"head": head, "tail": tail}


def _row(item: dict, record: dict) -> dict:
    meta = record["meta"]
    level = next((lv for lv in record["levels"] if lv["key"] == "regione"), None) or {}
    panel = level.get("panel")
    spark = charts.spark(panel["points"], "m", panel.get("floor"), compact=True) if panel else ""
    row = {
        "id": str(item["id"]), "name": item["name"], "path": item["path"],
        "family": item["catalog_family"], "y0": item["year_min"], "y1": item["year_max"],
        "complete": bool(item["complete"]), "completeness": round(100 * (item.get("completeness") or 0)),
        "n": level.get("territory_count"), "indexable": bool(meta.get("indexable")),
        "spark": spark, "change": _change(meta, panel, "regioni") if spark else None,
        "search": item.get("source_theme") if item.get("source_theme") != item["theme"] else None,
    }
    return row


def _sort_key(row: dict):
    """L'ordine di partenza, "Completezza" come nella SPA: prima le serie piu'
    complete, poi le piu' recenti, poi per nome."""
    return (-row["completeness"], -row["y1"], row["name"].lower())


@synchronized_cache(maxsize=2)
def rows(level_key: str = "regione") -> dict:
    """Le righe dell'elenco, raggruppate per area e per tema, e i conteggi.

    Una riga per ogni serie del catalogo, nessuna tolta: il loro numero e'
    quello di `get_atlas_catalog()["indicators"]`. Il tema e l'area sono quelli
    del catalogo, dove ogni tema sta in un'area sola."""
    if level_key != "regione":
        raise ValueError(f"atlante: livello {level_key!r} non ancora servito")
    catalog = get_atlas_catalog()
    records = {str(record["meta"]["id"]): record for record in indicator_universe.projection()}
    by_theme: dict[str, list[dict]] = {}
    for item in catalog["indicators"]:
        record = records.get(str(item["id"]))
        if record is None:
            raise LookupError(f"atlante: {item['id']} e' nel catalogo ma non nella proiezione")
        by_theme.setdefault(item["theme"], []).append(_row(item, record))
    themes = {theme["name"]: theme for theme in catalog["themes"]}
    areas = []
    for area in catalog["macro_areas"]:
        groups = []
        for name in area["themes"]:
            items = sorted(by_theme.pop(name, []), key=_sort_key)
            if items:
                theme = themes[name]
                groups.append({"name": name, "path": theme["path"],
                               "slug": theme["slug"], "rows": items})
        if groups:
            areas.append({"name": area["name"], "slug": slugify(area["name"]), "groups": groups})
    if by_theme:
        # Il guasto silenzioso di CLAUDE.md: un tema senza area toglierebbe le
        # sue righe dall'elenco senza che niente fallisca.
        raise LookupError(f"atlante: temi senza area {sorted(by_theme)}")
    flat = [row for area in areas for group in area["groups"] for row in group["rows"]]
    return {
        "areas": areas,
        "total": len(flat),
        "complete": sum(1 for row in flat if row["complete"]),
        "with_spark": sum(1 for row in flat if row["spark"]),
        "indexable": [row for row in flat if row["indexable"]],
        "years": (min(row["y0"] for row in flat), max(row["y1"] for row in flat)),
        "sources": [{"id": fam["id"], "label": fam["label"]} for fam in catalog["source_families"]],
    }


def map_view(indicator: tuple[str, str] = MAP_INDICATOR) -> dict:
    """La vista dell'indicatore della mappa, livello regionale."""
    view = indicator_view.build_indicator_view(*indicator)
    if view is None:
        raise LookupError(f"atlante: l'indicatore della mappa {indicator} non esiste")
    level = next(lv for lv in view["levels"] if lv["key"] == "regione")
    return {"meta": view["meta"], "level": level}


def derive(ctx: dict) -> dict:
    data = rows(ctx.get("level") or "regione")
    shown = map_view(tuple(ctx.get("map_indicator") or MAP_INDICATOR))
    meta, level = shown["meta"], shown["level"]
    module = explore_module(meta, level, claim=ranking_claim(level))
    summary = catalog_summary()
    year_min, year_max = data["years"]
    return {
        "areas": data["areas"], "total": data["total"], "complete": data["complete"],
        "partial": data["total"] - data["complete"], "with_spark": data["with_spark"],
        "without_spark": data["total"] - data["with_spark"],
        "indexable": data["indexable"], "year_min": year_min, "year_max": year_max,
        "sources": data["sources"], "institutions": summary["institutions_label"],
        "years": list(range(year_min, year_max + 1)), "sorts": SORTS,
        "panel_total": indicator_view.PANEL_TOTALS["regione"],
        "panel_need": indicator_view.panel_need("regione"),
        "map": {"meta": meta, "level": level, "module": module,
                "code": sources.indicator_code(meta["family"], meta["raw_id"])},
    }
