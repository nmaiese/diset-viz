"""Token di sessione firmati per il quiz "Chi è maggiore?" e "Ordina le
regioni": tracciano streak/record senza alcuno stato lato server.

Il client passa avanti e indietro un token opaco firmato con HMAC
(app.secret_key), quindi non falsificabile senza la chiave. Ogni round
scelto dal server lega il token a un'impronta (fingerprint) dell'indicatore
e delle regioni coinvolte: lo streak avanza solo rispondendo davvero al
round proposto dal server, non a uno costruito lato client. La valutazione
della risposta (giusto/sbagliato) resta interamente in app.quiz, che è
l'unica fonte di verità: questo modulo si limita a contare le serie.

apply_answer è una funzione pura di (stato_decodificato, campi_inviati). Un
round si risponde una volta sola: `claim_round` segna la coppia (sid, q) in
`quiz_answered` e la seconda risposta allo stesso round e' rifiutata dalla vista
(409), quindi il token da solo non basta a "pompare" lo streak con dei replay.

Versione 2 del token: oltre alla serie porta `iat` (quando il server ha emesso il
round), `n` (nonce del round), `t` (timer attivo sì/no, deciso all'apertura della
sessione) e `st` (quando la sessione e' nata). Il tempo lo misura il server, mai
il client. Un token di un'altra versione apre una sessione nuova.
"""

import hashlib
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone

from itsdangerous import BadData, URLSafeTimedSerializer
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from app import app
from app.db import session_scope
from app.models import QuizAnswered

log = logging.getLogger(__name__)

_SALT = "quiz-session"
_MAX_AGE_S = 12 * 3600
_VERSION = 2
_REQUIRED_KEYS = {"v", "m", "sid", "s", "b", "r", "c", "q", "fp", "x", "iat", "n", "t", "st"}

# Il round di "Chi e' maggiore?" dura 10 s (ROUND_MS in frontend/src/game/compare.jsx):
# il server concede 2 s per la rete e oltre questo la risposta e' un errore.
ROUND_TIME_S = 10
ROUND_TOLERANCE_S = 2
# Sotto questo tempo medio per round una sessione non e' umana: vedi views.py.
MIN_ROUND_TIME_S = 1.5


def _now():
    return time.time()


def _serializer():
    return URLSafeTimedSerializer(app.secret_key, salt=_SALT)


def _fingerprint(mode, session_id, seq, indicator_id, year, region_keys, extra, nonce=""):
    parts = "|".join([
        mode,
        session_id,
        str(seq),
        str(nonce),
        str(indicator_id),
        str(year),
        ",".join(sorted(region_keys)),
        str(extra),
    ])
    return hashlib.sha256(parts.encode("utf-8")).hexdigest()[:16]


def new_state(mode, timer=True):
    """Sessione nuova. `timer` decide per tutta la sessione se il tempo dei round
    e' controllato: una sessione senza timer e' allenamento e non va in classifica."""
    return {
        "v": _VERSION, "m": mode, "sid": secrets.token_hex(8),
        "s": 0, "b": 0, "r": 0, "c": None, "q": 0, "fp": None, "x": None,
        "iat": None, "n": None, "t": bool(timer), "st": _now(),
    }


def _decode(token, mode):
    """Lo stato firmato di un token di questa modalità, o None se manca, è
    scaduto, manomesso, di un'altra versione o di un'altra modalità."""
    if not token or not isinstance(token, str):
        return None
    try:
        data = _serializer().loads(token, max_age=_MAX_AGE_S)
    except BadData:
        return None
    if not isinstance(data, dict) or not _REQUIRED_KEYS.issubset(data.keys()):
        return None
    if data.get("v") != _VERSION or data.get("m") != mode:
        return None
    return data


def load_state(token, mode, timer=True):
    """Decodifica un token del client, o apre una sessione nuova se manca,
    è scaduto, manomesso, di un'altra versione o di un'altra modalità. `timer`
    conta solo quando la sessione si apre: un token valido porta il suo."""
    data = _decode(token, mode)
    return data if data is not None else new_state(mode, timer)


def signed_sid(token, mode):
    """Il `sid` di un token valido di questa modalità, o None. Serve al limite di
    frequenza per sessione: un token non valido non deve creare un secchio con un
    `sid` casuale (ogni richiesta una chiave nuova in cache)."""
    data = _decode(token, mode)
    return None if data is None else data["sid"]


def peek_state(token):
    """Decodifica un token senza conoscere in anticipo la modalità: usato
    dall'endpoint di submit della classifica, dove modalità, session_id e
    punteggio derivano solo dal token (il client non manda mai un
    punteggio). None se il token manca, è scaduto, manomesso o corrotto."""
    if not token or not isinstance(token, str):
        return None
    try:
        data = _serializer().loads(token, max_age=_MAX_AGE_S)
    except BadData:
        return None
    if not isinstance(data, dict) or not _REQUIRED_KEYS.issubset(data.keys()):
        return None
    if data.get("v") != _VERSION or data.get("m") not in ("compare", "order"):
        return None
    return data


def sign_state(state):
    return _serializer().dumps(state)


