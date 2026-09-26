"""Le definizioni brevi che si aprono accanto a una parola (`ui.term` in
`v1/_ui.html`).

Sono le parole che fermano chi legge una scheda o una classifica e che la
pagina usa senza spiegarle ogni volta: "media semplice", il verso, n.d.,
"copertura variabile", il punteggio da 0 a 100. Il testo sta qui una volta
sola, cosi' la stessa parola si spiega allo stesso modo su ogni pagina, e
rimanda alla metodologia per il resto. Niente cifre: le cifre stanno nella
pagina, la definizione dice come leggerle.
"""

from __future__ import annotations

from itertools import count

TERMS: dict[str, dict[str, str]] = {
    "media-semplice": {
        "label": "media semplice",
        "text": ("La media dei valori dei territori, ognuno con lo stesso peso qualunque sia la sua "
                 "popolazione. Non è il valore nazionale calcolato sulle persone, che la fonte "
                 "pubblica a parte."),
        "href": "/metodologia",
    },
    "verso": {
        "label": "verso",
        "text": ("Dice se un valore più alto è meglio, peggio o nessuno dei due. Decide l'ordine delle "
                 "classifiche, non il colore: sulla mappa il colore segue solo la grandezza."),
        "href": "/metodologia",
    },
    "nd": {
        "label": "n.d.",
        "text": ("Dato non disponibile: la fonte non pubblica il valore per quel territorio in "
                 "quell'anno. Sulla mappa il territorio è tratteggiato."),
        "href": "/metodologia",
    },
    "copertura-variabile": {
        "label": "Copertura variabile",
        "text": ("Da un anno all'altro cambiano troppo i territori con il dato. Una media su gruppi "
                 "diversi salirebbe o scenderebbe per chi entra e chi esce, quindi la linea non si "
                 "disegna."),
        "href": "/metodologia",
    },
    "punteggio": {
        "label": "punteggio",
        "text": ("Un numero da 0 a 100 che mette insieme gli indicatori di una dimensione, ognuno col "
                 "suo verso. 50 è la media semplice dei territori: sopra si sta meglio della media, "
                 "sotto peggio. Ordina i territori, non misura il benessere."),
        "href": "/metodologia#qualita-della-vita",
    },
}

_ids = count(1)


def term(key: str) -> dict[str, str] | None:
    """La definizione di `key` con un id nuovo per il suo popover, o None."""
    entry = TERMS.get(key)
    if entry is None:
        return None
    return {**entry, "key": key, "id": f"def-{key}-{next(_ids)}"}
