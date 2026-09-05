"""Lo stato editoriale dell'atlante: che cosa e' scritto, e che cosa manca.

Un criterio solo, e sta qui. La coda della redazione (`motore coda` nel repo
`nmaiese/redazione-ai`) e il cruscotto devono mostrare **la stessa classifica**:
due punteggi per la stessa domanda divergono, e questo progetto ha gia' pagato
per una regola copiata in due posti. La redazione importa da qui, non ricalcola.

Sta nel sito e non nella redazione per due ragioni. Il cruscotto lo serve
questa app, che non ha la redazione in immagine; e chi calcola lo stato deve
leggere `app.*` (catalogo, view model), quindi tenerlo di la' chiuderebbe un
anello di import.
"""

import hashlib

from app import sources
from app.cache_util import synchronized_cache
from app.indicator_texts import build_article, emitted_roles, get_text
from app.indicator_universe import projection
from scripts.prose_rules import rilievi as rilievi_prosa


def parole(entry):
    """Le parole di un articolo: lead piu' i corpi delle sezioni.

    Sta qui e non nella redazione perche' la usano tutti e due, e il
    cruscotto confronta il conteggio dell'articolo servito con quello che la run
    ha registrato: se i due conteggi non sono la stessa funzione, il confronto
    misura la differenza fra due definizioni invece che fra due articoli.
    """
    testo = " ".join([entry.get("lead") or ""] +
                     [s.get("body") or "" for s in entry.get("sections") or []])
    return len(testo.split())


def impronta_prosa(entry):
    """L'identita' della prosa di un articolo: lead piu' `sections[].{role,h,body}`.

    E' il `prose_fingerprint` che `app/indicator_texts.build_article` e
    `docs/INDICATOR_PAGES.md` gia' nominano: qui c'e' la funzione, e la
    definizione e' quella che quei due testi dichiarano.

    I conteggi non identificano un testo. Il cruscotto confrontava le sole
    parole per dire se l'articolo servito e' quello che l'ultima run ha scritto,
    e due riscritture della stessa lunghezza si leggevano `in linea` con
    certezza `alta` mentre la pagina in produzione era un'altra: una
    pubblicazione in attesa che spariva dalla vista.

    **Non e' l'impronta della bozza** (quella che `motore verifica` calcola
    sulla bozza nel repo della redazione), che
    congela il testo *prima* che venga scritto e ci mette dentro anche le fonti,
    per accorgersi se e' finita su disco una bozza diversa da quella verificata.
    Due domande diverse, e i nomi restano diversi apposta: li' si chiede se il
    testo pubblicato e' quello approvato, qui se il disco e' in linea col deploy.
    """
    # Spazi normalizzati dalle due parti: la run stampa l'impronta dell'entry
    # che ha appena scritto, il sito la ricalcola dal JSON servito, e un a capo
    # diverso fra i due non e' una riscrittura.
    # I ruoli emessi entrano, e non e' un di piu': assorbire la definizione nel
    # blocco "Come leggere il dato" cambia quello che la pagina mostra **senza
    # toccare una parola**, quindi un'entry che riscrive solo `roles_covered`
    # si leggerebbe "in linea" mentre in produzione c'e' un'altra pagina.
    pezzi = [",".join(emitted_roles(entry)),
             " ".join((entry.get("lead") or "").split())]
    for sezione in entry.get("sections") or []:
        if not isinstance(sezione, dict):
            continue
        pezzi.append("\x1f".join([
            (sezione.get("role") or "").strip(),
            (sezione.get("h") or "").strip(),
            " ".join((sezione.get("body") or "").split()),
        ]))
    testo = "\x1e".join(pezzi)
    return hashlib.sha256(testo.encode("utf-8")).hexdigest()[:16]


@synchronized_cache(maxsize=1)
def _per_coppia():
    return {(r["family"], r["raw_id"]): r for r in projection()}


def _valuta(record, level_key=None):
    """Lo stato editoriale di un indicatore a un livello, dalla proiezione."""
    meta = record["meta"]
    level = next((lv for lv in record["levels"] if lv["key"] == level_key),
                 record["levels"][0])
    article = build_article(meta["id"], level["key"])
    # `missing` è relativo alle sezioni che l'articolo emette: un'entry con
    # `roles_covered` che assorbe la definizione nel blocco "Come leggere" non
    # emette quella sezione, quindi non risulta "da scrivere" (altrimenti il
    # produttore la riscriverebbe a ogni run).
    missing = [s["role"] for s in article["sections"] if not s["authored"]]
    vintage = article["vintage"]
    stale = vintage is not None and vintage < level["year_max"]

    # A stale figure is wrong, a missing section is only plain: staleness wins.
    # Then how much of the article is missing, then whether anyone will see it.
    score = 0
    if stale:
        score += 100
    if not article["lead"]:
        score += 20
    score += 10 * len(missing)
    if meta["indexable"]:
        score += 15
    return {
        "id": meta["id"],
        "code": sources.indicator_code(record["family"], record["raw_id"]),
        "level": level["key"],
        "levels": len(record["levels"]),
        # Il livello predefinito e' quello su cui l'articolo va scritto:
        # `content/indicators/` tiene un file per **indicatore**, quindi un
        # articolo provinciale sostituirebbe quello regionale invece di
        # aggiungersi. Senza questo campo le 34 righe non predefinite si leggono
        # come lavoro da fare e non lo sono.
        "default_level": record["default_level"],
        "name": meta["name"],
        "theme": meta["theme"],
        "family": record["family"],
        "family_label": meta["family_label"],
        "indexable": meta["indexable"],
        "indexable_reason": meta.get("indexable_reason"),
        "canonical_path": meta["canonical_path"],
        "year_max": level["year_max"],
        "vintage": vintage,
        "stale": stale,
        "lead": bool(article["lead"]),
        "missing": missing,
        "written": len(article["sections"]) - len(missing),
        # Il denominatore è quello dell'articolo, non il quattro fisso: un
        # articolo opt-in completo ne emette tre, e stamparlo come `3/4` accanto
        # a `mancano: -` dava all'operatore due segnali che si contraddicono.
        "sections": len(article["sections"]),
        # L'anatomia dell'articolo, ruolo per ruolo, col titolo che l'autore ha
        # scritto. Il cruscotto la disegna come un glifo di cinque parti (il lead
        # piu' i quattro ruoli): il conteggio da solo direbbe "2 su 4" senza dire
        # **quali** due, e i due che mancano non si riparano allo stesso modo.
        "roles": [{"role": s["role"], "authored": bool(s["authored"]),
                   "heading": s.get("heading")} for s in article["sections"]],
        "score": score,
    }


