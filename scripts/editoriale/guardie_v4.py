"""Controlli editoriali G2 e G4 condivisi da schede e articoli."""
from __future__ import annotations

import argparse
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path


_INTERNAL = re.compile(
    r"\bindicizz\w*|\bseo\b|\bsitemap\b|\bnoindex\b|\bparola\s+chiave\b|"
    r"\bgoogle\b.{0,100}\b(?:indicizz\w*|seo|sitemap|noindex|parola\s+chiave|priorit\w*)\b|"
    r"\bpriorit\w*.{0,60}\bindicizz\w*\b",
    re.I,
)
_NUMBER = re.compile(r"(?<![\w/-])(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?(?:%|ª|°)?(?![\w/-])")
_YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_UNIT = re.compile(
    r"%|€|\beuro\b|\bpunti?\b|\banni?\b|\bper\s+1[.]?000\b|"
    r"\bper\s+10[.]?000\b|\b(?:abitanti|nascite|decessi|addetti|imprese|euro|"
    r"giorni|giornate|ore|km|chilometri|presenze|pernottamenti|posti|volte)\b",
    re.I,
)
_SENTENCE = re.compile(r".+?(?:[!?]+|\.(?!\d)|$)", re.S)
_SKIP = re.compile(r"^\s*(?:>\s*)?(?:note|fonti|riferimenti|bibliografia)\b|^\s*\d+[.)]\s")
_LINK_URL = re.compile(r"https?://\S+|(?:\]\()([^)]*)\)")
_NATIONAL = re.compile(r"(?<!d')\b(?:italia|nazional\w*|media italiana)\b", re.I)
_SIMPLE = re.compile(r"\bmedia\s+(?:aritmetica\s+)?semplice\b", re.I)
_OFFICIAL = re.compile(r"\b(?:dato|valore|media)\s+(?:nazionale\s+)?ufficiale\b|\b(?:istat|eurostat)\b.{0,35}\b(?:dato|valore|media)\s+nazionale\b|\b(?:dato|valore|media)\s+(?:nazionale\s+)?(?:istat|eurostat)\b", re.I)
_MEASURE = re.compile(r"(?<![\w])(?P<number>\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?)(?:\s*%|\b)")
_COUNT = re.compile(r"\b(?P<count>\d{1,3})\s+(?P<geo>province|regioni)\b|\btutte\s+le\s+(?P<all>province|regioni)\b", re.I)
_RATIO = re.compile(r"\b(?:\d+(?:,\d+)?|due|tre|quattro|cinque|sei|sette|otto|nove|dieci)\s+volte\b", re.I)
_COMPARISON = re.compile(r"\b(?:estremi|divario|rapporto|rispetto|confronto|quello|quella|tra|fra)\b", re.I)


def decimal_value(value):
    """Read published decimal text without binary float subtraction."""
    try:
        return Decimal(str(value).strip().replace(".", "").replace(",", ".") if isinstance(value, str) and "," in value else str(value).strip())
    except (InvalidOperation, ValueError):
        return None


