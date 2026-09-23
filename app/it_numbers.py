"""I numeri come li legge un italiano, in un posto solo.

La pagina provincia li scriveva in tre modi alla stessa URL: il filtro `it_num`
dei template, `agent_discovery._number` per il Markdown e il `str()` di Python
dentro il Markdown stesso, che dava 8.829 decimali col punto. Tre copie della
stessa regola sono tre regole appena una cambia, quindi i template e le
proiezioni Markdown chiamano queste funzioni.
"""
from __future__ import annotations


def number(value, decimals=1):
    """`1234.5` -> `"1.234,5"`: punto per le migliaia, virgola per i decimali."""
    if value is None:
        return "n.d."
    try:
        formatted = f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return str(value)
    return formatted.replace(",", "§").replace(".", ",").replace("§", ".")


def change(value, decimals=1):
    """Una variazione col segno: `"+3,9"`, `"-1,2"`, e `"invariato"` sullo zero.

    Lo zero non prende segno. Una differenza di 0,03 scritta con un decimale
    diventava "+0,0", che dice "e' salito" su un numero che non si e' mosso.
    """
    if value is None:
        return None
    formatted = number(abs(value), decimals)
    if float(formatted.replace(".", "").replace(",", ".")) == 0:
        return "invariato"
    return f"{'+' if value > 0 else '-'}{formatted}"
