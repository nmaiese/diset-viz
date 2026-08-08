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
first H2 opens on "il numeratore è in equivalenti a tempo pieno, il denominatore
no", accounting before the story. The reader-editor is that independent judge:
read-only, `soft` (queues, never blocks the merge), a sibling of the verifier
rather than a link in a chain.

## The store, and why a fingerprint

A reading is a statement about **a text**, exactly like a verification, so it
expires when that text changes and nothing else expires it. Each record carries
`reading_fingerprint` of the prose it read, and a reading covers an article only
while its prose still hashes to that value. It is **not** the verifier's
fingerprint: that one sorts sections by role because a verifier does not care
about order, while a reading judges `structure` among its criteria, where order
is exactly what is being judged. A rewrite for readability still expires the
verification too (the two fingerprints differ, but the verifier's own
`prose_fingerprint` still changes with the wording), and the article is re-read
and re-verified. One file per reading in `data/pipeline/letture/`, append-only,
named for the three fields a reading is an assertion about:
`{code}__{level}__{fingerprint}.json`.

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
import hashlib
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import indicator_store  # noqa: E402  (path bootstrap above)
from scripts import verification_queue  # noqa: E402


def reading_fingerprint(entry: dict) -> str:
    """A fingerprint of the prose a reading judged, sensitive to section order.

    `verification_queue.prose_fingerprint` sorts sections by role on purpose: a
    verifier checks facts, and reordering sections changes nothing it read. A
    reader-editor judges *readability*, where order is part of what is being
    judged (`structure` is one of `CRITERIA`): moving `limiti` ahead of
    `dinamica` is exactly the kind of fix a `revise` on `structure` asks for,
    and the role-sorted fingerprint cannot see it. Reusing it here meant a
    structure-only rewrite left the stale `revise` reading in place: the
    fingerprint still matched, so no new reading was scheduled and the
    rewrite-brake counter stayed pinned to the old text forever.

    Otherwise identical to `prose_fingerprint`: same rendered-only filter, same
    whitespace normalisation, same emitted-roles suffix. Only the join key
    changes (list order instead of role), so two readings of prose that only
    differ in section order now land on different files, as they should.
    """
    rendered = set(verification_queue._emitted_role_list(entry))
    parts = [("lead", "", entry.get("lead") or "")]
    for section in entry.get("sections") or []:
        role = section.get("role") or ""
        if role and role not in rendered:
            continue
        parts.append((role, section.get("h") or "", section.get("body") or ""))
    blob = "\n".join(
        f"{index}:{role}:"
        + verification_queue.WHITESPACE.sub(" ", heading).strip()
        + ":" + verification_queue.WHITESPACE.sub(" ", text).strip()
        for index, (role, heading, text) in enumerate(parts)
    )
    emitted = verification_queue._emitted_roles(entry)
    if emitted is not None:
        blob += "\nruoli-emessi:" + ",".join(emitted)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]

# Il registro delle letture, un file per lettura. Perimetro del solo
# reader-editor, come `verifiche/` lo è del solo verificatore: un registro
# append-only, un file per record, così due letture concorrenti non collidono
# mai su una coda condivisa.
READINGS_DIR = PROJECT_ROOT / "data" / "pipeline" / "letture"

# I criteri della leggibilità, ognuno 0-2, assi separati mai una media unica:
# una grande accuratezza non deve poter compensare una pessima leggibilità, che
# è il difetto per cui la rubrica a punteggio unico non basta.
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
    # L'impronta della prosa su cui questa lettura è un'affermazione. Tutto il
    # resto è informativo, questo è il campo su cui la coda fa il join.
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
# parcheggia: è il tetto ai round di riscrittura-per-leggibilità del produttore,
# non ai fatti. Tre tentativi prima di fermare il loop.
READABILITY_ROUNDS = 3

# I fallimenti duri ammessi, gli stessi sette di `.claude/agents/reader-editor.md`.
# Un vocabolario chiuso e non testo libero perché queste stringhe non sono prosa:
# `review_queue` e il lanciatore le uniscono in una riga per il produttore, e una
# classe inventata da una run non vorrebbe dire niente per chi la legge dopo.
HARD_FAILURES = (
    "lead_requires_methodology",
    "thesis_unidentifiable",
    "what_is_measured_unclear",
    "filler_section",
    "undefined_key_jargon",
    "numeric_overload",
    "interchangeable_article",
)

