"""La guardia deterministica su un articolo del blog (`content/posts/*.md`).

    bin/py -m scripts.editoriale.guardia_articolo content/posts/2026-10-05-reddito-pro-capite-regioni-non-e-il-pil.md
    bin/py -m scripts.editoriale.guardia_articolo content/posts/*.md --json
    bin/py -m scripts.editoriale.guardia_articolo content/posts/<file>.md --tetto 800

`guardia.py` guarda le schede indicatore, `scripts/trend_articles/verify.py`
l'articolo nato dalla pipeline dei trend (dossier, scheda della foto, trend).
Questa guarda l'articolo scritto a mano, che non ha ne' dossier ne' scheda
della foto: ha il CSV che dichiara in `dataset.download`, e li' si ricalcolano
le cifre che un revisore ricontrollava a mano.

Cinque controlli, tutti meccanici:

1. **Cifre contro il CSV** dell'articolo e le sue `external_figures`. Una cifra
   che sta nel CSV, con l'arrotondamento con cui e' scritta e la virgola
   italiana, e' verificata. Una cifra che non ha corrispondenza e' **non
   verificabile** e non fa fallire: un rapporto, una differenza o il valore di
   un anno che il CSV non porta non sono un errore. E' un **errore** solo la
   cifra che il testo lega a una cella precisa e che non coincide: nella stessa
   frase c'e' un territorio del CSV e un anno che e' nell'intestazione di una
   colonna, e il numero cade nell'intervallo di quelle colonne. Senza questo
   doppio ancoraggio non si accusa nessuno. Un punto decimale all'inglese e un
   segno scritto sbagliato sono errori di forma.
2. **Link interni**: ogni link che porta a una pagina del sito risponde 200
   senza redirect, con `scripts/audit_link_interni.LinkChecker`, lo stesso
   controllo che fa la prova sulla sitemap.
3. **Frontmatter**: `title`, `description`, `date`, `indicator`; il blocco
   `dataset` con `name`, `creator`, `source_url` e un `download` che esiste; se
   c'e' una copertina, `cover_alt` e `cover_credit` con autore, licenza e
   fonte; ogni `external_figures` con fonte e URL. Le figure `<!-- figura: x -->`
   hanno il loro SVG, con `<title>` (l'alt) e `<desc>` (la didascalia) non vuoti.
   Non si chiede `trend:` ne' la scheda `.photo.json`: sono della pipeline dei
   trend, e un articolo scritto a mano non li ha.
4. **Forma di `content/STYLE.md`** che si controlla a macchina: mai `—`, `–`,
   `;`, `…`, e le parole di prosa (tabelle e fonti escluse, come in
   `verify.py`) entro il tetto, mille per `REVIEW.md`. Il tetto superato e' un
   avviso, come in `verify.py`: la lunghezza giusta la giudica il revisore.
5. **Esito**: rilievi numerati con `file:riga`, in tre gravita'. Gli **errori**
   danno esito 1, gli **avvisi** e i **non verificabili** si leggono e danno 0.
   `--json` stampa lo stesso referto per le macchine.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

import frontmatter

from app import blog
from app.design import numfmt
from scripts.audit_link_interni import _internal_path
from scripts.editoriale.guardia import NUMBER_RE, TYPO_RE, _excerpt, _is_checkable, _number_value
from scripts.trend_articles.verify import LINK, _clean_body

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
WORD_CAP = 1000

ERROR, WARNING, UNVERIFIABLE = "errore", "avviso", "non verificabile"
SEVERITY_ORDER = {ERROR: 0, WARNING: 1, UNVERIFIABLE: 2}

REQUIRED_FIELDS = ("title", "description", "date", "indicator")
DATASET_FIELDS = ("name", "creator", "source_url", "download")
CREDIT_FIELDS = ("author", "license", "source_url")
PROSE_FIELDS = ("title", "seo_title", "description", "cover_alt", "cover_caption")
TERRITORY_COLUMNS = ("regione", "provincia", "territorio", "chiave")

_COMMENT = re.compile(r"<!--.*?-->")
_ATTRS = re.compile(r"\{:[^}]*\}")
_FIGURE_MARKER = re.compile(r"<!--\s*figura:\s*([a-z0-9][a-z0-9-]*)\s*-->")
_LINK_TARGET = re.compile(r"(\]\()([^)\s]*)(\))")
_YEAR = re.compile(r"(?<!\d)(?:19|20)\d\d(?!\d)")
_SENTENCE_END = re.compile(r"[.!?]+[\"')»]*\s+(?=[A-ZÀ-Ý\"'«(])")


class Finding:
    """Un rilievo: la gravita', il controllo, la riga del file, il messaggio, la frase."""

    __slots__ = ("severity", "check", "line", "message", "quote")

    def __init__(self, severity, check, line, message, quote=""):
        self.severity = severity
        self.check = check
        self.line = line
        self.message = message
        self.quote = quote

    def __repr__(self):
        return f"Finding({self.severity!r}, {self.check!r}, {self.line!r}, {self.message!r})"

    def as_dict(self):
        return {"gravita": self.severity, "controllo": self.check, "riga": self.line,
                "messaggio": self.message, "citazione": self.quote}


