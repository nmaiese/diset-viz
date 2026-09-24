"""L'indice della qualita' della vita della 1.0: dove si vive meglio, regioni e
province insieme.

La vista dell'indice passa solo le prime tre righe dei due livelli, i conteggi
e i profili. La pagina chiede di piu' (prime cinque e ultime tre, chi eccelle
in ogni dimensione, fonti e anni, chi sale con ogni profilo): si chiede tutto
all'app, `quality_life_bes.build_bes_ranking`, la stessa funzione da cui la
vista prende l'anteprima. E' memoizzata in `app.cache`, quindi le dodici
classifiche (sei profili per due livelli) si calcolano una volta e non a ogni
richiesta.

I pezzi comuni alla classifica stanno in `classifica.py`: le righe portano i
punteggi grezzi, e le cifre le scrive il template con i filtri di `numfmt`.

La pagina apre con due strisce, le regioni e le province, ognuna sulla sua
scala: i punteggi dei due livelli si calcolano separatamente e non si
confrontano. Ogni striscia ha sotto la sua tabella completa, chiusa. Un
livello senza dati toglie le sue parti, non la pagina.
"""

from __future__ import annotations

from app.design import charts
from app.design.pages import classifica as cl

PODIUM_TOP = 5
PODIUM_BOTTOM = 3
LEVEL_KEYS = ("regione", "provincia")


def _ranking(level: str, slug: str) -> dict | None:
    """La classifica di un livello con un profilo, o None se il livello non ha dati."""
    from app.quality_life_bes import build_bes_ranking

    data = build_bes_ranking(level, slug)
    return data if data and data.get("ranking") else None


def _level_block(level: str, default: str) -> dict | None:
    """Un livello del doppio podio, con le cifre che la pagina ne dice."""
    data = _ranking(level, default)
    if data is None:
        return None
    spec = cl.LEVELS[level]
    ranking = data["ranking"]
    # I percorsi delle regioni li calcola la vista della classifica, non
    # quella dell'indice: qui si rifanno con la stessa regola.
    paths = cl.region_paths(ranking) if level == "provincia" else {}
    rows = cl.table_rows(ranking, level, paths, with_delta=False)
    n = len(rows)
    hidden = rows[PODIUM_TOP:-PODIUM_BOTTOM] if n > PODIUM_TOP + PODIUM_BOTTOM else []
    years = cl.scored_years(level, data)
    method = data.get("methodology") or {}
    institutions = method.get("catalog_institutions") or "Istat"
    span = cl.years_span(years)
    return {
        "level": level, "spec": spec, "n": n, "data": data, "ranking": ranking, "rows": rows,
        "region_paths": paths,
        "top": rows[:PODIUM_TOP], "bottom": rows[-PODIUM_BOTTOM:] if hidden else rows[PODIUM_TOP:],
        "gap_label": (f"{cl.from_to(hidden[0]['rank'], hidden[-1]['rank'])}: "
                      f"altre {len(hidden)} {spec['plural']}") if hidden else None,
        "first": cl.end(ranking[0], level), "last": cl.end(ranking[-1], level),
        "strip": cl.score_strip(ranking),
        "strip_claim": cl.south_claim(ranking, level, paths),
        "groups": cl.south_split(ranking, level, paths),
        "years": years, "years_text": cl.years_text(years), "years_span": span,
        "indicators": method.get("total_indicators"),
        "institutions": institutions, "source_ref": cl.source_ref(institutions, span),
        "breakdown": cl.breakdown(data),
        "dims": len(cl.measured_categories(data)),
        "missing": [cl.lower_first(c["name"]) for c in cl.missing_categories(data)],
        "href": cl.BASE + spec["url"],
        "fifty": cl.mean_is_fifty(ranking),
        "claim": cl.champions_claim(data, level),
    }


