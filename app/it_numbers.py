"""I numeri come li legge un italiano, in un posto solo.

La pagina provincia li scriveva in tre modi alla stessa URL: il filtro `it_num`
dei template, `agent_discovery._number` per il Markdown e il `str()` di Python
dentro il Markdown stesso, che dava 8.829 decimali col punto. Tre copie della
stessa regola sono tre regole appena una cambia, quindi i template e le
proiezioni Markdown chiamano queste funzioni.
"""
from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal


def rounded(value: float, decimals: int) -> Decimal:
    """La cifra arrotondata come la arrotonda il browser: mezzo per eccesso,
    sulla cifra come si scrive.

    Il formato di Python (`f"{v:.0f}"`) arrotonda i pareggi al pari e lavora sul
    binario: la retribuzione di Milano, 26348,5, usciva "26.348" dal server e
    "26.349" da `Intl.NumberFormat` in `static/js/v1.js`, che parte dalla cifra
    piu' corta che rappresenta il numero (`repr`) e porta il cinque in su. Qui
    si fa lo stesso: 13,25 fa 13,3 e 0,285 fa 0,29 da entrambe le parti.
    """
    return Decimal(repr(float(value))).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)


def number(value, decimals=1):
    """`1234.5` -> `"1.234,5"`: punto per le migliaia, virgola per i decimali.

    E' l'unico posto dove una cifra si arrotonda: `numfmt.text` e
    `seo_titles.format_number` passano di qui, cosi' pagina, title e gemello
    Markdown non si separano su un pareggio."""
    if value is None:
        return "n.d."
    try:
        v = float(value)
        formatted = (f"{rounded(v, decimals):,.{decimals}f}" if math.isfinite(v)
                     else f"{v:,.{decimals}f}")
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
