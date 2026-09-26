"""Il tipo di pagina che il page_view manda a GA4 (`page_type`).

Fino al 26 settembre 2026 il frammento del page_view (`_third_party_head.html`)
sapeva dire solo "atlas" (atlante e confronto, che lo dichiarano nel template),
"blog" (un prefisso) e "server" per tutto il resto: home, schede, regioni,
province, temi, qualita' della vita e quiz finivano nello stesso valore, e la
dimensione personalizzata `page_type` in GA4 non distingueva niente.

La classificazione sta qui, una sola, e si decide sul percorso, perche' vale
anche per il ripiego di `design.render` e per le pagine che non passano dalla
regia della 1.0 (quiz, pagine di fiducia). Un template che dichiara
`PAGE_TYPE` vince: e' il caso della 404, che su qualunque percorso e' "error".

I valori restano quelli di prima dove c'erano ("atlas" per atlante e
confronto, "blog", "game" come gia' dicono gli eventi del quiz), cosi' la serie
storica di quelle pagine non si spezza. `docs/tracking_spec.md` li elenca.
"""

from __future__ import annotations

# (prefisso, tipo): il primo che combacia vince. Un prefisso con la barra finale
# vale per le pagine sotto di lui, uno senza per il percorso esatto e per le
# pagine sotto ("/blog" copre "/blog" e "/blog/<slug>", non "/blogxyz").
_PREFIXES: tuple[tuple[str, str], ...] = (
    ("/indicatore", "indicator"),
    ("/regione", "region"),
    ("/regioni", "region"),
    ("/provincia", "province"),
    ("/province", "province"),
    ("/atlante", "atlas"),
    ("/confronto", "atlas"),
    ("/tema", "theme"),
    ("/temi", "theme"),
    ("/blog", "blog"),
    ("/qualita-della-vita", "quality_of_life"),
    ("/quiz", "game"),
    ("/gioco", "game"),
    ("/ricerca", "search"),
    ("/divari-regionali", "hub"),
    ("/catalogo-dati", "hub"),
    ("/metodologia", "info"),
    ("/chi-siamo", "info"),
    ("/contatti", "info"),
    ("/termini", "info"),
    ("/privacy", "info"),
    ("/account", "account"),
    ("/legacy", "legacy"),
    ("/legacy-reddito", "legacy"),
)

PAGE_TYPES: frozenset[str] = frozenset({"home", "error", "other"} | {kind for _, kind in _PREFIXES})


def page_type(path: str) -> str:
    """Il `page_type` di un percorso. "other" per cio' che non e' classificato."""
    if path == "/":
        return "home"
    for prefix, kind in _PREFIXES:
        if path == prefix or path.startswith(prefix + "/"):
            return kind
    return "other"
