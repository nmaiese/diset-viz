"""Which published articles a reader has found hard, and which nobody has read yet.

Three queues already exist. `text_queue` answers "what is left to write".
`review_queue` answers "which existing article is most likely to be *wrong*".
`verification_queue` answers "which signed article has nobody tried to *falsify*".
This answers a fourth, on an axis none of the others measure: **of the published
articles, which ones is a common reader unlikely to understand at first pass,
and which ones has no reader-editor looked at yet?**

It exists because the producer writes, self-judges readability, and signs, so the
one axis a factually clean article can still fail on is the one nobody
independent checks. `eur-rd_p_persreg` is the case: every figure is right and the
first H2 opens on "il numeratore e' in equivalenti a tempo pieno, il denominatore
no", accounting before the story. The reader-editor is that independent judge:
read-only, `soft` (queues, never blocks the merge), a sibling of the verifier
rather than a link in a chain.

## The store, and why a fingerprint

A reading is a statement about **a text**, exactly like a verification, so it
expires when that text changes and nothing else expires it. Each record carries
`prose_fingerprint` of the prose it read, and a reading covers an article only
while its prose still hashes to that value. Reusing the verifier's fingerprint is
deliberate: a rewrite for readability changes it, which expires *both* the reading
and the verification, and the article is re-read and re-verified. One file per
reading in `data/pipeline/letture/`, append-only, named for the three fields a
reading is an assertion about: `{code}__{level}__{fingerprint}.json`.

## The brake, and why it lives here and not in the prompt

A `revise` sends the article back to the producer, whose rewrite changes the
fingerprint, which expires the reading, which re-reads and can `revise` again.
Left unbounded on an unattended chain, one stubborn article ping-pongs producer
and reader-editor forever, and each round costs a producer *and* a verifier run
(the rewrite expires the verification too). The brake is a count, here in the
queue where the gate perimeter can see it, never in the agent prompt where it
could not be enforced: after `READABILITY_ROUNDS` distinct prose versions of a
code have each been told `revise`, the code is *parked*. Parking stops the
producer from being launched *for readability* on that code. It does not stop a
producer launched for another reason (a data refresh), and that rewrite gets a
fresh reading like any other.

Pure stdlib, like every script in the chain.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import indicator_store  # noqa: E402  (path bootstrap above)
from scripts import verification_queue  # noqa: E402
from scripts.verification_queue import prose_fingerprint  # noqa: E402  (single source)

# Il registro delle letture, un file per lettura. Perimetro del solo
# reader-editor, come `verifiche/` lo e' del solo verificatore: un registro
# append-only, un file per record, cosi' due letture concorrenti non collidono
# mai su una coda condivisa.
READINGS_DIR = PROJECT_ROOT / "data" / "pipeline" / "letture"

# I criteri della leggibilita', ognuno 0-2, assi separati mai una media unica:
# una grande accuratezza non deve poter compensare una pessima leggibilita', che
# e' il difetto per cui la rubrica a punteggio unico non basta.
CRITERIA = (
    "comprehension",
    "focus",
    "reader_relevance",
    "search_intent_coverage",
    "cognitive_load",
    "technical_translation",
    "structure",
    "unique_value",
)

VERDICTS = ("pass", "revise")

COLUMNS = [
    "code",
    "level",
    "at",
    "reviewed_at",
    # L'impronta della prosa su cui questa lettura e' un'affermazione. Tutto il
    # resto e' informativo, questo e' il campo su cui la coda fa il join.
    "prosa",
    "verdict",
    *CRITERIA,
    # Fallimenti duri: il lettore comune non capisce la pagina (lead che pretende
    # metodologia, tesi non identificabile, cosa misura il dato non si capisce,
    # sezione riempi-schema, tecnicismo decisivo non spiegato, carico numerico
    # eccessivo, articolo intercambiabile). Con `soft` accodano con peso alto.
    "hard_failures",
    # Un puntatore, non il record: la prova sta nella pull request e nel diario.
    "note",
]

# Dopo quante versioni distinte della prosa, ognuna bocciata, un codice si
# parcheggia: e' il tetto ai round di riscrittura-per-leggibilita' del produttore,
# non ai fatti. Tre tentativi prima di fermare il loop.
READABILITY_ROUNDS = 3

DATE = re.compile(r"\d{4}-\d{2}-\d{2}")

_REQUIRED_ROLES = {"definizione", "quadro", "dinamica", "limiti"}


def reading_name(row: dict) -> str:
    """Il nome del file di una lettura: articolo, livello, impronta della prosa.

    Gli stessi tre campi della verifica, e per la stessa ragione: due file con
    lo stesso nome sarebbero la stessa lettura scritta due volte, e due letture
    diverse non possono mai ricadere sullo stesso nome.
    """
    code = (row.get("code") or "ignoto").replace("/", "-")
    level = (row.get("level") or "regione").replace("/", "-")
    prosa = (row.get("prosa") or "senza-impronta").replace("/", "-")
    return f"{code}__{level}__{prosa}.json"


def load_readings(path=None) -> list[dict]:
    """Tutte le letture. `path` accetta una directory di shard (come le verifiche)."""
    target = Path(path) if path else READINGS_DIR
    if not target.is_dir():
        return []
    rows = []
    for shard in sorted(target.glob("*.json")):
        try:
            data = json.loads(shard.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            rows.append({column: data.get(column, "") for column in COLUMNS})
    return sorted(rows, key=lambda r: (r.get("at") or "", r.get("code") or ""))


def write_reading(row: dict, root=None) -> Path:
    """Registra una lettura. Ritorna il file scritto.

    Una per volta e non una lista, come le verifiche: il reader-editor ne produce
    una per articolo, e una funzione che riscrive tutto il registro e' il modo in
    cui un registro append-only smette di esserlo per sbaglio.
    """
    target = Path(root or READINGS_DIR)
    target.mkdir(parents=True, exist_ok=True)
    payload = {column: row.get(column, "") for column in COLUMNS}
    path = target / reading_name(payload)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _score(value):
    """Un criterio 0-2, o None quando la cella non e' un intero in quell'intervallo."""
    text = str(value).strip()
    if not text.lstrip("-").isdigit():
        return None
    number = int(text)
    return number if 0 <= number <= 2 else None


def _text(value) -> str:
    """Una cella di testo, o stringa vuota se non e' testo."""
    return value.strip() if isinstance(value, str) else ""


