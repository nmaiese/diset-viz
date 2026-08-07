"""La forza di un angolo e' quanto e' raro, non quanto e' grande.

Il primo giro misurava la dimensione dell'effetto e basta. Sul catalogo vero
il risultato era che due tipi soli aprivano il 90% degli articoli
(`graduatoria-spezzata` 57,7%, `controcorrente` 32,2%): non perche' quelle
fossero le storie migliori, ma perche' quei due rilevatori sparano forte quasi
sempre. Una graduatoria di venti valori ha *sempre* un salto piu' largo degli
altri, e in quasi ogni serie *qualcuno* si muove controcorrente.

Ordinare per dimensione dell'effetto vuol dire quindi ordinare per tipo, e
riportare l'uniformita' un livello sopra: tutti gli articoli aprirebbero allo
stesso modo, che e' il difetto che questo pacchetto esiste per togliere.

La correzione: si misura ogni rilevatore su tutto il catalogo una volta, si
salvano i quantili, e a runtime la forza diventa **il posto che quell'effetto
occupa nella distribuzione del proprio tipo**. Un salto di graduatoria vale
0,9 solo se e' fra i piu' netti che quel rilevatore abbia mai visto, non
perche' i salti di graduatoria sono grossi in generale.

La tabella si rigenera con `python3 -m scripts.calibrate_angles`, e va
rigenerata quando entrano famiglie di dati nuove. Se manca, `strength` resta la
dimensione grezza: il pacchetto funziona lo stesso, ordina peggio, e
`packs.calibration.is_loaded()` dice che sta succedendo.
"""
from __future__ import annotations

import json
import os

TABLE_PATH = os.path.join(os.path.dirname(__file__), "calibration.json")

# Quanti punti di quantile salvare per tipo. Venti bastano: la forza serve a
# ordinare una decina di angoli, non a fare inferenza.
QUANTILES = 20

_table = None


def _load():
    global _table
    if _table is None:
        try:
            with open(TABLE_PATH, encoding="utf-8") as handle:
                _table = json.load(handle)
        except (OSError, ValueError):
            _table = {}
    return _table


def is_loaded():
    """C'e' una tabella, o si sta ordinando per dimensione grezza?"""
    return bool(_load())


def reload_table():
    """Rilegge la tabella da disco. Serve ai test e dopo una rigenerazione."""
    global _table
    _table = None
    return _load()


def calibrate(kind, raw):
    """Da dimensione dell'effetto a posto nella distribuzione del proprio tipo.

    Interpolazione lineare fra i quantili, cosi' due effetti vicini non
    finiscono sullo stesso gradino e l'ordinamento resta informativo. Fuori
    tabella si torna alla dimensione grezza, che e' il comportamento giusto per
    un tipo mai calibrato: meglio un ordine imperfetto che un ordine inventato.
    """
    edges = _load().get(kind)
    if not edges:
        return raw
    if raw <= edges[0]:
        return 0.0
    if raw >= edges[-1]:
        return 1.0
    for index in range(len(edges) - 1):
        low, high = edges[index], edges[index + 1]
        if low <= raw <= high:
            span = high - low
            inside = 0.0 if span == 0 else (raw - low) / span
            return (index + inside) / (len(edges) - 1)
    return raw


def build_table(samples):
    """{tipo: [quantili]} da {tipo: [dimensioni osservate]}.

    Un tipo con meno campioni dei quantili richiesti non entra: calibrare su
    cinque osservazioni vuol dire prendere il rumore per una distribuzione.
    """
    table = {}
    for kind, values in samples.items():
        clean = sorted(value for value in values if value is not None)
        if len(clean) < QUANTILES:
            continue
        edges = []
        for step in range(QUANTILES + 1):
            position = step * (len(clean) - 1) / QUANTILES
            low = int(position)
            high = min(low + 1, len(clean) - 1)
            weight = position - low
            # Non decrescente per costruzione, tranne che in virgola mobile:
            # l'interpolazione fra due campioni uguali produceva 0,9 seguito da
            # 0,9000000000000001, e `calibrate` cerca un intervallo con
            # `low <= raw <= high`, che su bordi invertiti non trova niente e
            # ricade sulla dimensione grezza senza dirlo.
            value = round(clean[low] * (1 - weight) + clean[high] * weight, 6)
            edges.append(max(value, edges[-1]) if edges else value)
        table[kind] = edges
    return table
