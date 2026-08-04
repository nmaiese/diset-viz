#!/usr/bin/env python3
"""Il vocabolario della pratica editoriale, come codice.

Questo modulo e' la Fase A resa eseguibile: gli stati finiti, i tipi di pratica,
le transizioni ammesse, la tassonomia degli errori e il punteggio di priorita'
descritti in `docs/EDITORIAL_PRACTICE.md`. Non tocca il disco e non conosce la
catena: sono definizioni pure, cosi' che una regola del dominio si possa provare
con un test invece che discutere a voce.

Nessun import fuori dalla stdlib, come ogni script della catena: gira su un
checkout fresco, prima che esista il venv dell'app.
"""

from __future__ import annotations

# --- Stati (docs/EDITORIAL_PRACTICE.md, §3) ---------------------------------
# Uno solo attivo per pratica. Ogni stato ha una condizione verificabile contro
# gli artefatti: e' cio' che rende lo stato "dichiarato ma riconciliabile" e non
# semplicemente dedotto.
STATES = (
    "proposta",            # un candidato approved non ancora promosso
    "in-lavorazione",      # uno stadio obbligatorio non e' ancora completo
    "in-attesa",           # ferma in attesa di una condizione (vedi IN_ATTESA_MOTIVI)
    "pronta-al-merge",     # tutti gli stadi del ciclo completi, cancello verde
    "fusa",                # il ciclo e' su master, non ancora verificato sul sito
    "pubblicata",          # visibile sul sito e verificata
    "invalidata",          # un input e' cambiato: passaggi a valle non valgono piu'
    "in-quarantena",       # in-attesa terminale, tolta dalla coda per non fermare le altre
    "chiusa",              # esito terminale raggiunto
)

# I motivi che qualificano `in-attesa`. Un solo stato di sosta, armonizzato dai due
# di prima (`in-attesa-di-monte` + `bloccata`): il motivo dice perche', e porta la
# classe d'errore giusta (monte-mancante e' un'attesa normale, senza errore; gli
# altri aspettano un cambio esterno o una correzione tecnica).
IN_ATTESA_MOTIVI = (
    "monte-mancante",       # l'artefatto dello stadio a monte non esiste ancora
    "dipendenza-esterna",   # aspetta un chiarimento o un cambio alla fonte / config
    "tecnico",              # una correzione tecnica (cancello rosso, conflitto)
)

# --- Esiti terminali (§7) ----------------------------------------------------
# "PR chiusa" non e' un esito editoriale. Una pratica `chiusa` porta uno di questi.
TERMINAL_OUTCOMES = (
    "pubblicata-verificata",  # il solo esito "riuscito"
    "rifiutata",
    "duplicata",
    "sostituita",
    "ritirata",
    "bloccata-terminale",
    "annullata",
)

# --- Tipi di pratica (§2) ----------------------------------------------------
# Piu' due oggetti pre-pratica che non aprono un record: la ricognizione delle
# fonti e la scoperta dei candidati restano batch (§5).
PRACTICE_TYPES = (
    "nuovo",
    "aggiornamento",
    "revisione",
    "smentita",
    "integrazione",
    "ritiro",
    "rollback",
    "metadati",
)
PRE_PRACTICE = ("candidato-fonte", "candidato-indicatore")

# L'ordine di catena degli stadi editoriali (dopo la promozione). Coincide con
# l'ordine di precedenza del lanciatore per gli stadi che toccano una pratica.
EDITORIAL_STAGES = ("promoter", "curator", "writer", "reviewer", "verificatore")

# Lo stadio in cui una pratica di ciascun tipo entra.
ENTRY_STAGE = {
    "nuovo": "promoter",
    "aggiornamento": "writer",
    "revisione": "reviewer",
    "smentita": "reviewer",
    "integrazione": "curator",
    "ritiro": "curator",
    "rollback": "reviewer",
    "metadati": "curator",
}

