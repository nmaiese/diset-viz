"""Il confronto della 1.0: un indicatore, fino a tre regioni, reso dal server.

`/confronto` era l'ultima rotta della SPA. Adesso la pagina arriva completa
dal server: il selettore dell'indicatore e delle regioni (un `form` GET, che
senza JavaScript e' il modo di cambiare confronto), la mappa dell'anno scelto
con le regioni del confronto in evidenza, la tabella con valore e posizione,
e la serie nel tempo delle regioni scelte con la media semplice delle regioni
come riferimento. Con il JavaScript l'isola `static/js/confronto.js` cambia
indicatore, regioni e anno senza ricaricare, leggendo `/api/indicator/<id>`,
e salva i confronti sull'account.

**Lo stato vive nell'URL**, con i nomi dei parametri della SPA: `indicator`
(l'id del catalogo, `105` o `bes:10AMB014`, oppure il codice della scheda,
`ter-105`), `region` ripetuto fino a tre volte (la chiave, `lombardia`, o il
nome, `Lombardia`, come lo scriveva la SPA), `year` (anche `anno`). Un valore
che non regge si lascia cadere e vale il valore di partenza: un link vecchio
apre sempre un confronto. `livello` c'e' gia' ma conosce solo `regione`
(`LEVELS`): le province arrivano con il loro selettore, e un livello
sconosciuto vale le regioni.

Tutto cio' che la pagina scrive viene da `get_atlas_indicator`, lo stesso
payload di `/api/indicator/<id>` che l'isola legge: la pagina servita e quella
ridisegnata dal JavaScript partono dagli stessi numeri. Il ripiego non c'e':
se questo modulo cede, `design.render` risponde 500 (vedi `app/views.py`).
"""

from __future__ import annotations

import unicodedata

from app import indicator_view, sources
from app.atlas_catalog import get_atlas_catalog, get_atlas_indicator
from app.design import charts, numfmt
from app.design.common import LOWER_BETTER, legend

# I livelli che il confronto conosce. Le province (PR12) si aggiungono qui,
# con il loro insieme di territori e il loro pannello: il selettore, l'URL e
# l'isola leggono gia' `livello`.
LEVELS = {"regione": {"label": "Regioni", "plural": "regioni", "singular": "regione"}}
DEFAULT_LEVEL = "regione"

# Fino a tre regioni, come la SPA: tre linee e tre colori si leggono ancora.
MAX_TERRITORIES = 3
# Nord, Centro e Mezzogiorno, quando il link non dice altro.
DEFAULT_REGIONS = ("lombardia", "lazio", "campania")
# La palette categorica (--cat-1..3): il colore identifica una regione, non la
# giudica. Nel CSS stanno come classi `s1`..`s3`, mai scritti nel markup.
SERIES_CLASSES = ("s1", "s2", "s3")


def _norm(text: str) -> str:
    """"Valle d'Aosta" e "valle-d-aosta" si incontrano: minuscolo, senza
    accenti, con solo lettere e cifre."""
    plain = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    return "".join(ch for ch in plain.lower() if ch.isalnum())


def catalog_ids() -> set[str]:
    return {str(item["id"]) for item in get_atlas_catalog()["indicators"]}


def default_indicator() -> str:
    """L'indicatore di partenza: quello in evidenza nel catalogo, come la SPA."""
    return str(get_atlas_catalog()["featured_indicator_id"])


def indicator_id(value) -> str | None:
    """L'id del catalogo per `105`, `bes:10AMB014` o `ter-105`, o None se il
    catalogo regionale non lo ha."""
    raw = str(value or "").strip()
    if not raw:
        return None
    ids = catalog_ids()
    if raw in ids:
        return raw
    parsed = sources.parse_indicator_code(raw)
    if parsed:
        wanted = sources.internal_id(*parsed)
        if wanted in ids:
            return wanted
    return None


def _territories(payload: dict) -> dict[str, str]:
    """{chiave: nome} delle regioni che hanno almeno un valore."""
    return {row["region_key"]: row["region"] for row in payload["series"] if row["value"] is not None}


def _years(payload: dict) -> list[int]:
    return sorted({int(row["year"]) for row in payload["series"] if row["value"] is not None})


def resolve_state(args) -> dict:
    """Lo stato del confronto dall'URL, normalizzato: `level`, `indicator`
    (id del catalogo), `regions` (chiavi, al massimo tre, nell'ordine
    chiesto) e `year`. `args` e' un `MultiDict` (`request.args`) o un dict."""
    getlist = args.getlist if hasattr(args, "getlist") else (lambda k: [args[k]] if k in args else [])
    level = args.get("livello") if args.get("livello") in LEVELS else DEFAULT_LEVEL
    wanted = indicator_id(args.get("indicator") or args.get("indicatore")) or default_indicator()
    payload = get_atlas_indicator(wanted)
    if payload is None:
        raise LookupError(f"confronto: l'indicatore {wanted} non ha un payload")
    names = _territories(payload)
    by_norm = {_norm(key): key for key in names} | {_norm(name): key for key, name in names.items()}
    regions: list[str] = []
    for value in getlist("region") + getlist("regione"):
        key = by_norm.get(_norm(value))
        if key and key not in regions:
            regions.append(key)
    regions = regions[:MAX_TERRITORIES]
    if not regions:
        regions = [key for key in DEFAULT_REGIONS if key in names] or sorted(names)[:MAX_TERRITORIES]
    years = _years(payload)
    try:
        year = int(args.get("year") or args.get("anno") or 0)
    except (TypeError, ValueError):
        year = 0
    if year not in years:
        year = years[-1]
    return {"level": level, "indicator": wanted, "regions": tuple(regions), "year": year}


