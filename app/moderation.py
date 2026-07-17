"""Validazione dei nickname per la classifica del quiz: niente account,
niente email, solo un nome pubblico scelto dal giocatore. Filtro
proporzionato a un gioco casual, non un sistema anti-abuso completo."""

import re
import unicodedata

_MIN_LEN = 2
_MAX_LEN = 16
_VALID_RE = re.compile(r"^[0-9A-Za-zÀ-ÖØ-öø-ÿ _.\-]+$")

# Volgarità e insulti comuni it/en, confrontati sulla forma de-accentata,
# minuscola e senza separatori: basta a filtrare i tentativi più ovvi senza
# pretendere di essere un sistema di moderazione completo.
_BLOCKLIST = {
    "merda", "cazzo", "cazzi", "stronzo", "stronza", "puttana", "troia",
    "vaffanculo", "fanculo", "coglione", "coglioni", "bastardo", "bastarda",
    "porco", "porca", "culo", "negro", "negra", "frocio", "checca",
    "handicappato", "mongoloide", "ritardato", "ritardata",
    "fuck", "shit", "bitch", "asshole", "bastard", "cunt", "nigger", "nigga",
    "faggot", "retard", "whore", "slut", "dick", "pussy", "rape", "nazi",
    "hitler", "admin", "moderator", "moderatore",
}


def _deaccent(value):
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_nickname(raw):
    value = unicodedata.normalize("NFKC", (raw or "").strip())
    return re.sub(r"\s+", " ", value)


def validate_nickname(raw):
    """Ritorna (nickname_normalizzato, None) se valido, altrimenti
    (None, error_code) con error_code in {"nickname_invalid", "nickname_blocked"}."""
    value = normalize_nickname(raw)
    if not (_MIN_LEN <= len(value) <= _MAX_LEN):
        return None, "nickname_invalid"
    if not _VALID_RE.match(value):
        return None, "nickname_invalid"
    stripped = re.sub(r"[ _.\-]", "", _deaccent(value)).lower()
    for word in _BLOCKLIST:
        if word in stripped:
            return None, "nickname_blocked"
    return value, None