def _low_scores(row: dict) -> list:
    """I criteri che questa lettura ha messo sotto il massimo, dal piu' basso.

    Sono l'indirizzo della bocciatura: `structure` a 0 e `cognitive_load` a 1
    dicono al produttore che deve rifare l'ordine e alleggerire i periodi, non
    cambiare lessico. Un criterio a 2 non e' un problema e non entra.
    """
    scored = [(name, _score(row.get(name))) for name in CRITERIA]
    return [(name, value) for name, value in sorted(
        (pair for pair in scored if pair[1] is not None and pair[1] < 2),
        key=lambda pair: (pair[1], pair[0]))]


def _hard_failures(row: dict) -> list:
    raw = row.get("hard_failures") or []
    if isinstance(raw, str):
        raw = [part.strip() for part in raw.split(";") if part.strip()]
    return list(raw)


def row_problems(row: dict) -> list[str]:
    """Perche' una lettura non e' credibile, se non lo e'.

    Lo strict per lo store, sul modello di `verification_queue.row_problems`. Il
    verdetto e i criteri devono essere coerenti: un `pass` con un fallimento duro,
    o un `revise` senza un solo criterio sotto il massimo e senza fallimenti duri,
    e' una contraddizione, esattamente come `esito=pulito` con smentite.
    """
    problems = []
    if not (row.get("code") or "").strip():
        problems.append("nessun codice")
    if not DATE.fullmatch((row.get("at") or "").strip()):
        problems.append(f"data non valida: {row.get('at')!r}")
    if not (row.get("prosa") or "").strip():
        problems.append("nessuna impronta della prosa")
    scores = {name: _score(row.get(name)) for name in CRITERIA}
    malformed = sorted(name for name, value in scores.items() if value is None)
    if malformed:
        problems.append(
            "criteri che non sono interi in 0-2: "
            + ", ".join(f"{name}={row.get(name)!r}" for name in malformed)
        )
    verdict = (row.get("verdict") or "").strip()
    if verdict not in VERDICTS:
        problems.append(f"verdetto ignoto {verdict!r}, attesi {' o '.join(VERDICTS)}")
        return problems
    if malformed:
        return problems
    failures = _hard_failures(row)
    below_max = any(scores[name] < 2 for name in CRITERIA)
    if verdict == "pass" and failures:
        problems.append(f"verdetto 'pass' con fallimenti duri: {failures}")
    if verdict == "revise" and not below_max and not failures:
        problems.append("verdetto 'revise' senza un criterio sotto il massimo ne' un fallimento duro")
    # La nota e' il punto d'inciampo, cioe' l'unica cosa che il produttore riceve
    # per sapere DOVE riscrivere: una bocciatura muta e' un'opinione, e rimette la
    # riscrittura a indovinare. Il tipo si controlla sempre, anche su un `pass`,
    # per un motivo che non e' formale: `build_queue` fa `.strip()` su questo
    # campo, quindi una nota scritta come lista (`"note": ["..."]`, l'errore piu'
    # facile da fare a mano in un JSON) alzerebbe un AttributeError dopo il merge
    # e fermerebbe la coda, il lanciatore e la coda del revisore per il catalogo
    # intero.
    note = row.get("note", "")
    if not isinstance(note, str):
        problems.append(f"nota che non e' una stringa: {type(note).__name__}")
    elif verdict == "revise" and not note.strip():
        problems.append("verdetto 'revise' senza nota: dove inciampa il lettore va scritto")
    return problems


