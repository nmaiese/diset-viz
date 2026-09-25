"""Il confronto della 1.0: un indicatore, fino a tre regioni o tre province,
reso dal server.

`/confronto` era l'ultima rotta della SPA. Adesso la pagina arriva completa
dal server: il selettore dell'indicatore e delle regioni (un `form` GET, che
senza JavaScript e' il modo di cambiare confronto), la mappa dell'anno scelto
con le regioni del confronto in evidenza, la tabella con valore e posizione,
e la serie nel tempo delle regioni scelte con la media semplice delle regioni
come riferimento. Con il JavaScript l'isola `static/js/confronto.js` cambia
indicatore, regioni e anno senza ricaricare, leggendo `/api/indicator/<id>`,
e salva i confronti sull'account.

**Lo stato vive nell'URL**: `indicator` (l'id del catalogo, `105` o
`bes:10AMB014`, come nei link `?indicator=` della SPA, oppure il codice della
scheda, `ter-105`), `region` ripetuto fino a tre volte (la chiave,
`lombardia`, o il nome, `Lombardia`), `year` (anche `anno`). Il confronto
della SPA non teneva regioni e anno nell'URL: quei parametri nascono qui. Un valore
che non regge si lascia cadere e vale il valore di partenza: un link vecchio
apre sempre un confronto.

**Il livello** (`livello`, `LEVELS`): `regione`, il confronto di sempre, o
`provincia`, fino a tre province, mai regioni e province insieme. Un livello
sconosciuto vale le regioni. Sulle province le province stanno in `provincia`
ripetuto fino a tre volte (al posto di `region`), e gli indicatori offerti sono
solo quelli con la vista `/province` che passa la regola dell'indice
(`province_ids`): un indicatore che non ce l'ha torna a quello di partenza del
livello, come una regione che non regge. Nello stato la chiave `regions` porta
i territori del livello, regioni o province.

Tutto cio' che la pagina scrive viene dallo stesso payload che l'isola legge:
`get_atlas_indicator` per le regioni, cioe' `/api/indicator/<id>`, e
`indicator_universe.province_payload` per le province, cioe'
`/api/indicator/<id>?livello=provincia`. La pagina servita e quella ridisegnata
dal JavaScript partono dagli stessi numeri. Il ripiego non c'e': se questo
modulo cede, `design.render` risponde 500 (vedi `app/views.py`).
"""

from __future__ import annotations

import unicodedata

from app import bes_data, indicator_universe, indicator_view, profiles, province_profile, sources
from app.atlas_catalog import get_atlas_catalog, get_atlas_indicator
from app.design import charts, maps, numfmt
from app.design.common import LOWER_BETTER, legend

# Fino a tre territori, come la SPA: tre linee e tre colori si leggono ancora.
MAX_TERRITORIES = 3
# Nord, Centro e Mezzogiorno, quando il link non dice altro.
DEFAULT_REGIONS = ("lombardia", "lazio", "campania")
DEFAULT_PROVINCES = ("milano", "roma", "napoli")
# La palette categorica (--cat-1..3): il colore identifica un territorio, non
# lo giudica. Nel CSS stanno come classi `s1`..`s3`, mai scritti nel markup.
SERIES_CLASSES = ("s1", "s2", "s3")

# I livelli che il confronto conosce. `param` e `aliases` sono i nomi dei
# territori nell'URL, `profile` il profilo di un territorio, `defaults` i
# territori di partenza. Il selettore, l'URL e l'isola li leggono da qui.
LEVELS = {
    "regione": {"label": "Regioni", "plural": "regioni", "singular": "regione", "param": "region",
                "aliases": ("regione",), "profile": "/regione/", "defaults": DEFAULT_REGIONS},
    "provincia": {"label": "Province", "plural": "province", "singular": "provincia", "param": "provincia",
                  "aliases": (), "profile": "/provincia/", "defaults": DEFAULT_PROVINCES},
}
DEFAULT_LEVEL = "regione"
ORDINALS = ("Prima", "Seconda", "Terza")


def _norm(text: str) -> str:
    """"Valle d'Aosta" e "valle-d-aosta" si incontrano: minuscolo, senza
    accenti, con solo lettere e cifre."""
    plain = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    return "".join(ch for ch in plain.lower() if ch.isalnum())


def catalog_ids() -> set[str]:
    return {str(item["id"]) for item in get_atlas_catalog()["indicators"]}


