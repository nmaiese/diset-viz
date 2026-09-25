"""L'atlante della 1.0: la mappa di un indicatore e tutte le serie, su due livelli.

La pagina e' resa dal server con i componenti della 1.0, su due livelli: le
regioni a `/atlante`, le province a `/atlante?livello=provincia`, con il
selettore Regioni/Province come unico controllo del livello. In alto "Sulla
mappa", il modulo dato della scheda (`indicatore.explore_module`, la stessa
macro `ui.explore`) su un indicatore fisso per livello. Sotto "Tutti gli
indicatori": una tabella per tema, con il link alla scheda, la sparkline della
media semplice sul pannello fisso del livello (`indicator_view.fixed_panel`,
letta dalla proiezione), la variazione in chiaro e l'etichetta di stato sulle
parziali. All'apertura si vedono tutte: filtri, ricerca e ordine li fa
`atlante.js` sui `data-*` delle righe, con gli stessi parametri dell'atlante di
prima.

Le righe delle regioni sono le serie del catalogo regionale
(`get_atlas_catalog`). Quelle delle province sono le schede BES con il livello
provinciale (`bes_data.all_bes_indicators`), lette dalla stessa proiezione: il
catalogo e `/api/catalog` restano regionali.

Le righe si compongono una volta per processo e per livello (`rows`,
`synchronized_cache`): leggono la proiezione, che a freddo costa circa tre
secondi, e la pagina di partenza di ogni livello sta comunque nella cache di
Flask per cinque minuti.
"""

from __future__ import annotations

from app import indicator_universe, indicator_view, seo_policy, sources
from app.atlas_catalog import catalog_summary, get_atlas_catalog
from app.bes_data import all_bes_indicators, bes_level_path
from app.cache_util import synchronized_cache
from app.design import charts, numfmt
from app.design.common import signed, with_unit
from app.design.pages.indicatore import explore_module, ranking_claim
from app.profiles import slugify
from app.taxonomy import (
    CANONICAL_CATEGORIES,
    CATEGORY_NAME_TO_SLUG,
    MACRO_AREAS,
    category_path,
    slugify_taxonomy,
)

# L'indicatore della mappa sulle regioni: `featured_indicator_id` del catalogo
# (oggi 105). La prova in tests/integration/test_atlante.py controlla che sia
# ancora quello, indicizzabile e con il dato di tutte le regioni nell'ultimo
# anno: se cade, si sceglie con la stessa regola. Il verso non si chiede, il
# tasso di turisticita' descrive senza giudicare. Fisso e non estratto,
# perche' la pagina sta in cache.
MAP_INDICATOR = ("territorial", "105")

# L'indicatore della mappa sulle province: la speranza di vita alla nascita.
# La prova guarda il livello provinciale della scheda, mai `meta`: la vista
# regionale di bes-01SAL001 ha il canonical su ter-910, e la scheda come
# insieme non dice niente della sua `/province`. Il livello deve restare
# indicizzabile, con tutte le 107 province nell'ultimo anno e un verso.
MAP_INDICATOR_PROVINCE = ("bes", "01SAL001")
MAP_INDICATORS = {"regione": MAP_INDICATOR, "provincia": MAP_INDICATOR_PROVINCE}

# I due livelli dell'atlante, con l'indirizzo di ognuno. Il selettore porta
# qui, e nessun altro controllo cambia livello.
LEVEL_PATHS = {"regione": "/atlante", "provincia": "/atlante?livello=provincia"}

# Gli ordini dell'elenco, gli stessi della SPA (`SORTS` in main.jsx).
SORTS = (("complete", "Completezza"), ("recent", "Più recente"), ("az", "A-Z"), ("theme", "Tema"))


def _shown(value: float, decimals: int) -> float:
    """Il valore come il lettore lo legge, arrotondato come lo scrive `numfmt`."""
    body = numfmt.text(value, decimals).replace(".", "").replace(",", ".")
    return float(body.replace(numfmt.MINUS, "-"))


