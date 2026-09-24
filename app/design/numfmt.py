"""Come si scrive una cifra nella 1.0: un posto solo.

La prima iterazione dei prototipi aveva sette formattatori diversi fra
template e logica di pagina, e la stessa grandezza usciva con decimali diversi
da una pagina all'altra. Qui ci sono i ruoli di una cifra e, per ciascuno, una
regola sola. I template non formattano: chiamano i filtri `num`, `rank` e
`delta`, che producono un `<data value>` con il valore per le macchine e il
testo per le persone.

Ruoli:
- figure: la cifra di una tessera o di una frase. Decimali dalla grandezza
  (la regola di seo_titles, la stessa dei title).
- cell: la cifra in una colonna. Decimali dati dalla colonna, uguali per tutte
  le righe, o dalla grandezza se la colonna non li dice.
- score: un punteggio da 0 a 100, sempre con un decimale.
- ratio: un rapporto ("2,5 volte"), sempre con un decimale.
- delta: una variazione, sempre col segno, e "invariato" sullo zero.
- rank: una posizione, "14ª", con il denominatore se c'e'.
- count: un conteggio (regioni, anni, indicatori), sempre intero.

Il segno negativo e' il trattino ASCII, come in `it_num` e nei gemelli
Markdown: una cifra si scrive allo stesso modo nella pagina, nel Markdown e
nel JSON-LD, e `static/js/v1.js` fa lo stesso, cosi' server e client non
divergono.
"""

from __future__ import annotations

import math
import re
from html import escape

from markupsafe import Markup

MINUS = "-"
THIN = " "  # spazio fine fra la cifra e l'unita'
FIXED = {"score": 1, "ratio": 1, "rank": 0, "count": 0}


def magnitude_decimals(value: float) -> int:
    """La regola di seo_titles._decimals: la grandezza decide se il decimale conta.

    Lo zero si scrive "0": "0,00" diceva una precisione che uno zero non ha, e
    finiva nei title ("dal 358% al 0,00%"). La stessa regola sta in
    `seo_titles._decimals` e in `decimals` di `static/js/v1.js`, e
    `tests/unit/test_decimals_parity.py` controlla che le tre concordino.
    """
    m = abs(float(value))
    if m == 0 or m >= 100:
        return 0
    if m >= 10:
        return 1
    return 2 if m < 1 else 1


