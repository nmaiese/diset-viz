"""L'articolo del blog nella veste 1.0: le parti nuove, composte dal pezzo vero.

Il corpo arriva gia' in HTML (`post.body_html`), scritto dalla redazione. Qui
non si riscrive una parola: si smonta in blocchi di primo livello e si rimonta
nell'ordine della pagina articolo del sistema.

- La frase evidenziata (`p.data-callout`) e "In breve" salgono in testa, come
  risposta in breve.
- "Dati usati", "Fonti" e la riga finale "Dati: ..." scendono nel blocco unico
  "Dati e metodo".
- Ogni figura di `scripts/trend_articles/figures.py` diventa la figura comune
  (`.figure`): titolo, sottotitolo, nota e fonte escono dall'SVG e tornano
  come testo HTML, il disegno esce in due tagli (largo a 680, stretto a 360)
  perche' il testo resti a 13 pixel veri anche sul telefono, e i valori letti
  dal disegno stanno in una tabella sotto.
- Le tabelle Markdown prendono didascalia, `scope` e la riga di riferimento.
- Ogni cifra di una tabella passa da `numfmt`, con i decimali che la fonte ha
  scritto. La prosa della redazione non si tocca.
- La copertina fotografica diventa l'immagine d'apertura, con didascalia e
  credito. Una copertina che e' un grafico (le vecchie schede social in SVG)
  non si ritaglia come una foto: al suo posto la pagina apre con la striscia
  del divario disegnata dagli stessi dati, nell'anno del pezzo. Se l'anno non
  si trova, o i dati di oggi non coincidono con la tabella del pezzo, la
  striscia si toglie e apre la copertina com'e'.
- Il rimando alla scheda va alla fine della sezione della prima figura o della
  prima tabella, e comunque prima di ogni altro link a una scheda: la guardia
  sulla collisione dei titoli legge il primo `href` verso `/indicatore/`.

Niente solleva: un pezzo che il parser non riconosce passa com'e', e cio' che
manca toglie la sua parte di pagina.
"""

from __future__ import annotations

import re
import struct
from functools import lru_cache
from html import escape, unescape
from html.parser import HTMLParser

from markupsafe import Markup

from app import sources
from app.blog import STATIC_DIR
from app.design import charts, numfmt
from app.design.common import count_word, date_it
from app.indicator_notes import figure_unit

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
NUMBER = r"-?\d[\d.]*(?:,\d+)?"
SOURCE_NUMBER = re.compile(r"^([+\-−]?)(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d+))?(\s?%)?$")
YEAR = re.compile(r"\b((?:19|20)\d\d)\b")
NARROW = 360
# Larghezza media di un carattere a 13 pixel, con un po' di margine: serve a
# non far toccare le etichette quando il disegno si stringe.
CHAR = 6.6


# ---------------------------------------------------------------- blocchi

class _TopLevel(HTMLParser):
    """Le posizioni d'inizio degli elementi di primo livello."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.depth = 0
        self.starts: list[tuple[int, int]] = []

    def handle_starttag(self, tag, attrs):
        if self.depth == 0:
            self.starts.append(self.getpos())
        if tag not in VOID:
            self.depth += 1

    def handle_startendtag(self, tag, attrs):
        if self.depth == 0:
            self.starts.append(self.getpos())

    def handle_endtag(self, tag):
        if tag not in VOID:
            self.depth = max(0, self.depth - 1)


def blocks(html: str) -> list[str]:
    """Il corpo diviso nei suoi elementi di primo livello, in ordine."""
    parser = _TopLevel()
    parser.feed(html)
    parser.close()
    # HTMLParser conta le righe solo sugli a capo: le posizioni si ricostruiscono
    # allo stesso modo, non con splitlines, che spezza anche su altri separatori.
    line_offsets = [0]
    for line in html.split("\n"):
        line_offsets.append(line_offsets[-1] + len(line) + 1)
    starts = [line_offsets[line - 1] + col for line, col in parser.starts]
    ends = starts[1:] + [len(html)]
    return [html[a:b].strip() for a, b in zip(starts, ends) if html[a:b].strip()]


def tag_of(block: str) -> tuple[str, str]:
    m = re.match(r"<(\w+)([^>]*)>", block)
    return (m.group(1).lower(), m.group(2)) if m else ("", "")


def text_of(fragment: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def heading_id(block: str) -> str | None:
    m = re.search(r'\bid="([^"]+)"', block.split(">", 1)[0])
    return m.group(1) if m else None


def section(items: list[str], start: int) -> int:
    """L'indice del primo H2 dopo `start`, o la fine: dove finisce la sezione."""
    for i in range(start + 1, len(items)):
        if tag_of(items[i])[0] == "h2":
            return i
    return len(items)


def take_section(items: list[str], ident: str) -> list[str] | None:
    """Toglie da `items` l'H2 con quell'id e cio' che lo segue fino al prossimo H2."""
    for i, block in enumerate(items):
        if tag_of(block)[0] == "h2" and heading_id(block) == ident:
            end = section(items, i)
            taken = items[i:end]
            del items[i:end]
            return taken
    return None


# ---------------------------------------------------------------- cifre della fonte

def _source_number(text: str) -> tuple[float, int, bool, bool] | None:
    """`"20,3"` -> (20.3, 1 decimale, non percentuale, senza +). None se non e' solo una cifra."""
    m = SOURCE_NUMBER.match((text or "").strip())
    if not m:
        return None
    sign, whole, dec, pct = m.groups()
    value = float(whole.replace(".", "") + (f".{dec}" if dec else ""))
    return (-value if sign in ("-", "−") else value), len(dec or ""), bool(pct), sign == "+"


def _is_year(text: str) -> bool:
    return bool(re.fullmatch(r"(19|20)\d\d", (text or "").strip()))