def _eligible(entry: dict) -> bool:
    """Un articolo e' leggibile-da-un-lettore quando e' completo e firmato.

    Completo = lead piu' i quattro ruoli con un corpo scritto; firmato =
    `reviewed_at` valorizzato. E' vicino ma non identico a `pubblicata` di
    `practice_timeline`: quello pretende anche la verifica (`verificatore` fra i
    `required_stages`), questo no. La differenza e' voluta e utile: un articolo
    firmato ma non ancora verificato si puo' gia' leggere, ed e' proprio l'ordine
    che l'hint del lanciatore vuole (leggere prima di verificare, cosi' una
    bocciatura non spreca una verifica su un testo che verra' riscritto). Letto
    dai soli testi per tenere questo modulo indipendente dalla macchina a stati.
    """
    lead = (entry.get("lead") or "").strip()
    roles = {
        section.get("role")
        for section in entry.get("sections") or []
        if (section.get("body") or "").strip()
    }
    return bool(lead) and _REQUIRED_ROLES.issubset(roles) and bool(entry.get("reviewed_at"))


def load_texts(root=None) -> dict:
    return indicator_store.load_all(root)


def build_queue(texts=None, readings=None) -> list[dict]:
    """Una riga per articolo pubblicato: il suo stato di lettura contro la prosa di adesso.

    `status` e' uno di:
      `unread`  nessuna lettura copre la prosa corrente -> tocca al reader-editor;
      `revise`  la lettura corrente boccia, e il codice non e' parcheggiato -> tocca
                al produttore (riscrittura per leggibilita');
      `parked`  la lettura corrente boccia ma `READABILITY_ROUNDS` versioni sono
                gia' state bocciate -> il freno morde, non si lancia niente;
      `clean`   la lettura corrente promuove -> niente da fare.
    """
    texts = texts if texts is not None else load_texts()
    readings = readings if readings is not None else load_readings()

    by_key: dict[tuple[str, str], list[dict]] = {}
    for row in readings:
        key = (row.get("code") or "", row.get("level") or "regione")
        by_key.setdefault(key, []).append(row)

    out = []
    for key, entry in texts.items():
        if not _eligible(entry):
            continue
        code = verification_queue.code_of(key)
        level = (entry.get("level") or "regione")
        fingerprint = prose_fingerprint(entry)
        rows = by_key.get((code, level), [])
        match = next((r for r in rows if (r.get("prosa") or "").strip() == fingerprint), None)
        revised_versions = {
            r.get("prosa") for r in rows
            if (r.get("verdict") or "").strip() == "revise" and (r.get("prosa") or "").strip()
        }
        parked = len(revised_versions) >= READABILITY_ROUNDS

        if match is None:
            status = "unread"
        elif (match.get("verdict") or "").strip() == "revise":
            status = "parked" if parked else "revise"
        else:
            status = "clean"

        out.append({
            "code": code,
            "key": key,
            "level": level,
            "prosa": fingerprint,
            "status": status,
            "verdict": (match.get("verdict") or "").strip() if match else "",
            "hard_failures": _hard_failures(match) if match else [],
            # Il punto d'inciampo e i criteri caduti, non solo che l'articolo e'
            # caduto. La riga e' cio' che il lanciatore trasforma in un lancio del
            # produttore, e senza queste due voci la riscrittura parte cieca: il
            # produttore sa di essere stato bocciato e non sa dove, quindi puo'
            # riscrivere l'altra meta' dell'articolo e farsi bocciare di nuovo
            # finche' il freno non parcheggia il codice. Il reader-editor la nota
            # la scrive gia' (`note`, obbligatoria su un `revise`), e buttarla via
            # qui era il modo piu' caro di non leggerla.
            # `_text` e non `.strip()` diretto: il cancello rifiuta una nota che
            # non e' una stringa, ma questa coda gira anche su cio' che e' gia'
            # fuso e non deve poter morire su una scheggia storta.
            "note": _text(match.get("note")) if match else "",
            "low_scores": _low_scores(match) if match else [],
            "revised_rounds": len(revised_versions),
        })
    return sorted(out, key=lambda r: (r["status"], r["code"]))