def _change(meta: dict, panel: dict, plural: str) -> dict:
    """La variazione di una riga, in chiaro: la differenza nell'unita' delle
    variazioni ("+54,3 punti percentuali" per una percentuale,
    `change_unit_label`), poi i due valori e i due anni. Quando il gruppo del
    pannello non e' intero la riga dice su quante regioni o province e' la
    media.

    Le tre cifre hanno gli stessi decimali (`column_decimals` sui due
    estremi), e la variazione e' la differenza dei due valori come sono
    scritti: "+0,004 da 0,29 a 0,30" sembrava smentire le cifre accanto."""
    first, last = panel["points"][0], panel["points"][-1]
    unit = meta.get("value_unit") or meta.get("unit")
    change_unit = meta.get("change_unit") or unit
    decimals = numfmt.column_decimals([first["value"], last["value"]])
    delta = round(_shown(last["value"], decimals) - _shown(first["value"], decimals), decimals)
    shown = numfmt.change_text(delta, decimals)
    if shown == numfmt.UNCHANGED:
        head = "invariata"
    else:
        head = signed(delta, change_unit, decimals)
    tail = (f"da {with_unit(first['value'], unit, decimals)} a {with_unit(last['value'], unit, decimals)}, "
            f"dal {first['year']} al {last['year']}")
    if panel["members"] < panel["total"]:
        tail += f", media di {panel['members']} {plural} presenti in tutti gli anni"
    return {"head": head, "tail": tail}


def _trend(meta: dict, level: dict, plural: str) -> tuple[str, dict | None]:
    """La sparkline del pannello fisso di un livello e la variazione in chiaro,
    o ("", None) quando il pannello non arriva a tre anni."""
    panel = level.get("panel")
    spark = charts.spark(panel["points"], "m", panel.get("floor"), compact=True) if panel else ""
    return spark, (_change(meta, panel, plural) if spark else None)


def province_path(record: dict) -> str | None:
    """Il link "anche per provincia" di una riga regionale, o None.

    La `/province` della scheda quando la scheda ha tutti e due i livelli
    (`bes_level_path`, mai un `?livello=` composto qui). Quando la scheda ha
    solo le regioni e le province stanno in una gemella
    (`taxonomy.PROVINCE_TWINS`, come ter-910 e bes-01SAL001), la gemella aperta
    sulle province (`indicator_view.twin_level`)."""
    keys = {level["key"] for level in record["levels"]}
    if "provincia" in keys and record["family"] == "bes":
        return bes_level_path(record["raw_id"], "provincia")
    twin = indicator_view.twin_level(record["meta"], record["levels"])
    return twin["path"] if twin and twin["key"] == "provincia" else None


def _row(item: dict, record: dict) -> dict:
    """Una riga delle regioni: una serie del catalogo regionale."""
    meta = record["meta"]
    level = next((lv for lv in record["levels"] if lv["key"] == "regione"), None) or {}
    spark, change = _trend(meta, level, "regioni")
    return {
        "id": str(item["id"]), "code": sources.indicator_code(*sources.split_internal_id(item["id"])),
        "name": item["name"], "path": item["path"],
        "family": item["catalog_family"], "y0": item["year_min"], "y1": item["year_max"],
        "complete": bool(item["complete"]), "completeness": round(100 * (item.get("completeness") or 0)),
        "n": level.get("territory_count"), "indexable": bool(meta.get("indexable")),
        "spark": spark, "change": change,
        "search": item.get("source_theme") if item.get("source_theme") != item["theme"] else None,
        "also": province_path(record),
    }


def _province_row(item: dict, record: dict) -> dict:
    """Una riga delle province: una scheda BES letta sul suo livello provinciale.

    Cio' che la riga dice viene dal livello, mai da `meta`: anni, province col
    dato, indicizzabilita' della pagina a cui porta, pannello. Una serie e'
    completa, come nel catalogo delle regioni, quando ha tutte le 107 province
    nell'ultimo anno e una copertura di almeno 0,98."""
    meta, raw_id = record["meta"], record["raw_id"]
    level = next(lv for lv in record["levels"] if lv["key"] == "provincia")
    coverage = item["levels"]["provincia"].get("coverage_latest") or 0
    count = level["territory_count"]
    spark, change = _trend(meta, level, "province")
    theme = meta.get("theme")
    return {
        "id": sources.internal_id("bes", raw_id), "code": sources.indicator_code("bes", raw_id),
        "name": meta["name"], "path": bes_level_path(raw_id, "provincia"),
        "family": "bes", "y0": level["year_min"], "y1": level["year_max"],
        "complete": count == indicator_view.PANEL_TOTALS["provincia"] and coverage >= seo_policy.MIN_COMPLETENESS,
        "completeness": round(100 * coverage), "n": count,
        "indexable": indicator_view.level_indexable(meta, "provincia", record["levels"][0]["key"]),
        "spark": spark, "change": change,
        "search": meta.get("source_theme") if meta.get("source_theme") != theme else None,
        "also": None,
    }