# Gli stadi obbligatori per tipo (§2). Gli stadi non elencati sono saltabili, e
# si saltano solo se una condizione verificabile lo consente (es. il
# verificatore e' saltabile "se la prosa non cambia", controllabile con
# l'impronta `prosa` che gia' esiste).
REQUIRED_STAGES = {
    "nuovo": ("curator", "writer", "reviewer", "verificatore"),
    "aggiornamento": ("writer", "reviewer"),
    "revisione": ("reviewer",),
    "smentita": ("reviewer", "verificatore"),
    "integrazione": ("curator", "writer", "reviewer", "verificatore"),
    "ritiro": ("curator", "writer"),
    "rollback": ("reviewer",),
    "metadati": ("curator",),
}

# --- Transizioni ammesse (§4) ------------------------------------------------
# Il grafo degli stati e' universale; i tipi differiscono negli stadi
# obbligatori, non nel grafo. Nessun salto implicito: una coppia non elencata e'
# una transizione vietata (es. `in-lavorazione -> pubblicata` saltando `fusa`).
TRANSITIONS = frozenset({
    ("proposta", "in-lavorazione"),
    ("proposta", "chiusa"),
    ("proposta", "in-attesa"),
    ("in-lavorazione", "in-attesa"),
    ("in-lavorazione", "pronta-al-merge"),
    ("in-lavorazione", "invalidata"),
    ("in-lavorazione", "chiusa"),
    ("in-attesa", "in-lavorazione"),
    ("in-attesa", "in-quarantena"),
    ("in-attesa", "chiusa"),
    ("pronta-al-merge", "fusa"),
    ("pronta-al-merge", "invalidata"),
    ("pronta-al-merge", "in-attesa"),
    ("fusa", "pubblicata"),
    ("fusa", "invalidata"),
    ("pubblicata", "chiusa"),
    ("pubblicata", "invalidata"),
    ("invalidata", "in-lavorazione"),
    ("invalidata", "chiusa"),
    ("in-quarantena", "in-lavorazione"),
    ("in-quarantena", "chiusa"),
})

# --- Tassonomia degli errori (§9) --------------------------------------------
# Un blocco generico non dice se e quando ritentare. Sei classi, ognuna con un
# comportamento. Il tetto di retry vive nel record di pratica, mai in un prompt.
RETRY_CEILING = {
    "transitorio": 3,                     # ritenta con backoff, soglia bassa
    "tecnico": 2,                         # ritenta dopo la correzione
    "ripetibile-dopo-cambio-esterno": 0,  # non ritentare da solo: aspetta un cambio esterno
    "terminale": 0,                       # chiude la pratica, non ritenta
}
# Classi che sono rientri, non fallimenti: non contano contro il tetto.
RIENTRO_CLASSES = frozenset({"editoriale", "cambiamento-in-corsa"})
ERROR_CLASSES = tuple(RETRY_CEILING) + tuple(sorted(RIENTRO_CLASSES))


def can_transition(frm: str, to: str) -> bool:
    """Vero se `frm -> to` e' una transizione ammessa del ciclo di vita."""
    return (frm, to) in TRANSITIONS


def is_terminal_state(state: str) -> bool:
    return state == "chiusa"


def next_required_stage(ptype: str, completed_stages) -> str | None:
    """Il primo stadio obbligatorio del tipo non ancora completato, in ordine di
    catena. `None` quando il ciclo ha finito gli stadi obbligatori.

    E' il cuore della ripresa (§9): riprendere una pratica interrotta e' guardare
    quali stadi hanno gia' l'artefatto atteso e ripartire dal primo che manca.
    """
    done = set(completed_stages or ())
    for stage in REQUIRED_STAGES.get(ptype, ()):
        if stage not in done:
            return stage
    return None


def retry_ceiling(error_class: str) -> int | None:
    """Il numero massimo di tentativi per una classe di errore.

    `None` per le classi di rientro (editoriale, cambiamento-in-corsa): sono
    rientri guidati dai dati, non fallimenti, e non hanno un tetto perche' non
    contano come tentativi. Le classi note hanno un intero; una classe ignota
    e' trattata come terminale (0), il default prudente.
    """
    if error_class in RIENTRO_CLASSES:
        return None
    return RETRY_CEILING.get(error_class, 0)


