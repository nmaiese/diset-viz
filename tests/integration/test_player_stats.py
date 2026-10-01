"""Statistiche account + achievements (Fase 5.2).

Solo con login: le stats server non esistono per gli anonimi. Verifica gli
aggregati (best=max, contatori=somma), la streak giornaliera, la valutazione
idempotente degli achievement, e il merge locale->account."""

import json
import shutil
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import jwt

from app import achievements, app, config, game_daily, player_stats
from app.db import session_scope
from app.models import DailyResult, DailyScore

_CASI_SERIE = Path(__file__).resolve().parents[1] / "fixtures" / "play_streak_cases.json"

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


class RigheStoricheNonIsoTest(StatsBase):
    """R1 punto 11: su `master` `daily_results` ha ricevuto il puzzle_id intero
    (`daily:2026-...`, `practice-...`). Una riga cosi' non deve bloccare i traguardi."""

    def _riga_storica(self, auth_id, puzzle_date="daily:2026-09-20", solved=0):
        with session_scope() as s:
            s.add(DailyResult(auth_id=auth_id, puzzle_date=puzzle_date, attempts=6, solved=solved))

    def test_i_traguardi_si_sbloccano_anche_con_una_riga_storica_non_iso(self):
        self._riga_storica("u-storico")
        player_stats.record_quiz_answer("u-storico", "compare", True, 1)
        ids = [a["id"] for a in achievements.evaluate("u-storico")]
        self.assertIn("first_correct", ids)

    def test_daily_streaks_ignora_le_date_non_iso(self):
        oggi = date(2026, 10, 10)
        self.assertEqual(
            player_stats._daily_streaks(["daily:2026-10-09", "practice-1", "2026-10-09", "2026-10-10"], today=oggi),
            (2, 2))
        self.assertEqual(player_stats._daily_streaks(["daily:2026-10-09"], today=oggi), (0, 0))

    def test_stats_map_non_solleva_con_una_vittoria_non_iso(self):
        self._riga_storica("u-storico2", "practice-7", solved=1)
        self.assertEqual(player_stats.stats_map("u-storico2")["daily"]["max_daily_streak"], 0)


class PlayStreakTest(StatsBase):
    """La definizione unica di serie: giorni giocati di fila, con un giorno di riposo
    automatico al massimo una volta ogni 7 giorni. I vettori stanno in
    tests/fixtures/play_streak_cases.json: il frontend li legge con la stessa funzione in JS."""

    def test_i_vettori_di_prova(self):
        casi = json.loads(_CASI_SERIE.read_text(encoding="utf-8"))["cases"]
        self.assertGreaterEqual(len(casi), 10)
        for caso in casi:
            with self.subTest(caso["name"]):
                esito = player_stats.play_streak(caso["dates"], today=date.fromisoformat(caso["today"]))
                self.assertEqual(esito, {"current": caso["current"], "max": caso["max"]})

    def test_la_serie_di_gioco_si_legge_da_daily_results_e_daily_scores(self):
        oggi = game_daily.today_rome()
        with session_scope() as s:
            s.add(DailyResult(auth_id="u-gioco", puzzle_date=oggi.isoformat(), attempts=3, solved=0))
            s.add(DailyScore(auth_id="u-gioco", gioco="order", data=(oggi - timedelta(days=1)).isoformat(),
                             punteggio=2, created_at="2026-09-30T08:00:00Z"))
            s.add(DailyScore(auth_id="u-gioco", gioco="compare", data=(oggi - timedelta(days=2)).isoformat(),
                             punteggio=2, created_at="2026-09-30T08:00:00Z"))
        self.assertEqual(player_stats.play_streak_for("u-gioco"), {"current": 3, "max": 3})

    def test_player_me_espone_play_streak_e_tiene_il_resto(self):
        c = app.test_client()
        h = {"Authorization": "Bearer " + _token("u-me-streak")}
        player_stats.record_daily("u-me-streak", game_daily.today_rome().isoformat(), 2, True)
        stats = c.get("/api/player/me", headers=h).get_json()["stats"]
        self.assertEqual(stats["play_streak"], {"current": 1, "max": 1})
        self.assertEqual(stats["daily"]["current_daily_streak"], 1)
        self.assertIn("compare", stats)


class ProgressoTraguardiTest(StatsBase):
    """Ogni traguardo con una soglia dice a che punto e' chi lo insegue: {value, target}."""

    SOGLIE = {"compare_10": 10, "compare_25": 25, "order_10": 10, "daily_streak_7": 7, "veteran_50": 50, "fedele": 30}

    def _lista(self, auth_id):
        return {a["id"]: a for a in achievements.list_for(auth_id)}

    def test_i_traguardi_a_soglia_portano_il_progresso(self):
        lista = self._lista("u-prog")
        for aid, soglia in self.SOGLIE.items():
            with self.subTest(aid):
                self.assertEqual(lista[aid]["progress"], {"value": 0, "target": soglia})
        for aid in ("first_correct", "geografo", "giro_ditalia"):
            self.assertNotIn("progress", lista[aid])

    def test_il_valore_segue_le_statistiche_e_non_supera_la_soglia(self):
        player_stats.record_quiz_answer("u-prog2", "compare", True, 12)
        player_stats.record_quiz_answer("u-prog2", "order", True, 4)
        oggi = game_daily.today_rome()
        for i in range(3):
            player_stats.record_daily("u-prog2", (oggi - timedelta(days=i)).isoformat(), 1, True)
        lista = self._lista("u-prog2")
        self.assertEqual(lista["compare_10"]["progress"], {"value": 10, "target": 10})
        self.assertEqual(lista["compare_25"]["progress"], {"value": 12, "target": 25})
        self.assertEqual(lista["order_10"]["progress"], {"value": 4, "target": 10})
        self.assertEqual(lista["daily_streak_7"]["progress"], {"value": 3, "target": 7})
        self.assertEqual(lista["veteran_50"]["progress"], {"value": 5, "target": 50})
        self.assertEqual(lista["fedele"]["progress"], {"value": 3, "target": 30})

    def test_il_testo_di_daily_streak_7_dice_che_conta_solo_indovina(self):
        lista = self._lista("u-prog3")
        self.assertEqual(lista["daily_streak_7"]["description"], "7 giorni di fila con la Regione del giorno risolta")


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
