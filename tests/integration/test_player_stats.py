"""Statistiche account + achievements (Fase 5.2).

Solo con login: le stats server non esistono per gli anonimi. Verifica gli
aggregati (best=max, contatori=somma), la streak giornaliera, la valutazione
idempotente degli achievement, e il merge locale->account."""

import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt

from app import achievements, app, config, player_stats

_SECRET = "test-jwt-secret"


def _token(sub="uuid-a", email="a@example.com"):
    payload = {"sub": sub, "email": email, "aud": "authenticated",
               "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    return jwt.encode(payload, _SECRET, algorithm="HS256")


class StatsBase(unittest.TestCase):
    def setUp(self):
        self._saved = (config.SUPABASE_JWT_SECRET, config.SUPABASE_URL, config.LEADERBOARD_DB)
        config.SUPABASE_JWT_SECRET = _SECRET
        config.SUPABASE_URL = ""
        self._tmp = tempfile.mkdtemp()
        config.LEADERBOARD_DB = str(Path(self._tmp) / "s.sqlite3")

    def tearDown(self):
        config.SUPABASE_JWT_SECRET, config.SUPABASE_URL, config.LEADERBOARD_DB = self._saved
        shutil.rmtree(self._tmp, ignore_errors=True)


class StatsModuleTest(StatsBase):
    def test_quiz_answer_accumulates_and_best_is_max(self):
        player_stats.record_quiz_answer("u1", "compare", True, 3)
        player_stats.record_quiz_answer("u1", "compare", False, 2)  # best non regredisce
        st = player_stats.stats_map("u1")["compare"]
        self.assertEqual(st["rounds_played"], 2)
        self.assertEqual(st["correct"], 1)
        self.assertEqual(st["best_streak"], 3)

    def test_daily_is_idempotent_per_date_and_streak(self):
        self.assertTrue(player_stats.record_daily("u1", "2026-07-20", 2, True))
        self.assertFalse(player_stats.record_daily("u1", "2026-07-20", 1, True))  # stesso giorno
        player_stats.record_daily("u1", "2026-07-21", 3, True)
        st = player_stats.stats_map("u1")["daily"]
        self.assertEqual(st["games_played"], 2)
        self.assertEqual(st["wins"], 2)
        self.assertEqual(st["max_daily_streak"], 2)  # 20 e 21 consecutivi

    def test_merge_local_best_max_counters_sum(self):
        player_stats.record_quiz_answer("u1", "compare", True, 5)  # rounds1 correct1 best5
        player_stats.merge_local("u1", {"compare": {"best_streak": 3, "rounds_played": 10, "correct": 7}})
        st = player_stats.stats_map("u1")["compare"]
        self.assertEqual(st["best_streak"], 5)      # max(5,3)
        self.assertEqual(st["rounds_played"], 11)   # 1 + 10
        self.assertEqual(st["correct"], 8)          # 1 + 7


class AchievementsTest(StatsBase):
    def test_first_correct_unlocks_once(self):
        player_stats.record_quiz_answer("u1", "compare", True, 1)
        got = achievements.evaluate("u1")
        ids = [a["id"] for a in got]
        self.assertIn("first_correct", ids)
        # idempotente: seconda valutazione non ripropone
        self.assertEqual(achievements.evaluate("u1"), [])

    def test_list_for_shows_locked_and_unlocked(self):
        player_stats.record_quiz_answer("u1", "compare", True, 1)
        achievements.evaluate("u1")
        cat = {a["id"]: a["unlocked"] for a in achievements.list_for("u1")}
        self.assertTrue(cat["first_correct"])
        self.assertFalse(cat["veteran_50"])


class PlayerApiTest(StatsBase):
    def test_player_me_requires_login(self):
        self.assertEqual(app.test_client().get("/api/player/me").status_code, 401)

    def test_player_me_and_merge_with_token(self):
        c = app.test_client()
        h = {"Authorization": "Bearer " + _token()}
        body = c.get("/api/player/me", headers=h).get_json()
        self.assertIn("stats", body)
        self.assertIn("achievements", body)
        # merge locale -> account, sblocca first_correct via correct>0
        r = c.post("/api/player/merge", json={"stats": {"compare": {"correct": 1, "rounds_played": 1}}}, headers=h)
        self.assertEqual(r.status_code, 200)
        ids = [a["id"] for a in r.get_json()["achievements"]]
        self.assertIn("first_correct", ids)


if __name__ == "__main__":
    unittest.main()
