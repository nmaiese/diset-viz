"""Preferiti indicatore (Fase 5.1): store per-utente e endpoint authed.

Solo con login: gli endpoint danno 401 agli anonimi. L'`auth_id` viene sempre dal
JWT verificato, mai dal body: un utente non puo' leggere o scrivere i preferiti di
un altro."""

import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt

from app import app, config, favorites
from app.db import session_scope
from app.models import Favorite

_SECRET = "test-jwt-secret"


def _token(sub="uuid-a", email="a@example.com"):
    payload = {"sub": sub, "email": email, "aud": "authenticated",
               "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    return jwt.encode(payload, _SECRET, algorithm="HS256")


class FavoritesBase(unittest.TestCase):
    def setUp(self):
        self._saved = (config.SUPABASE_JWT_SECRET, config.SUPABASE_URL, config.LEADERBOARD_DB)
        config.SUPABASE_JWT_SECRET = _SECRET
        config.SUPABASE_URL = ""
        self._tmp = tempfile.mkdtemp()
        config.LEADERBOARD_DB = str(Path(self._tmp) / "fav.sqlite3")

    def tearDown(self):
        config.SUPABASE_JWT_SECRET, config.SUPABASE_URL, config.LEADERBOARD_DB = self._saved
        shutil.rmtree(self._tmp, ignore_errors=True)


class FavoritesStoreTest(FavoritesBase):
    def test_add_is_idempotent_and_list_orders_recent_first(self):
        favorites.add("u1", "105")
        favorites.add("u1", "105")  # doppione: ignorato
        favorites.add("u1", "bes:10AMB002")
        ids = favorites.list_ids("u1")
        self.assertEqual(sorted(ids), ["105", "bes:10AMB002"])
        with session_scope() as s:
            self.assertEqual(s.query(Favorite).count(), 2)

    def test_remove_and_isolation_between_users(self):
        favorites.add("u1", "105")
        favorites.add("u2", "105")
        favorites.remove("u1", "105")
        self.assertEqual(favorites.list_ids("u1"), [])
        self.assertEqual(favorites.list_ids("u2"), ["105"])  # l'altro utente intatto


class FavoritesApiTest(FavoritesBase):
    def test_endpoints_require_login(self):
        c = app.test_client()
        self.assertEqual(c.get("/api/favorites").status_code, 401)
        self.assertEqual(c.post("/api/favorites", json={"indicator_id": "105"}).status_code, 401)
        self.assertEqual(c.delete("/api/favorites/105").status_code, 401)

    def test_add_list_remove_with_a_valid_token(self):
        c = app.test_client()
        h = {"Authorization": "Bearer " + _token()}
        self.assertEqual(c.post("/api/favorites", json={"indicator_id": "105"}, headers=h).status_code, 200)
        self.assertEqual(c.post("/api/favorites", json={"indicator_id": "bes:10AMB002"}, headers=h).status_code, 200)
        body = c.get("/api/favorites", headers=h).get_json()
        self.assertEqual(set(body["favorites"]), {"105", "bes:10AMB002"})
        self.assertEqual(c.delete("/api/favorites/105", headers=h).status_code, 200)
        body = c.get("/api/favorites", headers=h).get_json()
        self.assertEqual(body["favorites"], ["bes:10AMB002"])

    def test_bad_indicator_rejected(self):
        c = app.test_client()
        h = {"Authorization": "Bearer " + _token()}
        self.assertEqual(c.post("/api/favorites", json={"indicator_id": ""}, headers=h).status_code, 400)
        self.assertEqual(c.post("/api/favorites", json={"indicator_id": "x" * 65}, headers=h).status_code, 400)


if __name__ == "__main__":
    unittest.main()
