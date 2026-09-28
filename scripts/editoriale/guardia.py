"""La guardia deterministica sulla prosa di una scheda indicatore, scritta a mano.

    bin/py -m scripts.editoriale.guardia ter-12
    bin/py -m scripts.editoriale.guardia ter-12 --dossier lavoro/ter-12/dossier.json
    bin/py -m scripts.editoriale.guardia ter-12 --dossier lavoro/ter-12/dossier.json --fonti lavoro/ter-12/fonti.md

Il test che verificava i testi scritti a mano, `tests/integration/test_indicator_texts.py`,
e' stato tolto nel commit `eb2c2f72`. Da allora un articolo puo' pubblicare una
cifra sbagliata, un link non canonico, un marcatore `<!-- grafico -->` che punta
a un indicatore inesistente e sparisce in silenzio, o una sezione `libera`
senza titolo che il renderer scarta senza dirlo a nessuno. Questa e' **una**
guardia deterministica e bloccante: la leggibilita' la giudica il revisore, non
un lint, quindi qui non c'e' niente che giudichi la prosa.

Cinque controlli, tutti meccanici:

1. **Cifre contro il dossier**, solo quando `--dossier` e' dato. Ogni numero
   scritto in cifre nel testo deve corrispondere, con l'arrotondamento con cui
   e' scritto, a una cifra del dossier o della colonna "citazione letterale"
   di `--fonti`. Quando il numero non porta un segno esplicito (la direzione e'
   detta a parole, "e' sceso di 2,1 punti") si confronta il valore assoluto:
   e' il difetto di `gate2_verify.py`, che confrontava il segno e basta.
2. **Link interni canonici**: `/indicatore/<slug>/<codice>`, mai `/?indicator=`.
3. **Marcatori dei grafici che si disegnano davvero**, con `app/charts.py`.
4. **Sezioni `libera` senza titolo**: bloccanti, come lo sono gia' in pagina.
5. **Assoluti tipografici**: mai `—`, `–`, `;`, `…`.

Anni, ranghi e piccoli conteggi non passano dal controllo 1: il modo e'
documentato accanto a `NUMBER_RE`, qui sotto.

Il vincolo decisivo e' restare verdi su tutti gli articoli committati. Nessun
articolo del catalogo porta oggi un dossier o un file di fonti (`lavoro/` non
e' nel repo), quindi sul catalogo reale girano solo i controlli 2-5; il
controllo 1 lo esercita solo chi passa `--dossier`, ed e' provato a parte nei
test con un dossier costruito apposta.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from app import charts, sources
from app.design import numfmt
from app.indicator_texts import DEFAULT_LEVEL, LIBERA
from app.indicator_view import build_indicator_view
from scripts import indicator_store
from scripts.editoriale import brief
from scripts.prose_lint import LINK, prose_fields


class Defect:
    """Un difetto trovato: il controllo che l'ha visto, dove, la frase citata."""

    __slots__ = ("check", "field", "quote", "message")

    def __init__(self, check, field, quote, message):
        self.check = check
        self.field = field
        self.quote = quote
        self.message = message

    def __repr__(self):
        return f"Defect({self.check!r}, {self.field!r}, {self.quote!r}, {self.message!r})"

    def __eq__(self, other):
        if not isinstance(other, Defect):
            return NotImplemented
        return (self.check, self.field, self.quote, self.message) == \
            (other.check, other.field, other.quote, other.message)

    def line(self):
        return f"[{self.check}] {self.field}: {self.message} -- {self.quote!r}"


def _excerpt(text, start, end, radius=30):
    """La frase citata: il testo colpito con un po' di contesto attorno."""
    a, b = max(0, start - radius), min(len(text), end + radius)
    prefix = "..." if a > 0 else ""
    suffix = "..." if b < len(text) else ""
    return f"{prefix}{text[a:b].strip()}{suffix}"