def editorial_checks(sentence, observations, geography, year=None, unit="", name="", official=False):
    """Return (severity, rule, reason) for one sentence and one source selection.

    observations maps year to distinct territory keys and Decimal values. Missing
    selection stays unverifiable; no national value is synthesized.
    """
    sentence = str(sentence)
    years = set(re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", sentence))
    selected = next(iter(years)) if len(years) == 1 else str(year) if not years and year is not None else None
    if selected is None and len(observations) == 1:
        selected = next(iter(observations))
    values = observations.get(str(selected)) if selected is not None else None
    result = []
    if _NATIONAL.search(sentence) and not _SIMPLE.search(sentence):
        national = _NATIONAL.search(sentence)
        near = sentence[max(0, national.start() - 25):national.end() + 70]
        numbers = [decimal_value(m.group("number")) for m in _MEASURE.finditer(near)]
        numbers = [n for n in numbers if n is not None and not (1900 <= n <= 2100 and n == n.to_integral_value())]
        if numbers:
            if not values or len(years) > 1:
                result.append(("non verificabile", "G1", "CSV o anno della media territoriale non determinabile"))
            elif not (_OFFICIAL.search(sentence) and
                      (official or re.search(r"\b(?:dato|valore|media)\s+(?:nazionale\s+)?(?:istat|eurostat)\b", sentence, re.I))):
                mean = sum(values.values()) / len(values)
                if any(abs(number - mean) <= Decimal("0.05") for number in numbers):
                    result.append(("errore", "G1", f"media semplice di {len(values)} {geography} nel {selected} chiamata nazionale"))
    count_matches = list(_COUNT.finditer(sentence))
    for match in count_matches:
        geo = match.group("geo") or match.group("all")
        before = sentence[max(0, match.start() - 12):match.start()]
        if geo.lower() != geography or re.search(r"\b(?:su|non)\s*$", before, re.I):
            continue
        after = sentence[match.end():match.end() + 20]
        if re.match(r"\s+su\s+\d+", after, re.I):
            continue
        count_values = values
        count_period = selected
        if not count_values and not years and observations and len({len(cells) for cells in observations.values()}) == 1:
            count_values = next(iter(observations.values()))
            count_period = "ogni anno disponibile"
        if not count_values or len(years) > 1:
            result.append(("non verificabile", "G7", f"anno o CSV delle {geo} non determinabile"))
            continue
        claimed = int(match.group("count")) if match.group("count") else {"province": 107, "regioni": 20}[geo.lower()]
        if claimed != len(count_values):
            result.append(("errore", "G7", f"{claimed} {geo} dichiarate, {len(count_values)} osservate nel {count_period}"))
    if _RATIO.search(sentence) and _COMPARISON.search(sentence):
        duration = bool(re.search(r"\b(?:speranza di vita|durata|anni di vita|anni vissuti)\b", name, re.I)) or unit.lower().strip() in {"anni", "anno", "years"}
        if re.search(r"\bvolte\s+(?:il|lo|la)\s+(?:divario|differenza|distanza)\b", sentence, re.I):
            duration = False
        nonpositive = bool(values and min(values.values()) <= 0)
        if duration or nonpositive:
            reason = "durata in anni" if duration else "valori non positivi"
            result.append(("errore", "G6", f"rapporto fra estremi non giustificato: {reason}"))
        else:
            result.append(("avviso", "G6", "verificare significato del rapporto fra estremi"))
    return result


def g2(text):
    """True per messaggi interni; Google come fonte/servizio resta legittimo."""
    return bool(_INTERNAL.search(str(text or "")))


def g4_text(text, previous_has_year=False):
    """Numeri senza unità o anno nella frase corrente o nella precedente."""
    text = _LINK_URL.sub(" ", str(text or ""))
    sentences = list(_SENTENCE.finditer(text))
    findings = []
    for sentence in sentences:
        phrase = sentence.group(0)
        has_year = bool(_YEAR.search(phrase))
        if _SKIP.match(phrase.strip()):
            previous_has_year = has_year
            continue
        for match in _NUMBER.finditer(phrase):
            value = match.group(0)
            if value.endswith(("%", "ª", "°")) or _YEAR.fullmatch(value):
                continue
            left, right = phrase[max(0, match.start() - 24):match.start()], phrase[match.end():match.end() + 36]
            if _UNIT.search(left + " " + right) or has_year or previous_has_year:
                continue
            findings.append((value, sentence.start() + match.start()))
        previous_has_year = has_year
    return findings


def g4_title(text):
    """Titoli di figura/tabella: ogni numero nudo costituisce blocco."""
    text = _LINK_URL.sub(" ", str(text or ""))
    return [m.group(0) for m in _NUMBER.finditer(text)
            if not m.group(0).endswith(("%", "ª", "°")) and not _YEAR.fullmatch(m.group(0))]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args(argv)
    blocked = False
    for path in args.paths:
        files = sorted(path.rglob("*.md")) if path.is_dir() else [path]
        for file in files:
            if not file.is_file():
                continue
            lines = file.read_text(encoding="utf-8").splitlines()
            frontmatter = bool(lines and lines[0].strip() == "---")
            in_public_metadata = False
            in_sources = False
            previous_line_has_year = False
            for line_no, line in enumerate(lines, 1):
                if frontmatter:
                    if line.strip() == "---" and line_no > 1:
                        frontmatter = False
                        in_public_metadata = False
                        continue
                    if re.match(r"^(?:title|seo_title|description|cover_alt|cover_caption)\s*:", line):
                        in_public_metadata = True
                    elif re.match(r"^[\w-]+\s*:", line):
                        in_public_metadata = False
                    if in_public_metadata and g2(line):
                        print(f"BLOCCO {file}:{line_no}: G2 messaggio interno")
                        blocked = True
                    continue
                if g2(line):
                    print(f"BLOCCO {file}:{line_no}: G2 messaggio interno")
                    blocked = True
                if re.match(r"^\s*#{1,3}\s*(?:note|fonti|riferimenti|bibliografia)\b", line, re.I):
                    in_sources = True
                elif re.match(r"^\s*#{1,3}\s+", line):
                    in_sources = False
                if in_sources or line.lstrip().startswith(("|", "```")) or line.lstrip().startswith(">"):
                    previous_line_has_year = False
                    continue
                for number, _ in g4_text(line, previous_line_has_year):
                    print(f"AVVISO {file}:{line_no}: G4 numero senza unità/anno: {number}")
                stripped = line.strip()
                if re.match(r"^#{1,6}\s*(?:figura|tabella)\b", stripped, re.I) or re.match(r"^\s*\*\*(?:figura|tabella)\b", stripped, re.I):
                    for number in g4_title(stripped):
                        print(f"BLOCCO {file}:{line_no}: G4 titolo figura/tabella senza unità/anno: {number}")
                        blocked = True
                previous_line_has_year = bool(_YEAR.search(line))
    return int(blocked)


if __name__ == "__main__":
    sys.exit(main())