# --- la lettura del file -------------------------------------------------------


class Article:
    """Il file letto una volta: frontmatter, corpo e il numero di riga di ogni cosa."""

    def __init__(self, path):
        self.path = Path(path)
        raw = self.path.read_text(encoding="utf-8")
        self.lines = raw.splitlines()
        post = frontmatter.loads(raw)
        self.meta = post.metadata
        self.body_start = 0  # indice (da 0) della prima riga del corpo
        if self.lines and self.lines[0].strip() == "---":
            end = next((i for i in range(1, len(self.lines)) if self.lines[i].strip() == "---"), None)
            if end is not None:
                self.body_start = end + 1
        self.body_lines = self.lines[self.body_start:]
        self.slug = str(self.meta.get("slug") or re.sub(r"^\d{4}-\d{2}-\d{2}-", "", self.path.stem))

    def field_line(self, key):
        """La riga (da 1) in cui il frontmatter apre `key`, o 1 se non c'e'."""
        pattern = re.compile(rf"^{re.escape(key)}\s*:")
        for index in range(self.body_start):
            if pattern.match(self.lines[index]):
                return index + 1
        return 1

    def body_line(self, index):
        return self.body_start + index + 1


def _blank(match):
    return " " * len(match.group(0))


def _prose_line(line):
    """Una riga del corpo senza cio' che non e' prosa, a pari lunghezza: gli
    indirizzi dei link, i commenti dei marcatori e gli attributi `{: ...}`."""
    line = _COMMENT.sub(_blank, line)
    line = _ATTRS.sub(_blank, line)
    return _LINK_TARGET.sub(lambda m: m.group(1) + " " * len(m.group(2)) + m.group(3), line)


# --- il CSV dell'articolo ------------------------------------------------------


def _normalize(text):
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def _to_float(cell):
    cell = (cell or "").strip()
    if not cell:
        return None
    try:
        return float(cell.replace(",", ".") if "," in cell and "." not in cell else cell)
    except ValueError:
        return None


class Table:
    """Il CSV: le colonne numeriche e i territori con le loro righe."""

    def __init__(self, path):
        with Path(path).open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        self.columns = {}
        names = list(rows[0].keys()) if rows else []
        for name in names:
            values = [_to_float(row.get(name)) for row in rows]
            if rows and all(v is not None for v in values):
                self.columns[name] = values
        self.territories = []  # (nome normalizzato, indice di riga, etichetta)
        for index, row in enumerate(rows):
            label = next((row[c] for c in names if c.lower() in TERRITORY_COLUMNS and row.get(c)), f"riga {index + 2}")
            seen = set()
            for column in names:
                if column.lower() in TERRITORY_COLUMNS and row.get(column):
                    term = _normalize(row[column])
                    if term and term not in seen:
                        seen.add(term)
                        self.territories.append((term, index, label))

    def all_values(self):
        return [v for values in self.columns.values() for v in values]


# --- il controllo 1: le cifre ----------------------------------------------------


