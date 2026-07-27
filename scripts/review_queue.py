"""What a human still has to read: articles ranked by editorial risk.

`text_queue` answers "what is left to write". This answers the other question,
the one that grows instead of shrinking: **of the articles that exist, which
ones are most likely to be wrong?**

The mechanical guards in `tests/test_indicator_texts.py` check what a regex can
check: style, structure, vintage, decimal figures attributed to a region, and
thresholds asserted over a list of regions. Everything they cannot check is
listed in `docs/INDICATOR_PAGES.md` and needs eyes. That list is not a vague
warning, it is a set of patterns, and a pattern can be looked for:

    definizione     the article describes a quantity the source does not define
    universale      "ovunque", "sempre", "da anni": one counter-example makes it false
    causale         "grazie a", "spinto da": the indicator shows no mechanism
    esterno         a claim about Europe or a national ranking with no source in `fonti`
    provincia       figures on a provincial article, which the region regex cannot read
    eco             a figure the cockpit already prints, restated in the prose
    mestiere        the bot tells content/STYLE.md names, from scripts/prose_lint

None of these is a defect by itself. They are the sentences where a defect
hides, so they decide reading order rather than pass or fail. An article the
reviewer has signed off carries `reviewed_at` and leaves the queue until its
text or its data changes.

`definizione` is the newest and it sorts above all the others, including
`rilettura`. It comes from `scripts/definition_check`, which reads the article
against Istat's own wording in `data/definitions/istat_territoriali.csv`. Every
other signal here marks a sentence that might be false about the numbers; this
one marks a sentence that might be false about what the page is even measuring,
and that is the one class a reader checking arithmetic will confirm as correct.

    .venv/bin/python -m scripts.review_queue                # top of the queue
    .venv/bin/python -m scripts.review_queue --all
    .venv/bin/python -m scripts.review_queue --flag definizione
    .venv/bin/python -m scripts.review_queue --flag causale
    .venv/bin/python -m scripts.review_queue --csv
    .venv/bin/python -m scripts.review_queue --show dem:OLDAGEDEPR
"""

import argparse
import csv
import io
import re

from app import indicator_texts, sources
from app.indicator_view import build_indicator_view
from scripts import definition_check, indicator_store, prose_lint, verification_queue
from scripts.fetch_definitions import load_definitions

# A claim that holds "everywhere" or "always" is false the moment one territory
# disagrees, and the brief has a block (SI MUOVONO CONTROCORRENTE) that settles
# it in one look. Two real notes shipped with this exact mistake.
UNIVERSAL = re.compile(
    r"\b(ovunque|sempre|storicamente|da anni|in ogni regione|in tutte le regioni|"
    r"in nessuna regione|nessuna regione|tutte le regioni|senza eccezioni|"
    r"in ogni provincia|in tutte le province)\b", re.I,
)
# A territorial indicator shows a level, never a mechanism. These are the
# phrasings that quietly turn a correlation into a cause.
CAUSAL = re.compile(
    r"\b(grazie a|grazie all|spinto da|spinta da|trainato da|per effetto|"
    r"a causa d|dovuto a|dovuta a|per merito|complice|colpa d|"
    r"si spiega con|dipende dal|dipende dalla)\w*", re.I,
)
# Anything comparing outside this dataset needs a verified source in `fonti`.
EXTERNAL_CLAIM = re.compile(
    r"\b(europ\w+|\bUE\b|\bOCSE\b|\bOECD\b|media nazionale|in Italia|"
    r"primato|record|il più alto d|la più alta d|il più basso d|la più bassa d)", re.I,
)
DECIMAL = re.compile(r"\d+,\d+")
# The bot tells live in `scripts/prose_lint`, which owns the patterns and the
# catalogue-wide counts. Borrowed rather than restated: a second copy of the spy
# lexicon here would drift from the one the writer lints its draft against, and
# the two would then disagree about the same sentence.
#
# The closing question is deliberately left out of the flag. It is on 340 of the
# 364 articles, so as a *reading order* signal it is a constant added to almost
# every row, which changes nothing and hides the rest. It stays a backlog number
# in `prose_lint --summary` and an instruction in the reviewer's prompt.
#
# `ripetuto` is in, and it is the reason this is a subtraction from every signal
# rather than a copy of `CHECKS`. It lives outside `CHECKS` in `prose_lint`
# because it compares two numbers instead of matching a pattern, and taking
# `CHECKS` verbatim silently excluded it: the one signal two independent judges
# named on their own, the one worth the most per occurrence, was the one the
# reading order could not see. ter-408 carried it and the queue said "nessun
# segnale di rischio". Built as "everything except the questions" so a check
# added to `prose_lint` tomorrow reaches the reviewer by default, which is the
# direction the mistake should point.
CRAFT_TELLS = tuple(name for name in prose_lint.ALL_SIGNALS if name != "domanda")