def is_default(state: dict) -> bool:
    """Lo stato della pagina nuda, quello che sta in cache."""
    return state == resolve_state({})


def query(state: dict) -> str:
    """La query string dello stato, vuota per la pagina nuda. L'ordine e i
    nomi sono quelli che scrive anche `confronto.js`."""
    if is_default(state):
        return ""
    payload = get_atlas_indicator(state["indicator"])
    parts = [f"indicator={state['indicator']}"]
    parts += [f"region={key}" for key in state["regions"]]
    if state["year"] != _years(payload)[-1]:
        parts.append(f"year={state['year']}")
    if state["level"] != DEFAULT_LEVEL:
        parts.append(f"livello={state['level']}")
    return "?" + "&".join(parts)


def indicator_options() -> list[dict]:
    """Il selettore dell'indicatore: aree, temi, e in ogni tema le serie per
    nome. `u` e' l'unita' come si scrive accanto a una cifra
    (`numfmt.phrase_unit`): l'isola la legge dall'opzione, perche' l'API da'
    l'etichetta della fonte ("Valori percentuali") e la pagina scrive "%"."""
    catalog = get_atlas_catalog()
    by_theme: dict[str, list[dict]] = {}
    for item in catalog["indicators"]:
        by_theme.setdefault(item["theme"], []).append({
            "id": str(item["id"]), "name": item["name"], "u": numfmt.phrase_unit(item.get("unit")) or "",
        })
    groups = []
    for area in catalog["macro_areas"]:
        for theme in area["themes"]:
            items = sorted(by_theme.pop(theme, []), key=lambda i: i["name"].lower())
            if items:
                groups.append({"label": theme, "entries": items})
    if by_theme:
        # Lo stesso guasto silenzioso dell'atlante: un tema senza area
        # toglierebbe le sue serie dal selettore senza che niente fallisca.
        raise LookupError(f"confronto: temi senza area {sorted(by_theme)}")
    return groups


def _ranked(values: dict[str, float], names: dict[str, str], lower_better: bool) -> list[str]:
    """Le chiavi dal primo all'ultimo posto. A pari valore per nome, come
    `rows` di v1.js e come l'isola."""
    return sorted(values, key=lambda k: ((values[k] if lower_better else -values[k]), names[k]))


def derive(ctx: dict) -> dict:
    state = ctx["state"]
    level = LEVELS[state["level"]]
    payload = get_atlas_indicator(state["indicator"])
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

    # La media semplice delle regioni con il dato, anno per anno. Nella serie
    # solo sugli anni in cui almeno `need` regioni hanno il dato: una media di
    # sei regioni non e' la stessa grandezza di una media di venti.
    need = indicator_view.panel_need(state["level"])
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
    for key in state["regions"]:
        classes.setdefault(key, "is-on")

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

    return {
        "level": state["level"], "levels": LEVELS, "plural": level["plural"], "singular": level["singular"],
        "indicator": {
            "id": str(meta["id"]), "code": sources.indicator_code(family, raw_id), "name": meta["name"],
            "path": meta["path"], "theme": meta.get("theme"), "source_label": meta.get("source_label") or meta.get("source"),
            "source_url": meta.get("source_url"), "unit_label": meta.get("unit"),
        },
        "unit": unit, "decimals": decimals, "series_decimals": series_decimals,
        "lower_better": lower_better, "contextual": direction not in ("higher_better", *LOWER_BETTER),
        "year": year, "years": list(reversed(years)), "year_min": years[0], "year_max": years[-1],
        "territories": sorted(({"key": k, "name": v} for k, v in names.items()), key=lambda t: t["name"]),
        "selected": selected, "max": MAX_TERRITORIES, "total": len(now),
        "avg": avg_now, "avg_n": avg_n, "avg_text": _with_unit(avg_now, unit, decimals), "need": need,
        "answer": answer, "chart": chart, "series_rows": series_rows,
        "map_classes": classes, "map_names": names,
        "map_values": {k: _with_unit(v, unit) for k, v in now.items()},
        "legend": legend(values, unit) if values else None, "legend_nd": len(now) < len(names),
        "options": indicator_options(),
        "js": {
            "indicator": str(meta["id"]), "level": state["level"], "regions": list(state["regions"]),
            "year": year, "latest": years[-1], "default": _default_js(),
            "max": MAX_TERRITORIES, "need": need, "classes": list(SERIES_CLASSES),
            "plural": level["plural"],
        },
    }


def _default_js() -> dict:
    """Lo stato della pagina nuda, per l'isola: con quello l'URL resta
    `/confronto` senza query."""
    state = resolve_state({})
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