def cell(text, decimals: int | None = None) -> Markup:
    """Una cifra della fonte come la scrive il sistema: `numfmt`, con i decimali
    della fonte (o della sua colonna). Un anno o un testo restano com'erano."""
    if isinstance(text, Markup):
        return text
    parsed = None if _is_year(text) else _source_number(text)
    if not parsed:
        return Markup(escape(text))
    value, own, pct, plus = parsed
    return numfmt.num(value, "%" if pct else None, "delta" if plus else "cell", own if decimals is None else decimals)


def _column_decimals(rows: list[list], i: int) -> tuple[bool, int | None]:
    """Se la colonna e' di cifre, e con quanti decimali: i piu' fini che la fonte scrive."""
    values = [r[i] for r in rows if i < len(r) and str(r[i]).strip()]
    if not values:
        return False, None
    parsed = [None if isinstance(v, Markup) or _is_year(v) else _source_number(v) for v in values]
    numeric = all(p or isinstance(v, Markup) for p, v in zip(parsed, values))
    return numeric, max((p[1] for p in parsed if p), default=None)


# Le colonne dei territori. Il nome diventa il link alla sua pagina quando
# coincide esattamente con una regione o una provincia: l'articolo sulle
# province ne nominava 123 in tabella senza un link, e "Continua a esplorare"
# restava vuoto. Solo le tabelle, mai la prosa, dove "a Torino" e' una citta'.
TERRITORY_COLUMNS = {"Provincia": ("provincia",), "Regione": ("regione",),
                     "Territorio": ("regione", "provincia")}
# Quanti territori in "Continua a esplorare": con le tabelle legate sarebbero
# centoventi.
TERRITORY_NAMED_MAX = 6


def _territory_cell(name, kinds) -> str:
    from app import territory_search

    text = escape(str(name))
    path = territory_search.path_for_name(str(name), kinds) if kinds else None
    return f'<a href="{path}">{text}</a>' if path else text


def _table(caption: str, head: list[str], rows: list[list], label: str, ref_rows: set[int] = frozenset(),
           visible_caption: bool = False) -> str:
    """Una tabella dati del sistema: didascalia, scope, cifre a destra con decimali
    uniformi per colonna. Da quattro colonne in su, sul telefono, blocchi etichettati."""
    columns = [_column_decimals(rows, i) for i in range(len(head))]
    kinds = TERRITORY_COLUMNS.get(head[0]) if head else None
    stack = len(head) >= 4
    right = ' class="r"'
    th = "".join(f'<th scope="col"{right if i and columns[i][0] else ""}>{escape(h)}</th>' for i, h in enumerate(head))
    body = []
    for n, row in enumerate(rows):
        cells = []
        for i, c in enumerate(row[1:], 1):
            numeric, dec = columns[i] if i < len(columns) else (False, None)
            label_attr = f' data-label="{escape(head[i])}"' if stack and i < len(head) else ""
            cls = ' class="val"' if numeric else ""
            cells.append(f"<td{cls}{label_attr}>{cell(c, dec) if numeric else escape(str(c))}</td>")
        tr = ' class="ref"' if n in ref_rows else ""
        name = escape(str(row[0])) if n in ref_rows else _territory_cell(row[0], kinds)
        body.append(f'<tr{tr}><th scope="row">{name}</th>{"".join(cells)}</tr>')
    wrap = "stackwrap tablewrap" if stack else "tablewrap"
    table_cls = "table table--compact" + (" table--stack" if stack else "")
    cap = "<caption>" if visible_caption else '<caption class="sr-only">'
    return (f'<div class="{wrap}" tabindex="0" role="region" aria-label="{escape(label)}">'
            f'<table class="{table_cls}">{cap}{escape(caption)}</caption>'
            f'<thead><tr>{th}</tr></thead><tbody>{"".join(body)}</tbody></table></div>')


# ---------------------------------------------------------------- figure: lettura

def _svg_text(svg: str, cls: str) -> list[str]:
    return [text_of(m) for m in re.findall(rf'<text class="{cls}(?: [^"]*)?"[^>]*>(.*?)</text>', svg, re.DOTALL)]


def _drop_text(svg: str, cls: str) -> str:
    return re.sub(rf'\s*<text class="{cls}"[^>]*>.*?</text>', "", svg, flags=re.DOTALL)


def _attr(tag: str, name: str) -> str | None:
    m = re.search(rf'\s{name}="([^"]*)"', tag)
    return m.group(1) if m else None


def _num_attr(tag: str, name: str) -> float:
    return float(_attr(tag, name) or 0)


def _set(tag: str, name: str, value: float | str) -> str:
    text = f"{value:.1f}" if isinstance(value, float) else str(value)
    return re.sub(rf'(\s{name}=")[^"]*(")', lambda m: m.group(1) + text + m.group(2), tag, count=1)


def _each(svg: str, fn) -> str:
    """Applica `fn(tag_aperto, testo, classe)` a ogni elemento del disegno.

    `testo` e' il contenuto di un `<text>`, None per le forme. `fn` restituisce
    l'elemento intero riscritto, o una stringa vuota per toglierlo."""
    def one(m):
        tag, content = m.group(1), m.group(2)
        cls = _attr(tag, "class") or ""
        return fn(tag, content, cls, m.group(0))
    return re.sub(r"(<text\b[^>]*>)(.*?)</text>|(<(?:rect|line|circle|polyline)\b[^>]*>)",
                  lambda m: one(m) if m.group(1) else fn(m.group(3), None, _attr(m.group(3), "class") or "", m.group(3)),
                  svg, flags=re.DOTALL)


def _bar_rows(svg: str) -> list[tuple[bool, str, float, str]]:
    return [(bool(on), text_of(name), float(width), text_of(value)) for on, name, width, value in re.findall(
        r'<text class="fig__name( is-on)?"[^>]*>(.*?)</text>\s*'
        r'<rect class="fig__bar(?: is-on)?"[^>]*\bwidth="([\d.]+)"[^>]*/>\s*'
        r'<text class="fig__value(?: is-on)?"[^>]*>(.*?)</text>', svg, re.DOTALL)]


