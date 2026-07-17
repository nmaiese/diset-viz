"""Token di sessione firmati per il quiz "Chi è maggiore?" e "Ordina le
regioni": tracciano streak/record senza alcuno stato lato server.

Il client passa avanti e indietro un token opaco firmato con HMAC
(app.secret_key), quindi non falsificabile senza la chiave. Ogni round
scelto dal server lega il token a un'impronta (fingerprint) dell'indicatore
e delle regioni coinvolte: lo streak avanza solo rispondendo davvero al
round proposto dal server, non a uno costruito lato client. La valutazione
della risposta (giusto/sbagliato) resta interamente in app.quiz, che è
l'unica fonte di verità: questo modulo si limita a contare le serie.

apply_answer è una funzione pura di (stato_decodificato, campi_inviati):
inviare due volte la stessa risposta con lo stesso token produce sempre lo
stesso risultato (nessun modo di "pompare" lo streak con dei replay).
"""

import hashlib
import secrets

from itsdangerous import BadData, URLSafeTimedSerializer

from app import app

_SALT = "quiz-session"
_MAX_AGE_S = 12 * 3600
_REQUIRED_KEYS = {"v", "m", "sid", "s", "b", "r", "c", "q", "fp", "x"}


def _serializer():
    return URLSafeTimedSerializer(app.secret_key, salt=_SALT)


def _fingerprint(mode, session_id, seq, indicator_id, year, region_keys, extra):
    parts = "|".join([
        mode,
        session_id,
        str(seq),
        str(indicator_id),
        str(year),
        ",".join(sorted(region_keys)),
        str(extra),
    ])
    return hashlib.sha256(parts.encode("utf-8")).hexdigest()[:16]


def new_state(mode):
    return {
        "v": 1, "m": mode, "sid": secrets.token_hex(8),
        "s": 0, "b": 0, "r": 0, "c": None, "q": 0, "fp": None, "x": None,
    }


def load_state(token, mode):
    """Decodifica un token del client, o apre una sessione nuova se manca,
    è scaduto, manomesso o appartiene a un'altra modalità."""
    if not token or not isinstance(token, str):
        return new_state(mode)
    try:
        data = _serializer().loads(token, max_age=_MAX_AGE_S)
    except BadData:
        return new_state(mode)
    if not isinstance(data, dict) or not _REQUIRED_KEYS.issubset(data.keys()):
        return new_state(mode)
    if data.get("v") != 1 or data.get("m") != mode:
        return new_state(mode)
    return data


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
    if data.get("v") != 1 or data.get("m") not in ("compare", "order"):
        return None
    return data


def sign_state(state):
    return _serializer().dumps(state)


def bind_round(state, indicator_id, year, region_keys, extra, count=None):
    """Lega il token al round appena scelto dal server. Ritorna il nuovo
    token da restituire nel payload del round (nessuno stato server)."""
    next_seq = state["q"] + 1
    fp = _fingerprint(state["m"], state["sid"], next_seq, indicator_id, year, region_keys, extra)
    next_state = {
        **state,
        "q": next_seq,
        "fp": fp,
        "x": extra,
        "c": count if count is not None else state.get("c"),
    }
    return sign_state(next_state)


def apply_answer(state, indicator_id, year, region_keys, correct):
    """Valida che la risposta corrisponda al round legato dal fingerprint,
    poi aggiorna streak/record/round giocati. Ritorna (session, token) o
    (None, None) se il token è assente, manomesso o non lega a questa
    risposta (il gioco resta comunque giocabile, solo senza classifica)."""
    if state.get("fp") is None:
        return None, None
    expected = _fingerprint(state["m"], state["sid"], state["q"], indicator_id, year, region_keys, state.get("x"))
    if expected != state["fp"]:
        return None, None
    next_streak = state["s"] + 1 if correct else 0
    next_best = max(state["b"], next_streak)
    next_state = {**state, "s": next_streak, "b": next_best, "r": state["r"] + 1, "fp": None, "x": None}
    token = sign_state(next_state)
    session = {
        "session_id": next_state["sid"],
        "streak": next_streak,
        "best": next_best,
        "rounds": next_state["r"],
        "count": next_state.get("c"),
    }
    return session, token
