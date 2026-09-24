"""L'indice della qualita' della vita della 1.0: dove si vive meglio, regioni e
province insieme.

Il contesto della rotta `/qualita-della-vita` porta solo le prime tre righe dei
due livelli, i conteggi e i profili. La pagina 1.0 chiede di piu' (prime cinque
e ultime tre, chi eccelle in ogni dimensione, fonti e anni): si leggono dal
contesto catturato, nello stesso momento, delle due classifiche, e si accettano
solo se le prime tre righe e i conteggi coincidono con quelli dell'indice. Nella
1.0 la vista dell'indice passera' la classifica intera, che gia' calcola.

Chi sale di piu' con ogni profilo si chiede all'app (`build_bes_ranking`), con
la stessa verifica sul profilo Equilibrato. I pezzi comuni alla classifica
stanno in `classifica.py`: le righe portano i punteggi grezzi, e le cifre le
scrive il template con i filtri di `numfmt`.

La pagina apre con due strisce, le regioni e le province, ognuna sulla sua
scala: i punteggi dei due livelli si calcolano separatamente e non si
confrontano. Ogni striscia ha sotto la sua tabella completa, chiusa.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import derive as helpers

PODIUM_TOP = 5
PODIUM_BOTTOM = 3


def _load_shared():
    """`classifica.py`, caricato per percorso come fa build.py con le pagine."""
    path = Path(__file__).with_name("classifica.py")
    spec = importlib.util.spec_from_file_location("proto_pages_classifica_shared", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cl = _load_shared()


def _check_preview(index_rows: list[dict], ranking: list[dict], total: int, what: str) -> None:
    """La classifica presa dall'altra cattura deve essere la stessa dell'indice."""
    head = [(r["key"], r["score"]) for r in ranking[: len(index_rows)]]
    if head != [(r["key"], r["score"]) for r in index_rows] or len(ranking) != total:
        msg = (f"La classifica catturata delle {what} non coincide con l'indice: "
               f"prime righe {head} contro {[(r['key'], r['score']) for r in index_rows]}, "
               f"{len(ranking)} righe contro {total}")
        raise ValueError(msg)


def _level_block(ctx_level: dict, level: str) -> dict:
    """Un livello del doppio podio, con le cifre che la pagina ne dice."""
    data = ctx_level["data"]
    spec = cl.LEVELS[level]
    ranking = data["ranking"]
    region_paths = ctx_level.get("region_paths") or {}
    rows = cl.table_rows(ranking, level, region_paths, with_delta=False)
    n = len(rows)
    hidden = rows[PODIUM_TOP:-PODIUM_BOTTOM] if n > PODIUM_TOP + PODIUM_BOTTOM else []
    years = cl.scored_years(level, data)
    method = data.get("methodology") or {}
    first, last = ranking[0], ranking[-1]

    def end(row):
        phrase = cl.of_place(row["name"], level)
        return {"prep": cl.split_prep(phrase, row["name"]), "name": row["name"],
                "href": spec["profile"] + row["key"], "score": row["score"]}

    return {
        "level": level, "spec": spec, "n": n, "data": data, "ranking": ranking, "rows": rows,
        "top": rows[:PODIUM_TOP], "bottom": rows[-PODIUM_BOTTOM:] if hidden else rows[PODIUM_TOP:],
        "gap_label": (f"{cl.from_to(hidden[0]['rank'], hidden[-1]['rank'])}: "
                      f"altre {len(hidden)} {spec['plural']}") if hidden else None,
        "first": end(first), "last": end(last), "gap": first["score"] - last["score"],
        "strip": cl.score_strip(ranking),
        "strip_claim": cl.south_claim(ranking, level, region_paths),
        "groups": cl.south_split(ranking, level, region_paths),
        "years": years, "years_text": cl.years_text(years), "years_span": cl.years_span(years),
        "indicators": method.get("total_indicators"),
        "institutions": method.get("catalog_institutions") or "Istat",
        "breakdown": cl.breakdown(data),
        "dims": len(cl.measured_categories(data)),
        "missing": [cl.lower_first(c["name"]) for c in cl.missing_categories(data)],
        "href": cl.BASE + spec["url"],
        "fifty": cl.mean_is_fifty(ranking),
        "claim": cl.champions_claim(data, level),
    }


def _profile_rows(ctx: dict, regions: dict, provinces: dict) -> list[dict]:
    """I profili, ognuno con il suo motivo per cliccare: chi guadagna di piu'
    rispetto a Equilibrato, fra le regioni e fra le province."""
    default = ctx.get("default_profile") or "standard"
    profiles = ctx.get("profiles") or []
    by_level = {
        "regione": cl.profile_rankings("regione", profiles, regions["ranking"]),
        "provincia": cl.profile_rankings("provincia", profiles, provinces["ranking"]),
    }
    out = []
    for p in profiles:
        motive = None
        if p["slug"] != default:
            parts = []
            for level, label in (("regione", "Fra le regioni"), ("provincia", "fra le province")):
                ranking = (by_level[level] or {}).get(p["slug"])
                if not ranking:
                    parts.append(f"{label} {helpers.PLACEHOLDER}")
                    continue
                up = cl.movers(ranking, level, denominator=f"su {len(ranking)}")["up"]
                parts.append(f"{label} {up['text']}" if up else f"{label} nessuna sale")
            motive = ", ".join(parts) + "."
        out.append({
            "name": p["name"], "description": p["description"], "default": p["slug"] == default,
            "regions": cl.profile_href("regione", p["slug"], default),
            "provinces": cl.profile_href("provincia", p["slug"], default),
            "motive": motive,
        })
    return out


def _champions(regions: dict, provinces: dict) -> list[dict]:
    """Dove eccelle ogni territorio: chi ha il punteggio piu' alto in ogni
    dimensione, fra le regioni e fra le province, con i pari merito. Le
    dimensioni senza dati provinciali restano scritte."""
    reg = cl.category_leaders(regions["data"])
    prov = cl.category_leaders(provinces["data"])
    region_paths = provinces.get("region_paths") or {}

    def cells(group, level):
        spec = cl.LEVELS[level]
        return [{"name": e["territory"], "href": spec["profile"] + e["key"], "score": e["score"],
                 "where": e.get("region") if level == "provincia" else None,
                 "where_href": region_paths.get(e.get("region") or "")} for e in group]

    out = []
    for cat in cl.measured_categories(regions["data"]):
        slug = cat["slug"]
        out.append({
            "name": cat["name"], "href": cl.category_path(slug),
            "regions": cells(reg.get(slug) or [], "regione"),
            "provinces": cells(prov.get(slug) or [], "provincia"),
        })
    return out


def derive(ctx: dict) -> dict:
    regions_ctx = cl.sibling("classifica")
    provinces_ctx = cl.sibling("classifica-province")
    _check_preview(ctx.get("preview_rows") or [], regions_ctx["data"]["ranking"], ctx.get("region_total"), "regioni")
    _check_preview(ctx.get("province_preview") or [], provinces_ctx["data"]["ranking"], ctx.get("province_total"),
                   "province")
    # region_paths viene dalla vista della classifica provinciale: e' l'unica
    # che lo calcola, e ai podi serve per il link della regione di ogni provincia.
    provinces_ctx.setdefault("region_paths", {})
    regions = _level_block(regions_ctx, "regione")
    provinces = _level_block(provinces_ctx, "provincia")

    spans = [b["years"] for b in (regions, provinces)]
    if all(spans):
        overall = {"min": min(s["min"] for s in spans), "max": max(s["max"] for s in spans)}
        years_span = f"{overall['min']}-{overall['max']}"
    else:
        years_span = helpers.PLACEHOLDER

    # Le strisce dicono estremi, media e distanza: le tessere dicono quanto
    # sta indietro il Mezzogiorno a ogni livello, e su quanti indicatori.
    tiles = []
    for b, label in ((regions, "delle regioni"), (provinces, "delle province")):
        g = b["groups"]
        if g["north"]["n"] and g["south"]["n"] and not g["unknown"]["n"]:
            tiles.append({"label": f"Mezzogiorno, media semplice {label}", "value": g["south"]["mean"], "unit": "punti",
                          "role": "score", "sub": f"contro {cl.points(g['north']['mean'])} del Centro-Nord"})
    tiles.append(cl.count_tile("Indicatori per le regioni", regions["indicators"], f"dati {regions['years_text']}"))
    tiles.append(cl.count_tile("Indicatori per le province", provinces["indicators"], f"dati {provinces['years_text']}"))
    institutions = regions["institutions"]
    default_name = next((p["name"] for p in ctx.get("profiles") or [] if p["slug"] == ctx.get("default_profile")),
                        "Equilibrato")
    downloads = {level: cl.downloads(level, ctx.get("default_profile"), ctx.get("default_profile"))
                 for level in ("regione", "provincia")}
    return {
        "regions": regions, "provinces": provinces, "levels": [regions, provinces],
        "tiles": tiles, "institutions": institutions, "area_label": cl.charts.AREA_LABEL, "years_span": years_span, "default_name": default_name,
        "profiles": _profile_rows(ctx, regions, provinces),
        "champions": _champions(regions_ctx, provinces_ctx),
        "downloads": downloads,
        "spread": cl.display_spread(),
    }
