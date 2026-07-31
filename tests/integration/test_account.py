"""Pagina account: confronti salvati, nickname, export, cancellazione (Fase 5.3).

Tutto solo con login. La cancellazione elimina le righe (l'utente Supabase non si
tocca in test: SUPABASE_URL vuoto -> supabase_deleted False, rows_deleted True)."""

import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt

from app import account, app, comparisons, config, favorites
from app.db import session_scope
from app.models import Favorite

_SECRET = "test-jwt-secret"


def _token(sub="uuid-a", email="a@example.com"):
    payload = {"sub": sub, "email": email, "aud": "authenticated",
               "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    return jwt.encode(payload, _SECRET, algorithm="HS256")


class AccountBase(unittest.TestCase):
    def setUp(self):
        self._saved = (config.SUPABASE_JWT_SECRET, config.SUPABASE_URL, config.LEADERBOARD_DB)
        config.SUPABASE_JWT_SECRET = _SECRET
        config.SUPABASE_URL = ""
        self._tmp = tempfile.mkdtemp()
        config.LEADERBOARD_DB = str(Path(self._tmp) / "a.sqlite3")

    def tearDown(self):
        config.SUPABASE_JWT_SECRET, config.SUPABASE_URL, config.LEADERBOARD_DB = self._saved
        shutil.rmtree(self._tmp, ignore_errors=True)


class ComparisonsTest(AccountBase):
    def test_requires_login(self):
        c = app.test_client()
        self.assertEqual(c.get("/api/comparisons").status_code, 401)
        self.assertEqual(c.post("/api/comparisons", json={"title": "x"}).status_code, 401)

    def test_save_list_delete(self):
        c = app.test_client()
        h = {"Authorization": "Bearer " + _token()}
        r = c.post("/api/comparisons", json={"title": "Nord vs Sud", "config": {"regions": ["01", "19"]}}, headers=h)
        self.assertEqual(r.status_code, 200)
        cid = r.get_json()["comparison"]["id"]
        items = c.get("/api/comparisons", headers=h).get_json()["comparisons"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Nord vs Sud")
        self.assertEqual(items[0]["config"]["regions"], ["01", "19"])
        self.assertEqual(c.delete(f"/api/comparisons/{cid}", headers=h).status_code, 200)
        self.assertEqual(c.get("/api/comparisons", headers=h).get_json()["comparisons"], [])

    def test_isolation(self):
        comparisons.save("u1", "mine", {})
        comparisons.save("u2", "theirs", {})
        self.assertEqual([x["title"] for x in comparisons.list_for("u1")], ["mine"])


class AccountApiTest(AccountBase):
    def test_nickname_update(self):
        c = app.test_client()
        h = {"Authorization": "Bearer " + _token()}
        c.get("/api/auth/me", headers=h)  # crea il profilo
        r = c.patch("/api/player/nickname", json={"nickname": "Anna"}, headers=h)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["nickname"], "Anna")

    def test_export_and_delete(self):
        c = app.test_client()
        h = {"Authorization": "Bearer " + _token()}
        c.get("/api/auth/me", headers=h)
        favorites.add("uuid-a", "105")
        exp = c.get("/api/account/export", headers=h).get_json()
        self.assertEqual([f["indicator_id"] for f in exp["favorites"]], ["105"])
        # cancellazione: righe via, supabase non toccato in test
        res = c.delete("/api/account", headers=h).get_json()
        self.assertTrue(res["rows_deleted"])
        with session_scope() as s:
            self.assertEqual(s.query(Favorite).filter(Favorite.auth_id == "uuid-a").count(), 0)

    def test_account_page_renders(self):
        self.assertEqual(app.test_client().get("/account").status_code, 200)


if __name__ == "__main__":
    unittest.main()