def retry_exhausted(error_class: str, attempts: int) -> bool:
    """Vero quando i tentativi hanno superato il tetto della classe: la pratica
    va messa in quarantena (§3). Le classi di rientro non si esauriscono mai."""
    ceiling = retry_ceiling(error_class)
    if ceiling is None:
        return False
    return attempts >= ceiling


def _days_between(start: str, end: str) -> int:
    """Giorni fra due date `YYYY-MM-DD`, 0 se una manca o non e' leggibile.

    Aritmetica di calendario senza `datetime.now`, cosi' la funzione resta pura
    e il test deterministico: entrambe le date arrivano dal chiamante.
    """
    from datetime import date

    def _parse(value):
        try:
            y, m, d = (int(x) for x in str(value)[:10].split("-"))
            return date(y, m, d)
        except (ValueError, TypeError):
            return None

    a, b = _parse(start), _parse(end)
    if a is None or b is None:
        return 0
    return (b - a).days


def priority_score(practice: dict, today: str) -> float:
    """Il punteggio di priorita' di una pratica (§11), non dello stadio.

    L'ordine di catena da solo e' insufficiente: una correzione urgente di un
    dato pubblicato non deve aspettare dietro una coda di candidature nuove. Il
    punteggio e' derivato da campi verificabili del record, mai da un giudizio,
    e lo consulta il lanciatore a parita' di stadio pronto. Piu' alto = prima.

    I fattori, in ordine di peso:
      - errore pubblico (una smentita su una pagina online): massimo;
      - prossimita' alla pubblicazione: un ciclo quasi concluso vale piu' di uno
        appena nato, perche' chiude lavoro invece di aprirne;
      - dati scaduti su un indicatore nel punteggio;
      - anzianita' della pratica, per evitare la fame di una classe;
      - tentativi gia' falliti, che abbassano, per non monopolizzare la coda.
    """
    flags = practice.get("flags") or {}
    score = 0.0

    if flags.get("open_smentita") and practice.get("state") in ("fusa", "pubblicata", "invalidata"):
        score += 100.0

    ptype = practice.get("type", "nuovo")
    required = practice.get("required_stages") or REQUIRED_STAGES.get(ptype, ())
    if required:
        done = len(set(practice.get("completed_stages") or ()) & set(required))
        score += 20.0 * (done / len(required))

    if flags.get("stale_curation") or flags.get("stale_vintage"):
        if practice.get("score_eligible"):
            score += 15.0
        else:
            score += 8.0

    age = _days_between(practice.get("entered_at", ""), today)
    score += min(max(age, 0), 60) * 0.25   # fino a 15 punti a 60 giorni

    score -= 5.0 * int(practice.get("attempts", 0) or 0)

    return round(score, 3)


def practice_id(indicator_id: str, ptype: str, seq: int) -> str:
    """La chiave di una pratica: `<indicator_id>#<tipo>-<seq>`.

    Lega i tre livelli senza confonderli: l'indicatore ancora l'identita'
    permanente, il tipo dice che genere di ciclo e', la sequenza lo ordina nella
    storia dell'indicatore (§1).
    """
    if ptype not in PRACTICE_TYPES:
        raise ValueError(f"tipo di pratica sconosciuto: {ptype!r}")
    return f"{indicator_id}#{ptype}-{int(seq)}"


def parse_practice_id(pid: str):
    """`(indicator_id, tipo, seq)` da una chiave di pratica. L'inverso di
    `practice_id`. L'indicatore puo' contenere trattini (`bes:09PAE009-N25`),
    quindi lo split parte da destra su `#` e poi sull'ultimo `-`."""
    indicator, _, rest = pid.rpartition("#")
    if not indicator or "-" not in rest:
        raise ValueError(f"chiave di pratica malformata: {pid!r}")
    ptype, _, seq = rest.rpartition("-")
    return indicator, ptype, int(seq)
