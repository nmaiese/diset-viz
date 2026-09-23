"""L'articolo del blog nella veste 1.0: le parti nuove, composte dal pezzo vero.

Il corpo arriva gia' in HTML (`post.body_html`), scritto dalla redazione. Qui
non si riscrive una parola: si smonta in blocchi di primo livello e si rimonta
nell'ordine di SISTEMA.md.

- La frase evidenziata (`p.data-callout`) e "In breve" salgono in testa, come
  risposta in breve.
- "Dati usati", "Fonti" e la riga finale "Dati: ..." scendono nel blocco unico
  "Dati e metodo".
- Ogni figura di `scripts/trend_articles/figures.py` perde titolo, sottotitolo,
  nota e fonte dentro l'SVG, che tornano come testo HTML sopra e sotto il
  disegno, e guadagna la tabella dei valori letti dal disegno stesso.
- Le tabelle Markdown prendono didascalia, `scope` e la riga di riferimento.
- Il rimando alla scheda va alla fine della sezione della prima figura o della
  prima tabella, e comunque prima di ogni altro link a una scheda: la guardia
  sulla collisione dei titoli legge il primo `href` verso `/indicatore/`.

Gli id del corpo portano il segnaposto `MARK`: il template lo sostituisce con
`aid('')`, cosi' nell'Artifact si prefissano come quelli dei template.
"""

from __future__ import annotations

import re
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path

import derive as shared

ROOT = Path(__file__).resolve().parents[4]
MARK = "__aid__"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
NUMBER = r"-?\d[\d.]*(?:,\d+)?"


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


def mark_ids(html: str) -> str:
    """Gli id, le ancore e i riferimenti aria del corpo col segnaposto del prefisso."""
    html = re.sub(r'(?<![\w-])id="', f'id="{MARK}', html)
    html = re.sub(r'href="#', f'href="#{MARK}', html)
    return re.sub(r'aria-labelledby="([^"]+)"',
                  lambda m: 'aria-labelledby="' + " ".join(MARK + t for t in m.group(1).split()) + '"', html)


# ---------------------------------------------------------------- figure

def _svg_text(svg: str, cls: str) -> list[str]:
    return [text_of(m) for m in re.findall(rf'<text class="{cls}(?: [^"]*)?"[^>]*>(.*?)</text>', svg, re.DOTALL)]


def _drop_text(svg: str, cls: str) -> str:
    return re.sub(rf'\s*<text class="{cls}"[^>]*>.*?</text>', "", svg, flags=re.DOTALL)