# The signals from `definition_check` that mean "this article may be describing
# another quantity". `termini` is left out: it is a coverage ratio over the
# official wording, and an article that says "chi lavora in azienda" for
# "addetti" trips it while being right. It stays reachable from the script,
# which is where a loose net belongs.
DEFINITION_SIGNALS = ("contraddizione", "base", "soglia")

FLAG_LABELS = {
    "smentita": "il verificatore ha fatto cadere un'affermazione, ed e' ancora in pagina",
    "definizione": "descrive una quantita' diversa da quella della fonte",
    "universale": "afferma un andamento generale",
    "causale": "attribuisce una causa",
    "esterno": "confronto fuori dal dataset senza fonte",
    "provincia": "cifre provinciali, non verificate dalle guardie",
    "eco": "ripete una cifra del cruscotto",
    "mestiere": "tell da bot che STYLE.md nomina",
    "rilettura": "i dati si sono mossi dopo la firma",
}
# Weights: how much each pattern moves an article up the reading order. A causal
# claim is the worst because it is invisible to every guard and reads as fact.
FLAG_WEIGHT = {
    # Il primo di tutti, e l'unico che non e' un sospetto. Ogni altro segnale qui
    # marca una frase che *potrebbe* essere sbagliata: questo marca una frase che
    # un verificatore avversariale ha gia' fatto cadere, con la prova, e che e'
    # ancora in pagina perche' nessuno l'ha riscritta. Il verificatore non ha
    # `content/indicators/` nel perimetro proprio perche' la riparazione tocchi
    # a chi legge questa coda, quindi se questo segnale non fosse in cima il
    # cerchio non si chiuderebbe e la smentita resterebbe in un registro.
    "smentita": 60,
    # `definizione` viene subito dopo, sopra `rilettura`, and it is the only
    # flag whose rank was decided by counting. Reading a batch of eleven
    # articles against the data found no arithmetic error and four wrong
    # descriptions of what the indicator counts. A wrong figure dies at the
    # first reader who opens the brief; a wrong definition survives every
    # reading that checks arithmetic, because the arithmetic is right. `ter-402`
    # carried one into the `limiti` section, which is the place meant to say
    # what the indicator does not measure.
    "definizione": 50,
    # `rilettura` outranks the risk flags on purpose. The others mark a sentence
    # that *might* be wrong; this one marks an article whose figures have been
    # rewritten since anybody read it, so nothing in it has been checked at all.
    "rilettura": 45,
    "causale": 40, "esterno": 30, "universale": 25, "provincia": 20,
    # Below `provincia` on purpose. A bot tell makes an article read badly, the
    # flags above mark one that may be false, and a false sentence outranks an
    # ugly one every time.
    "mestiere": 15, "eco": 10,
}


def load_texts(root=None):
    """Tutti gli articoli. `root` e' una directory di store, non piu' un file."""
    return indicator_store.load_all(root)


def resolve_key(texts, code):
    """The internal id for a code written either way, or None.

    `--show` used to index the texts dict directly, so it accepted the internal
    id (`920`, `bes:10AMB004`) and silently refused the URL form (`ter-920`,
    `bes-10AMB004`). The URL form is the one every other command in the chain
    takes, and it is the one this file's own docstring and the reviewer's prompt
    put in their examples, so the documented invocation answered "nessun
    articolo" for every indicator. A reviewer that hits that either works around
    it or skips the step, and neither leaves a trace.
    """
    if code in texts:
        return code
    parsed = sources.parse_indicator_code(code)
    if parsed is not None:
        key = sources.internal_id(*parsed)
        if key in texts:
            return key
    return None


def prose_fields(entry):
    """(field, text) for every piece of hand-written prose in an entry."""
    out = []
    if entry.get("lead"):
        out.append(("lead", entry["lead"]))
    for section in entry.get("sections") or []:
        if (section.get("body") or "").strip():
            out.append((f"sections.{section.get('role')}", section["body"]))
    return out


def _cockpit_figures(level):
    """The numbers the cockpit prints on its own, to two decimals as strings.

    Restating one of these is the duplication the layout was rebuilt to remove
    (docs/INDICATOR_PAGES.md), and no guard catches it because the figure is
    correct. It is only redundant.
    """
    stats = level["stats"]
    values = [
        stats.get("year_avg"), stats.get("gap_abs"),
        (level.get("best") or {}).get("value"), (level.get("worst") or {}).get("value"),
    ]
    annual = level.get("annual_change") or {}
    values.append(annual.get("average_delta"))
    out = set()
    for value in values:
        if isinstance(value, (int, float)):
            out.add(f"{value:.2f}".replace(".", ","))
    return out