# --- il controllo 1: le cifre -----------------------------------------------
#
# Un numero scritto in cifre e' "controllabile" solo quando porta con se' la
# prova di essere una misura e non un anno, un rango o un piccolo conteggio:
#
# - una virgola decimale ("9,8", "-2,1"): sempre controllabile, e' cosi' che si
#   scrive una cifra reale in questo sito;
# - un separatore delle migliaia ("21.702"): sempre controllabile, nessun anno
#   e nessun conteggio arriva a quattro cifre con un punto;
# - seguito subito da "%" senza spazio ("116%"): controllabile anche intero,
#   perche' il segno di percentuale toglie l'ambiguita';
# - in ogni altro caso (un intero nudo: "2025", "venti" non c'entra perche' e'
#   una parola, "14" davanti a "posizione") e' un anno, un rango scritto in
#   cifre ("14ª", escluso anche perche' seguito da "ª"/"°") o un piccolo
#   conteggio: non si controlla, perche' la fonte di questi numeri non e' mai
#   una cifra del dossier ma il catalogo dei territori o il calendario.
NUMBER_RE = re.compile(
    r"(?<![\w.,%])(?P<sign>[+-])?(?P<int>\d{1,3}(?:\.\d{3})+|\d+)(?:,(?P<dec>\d+))?"
)
RANK_SUFFIXES = ("ª", "°")


def _number_value(sign, int_part, dec):
    digits = int_part.replace(".", "")
    value = float(f"{digits}.{dec}") if dec else float(digits)
    return -value if sign == "-" else value


def _is_checkable(match, text):
    if match.group("dec") or "." in match.group("int"):
        return text[match.end():match.end() + 1] not in RANK_SUFFIXES
    return text[match.end():match.end() + 1] == "%" or bool(re.match(r"\.\d{1,2}(?!\d)", text[match.end():]))


def dossier_figures(dossier):
    """Ogni cifra `{"valore": ..., "testo": ...}` del dossier, come float."""
    found = []

    def walk(node):
        if isinstance(node, dict):
            value = node.get("valore")
            if "testo" in node and isinstance(value, (int, float)) and not isinstance(value, bool):
                found.append(float(value))
                return
            for item in node.values():
                walk(item)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(dossier)
    return found


def source_figures(path):
    """Le cifre della colonna "citazione letterale" di un file `fonti.md`.

    Una tabella Markdown con una colonna la cui intestazione contiene
    "citazione letterale" (case-insensitive): ogni numero scritto in cifre
    dentro quella colonna entra nel controllo 1 come le cifre del dossier.
    Nessun file, o nessuna colonna con quel nome, e' un ritorno vuoto: il
    controllo 1 resta valido lo stesso, solo piu' piccolo.
    """
    if path is None or not Path(path).exists():
        return []
    rows = [line for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip().startswith("|")]
    if len(rows) < 2:
        return []
    header = [cell.strip().lower() for cell in rows[0].strip().strip("|").split("|")]
    try:
        column = next(i for i, name in enumerate(header) if "citazione letterale" in name)
    except StopIteration:
        return []
    found = []
    for row in rows[2:]:  # la riga 0 e' l'intestazione, la riga 1 il separatore `---`
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if column >= len(cells):
            continue
        for match in NUMBER_RE.finditer(cells[column]):
            found.append(_number_value(match.group("sign"), match.group("int"), match.group("dec")))
    return found