def province_pages() -> list[dict]:
    """Le `/province` che passano la regola dell'indice, una per scheda a due
    livelli: `indicator_universe.level_pages(listed=True)`, cioe' la regola
    (`indicator_view.level_passes_rule`) e non l'interruttore
    `seo_policy.LEVEL_PAGES_INDEXABLE`, che toglie l'indice e non i link. Le
    schede solo provinciali non hanno una `/province` e non ci sono."""
    return [page for page in indicator_universe.level_pages(listed=True)
            if not page["base"] and page["level"]["key"] == "provincia"]


def province_ids() -> set[str]:
    return {str(page["meta"]["id"]) for page in province_pages()}


def level_ids(level: str) -> set[str]:
    """Gli indicatori che il confronto offre su un livello."""
    return catalog_ids() if level == "regione" else province_ids()


def payload_for(indicator: str, level: str) -> dict | None:
    """Il payload che la pagina compone e l'isola legge, per livello."""
    if level == "regione":
        return get_atlas_indicator(indicator)
    return indicator_universe.province_payload(indicator)


def default_indicator(level: str = DEFAULT_LEVEL) -> str:
    """L'indicatore di partenza: sulle regioni quello in evidenza nel catalogo,
    come la SPA, sulle province quello della mappa dell'atlante (la speranza di
    vita), o il primo per id se la sua `/province` uscisse dalla regola."""
    if level == "regione":
        return str(get_atlas_catalog()["featured_indicator_id"])
    from app.design.pages.atlante import MAP_INDICATORS

    wanted = sources.internal_id(*MAP_INDICATORS["provincia"])
    ids = province_ids()
    if wanted in ids:
        return wanted
    if not ids:
        raise LookupError("confronto: nessuna /province passa la regola")
    return sorted(ids)[0]


def indicator_id(value, level: str = DEFAULT_LEVEL) -> str | None:
    """L'id del catalogo per `105`, `bes:10AMB014` o `ter-105`, o None se il
    livello non lo offre."""
    raw = str(value or "").strip()
    if not raw:
        return None
    ids = level_ids(level)
    if raw in ids:
        return raw
    parsed = sources.parse_indicator_code(raw)
    if parsed:
        wanted = sources.internal_id(*parsed)
        if wanted in ids:
            return wanted
    return None


def _territories(payload: dict) -> dict[str, str]:
    """{chiave: nome} dei territori che hanno almeno un valore."""
    return {row["region_key"]: row["region"] for row in payload["series"] if row["value"] is not None}


def _years(payload: dict) -> list[int]:
    return sorted({int(row["year"]) for row in payload["series"] if row["value"] is not None})


def resolve_state(args) -> dict:
    """Lo stato del confronto dall'URL, normalizzato: `level`, `indicator`
    (id del catalogo), `regions` (le chiavi dei territori del livello, al
    massimo tre, nell'ordine chiesto) e `year`. `args` e' un `MultiDict`
    (`request.args`) o un dict."""
    getlist = args.getlist if hasattr(args, "getlist") else (lambda k: [args[k]] if k in args else [])
    level = args.get("livello") if args.get("livello") in LEVELS else DEFAULT_LEVEL
    spec = LEVELS[level]
    wanted = indicator_id(args.get("indicator") or args.get("indicatore"), level) or default_indicator(level)
    payload = payload_for(wanted, level)
    if payload is None:
        raise LookupError(f"confronto: l'indicatore {wanted} non ha un payload per il livello {level}")
    names = _territories(payload)
    by_norm = {_norm(key): key for key in names} | {_norm(name): key for key, name in names.items()}
    chosen: list[str] = []
    for name in (spec["param"], *spec["aliases"]):
        for value in getlist(name):
            key = by_norm.get(_norm(value))
            if key and key not in chosen:
                chosen.append(key)
    chosen = chosen[:MAX_TERRITORIES]
    if not chosen:
        chosen = [key for key in spec["defaults"] if key in names] or sorted(names)[:MAX_TERRITORIES]
    years = _years(payload)
    try:
        year = int(args.get("year") or args.get("anno") or 0)
    except (TypeError, ValueError):
        year = 0
    if year not in years:
        year = years[-1]
    return {"level": level, "indicator": wanted, "regions": tuple(chosen), "year": year}


def nude_state(level: str = DEFAULT_LEVEL) -> dict:
    """Lo stato della pagina nuda di un livello."""
    return resolve_state({"livello": level})