def column_decimals(values) -> int:
    """I decimali di una colonna: quelli della cifra mediana, uguali per tutte le righe.

    Una mediana a zero tiene i due decimali di prima: la regola dello zero vale
    per la cifra da sola, e una colonna a zero decimali arrotonderebbe a "1" e
    "0" anche le righe che zero non sono."""
    vals = sorted(abs(float(v)) for v in values if v is not None)
    if not vals:
        return 0
    median = vals[len(vals) // 2]
    return magnitude_decimals(median) if median else 2


# "dal", "dallo", "dall'" davanti a una cifra: la forma la decide come la cifra
# si legge. "otto", "undici" e "uno" cominciano per vocale, "zero" vuole "lo".
_ARTICULATED = {
    "di": ("del ", "dello ", "dell'"),
    "da": ("dal ", "dallo ", "dall'"),
    "a": ("al ", "allo ", "all'"),
}
_READS_AS_ZERO = re.compile(r"0(?![\d.])")
# 8, 80, 800, 8.000 (otto...); 11, 11,3, 11.000 (undici...); 1 e 1,x (uno).
# Non 110-119 ("centodieci") e non 1.022 ("milleventidue").
_READS_WITH_VOWEL = re.compile(r"8|11(?!\d)|1(?![\d.])")


def articulated(preposition: str, figure: str) -> str:
    """La preposizione articolata davanti a una cifra gia' scritta all'italiana:
    `articulated("da", "89,1%")` -> "dall'", `("a", "0,22%")` -> "allo ",
    `("di", "116%")` -> "del ".

    Un posto solo, perche' erano due regole scritte a mano e sbagliavano in due
    modi diversi: i title dicevano "dal 8" e "al 0,00%", le frasi della scheda
    "dell'116%" (la vecchia regola vedeva "11" in testa a 116). Il negativo si
    legge "meno" e prende la forma piena. `preposition` e' "di", "da" o "a".
    """
    plain, before_zero, elided = _ARTICULATED[preposition]
    text = (figure or "").strip()
    if text.startswith((MINUS, "−")):
        return plain
    if _READS_AS_ZERO.match(text):
        return before_zero
    if _READS_WITH_VOWEL.match(text):
        return elided
    return plain


def text(value, decimals: int | None = None, sign: bool = False) -> str:
    """`-1234.5` -> `−1.234,5`. Con sign=True il positivo porta il `+`."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n.d."
    v = float(value)
    d = magnitude_decimals(v) if decimals is None else decimals
    body = f"{abs(v):,.{d}f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    rounded_zero = float(body.replace(".", "").replace(",", ".")) == 0
    if v < 0 and not rounded_zero:
        return MINUS + body
    if sign and v > 0 and not rounded_zero:
        return "+" + body
    return body


def lower_first(text: str) -> str:
    """"Per 1.000 abitanti" -> "per 1.000 abitanti", ma "GWh" e "KTep" restano
    come sono: una sigla con la maiuscola non si abbassa, "gWh" e' un'altra
    unita'."""
    if len(text) > 1 and text[1].isupper():
        return text
    return text[:1].lower() + text[1:]


def short_unit(unit: str | None) -> str | None:
    """L'unita' come si scrive accanto a una cifra ("anni", "per 10.000 occupati")."""
    unit = (unit or "").strip()
    if not unit:
        return None
    if unit.startswith("%"):
        return "%"
    m = re.match(r"(?i)numero medio di (.+)", unit)
    if m:
        return m.group(1)
    lowered = lower_first(unit)
    if lowered.startswith("per "):
        return lowered
    if len(unit) <= 14:
        return unit
    if len(unit) <= 24:
        return lowered
    return None


# Etichette della fonte che dicono che cosa si conta ma non sono un'unita' da
# scrivere accanto a una cifra: "29,0 numero", "7,0 Valore medio", "0,61 classi".
GENERIC_UNITS = {"numero", "numero medio", "valore medio", "indice", "indice (0-1)", "rapporto", "classi"}
# "centomila anziani" e' un tasso, ogni centomila anziani: scritto accanto a una
# cifra senza "ogni", "228 centomila anziani" si legge come ventidue milioni.
RATE_BASE = re.compile(r"(cento|mille|diecimila|centomila|un milione di) ")


def phrase_unit(unit: str | None) -> str | None:
    """L'unita' come si scrive dopo una cifra: "euro", "%", "per mille
    abitanti", "ogni centomila anziani". None quando l'etichetta della fonte non
    e' un'unita': la cifra resta nuda, e l'unita' la dice la riga sotto il titolo
    o l'intestazione della colonna. La usano `num` (tessere, celle, frasi dei
    template), `common.with_unit` e `common.signed` (frasi composte in Python) e
    il JavaScript delle mappe, cosi' la stessa cifra si scrive uguale ovunque."""
    u = short_unit(unit)
    if not u or u == "%":
        return u
    u = lower_first(u)
    if u in GENERIC_UNITS:
        return None
    m = re.match(r"(?:numero medio|numero|valori) (per .+)$", u)
    if m:
        return m.group(1)
    m = re.match(r"numero di (.+)$", u)
    if m:
        return m.group(1)
    if RATE_BASE.match(u):
        return "ogni " + u
    return u


def num(value, unit: str | None = None, role: str = "figure", decimals: int | None = None) -> Markup:
    """Una cifra con la sua unita', come elemento `<data>`."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return Markup('<span class="n n--nd"><abbr title="dato non disponibile">n.d.</abbr></span>')
    d = FIXED.get(role, decimals)
    shown = text(value, d, sign=(role == "delta"))
    if role == "delta" and shown in ("0", "0,0", "0,00"):
        return Markup('<data class="n n--delta" value="0">invariato</data>')
    u = phrase_unit(unit)
    unit_html = ""
    if u == "%":
        unit_html = '<span class="n__u n__u--pct">%</span>'
    elif u:
        unit_html = f'<span class="n__u">{THIN}{escape(u)}</span>'
    raw = f"{float(value):.6g}"
    return Markup(f'<data class="n n--{role}" value="{raw}">{escape(shown)}{unit_html}</data>')


def rank(position, total=None, of: str | None = None) -> Markup:
    """"14ª su 20", con la posizione in `<data>` e il denominatore piu' piccolo."""
    if position is None:
        return Markup('<span class="n n--nd">n.d.</span>')
    tail = ""
    if total is not None:
        tail = f'<span class="n__u">{THIN}su {int(total)}{(" " + escape(of)) if of else ""}</span>'
    pos = round(float(position))  # una posizione media di 13,9 si scrive 14ª, come nei title
    return Markup(f'<span class="n n--rank"><data value="{pos}">{pos}</data>'
                  f'<span class="n__o">ª</span>{tail}</span>')


def delta(value, unit: str | None = None, decimals: int | None = None) -> Markup:
    return num(value, unit, role="delta", decimals=decimals)


def register(env) -> None:
    """I filtri dei template: `{{ v | num('euro') }}`, `{{ 14 | rank(20) }}`, `{{ d | delta('euro') }}`."""
    env.filters["num"] = num
    env.filters["rank"] = rank
    env.filters["delta"] = delta
    env.filters["numtext"] = text
    env.globals["column_decimals"] = column_decimals