def _written(match):
    """La cifra come e' scritta, senza segno: `28.154`, `2,3`."""
    return match.group("int") + (f",{match.group('dec')}" if match.group("dec") else "")


def _renders(value, written, decimals, scaled):
    candidates = [value / 1000 if scaled else value]
    return any(numfmt.text(abs(c), decimals) == written for c in candidates)


def _decimals(match):
    return len(match.group("dec")) if match.group("dec") else 0


def _sentences(text):
    start = 0
    for found in _SENTENCE_END.finditer(text):
        yield start, text[start:found.end()]
        start = found.end()
    if start < len(text):
        yield start, text[start:]


def _anchor(sentence, table):
    """Le celle che la frase nomina: i territori del CSV per gli anni nelle
    intestazioni. `None` se manca uno dei due ancoraggi."""
    normalized = f" {_normalize(sentence)} "
    rows = sorted({index for term, index, _ in table.territories if f" {term} " in normalized})
    years = set(_YEAR.findall(sentence))
    # Un anno che nessuna colonna porta (il 2002 di una serie che il CSV non ha)
    # rende ambigua la frase: la cifra potrebbe essere di quell'anno.
    if any(not any(re.search(rf"(?<!\d){y}(?!\d)", c) for c in table.columns) for y in years):
        return None
    columns = [c for c in table.columns if any(re.search(rf"(?<!\d){y}(?!\d)", c) for y in years)]
    if not rows or not columns:
        return None
    labels = {index: label for _, index, label in table.territories}
    cells = [(labels[r], c, table.columns[c][r]) for r in rows for c in columns]
    magnitudes = [abs(v) for c in columns for v in table.columns[c]]
    return cells, (min(magnitudes), max(magnitudes))


def check_figures(article, table, external):
    """Il controllo 1. Restituisce i rilievi: errori di forma e di cella, non verificabili."""
    findings = []
    external_values = {re.sub(r"^[+-]", "", str(e.get("value")).strip()) for e in external if isinstance(e, dict)}
    pool = table.all_values() if table else []
    for index, raw in enumerate(article.body_lines):
        line = _prose_line(raw).replace("*", " ")
        line_no = article.body_line(index)
        for _, sentence in _sentences(line):
            for match in NUMBER_RE.finditer(sentence):
                if not _is_checkable(match, sentence):
                    continue
                quote = _excerpt(sentence, match.start(), match.end()).strip()
                shown = match.group(0)
                if match.group("sep") == ".":
                    findings.append(Finding(ERROR, "cifre", line_no, f"{shown!r} usa il punto decimale all'inglese: la forma italiana vuole la virgola", quote))
                    continue
                written, decimals = _written(match), _decimals(match)
                scaled = sentence[match.end():].lower().startswith(" mila")
                if written in external_values:
                    continue
                matching = [v for v in pool if _renders(v, written, decimals, scaled)]
                if matching:
                    if match.group("sign") and not any(numfmt.text(v / 1000 if scaled else v, decimals) == match.group(0) for v in matching):
                        findings.append(Finding(ERROR, "cifre", line_no, f"{shown!r} ha il segno sbagliato: nel CSV la cifra ha il segno opposto", quote))
                    continue
                anchored = _anchor(sentence, table) if table else None
                value = abs(_number_value(None, match.group("int"), match.group("dec")))
                if scaled:
                    value *= 1000
                if anchored and anchored[1][0] * 0.9 <= value <= anchored[1][1] * 1.1:
                    cells = sorted(anchored[0], key=lambda cell: abs(abs(cell[2]) - value))[:3]
                    expected = ", ".join(f"{label} {column} = {numfmt.text(cell, max(decimals, 0))}" for label, column, cell in cells)
                    findings.append(Finding(ERROR, "cifre", line_no, f"{shown!r} non coincide con il CSV ({expected})", quote))
                else:
                    findings.append(Finding(UNVERIFIABLE, "cifre", line_no, f"{shown!r} non e' nel CSV ne' fra le external_figures", quote))
    return findings


# --- il controllo 2: i link interni --------------------------------------------


