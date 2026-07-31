"""Verifica del Bearer JWT Supabase e attribuzione opzionale dello user_id.

Auth degrada ad anonimo per default: senza materiale di verifica configurato, un
token e' semplicemente ignorato e il gioco resta com'era. Qui si prova che un
token valido diventa identita', uno scaduto/manomesso no, e che un punteggio
inviato con un JWT valido si lega all'account."""

import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt

from app import app, auth, config, leaderboard
from app.db import session_scope
from app.models import Score

_SECRET = "test-jwt-secret"


def _token(sub="uuid-abc", email="player@example.com", exp_delta=3600, aud="authenticated"):
    payload = {"sub": sub, "email": email, "aud": aud,
               "exp": datetime.now(timezone.utc) + timedelta(seconds=exp_delta)}
    return jwt.encode(payload, _SECRET, algorithm="HS256")


class AuthTokenTest(unittest.TestCase):
    def setUp(self):
        self._saved = (config.SUPABASE_JWT_SECRET, config.SUPABASE_URL)
        config.SUPABASE_JWT_SECRET = _SECRET
        config.SUPABASE_URL = ""

    def tearDown(self):
        config.SUPABASE_JWT_SECRET, config.SUPABASE_URL = self._saved

    def test_a_valid_token_becomes_identity(self):
        user = auth.current_user({"Authorization": "Bearer " + _token()})
        self.assertEqual(user, {"id": "uuid-abc", "email": "player@example.com"})

    def test_email_is_lowercased(self):
        user = auth.current_user({"Authorization": "Bearer " + _token(email="MixedCase@Example.com")})
        self.assertEqual(user["email"], "mixedcase@example.com")

    def test_no_header_is_anonymous(self):
        self.assertIsNone(auth.current_user({}))

    def test_tampered_token_is_anonymous(self):
        bad = _token()[:-2] + "zz"
        self.assertIsNone(auth.current_user({"Authorization": "Bearer " + bad}))

    def test_expired_token_is_anonymous(self):
        self.assertIsNone(auth.current_user({"Authorization": "Bearer " + _token(exp_delta=-10)}))

    def test_wrong_audience_is_anonymous(self):
        self.assertIsNone(auth.current_user({"Authorization": "Bearer " + _token(aud="anon")}))

    def test_auth_off_ignores_even_a_valid_token(self):
        config.SUPABASE_JWT_SECRET = ""
        config.SUPABASE_URL = ""
        self.assertIsNone(auth.current_user({"Authorization": "Bearer " + _token()}))

    def test_is_admin_matches_only_the_allowlisted_email(self):
        saved = config.MONITOR_ADMIN_EMAIL
        config.MONITOR_ADMIN_EMAIL = "boss@example.com"
        try:
            self.assertTrue(auth.is_admin({"id": "1", "email": "boss@example.com"}))
            self.assertFalse(auth.is_admin({"id": "2", "email": "other@example.com"}))
            self.assertFalse(auth.is_admin(None))
        finally:
            config.MONITOR_ADMIN_EMAIL = saved


class AuthMeRouteTest(unittest.TestCase):
    def setUp(self):
        self._saved = (config.SUPABASE_JWT_SECRET, config.SUPABASE_URL, config.LEADERBOARD_DB)
        config.SUPABASE_JWT_SECRET = _SECRET
        config.SUPABASE_URL = ""
        # /api/auth/me fa upsert del profilo: DB temporaneo, non lo sqlite di dev.
        self._tmp = tempfile.mkdtemp()
        config.LEADERBOARD_DB = str(Path(self._tmp) / "auth.sqlite3")

    def tearDown(self):
        config.SUPABASE_JWT_SECRET, config.SUPABASE_URL, config.LEADERBOARD_DB = self._saved
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_me_is_anonymous_without_a_token(self):
        body = app.test_client().get("/api/auth/me").get_json()
        self.assertEqual(body, {"user": None, "profile": None})

    def test_me_reflects_a_valid_token_and_upserts_profile(self):
        body = app.test_client().get(
            "/api/auth/me", headers={"Authorization": "Bearer " + _token()}).get_json()
        self.assertEqual(body["user"], {"id": "uuid-abc", "email": "player@example.com"})
        # il profilo e' stato creato e torna nella risposta
        self.assertEqual(body["profile"]["auth_id"], "uuid-abc")
        self.assertEqual(body["profile"]["email"], "player@example.com")


class ScoreUserIdTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._saved = config.LEADERBOARD_DB
        config.LEADERBOARD_DB = str(Path(self._tmp) / "lb.sqlite3")

    def tearDown(self):
        config.LEADERBOARD_DB = self._saved
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_user_id_is_stored_when_present_and_null_when_anonymous(self):
        leaderboard.submit("compare", "sid-auth", "Anna", 5, {}, user_id="uuid-1")
        leaderboard.submit("compare", "sid-anon", "Bo", 4, {})
        with session_scope() as s:
            by_sid = {r.session_id: r.user_id for r in s.query(Score).all()}
        self.assertEqual(by_sid["sid-auth"], "uuid-1")
        self.assertIsNone(by_sid["sid-anon"])


if __name__ == "__main__":
    unittest.main()