def check_figures(fields, internal_key, dossier, source_values):
    """Il controllo 1: ogni cifra scritta contro il dossier (e le fonti).

    Un numero senza segno esplicito passa se il dossier porta la stessa cifra
    con **qualunque** segno: la direzione detta a parole si confronta sul
    valore assoluto. Un numero con un `+` o un `-` scritto deve trovare quel
    segno nel dossier; se il dossier ha la cifra ma con il segno opposto, e'
    il difetto di `gate2_verify.py`, non una cifra assente.
    """
    pool = dossier_figures(dossier) + list(source_values)

    from app.indicator_view import build_indicator_view
    from app import sources
    from app.divari import _AREA_BY_KEY
    from app.profiles import region_key_for

    parsed = sources.split_internal_id(internal_key)
    if parsed:
        family, raw_id = parsed
        try:
            view = build_indicator_view(family, raw_id)
            if view:
                views = [view]
                for sibling in view.get("dimension_siblings", []):
                    sib_view = build_indicator_view(family, sibling["id"])
                    if sib_view:
                        views.append(sib_view)

                for v in views:
                    for level in v.get("levels", []):
                        matrix = level.get("matrix", {})
                        area_of = {}
                        for t in level.get("territories", []):
                            t_key = t.get("key")
                            if level["key"] == "regione":
                                area = _AREA_BY_KEY.get(t_key)
                            else:
                                region = t.get("region")
                                area = _AREA_BY_KEY.get(region_key_for(region or "")) if region else None
                            if area:
                                area_of[t_key] = area

                        for year_data in matrix.values():
                            area_sums = {}
                            area_counts = {}
                            for t_key, val in year_data.items():
                                num = None
                                if isinstance(val, (int, float)) and not isinstance(val, bool):
                                    num = float(val)
                                elif isinstance(val, dict) and "v" in val and isinstance(val.get("v"), (int, float)) and not isinstance(val["v"], bool):
                                    num = float(val["v"])

                                if num is not None:
                                    pool.append(num)
                                    area = area_of.get(t_key)
                                    if area:
                                        area_sums[area] = area_sums.get(area, 0.0) + num
                                        area_counts[area] = area_counts.get(area, 0) + 1

                            for area, total in area_sums.items():
                                if area_counts[area] > 0:
                                    pool.append(total / area_counts[area])
        except Exception:
            pass
    defects = []
    for field, text in fields:
        for match in NUMBER_RE.finditer(text):
            if not _is_checkable(match, text):
                continue
            signed = bool(match.group("sign"))
            decimals = len(match.group("dec")) if match.group("dec") else 0
            target = round(_number_value(match.group("sign"), match.group("int"), match.group("dec")), decimals)
            if any(abs(round(value, decimals) - target) < 1e-9 for value in pool):
                continue
            target_abs = abs(target)
            wrong_sign = any(abs(round(abs(value), decimals) - target_abs) < 1e-9 for value in pool)
            if wrong_sign and not signed:
                continue  # il valore assoluto corrisponde, e il testo non dichiarava un segno
            quote = _excerpt(text, match.start(), match.end())
            if wrong_sign:
                defects.append(Defect(
                    "cifre", field, quote,
                    f"{match.group(0)!r} ha il segno sbagliato: il dossier porta {target_abs:g} "
                    "con il segno opposto"
                ))
            else:
                nearby = sorted({numfmt.text(value, decimals) for value in pool
                                  if abs(abs(value) - target_abs) < target_abs * 0.2 + 5})[:5]
                note = f" (valori vicini nel dossier: {', '.join(nearby)})" if nearby else ""
                defects.append(Defect(
                    "cifre", field, quote,
                    f"{match.group(0)!r} non corrisponde a nessuna cifra del dossier o di --fonti{note}"
                ))
    return defects


# --- il controllo 2: i link -------------------------------------------------


def _indicator_code_in(url):
    """Il segmento codice di un link `/indicatore/...`, o None se non e' quella forma."""
    parts = [p for p in url.split("/") if p]
    if len(parts) < 2 or parts[0] != "indicatore":
        return None
    return parts[-2] if parts[-1] == "province" else parts[-1]


def check_links(fields):
    """Il controllo 2: ogni link interno a una scheda e' il suo percorso canonico."""
    defects = []
    for field, text in fields:
        for match in LINK.finditer(text):
            url = match.group(2)
            quote = _excerpt(text, match.start(), match.end())
            if "?indicator=" in url:
                defects.append(Defect("link", field, quote, f"{url!r} non e' un link canonico: usa /indicatore/<slug>/<codice>"))
                continue
            if not url.startswith("/indicatore/"):
                continue
            code = _indicator_code_in(url)
            parsed = sources.parse_indicator_code(code or "")
            if parsed is None:
                defects.append(Defect("link", field, quote, f"{url!r}: {code!r} non e' un codice riconoscibile"))
                continue
            family, raw_id = parsed
            try:
                view = build_indicator_view(family, raw_id)
            except Exception:  # noqa: BLE001 - un link rotto e' un difetto, qualunque sia la causa
                view = None
            if view is None:
                defects.append(Defect("link", field, quote, f"{url!r}: {code!r} non risolve a nessuna scheda"))
                continue
            canonical_paths = {level["canonical_path"] for level in view["levels"]}
            if url not in canonical_paths:
                defects.append(Defect(
                    "link", field, quote,
                    f"{url!r} non e' il percorso canonico ({', '.join(sorted(canonical_paths))})"
                ))
    return defects