def _sort_key(row: dict):
    """L'ordine di partenza, "Completezza" come nella SPA: prima le serie piu'
    complete, poi le piu' recenti, poi per nome."""
    return (-row["completeness"], -row["y1"], row["name"].lower())


def _regional_rows() -> tuple[dict[str, list[dict]], list[dict]]:
    """Le righe delle regioni per tema, e le aree del catalogo coi loro temi."""
    catalog = get_atlas_catalog()
    records = {str(record["meta"]["id"]): record for record in indicator_universe.projection()}
    by_theme: dict[str, list[dict]] = {}
    for item in catalog["indicators"]:
        record = records.get(str(item["id"]))
        if record is None:
            raise LookupError(f"atlante: {item['id']} e' nel catalogo ma non nella proiezione")
        by_theme.setdefault(item["theme"], []).append(_row(item, record))
    themes = {theme["name"]: theme for theme in catalog["themes"]}
    areas = [{"name": area["name"],
              "themes": [{"name": name, "path": themes[name]["path"], "slug": themes[name]["slug"]}
                         for name in area["themes"]]}
             for area in catalog["macro_areas"]]
    return by_theme, areas


def province_items() -> list[dict]:
    """Le schede BES con il livello provinciale, dalla loro fonte: una riga
    delle province per ognuna, solo provinciali comprese."""
    return [item for item in all_bes_indicators() if "provincia" in item["levels"]]


def _province_rows() -> tuple[dict[str, list[dict]], list[dict]]:
    """Le righe delle province per tema, e le aree coi loro temi.

    Il tema e' quello della scheda, e l'area si ricava dal tema con la stessa
    corrispondenza del catalogo (`taxonomy.MACRO_AREAS` sugli slug di
    `CANONICAL_CATEGORIES`): le schede solo provinciali non hanno una
    `macro_area` loro, e senza questo sparirebbero da ogni filtro d'area."""
    records = {(record["family"], record["raw_id"]): record for record in indicator_universe.projection()}
    by_theme: dict[str, list[dict]] = {}
    for item in province_items():
        record = records.get(("bes", item["id"]))
        if record is None or not any(lv["key"] == "provincia" for lv in record["levels"]):
            raise LookupError(f"atlante: bes-{item['id']} ha le province ma non nella proiezione")
        theme = record["meta"].get("theme")
        if CATEGORY_NAME_TO_SLUG.get(theme) is None:
            raise LookupError(f"atlante: bes-{item['id']} ha il tema {theme!r}, fuori dalle categorie")
        by_theme.setdefault(theme, []).append(_province_row(item, record))
    areas = []
    for area, slugs in MACRO_AREAS.items():
        themes = []
        for slug in slugs:
            name = CANONICAL_CATEGORIES[slug]["name"]
            themes.append({"name": name, "path": category_path(slug), "slug": slugify_taxonomy(name)})
        areas.append({"name": area, "themes": themes})
    return by_theme, areas