DATE = re.compile(r"\d{4}-\d{2}-\d{2}")

# I tre sostanziali, non i quattro ruoli. `definizione` è la sola omettibile,
# perché il blocco "Come leggere il dato" la copre, ed è la regola che
# `app.indicator_texts.SUBSTANTIVE_ROLES` possiede e che questo modulo
# rispecchia (stdlib puro, non importa `app`). Pretendendone quattro, questa
# coda dichiarava incompleto ogni articolo della macchina nuova, che la
# definizione la omette apposta: `ter-30` scrive `quadro, limiti, dinamica`, e
# la pagina lo rende completo mentre la coda lo teneva fuori.
_REQUIRED_ROLES = verification_queue.SUBSTANTIVE_ROLES


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
    una per articolo, e una funzione che riscrive tutto il registro è il modo in
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
    """Un criterio 0-2, o None quando la cella non è un intero in quell'intervallo."""
    text = str(value).strip()
    if not text.lstrip("-").isdigit():
        return None
    number = int(text)
    return number if 0 <= number <= 2 else None


def _text(value) -> str:
    """Una cella di testo, o stringa vuota se non è testo."""
    return value.strip() if isinstance(value, str) else ""


def _low_scores(row: dict) -> list:
    """I criteri che questa lettura ha messo sotto il massimo, dal più basso.

    Sono l'indirizzo della bocciatura: `structure` a 0 e `cognitive_load` a 1
    dicono al produttore che deve rifare l'ordine e alleggerire i periodi, non
    cambiare lessico. Un criterio a 2 non è un problema e non entra.
    """
    scored = [(name, _score(row.get(name))) for name in CRITERIA]
    return [(name, value) for name, value in sorted(
        (pair for pair in scored if pair[1] is not None and pair[1] < 2),
        key=lambda pair: (pair[1], pair[0]))]


def _hard_failures(row: dict) -> list:
    """I fallimenti duri di una riga, sempre come lista di stringhe.

    Difensivo di proposito: il cancello rifiuta una scheggia storta, ma questa
    funzione gira anche su ciò che è già fuso, e ciò che ne esce finisce in
    `", ".join(...)` nel lanciatore e in `review_queue`. Un elemento che non è
    una stringa (`[["numeric_overload"]]`, la lista annidata più facile da
    scrivere a mano) alzerebbe lì un TypeError, cioè fermerebbe coda,
    lanciatore e coda del revisore per il catalogo intero. Meglio perdere un
    elemento illeggibile che la catena.
    """
    raw = row.get("hard_failures") or []
    if isinstance(raw, str):
        raw = [part.strip() for part in raw.split(";") if part.strip()]
    if not isinstance(raw, (list, tuple)):
        return []
    return [item.strip() for item in raw if isinstance(item, str) and item.strip()]


