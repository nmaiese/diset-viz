"""Il grafico dentro l'articolo: una dispersione fra due indicatori, disegnata qui.

La pagina indicatore mostra già mappa, classifica e serie storica. Quello che
non mostra, e che nessun grafico del sito mostra, è **come questo indicatore si
dispone rispetto a un altro**: una regione per punto, e in evidenza le regioni
che stanno fuori dal disegno. È l'unica figura che aggiunge qualcosa al testo
invece di ripeterlo, e per questo è l'unica che esiste.

## Come si chiede

Nel corpo di una sezione dell'articolo, su una riga sua:

    <!-- grafico: dispersione con=dem-BIRTHRATE evidenzia=Sardegna,Lazio
         didascalia="Le due regioni accese non seguono le altre." -->

`con` è il codice dell'altro indicatore come sta nell'URL (`ter-401`,
`bes-12SER026`, `dem-BIRTHRATE`). `evidenzia` e `didascalia` sono facoltativi.
Il marcatore resta in italiano perché lo scrive chi redige, dentro il testo.

## Perché si disegna al render e non si salva

Come le sezioni composte del template, la figura **non viene congelata nel file
dell'articolo**: i valori si rileggono dai dati a ogni richiesta. Un SVG salvato
nel Markdown mostrerebbe i numeri del giorno in cui è stato scritto, e un
aggiornamento della fonte lo lascerebbe indietro senza che nessuno se ne
accorga. Qui quel rischio non esiste: se cambiano i dati, cambia il disegno.

Corollario: **una figura che non si può disegnare non rompe la pagina.** Se
l'altro indicatore non esiste più, se non ha dati, se le regioni in comune sono
troppo poche, il marcatore sparisce e il testo resta intero. Il pezzo si scrive
perché regga anche senza la figura.
"""

from __future__ import annotations

import re

from markupsafe import Markup, escape

from app import sources

# Il marcatore come lo scrive chi redige: tollerante sugli spazi e sull'a capo,
# perché lo batte a mano una persona (o un modello) dentro un paragrafo.
MARKER_RE = re.compile(r"<!--\s*grafico:\s*dispersione\s+(?P<args>[^>]*?)\s*-->", re.IGNORECASE | re.DOTALL)
_ARG_RE = re.compile(r'(\w+)\s*=\s*(?:"([^"]*)"|([^\s"]+))')

# Sotto otto territori in comune una dispersione non si legge: sono otto punti
# sparsi, e il lettore ci vede un disegno che i dati non hanno.
MIN_POINTS = 8

# La tela. Il viewBox è fisso e il CSS la scala, come per la sparkline: due modi
# di dimensionare un SVG nella stessa pagina sarebbero uno di troppo.
WIDTH = 320.0
HEIGHT = 240.0
MARGIN = 26.0


def parse_args(text):
    """`con=ter-401 evidenzia=Lazio,Sardegna` -> dizionario. Le virgolette reggono gli spazi."""
    found = {}
    for name, quoted, bare in _ARG_RE.findall(text or ""):
        found[name.lower()] = quoted if quoted else bare
    return found


def requested(body):
    """Le figure chieste da un corpo di sezione, nell'ordine in cui compaiono."""
    return [parse_args(match.group("args")) for match in MARKER_RE.finditer(body or "")]


def _values(code, level_key):
    """(meta, {nome del territorio: valore}, anno) all'ultimo anno, o (None, None, None)."""
    from app.indicator_view import build_indicator_view

    # Due forme in circolazione, e qui arrivano entrambe: il codice dell'URL che
    # scrive chi redige ("ter-401") e la chiave interna dell'articolo che si sta
    # rendendo ("bes:12SER026", "17").
    parsed = sources.parse_indicator_code(code or "") or sources.split_internal_id(code or "")
    if not parsed:
        return None, None, None
    family, raw_id = parsed
    try:
        view = build_indicator_view(family, raw_id)
    except Exception:
        return None, None, None
    if not view:
        return None, None, None
    levels = {level["key"]: level for level in view["levels"]}
    level = levels.get(level_key) or view["levels"][0]
    matrix = level.get("matrix") or {}
    if not matrix:
        return None, None, None
    year = max(int(y) for y in matrix)
    names = {row["key"]: row["name"] for row in level["territories"]}
    row = matrix.get(str(year)) or matrix.get(year) or {}
    return view["meta"], {names.get(k, k): v for k, v in row.items() if v is not None}, year


def pairs(mine, theirs):
    """[(territorio, x, y)] sui soli territori che i due indicatori hanno in comune."""
    return [(name, theirs[name], mine[name]) for name in sorted(set(mine) & set(theirs))]


def _scale(values, start, end):
    """Da valore a coordinata, con un respiro del 6% ai due estremi perché i punti non tocchino il bordo."""
    low, high = min(values), max(values)
    if high == low:
        return lambda _: (start + end) / 2
    room = (high - low) * 0.06
    low, high = low - room, high + room
    return lambda value: start + (value - low) / (high - low) * (end - start)


