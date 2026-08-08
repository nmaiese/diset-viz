"""Quale testo vero mettere davanti a chi scrive, deciso dai dati.

`content/esempi/` esiste perché il progetto aveva trenta divieti e zero
esempi, e gli articoli rispettavano ogni divieto senza somigliare a niente. Il
README di quella cartella lo dice per primo, e dice anche la regola d'uso:
**uno per articolo, non tutti**, perché mediarne otto produce l'assenza di
registro, che è il punto di partenza.

Restava un pezzo scoperto: *quale*. Sceglierlo era lasciato al modello, e un
modello che sceglie da solo sceglie quasi sempre lo stesso, così come sceglieva
quasi sempre la stessa apertura. Qui l'esempio lo decide **l'angolo vincente**
del pacchetto: una serie che cambia regime prende il modello che racconta il
tempo, una graduatoria spezzata prende quello che legge una classifica dal
primo, un territorio fuori scala prende quello che apre sul luogo invece che
sulla cifra.

La mappa non è un'opinione sul bello: è l'accoppiamento fra la forma della
storia trovata nei dati e la forma di storia che quell'estratto sa fare, ed è
la colonna "forma di storia" del README a dirlo.
"""
from __future__ import annotations

import os

ESEMPI_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content", "esempi")

# angolo -> estratto. Il commento accanto è la colonna "forma di storia" del
# README: se la mappa e l'indice divergono, è l'indice ad avere ragione.
BY_ANGLE = {
    # il tempo che risponde a una domanda: le storie che stanno nella serie
    "rottura-di-pendenza": "lavoce-decentramento-storico.md",
    "accelerazione": "lavoce-decentramento-storico.md",
    "rallentamento": "lavoce-decentramento-storico.md",
    "ritorno-al-livello": "lavoce-decentramento-storico.md",
    # perché due grandezze divergono: le storie che stanno fra i territori
    "divario-che-si-allarga": "lavoce-salari-sud.md",
    "divario-che-si-chiude": "lavoce-salari-sud.md",
    "gruppi-che-divergono": "lavoce-salari-sud.md",
    "gruppi-che-convergono": "lavoce-salari-sud.md",
    # una classifica di rapporti, letta dal primo
    "graduatoria-spezzata": "infodata-mortalita-comuni.md",
    # dire che la lettura ovvia del dato è sbagliata
    "sorpasso": "pagellapolitica-record-occupati.md",
    # Stessa forma di storia, un piano sopra: non un territorio che ne scavalca
    # un altro ma un gruppo che ne scavalca un altro. Mapparlo non è
    # facoltativo come per un tipo raro qualunque: la sua forza è fissa e alta
    # (0,8, vedi `packs.angles.group_divergence`), quindi quando esce apre
    # quasi sempre l'articolo, e senza una riga qui `pick()` scenderebbe a un
    # angolo più debole o all'estratto del "nessuna storia".
    "gruppi-che-si-sorpassano": "pagellapolitica-record-occupati.md",
    "controcorrente": "pagellapolitica-record-occupati.md",
    # il luogo prima della cifra: un territorio estremo che vale nominare
    "valore-fuori-scala": "ilpost-borgo-albergo.md",
}

# Quando non c'è nessun angolo. Non è un ripiego elegante: un indicatore senza
# storia strutturale va scritto come un comunicato asciutto, non come un pezzo,
# e questo estratto è esattamente quello.
WHEN_THERE_IS_NO_STORY = "istat-conti-territoriali.md"


def pick(angles):
    """Il nome del file di esempio per questo pacchetto.

    Si guarda l'angolo più forte, e si scende finché se ne trova uno mappato:
    un tipo nuovo non deve far cadere la scelta sul ripiego, deve far scegliere
    il secondo angolo, che è comunque una storia di questo indicatore.
    """
    for angle in angles or []:
        name = BY_ANGLE.get(angle.get("type"))
        if name:
            return name
    return WHEN_THERE_IS_NO_STORY


def path_of(name):
    return os.path.join(ESEMPI_DIR, name)


def read(name):
    with open(path_of(name), encoding="utf-8") as handle:
        return handle.read()


def available():
    return sorted(item for item in os.listdir(ESEMPI_DIR)
                  if item.endswith(".md") and item != "README.md")