def _ref_label(svg: str) -> tuple[str, str] | None:
    """La riga di riferimento del disegno ("Italia 11,0"): nome e cifra."""
    ref = _svg_text(svg, "fig__ref-label")
    m = re.match(rf"(.*\S)\s+({NUMBER})$", ref[0]) if ref else None
    if not m or _source_number(m.group(2)) is None:
        return None
    return m.group(1)[:1].upper() + m.group(1)[1:], m.group(2)


# ---------------------------------------------------------------- figure: il taglio stretto

def _narrow_bars(svg: str) -> str:
    """Le barre a 360: la colonna dei nomi quanto il nome piu' lungo, le barre
    scalate nello spazio che resta, le cifre in fondo alla barra."""
    rects = re.findall(r'<rect class="fig__bar[^"]*"[^>]*>', svg)
    names = _svg_text(svg, "fig__name")
    values = _svg_text(svg, "fig__value")
    left = _num_attr(rects[0], "x")
    widest = max(_num_attr(r, "width") for r in rects) or 1
    longest = min(24, max(len(n) for n in names))
    nl = round(max(90, longest * CHAR + 14))
    k = (NARROW - nl - max(len(v) for v in values) * CHAR - 10) / widest

    def px(x):
        return nl + (x - left) * k

    def fix(tag, content, cls, whole):
        if content is not None:
            if cls.startswith("fig__name"):
                short = content if len(text_of(content)) <= 24 else escape(text_of(content)[:22].rstrip() + ".")
                return f"{_set(tag, 'x', float(nl - 8))}{short}</text>"
            if cls.startswith(("fig__value", "fig__ref-label")):
                return f"{_set(tag, 'x', px(_num_attr(tag, 'x') - 6) + 6)}{content}</text>"
            if cls.startswith("fig__gap"):
                return f"{_set(tag, 'x', float(nl))}{content}</text>"
            return whole
        if cls.startswith("fig__bar"):
            return _set(_set(tag, "x", float(nl)), "width", _num_attr(tag, "width") * k)
        if cls.startswith("fig__ref"):
            return _set(_set(tag, "x1", px(_num_attr(tag, "x1"))), "x2", px(_num_attr(tag, "x2")))
        return whole
    return _each(svg, fix)


def _narrow_lines(svg: str) -> str:
    """Le linee a 360: l'asse delle cifre a sinistra, le etichette a fine linea a
    destra, gli anni diradati perche' non si tocchino."""
    grid = re.search(r'<line class="fig__grid"[^>]*>', svg)
    left, right = _num_attr(grid.group(0), "x1"), _num_attr(grid.group(0), "x2")
    labels = _svg_text(svg, "fig__label")
    nl, nr = 40, NARROW - (max((len(t) for t in labels), default=6) * CHAR + 12)
    k = (nr - nl) / ((right - left) or 1)

    def px(x):
        return nl + (x - left) * k

    # Gli anni: il primo, l'ultimo e quelli a 36 unita' dal precedente.
    years = [px(_num_attr(t, "x")) for t in re.findall(r'<text class="fig__axis"[^>]*text-anchor="middle"[^>]*>', svg)]
    keep, last = set(), None
    for i, x in enumerate(years):
        if last is None or x - last >= 36:
            keep.add(i)
            last = x
    if years and len(years) - 1 not in keep:
        if keep and years[-1] - years[max(keep)] < 36:
            keep.discard(max(keep))
        keep.add(len(years) - 1)
    seen = {"year": -1}

    def fix(tag, content, cls, whole):
        if content is not None:
            if cls == "fig__axis" and _attr(tag, "text-anchor") == "middle":
                seen["year"] += 1
                return f"{_set(tag, 'x', px(_num_attr(tag, 'x')))}{content}</text>" if seen["year"] in keep else ""
            if cls == "fig__axis":
                return f"{_set(tag, 'x', float(nl - 6))}{content}</text>"
            if cls.startswith("fig__label"):
                return f"{_set(tag, 'x', px(_num_attr(tag, 'x') - 8) + 8)}{content}</text>"
            return whole
        if cls.startswith("fig__grid"):
            return _set(_set(tag, "x1", float(nl)), "x2", float(nr))
        if cls.startswith("fig__line"):
            points = " ".join(f"{px(float(a)):.1f},{b}" for a, b in re.findall(r"([\d.]+),([\d.]+)", _attr(tag, "points")))
            return _set(tag, "points", points)
        if cls.startswith("fig__dot"):
            return _set(tag, "cx", px(_num_attr(tag, "cx")))
        return whole
    return _each(svg, fix)