# --- il controllo 3: i marcatori dei grafici --------------------------------


def check_markers(fields, internal_key, level_key):
    """Il controllo 3: ogni marcatore `<!-- grafico -->` produce davvero un SVG."""
    defects = []
    for field, text in fields:
        for match in charts.MARKER_RE.finditer(text):
            spec = charts.parse_args(match.group("args"))
            kind = match.group("tipo").lower()
            quote = _excerpt(text, match.start(), match.end())
            try:
                svg = charts.portrait(spec, level_key) if kind == "ritratto" \
                    else charts.figure(internal_key, spec, level_key)
            except Exception as error:  # noqa: BLE001 - un marcatore rotto e' un difetto
                defects.append(Defect("grafico", field, quote, f"il marcatore solleva {error!r}"))
                continue
            if not svg:
                defects.append(Defect("grafico", field, quote, "il marcatore non produce nessun SVG"))
    return defects


# --- il controllo 4: la forma libera senza titolo ---------------------------


def check_free_sections(entry):
    """Il controllo 4: una sezione `libera` con testo ma senza titolo e' bloccante."""
    defects = []
    for index, section in enumerate(entry.get("sections") or []):
        if not isinstance(section, dict) or section.get("role") != LIBERA:
            continue
        body = (section.get("body") or "").strip()
        if not body:
            continue
        if not (section.get("h") or "").strip():
            field = f"sections.{LIBERA}[{index}]"
            defects.append(Defect(
                "sezione", field, _excerpt(body, 0, min(60, len(body))),
                "sezione libera senza titolo: la pagina la scarta in silenzio"
            ))
    return defects


# --- il controllo 5: gli assoluti tipografici -------------------------------

TYPO_RE = re.compile(r"[—–;…]")


def check_typography(fields):
    """Il controllo 5: mai `—`, `–`, `;`, `…` nella prosa."""
    defects = []
    for field, text in fields:
        for match in TYPO_RE.finditer(text):
            defects.append(Defect(
                "tipografia", field, _excerpt(text, match.start(), match.end()),
                f"carattere vietato {match.group(0)!r}"
            ))
    return defects


# --- il risultato ------------------------------------------------------------


def check_article(internal_key, entry, dossier=None, source_values=None):
    """Ogni difetto di un articolo. `dossier` e `source_values` sono opzionali:
    senza dossier il controllo 1 non gira, come oggi su tutto il catalogo."""
    fields = prose_fields(entry)
    if not fields:
        return []
    level_key = entry.get("level") or DEFAULT_LEVEL
    defects = []
    defects += check_typography(fields)
    defects += check_free_sections(entry)
    defects += check_links(fields)
    defects += check_markers(fields, internal_key, level_key)
    if dossier is not None or source_values:
        defects += check_figures(fields, internal_key, dossier or {}, source_values or [])
    return defects


# --- la CLI -------------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("code", help="codice della scheda: ter-12, 12, bes-06POL012P o bes:06POL012P")
    parser.add_argument("--dossier", type=Path, help="il dossier di scripts.editoriale.brief, per il controllo 1")
    parser.add_argument("--fonti", type=Path, help="fonti.md, colonna 'citazione letterale', per il controllo 1")
    args = parser.parse_args(argv)

    try:
        family, raw_id = brief.resolve(args.code)
    except LookupError as error:
        print(f"guardia: {error}", file=sys.stderr)
        return 2
    internal_key = sources.internal_id(family, raw_id)
    entry = indicator_store.read(internal_key)
    if entry is None:
        print(f"guardia: nessun articolo scritto per {args.code}, niente da controllare")
        return 0

    dossier = None
    if args.dossier is not None:
        try:
            dossier = json.loads(args.dossier.read_text(encoding="utf-8"))
        except FileNotFoundError:
            parser.error(f"il dossier {args.dossier} non esiste")
    source_values = source_figures(args.fonti) if args.fonti is not None else []

    defects = check_article(internal_key, entry, dossier=dossier, source_values=source_values)
    if not defects:
        print(f"guardia: {args.code} pulito ({len(prose_fields(entry))} campi controllati)")
        return 0
    print(f"guardia: {len(defects)} difetti su {args.code}", file=sys.stderr)
    for defect in defects:
        print(f"  {defect.line()}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