def assess(family, raw_id, level_key=None):
    """The editorial state of one indicator at one territorial level.

    Level-aware on purpose. This used to read `levels[0]` and call
    `build_article` with no level, so the 34 two-level BES indicators were only
    ever judged on their regional half: a provincial article, once written,
    still showed as `0/4` and could never be reported as done, while the
    provincial page of every other one was invisible to the worklist.
    """
    record = _per_coppia().get((family, str(raw_id)))
    return None if record is None else _valuta(record, level_key)


@synchronized_cache(maxsize=1)
def build_queue():
    """One row per (indicator, territorial level), because that is the unit of
    work: an article is written against one level and used only there."""
    rows = []
    for record in projection():
        for level in record["levels"]:
            rows.append(_valuta(record, level["key"]))
    rows.sort(key=lambda row: (-row["score"], row["name"], row["level"]))
    return rows


def da_scrivere(row):
    """Il predicato di "incompleto", in un posto solo: lo usano la coda, il
    dossier e il conteggio del cruscotto."""
    return bool(row["missing"]) or not row["lead"] or row["stale"]


@synchronized_cache(maxsize=1)
def catalogo():
    """Le righe del cruscotto editoriale piu' i totali del recap.

    Una riga per (indicatore, livello), che e' l'unita' della coda verbatim: due
    unita' diverse per la stessa cosa divergono. Le righe predefinite sono i 634
    indicatori con una pagina.

    In cache per la vita del processo, come `projection()`: `content/indicators/`
    lo legge `app/indicator_texts._load()` sotto `lru_cache`, quindi dentro un
    processo e' congelato, e un deploy ricrea il processo. Mai `@cache.memoize`,
    che ripicklerebbe centinaia di KB ogni trenta secondi e rifarebbe la passata
    a ogni scadenza per riottenere lo stesso identico risultato.
    """
    righe = []
    misurati = {}
    for row in build_queue():
        if row["id"] not in misurati:
            entry = get_text(row["id"])
            misurati[row["id"]] = ((len(rilievi_prosa(entry)), parole(entry), impronta_prosa(entry))
                                   if entry else (0, 0, None))
        # Un articolo vale per **un livello solo** (`entry["level"]`), mentre lo
        # store tiene un file per indicatore: la riga dell'altro livello vede
        # quello stesso file ma la sua pagina non ne rende una parola. Attribuirle
        # quelle parole direbbe che c'e' un testo dove non c'e', e il confronto
        # con le parole della run leggerebbe "non in linea" per sempre.
        serve_questo_livello = bool(row["written"]) or row["lead"]
        conta_rilievi, conta_parole, firma = (
            misurati[row["id"]] if serve_questo_livello else (0, 0, None))
        righe.append({
            "id": row["id"],
            "codice": row["code"],
            "nome": row["name"],
            "famiglia": row["family"],
            "famiglia_label": row["family_label"],
            "tema": row["theme"],
            "livello": row["level"],
            "livelli": row["levels"],
            "predefinito": row["level"] == row["default_level"],
            "anno_dato": row["year_max"],
            "vintage": row["vintage"],
            "arretrato": row["stale"],
            "lead": row["lead"],
            "mancanti": row["missing"],
            "scritte": row["written"],
            "sezioni": row["sections"],
            "ruoli": row["roles"],
            "indicizzabile": row["indexable"],
            "motivo": row["indexable_reason"],
            "percorso": row["canonical_path"],
            "punteggio": row["score"],
            "rilievi": conta_rilievi,
            "parole": conta_parole,
            "impronta_prosa": firma,
        })
    return {"righe": righe, "totali": _totali(righe)}


def _totali(righe):
    predefinite = [r for r in righe if r["predefinito"]]
    return {
        "indicatori": len(predefinite),
        "pagine": len(righe),
        "indicizzabili": sum(1 for r in predefinite if r["indicizzabile"]),
        "con_articolo": sum(1 for r in predefinite if r["scritte"] or r["lead"]),
        "completi": sum(1 for r in predefinite
                        if not r["mancanti"] and r["lead"] and not r["arretrato"]),
        "arretrati": sum(1 for r in predefinite if r["arretrato"]),
        "senza_testo": sum(1 for r in predefinite if not r["scritte"] and not r["lead"]),
        "rilievi": sum(r["rilievi"] for r in predefinite),
    }


def cache_clear():
    _per_coppia.cache_clear()
    build_queue.cache_clear()
    catalogo.cache_clear()