def _narrow_scatter(svg: str) -> str:
    """La dispersione a 360: i punti riproiettati in orizzontale, e i nomi dei
    territori ricollocati perche' non si sovrappongano nel disegno piu' stretto."""
    ytick = re.search(r'<text class="fig__axis"[^>]*text-anchor="end"[^>]*>', svg)
    xname = re.search(r'<text class="fig__axis-name"[^>]*text-anchor="end"[^>]*>', svg)
    left = _num_attr(ytick.group(0), "x") + 6
    right = _num_attr(xname.group(0), "x")
    nl, nr = 40, NARROW - 12
    k = (nr - nl) / ((right - left) or 1)

    def px(x):
        return nl + (x - left) * k

    # Ogni nome col suo punto: il generatore lo mette a 7 unita' dal centro e,
    # se tocca un altro nome, lo fa scivolare in basso di una riga.
    points = [(_num_attr(t, "cx"), _num_attr(t, "cy"), "is-on" in t) for t in re.findall(r"<circle class=\"fig__pt[^\"]*\"[^>]*>", svg)]
    points += [(_num_attr(t, "x") + 4, _num_attr(t, "y") + 4, "is-on" in t) for t in re.findall(r"<rect class=\"fig__pt[^\"]*\"[^>]*>", svg)]
    labels = []
    for tag, content in re.findall(r'(<text class="fig__pt-name[^"]*"[^>]*>)(.*?)</text>', svg, re.DOTALL):
        on = "is-on" in (_attr(tag, "class") or "")
        x, y = _num_attr(tag, "x"), _num_attr(tag, "y")
        bx = x + 7 if _attr(tag, "text-anchor") == "end" else x - 7
        near = [p for p in points if p[2] == on and abs(p[0] - bx) < 0.3 and p[1] <= y - 4 + 0.3]
        if not near:
            continue
        cx, cy, _ = max(near, key=lambda p: p[1])
        labels.append((cy, px(cx), text_of(content), on))
    placed, out = [], []

    def hits(ly, x0, width):
        return any(abs(ly - p[0]) < 13 and x0 < p[1] + p[2] and p[1] < x0 + width for p in placed)

    for cy, cx, name, on in sorted(labels):
        width = len(name) * CHAR
        fits_right, fits_left = cx + 7 + width <= NARROW, cx - 7 - width >= 0
        right_side = fits_right or not fits_left
        ly = cy + 4
        # Se il lato preferito e' occupato e l'altro e' libero, il nome cambia lato
        # invece di scivolare lontano dal suo punto.
        here, there = (cx + 7, cx - 7 - width) if right_side else (cx - 7 - width, cx + 7)
        if hits(ly, here, width) and (fits_left if right_side else fits_right) and not hits(ly, there, width):
            right_side = not right_side
        x0 = cx + 7 if right_side else cx - 7 - width
        while hits(ly, x0, width):
            ly += 13
        placed.append((ly, x0, width))
        anchor = "" if right_side else ' text-anchor="end"'
        tx = cx + 7 if right_side else cx - 7
        out.append(f'<text class="fig__pt-name{" is-on" if on else ""}" x="{tx:.1f}" y="{ly:.1f}"{anchor}>{escape(name)}</text>')

    def fix(tag, content, cls, whole):
        if content is not None:
            if cls.startswith("fig__pt-name"):
                return ""
            if cls == "fig__axis" and _attr(tag, "text-anchor") == "middle":
                return f"{_set(tag, 'x', px(_num_attr(tag, 'x')))}{content}</text>"
            if cls == "fig__axis":
                return f"{_set(tag, 'x', float(nl - 6))}{content}</text>"
            if cls.startswith("fig__axis-name"):
                return f"{_set(tag, 'x', float(nr if _attr(tag, 'text-anchor') == 'end' else nl))}{content}</text>"
            return whole
        if cls.startswith("fig__pt") and tag.startswith("<circle"):
            return _set(tag, "cx", px(_num_attr(tag, "cx")))
        if cls.startswith("fig__pt"):
            return _set(tag, "x", px(_num_attr(tag, "x") + 4) - 4)
        if cls.startswith("fig__grid"):
            if _attr(tag, "x1") == _attr(tag, "x2"):
                x = px(_num_attr(tag, "x1"))
                return _set(_set(tag, "x1", x), "x2", x)
            return _set(_set(tag, "x1", float(nl)), "x2", float(nr))
        return whole
    return _each(svg, fix).replace("</svg>", "".join(out) + "</svg>")


def _narrow(svg: str, kind: str, width: int) -> str | None:
    """Il taglio stretto del disegno, con gli id propri (i due tagli stanno nella stessa pagina)."""
    draw = {"bars": _narrow_bars, "lines": _narrow_lines, "scatter": _narrow_scatter}.get(kind)
    if not draw:
        return None
    try:
        narrow = draw(svg)
    except (AttributeError, ValueError, IndexError, TypeError, ZeroDivisionError):
        return None
    narrow = re.sub(rf'viewBox="0 ([\d.]+) {width} ', rf'viewBox="0 \1 {NARROW} ', narrow, count=1)
    narrow = re.sub(r'(<(?:title|desc)\b[^>]*\bid=")([^"]+)"', r'\1\2-s"', narrow)
    return re.sub(r'aria-labelledby="([^"]+)"', lambda m: 'aria-labelledby="' + " ".join(t + "-s" for t in m.group(1).split()) + '"',
                  narrow, count=1)


# ---------------------------------------------------------------- figure: i valori in tabella

def _bars_values(svg: str, caption: str) -> str | None:
    rows = _bar_rows(svg)
    if not rows:
        return None
    ref = _ref_label(svg)
    ref_value = _source_number(ref[1])[0] if ref else None
    out, refs = [], set()
    for _, name, _, value in rows:
        number = _source_number(value)
        if ref and ref_value is not None and number and number[0] < ref_value:
            refs.add(len(out))
            out.append([ref[0], ref[1]])
            ref = None
        out.append([name, value])
    if ref:
        refs.add(len(out))
        out.append([ref[0], ref[1]])
    # L'unita' e' l'ultima frase del sottotitolo quando non porta l'anno.
    sentences = [x.strip() for x in caption.rstrip(".").split(". ") if x.strip()]
    unit = sentences[-1] if len(sentences) > 1 and not YEAR.search(sentences[-1]) else "Valore"
    who = "Provincia" if "provinc" in caption.lower() else "Territorio"
    return _table(caption, [who, unit[:1].upper() + unit[1:]], out, "I valori del grafico", refs)


