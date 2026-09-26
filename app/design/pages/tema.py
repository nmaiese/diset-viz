"""La pagina di un tema della 1.0 (`/tema/<slug>`).

La vista passa il profilo del tema (`get_atlas_theme_profile`), la classifica
delle regioni sul tema (`profiles.theme_standings`), i colori della mappa, i
temi fratelli, gli indicatori in evidenza (`views._theme_featured`) e le schede
del tema con i valori delle province. Qui si compone solo cio' che la pagina
chiede in piu' a quei dati, con le funzioni che le altre pagine gia' usano:

- la classifica come la legge la classifica della qualita' della vita
  (`classifica.map_block` per mappa, soglie e richiami, `classifica.score_strip`
  per la striscia), sul punteggio del tema portato da 0-1 a 0-100;
- l'andamento di ogni serie dalle righe dell'atlante (`atlante.rows`), la
  sparkline della media semplice sul pannello fisso e la variazione in chiaro,
  cosi' la pagina tema e l'atlante dicono la stessa cosa della stessa serie;
- l'elenco di tutte le serie, raggruppato per sottotema della fonte quando il
  tema ne raccoglie piu' d'uno.

Nessuna cifra si ricalcola: le posizioni, i punteggi e i conteggi sono quelli
che la vista gia' passa.
"""

from __future__ import annotations

from app.design import charts
from app.design.pages import atlante
from app.design.pages import classifica as cl

# Le regioni agli estremi in "Continua da qui": le prime tre e le ultime due,
# come la pagina di prima.
HEAD = 3
TAIL = 2


def _ranking(standings: dict, map_colors: dict) -> list[dict]:
    """Le righe della classifica del tema, nella forma che leggono
    `classifica.map_block` e `classifica.score_strip`: punteggio da 0 a 100."""
    areas = charts.area_map()
    out = []
    for row in standings.get("rows") or []:
        score = row["score"] * 100
        out.append({
            "rank": row["rank"], "key": row["region_key"], "name": row["region"], "href": row["path"],
            "score": score, "width": cl.bar_width(score), "area": areas.get(row["region_key"]),
            "color": map_colors.get(row["region_key"]), "best": row.get("best_indicator"),
        })
    return out


def _claim(ranking: list[dict]) -> str | None:
    """Il titolo-affermazione della striscia, solo quando e' la forma che non
    dipende dalla scala ("occupano le ultime otto posizioni"): la soglia di 50
    della qualita' della vita qui non e' la media."""
    text = cl.south_claim(ranking, "regione", {})
    return text if text and "ultime" in text else None


def _theme_rows(theme: str) -> dict[str, dict]:
    """Le righe dell'atlante del tema, per percorso della scheda."""
    for area in atlante.rows("regione")["areas"]:
        for group in area["groups"]:
            if group["name"] == theme:
                return {row["path"]: row for row in group["rows"]}
    return {}


def _item(ind: dict, rows: dict, province_links: dict) -> dict:
    """Una serie del tema con cio' che ne dice l'atlante."""
    row = rows.get(ind["path"]) or {}
    return {
        "name": ind["name"], "path": ind["path"], "plain": ind.get("plain"),
        "y0": ind["year_min"], "y1": ind["year_max"], "n": ind.get("region_count"),
        "complete": bool(ind.get("complete")), "scored": bool(ind.get("quality_life_scored")),
        "source_theme": ind.get("source_theme"),
        "spark": row.get("spark") or "", "change": row.get("change"),
        # La vista provinciale: quella che l'atlante gia' trova (anche la
        # gemella), o la voce della sezione "Per provincia" della stessa scheda.
        "also": row.get("also") or province_links.get(ind["path"]),
    }


def _groups(items: list[dict], theme: str) -> list[dict]:
    """Le serie per sottotema della fonte, nell'ordine in cui il profilo le
    elenca (prima le complete, poi per nome). Un sottotema solo, o uguale al
    tema, non fa un gruppo: resta un elenco."""
    groups: dict[str, list[dict]] = {}
    for item in items:
        groups.setdefault(item["source_theme"] or theme, []).append(item)
    if len(groups) < 2:
        return [{"name": None, "series": items}]
    return [{"name": name, "series": group}
            for name, group in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))]


def derive(ctx: dict) -> dict:
    profile = ctx["profile"]
    standings = ctx.get("standings") or {}
    rated = bool(standings.get("rated") and standings.get("rows"))
    ranking = _ranking(standings, ctx.get("map_colors") or {}) if rated else []
    rows = _theme_rows(profile["theme"])
    province_links = {item["canonical_path"]: item["path"] for item in ctx.get("province_indicators") or []
                      if item["path"] != item["canonical_path"]}
    items = [_item(ind, rows, province_links) for ind in profile["indicators"]]
    by_path = {item["path"]: item for item in items}
    featured = [by_path[ind["path"]] for ind in ctx.get("featured") or [] if ind["path"] in by_path]
    years = [item["y1"] for item in items if item["y1"]]
    first_years = [item["y0"] for item in items if item["y0"]]

    tiles = [
        {"label": "Indicatori", "value": profile["indicator_count"], "role": "count",
         "sub": "serie per regione"},
        {"label": "Completi", "value": profile["complete_count"], "role": "count",
         "sub": "con tutte le regioni"},
        {"label": "Nella qualità della vita", "value": profile["quality_life_count"], "role": "count",
         "sub": "entrano nel punteggio", "href": "/qualita-della-vita"},
        {"label": "Ultimo anno", "num": str(max(years)) if years else "n.d.",
         "sub": f"primo dato nel {min(first_years)}" if first_years else None},
    ]

    first = ranking[0] if ranking else None
    last = ranking[-1] if ranking else None
    return {
        "rated": rated,
        "ranking": ranking,
        "first": first, "last": last,
        "gap": (first["score"] - last["score"]) if first else None,
        "map": cl.map_block(ranking) if ranking else None,
        "strip": cl.score_strip(ranking) if ranking else {"svg": "", "legend": []},
        "claim": _claim(ranking) if ranking else None,
        "area_label": charts.AREA_LABEL,
        "tiles": tiles,
        "years_span": f"{min(first_years)}-{max(years)}" if years and first_years else None,
        "featured": featured,
        "featured_odd": len(featured) % 2 == 1,
        "groups": _groups(items, profile["theme"]),
        "total": len(items),
        "with_spark": sum(1 for item in items if item["spark"]),
        "ends": ([*ranking[:HEAD], *ranking[-TAIL:]] if len(ranking) > HEAD + TAIL else ranking),
    }