def _it_number(text: str) -> float | None:
    m = re.search(NUMBER, text or "")
    if not m:
        return None
    try:
        return float(m.group(0).replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _table(caption: str, head: list[str], rows: list[list[str]], label: str, ref_rows: set[int] = frozenset()) -> str:
    """Una tabella dati del sistema: didascalia, scope, cifre a destra."""
    right = ' class="r"'
    th = "".join(f'<th scope="col"{right if i else ""}>{escape(h)}</th>' for i, h in enumerate(head))
    body = []
    for n, row in enumerate(rows):
        cells = "".join(f'<td class="val">{escape(c)}</td>' for c in row[1:])
        cls = ' class="ref"' if n in ref_rows else ""
        body.append(f'<tr{cls}><th scope="row">{escape(row[0])}</th>{cells}</tr>')
    return (f'<div class="tablewrap" tabindex="0" role="region" aria-label="{escape(label)}">'
            f'<table class="table table--compact"><caption class="sr-only">{escape(caption)}</caption>'
            f'<thead><tr>{th}</tr></thead><tbody>{"".join(body)}</tbody></table></div>')


def _bars(svg: str, caption: str) -> str | None:
    """La classifica a barre del disegno come tabella con le barre: la veste del
    telefono, dove il testo dell'SVG scenderebbe a sei pixel."""
    rows = re.findall(r'<text class="fig__name( is-on)?"[^>]*>(.*?)</text>\s*'
                      r'<rect class="fig__bar(?: is-on)?"[^>]*\bwidth="([\d.]+)"[^>]*/>\s*'
                      r'<text class="fig__value(?: is-on)?"[^>]*>(.*?)</text>', svg, re.DOTALL)
    if not rows:
        return None
    widest = max(float(w) for _, _, w, _ in rows) or 1
    ref = _svg_text(svg, "fig__ref-label")
    ref_row = None
    if ref:
        m = re.match(rf"(.*\S)\s+({NUMBER})$", ref[0])
        if m and _it_number(m.group(2)) is not None:
            ref_row = (m.group(1)[:1].upper() + m.group(1)[1:], m.group(2), _it_number(m.group(2)))
    out = []
    for on, name, width, value in rows:
        number = _it_number(text_of(value))
        if ref_row and number is not None and number < ref_row[2]:
            out.append(f'<tr class="ref"><th scope="row">{escape(ref_row[0])}</th><td class="barcell" aria-hidden="true"></td>'
                       f'<td class="val">{escape(ref_row[1])}</td></tr>')
            ref_row = None
        pct = round(float(width) / widest * 100, 1)
        cls = ' class="is-on"' if on else ""
        out.append(f'<tr{cls}><th scope="row">{escape(text_of(name))}</th>'
                   f'<td class="barcell" aria-hidden="true"><span class="bar"><i style="width: {pct}%"></i></span></td>'
                   f'<td class="val">{escape(text_of(value))}</td></tr>')
    if ref_row:
        out.append(f'<tr class="ref"><th scope="row">{escape(ref_row[0])}</th><td class="barcell" aria-hidden="true"></td>'
                   f'<td class="val">{escape(ref_row[1])}</td></tr>')
    # L'unita' e' l'ultima frase del sottotitolo quando non porta l'anno.
    sentences = [x.strip() for x in caption.rstrip(".").split(". ") if x.strip()]
    unit = sentences[-1] if len(sentences) > 1 and not re.search(r"\b(19|20)\d\d\b", sentences[-1]) else "Valore"
    who = "Provincia" if "provinc" in caption.lower() else "Territorio"
    return ('<div class="art-bars"><table class="table table--compact">'
            f'<caption class="sr-only">{escape(caption)}</caption>'
            f'<thead><tr><th scope="col">{who}</th><th class="barcell" scope="col"><span class="sr-only">Barra</span></th>'
            f'<th class="r" scope="col">{escape(unit[:1].upper() + unit[1:])}</th></tr></thead><tbody>{"".join(out)}</tbody></table></div>')


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
            rows = [[m.group(1), f"{m.group(2)} nel {m.group(3)}", f"{m.group(4)} nel {m.group(5)}"] for m in lines]
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
    """Una figura del generatore nella grammatica della 1.0; ogni altra passa com'e'."""
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
    caption = subtitle or title
    bars = _bars(svg, caption)
    values = None if bars else _values(m.group(0), caption, note)
    kind = "bars" if bars else "chart"
    out = [f'<figure class="art-fig art-fig--{kind}">',
           f'<figcaption class="art-fig__head"><h3 class="h-sub">{escape(title)}</h3>'
           + (f'<p class="subline">{escape(subtitle)}</p>' if subtitle else "") + "</figcaption>",
           f'<div class="art-fig__chart">{svg}</div>' if not bars else
           f'<div class="art-fig__chart"><div class="art-fig__l">{svg}</div>{bars}</div>']
    if note:
        out.append(f'<p class="art-fig__note">{escape(note)}</p>')
    if source:
        out.append(f'<p class="source">{escape(source)}</p>')
    if values:
        out.append(f'<details class="more"><summary>I valori in tabella</summary>{values}</details>')
    out.append("</figure>")
    return "".join(out)


# ---------------------------------------------------------------- tabelle e citazioni

def table(block: str) -> str:
    """Una tabella Markdown con didascalia, scope e la riga di riferimento."""
    head = [text_of(h) for h in re.findall(r"<th[^>]*>(.*?)</th>", block.split("</thead>")[0], re.DOTALL)]
    body_rows = re.findall(r"<tr>(.*?)</tr>", block.split("</thead>")[-1], re.DOTALL)
    if not head or not body_rows:
        return block
    rows, refs = [], set()
    for n, row in enumerate(body_rows):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
        if not cells:
            continue
        if cells[0].strip().startswith("<em>"):
            refs.add(len(rows))
        rows.append([text_of(c) for c in cells])
    if len(head) == 2:
        caption = f"{head[1]}, per {head[0][:1].lower()}{head[0][1:]}"
    else:
        caption = ", ".join(head)
    return _table(caption, head, rows, caption, refs).replace('<caption class="sr-only">', "<caption>", 1)


def quote(block: str) -> str:
    """Una frase della redazione in evidenza non e' la citazione di una fonte."""
    if "<a " in block or "«" in block:
        return block
    return block.replace("<blockquote>", '<blockquote class="pull">', 1)


# ---------------------------------------------------------------- copertina

def image_size(path: str | None) -> tuple[int, int] | None:
    """Le misure vere dell'immagine sul disco, per width e height senza salti."""
    if not path:
        return None
    local = ROOT / "app" / path.lstrip("/")
    if not local.exists():
        return None
    if local.suffix == ".svg":
        m = re.search(r'viewBox="[\d.]+ [\d.]+ ([\d.]+) ([\d.]+)"', local.read_text(encoding="utf-8")[:600])
        return (round(float(m.group(1))), round(float(m.group(2)))) if m else None
    try:
        from PIL import Image

        with Image.open(local) as img:
            return img.size
    except OSError:
        return None


# ---------------------------------------------------------------- pagina

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
    sources = take_section(items, "fonti")
    data_note = None
    if items and re.match(r"<p>\s*<em>\s*Dati:", items[-1]):
        data_note = items.pop()

    items = [figure(b) if tag_of(b)[0] == "figure" else table(b) if tag_of(b)[0] == "table"
             else quote(b) if tag_of(b)[0] == "blockquote" else b for b in items]

    # Il rimando: alla fine della sezione della prima figura o tabella, e mai
    # dopo un altro link a una scheda.
    anchor = next((i for i, b in enumerate(items) if b.startswith(("<figure", '<div class="tablewrap"'))), None)
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
    for path, label in re.findall(r'<a href="(/(?:indicatore|regione|provincia|blog)/[^"#?]+)">(.*?)</a>', "".join(items), re.DOTALL):
        if path in seen or path in related_slugs:
            continue
        seen.add(path)
        text = text_of(label)
        kind = "indicatore" if path.startswith("/indicatore/") else "blog" if path.startswith("/blog/") else "territorio"
        named[kind].append({"path": path, "label": text[:1].upper() + text[1:]})

    cover_size = image_size(post.get("cover"))
    related = []
    for item in ctx.get("related") or []:
        if item["slug"] == post["slug"]:
            continue
        related.append({**item, "size": image_size(item.get("cover")), "date_label": shared.date_it(item.get("date"))})

    period = (dataset.get("temporal") or "").replace("/", "-") or (str(meta["year_max"]) if meta.get("year_max") else None)
    institution = dataset.get("creator") or meta.get("source_label") or meta.get("source")
    read = post.get("read_time")
    # La licenza dei dati del pezzo: quella del sito se coincide, altrimenti
    # il link della fonte con il suo nome generico.
    license_url = dataset.get("license") or ctx.get("data_license_url")
    license_label = (ctx.get("data_license_label") if license_url == ctx.get("data_license_url")
                     else "la licenza indicata dalla fonte")
    citation = f"Divario Italia, «{post['title']}», {shared.date_it(post.get('date'))}. {ctx.get('canonical')}"

    return {
        "mark": MARK,
        "callout": callout,
        "brief_title": text_of(brief[0]) if brief else None,
        "brief_list": brief_list,
        "body_before": mark_ids("\n".join(items[:split])),
        "body_after": mark_ids("\n".join(items[split:])),
        "toc": toc,
        "used": "".join(used[1:]) if used else None,
        "sources": "".join(sources[1:]).replace("<ul>", '<ul class="reflist">', 1) if sources else None,
        "data_note": re.sub(r"</?em>", "", data_note) if data_note else None,
        "named": named,
        "related": related[:3],
        "cover_size": cover_size,
        "published": shared.date_it(post.get("date")),
        "modified": shared.date_it(post.get("date_modified")) if post.get("date_modified") != post.get("date") else None,
        "reviewed": shared.date_it(post.get("date_modified") or post.get("date")),
        "read_label": (f"{read} minuto di lettura" if read == 1 else f"{read} minuti di lettura") if read else None,
        "period": period,
        "institution": institution,
        "theme_path": f"/tema/{meta['theme_slug']}" if meta.get("theme_slug") else None,
        "theme": meta.get("theme"),
        "indicator_years": (f"dal {meta['year_min']} al {meta['year_max']}"
                            if meta.get("year_min") and meta.get("year_max") and meta["year_min"] != meta["year_max"]
                            else f"nel {meta['year_max']}" if meta.get("year_max") else None),
        "license": {"url": license_url, "label": license_label},
        "citation": citation,
    }