def is_default(state: dict) -> bool:
    """Lo stato della pagina nuda del suo livello, quello che sta in cache."""
    return state == nude_state(state["level"])


def level_path(level: str) -> str:
    """L'indirizzo della pagina nuda di un livello."""
    return "/confronto" if level == DEFAULT_LEVEL else f"/confronto?livello={level}"


def query(state: dict) -> str:
    """La query string dello stato: vuota per la pagina nuda delle regioni,
    `?livello=provincia` per quella delle province. L'ordine e i nomi sono
    quelli che scrive anche `confronto.js`."""
    if is_default(state):
        return level_path(state["level"])[len("/confronto"):]
    payload = payload_for(state["indicator"], state["level"])
    param = LEVELS[state["level"]]["param"]
    parts = [f"indicator={state['indicator']}"]
    parts += [f"{param}={key}" for key in state["regions"]]
    if state["year"] != _years(payload)[-1]:
        parts.append(f"year={state['year']}")
    if state["level"] != DEFAULT_LEVEL:
        parts.append(f"livello={state['level']}")
    return "?" + "&".join(parts)


def switch_href(level: str, indicator: str) -> str:
    """Il link del selettore del livello verso `level`: tiene l'indicatore se
    quel livello lo offre e non e' gia' il suo di partenza, altrimenti porta
    alla pagina nuda del livello. La stessa regola di `switchHref` nell'isola."""
    if indicator not in level_ids(level) or indicator == default_indicator(level):
        return level_path(level)
    return f"/confronto?indicator={indicator}" + ("" if level == DEFAULT_LEVEL else f"&livello={level}")


def compare_path(meta: dict, level_key: str) -> str | None:
    """Il confronto di una scheda aperta su un livello, o None se il
    confronto non offre l'indicatore su quel livello. Lo usa la corsia "Lo
    stesso dato, altre viste" della scheda alla sua `/province`."""
    indicator = str(meta.get("id") or "")
    if level_key not in LEVELS or indicator not in level_ids(level_key):
        return None
    return switch_href(level_key, indicator)


def _group(items: list[dict]) -> list[dict]:
    """Aree, temi, e in ogni tema le serie per nome."""
    catalog = get_atlas_catalog()
    by_theme: dict[str, list[dict]] = {}
    for item in items:
        by_theme.setdefault(item["theme"], []).append(item)
    groups = []
    for area in catalog["macro_areas"]:
        for theme in area["themes"]:
            entries = sorted(by_theme.pop(theme, []), key=lambda i: i["name"].lower())
            if entries:
                groups.append({"label": theme,
                               "entries": [{"id": e["id"], "name": e["name"], "u": e["u"]} for e in entries]})
    if by_theme:
        # Lo stesso guasto silenzioso dell'atlante: un tema senza area
        # toglierebbe le sue serie dal selettore senza che niente fallisca.
        raise LookupError(f"confronto: temi senza area {sorted(by_theme)}")
    return groups


def indicator_options(level: str = DEFAULT_LEVEL) -> list[dict]:
    """Il selettore dell'indicatore: aree, temi, e in ogni tema le serie per
    nome. Sulle regioni il catalogo dell'atlante, sulle province le schede con
    la `/province` che passa la regola. `u` e' l'unita' come si scrive accanto
    a una cifra (`numfmt.phrase_unit`): l'isola la legge dall'opzione, perche'
    l'API da' l'etichetta della fonte ("Valori percentuali") e la pagina
    scrive "%"."""
    if level == "regione":
        items = [{"id": str(item["id"]), "name": item["name"], "theme": item["theme"],
                  "u": numfmt.phrase_unit(item.get("unit")) or ""}
                 for item in get_atlas_catalog()["indicators"]]
    else:
        items = [{"id": str(page["meta"]["id"]), "name": page["meta"]["name"], "theme": page["meta"]["theme"],
                  "u": numfmt.phrase_unit(page["meta"].get("unit")) or ""}
                 for page in province_pages()]
    return _group(items)


def province_groups(names: dict[str, str]) -> list[dict]:
    """Le province del selettore, regione per regione: le stesse chiavi, gli
    stessi nomi e lo stesso ordine dell'indice delle province
    (`province_profile.by_region`), solo quelle che hanno il dato
    dell'indicatore (`names`). Le regioni nell'ordine geografico del sito."""
    overview = profiles.regions_overview()
    groups = []
    for region_key, provinces in province_profile.by_region().items():
        entries = [{"key": p["key"], "name": p["name"]} for p in provinces if p["key"] in names]
        if entries:
            groups.append({"key": region_key, "label": overview[region_key]["region"], "entries": entries})
    return groups