def open_refutations(texts=None, verifications=None):
    """{(codice, livello): [rilievi]} per le smentite ancora in pagina.

    Aperta vuol dire che la prosa di adesso e' ancora quella che il verificatore
    ha fatto cadere. Se qualcuno l'ha riscritta la smentita e' spenta, e
    l'articolo torna in coda al verificatore invece che qui: le due code si
    passano il lavoro senza che nessuna delle due debba cancellare una riga
    dell'altra.
    """
    try:
        rows = verification_queue.build_queue(
            texts if texts is not None else verification_queue.load_texts(),
            verifications if verifications is not None else verification_queue.load_verifications(),
        )
    except (OSError, ValueError):
        return {}
    out = {}
    for row in verification_queue.open_refutations(rows):
        detail = row.get("rilievi") or f"{row['smentite']} smentite senza dettaglio"
        out[(row["code"], row["level"])] = [detail]
    return out


def assess(key, entry, view=None, definitions=None, refutations=None):
    """Risk flags and a reading-order score for one article."""
    if view is None:
        family, raw_id = sources.split_internal_id(key)
        view = build_indicator_view(family, raw_id)
    if view is None:
        return None
    level_key = entry.get("level") or indicator_texts.DEFAULT_LEVEL
    level = next((lv for lv in view["levels"] if lv["key"] == level_key), None)
    if level is None:
        return None

    fields = prose_fields(entry)
    text = " ".join(body for _, body in fields)
    has_sources = bool(entry.get("fonti"))
    cockpit = _cockpit_figures(level)

    hits = {}
    for flag, pattern in (
        ("universale", UNIVERSAL), ("causale", CAUSAL), ("esterno", EXTERNAL_CLAIM),
    ):
        found = sorted({m.group(0).lower() for m in pattern.finditer(text)})
        if found and not (flag == "esterno" and has_sources):
            hits[flag] = found
    if level_key != "regione" and DECIMAL.search(text):
        hits["provincia"] = sorted({m.group(0) for m in DECIMAL.finditer(text)})[:5]
    echoed = sorted({m.group(0) for m in DECIMAL.finditer(text)} & cockpit)
    if echoed:
        hits["eco"] = echoed
    linted = prose_lint.inspect(entry) or {"hits": {}}
    tells = [
        found for name in CRAFT_TELLS for found in linted["hits"].get(name, [])
    ]
    if tells:
        hits["mestiere"] = tells

    meta = view["meta"]
    # Le smentite aperte, lette dal registro del verificatore. `None` significa
    # "non guardato": un chiamante che non passa il registro non deve ricevere un
    # silenzio che somiglia a "nessuna smentita".
    if refutations is None:
        refutations = open_refutations()
    code_now = sources.indicator_code(meta["family"], meta["raw_id"])
    refuted = refutations.get((code_now, level_key))
    if refuted:
        hits["smentita"] = refuted

    # The definitions CSV covers the territorial family only, and may not have
    # been fetched at all on a fresh checkout. Both cases mean "no opinion", not
    # "clean": `definition_check` says `scoperto` and the flag stays off.
    if definitions is None:
        definitions = load_definitions()
    official = definitions.get(definition_check.official_id(key) or "")
    if official:
        found = definition_check.check_entry(
            sources.indicator_code(meta["family"], meta["raw_id"]), entry, official
        )["hits"]
        clashes = [
            f"{name}: {item}"
            for name in DEFINITION_SIGNALS
            for item in found.get(name, [])
        ]
        if clashes:
            hits["definizione"] = clashes

    score = sum(FLAG_WEIGHT[flag] for flag in hits)
    if meta["indexable"]:
        score += 15
    if meta.get("quality_life_scored"):
        score += 10
    reviewed = (entry.get("reviewed_at") or "").strip()
    vintage = entry.get("vintage")
    reviewed_vintage = entry.get("reviewed_vintage")
    # A signature is a statement about a text *and* about the numbers under it,
    # so it expires when the numbers move. The writer refreshes an article whose
    # vintage has fallen behind, which rewrites the figures in every sentence:
    # the reader who signed off did not read those sentences. Without this the
    # queue would drain once and never refill, and the chain would look finished
    # while the published catalogue quietly aged underneath it.
    #
    # Keyed on the vintage, not on a calendar interval: a series that has not
    # published a new year has nothing new to read, and re-reading it on a timer
    # is churn dressed up as diligence.
    #
    # Una smentita aperta invalida la firma allo stesso modo di un vintage che non
    # combacia, e per la stessa ragione: la firma dice "l'ho letto e regge", e un
    # verificatore ha mostrato con la prova che una frase non regge. Senza questa
    # riga il segnale `smentita` valeva 60 e poi lo azzeravamo due righe sotto,
    # perche' l'articolo e' firmato: il peso c'era, l'articolo restava fuori dalla
    # coda, e il cerchio fra i due stadi non si chiudeva. Trovato provando il
    # segnale invece di fidarsi del fatto che comparisse.
    refuted = "smentita" in hits
    stale_signature = bool(reviewed) and reviewed_vintage != vintage
    if reviewed and not stale_signature and not refuted:
        # Signed off and still current: it stays in --all for the record, out of
        # the reading order.
        score = 0
    elif stale_signature:
        hits["rilettura"] = [f"firmato sul {reviewed_vintage or 'ignoto'}, ora {vintage}"]
        score += FLAG_WEIGHT["rilettura"]
    return {
        "id": key,
        "code": sources.indicator_code(meta["family"], meta["raw_id"]),
        "level": level_key,
        "name": meta["name"],
        "indexable": meta["indexable"],
        "written": sum(1 for field, _ in fields if field.startswith("sections.")),
        "reviewed_at": "" if (stale_signature or refuted) else reviewed,
        "signed_vintage": reviewed_vintage,
        "vintage": vintage,
        "flags": hits,
        "score": score,
    }


