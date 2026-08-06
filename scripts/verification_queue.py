"""Which published articles nobody has tried to falsify yet.

`text_queue` answers "what is left to write". `review_queue` answers "which of
the articles that exist is most likely to be wrong". This answers the third
question, the one the other two cannot: **of the articles a reviewer has already
signed, which ones has nobody tried to knock down?**

It exists because of a number. Reading eleven freshly written articles against
the data produced 19 false claims out of 392 checked. Verifying the same eleven
*after* the reviewer had signed them produced 7 out of 529. The reviewer removes
most of the errors and leaves some, and a signature is the reviewer's own word
about their own work, so nothing in the chain checked it:

    note migrate, mai rilette          113 controllate, 11 false   9,7%
    scritte nel lotto 2, non rilette   392 controllate, 19 false   4,8%
    scritte nel lotto 2 e rilette      529 controllate,  7 false   1,3%

The verifier corrects nothing. Its whole output is a row in
`data/pipeline/verifiche/`, one file per verification, and a refuted claim
comes back to the reviewer as
the `smentita` flag of `review_queue`, which outranks every other signal there.
Separating the two is the point: a stage that both finds and fixes grades its own
homework, which is the problem it was built to solve one level up.

    python3 scripts/verification_queue.py                 # la coda
    python3 scripts/verification_queue.py --open          # solo le smentite aperte
    python3 scripts/verification_queue.py --show ter-611
    python3 scripts/verification_queue.py --csv

## Perche' un'impronta della prosa e non una data

A verification is a statement about **a text**, so it expires when that text
changes, and nothing else expires it. The row carries a fingerprint of the prose
it read, and an article is verified only while its prose still hashes to that
value.

The alternative, comparing `reviewed_at` with the verification date, was written
first and thrown away: two events on the same day are indistinguishable, and the
reviewer who fixes a refuted sentence signs it the same day the verifier
refuted it. With the fingerprint there is no arithmetic and no tie. It is the
same discipline as `reviewed_vintage` for the reviewer, applied to the thing that
actually moved.

Pure stdlib, like every script in the chain.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import indicator_store  # noqa: E402  (path bootstrap above)

# Il registro delle verifiche, un file per verifica.
#
# Era un CSV unico a cui si appendeva in fondo, ed era la seconda meta' dello
# stesso guasto che ha fatto shardare il diario: due stadi che scrivono in coda
# allo stesso file collidono sempre, e il contratto se la cavava dicendo agli
# agenti di tenere entrambe le parti a mano. Peggio, il cancello pretende che
# il registro sia append-only, quindi una risoluzione sbagliata di quel
# conflitto era anche una violazione del cancello dello stadio che la faceva.
#
# Il nome del file e' la chiave naturale della verifica: quale articolo, a
# quale livello, e su quale versione della prosa. Riverificare lo stesso
# articolo dopo una correzione produce un'impronta nuova, quindi un file nuovo,
# quindi non si sovrascrive niente.
VERIFICATIONS_DIR = PROJECT_ROOT / "data" / "pipeline" / "verifiche"

COLUMNS = [
    "code",
    "level",
    "at",
    "vintage",
    "reviewed_at",
    # The fingerprint of the prose this row is a statement about. Everything
    # else in the row is informative; this is the field the queue joins on.
    "prosa",
    "controllate",
    "confermate",
    "smentite",
    "non_verificabili",
    "esito",
    # A pointer, not the record. The evidence for a refutation lives in the
    # pull request and in the journal's `detail`, because it is prose and does
    # not survive a semicolon-separated column intact.
    "rilievi",
]

OUTCOMES = ("pulito", "smentito")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
WHITESPACE = re.compile(r"\s+")


def prose_fingerprint(entry: dict) -> str:
    """A short hash of every hand-written word in an article.

    Ordered by role rather than by the list order so that reordering the
    sections, which changes nothing a verifier read, does not invalidate the
    verification. Whitespace is normalized for the same reason.

    **The authored `h` counts as prose**, and leaving it out was a real hole.
    118 sections carry a hand-written heading, they are visible on the page, and
    they make claims: `ter-651` heads its `dinamica` with "Cinque anni di
    guadagni, un anno che ne toglie piu' della meta'", which its verifier
    checked and confirmed (+1,413 against -0,855, the 61%). Hashing only the
    body meant a clean verification kept covering a replaced heading, and
    repairing a refuted heading did not requeue the article.
    """
    parts = [("lead", "", entry.get("lead") or "")]
    # I titoli autorati (`h1`, `seo_title`) sono prosa a tutti gli effetti, per la
    # stessa ragione per cui lo e' l'`h` di una sezione: sono visibili, e uno di
    # loro e' anche cio' che si legge in SERP, quindi puo' fare un'affermazione.
    # Sono campi vuoti su tutti gli articoli di oggi, percio' le trecento impronte
    # non si muovono, ma senza di loro un titolo aggiunto o corretto dopo la firma
    # lasciava la verifica vecchia a combaciare su una frase che nessuno ha mai
    # controllato: il buco che l'`h` ha gia' aperto una volta.
    for field in ("h1", "seo_title"):
        value = entry.get(field)
        if isinstance(value, str) and value.strip():
            parts.append((field, "", value))
    for section in entry.get("sections") or []:
        parts.append((
            section.get("role") or "",
            section.get("h") or "",
            section.get("body") or "",
        ))
    blob = "\n".join(
        role + ":" + WHITESPACE.sub(" ", heading).strip()
        + ":" + WHITESPACE.sub(" ", text).strip()
        for role, heading, text in sorted(parts)
    )
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


def load_texts(root=None) -> dict:
    """Tutti gli articoli. `root` e' una directory di store, non piu' un file."""
    return indicator_store.load_all(root)


def verification_name(row: dict) -> str:
    """Il nome del file di una verifica: articolo, livello, impronta della prosa.

    Sono i tre campi su cui la verifica e' un'affermazione, quindi due file con
    lo stesso nome sarebbero la stessa verifica scritta due volte, e due
    verifiche diverse non possono mai ricadere sullo stesso nome.
    """
    code = (row.get("code") or "ignoto").replace("/", "-")
    level = (row.get("level") or "regione").replace("/", "-")
    prosa = (row.get("prosa") or "senza-impronta").replace("/", "-")
    return f"{code}__{level}__{prosa}.json"


def load_verifications(path=None) -> list[dict]:
    """Tutte le verifiche.

    `path` accetta una directory di shard o un `.csv`, per la stessa ragione
    per cui `pipeline_log.read_journal` accetta tutte e due le forme: i test
    ne scrivono uno temporaneo e la catena scrive l'altra. Il vecchio registro
    unico non si legge piu' in automatico perche' non esiste piu': le sue righe
    sono state travasate negli shard, e leggerle da tutte e due le parti le
    avrebbe contate due volte.
    """
    target = Path(path) if path else VERIFICATIONS_DIR
    if target.is_dir():
        return _read_verification_shards(target)
    if target.exists():
        return _read_verification_csv(target)
    return []


def _read_verification_shards(root) -> list[dict]:
    rows = []
    for shard in sorted(Path(root).glob("*.json")):
        try:
            data = json.loads(shard.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            rows.append({column: data.get(column, "") for column in COLUMNS})
    return sorted(rows, key=lambda r: (r.get("at") or "", r.get("code") or ""))


def _read_verification_csv(path) -> list[dict]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def write_verification(row: dict, root=None) -> Path:
    """Registra una verifica. Ritorna il file scritto.

    Una per volta e non una lista: il verificatore ne produce una per articolo,
    e una funzione che riscrive tutto il registro e' esattamente il modo in cui
    un registro append-only smette di esserlo per sbaglio.
    """
    target = Path(root or VERIFICATIONS_DIR)
    target.mkdir(parents=True, exist_ok=True)
    payload = {column: row.get(column, "") for column in COLUMNS}
    path = target / verification_name(payload)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def code_of(key: str) -> str:
    """The URL form of an internal key, which is how the rest of the chain writes it."""
    return f"ter-{key}" if key.isdigit() else key.replace(":", "-", 1)


def _int(value) -> int:
    """Lenient, for display and for counting. `row_problems` is the strict one."""
    try:
        return int(str(value).strip() or 0)
    except ValueError:
        return 0


COUNTERS = ("controllate", "confermate", "smentite", "non_verificabili")


def _counter(value) -> int | None:
    """A counter, or None when the cell is not a non-negative integer.

    Both halves matter and both were missing. A non-numeric cell used to read as
    zero, so a typo produced a silent "I checked nothing". A negative cell used
    to survive: `controllate=40, confermate=41, smentite=-1` sums to 40 and
    passed every check, while `smentite > 0` stayed false, so the refutation was
    recorded and invisible at the same time.
    """
    text = str(value).strip()
    if not text.isdigit():
        return None
    return int(text)


def row_problems(row: dict) -> list[str]:
    """Why a verification row cannot be believed, if it cannot.

    `controllate` is the field that does not negotiate: without it, "zero
    refutations" and "I did not look" are the same zero, and the whole stage
    becomes a rubber stamp that costs a pull request per article.
    """
    problems = []
    if not (row.get("code") or "").strip():
        problems.append("nessun codice")
    if not DATE.fullmatch((row.get("at") or "").strip()):
        problems.append(f"data non valida: {row.get('at')!r}")
    if not (row.get("prosa") or "").strip():
        problems.append("nessuna impronta della prosa")
    counters = {name: _counter(row.get(name)) for name in COUNTERS}
    malformed = sorted(name for name, value in counters.items() if value is None)
    if malformed:
        problems.append(
            "contatori che non sono interi non negativi: "
            + ", ".join(f"{name}={row.get(name)!r}" for name in malformed)
        )
        return problems
    controllate = counters["controllate"]
    if controllate <= 0:
        problems.append("affermazioni_controllate a zero: una verifica che non ha guardato")
    parts = sum(counters[name] for name in ("confermate", "smentite", "non_verificabili"))
    if controllate and parts != controllate:
        problems.append(
            f"i conti non tornano: {parts} fra confermate, smentite e non verificabili "
            f"contro {controllate} controllate"
        )
    esito = (row.get("esito") or "").strip()
    if esito not in OUTCOMES:
        problems.append(f"esito ignoto {esito!r}, attesi {' o '.join(OUTCOMES)}")
    elif (esito == "pulito") != (counters["smentite"] == 0):
        problems.append(f"esito {esito!r} con {counters['smentite']} smentite")
    return problems


def build_queue(texts=None, verifications=None) -> list[dict]:
    """One row per signed article, saying whether a verification still covers it."""
    texts = texts if texts is not None else load_texts()
    verifications = verifications if verifications is not None else load_verifications()

    by_key: dict[tuple[str, str], list[dict]] = {}
    for row in verifications:
        by_key.setdefault(((row.get("code") or "").strip(), (row.get("level") or "").strip()), []).append(row)

    out = []
    for key in sorted(texts):
        entry = texts[key]
        code = code_of(key)
        level = entry.get("level") or "regione"
        signed = (entry.get("reviewed_at") or "").strip()
        vintage = entry.get("vintage")
        # Only a signed article is worth verifying. On an unsigned one the
        # verifier would be measuring the writer, which is a useful experiment
        # (it is how the 4,8% above was obtained) and a terrible standing queue:
        # the reviewer is about to rewrite the sentences anyway.
        current = bool(DATE.fullmatch(signed)) and entry.get("reviewed_vintage") == vintage
        fingerprint = prose_fingerprint(entry)
        rows = by_key.get((code, level), [])
        match = next((r for r in rows if (r.get("prosa") or "").strip() == fingerprint), None)
        latest = rows[-1] if rows else None
        open_refutation = bool(
            match and _int(match.get("smentite")) > 0
        )
        out.append({
            "code": code,
            "key": key,
            "level": level,
            "vintage": vintage,
            "reviewed_at": signed,
            "verifiable": current,
            "verified": match is not None,
            "prosa": fingerprint,
            "smentite": _int(match.get("smentite")) if match else 0,
            "controllate": _int(match.get("controllate")) if match else 0,
            "open_refutation": open_refutation,
            "rilievi": (match or {}).get("rilievi", "") if match else "",
            # A verification of prose that has since changed is not a failure,
            # it is simply spent. Naming it separately keeps "never verified"
            # apart from "verified, then rewritten", which need different reading.
            "stale": bool(latest and match is None),
        })
    return out


def waiting(rows: list[dict]) -> list[dict]:
    """The articles the verifier should take, worst first."""
    todo = [row for row in rows if row["verifiable"] and not row["verified"]]
    # A spent verification first: somebody rewrote a text that had been checked,
    # so it is the one place where a refuted sentence could have come back.
    todo.sort(key=lambda row: (not row["stale"], row["code"]))
    return todo


def open_refutations(rows: list[dict]) -> list[dict]:
    return [row for row in rows if row["open_refutation"]]


def summarize(rows: list[dict]) -> dict:
    verifiable = [row for row in rows if row["verifiable"]]
    verified = [row for row in verifiable if row["verified"]]
    return {
        "articoli": len(rows),
        "firmati": len(verifiable),
        "verificati": len(verified),
        "da_verificare": len(waiting(rows)),
        "riverificare": sum(1 for row in verifiable if row["stale"] and not row["verified"]),
        "smentite_aperte": len(open_refutations(rows)),
        "affermazioni_controllate": sum(row["controllate"] for row in verified),
        "smentite": sum(row["smentite"] for row in verified),
    }


def _print(rows: list[dict], limit: int) -> None:
    summary = summarize(rows)
    print(
        f"{summary['articoli']} articoli, {summary['firmati']} firmati dal revisore, "
        f"{summary['verificati']} verificati, {summary['da_verificare']} da verificare."
    )
    if summary["riverificare"]:
        print(f"  di cui {summary['riverificare']} da riverificare: il testo e' cambiato dopo la verifica")
    if summary["affermazioni_controllate"]:
        print(
            f"  finora: {summary['affermazioni_controllate']} affermazioni controllate, "
            f"{summary['smentite']} smentite"
        )
    aperte = open_refutations(rows)
    if aperte:
        print(f"  SMENTITE APERTE su {len(aperte)} articoli, tocca al revisore:")
        for row in aperte[:limit]:
            print(f"    {row['code']:16} {row['smentite']} smentite   {row['rilievi'][:90]}")
    print()
    todo = waiting(rows)
    if not todo:
        print("nessun articolo firmato resta senza verifica")
        return
    print(f"{'codice':18} {'liv':10} {'vintage':>7}  {'stato'}")
    print("-" * 70)
    for row in todo[:limit]:
        state = "riverificare" if row["stale"] else "mai verificato"
        print(f"{row['code']:18} {row['level']:10} {str(row['vintage']):>7}  {state}")
    if len(todo) > limit:
        print(f"\n... e altri {len(todo) - limit}. Usa --all per l'elenco completo.")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--open", action="store_true",
                        help="solo le smentite aperte, quelle che il revisore deve chiudere")
    parser.add_argument("--show", help="un articolo solo (ter-611, bes-12SER003)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--texts", help="una directory di articoli, o un vecchio file unico")
    parser.add_argument("--verifiche")
    args = parser.parse_args(argv)

    rows = build_queue(load_texts(args.texts), load_verifications(args.verifiche))

    problems = [
        (row.get("code"), problem)
        for row in load_verifications(args.verifiche)
        for problem in row_problems(row)
    ]
    if problems:
        print("ATTENZIONE, righe di verifica non credibili:", file=sys.stderr)
        for code, problem in problems[:10]:
            print(f"  {code}: {problem}", file=sys.stderr)

    if args.show:
        wanted = args.show.strip()
        row = next((r for r in rows if r["code"] == wanted or r["key"] == wanted), None)
        if row is None:
            print(f"nessun articolo per {args.show}", file=sys.stderr)
            return 1
        print(json.dumps(row, ensure_ascii=False, indent=1))
        return 0
    if args.json:
        print(json.dumps({"rows": rows, "summary": summarize(rows)}, ensure_ascii=False, indent=1))
        return 0
    if args.csv:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        print(buffer.getvalue(), end="")
        return 0
    if args.open:
        for row in open_refutations(rows):
            print(f"{row['code']:16} {row['smentite']} smentite   {row['rilievi']}")
        return 0

    _print(rows, len(rows) if args.all else args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
