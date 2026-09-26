"""L'indice dei temi della 1.0 (`/temi`).

La vista passa le aree coi loro temi (`views._themes_index_areas`: conteggi,
gli indicatori con cui la pagina del tema apre, la regione in testa e quella
in coda), i totali del catalogo dell'atlante e il conto delle schede con i
valori delle province. Qui si aggiunge solo il distintivo di ogni area, lo
stesso della fascia `#temi` della home (`home.AREA_LOOK`), e il link al
profilo delle regioni nominate in testa e in coda.
"""

from __future__ import annotations

from app.design.pages.home import AREA_LOOK, region_names

# Quanti indicatori una scheda di tema nomina: il resto sta un clic piu' in la'.
EXAMPLES = 3


def _region(name: str | None, keys: dict[str, str]) -> dict | None:
    """Una regione nominata, col link al suo profilo quando e' una regione vera."""
    if not name:
        return None
    key = keys.get(name)
    return {"name": name, "href": f"/regione/{key}" if key else None}


def derive(ctx: dict) -> dict:
    keys = {name: key for key, name in region_names().items()}
    areas = []
    for area in ctx.get("areas") or []:
        themes = []
        for theme in area["themes"]:
            examples = theme.get("featured", [])[:EXAMPLES]
            themes.append({
                **theme,
                "examples": examples,
                "more": theme["indicator_count"] - len(examples),
                "head": _region(theme.get("lead"), keys),
                "tail": _region(theme.get("lag"), keys),
            })
        areas.append({
            **area,
            **AREA_LOOK.get(area["area"], {"icon": "catalog", "tone": "neutral"}),
            "themes": themes,
        })
    return {
        "areas": areas,
        "area_count": len(areas),
        "ranked": sum(1 for area in areas for theme in area["themes"] if theme["head"]),
    }
