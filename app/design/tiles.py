"""L'Italia a tessere: le 20 regioni in una griglia, una casella uguale per regione.

La mappa geografica da' a ogni regione il suo peso di superficie: la Valle
d'Aosta e il Molise sono pochi pixel, e sul telefono non si toccano. La
griglia li mette tutti alla stessa misura, conservando la forma dell'Italia
abbastanza da riconoscerla: e' la figura in cui la striscia del divario si
ricompone ("Striscia | Italia" nella scheda).

Le coordinate sono scritte a mano, una volta: colonna e riga di ogni regione
in una griglia di 5 colonne per 9 righe, con le vicine accanto quando la
griglia lo permette. Le sigle sono quelle d'uso corrente.
"""

from __future__ import annotations

from app.data import REGION_GEO_AREA

COLUMNS = 5
ROWS = 9

GRID: dict[str, tuple[int, int]] = {
    "valle-d-aosta": (0, 0), "trentino-alto-adige": (2, 0), "friuli-venezia-giulia": (3, 0),
    "piemonte": (0, 1), "lombardia": (1, 1), "veneto": (2, 1),
    "liguria": (0, 2), "emilia-romagna": (1, 2),
    "toscana": (1, 3), "umbria": (2, 3), "marche": (3, 3),
    "lazio": (2, 4), "abruzzo": (3, 4), "molise": (4, 4),
    "sardegna": (0, 5), "campania": (3, 5), "puglia": (4, 5),
    "basilicata": (4, 6),
    "calabria": (4, 7),
    "sicilia": (3, 8),
}

ABBR: dict[str, str] = {
    "valle-d-aosta": "VdA", "trentino-alto-adige": "TAA", "friuli-venezia-giulia": "FVG",
    "piemonte": "Pie", "lombardia": "Lom", "veneto": "Ven", "liguria": "Lig", "emilia-romagna": "ER",
    "toscana": "Tos", "umbria": "Umb", "marche": "Mar", "lazio": "Laz", "abruzzo": "Abr",
    "molise": "Mol", "sardegna": "Sar", "campania": "Cam", "puglia": "Pug", "basilicata": "Bas",
    "calabria": "Cal", "sicilia": "Sic",
}

if set(GRID) != set(REGION_GEO_AREA) or set(ABBR) != set(REGION_GEO_AREA):
    raise ValueError("la griglia delle regioni non copre le 20 regioni di REGION_GEO_AREA")
if len(set(GRID.values())) != len(GRID):
    raise ValueError("due regioni nella stessa casella della griglia")


def layout(classes: dict[str, str], names: dict[str, str], values: dict[str, str],
           short: dict[str, str]) -> list[dict]:
    """Le 20 caselle, ciascuna col gradino della mappa (`classes`, "q1".."q6"),
    il nome, il valore con la sua unita' (per chi legge con la sintesi vocale)
    e la sola cifra (dentro la casella). Una regione senza dato ha il gradino
    vuoto e "n.d."."""
    out = []
    for key, (col, row) in GRID.items():
        cls = (classes.get(key) or "").split()
        step = next((c for c in cls if len(c) == 2 and c[0] == "q" and c[1] in "123456"), "")
        out.append({"key": key, "abbr": ABBR[key], "name": names.get(key, key),
                    "value": values.get(key) or "n.d.", "short": short.get(key) or "n.d.", "col": col + 1, "row": row + 1, "step": step})
    return out
