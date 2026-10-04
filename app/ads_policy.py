"""La regola degli annunci: dove un'unita' pubblicitaria potra' comparire.

Oggi il sito carica solo il loader AdSense (`_third_party_head.html`), nessuna
unita' `<ins class="adsbygoogle">`. Quando arriveranno, il posto per decidere
se mostrare o no un'annuncio e' questa funzione, una sola, e non una condizione
sparsa nei template: AdSense rifiuta un sito anche per annunci su schermate
senza contenuto editoriale, quindi la regola e' conservativa.

`page` e' il tipo di pagina (`app/page_types.page_type`): lo stesso valore che
il page_view manda a GA4. `word_count` e' il numero di parole di testo
editoriale della pagina; quando non si sa, la regola spegne gli annunci invece
di rischiare.
"""

from __future__ import annotations

# Un articolo del blog e' contenuto editoriale per definizione, anche se corto.
EDITORIAL_ALWAYS = frozenset({"blog"})

# Schermate di interfaccia, mai con annunci: niente testo editoriale da
# accompagnare, e sono proprio il caso che AdSense non vuole.
INTERFACE = frozenset({"atlas", "search", "game", "account", "legacy", "error"})

# La soglia di testo editoriale sotto cui una pagina non porta annunci.
MIN_WORDS = 500


def ads_allowed(page: str, word_count: int | None = None) -> bool:
    """Vera solo per articoli e pagine con almeno `MIN_WORDS` parole editoriali.

    Falsa per le interfacce (quiz, atlante, confronto, ricerca), per le pagine
    sotto soglia e per quelle di cui non si sa il numero di parole.
    """
    if page in INTERFACE:
        return False
    if page in EDITORIAL_ALWAYS:
        return True
    if word_count is None:
        return False
    return word_count >= MIN_WORDS