def _profile_rows(profiles: list[dict], default: str, blocks: dict) -> list[dict]:
    """I profili, ognuno con il suo motivo per cliccare: chi guadagna di piu'
    rispetto a Equilibrato, fra le regioni e fra le province. Un livello senza
    classifica toglie la sua meta' della frase."""
    by_level = {level: cl.profile_rankings(level, profiles) for level in LEVEL_KEYS if blocks.get(level)}
    out = []
    for p in profiles:
        motive = None
        if p["slug"] != default:
            parts = []
            for level, label in (("regione", "fra le regioni"), ("provincia", "fra le province")):
                ranking = (by_level.get(level) or {}).get(p["slug"])
                if not ranking:
                    continue
                up = cl.movers(ranking, level, denominator=f"su {len(ranking)}")["up"]
                parts.append(f"{label} {up['text']}" if up else f"{label} nessuna sale")
            if parts:
                text = ", ".join(parts) + "."
                motive = text[:1].upper() + text[1:]
        out.append({
            "name": p["name"], "description": p.get("description"), "default": p["slug"] == default,
            "regions": cl.profile_href("regione", p["slug"], default),
            "provinces": cl.profile_href("provincia", p["slug"], default),
            "motive": motive,
        })
    return out


def _champions(regions: dict | None, provinces: dict | None) -> list[dict]:
    """Dove eccelle ogni territorio: chi ha il punteggio piu' alto in ogni
    dimensione, fra le regioni e fra le province, con i pari merito. Le
    dimensioni senza dati provinciali restano scritte."""
    if not regions:
        return []
    reg = cl.category_leaders(regions["data"])
    prov = cl.category_leaders(provinces["data"]) if provinces else {}
    paths = (provinces or {}).get("region_paths") or {}

    def cells(group, level):
        spec = cl.LEVELS[level]
        return [{"name": e["territory"], "href": spec["profile"] + e["key"], "score": e["score"],
                 "where": e.get("region") if level == "provincia" else None,
                 "where_href": paths.get(e.get("region") or "")} for e in group]

    out = []
    for cat in cl.measured_categories(regions["data"]):
        slug = cat["slug"]
        out.append({
            "name": cat["name"], "href": cl.safe_category_path(slug),
            "regions": cells(reg.get(slug) or [], "regione"),
            "provinces": cells(prov.get(slug) or [], "provincia"),
        })
    return out


def derive(ctx: dict) -> dict:
    default = ctx.get("default_profile") or "standard"
    profiles = ctx.get("profiles") or []
    regions = _level_block("regione", default)
    provinces = _level_block("provincia", default) if ctx.get("has_province_data", True) else None
    blocks = {"regione": regions, "provincia": provinces}
    levels = [b for b in (regions, provinces) if b]

    spans = [b["years"] for b in levels]
    years_span = None
    if spans and all(spans):
        lo, hi = min(s["min"] for s in spans), max(s["max"] for s in spans)
        years_span = str(lo) if lo == hi else f"{lo}-{hi}"

    # Le strisce dicono estremi, media e distanza: le tessere dicono quanto
    # sta indietro il Mezzogiorno a ogni livello, e su quanti indicatori.
    tiles = []
    for b in levels:
        g = b["groups"]
        if g["north"]["n"] and g["south"]["n"] and not g["unknown"]["n"]:
            tiles.append({"label": f"Mezzogiorno, media semplice delle {b['spec']['plural']}", "value": g["south"]["mean"],
                          "unit": "punti", "role": "score",
                          "sub": f"contro {cl.points(g['north']['mean'])} del Centro-Nord"})
    for b in levels:
        tile = cl.count_tile(f"Indicatori per le {b['spec']['plural']}", b["indicators"],
                             f"dati {b['years_text']}" if b["years_text"] else None)
        if tile:
            tiles.append(tile)

    institutions = (regions or provinces or {}).get("institutions") or "Istat"
    default_name = next((p["name"] for p in profiles if p["slug"] == default), "Equilibrato")
    return {
        "regions": regions, "provinces": provinces, "levels": levels,
        "counts": " e ".join(f"{b['n']} {b['spec']['plural']}" for b in levels),
        "fifty": bool(levels) and all(b["fifty"] for b in levels),
        "tiles": tiles, "institutions": institutions, "area_label": charts.AREA_LABEL,
        "years_span": years_span, "source_ref": cl.source_ref(institutions, years_span),
        "default_name": default_name,
        "profiles": _profile_rows(profiles, default, blocks),
        "champions": _champions(regions, provinces),
        "downloads": {level: cl.downloads(level, default, default) for level in LEVEL_KEYS if blocks.get(level)},
        "spread": cl.display_spread(),
    }
