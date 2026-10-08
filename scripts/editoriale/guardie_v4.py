"""Controlli editoriali G2 e G4 condivisi da schede e articoli."""
from __future__ import annotations

import argparse
import re
import sys
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