def row_problems(row: dict) -> list[str]:
    """Perché una lettura non è credibile, se non lo è.

    Lo strict per lo store, sul modello di `verification_queue.row_problems`. Il
    verdetto e i criteri devono essere coerenti: un `pass` con un fallimento duro,
    o un `revise` senza un solo criterio sotto il massimo e senza fallimenti duri,
    è una contraddizione, esattamente come `esito=pulito` con smentite.
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
        problems.append("verdetto 'revise' senza un criterio sotto il massimo né un fallimento duro")
    # La nota è il punto d'inciampo, cioè l'unica cosa che il produttore riceve
    # per sapere DOVE riscrivere: una bocciatura muta è un'opinione, e rimette la
    # riscrittura a indovinare. Il tipo si controlla sempre, anche su un `pass`,
    # per un motivo che non è formale: `build_queue` fa `.strip()` su questo
    # campo, quindi una nota scritta come lista (`"note": ["..."]`, l'errore più
    # facile da fare a mano in un JSON) alzerebbe un AttributeError dopo il merge
    # e fermerebbe la coda, il lanciatore e la coda del revisore per il catalogo
    # intero.
    # I fallimenti duri sono un vocabolario chiuso, e il controllo guarda il campo
    # **grezzo**: `_hard_failures` scarta in silenzio ciò che non è una stringa
    # (per non far cadere la coda su una scheggia già fusa), quindi un cancello
    # che leggesse solo il ripulito accetterebbe proprio la riga storta che deve
    # fermare, e la lista annidata arriverebbe intatta al `join` del lanciatore.
    raw_failures = row.get("hard_failures") or []
    if isinstance(raw_failures, str):
        raw_failures = [part.strip() for part in raw_failures.split(";") if part.strip()]
    if not isinstance(raw_failures, (list, tuple)):
        problems.append(f"fallimenti duri che non sono una lista: {type(raw_failures).__name__}")
    else:
        bad = [item for item in raw_failures
               if not isinstance(item, str) or item.strip() not in HARD_FAILURES]
        if bad:
            problems.append(
                "fallimenti duri ignoti: " + ", ".join(repr(item) for item in bad[:3])
                + f". Ammessi: {', '.join(HARD_FAILURES)}")
    note = row.get("note", "")
    if not isinstance(note, str):
        problems.append(f"nota che non è una stringa: {type(note).__name__}")
    elif verdict == "revise" and not note.strip():
        problems.append("verdetto 'revise' senza nota: dove inciampa il lettore va scritto")
    return problems


def _eligible(entry: dict) -> bool:
    """Un articolo è leggibile-da-un-lettore quando è completo e firmato.

    Completo = lead più i quattro ruoli con un corpo scritto; firmato =
    `reviewed_at` valorizzato. È vicino ma non identico a `pubblicata` di
    `practice_timeline`: quello pretende anche la verifica (`verificatore` fra i
    `required_stages`), questo no. La differenza è voluta e utile: un articolo
    firmato ma non ancora verificato si può già leggere, ed è proprio l'ordine
    che l'hint del lanciatore vuole (leggere prima di verificare, così una
    bocciatura non spreca una verifica su un testo che verrà riscritto). Letto
    dai soli testi per tenere questo modulo indipendente dalla macchina a stati.

    L'officina entra dalla seconda porta, come nella coda di verifica: non ha un
    revisore, quindi la firma non arriverà mai, e senza questa riga il reader
    editor resterebbe in ombra su una macchina che non gli manda niente da
    leggere. Resta `soft` in entrambi i casi: accoda, non ferma un merge.
    """
    lead = (entry.get("lead") or "").strip()
    roles = {
        section.get("role")
        for section in entry.get("sections") or []
        if (section.get("body") or "").strip()
    }
    firmato = bool(entry.get("reviewed_at")) or entry.get("origine") == verification_queue.OFFICINA
    return bool(lead) and _REQUIRED_ROLES.issubset(roles) and firmato


def load_texts(root=None) -> dict:
    return indicator_store.load_all(root)


def build_queue(texts=None, readings=None) -> list[dict]:
    """Una riga per articolo pubblicato: il suo stato di lettura contro la prosa di adesso.

    `status` è uno di:
      `unread`  nessuna lettura copre la prosa corrente -> tocca al reader-editor;
      `revise`  la lettura corrente boccia, e il codice non è parcheggiato -> tocca
                al produttore (riscrittura per leggibilità);
      `parked`  la lettura corrente boccia ma `READABILITY_ROUNDS` versioni sono
                già state bocciate -> il freno morde, non si lancia niente;
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
        fingerprint = reading_fingerprint(entry)
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
            # Il punto d'inciampo e i criteri caduti, non solo che l'articolo è
            # caduto. La riga è ciò che il lanciatore trasforma in un lancio del
            # produttore, e senza queste due voci la riscrittura parte cieca: il
            # produttore sa di essere stato bocciato e non sa dove, quindi può
            # riscrivere l'altra metà dell'articolo e farsi bocciare di nuovo
            # finché il freno non parcheggia il codice. Il reader-editor la nota
            # la scrive già (`note`, obbligatoria su un `revise`), e buttarla via
            # qui era il modo più caro di non leggerla.
            # `_text` e non `.strip()` diretto: il cancello rifiuta una nota che
            # non è una stringa, ma questa coda gira anche su ciò che è già
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

    È la sorgente del flag `leggibilita` di `review_queue`, l'analogo di
    `verification_queue.open_refutations` per l'altro critico: solo lo stato
    `revise` (impronta corrente, sotto il tetto del freno), mai `parked`, così
    un articolo che non converge smette di tornare al produttore per leggibilità
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
