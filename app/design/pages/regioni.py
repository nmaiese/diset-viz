"""L'indice delle regioni della 1.0: `/regioni`.

La vista passa le venti regioni nell'ordine geografico del sito
(`profiles.regions_overview`) e quante province ha ognuna. La pagina chiede di
piu': la ripartizione di ogni regione, il tema dove va meglio e quello dove va
peggio con la posizione, e la posizione nella qualita' della vita. Non si
ricalcola niente: le frasi escono dalle stesse funzioni della pagina regione
(`regione._answer`, `regione._region_quality`, `regione._track`), cosi' la
scheda dell'indice non contraddice il profilo a cui porta, come l'anteprima
della home.

La scelta del tema per posizione, e non per percentile come `strong` e `weak`
della panoramica, e' quella di `regione._answer`: "Va peggio in Lavoro, 17ª"
accanto a una tabella con un tema 19ª era il difetto che quella funzione
chiude.
"""

from __future__ import annotations

from app import profiles
from app.design import charts
from app.design.common import the_place
from app.design.pages import regione

AREAS = ("nord", "centro", "sud")


def _quality_end(row: dict, names: dict[str, str]) -> dict:
    name = names.get(row["key"]) or row["name"]
    return {"name": name, "the_name": the_place(name, "regione"), "href": f"/regione/{row['key']}"}


def derive(ctx: dict) -> dict:
    counts = ctx.get("province_counts") or {}
    areas = charts.area_map()
    quality = regione._region_quality()
    ranks = quality["ranks"] if quality else {}
    q_total = len(ranks) or None

    cards = []
    for entry in ctx["regions"]:
        key = entry["region_key"]
        area = areas.get(key)
        if area not in AREAS:
            raise LookupError(f"regione {key!r}: nessuna ripartizione")
        profile = profiles.region_profile(key)
        answer = regione._answer(profile) if profile else {}
        rank = ranks.get(key)
        cards.append({
            "key": key, "name": entry["region"], "href": entry["path"], "area": area,
            "provinces": counts.get(key),
            "strong": answer.get("strong"), "weak": answer.get("weak"),
            "quality_rank": rank, "quality_track": regione._track(rank, q_total),
        })

    groups = [{"area": a, "label": charts.AREA_LABEL[a], "id": f"ripartizione-{a}",
               "regions": [c for c in cards if c["area"] == a]} for a in AREAS]
    groups = [g for g in groups if g["regions"]]

    names = {c["key"]: c["name"] for c in cards}
    first = last = None
    if quality:
        first = _quality_end(quality["rows"][0], names)
        last = _quality_end(quality["rows"][-1], names)

    return {
        "n": len(cards),
        "groups": groups,
        "area_counts": [{"label": g["label"], "count": len(g["regions"])} for g in groups],
        "names": names,
        "quality": {"first": first, "last": last, "total": q_total,
                    "profile": quality.get("profile") if quality else None} if first else None,
    }
