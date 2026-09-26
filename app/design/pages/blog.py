"""L'indice delle storie della 1.0: la piu' recente grande, le altre in schede.

La vista (`blog_index` in app/views.py) passa i post gia' in ordine, dal piu'
recente, e i tag con i loro conteggi. Qui si compone cio' che la pagina chiede
in piu': la scheda di ogni storia (la stessa della fascia storie della home,
`home.story`, con la data scritta per esteso e le misure della copertina),
la frase in testa con il numero delle storie e la data dell'ultima, e l'indice
per tema. La vista non filtra per tag: il filtro sono ancore verso le sezioni
dell'indice in fondo alla pagina, link veri che funzionano senza JavaScript.
"""

from __future__ import annotations

import re
import unicodedata

from app.design.common import date_it
from app.design.pages.home import story

# I tag che dicono l'anno dei dati ("Dati 2024") non sono un tema.
YEAR_TAG = re.compile(r"^Dati \d{4}$")

# Quanti temi si offrono in testa come filtro: quelli con piu' storie. Gli
# altri stanno nell'indice per tema, a un'ancora di distanza.
TOP_TAGS = 4


def tag_slug(tag: str) -> str:
    """"Divario Nord-Sud" -> "tema-divario-nord-sud": l'ancora della sezione."""
    folded = unicodedata.normalize("NFKD", tag).encode("ascii", "ignore").decode("ascii").lower()
    return "tema-" + re.sub(r"[^a-z0-9]+", "-", folded).strip("-")


def derive(ctx: dict) -> dict:
    posts = list(ctx.get("posts") or [])
    stories = [story(p) for p in posts]
    for s, p in zip(stories, posts):
        s["tags"] = [{"name": t, "anchor": tag_slug(t)} for t in (p.get("tags") or []) if not YEAR_TAG.match(t)]

    by_tag: dict[str, list[dict]] = {}
    for s in stories:
        for t in s["tags"]:
            by_tag.setdefault(t["name"], []).append(s)
    # L'indice tiene i temi con almeno due storie: un tema con una storia
    # sola ripete una scheda che sta gia' in "Tutte le storie".
    index = [{"name": name, "anchor": tag_slug(name), "stories": items}
             for name, items in sorted(by_tag.items(), key=lambda kv: (-len(kv[1]), kv[0].lower()))
             if len(items) > 1]

    latest = posts[0]["date"].isoformat() if posts else None
    return {
        "lead": stories[0] if stories else None,
        "rest": stories[1:],
        "count": len(stories),
        "latest": latest,
        "latest_label": date_it(latest),
        "top_tags": index[:TOP_TAGS],
        "index": index,
    }