def _values(svg: str, caption: str, note: str) -> str | None:
    """La tabella dei valori per le linee e le dispersioni, letta dalla descrizione."""
    desc = text_of(" ".join(re.findall(r"<desc[^>]*>(.*?)</desc>", svg, re.DOTALL)))
    parts = [p.strip() for p in desc.split(";") if p.strip()]
    lines = [re.match(rf"(.+?): da ({NUMBER}) nel (\d{{4}}) a ({NUMBER}) nel (\d{{4}})$", p) for p in parts]
    if parts and all(lines):
        firsts, lasts = {m.group(3) for m in lines}, {m.group(5) for m in lines}
        if len(firsts) == 1 and len(lasts) == 1:
            head = ["Serie", firsts.pop(), lasts.pop()]
            rows = [[m.group(1), m.group(2), m.group(4)] for m in lines]
        else:
            head = ["Serie", "Primo anno", "Ultimo anno"]
            rows = [[m.group(1), Markup(f"{cell(m.group(2))} nel {m.group(3)}"), Markup(f"{cell(m.group(4))} nel {m.group(5)}")]
                    for m in lines]
        return _table(caption, head, rows, "I valori del grafico")
    points = [re.match(rf"(.+?): ({NUMBER}) e ({NUMBER})$", p) for p in parts]
    if parts and all(points):
        names = _svg_text(svg, "fig__axis-name")
        x_name = next((n for n in names if "→" in n), "Primo valore").replace("→", "").strip()
        y_name = next((n for n in names if "↑" in n), "Secondo valore").replace("↑", "").strip()
        unit = "Provincia" if "provincia" in note.lower() else "Regione" if "regione" in note.lower() else "Territorio"
        rows = [[m.group(1), m.group(2), m.group(3)] for m in points]
        return _table(caption, [unit, x_name[:1].upper() + x_name[1:], y_name[:1].upper() + y_name[1:]], rows,
                      "I valori del grafico")
    return None


def figure(block: str) -> str:
    """Una figura del generatore nella figura comune della 1.0; ogni altra passa com'e'.

    Il disegno lo scrive un programma della redazione, non questa pagina: se
    una sua variante non si lascia leggere, la figura resta quella di prima
    invece di rompere l'articolo."""
    try:
        return _figure(block)
    except (AttributeError, ValueError, IndexError, TypeError, ZeroDivisionError):
        return block


def _figure(block: str) -> str:
    m = re.search(r"<svg\b[^>]*\bclass=\"fig\"[^>]*>.*?</svg>", block, re.DOTALL)
    if not m:
        return block
    svg = m.group(0)
    view = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
    title = (_svg_text(svg, "fig__title") or [""])[0]
    if not view or not title:
        return block
    width, height = int(view.group(1)), int(view.group(2))
    subtitle = (_svg_text(svg, "fig__subtitle") or [""])[0]
    note = (_svg_text(svg, "fig__note") or [""])[0]
    source = (_svg_text(svg, "fig__source") or [""])[0]
    title_id = re.search(r'<title id="([^"]+)"', svg)
    base = re.sub(r"-t$", "", title_id.group(1)) if title_id else "fig-" + re.sub(r"\W+", "-", title.lower()).strip("-")[:40]
    # I valori si leggono dal disegno com'e' uscito dal generatore.
    kind = "bars" if "fig__bar" in svg else "scatter" if "fig__pt" in svg else "lines" if "fig__line" in svg else None
    caption = subtitle or title
    values = _bars_values(svg, caption) if kind == "bars" else _values(svg, caption, note)
    # Le righe tolte stanno a posti fissi (figures.py): titolo a 20, sottotitolo
    # a 40, nota a height-26, fonte a height-6. Il disegno resta fra le due.
    top = 40
    bottom = height - (40 if note else 20)
    for cls in ("fig__title", "fig__subtitle", "fig__note", "fig__source"):
        svg = _drop_text(svg, cls)
    svg = svg.replace(view.group(0), f'viewBox="0 {top} {width} {bottom - top}"', 1)
    # La descrizione e' letta ad alta voce: niente punto e virgola.
    svg = re.sub(r"(<desc[^>]*>)(.*?)(</desc>)", lambda d: d.group(1) + re.sub(r";\s*", ". ", d.group(2)) + d.group(3),
                 svg, flags=re.DOTALL)
    # Il tratteggio e' della media semplice: il valore Italia dell'Istat e' un
    # dato ufficiale e si disegna pieno.
    if (_svg_text(svg, "fig__ref-label") or [""])[0].startswith("Italia"):
        svg = svg.replace('class="fig__ref"', 'class="fig__ref fig__ref--official"')
    narrow = _narrow(svg, kind, width)
    out = [f'<figure class="figure art-fig" aria-labelledby="{base}-h">',
           f'<h3 class="figure__title" id="{base}-h">{escape(title)}</h3>']
    if subtitle:
        out.append(f'<p class="figure__note">{escape(subtitle)}</p>')
    if narrow:
        out.append(f'<div class="figure__chart chart"><div class="chart__l">{svg}</div><div class="chart__s">{narrow}</div></div>')
    else:
        out.append(f'<div class="figure__chart">{svg}</div>')
    if note:
        out.append(f'<p class="figure__note">{escape(note)}</p>')
    if source:
        out.append(f'<p class="source">{escape(source)}</p>')
    if values:
        out.append(f'<details class="more"><summary>I valori in tabella</summary>{values}</details>')
    out.append("</figure>")
    return "".join(out)


# ---------------------------------------------------------------- tabelle e citazioni

def _markdown_table(block: str) -> tuple[list[str], list[list[str]], set[int]] | None:
    """Intestazione, righe e righe di riferimento (in corsivo) di una tabella Markdown."""
    head = [text_of(h) for h in re.findall(r"<th[^>]*>(.*?)</th>", block.split("</thead>")[0], re.DOTALL)]
    body_rows = re.findall(r"<tr>(.*?)</tr>", block.split("</thead>")[-1], re.DOTALL)
    if not head or not body_rows:
        return None
    rows, refs = [], set()
    for row in body_rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
        if not cells:
            continue
        if cells[0].strip().startswith("<em>"):
            refs.add(len(rows))
        rows.append([text_of(c) for c in cells])
    return head, rows, refs


def table(block: str) -> str:
    """Una tabella Markdown con didascalia, scope, la riga di riferimento e le cifre di numfmt."""
    parsed = _markdown_table(block)
    if not parsed:
        return block
    head, rows, refs = parsed
    if len(head) == 2:
        caption = f"{head[1]}, per {head[0][:1].lower()}{head[0][1:]}"
    else:
        caption = ", ".join(head)
    return _table(caption, head, rows, caption, refs, visible_caption=True)