def _ranked(values: dict[str, float], names: dict[str, str], lower_better: bool) -> list[str]:
    """Le chiavi dal primo all'ultimo posto. A pari valore per nome, come
    `rows` di v1.js e come l'isola."""
    return sorted(values, key=lambda k: ((values[k] if lower_better else -values[k]), names[k]))


def derive(ctx: dict) -> dict:
    state = ctx["state"]
    level_key = state["level"]
    level = LEVELS[level_key]
    payload = payload_for(state["indicator"], level_key)
    meta = payload["metadata"]
    names = _territories(payload)
    years = _years(payload)
    year = state["year"]
    direction = (meta.get("explain") or {}).get("direction")
    lower_better = direction in LOWER_BETTER
    unit = numfmt.phrase_unit(meta.get("unit")) or ""

    matrix: dict[int, dict[str, float]] = {}
    for row in payload["series"]:
        if row["value"] is not None:
            matrix.setdefault(int(row["year"]), {})[row["region_key"]] = float(row["value"])
    now = matrix.get(year, {})
    decimals = numfmt.column_decimals(list(now.values()))
    order = _ranked(now, names, lower_better)
    position = {key: i + 1 for i, key in enumerate(order)}

    # La media semplice dei territori con il dato, anno per anno. Nella serie
    # solo sugli anni in cui almeno `need` territori hanno il dato (16 regioni
    # su 20, 86 province su 107): una media di sei regioni non e' la stessa
    # grandezza di una media di venti.
    need = indicator_view.panel_need(level_key)
    averages = {yr: (sum(vals.values()) / len(vals), len(vals)) for yr, vals in matrix.items() if vals}
    avg_now, avg_n = averages.get(year, (None, 0))

    selected = []
    for i, key in enumerate(state["regions"]):
        value = now.get(key)
        selected.append({
            "key": key, "name": names[key], "cls": SERIES_CLASSES[i], "value": value,
            "rank": position.get(key), "text": _with_unit(value, unit, decimals),
        })

    lines = [{"name": s["name"], "cls": s["cls"],
              "points": [(yr, matrix[yr].get(s["key"])) for yr in years]} for s in selected]
    avg_line = [(yr, averages[yr][0] if averages.get(yr, (0, 0))[1] >= need else None) for yr in years]
    chart = charts.compare_series(years, lines, avg_line, year) if len(years) > 1 else ""

    values = list(now.values())
    span = (max(values) - min(values)) or 1 if values else 1
    lo = min(values) if values else 0
    classes = {}
    for key, value in now.items():
        step = min(6, int((value - lo) / span * 6) + 1)
        classes[key] = f"q{step}" + (" is-on" if key in state["regions"] else "")
    # Un territorio a confronto senza il dato dell'anno resta contornato e
    # tratteggiato: `is-nd` dice alla mappa di dargli il motivo del n.d.
    for key in state["regions"]:
        classes.setdefault(key, "is-on is-nd")
    map_names = dict(names)
    if level_key == "provincia":
        # Anche le province senza il dato hanno un nome nel suggerimento.
        map_names = {k: info["name"] for k, info in bes_data.get_bes_territories("provincia").items()} | names

    answer = answer_text(meta["name"], year, [(s["name"], s["value"]) for s in selected],
                         avg_now, avg_n, level["plural"], unit, decimals)

    family, raw_id = sources.split_internal_id(meta["id"])
    series_rows = []
    for yr in reversed(years):
        cells = [matrix[yr].get(s["key"]) for s in selected]
        avg = averages.get(yr)
        series_rows.append({"year": yr, "cells": cells,
                            "avg": avg[0] if avg and avg[1] >= need else None})
    series_decimals = numfmt.column_decimals([v for r in series_rows for v in r["cells"] if v is not None])

    groups = province_groups(names) if level_key == "provincia" else None
    options = indicator_options(level_key)
    offered = {o["id"] for g in options for o in g["entries"]}
    others = [lv for lv in LEVELS if lv != level_key]
    tabs = [{"key": lv, "label": spec["label"], "current": lv == level_key,
             "href": level_path(lv) if lv == level_key else switch_href(lv, str(meta["id"]))}
            for lv, spec in LEVELS.items()]

    return {
        "level": level_key, "levels": LEVELS, "plural": level["plural"], "singular": level["singular"],
        "param": level["param"], "profile": level["profile"], "ordinals": ORDINALS, "tabs": tabs,
        "indicator": {
            "id": str(meta["id"]), "code": sources.indicator_code(family, raw_id), "name": meta["name"],
            "path": meta["path"], "theme": meta.get("theme"), "source_label": meta.get("source_label") or meta.get("source"),
            "source_url": meta.get("source_url"), "unit_label": meta.get("unit"),
        },
        "unit": unit, "decimals": decimals, "series_decimals": series_decimals,
        "lower_better": lower_better, "contextual": direction not in ("higher_better", *LOWER_BETTER),
        "year": year, "years": list(reversed(years)), "year_min": years[0], "year_max": years[-1],
        "territories": sorted(({"key": k, "name": v} for k, v in names.items()), key=lambda t: t["name"]),
        "groups": groups,
        "selected": selected, "max": MAX_TERRITORIES, "total": len(now),
        "avg": avg_now, "avg_n": avg_n, "avg_text": _with_unit(avg_now, unit, decimals), "need": need,
        "answer": answer, "chart": chart, "series_rows": series_rows,
        "map_classes": classes, "map_names": map_names,
        "map_values": {k: _with_unit(v, unit) for k, v in now.items()},
        # La voce n.d. si vede quando nell'anno un contorno della mappa resta
        # senza il dato: si contano i contorni, non i territori della serie.
        "legend": legend(values, unit) if values else None, "legend_nd": len(now) < len(maps.paths(level_key)),
        "options": options,
        "js": {
            "indicator": str(meta["id"]), "level": level_key, "regions": list(state["regions"]),
            "year": year, "latest": years[-1], "default": _default_js(level_key),
            "max": MAX_TERRITORIES, "need": need, "classes": list(SERIES_CLASSES),
            "plural": level["plural"], "singular": level["singular"], "param": level["param"],
            "profile": level["profile"],
            "groups": [[g["label"], [e["key"] for e in g["entries"]]] for g in groups] if groups else None,
            # Il selettore del livello: gli indicatori di questa pagina che
            # l'altro livello offre, e il suo di partenza (`switch_href`).
            "switch": {lv: {"shared": sorted(offered & level_ids(lv)), "default": default_indicator(lv)}
                       for lv in others},
        },
    }


