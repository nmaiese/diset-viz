"""La ricerca interna della 1.0: il campo in testa, i risultati per tipo.

La vista (`ricerca` in app/views.py) trova, ordina, filtra per `?tipo=` e
taglia la pagina: qui si compone solo cio' che la regia chiede in piu' a quelle
righe. I risultati della pagina si raggruppano per tipo nell'ordine della
vista (territori, temi, indicatori, articoli), il termine cercato e i suoi
sinonimi si evidenziano con `<mark>` sul testo gia' escapato, il filtro per
tipo e la paginazione numerata sono link veri.
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlencode

from markupsafe import Markup, escape

from app.design.common import date_it

# Quante pagine attorno a quella corrente mostra la paginazione, oltre alla
# prima e all'ultima.
PAGER_SPAN = 2

# Le domande d'esempio della pagina vuota: una per tipo di risultato.
EXAMPLES = ("Lecce", "Puglia", "lavoro", "speranza di vita", "reddito")


def _fold_char(ch: str) -> str:
    if ch.isspace():
        return " "
    return unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode("ascii").lower()


def highlight(text: str | None, terms: list[str]) -> Markup:
    """`text` escapato, con ogni occorrenza di `terms` dentro `<mark>`.

    Il confronto avviene sulla forma piegata (minuscolo, senza accenti) come
    nella ricerca, ma si marca il testo originale: ogni carattere piegato
    ricorda da quale carattere viene. Il primo termine e' la query, che vale
    ovunque; gli altri sono i sinonimi, che valgono come inizio di parola.
    Si escapa ogni pezzo prima di unirlo ai `<mark>`, quindi il testo della
    riga e la query non entrano mai nel markup come HTML.
    """
    text = text or ""
    folded_chars: list[str] = []
    origin: list[int] = []
    for index, ch in enumerate(text):
        for folded in _fold_char(ch):
            folded_chars.append(folded)
            origin.append(index)
    folded = "".join(folded_chars)

    spans: list[tuple[int, int]] = []
    for position, term in enumerate(t for t in terms if t):
        prefix = "" if position == 0 else r"(?<![a-z0-9])"
        for match in re.finditer(prefix + re.escape(term), folded):
            spans.append((origin[match.start()], origin[match.end() - 1] + 1))
    if not spans:
        return Markup(escape(text))

    merged: list[list[int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    out = []
    cursor = 0
    for start, end in merged:
        out.append(escape(text[cursor:start]))
        out.append(Markup("<mark>") + escape(text[start:end]) + Markup("</mark>"))
        cursor = end
    out.append(escape(text[cursor:]))
    return Markup("").join(out)


def search_href(query: str, kind: str = "", page: int = 1) -> str:
    params = [("q", query)]
    if kind:
        params.append(("tipo", kind))
    if page > 1:
        params.append(("pagina", page))
    return "/ricerca?" + urlencode(params)


def pager(query: str, kind: str, page: int, pages: int) -> dict | None:
    """Le pagine numerate: la prima, l'ultima e due per parte attorno a quella
    corrente, con un salto dove ne mancano."""
    if pages <= 1:
        return None
    shown = sorted({1, pages, *range(max(1, page - PAGER_SPAN), min(pages, page + PAGER_SPAN) + 1)})
    items = []
    previous = 0
    for n in shown:
        if n - previous > 1:
            items.append({"gap": True})
        items.append({"n": n, "href": search_href(query, kind, n), "current": n == page})
        previous = n
    return {
        "items": items,
        "prev": search_href(query, kind, page - 1) if page > 1 else None,
        "next": search_href(query, kind, page + 1) if page < pages else None,
    }


def _row(row: dict, terms: list[str]) -> dict:
    return {
        **row,
        "title_html": highlight(row["title"], terms),
        "summary_html": highlight(row["summary"], terms) if row.get("summary") else None,
        "date_label": date_it(row.get("date")),
    }


def derive(ctx: dict) -> dict:
    query = ctx.get("query") or ""
    kind = ctx.get("kind_param") or ""
    counts = ctx.get("kind_counts") or {}
    kinds = ctx.get("search_kinds") or ()
    terms = ctx.get("highlight_terms") or []

    seg = []
    if query and ctx.get("all_total"):
        seg.append({"label": "Tutti", "count": ctx["all_total"], "href": search_href(query), "current": not kind})
        for param, _row_kind, label in kinds:
            if counts.get(param) or param == kind:
                seg.append({"label": label, "count": counts.get(param, 0),
                            "href": search_href(query, param), "current": param == kind})

    groups = []
    rows = ctx.get("results") or []
    for param, row_kind, label in kinds:
        members = [_row(row, terms) for row in rows if row["kind"] == row_kind]
        if not members:
            continue
        total = counts.get(param, len(members))
        groups.append({
            "param": param,
            "kind": row_kind,
            "label": label,
            "count": total,
            "rows": members,
            # Il link al tipo intero, quando nella pagina "Tutti" se ne vede solo una parte.
            "more": search_href(query, param) if not kind and total > len(members) else None,
        })

    from app import province_profile
    from app.blog import get_posts
    from app.data import REGION_ORDER
    from app.atlas_catalog import atlas_themes_by_macro_area

    # Accanto ai risultati, da 960, la mappa per andare a una regione, nei
    # colori della qualita' della vita come nella testata della home: chi
    # cerca un luogo ci arriva con un clic, e la colonna non resta vuota.
    from app.design.pages import home

    names = home.region_names()
    nav_map = home.hero_map(names)
    return {
        "nav_map": nav_map, "region_names": names,
        "seg": seg,
        "groups": groups,
        "pager": pager(query, kind, ctx.get("page_number") or 1, ctx.get("pages") or 1),
        "kind_label": next((label for param, _k, label in kinds if param == kind), None),
        "examples": [{"label": text, "href": search_href(text)} for text in EXAMPLES],
        "scope": {
            "regions": len(REGION_ORDER),
            "provinces": province_profile.total(),
            "themes": sum(len(area["themes"]) for area in atlas_themes_by_macro_area()),
            "posts": len(get_posts()),
        },
    }
