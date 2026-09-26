"""L'indice delle province della 1.0: `/province`.

La vista passa le regioni nell'ordine geografico del sito, ognuna con le sue
province in ordine alfabetico (`province_profile.by_region`), e il totale. La
pagina ci aggiunge la ripartizione di ogni regione per il pallino, i nomi per
la mappa da cui scegliere e la frase-risposta: quante province e come si
dividono fra le regioni, contate qui dallo stesso elenco che la pagina mostra.

La posizione accanto a ogni nome e' quella della classifica della qualita'
della vita col profilo predefinito, che `by_region` porta gia': il profilo si
nomina dalla stessa classifica (`regione._province_quality`).
"""

from __future__ import annotations

from app.design import charts, common
from app.design.common import the_place
from app.design.pages import regione

_FROM = {"il ": "dal ", "l'": "dall'", "la ": "dalla ", "le ": "dalle "}
_TO = {"il ": "al ", "l'": "all'", "la ": "alla ", "le ": "alle "}


def _with_prep(name: str, preps: dict[str, str]) -> str:
    """"dalla Lombardia", "alla Valle d'Aosta": la preposizione articolata dall'articolo del nome."""
    the = the_place(name, "regione")
    for article, prep in preps.items():
        if the.startswith(article):
            return prep + the[len(article):]
    return the


def _spread(groups: list[dict]) -> dict | None:
    """La regione con piu' province e quella con meno, se sono una sola per parte."""
    if len(groups) < 2:
        return None
    sizes = [len(g["provinces"]) for g in groups]
    most, least = max(sizes), min(sizes)
    top = [g for g in groups if len(g["provinces"]) == most]
    bottom = [g for g in groups if len(g["provinces"]) == least]
    if most == least:
        return None
    return {
        "most": most, "least": least,
        "top": {"name": top[0]["name"], "from": _with_prep(top[0]["name"], _FROM), "href": top[0]["href"]}
        if len(top) == 1 else None,
        "bottom": {"name": bottom[0]["name"], "to": _with_prep(bottom[0]["name"], _TO), "href": bottom[0]["href"]}
        if len(bottom) == 1 else None,
    }


def derive(ctx: dict) -> dict:
    areas = charts.area_map()
    groups = []
    for region in ctx["regions"]:
        if not region.get("provinces"):
            continue
        key = region["region_key"]
        groups.append({
            "key": key, "id": f"regione-{key}", "name": region["region"], "href": region["path"],
            "area": areas.get(key), "provinces": region["provinces"],
        })
    quality = regione._province_quality()
    scores = {p["key"]: p["score"] for g in groups for p in g["provinces"] if p.get("score") is not None}
    total = quality.get("total") or ctx.get("total")
    return {
        # La mappa accanto all'elenco nei colori della qualita' della vita,
        # come nella testata della home: il nome sotto il mouse porta la
        # posizione, il clic apre il profilo.
        "map_steps": common.map_steps(scores) if len(scores) > 1 else None,
        "map_legend": common.legend(list(scores.values()), None) if len(scores) > 1 else None,
        "map_names": {p["key"]: (f"{p['name']}, {p['rank']}ª su {total}" if p.get("rank") and total else p["name"])
                      for g in groups for p in g["provinces"]},
        "groups": groups,
        "regions": len(groups),
        "spread": _spread(groups),
        "names": {p["key"]: p["name"] for g in groups for p in g["provinces"]},
        "quality_total": quality.get("total") or ctx.get("total"),
        "profile": quality.get("profile"),
        "area_label": charts.AREA_LABEL,
    }