def quote(block: str) -> str:
    """Una frase della redazione in evidenza non e' la citazione di una fonte."""
    if "<a " in block or "«" in block:
        return block
    return block.replace("<blockquote>", '<blockquote class="pull">', 1)


# ---------------------------------------------------------------- copertina

def _raster_size(head: bytes) -> tuple[int, int] | None:
    """Larghezza e altezza scritte nell'intestazione di un PNG, un JPEG o un WebP."""
    if head[:8] == b"\x89PNG\r\n\x1a\n" and len(head) >= 24:
        return struct.unpack(">II", head[16:24])
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP" and len(head) >= 30:
        chunk = head[12:16]
        if chunk == b"VP8 ":
            w, h = struct.unpack("<HH", head[26:30])
            return w & 0x3FFF, h & 0x3FFF
        if chunk == b"VP8L":
            bits = int.from_bytes(head[21:25], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        if chunk == b"VP8X":
            return int.from_bytes(head[24:27], "little") + 1, int.from_bytes(head[27:30], "little") + 1
        return None
    if head[:2] == b"\xff\xd8":
        # Il JPEG: si scorrono i segmenti fino al primo SOF, che porta le misure.
        i = 2
        while i + 9 <= len(head):
            if head[i] != 0xFF:
                return None
            marker = head[i + 1]
            if marker == 0xFF:
                i += 1
                continue
            if marker in (0x01, 0xD8) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", head[i + 5:i + 9])
                return w, h
            i += 2 + struct.unpack(">H", head[i + 2:i + 4])[0]
    return None


@lru_cache(maxsize=256)
def image_size(path: str | None) -> tuple[int, int] | None:
    """Le misure vere dell'immagine sul disco, per width e height senza salti.

    Un SVG le dice nel viewBox, un raster nella sua intestazione. Se non si
    leggono si omettono: un'immagine senza misure salta al caricamento, una
    con le misure sbagliate si deforma. Le immagini del sito sono immutabili
    per la vita del processo, quindi si leggono una volta."""
    if not path or not path.startswith("/static/"):
        return None
    local = STATIC_DIR / path.removeprefix("/static/")
    try:
        if local.suffix == ".svg":
            m = re.search(r'viewBox="[\d.]+ [\d.]+ ([\d.]+) ([\d.]+)"', local.read_text(encoding="utf-8")[:2000])
            return (round(float(m.group(1))), round(float(m.group(2)))) if m else None
        with local.open("rb") as file:
            size = _raster_size(file.read(1 << 18))
    except (OSError, ValueError, struct.error):
        return None
    return size if size and size[0] > 0 and size[1] > 0 else None


def hero(post: dict) -> dict | None:
    """La copertina come immagine d'apertura: l'immagine, le sue proporzioni, didascalia e credito."""
    cover = post.get("cover")
    if not cover:
        return None
    return {"src": cover, "alt": post.get("cover_alt") or "", "size": image_size(cover),
            "caption": post.get("cover_caption") or None, "credit": post.get("cover_credit") or None}


def _source_decimals(values: list[float]) -> int:
    """I decimali che la fonte scrive: quelli del valore che ne ha di piu', fino a due."""
    return max((len(f"{round(v, 6):g}".partition(".")[2]) for v in values), default=0) if values else 0


def _unit_from_tables(items: list[str], name: str) -> str | None:
    """L'unita' che la redazione scrive nell'intestazione della sua tabella:
    "Indice di vecchiaia 2026 (anziani per 100 giovani)" -> "anziani per 100 giovani"."""
    for block in items:
        if tag_of(block)[0] != "table":
            continue
        for th in re.findall(r"<th[^>]*>(.*?)</th>", block, re.DOTALL):
            m = re.search(r"\(([^)]+)\)\s*$", text_of(th))
            if m and name.lower()[:12] in text_of(th).lower() and not _is_year(m.group(1)):
                return m.group(1)
    return None


def _piece_table(items: list[str]) -> dict | None:
    """La prima tabella del pezzo che dichiara un anno nell'intestazione
    ("PIL pro capite 2024 (euro)"): l'anno, la cifra scritta per ogni
    territorio, i decimali della colonna e le righe della media in corsivo."""
    for block in items:
        if tag_of(block)[0] != "table":
            continue
        parsed = _markdown_table(block)
        if not parsed or len(parsed[0]) != 2:
            continue
        head, rows, refs = parsed
        year = YEAR.search(head[1])
        if not year:
            continue
        return {
            "year": int(year.group(1)),
            "written": {_key(r[0]): r[1] for n, r in enumerate(rows) if n not in refs and len(r) > 1},
            "decimals": _column_decimals(rows, 1)[1],
            "averages": [r[1] for n, r in enumerate(rows) if n in refs and len(r) > 1 and r[0].startswith("Media")],
        }
    return None


def _key(name: str) -> str:
    """Un nome di territorio confrontabile: "Trentino-Alto Adige" e "Trentino Alto Adige" coincidono."""
    return re.sub(r"[^a-z]", "", name.lower())


def _tag_year(post: dict) -> int | None:
    """L'anno dei dati dall'etichetta "Dati 2024" del pezzo."""
    for tag in post.get("tags") or []:
        m = re.fullmatch(r"Dati ((?:19|20)\d\d)", str(tag).strip())
        if m:
            return int(m.group(1))
    return None


def piece_year(post: dict, items: list[str]) -> int | None:
    """L'anno dei dati di cui parla il pezzo, non l'ultimo della serie.

    La serie dell'app si allunga dopo la pubblicazione: un pezzo sui dati del
    2024 non diventa un pezzo sul 2025 perche' l'Istat ha aggiunto un anno."""
    table_ = _piece_table(items)
    return table_["year"] if table_ else _tag_year(post)


def lead_strip(post: dict, items: list[str], year: int | None) -> dict | None:
    """La figura d'apertura quando la copertina e' un grafico: la striscia del
    divario dello stesso indicatore, nell'anno del pezzo, dai dati dell'app.

    Le cifre della striscia sono quelle della tabella del pezzo, con i suoi
    decimali: se un territorio che la tabella nomina ha oggi un altro valore
    (la fonte ha rivisto la serie), la striscia smentirebbe l'articolo che le
    sta sotto, e si toglie."""
    meta = post.get("indicator_meta") or {}
    ident = post.get("indicator")
    if not ident or not year:
        return None
    from app.data import get_indicator_year

    data = get_indicator_year(str(ident), int(year))
    values = [v for v in (data or {}).get("values") or [] if v.get("value") is not None]
    if len(values) < 5:
        return None
    areas = charts.area_map()
    rows = [{"key": v["region_key"], "name": v["region"], "value": v["value"], "area": areas.get(v["region_key"])} for v in values]
    table_ = _piece_table(items)
    if table_ and table_["year"] != year:
        table_ = None
    dec = table_["decimals"] if table_ and table_["decimals"] is not None else min(2, _source_decimals([r["value"] for r in rows]))
    avg = sum(r["value"] for r in rows) / len(rows)
    if table_:
        by_key = {_key(r["name"]): r for r in rows}
        for name, written in table_["written"].items():
            row = by_key.get(name)
            source = _source_number(written)
            if row is None or source is None or numfmt.text(row["value"], dec) != numfmt.text(source[0], dec):
                return None
        # La media della striscia e' quella della tabella: se i dati di oggi
        # contano altri territori (o ne mancano), le due medie si smentiscono.
        for written in table_["averages"]:
            source = _source_number(written)
            if source is None or numfmt.text(avg, dec) != numfmt.text(source[0], dec):
                return None
    lo, hi = min(r["value"] for r in rows), max(r["value"] for r in rows)
    strip = charts.divario_strip(rows, avg, meta.get("unit"), hi / lo if lo > 0 else None,
                                 avg_label=f"Media semplice {numfmt.text(avg, dec)}", decimals=dec)
    if not strip.get("svg"):
        return None

    south = [r for r in rows if r["area"] == "sud"]
    above = [r for r in south if r["value"] > avg]
    n = len(south)
    if not south:
        title = f"Nel {year} {len([r for r in rows if r['value'] > avg])} regioni su {len(rows)} stanno sopra la media semplice"
    elif len(above) == n:
        title = f"Nel {year} tutte le {count_word(n)} regioni del Mezzogiorno stanno sopra la media semplice"
    elif not above:
        title = f"Nel {year} tutte le {count_word(n)} regioni del Mezzogiorno stanno sotto la media semplice"
    else:
        below = n - len(above)
        verb_a = "sta" if len(above) == 1 else "stanno"
        noun = "regione" if len(above) == 1 else "regioni"
        title = (f"Nel {year} {count_word(len(above))} {noun} del Mezzogiorno su {count_word(n)} {verb_a} "
                 f"sopra la media semplice, {count_word(below)} sotto")
    unit = _unit_from_tables(items, meta.get("name") or "")
    source_name = meta.get("source_label") or meta.get("source")
    return {
        "title": title, "strip": strip, "unit": unit, "decimals": dec, "year": year, "avg": avg,
        "rows": sorted(rows, key=lambda r: -r["value"]), "area_label": charts.AREA_LABEL,
        "note": (f"Ogni punto è una regione, nel colore della sua ripartizione{', ' + unit if unit else ''}, {year}."
                 + (f" Fonte: {source_name}. Elaborazione Divario Italia." if source_name else " Elaborazione Divario Italia.")),
    }


def indicator_card(post: dict) -> dict | None:
    """La scheda dell'indicatore nella corsia "I dati": l'ultima media e la sua
    sparkline col pavimento.

    La serie e' quella del catalogo (`meta.spark`), la media semplice delle
    regioni che hanno il dato anno per anno: la card lo dice in chiaro, perche'
    in un anno possono mancare delle regioni. Il pavimento e' lo scarto
    interquartile delle regioni nell'anno dell'ultimo punto, letto con
    `get_atlas_indicator_year`, che serve ogni famiglia (non solo le serie
    Istat territoriali). None quando la scheda non ha una serie."""
    meta = post.get("indicator_meta") or {}
    spark = [p for p in meta.get("spark") or [] if p.get("value") is not None]
    if not post.get("indicator") or not spark:
        return None
    from app.atlas_catalog import get_atlas_indicator_year

    last = spark[-1]
    data = get_atlas_indicator_year(str(post["indicator"]), last["year"])
    floor = charts.spark_floor([row["value"] for row in data["values"]]) if data else None
    return {"value": last["value"], "year": last["year"], "unit": figure_unit(meta.get("name"), meta.get("unit")),
            "spark": spark, "floor": floor}


# ---------------------------------------------------------------- pagina

# Il percorso di uno script interno non dice niente a chi legge: la regia lo
# toglie dalle righe di "Dati e metodo" (resta nel front matter, nel JSON-LD
# e nel repo). Tre forme: la frase che e' solo il percorso ("Script
# `scripts/...`."), l'inciso fra parentesi, la coda di una frase ("con lo
# script scripts/...", ", calcolata da scripts/...").
_PATH = r"(?:<code>)?scripts/[\w/.-]*\w(?:</code>)?"
_PATH_ALONE = re.compile(r"\s*\bScript\s+" + _PATH + r"\s*\.")
_PATH_PAREN = re.compile(r"\s*\((?:[^()]*?\s)?" + _PATH + r"\)")
_PATH_TAIL = re.compile(r",?\s*(?:con lo |lo )?(?:script\s+|(?:calcolat[oa] )?(?:da|con)\s+)" + _PATH)


def without_paths(html: str | None) -> str | None:
    if not html:
        return html
    for rx in (_PATH_ALONE, _PATH_PAREN, _PATH_TAIL):
        html = rx.sub("", html)
    return html


def derive(ctx: dict) -> dict:
    post = ctx["post"]
    meta = post.get("indicator_meta") or {}
    dataset = post.get("dataset") or {}
    items = blocks(post.get("body_html") or "")

    # La risposta in breve: la frase evidenziata e l'elenco "In breve".
    callout = None
    for i, block in enumerate(items):
        if tag_of(block)[0] == "p" and "data-callout" in tag_of(block)[1]:
            callout = re.sub(r"^<p[^>]*>|</p>$", "", block).strip()
            del items[i]
            break
    brief = take_section(items, "in-breve")
    brief_list = "".join(brief[1:]) if brief else None

    # Dati e metodo: le sezioni della redazione, parola per parola.
    used = take_section(items, "dati-usati")
    sources_ = take_section(items, "fonti")
    data_note = None
    if items and re.match(r"<p>\s*<em>\s*Dati:", items[-1]):
        data_note = items.pop()

    year = piece_year(post, items)
    cover = post.get("cover") or ""
    # Una copertina SVG e' una vecchia scheda social: apre la striscia, e la
    # copertina resta solo se la striscia non si puo' disegnare.
    lead = lead_strip(post, items, year) if cover.endswith(".svg") else None
    opening = None if lead else hero(post)

    items = [figure(b) if tag_of(b)[0] == "figure" else table(b) if tag_of(b)[0] == "table"
             else quote(b) if tag_of(b)[0] == "blockquote" else b for b in items]

    # Il rimando: alla fine della sezione della prima figura o tabella, e mai
    # dopo un altro link a una scheda.
    anchor = next((i for i, b in enumerate(items) if b.startswith(("<figure", '<div class="tablewrap"', '<div class="stackwrap'))), None)
    if anchor is None:
        anchor = next((i for i, b in enumerate(items) if tag_of(b)[0] == "h2"), 0)
    split = section(items, anchor) if items else 0
    first_link = next((i for i, b in enumerate(items) if 'href="/indicatore/' in b), None)
    if first_link is not None and first_link < split:
        split = first_link

    toc = [{"id": heading_id(b), "text": text_of(b)} for b in items if tag_of(b)[0] == "h2" and heading_id(b)]

    # Continua a esplorare: le destinazioni che il pezzo stesso nomina.
    seen = {post.get("indicator_path"), "/blog/" + post["slug"]}
    related_slugs = {"/blog/" + r["slug"] for r in ctx.get("related") or []}
    named = {"indicatore": [], "territorio": [], "blog": []}
    # Prima i link della prosa, poi quelli delle tabelle, che legano ogni riga:
    # i territori che il pezzo nomina contano piu' di quelli che elenca.
    boxes = ("<figure", '<div class="tablewrap"', '<div class="stackwrap')
    ordered = "".join(b for b in items if not b.startswith(boxes)) + "".join(b for b in items if b.startswith(boxes))
    for path, label in re.findall(r'<a href="(/(?:indicatore|regione|provincia|blog)/[^"#?]+)">(.*?)</a>', ordered, re.DOTALL):
        if path in seen or path in related_slugs:
            continue
        seen.add(path)
        text = text_of(label)
        kind = "indicatore" if path.startswith("/indicatore/") else "blog" if path.startswith("/blog/") else "territorio"
        named[kind].append({"path": path, "label": text[:1].upper() + text[1:]})
    named["territorio"] = named["territorio"][:TERRITORY_NAMED_MAX]

    related = []
    for item in ctx.get("related") or []:
        if item["slug"] == post["slug"]:
            continue
        related.append({**item, "size": image_size(item.get("cover")), "date_label": date_it(item.get("date"))})

    period = (dataset.get("temporal") or "").replace("/", "-") or (str(year) if year else None)
    institution = dataset.get("creator") or meta.get("source_label") or meta.get("source")
    # La licenza dei dati del pezzo: quella del sito se coincide, altrimenti
    # il link della fonte con il suo nome generico.
    license_url = dataset.get("license") or sources.LICENSE_URL
    license_label = sources.LICENSE_LABEL if license_url == sources.LICENSE_URL else "la licenza indicata dalla fonte"
    citation = f"Divario Italia, «{post['title']}», {date_it(post.get('date'))}. {ctx.get('canonical') or post.get('url')}"

    return {
        "callout": callout,
        "brief_title": text_of(brief[0]) if brief else None,
        "brief_list": brief_list,
        "body_before": "\n".join(items[:split]),
        "body_after": "\n".join(items[split:]),
        "toc": toc,
        "used": without_paths("".join(used[1:])) if used else None,
        # Il metodo del front matter ripete "Dati usati" quando la redazione
        # l'ha scritto: in pagina va una volta sola.
        "method": None if used else without_paths(dataset.get("method")),
        "dataset_text": None if used else dataset.get("description"),
        "sources": "".join(sources_[1:]).replace("<ul>", '<ul class="reflist">', 1) if sources_ else None,
        "data_note": re.sub(r"</?em>", "", data_note) if data_note else None,
        "named": named,
        "related": related[:3],
        "hero": opening,
        "lead": lead,
        "published": date_it(post.get("date")),
        "modified": date_it(post.get("date_modified")) if post.get("date_modified") != post.get("date") else None,
        "reviewed": date_it(post.get("date_modified") or post.get("date")),
        "period": period,
        "institution": institution,
        "theme_path": f"/tema/{meta['theme_slug']}" if meta.get("theme_slug") else None,
        "theme": meta.get("theme"),
        "indicator_card": indicator_card(post),
        "indicator_years": (f"dal {meta['year_min']} al {meta['year_max']}"
                            if meta.get("year_min") and meta.get("year_max") and meta["year_min"] != meta["year_max"]
                            else f"nel {meta['year_max']}" if meta.get("year_max") else None),
        "license": {"url": license_url, "label": license_label},
        "citation": citation,
    }
