"""Controlli statici sui prototipi resi in dist/pagine.

    bin/py design/v1/tools/check_pages.py              tutte le pagine
    bin/py design/v1/tools/check_pages.py home regione solo alcune

Per ogni pagina: nessun trattino lungo o medio, punto e virgola o puntini nel
testo visibile e negli attributi letti ad alta voce (le stesse regole e la
stessa funzione dei test del sito); nessun numero in formato inglese; nessun
colore scritto fuori da tokens.css; un solo H1; il bersaglio del salto al
contenuto; id unici; nessun tracciamento; nessun segnaposto di cifra rimasto.
Esce non zero se qualcosa non va.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from html import unescape
from pathlib import Path

V1 = Path(__file__).resolve().parents[1]
DIST = V1 / "dist" / "pagine"
SRC = V1 / "src"

# Le stesse di tests/integration/test_hub_pages.py: FORBIDDEN_CHARS e visible_text.
FORBIDDEN_CHARS = ("—", "–", "…", ";")
PLACEHOLDER = "[dato da calcolare]"
COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(")


def visible_text(html: str) -> str:
    stripped = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.DOTALL)
    return unescape(re.sub(r"<[^>]+>", " ", stripped))


def spoken_attributes(html: str) -> str:
    return " ".join(unescape(v) for v in re.findall(r'\b(?:alt|aria-label|title|placeholder)="([^"]*)"', html))


def check(path: Path) -> list[str]:
    html = path.read_text(encoding="utf-8")
    body = html.split("<body", 1)[-1]
    problems = []
    text = visible_text(body) + " " + spoken_attributes(body)
    # Le versioni non sono cifre: "Creative Commons BY 4.0", "Divario Italia 1.0".
    text_numbers = re.sub(r"\b(BY|Italia) \d+\.\d+\b", " ", text)
    for ch in FORBIDDEN_CHARS:
        for m in re.finditer(re.escape(ch), text):
            problems.append(f"carattere vietato {ch!r}: ...{text[max(0, m.start() - 50):m.start() + 20].strip()}...")
    # 1,234.5 oppure 12.5 (non una data, non un anno, non una versione)
    for m in re.finditer(r"(?<![\d.,])\d{1,3}(?:,\d{3})+(?:\.\d+)?(?![\d])|(?<![\d.,/:-])\d+\.\d{1,2}(?![\d.])", text_numbers):
        problems.append(f"numero in formato inglese: {m.group(0)!r} in ...{text[max(0, m.start() - 40):m.end() + 20].strip()}...")
    if PLACEHOLDER in text:
        problems.append(f"{text.count(PLACEHOLDER)} cifre da calcolare ({PLACEHOLDER})")
    # Colori fuori dai token: negli attributi style e nei tag <style> che non sono tokens.css.
    for m in re.finditer(r'style="([^"]*)"', body):
        if COLOR.search(m.group(1)):
            problems.append(f"colore cotto in un attributo style: {m.group(1)[:80]}")
    h1 = re.findall(r"<h1\b", body)
    if len(h1) != 1:
        problems.append(f"{len(h1)} H1 invece di uno")
    if 'id="contenuto"' not in body:
        problems.append('manca id="contenuto"')
    ids = Counter(re.findall(r'\bid="([^"]+)"', body))
    dup = [k for k, n in ids.items() if n > 1]
    if dup:
        problems.append(f"id ripetuti: {dup[:8]}")
    markup = re.sub(r"<script.*?</script>", " ", body, flags=re.DOTALL)
    for anchor in set(re.findall(r'href="#([^"]+)"', markup)):
        if anchor not in ids:
            problems.append(f"ancora senza bersaglio: #{anchor}")
    if re.search(r"googletagmanager|adsbygoogle|supabase|iubenda|gtag\(", body):
        problems.append("tracciamento nella pagina")
    for img in re.findall(r"<img\b[^>]*>", body):
        if " alt=" not in img:
            problems.append(f"immagine senza alt: {img[:80]}")
    return problems


def check_sources() -> list[str]:
    """Il CSS dei componenti e delle pagine legge solo token."""
    problems = []
    for css in [SRC / "css" / "components.css", *sorted((SRC / "css" / "pages").glob("*.css"))]:
        source = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), css.read_text(encoding="utf-8"), flags=re.DOTALL)
        for n, line in enumerate(source.splitlines(), 1):
            if COLOR.search(line):
                problems.append(f"{css.relative_to(V1)}:{n}: colore fuori dai token: {line.strip()[:80]}")
    for tpl in sorted((SRC).rglob("*.j2")):
        for n, line in enumerate(tpl.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r'style="[^"]*(#[0-9a-fA-F]{3,8}\b|rgba?\()', line):
                problems.append(f"{tpl.relative_to(V1)}:{n}: colore cotto nel template")
    return problems


def main() -> None:
    names = sys.argv[1:]
    pages = [DIST / f"{n}.html" for n in names] if names else sorted(DIST.glob("*.html"))
    total = 0
    for path in pages:
        problems = check(path)
        total += len(problems)
        print(f"{path.name}: {'ok' if not problems else str(len(problems)) + ' problemi'}")
        for p in problems[:30]:
            print(f"  - {p}")
    source_problems = check_sources()
    total += len(source_problems)
    for p in source_problems:
        print(f"  - {p}")
    print("nessun problema" if not total else f"{total} problemi")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
