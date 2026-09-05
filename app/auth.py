"""Verifica del Bearer JWT di Supabase, lato server.

Supabase Auth (GoTrue) firma un JWT che il browser allega come
`Authorization: Bearer <token>`. Qui lo si verifica e se ne estrae identità
(`id` = UUID utente, `email`). Il backend Flask resta l'unica autorità sui dati
di gioco: l'anti-cheat della classifica non cambia, il JWT aggiunge solo
l'identità durevole a cui attribuire un punteggio.

Tutto è opzionale e degrada a "anonimo": senza materiale di verifica configurato
(`SUPABASE_JWT_SECRET` per HS256, o `SUPABASE_URL` per JWKS), `current_user()`
torna `None` e il gioco resta esattamente com'era. Così il codice si può
rilasciare prima che Supabase sia provisionato.
"""

import threading

import jwt

from app import config

_jwks_client = None
_jwks_lock = threading.Lock()

# Supabase mette gli utenti loggati nel ruolo/audience `authenticated`.
_AUDIENCE = "authenticated"


def _get_jwks_client():
    """Client JWKS in cache (chiavi asimmetriche). Usato solo se non c'è un
    segreto HS256. L'endpoint è quello standard di GoTrue."""
    global _jwks_client
    if _jwks_client is None:
        with _jwks_lock:
            if _jwks_client is None:
                url = config.SUPABASE_URL.rstrip("/") + "/auth/v1/.well-known/jwks.json"
                _jwks_client = jwt.PyJWKClient(url)
    return _jwks_client


def _bearer_token(headers):
    raw = headers.get("Authorization", "")
    if not raw.startswith("Bearer "):
        return None
    token = raw[len("Bearer "):].strip()
    return token or None


def verify_token(token):
    """Verifica firma, scadenza e audience. Torna i claim, o `None` se il token
    è assente, scaduto, manomesso, o se la verifica non è configurata."""
    if not token:
        return None
    try:
        if config.SUPABASE_JWT_SECRET:
            return jwt.decode(
                token, config.SUPABASE_JWT_SECRET, algorithms=["HS256"],
                audience=_AUDIENCE,
                options={"require": ["exp", "sub"]})
        if config.SUPABASE_URL:
            signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
            return jwt.decode(
                token, signing_key.key, algorithms=["ES256", "RS256"],
                audience=_AUDIENCE,
                options={"require": ["exp", "sub"]})
    except jwt.InvalidTokenError:
        return None
    except Exception:  # noqa: BLE001  (rete JWKS giù, chiave assente: mai un 500)
        return None
    return None


def current_user(headers):
    """L'utente autenticato per questa richiesta, o `None`.

    `{"id": <uuid>, "email": <str|"">}`. Non solleva mai: un token cattivo è
    semplicemente un anonimo."""
    claims = verify_token(_bearer_token(headers))
    if not claims:
        return None
    return {"id": claims.get("sub", ""), "email": (claims.get("email") or "").lower()}