def default_link_status():
    """Il controllo vero: l'app di Flask e `LinkChecker`. Si carica solo qui."""
    from app import app
    from scripts.audit_link_interni import LinkChecker

    checker = LinkChecker(app.test_client())

    def status(path):
        code, _, location, _ = checker.response(path)
        return code, location

    return status


def check_links(article, link_status):
    findings = []
    seen = {}
    for index, raw in enumerate(article.body_lines):
        for match in LINK.finditer(_COMMENT.sub(_blank, raw)):
            path = _internal_path(match.group(2))
            if not path:
                continue
            path = path.split("#")[0]
            if not path:
                continue
            if path not in seen:
                seen[path] = link_status(path)
            code, location = seen[path]
            if code != 200:
                where = f" verso {location}" if location else ""
                findings.append(Finding(ERROR, "link", article.body_line(index),
                                        f"il link interno {path} risponde {code}{where}, deve rispondere 200 senza redirect",
                                        _excerpt(raw, match.start(), match.end())))
    return findings


# --- il controllo 3: frontmatter e figure --------------------------------------


def check_frontmatter(article, static_dir=STATIC):
    findings = []
    meta = article.meta

    def missing(key, where=None):
        findings.append(Finding(ERROR, "frontmatter", article.field_line(where or key), f"manca `{key}`"))

    for field in REQUIRED_FIELDS:
        if not meta.get(field):
            missing(field)
    if meta.get("date") and blog._coerce_date(meta["date"]) is None:
        findings.append(Finding(ERROR, "frontmatter", article.field_line("date"), f"`date` {meta['date']!r} non e' una data AAAA-MM-GG"))

    dataset = meta.get("dataset")
    if not isinstance(dataset, dict) or not dataset:
        missing("dataset")
    else:
        for field in DATASET_FIELDS:
            if not dataset.get(field):
                missing(f"dataset.{field}", "dataset")
        download = str(dataset.get("download") or "")
        if download and not (static_dir / download.removeprefix("/static/").lstrip("/")).is_file():
            findings.append(Finding(ERROR, "frontmatter", article.field_line("download"), f"dataset.download {download} non esiste"))

    if meta.get("cover"):
        if not meta.get("cover_alt"):
            missing("cover_alt")
        credit = meta.get("cover_credit")
        if not isinstance(credit, dict):
            missing("cover_credit")
        else:
            for field in CREDIT_FIELDS:
                if not credit.get(field):
                    missing(f"cover_credit.{field}", "cover_credit")

    for i, entry in enumerate(meta.get("external_figures") or []):
        for field in ("source", "url"):
            if not isinstance(entry, dict) or not entry.get(field):
                missing(f"external_figures[{i}].{field}", "external_figures")
    return findings


def check_figure_files(article, figures_dir=None):
    figures_dir = Path(figures_dir) if figures_dir else blog.FIGURES_DIR
    findings = []
    for index, raw in enumerate(article.body_lines):
        for match in _FIGURE_MARKER.finditer(raw):
            name, line_no = match.group(1), article.body_line(index)
            path = figures_dir / article.slug / f"{name}.svg"
            if not path.is_file():
                findings.append(Finding(ERROR, "figure", line_no, f"la figura {name} non ha il suo SVG ({article.slug}/{name}.svg)", match.group(0)))
                continue
            svg = path.read_text(encoding="utf-8")
            for tag, role in (("title", "alt"), ("desc", "didascalia")):
                found = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", svg, re.DOTALL)
                if not found or not found.group(1).strip():
                    findings.append(Finding(ERROR, "figure", line_no, f"la figura {name} non ha `<{tag}>` ({role})", match.group(0)))
    return findings


# --- il controllo 4: la forma ----------------------------------------------------


def check_typography(article):
    findings = []
    for key in PROSE_FIELDS:
        value = article.meta.get(key)
        for match in TYPO_RE.finditer(str(value or "")):
            findings.append(Finding(ERROR, "tipografia", article.field_line(key), f"carattere vietato {match.group(0)!r} in `{key}`", _excerpt(str(value), match.start(), match.end())))
    for index, raw in enumerate(article.body_lines):
        line = _prose_line(raw)
        for match in TYPO_RE.finditer(line):
            findings.append(Finding(ERROR, "tipografia", article.body_line(index), f"carattere vietato {match.group(0)!r}", _excerpt(line, match.start(), match.end())))
    return findings


