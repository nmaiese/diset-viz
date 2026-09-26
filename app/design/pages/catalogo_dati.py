"""Il catalogo dati della 1.0: le stesse voci, per tema, con un filtro.

La vista passa le voci del catalogo (`datasets`, la stessa proiezione di
sitemap e llms-full) con il tema e i file scaricabili di ognuna, e il JSON-LD
`DataCatalog` gia' composto, che qui non si tocca. Qui si compongono le cifre
della testata (voci, voci scaricabili, temi, istituzioni) e i gruppi: un tema
per gruppo, nell'ordine delle macro-aree dell'atlante e poi dei temi, le voci
in ordine alfabetico. Un tema che l'atlante non conosce va in coda, in ordine
alfabetico, e una voce senza tema in un gruppo "Altri indicatori": nessuna
voce resta fuori dalla pagina, perche' ognuna e' un `Dataset` del grafo e
deve avere il suo link visibile.
"""

from __future__ import annotations

from app.atlas_catalog import atlas_themes_by_macro_area

OTHER = "Altri indicatori"


def _theme_order() -> dict[str, dict]:
    """Tema -> posizione, macro-area e pagina, dall'atlante."""
    order: dict[str, dict] = {}
    for area in atlas_themes_by_macro_area():
        for theme in area["themes"]:
            order[theme["theme"]] = {"pos": len(order), "area": area["macro_area"], "path": theme["path"]}
    return order


def _institution(source: str) -> str:
    """"Istat, Banca dati territoriale..." -> "Istat"."""
    return source.split(",", 1)[0].strip()


def groups(datasets: list[dict], order: dict[str, dict]) -> list[dict]:
    by_theme: dict[str, list[dict]] = {}
    for item in datasets:
        by_theme.setdefault(item.get("theme") or OTHER, []).append(item)
    known = [name for name in by_theme if name in order]
    unknown = sorted((name for name in by_theme if name not in order and name != OTHER), key=str.casefold)
    names = sorted(known, key=lambda name: order[name]["pos"]) + unknown
    if OTHER in by_theme:
        names.append(OTHER)
    result = []
    for index, name in enumerate(names, start=1):
        items = sorted(by_theme[name], key=lambda item: item["name"].casefold())
        info = order.get(name) or {}
        result.append({
            "id": f"tema-{index}",
            "name": name,
            "area": info.get("area"),
            "path": info.get("path") or (items[0].get("theme_path") if name != OTHER else None),
            "items": items,
            "downloadable": sum(1 for item in items if item.get("downloadable")),
        })
    return result


def derive(ctx: dict) -> dict:
    datasets = ctx["datasets"]
    institutions: list[str] = []
    sources: set[str] = set()
    for item in datasets:
        source = item.get("source") or ""
        if not source:
            continue
        sources.add(source.casefold())
        name = _institution(source)
        if name and name not in institutions:
            institutions.append(name)
    # Istat prima: e' la fonte di quasi tutte le voci.
    institutions.sort(key=lambda name: (name != "Istat", name))
    grouped = groups(datasets, _theme_order())
    return {
        "total": len(datasets),
        "downloadable": sum(1 for item in datasets if item.get("downloadable")),
        "themes": sum(1 for g in grouped if g["name"] != OTHER),
        "sources": len(sources),
        "institutions": institutions,
        "groups": grouped,
    }
