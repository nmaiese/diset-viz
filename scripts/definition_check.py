"""What an article says the indicator counts, against what the source says it counts.

Every other guard in this repository compares the article to the **series**.
`tests/integration/test_indicator_texts.py` checks each decimal attributed to a region and
each threshold asserted over a list of them, `scripts/indicator_brief.py` hands
the writer the real values, `scripts/prose_lint.py` counts the bot tells. All of
them read the numbers.

The second batch of rewrites showed that the numbers are not where the errors
are. Of the false claims found by reading, none was an arithmetic mistake and
most were descriptions of the wrong quantity: `ter-402` called "imprese a guida
femminile" what Istat defines as women holding sole proprietorships, and said it
again in `limiti`, the section whose whole job is to state what the indicator
does not measure. `bes-11RIC023` declared a limit the definition contradicts
word for word. A wrong figure dies at the first reader who opens the brief. A
wrong definition survives every reading that checks arithmetic, because the
arithmetic is right.

So this compares prose to the committed source archive in `data/definitions/`:
the territorial `Metadati` sheet plus the federated BES, Multiscopo,
demographic and Eurostat definitions produced by the two fetchers there.

    python3 scripts/definition_check.py                 # i peggiori, in ordine
    python3 scripts/definition_check.py --summary       # il totale del catalogo
    python3 scripts/definition_check.py --show ter-402  # un articolo solo, per esteso
    python3 scripts/definition_check.py --json

**It is lexical, and it says so.** It cannot read Italian: what it does is find
the words the official definition leans on and ask whether the article ever uses
them. That makes it a place to look, like every other flag in this chain, and
never a verdict. Two consequences worth stating rather than discovering:

- a synonym reads as a miss. An article that writes "chi lavora in azienda" for
  "addetti" trips `termini` while being perfectly correct;
- an article can name every word and still describe the wrong thing.

What it is genuinely good at is the case that bit us: the definition carries a
denominator or a threshold ("sul totale delle imprese con R&S intra-muros",
"con più di dieci addetti", "per 100 abitanti") and the prose never mentions it.
That is not a synonym problem, it is a missing perimeter, and it is exactly the
shape of the errors the readers found.

Pure stdlib, like every script in the chain.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import prose_lint  # noqa: E402
from app import sources  # noqa: E402
from scripts.fetch_definitions import load_definitions  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Words that carry no information about what an indicator counts. Kept short on
# purpose: a long list starts hiding real misses, and the point of the check is
# the word the article never says.
STOPWORDS = {
    "a", "ad", "ai", "al", "all", "alla", "alle", "allo", "altre", "altri", "altro",
    "anche", "anni", "anno", "che", "chi", "ci", "col", "come", "con", "cui",
    "da", "dai", "dal", "dall", "dalla", "dalle", "dallo", "degli", "dei", "del",
    "dell", "della", "delle", "dello", "di", "e", "ed", "gli", "i", "il", "in",
    "l", "la", "le", "lo", "loro", "ma", "nei", "nel", "nell", "nella", "nelle",
    "nello", "non", "o", "od", "ogni", "oppure", "per", "piu", "poi", "quale",
    "quali", "quanto", "quello", "questa", "queste", "questi", "questo", "se",
    "sia", "sono", "su", "sui", "sul", "sull", "sulla", "sulle", "sullo", "tra",
    "un", "una", "uno", "è", "ché", "fra", "presso", "circa", "oltre",
    # Statistical scaffolding: true of half the catalogue, so it distinguishes
    # nothing and would drown the signal.
    "percentuale", "percentuali", "quota", "quote", "indice", "indicatore",
    "numero", "media", "medio", "medie", "totale", "totali", "valore", "valori",
    "rapporto", "incidenza", "tasso", "peso", "livello", "grado", "misura",
    "dato", "dati", "punti", "punto", "cento", "mille", "abitante", "abitanti",
    "regione", "regioni", "regionale", "regionali", "italia", "italiane",
    "italiano", "italiani", "residente", "residenti", "popolazione",
}

# The tail of the definition that names the base the numerator is divided by.
# Istat writes it half a dozen ways and the head noun is what matters, so each
# pattern captures the phrase and the stemming does the rest.
BASE_PATTERNS = (
    re.compile(r"\bsul\s+totale\s+(?:complessivo\s+)?(?:di|dei|degli|delle|della|del|dell')\s*([^.,;()]{3,90})", re.I),
    re.compile(r"\bsul\s+totale\s+([^.,;()]{3,90})", re.I),
    re.compile(r"\bin\s+(?:percentuale|rapporto)\s+(?:su|sul|sulla|sulle|sui|sugli)\s+([^.,;()]{3,90})", re.I),
    re.compile(r"\brispetto\s+al\s+totale\s+(?:di|dei|degli|delle|della|del|dell')\s*([^.,;()]{3,90})", re.I),
    re.compile(r"\bper\s+(?:unita|unità)\s+di\s+lavoro\b", re.I),
    re.compile(r"\bogni\s+\d[\d.]*\s+([^.,;()]{3,60})", re.I),
    re.compile(r"\bper\s+\d[\d.]*\s+([^.,;()]{3,60})", re.I),
)

# A restriction that changes who is counted. Missing one of these is how an
# article about employees becomes an article about firms.
QUALIFIER_PATTERNS = (
    # age bands and single ages: "25-34 anni", "di 15 anni e più"
    re.compile(r"\b\d{1,3}\s*[-–]\s*\d{1,3}\s+anni\b", re.I),
    re.compile(r"\b(?:di|da|con)\s+\d{1,3}\s+anni\s+(?:e\s+(?:piu|più|oltre)|o\s+(?:piu|più))\b", re.I),
    # size thresholds: "con più di dieci addetti", "con almeno 10 addetti"
    re.compile(r"\bcon\s+(?:piu|più)\s+di\s+[\w]+\s+addetti\b", re.I),
    re.compile(r"\bcon\s+almeno\s+[\w]+\s+addetti\b", re.I),
    re.compile(r"\b(?:almeno|oltre)\s+\d[\d.]*\s+[a-zà-ù]+\b", re.I),
    # rates per base: "per 100 abitanti", "per 1.000 residenti"
    re.compile(r"\bper\s+\d[\d.]*\s+[a-zà-ù]+\b", re.I),
)

WORD = re.compile(r"[A-Za-zÀ-ÿ']{2,}")

# An age band, the one restriction Istat states in a form precise enough that a
# mismatch is a contradiction rather than a synonym.
AGE_BAND = re.compile(r"\b(\d{1,3})\s*[-–]\s*(\d{1,3})\s+anni\b", re.I)
# "con più di dieci addetti" and "con almeno dieci addetti" are different
# perimeters over the same number, and the article that swaps them is wrong
# while using every word of the definition. It is the narrowest check here and
# the only one that asserts rather than suggests.
INCLUSIVE = re.compile(
    r"\b(?:almeno|non meno di)\s+(?P<n>[\w.]+)\s+(?P<noun>addetti|dipendenti|anni)\b", re.I
)
EXCLUSIVE = re.compile(
    r"\b(?:piu|più)\s+di\s+(?P<n>[\w.]+)\s+(?P<noun>addetti|dipendenti|anni)\b", re.I
)

NUMBER_WORDS = {
    "zero": "0", "uno": "1", "due": "2", "tre": "3", "quattro": "4",
    "cinque": "5", "sei": "6", "sette": "7", "otto": "8", "nove": "9",
    "dieci": "10", "undici": "11", "dodici": "12", "venti": "20",
    "cinquanta": "50", "cento": "100", "mille": "1000",
}


def _number(token: str) -> str:
    plain = _fold(token).replace(".", "")
    return NUMBER_WORDS.get(plain, plain)


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def stem(word: str) -> str:
    """A crude Italian stem, enough to make singular and plural the same token.

    Not a linguistics exercise. It exists so "impresa" and "imprese", "addetto"
    and "addetti", "titolare" and "titolari", "occupate" and "occupazione" stop
    counting as different words: drop the inflectional vowel, then keep the
    first five characters.

    It over-merges, and that is the direction chosen on purpose: "impresa" and
    "imprenditoriale" land together, so the check occasionally believes a word
    is present when a cousin of it is. A false match costs one missed flag on an
    article a reviewer reads anyway. A false miss costs an entry in a list of
    148 that nobody then reads at all, which is how a guard stops guarding.
    """
    token = _fold(word).strip("'")
    if len(token) > 4 and token[-1] in "aeio":
        token = token[:-1]
    return token[:5]


def tokens(text: str) -> set[str]:
    return {stem(word) for word in WORD.findall(text or "")}


def content_terms(text: str) -> list[str]:
    """The words of a definition that say what it counts, in order, deduplicated."""
    out: list[str] = []
    seen: set[str] = set()
    for word in WORD.findall(text or ""):
        folded = _fold(word).strip("'")
        if len(folded) < 4 or folded in STOPWORDS:
            continue
        key = stem(word)
        if key in seen:
            continue
        seen.add(key)
        out.append(word)
    return out


def base_phrases(definition: str) -> list[str]:
    """The denominator, as the source words it. Empty when it names none."""
    found: list[str] = []
    for pattern in BASE_PATTERNS:
        match = pattern.search(definition or "")
        if not match:
            continue
        phrase = (match.group(1) if match.groups() else match.group(0)).strip()
        phrase = re.sub(r"\s*\(.*$", "", phrase).strip(" .,;")
        if phrase and phrase not in found:
            found.append(phrase)
        if found:
            break
    return found


def qualifiers(definition: str) -> list[str]:
    found: list[str] = []
    for pattern in QUALIFIER_PATTERNS:
        for match in pattern.finditer(definition or ""):
            phrase = match.group(0).strip()
            if phrase not in found:
                found.append(phrase)
    return found


def _missing(phrase: str, present: set[str]) -> list[str]:
    """The content words of `phrase` that no token in `present` covers."""
    return [word for word in content_terms(phrase) if stem(word) not in present]


def contradictions(definition: str, prose: str) -> list[str]:
    """Places where the article does not omit the source, it disagrees with it.

    Two shapes only, both narrow enough that a hit is worth trusting:

    - **the age band.** The source counts 15-64 and the article says 20-64. An
      article may legitimately name another band while discussing a linked
      indicator, so this fires only when the source's own band appears nowhere.
    - **the inclusive edge.** "Con più di dieci addetti" and "con almeno dieci
      addetti" are different populations, and the swap survives every guard
      because both sentences use the same words and the same number. A reader
      caught exactly this on `ter-72`, in the lead, under a green suite, in an
      article that got it right in three other places. That is why the wrong
      form is reported even when the right one is also present: an article that
      draws the perimeter both ways has one sentence that is false, and it is
      the sentence the reader meets first.
    """
    found: list[str] = []

    source_bands = {(m.group(1), m.group(2)) for m in AGE_BAND.finditer(definition)}
    prose_bands = {(m.group(1), m.group(2)) for m in AGE_BAND.finditer(prose)}
    if source_bands and prose_bands and not (source_bands & prose_bands):
        found.append(
            "età: la fonte dice %s, l'articolo solo %s"
            % (
                ", ".join(f"{a}-{b} anni" for a, b in sorted(source_bands)),
                ", ".join(f"{a}-{b} anni" for a, b in sorted(prose_bands)),
            )
        )

    for pattern, opposite, source_words, prose_words in (
        (EXCLUSIVE, INCLUSIVE, "più di", "almeno"),
        (INCLUSIVE, EXCLUSIVE, "almeno", "più di"),
    ):
        for match in pattern.finditer(definition):
            number = _number(match.group("n"))
            noun = _fold(match.group("noun"))
            for other in opposite.finditer(prose):
                if _number(other.group("n")) != number:
                    continue
                if _fold(other.group("noun")) != noun:
                    continue
                found.append(
                    "soglia: la fonte dice \"%s %s %s\", l'articolo \"%s %s %s\""
                    % (source_words, number, noun, prose_words, number, noun)
                )
    return found


def check_entry(code: str, entry: dict, definition: dict | None) -> dict:
    """Every definition signal for one article."""
    fields = prose_lint.prose_fields(entry)
    all_prose = " ".join(text for _field, text in fields)
    defining = " ".join(
        text for field, text in fields
        if field in ("lead", "sections.definizione")
    )
    everywhere = tokens(all_prose)
    in_definition = tokens(defining)

    row = {
        "code": code,
        "hits": {},
        "definition": (definition or {}).get("definizione", ""),
        "official_title": (definition or {}).get("indicatore", ""),
        "has_definition_section": any(f == "sections.definizione" for f, _ in fields),
        "term_coverage": None,
    }

    if definition is None:
        row["hits"]["scoperto"] = ["nessuna definizione ufficiale in archivio"]
        return row
    if not row["definition"]:
        row["hits"]["scoperto"] = ["la riga esiste ma la definizione è vuota"]
        return row
    if not all_prose.strip():
        row["hits"]["vuoto"] = ["nessuna prosa scritta a mano"]
        return row

    if not row["has_definition_section"]:
        row["hits"]["assente"] = ["nessuna sezione definizione scritta a mano"]

    found = contradictions(row["definition"], all_prose)
    if found:
        row["hits"]["contraddizione"] = found

    # A share, not a list. The list of missing words was the first shape of this
    # check and it flagged 148 articles out of 179, which is the same as flagging
    # none: an article that says "chi lavora in azienda" for "addetti" is right
    # and still misses the word. What is worth a reviewer's time is an article
    # that echoes almost nothing of the official definition, and that is a ratio.
    terms = content_terms(row["definition"])
    if terms:
        absent = [word for word in terms if stem(word) not in everywhere]
        row["term_coverage"] = round((len(terms) - len(absent)) / len(terms), 2)
        if row["term_coverage"] < TERM_COVERAGE_FLOOR and len(absent) >= 3:
            row["hits"]["termini"] = absent

    for phrase in base_phrases(row["definition"]):
        absent = _missing(phrase, in_definition)
        if absent:
            row["hits"].setdefault("base", []).append(
                f"{phrase} (mai: {', '.join(absent)})"
            )

    for phrase in qualifiers(row["definition"]):
        absent = _missing(phrase, everywhere)
        digits = re.findall(r"\d[\d.]*", phrase)
        numbers_absent = [d for d in digits if d not in all_prose]
        if absent or (digits and numbers_absent):
            row["hits"].setdefault("soglia", []).append(phrase)

    return row


# The reading order, worst first. `contraddizione` leads because it is the only
# one that asserts the article is wrong rather than suggesting where to look;
# `termini` is the widest net and the noisiest, so it sorts under the rest.
SIGNAL_ORDER = ("contraddizione", "base", "soglia", "termini", "assente", "vuoto", "scoperto")
SIGNAL_LABELS = {
    "contraddizione": "l'articolo dice una cosa diversa dalla fonte, non una in meno",
    "base": "il denominatore della fonte non compare nella definizione scritta",
    "soglia": "una soglia o una classe di età della fonte non compare nell'articolo",
    "termini": "l'articolo riprende quasi nulla della definizione ufficiale",
    "assente": "nessuna sezione definizione scritta a mano, la compone il template",
    "vuoto": "articolo senza prosa",
    "scoperto": "nessuna definizione di fonte da confrontare nell'archivio",
}
# Only these mean "the article may be describing another quantity". `assente`,
# `vuoto` and `scoperto` describe our coverage, not the article's honesty, and a
# ratchet built on them would punish the pages nobody has written yet.
SUBSTANTIVE = ("contraddizione", "base", "soglia", "termini")

# Below this share of the definition's own content words, an article is not
# paraphrasing the source, it is talking about something else. Calibrated on the
# catalogue: see docs/INDICATOR_PAGES.md for what the number costs either way.
TERM_COVERAGE_FLOOR = 0.35


def official_id(code: str) -> str | None:
    """Canonical definition key from an internal id or public URL code."""
    parsed = sources.parse_indicator_code(str(code))
    if parsed:
        family, raw_id = parsed
        return sources.internal_id(family, raw_id)
    family, raw_id = sources.split_internal_id(str(code))
    if family != "territorial":
        return sources.internal_id(family, raw_id)
    return raw_id if raw_id.isdigit() else None


def build_report(texts: dict, definitions: dict) -> list[dict]:
    rows = []
    for key in sorted(texts):
        entry = texts[key]
        code = key if key.isdigit() else key.replace(":", "-", 1)
        if code.isdigit():
            code = f"ter-{code}"
        ident = official_id(key)
        rows.append(check_entry(code, entry, definitions.get(ident) if ident else None))
    rows.sort(
        key=lambda row: (
            -sum(len(row["hits"].get(name, [])) for name in SUBSTANTIVE),
            -len(row["hits"]),
            row["code"],
        )
    )
    return rows


def summarize(rows: list[dict]) -> dict:
    counts = {name: {"articles": 0, "occurrences": 0} for name in SIGNAL_ORDER}
    for row in rows:
        for name, found in row["hits"].items():
            counts[name]["articles"] += 1
            counts[name]["occurrences"] += len(found)
    covered = [row for row in rows if "scoperto" not in row["hits"]]
    clean = [
        row for row in covered
        if not any(name in row["hits"] for name in SUBSTANTIVE)
    ]
    return {
        "articles": len(rows),
        "covered": len(covered),
        "clean": len(clean),
        "checks": {name: counts[name] for name in SIGNAL_ORDER},
    }


def _print_summary(summary: dict) -> None:
    print(f"ARTICOLI ESAMINATI  {summary['articles']}")
    print(f"  con una definizione ufficiale da confrontare   {summary['covered']}")
    print(f"  di questi, senza nessun rilievo di sostanza    {summary['clean']}")
    print()
    print(f"  {'segnale':<10} {'articoli':>9} {'occorrenze':>11}   che cos'è")
    for name in SIGNAL_ORDER:
        data = summary["checks"][name]
        print(f"  {name:<10} {data['articles']:>9} {data['occurrences']:>11}   {SIGNAL_LABELS[name]}")


def _print_rows(rows: list[dict], limit: int, verbose: bool) -> None:
    shown = 0
    for row in rows:
        substantive = [n for n in SUBSTANTIVE if n in row["hits"]]
        if not substantive:
            continue
        if shown >= limit:
            break
        shown += 1
        print(f"{row['code']}   {row['official_title']}")
        if verbose:
            print(f"  fonte: {row['definition']}")
        for name in SIGNAL_ORDER:
            found = row["hits"].get(name)
            if not found or name not in SUBSTANTIVE:
                continue
            print(f"  [{name}] {SIGNAL_LABELS[name]}")
            head = found if verbose else found[:6]
            print(f"        {' | '.join(str(item) for item in head)}")
        print()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--show", help="un articolo solo (ter-402 o l'id interno)")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--texts", help="un file diverso da quello in repo")
    parser.add_argument("--definitions", type=Path, help="un CSV diverso da quello in repo")
    args = parser.parse_args(argv)

    texts = prose_lint.load_texts(args.texts)
    definitions = load_definitions(args.definitions)
    if not definitions:
        print("nessuna definizione in archivio: python3 scripts/fetch_definitions.py",
              file=sys.stderr)
        return 1

    if args.show:
        key = prose_lint.resolve_key(texts, args.show)
        if key is None:
            print(f"nessun articolo per {args.show}", file=sys.stderr)
            return 1
        texts = {key: texts[key]}

    rows = build_report(texts, definitions)

    if args.json:
        print(json.dumps({"rows": rows, "summary": summarize(rows)},
                         ensure_ascii=False, indent=1))
        return 0
    if args.summary:
        _print_summary(summarize(rows))
        return 0
    if args.show:
        row = rows[0]
        print(f"{row['code']}   {row['official_title']}")
        print(f"  fonte: {row['definition'] or '(nessuna)'}")
        if not row["hits"]:
            print("  nessun rilievo")
        for name in SIGNAL_ORDER:
            found = row["hits"].get(name)
            if not found:
                continue
            print(f"  [{name}] {SIGNAL_LABELS[name]}")
            for item in found:
                print(f"        {item}")
        return 0

    _print_rows(rows, args.limit, verbose=False)
    _print_summary(summarize(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