def unread(rows) -> list[dict]:
    """Gli articoli senza una lettura corrente: il lavoro del reader-editor."""
    return [r for r in rows if r["status"] == "unread"]


def to_revise(rows) -> list[dict]:
    """Gli articoli bocciati e non parcheggiati: il lavoro di riscrittura del produttore."""
    return [r for r in rows if r["status"] == "revise"]


def open_revisions(texts=None, readings=None) -> dict:
    """{(codice, livello): riga} per gli articoli che una lettura corrente boccia
    e non sono parcheggiati.

    E' la sorgente del flag `leggibilita` di `review_queue`, l'analogo di
    `verification_queue.open_refutations` per l'altro critico: solo lo stato
    `revise` (impronta corrente, sotto il tetto del freno), mai `parked`, cosi'
    un articolo che non converge smette di tornare al produttore per leggibilita'
    invece di restare in cima alla sua coda per sempre.
    """
    rows = build_queue(texts, readings)
    return {(r["code"], r["level"]): r for r in rows if r["status"] == "revise"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unread", action="store_true", help="solo i non ancora letti")
    parser.add_argument("--revise", action="store_true", help="solo i bocciati da riscrivere")
    parser.add_argument("--json", action="store_true", help="uscita per un altro programma")
    args = parser.parse_args(argv)

    rows = build_queue()
    if args.unread:
        rows = unread(rows)
    elif args.revise:
        rows = to_revise(rows)

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0

    if not rows:
        print("Niente in coda di lettura.")
        return 0
    for row in rows:
        extra = ""
        if row["status"] == "parked":
            extra = f" (parcheggiato dopo {row['revised_rounds']} round)"
        elif row["status"] == "revise":
            extra = f" ({row['revised_rounds']} round finora)"
        print(f"{row['status']:8} {row['code']:28.28} {row['level']:9} {row['prosa']}{extra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