@synchronized_cache(maxsize=2)
def rows(level_key: str) -> dict:
    """Le righe dell'elenco di un livello, raggruppate per area e per tema, e i
    conteggi.

    Regioni: una riga per ogni serie del catalogo, nessuna tolta, il loro
    numero e' quello di `get_atlas_catalog()["indicators"]`. Province: una riga
    per ogni scheda di `province_items()`. Ogni tema sta in un'area sola, e un
    tema senza area e' un errore, non una riga persa."""
    if level_key == "regione":
        by_theme, area_list = _regional_rows()
    elif level_key == "provincia":
        by_theme, area_list = _province_rows()
    else:
        raise ValueError(f"atlante: livello {level_key!r} sconosciuto")
    areas = []
    for area in area_list:
        groups = []
        for theme in area["themes"]:
            items = sorted(by_theme.pop(theme["name"], []), key=_sort_key)
            if items:
                groups.append({**theme, "rows": items})
        if groups:
            areas.append({"name": area["name"], "slug": slugify(area["name"]), "groups": groups})
    if by_theme:
        # Il guasto silenzioso di CLAUDE.md: un tema senza area toglierebbe le
        # sue righe dall'elenco senza che niente fallisca.
        raise LookupError(f"atlante: temi senza area {sorted(by_theme)}")
    flat = [row for area in areas for group in area["groups"] for row in group["rows"]]
    families = {row["family"] for row in flat}
    return {
        "areas": areas,
        "total": len(flat),
        "complete": sum(1 for row in flat if row["complete"]),
        "with_spark": sum(1 for row in flat if row["spark"]),
        "indexable": [row for row in flat if row["indexable"]],
        "years": (min(row["y0"] for row in flat), max(row["y1"] for row in flat)),
        # Solo le fonti che il livello ha: una fonte senza righe e' rumore.
        "sources": [{"id": fam["id"], "label": fam["label"]}
                    for fam in get_atlas_catalog()["source_families"] if fam["id"] in families],
    }


def map_choice(code: str | None, level_key: str) -> tuple[str, str] | None:
    """L'indicatore della mappa scelto con il bottone "Sulla mappa" di una
    riga (`?mappa=<codice>`, come `ter-105`), o None se il codice non e' una
    riga dell'elenco di quel livello con il dato dei suoi territori. Il valore
    arriva dall'URL: si risolve contro le righe, e solo la coppia risolta va
    avanti."""
    parsed = sources.parse_indicator_code(str(code or "").strip())
    if parsed is None:
        return None
    wanted = sources.internal_id(*parsed)
    for area in rows(level_key)["areas"]:
        for group in area["groups"]:
            for row in group["rows"]:
                if row["id"] == wanted and row["n"]:
                    return parsed
    return None


def map_view(indicator: tuple[str, str], level_key: str) -> dict:
    """La vista dell'indicatore della mappa, sul livello dell'atlante."""
    view = indicator_view.build_indicator_view(*indicator)
    if view is None:
        raise LookupError(f"atlante: l'indicatore della mappa {indicator} non esiste")
    level = next((lv for lv in view["levels"] if lv["key"] == level_key), None)
    if level is None:
        raise LookupError(f"atlante: l'indicatore della mappa {indicator} non ha il livello {level_key}")
    return {"meta": view["meta"], "level": level}


def level_tabs(level_key: str) -> list[dict]:
    """Il selettore Regioni/Province: un link per livello, quello corrente con
    `aria-current`, e quante righe ha ognuno."""
    return [{"key": key, "label": indicator_view.LEVELS[key]["label"], "href": path,
             "current": key == level_key, "n": rows(key)["total"]}
            for key, path in LEVEL_PATHS.items()]


def derive(ctx: dict) -> dict:
    level_key = ctx.get("level") or "regione"
    data = rows(level_key)
    shown = map_view(tuple(ctx.get("map_indicator") or MAP_INDICATORS[level_key]), level_key)
    meta, level = shown["meta"], shown["level"]
    module = explore_module(meta, level, claim=ranking_claim(level))
    year_min, year_max = data["years"]
    # Le istituzioni del livello, non del catalogo: le province sono solo BES.
    institutions = (catalog_summary()["institutions_label"] if level_key == "regione"
                    else sources.institutions_label([source["id"] for source in data["sources"]]))
    return {
        "level": level_key, "plural": indicator_view.LEVELS[level_key]["plural"],
        "path": LEVEL_PATHS[level_key], "tabs": level_tabs(level_key),
        "areas": data["areas"], "total": data["total"], "complete": data["complete"],
        "partial": data["total"] - data["complete"], "with_spark": data["with_spark"],
        "without_spark": data["total"] - data["with_spark"],
        "indexable": data["indexable"], "year_min": year_min, "year_max": year_max,
        "sources": data["sources"], "institutions": institutions,
        "years": list(range(year_min, year_max + 1)), "sorts": SORTS,
        "panel_total": indicator_view.PANEL_TOTALS[level_key],
        "panel_need": indicator_view.panel_need(level_key),
        "map": {"meta": meta, "level": level, "module": module, "href": level["preferred_path"],
                "code": sources.indicator_code(meta["family"], meta["raw_id"])},
    }