def bind_round(state, indicator_id, year, region_keys, extra, count=None):
    """Lega il token al round appena scelto dal server. Ritorna il nuovo
    token da restituire nel payload del round (nessuno stato server)."""
    next_seq = state["q"] + 1
    nonce = secrets.token_hex(4)
    fp = _fingerprint(state["m"], state["sid"], next_seq, indicator_id, year, region_keys, extra, nonce)
    next_state = {
        **state,
        "q": next_seq,
        "fp": fp,
        "x": extra,
        "iat": _now(),
        "n": nonce,
        "c": count if count is not None else state.get("c"),
    }
    return sign_state(next_state)


def close_open_round(state):
    """Un nuovo round chiesto mentre ce n'e' uno ancora aperto conta quello aperto
    come sbagliato: la serie riparte da zero e il round `(sid, q)` si segna come
    risposto, cosi' non si puo' rispondere dopo. Senza, chi non gradisce una domanda
    ne chiederebbe un'altra a costo zero (reroll). Con un round non aperto (`fp` nullo:
    sessione nuova o risposta gia' data) non cambia niente."""
    if state.get("fp") is None:
        return state
    claim_round(state["sid"], state["q"])
    return {**state, "s": 0, "r": state["r"] + 1, "fp": None, "x": None, "iat": None, "n": None}


def open_round(state):
    """Lo stato da cui emettere il prossimo round a serie (`/round`). Due casi sono un
    reroll e azzerano la serie: un round ancora aperto (`close_open_round`) e un
    secondo round chiesto con lo stesso token gia' risposto. Il secondo caso prima
    passava: il token tornato da una risposta (`fp` nullo), mandato a `/round` piu'
    volte, dava ogni volta una domanda nuova con la serie intatta. Ora l'emissione del
    round `q + 1` si segna come `(sid, -(q + 1))`, la stessa forma di "Avanti" nella
    sfida del giorno, e dalla seconda in poi la serie riparte da zero. Il primo round
    emesso resta rispondibile: chi cambia domanda non tiene la serie, e basta. Senza
    il DB `claim_round` fallisce aperto e il controllo non c'e'."""
    state = close_open_round(state)
    if not claim_round(state["sid"], -(state["q"] + 1)):
        state = {**state, "s": 0}
    return state


def apply_answer(state, indicator_id, year, region_keys, correct):
    """Valida che la risposta corrisponda al round legato dal fingerprint,
    poi aggiorna streak/record/round giocati. Ritorna (session, token) o
    (None, None) se il token è assente, manomesso o non lega a questa
    risposta (il gioco resta comunque giocabile, solo senza classifica)."""
    if state.get("fp") is None:
        return None, None
    # Le chiavi arrivano dal corpo della richiesta: una che non e' una stringa non
    # lega niente (e non deve far cadere l'ordinamento dell'impronta).
    if not all(isinstance(k, str) for k in region_keys):
        return None, None
    expected = _fingerprint(state["m"], state["sid"], state["q"], indicator_id, year, region_keys,
                            state.get("x"), state.get("n"))
    if expected != state["fp"]:
        return None, None
    next_streak = state["s"] + 1 if correct else 0
    next_best = max(state["b"], next_streak)
    next_state = {**state, "s": next_streak, "b": next_best, "r": state["r"] + 1,
                  "fp": None, "x": None, "iat": None, "n": None}
    token = sign_state(next_state)
    session = {
        "session_id": next_state["sid"],
        "streak": next_streak,
        "best": next_best,
        "rounds": next_state["r"],
        "count": next_state.get("c"),
    }
    return session, token


def session_summary(session):
    """La parte della sessione che il client vede (mai `sid` ne' `count`), o None
    se il round non era legato."""
    if session is None:
        return None
    return {"streak": session["streak"], "best": session["best"], "rounds": session["rounds"]}


def round_timing(state, choice, now=None):
    """Com'e' andata la risposta rispetto al tempo del round, misurato dal server:
    "ok", "late" (oltre 10 s piu' 2 di tolleranza: e' un errore) o "early_timeout"
    (un `timeout` arrivato prima dei 10 s non vale). Senza timer attivo o senza un
    round emesso, niente controllo."""
    if not state.get("t") or state.get("iat") is None:
        return "ok"
    elapsed = (now if now is not None else _now()) - state["iat"]
    if elapsed > ROUND_TIME_S + ROUND_TOLERANCE_S:
        return "late"
    if choice == "timeout" and elapsed < ROUND_TIME_S:
        return "early_timeout"
    return "ok"


def is_plausible(state, now=None):
    """Una sessione da `r` round non puo' essere durata meno di r x 1,5 s dalla
    prima apertura: sotto, e' uno script e non una persona."""
    elapsed = (now if now is not None else _now()) - state["st"]
    return state["r"] * MIN_ROUND_TIME_S <= elapsed


def claim_round(sid, q):
    """Segna il round (sid, q) come risposto. False se c'era gia': il chiamante
    risponde 409. Nel DB e non in cache, perche' le istanze Cloud Run sono piu' di
    una. Se il DB non risponde il gioco resta giocabile (True), e l'errore va nel log."""
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    cutoff = (now - timedelta(seconds=_MAX_AGE_S)).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        with session_scope() as s:
            s.execute(delete(QuizAnswered).where(QuizAnswered.answered_at < cutoff))
            s.add(QuizAnswered(sid=sid, q=int(q), answered_at=stamp))
        return True
    except IntegrityError:
        return False
    except Exception:  # noqa: BLE001
        log.exception("quiz_answered: round %s/%s non registrato", sid, q)
        return True