def count_words(article):
    """Le parole di prosa: prima di `## Fonti`, senza tabelle, come `verify.py`."""
    prose = "\n".join(article.body_lines).split("## Fonti", 1)[0]
    prose = re.sub(r"^\|.*\|$", "", prose, flags=re.MULTILINE)
    return len(re.findall(r"\w+", _clean_body(prose)))


def check_length(article, cap):
    words = count_words(article)
    if words > cap:
        return words, [Finding(WARNING, "lunghezza", article.body_start + 1, f"{words} parole di prosa, tabelle e fonti escluse: il tetto e' {cap}")]
    return words, []


# --- il risultato ---------------------------------------------------------------


def check_article(path, link_status=None, cap=WORD_CAP, static_dir=STATIC, figures_dir=None):
    """Il referto di un articolo: `{"file", "parole", "tetto", "rilievi"}`.

    `link_status(path) -> (codice, location)` e' iniettabile: senza, si apre
    l'app di Flask. I rilievi sono ordinati per gravita' e per riga."""
    article = Article(path)
    findings = check_frontmatter(article, static_dir)
    table = None
    download = (article.meta.get("dataset") or {}).get("download") if isinstance(article.meta.get("dataset"), dict) else None
    if download:
        csv_path = Path(static_dir) / str(download).removeprefix("/static/").lstrip("/")
        if csv_path.is_file():
            table = Table(csv_path)
    findings += check_figures(article, table, article.meta.get("external_figures") or [])
    findings += check_links(article, link_status or default_link_status())
    findings += check_figure_files(article, figures_dir)
    findings += check_typography(article)
    words, length = check_length(article, cap)
    findings += length
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.line))
    return {"file": str(path), "parole": words, "tetto": cap, "rilievi": findings}


def _counts(report):
    counts = {ERROR: 0, WARNING: 0, UNVERIFIABLE: 0}
    for finding in report["rilievi"]:
        counts[finding.severity] += 1
    return counts


def format_report(report):
    counts = _counts(report)
    lines = [f"{report['file']}: {counts[ERROR]} errori, {counts[WARNING]} avvisi, "
             f"{counts[UNVERIFIABLE]} non verificabili ({report['parole']} parole, tetto {report['tetto']})"]
    for number, finding in enumerate(report["rilievi"], 1):
        quote = f" -- {finding.quote!r}" if finding.quote else ""
        lines.append(f"  {number}. {report['file']}:{finding.line} [{finding.severity}/{finding.check}] {finding.message}{quote}")
    return "\n".join(lines)


def report_dict(report):
    counts = _counts(report)
    return {"file": report["file"], "esito": 1 if counts[ERROR] else 0, "parole": report["parole"], "tetto": report["tetto"],
            "errori": counts[ERROR], "avvisi": counts[WARNING], "non_verificabili": counts[UNVERIFIABLE],
            "rilievi": [dict(numero=i, **f.as_dict()) for i, f in enumerate(report["rilievi"], 1)]}


def main(argv=None, link_status=None, **where):
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("articoli", nargs="+", type=Path, help="uno o piu' file di content/posts/")
    parser.add_argument("--json", action="store_true", help="il referto per le macchine")
    parser.add_argument("--tetto", type=int, default=WORD_CAP, help=f"tetto di parole di prosa (default {WORD_CAP})")
    args = parser.parse_args(argv)

    for path in args.articoli:
        if not path.is_file():
            parser.error(f"il file {path} non esiste")
    status = link_status or default_link_status()
    reports = [check_article(path, link_status=status, cap=args.tetto, **where) for path in args.articoli]
    failed = any(_counts(r)[ERROR] for r in reports)
    if args.json:
        print(json.dumps([report_dict(r) for r in reports], ensure_ascii=False, indent=2))
    else:
        print("\n".join(format_report(r) for r in reports))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