def build_queue(texts=None):
    texts = texts if texts is not None else load_texts()
    # Read once for the whole catalogue rather than once per article: 364 reads
    # of the same CSV is the kind of thing that makes a tool too slow to run.
    definitions = load_definitions()
    refutations = open_refutations(texts)
    rows = []
    for key, entry in texts.items():
        assessed = assess(key, entry, definitions=definitions, refutations=refutations)
        if assessed is not None:
            rows.append(assessed)
    rows.sort(key=lambda row: (-row["score"], row["name"]))
    return rows


def _print_one(key, entry, row):
    print(f"{row['code']}  ({row['id']}, livello {row['level']})")
    print(f"  {row['name']}")
    print(f"  indicizzabile: {'si' if row['indexable'] else 'no'}   "
          f"sezioni scritte: {row['written']}/4   "
          f"revisionato: {row['reviewed_at'] or 'mai'}")
    if not row["flags"]:
        print("  nessun segnale di rischio")
    for flag, found in row["flags"].items():
        print(f"  [{flag}] {FLAG_LABELS[flag]}")
        print(f"        {', '.join(str(f) for f in found[:6])}")
    print()
    for field, body in prose_fields(entry):
        print(f"  --- {field} ---")
        for line in body.split("\n"):
            if line.strip():
                print(f"  {line}")
        print()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--all", action="store_true", help="include articles already reviewed")
    parser.add_argument("--flag", help="only articles carrying this flag")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--show", help="print one article in full, with its flags")
    args = parser.parse_args(argv)

    texts = load_texts()
    if args.show:
        key = resolve_key(texts, args.show)
        if key is None:
            print(f"nessun articolo per {args.show}")
            return 1
        row = assess(key, texts[key])
        if row is None:
            print(f"{args.show}: indicatore non risolvibile")
            return 1
        _print_one(key, texts[key], row)
        return 0

    rows = build_queue(texts)
    if args.flag:
        rows = [row for row in rows if args.flag in row["flags"]]
    pending = [row for row in rows if not row["reviewed_at"]]

    if args.csv:
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=[
            "code", "id", "level", "name", "indexable", "written", "reviewed_at", "flags", "score",
        ], extrasaction="ignore")
        writer.writeheader()
        for row in (rows if args.all else pending):
            writer.writerow({**row, "flags": " ".join(row["flags"])})
        print(out.getvalue(), end="")
        return 0

    reviewed = sum(1 for row in rows if row["reviewed_at"])
    print(f"{len(rows)} articoli scritti, {reviewed} gia revisionati, "
          f"{len(pending)} da leggere.")
    counts = {}
    for row in pending:
        for flag in row["flags"]:
            counts[flag] = counts.get(flag, 0) + 1
    if counts:
        print("segnali: " + ", ".join(f"{flag} {n}" for flag, n in sorted(counts.items())))
    print()
    shown = (rows if args.all else pending)[: None if args.all else args.limit]
    print(f"{'codice':<18} {'liv':<10} {'idx':<4} {'segnali':<34} nome")
    print("-" * 118)
    for row in shown:
        flags = ",".join(row["flags"]) or ("ok" if row["reviewed_at"] else "-")
        print(f"{row['code']:<18} {row['level']:<10} "
              f"{'si' if row['indexable'] else 'no':<4} {flags:<34} {row['name'][:44]}")
    if not args.all and len(pending) > args.limit:
        print(f"\n... e altri {len(pending) - args.limit}. Usa --all per l'elenco completo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