def scatter_svg(points, highlighted, x_label, y_label):
    """Il disegno, da coordinate già pronte. Pura: nessun accesso ai dati, e per questo verificabile.

    La Y cresce verso l'alto come se lo aspetta chi guarda, quindi la coordinata
    dello schermo si rovescia. Il nome lo portano solo i punti accesi: venti
    etichette su una figura larga trecento pixel non si leggono, e l'SVG è
    comunque `aria-hidden` perché chi non vede legge la didascalia.
    """
    if len(points) < MIN_POINTS:
        return ""
    x = _scale([p[1] for p in points], MARGIN, WIDTH - MARGIN / 2)
    y = _scale([p[2] for p in points], HEIGHT - MARGIN, MARGIN / 2)
    parts = [
        f'<svg class="scatter" viewBox="0 0 {WIDTH:.0f} {HEIGHT:.0f}" aria-hidden="true" focusable="false">',
        f'<line class="scatter__axis" x1="{MARGIN:.0f}" y1="{HEIGHT - MARGIN:.0f}" '
        f'x2="{WIDTH - MARGIN / 2:.0f}" y2="{HEIGHT - MARGIN:.0f}"/>',
        f'<line class="scatter__axis" x1="{MARGIN:.0f}" y1="{MARGIN / 2:.0f}" '
        f'x2="{MARGIN:.0f}" y2="{HEIGHT - MARGIN:.0f}"/>',
    ]
    for name, vx, vy in points:
        on = name in highlighted
        parts.append(f'<circle class="scatter__dot{" is-on" if on else ""}" '
                     f'cx="{x(vx):.1f}" cy="{y(vy):.1f}" r="{4.2 if on else 3:.1f}"/>')
    for name, vx, vy in points:
        if name not in highlighted:
            continue
        cx, cy = x(vx), y(vy)
        # L'etichetta passa a sinistra quando il punto sta nella metà destra,
        # così non esce dalla tela: l'ancora del testo si sposta con lei.
        right = cx > WIDTH / 2
        parts.append(f'<text class="scatter__name" x="{cx + (-7 if right else 7):.1f}" y="{cy + 3.5:.1f}" '
                     f'text-anchor="{"end" if right else "start"}">{escape(name)}</text>')
    parts.append(f'<text class="scatter__axis-name" x="{WIDTH - MARGIN / 2:.0f}" y="{HEIGHT - 8:.0f}" '
                 f'text-anchor="end">{escape(x_label)}</text>')
    parts.append(f'<text class="scatter__axis-name" x="{MARGIN:.0f}" y="12">{escape(y_label)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def short_name(name):
    """Il nome dell'indicatore senza la coda fra parentesi che nomina fonte e livello.

    "Tasso di natalità (Istat, regioni)" -> "Tasso di natalità". Si toglie solo
    se dentro c'è una virgola: "(totale)", "(maschi)" e "(femmine)" distinguono
    varianti vere e devono restare.
    """
    return re.sub(r"\s*\([^()]*,[^()]*\)\s*$", "", name or "").strip()


def figure(indicator_id, spec, level_key):
    """Una `<figure>` completa, o stringa vuota se non c'è niente da disegnare."""
    my_meta, mine, my_year = _values(indicator_id, level_key)
    their_meta, theirs, their_year = _values(spec.get("con", ""), level_key)
    if not mine or not theirs:
        return ""
    points = pairs(mine, theirs)
    if len(points) < MIN_POINTS:
        return ""
    highlighted = {name.strip() for name in (spec.get("evidenzia") or "").split(",") if name.strip()}
    my_name, their_name = short_name(my_meta["name"]), short_name(their_meta["name"])
    drawing = scatter_svg(points, highlighted, f"{their_name} ({their_year})", f"{my_name} ({my_year})")
    if not drawing:
        return ""
    # La didascalia non è decorazione: una dispersione è illeggibile a uno
    # screen reader, quindi l'SVG è aria-hidden e il testo deve bastare da solo.
    # Perciò dice i due nomi, i due anni, quanti territori e quali sono accesi.
    written = (spec.get("didascalia") or "").strip()
    described = (f"Ogni punto è una regione: {their_name} nel {their_year} in orizzontale, "
                 f"{my_name} nel {my_year} in verticale. {len(points)} regioni con dati per entrambi.")
    on_chart = [name for name, _, _ in points if name in highlighted]
    if on_chart:
        described += f" In evidenza: {', '.join(on_chart)}."
    caption = f"{written} {described}".strip() if written else described
    return f'<figure class="scatter-figure">{drawing}<figcaption>{escape(caption)}</figcaption></figure>'


def render(html, indicator_id, level_key):
    """Sostituisce ogni marcatore nell'HTML della sezione con la sua figura.

    Si lavora sull'HTML e non sul Markdown perché un commento HTML attraversa la
    conversione intatto, mentre una `<figure>` inserita prima passerebbe per il
    parser Markdown e ne uscirebbe spezzata fra i paragrafi.
    """
    def replace(match):
        try:
            return figure(indicator_id, parse_args(match.group("args")), level_key)
        except Exception:
            # Una figura non vale la pagina: se qualcosa va storto, sparisce.
            return ""

    return Markup(MARKER_RE.sub(replace, html or ""))