def _default_js(level: str = DEFAULT_LEVEL) -> dict:
    """Lo stato della pagina nuda del livello, per l'isola: con quello l'URL
    resta `/confronto` (o `/confronto?livello=provincia`) senza altro."""
    state = nude_state(level)
    return {"indicator": state["indicator"], "regions": list(state["regions"]), "year": state["year"],
            "level": state["level"]}


def answer_text(name: str, year: int, values: list[tuple[str, float | None]], avg: float | None,
                avg_n: int, plural: str, unit: str, decimals: int) -> str | None:
    """La frase in testa: "PIL pro capite, 2010: Sicilia 17.290 e Veneto
    29.545 euro, contro una media semplice delle 20 regioni di 26.109 euro."

    L'unita' si scrive una volta, dopo l'ultima cifra dell'elenco, tranne il
    "%" che sta attaccato a ogni cifra. Le regioni senza il dato nell'anno non
    entrano nella frase: la tabella le dice "n.d.". `answerText` di
    confronto.js scrive la stessa frase."""
    shown = [(n, v) for n, v in values if v is not None]
    if not shown:
        return None
    parts = []
    for i, (region, value) in enumerate(shown):
        last = i == len(shown) - 1
        figure = _with_unit(value, unit, decimals) if (unit == "%" or last) else numfmt.text(value, decimals)
        parts.append(f"{region} {figure}")
    listed = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " e " + parts[-1]
    text = f"{name}, {year}: {listed}"
    if avg is not None:
        text += f", contro una media semplice delle {avg_n} {plural} di {_with_unit(avg, unit, decimals)}"
    return text + "."


def _with_unit(value, unit: str, decimals: int | None = None) -> str:
    """"1,9 giornate per abitante", "78,8%": come `common.with_unit`, con
    l'unita' gia' passata da `phrase_unit`, e come `withUnit` dell'isola."""
    if value is None:
        return "n.d."
    text = numfmt.text(value, decimals)
    if unit == "%":
        return f"{text}%"
    return f"{text} {unit}" if unit else text
