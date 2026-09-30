"""Sicurezza del gioco: vittorie giornaliere, round monouso, timer e difficolta'
decisi dal server, plausibilita' in classifica, path canonico, rate limit.

Ogni test qui sotto fallisce sul codice di prima (rapporto docs/gioco/ricerca,
C-tecnica §1 e §3)."""

import os
import shutil
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import jwt

from app import client_ip, profiles, app, config, game, game_daily, leaderboard, player_stats, quiz, quiz_tokens
from app.cache import cache
from app.db import session_scope
from app.models import DailyResult
from sqlalchemy import select

_SECRET = "test-jwt-secret"


def _jwt(sub="uuid-sic"):
    payload = {"sub": sub, "email": "s@example.com", "aud": "authenticated",
               "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    return jwt.encode(payload, _SECRET, algorithm="HS256")


def _clear_buckets():
    for key in ("rl:lb:127.0.0.1", "rl:ans:ip:127.0.0.1"):
        cache.delete(key)


class Base(unittest.TestCase):
    def setUp(self):
        self._saved = (config.SUPABASE_JWT_SECRET, config.SUPABASE_URL, config.LEADERBOARD_DB)
        config.SUPABASE_JWT_SECRET = _SECRET
        config.SUPABASE_URL = ""
        self._tmp = tempfile.mkdtemp()
        config.LEADERBOARD_DB = str(Path(self._tmp) / "s.sqlite3")
        _clear_buckets()

    def tearDown(self):
        config.SUPABASE_JWT_SECRET, config.SUPABASE_URL, config.LEADERBOARD_DB = self._saved
        shutil.rmtree(self._tmp, ignore_errors=True)
        _clear_buckets()


def _daily_rows(auth_id):
    with session_scope() as s:
        return s.execute(select(DailyResult).where(DailyResult.auth_id == auth_id)).scalars().all()


def _winning_key(puzzle_id):
    return game.build_puzzle(puzzle_id)["region_key"]


class DailyRecordTest(Base):
    def _win(self, client, puzzle_id, headers):
        return client.post("/api/game/guess", headers=headers, json={
            "puzzle_id": puzzle_id, "region_key": _winning_key(puzzle_id), "attempt": 1,
        })

    def test_daily_win_with_jwt_is_saved_and_streak_is_one(self):
        client = app.test_client()
        puzzle_id = f"daily:{game_daily.oggi_roma().isoformat()}"
        response = self._win(client, puzzle_id, {"Authorization": "Bearer " + _jwt()})
        self.assertEqual(response.status_code, 200)
        rows = _daily_rows("uuid-sic")
        self.assertEqual([(r.puzzle_date, r.solved) for r in rows],
                         [(game_daily.oggi_roma().isoformat(), 1)])
        daily = player_stats.stats_map("uuid-sic")["daily"]
        self.assertEqual(daily["current_daily_streak"], 1)
        me = client.get("/api/player/me", headers={"Authorization": "Bearer " + _jwt()}).get_json()
        self.assertEqual(me["stats"]["daily"]["wins"], 1)
        self.assertIn("historic_best_streak", me["stats"]["daily"])

    def test_only_todays_daily_is_recorded_not_practice_nor_archive(self):
        client = app.test_client()
        headers = {"Authorization": "Bearer " + _jwt()}
        today = game_daily.oggi_roma()
        practice_id = game.new_practice_puzzle_id()
        wrong = next(r["region_key"] for r in profiles.all_regions_index()
                     if r["region_key"] != _winning_key(practice_id))
        lost = client.post("/api/game/guess", headers=headers, json={
            "puzzle_id": practice_id, "region_key": wrong, "attempt": game.MAX_ATTEMPTS})
        self.assertTrue(lost.get_json()["finished"])
        yesterday = f"daily:{(today - timedelta(days=1)).isoformat()}"
        self.assertEqual(self._win(client, yesterday, headers).status_code, 200)
        self.assertEqual(_daily_rows("uuid-sic"), [])
        self.assertEqual(self._win(client, f"daily:{today.isoformat()}", headers).status_code, 200)
        self.assertEqual([r.puzzle_date for r in _daily_rows("uuid-sic")], [today.isoformat()])

    def test_record_daily_refuses_non_iso_date(self):
        self.assertFalse(player_stats.record_daily("u1", "daily:2026-07-20", 1, True))
        self.assertEqual(_daily_rows("u1"), [])

    def test_current_streak_is_zero_when_last_win_is_two_days_old(self):
        player_stats.record_daily("u1", "2026-07-19", 1, True)
        player_stats.record_daily("u1", "2026-07-20", 1, True)
        with mock.patch.object(game_daily, "oggi_roma", return_value=date(2026, 7, 22)):
            daily = player_stats.stats_map("u1")["daily"]
        self.assertEqual(daily["current_daily_streak"], 0)
        self.assertEqual(daily["max_daily_streak"], 2)
        with mock.patch.object(game_daily, "oggi_roma", return_value=date(2026, 7, 21)):
            self.assertEqual(player_stats.stats_map("u1")["daily"]["current_daily_streak"], 2)

    def test_historic_streak_stays_apart_from_daily_streak(self):
        player_stats.merge_local("u1", {"daily": {"max_daily_streak": 9}})
        daily = player_stats.stats_map("u1")["daily"]
        self.assertEqual(daily["historic_best_streak"], 9)
        self.assertEqual(daily["max_daily_streak"], 0)


def _compare_body(round_, choice, token=None):
    return {
        "indicator_id": round_["indicator"]["id"], "year": round_["indicator"]["year"],
        "region_a_key": round_["region_a"]["region_key"],
        "region_b_key": round_["region_b"]["region_key"],
        "choice": choice, "token": token or round_["token"],
    }


def _winner(round_):
    values = {r["region_key"]: r["value"] for r in quiz._quiz_indicator_payload(
        round_["indicator"]["id"], round_["indicator"]["year"])["values"]}
    a, b = round_["region_a"]["region_key"], round_["region_b"]["region_key"]
    return "region_a" if values[a] > values[b] else "region_b"


class RoundTest(Base):
    def test_same_round_twice_gives_409(self):
        client = app.test_client()
        round_ = client.get("/api/game/compare/round").get_json()
        body = _compare_body(round_, _winner(round_))
        self.assertEqual(client.post("/api/game/compare/answer", json=body).status_code, 200)
        self.assertEqual(client.post("/api/game/compare/answer", json=body).status_code, 409)

    def test_late_answer_with_timer_is_an_error(self):
        client = app.test_client()
        t0 = 1_800_000_000.0
        with mock.patch.object(quiz_tokens, "_now", return_value=t0):
            round_ = client.get("/api/game/compare/round").get_json()
        with mock.patch.object(quiz_tokens, "_now", return_value=t0 + 15):
            answer = client.post("/api/game/compare/answer",
                                 json=_compare_body(round_, _winner(round_))).get_json()
        self.assertFalse(answer["correct"])
        self.assertEqual(answer["session"]["streak"], 0)

    def test_early_timeout_does_not_count(self):
        client = app.test_client()
        t0 = 1_800_000_000.0
        with mock.patch.object(quiz_tokens, "_now", return_value=t0):
            round_ = client.get("/api/game/compare/round").get_json()
        with mock.patch.object(quiz_tokens, "_now", return_value=t0 + 2):
            response = client.post("/api/game/compare/answer", json=_compare_body(round_, "timeout"))
        self.assertEqual(response.status_code, 400)

    def test_untimed_session_is_not_submittable(self):
        client = app.test_client()
        t0 = 1_800_000_000.0
        with mock.patch.object(quiz_tokens, "_now", return_value=t0):
            round_ = client.get("/api/game/compare/round?timer=0").get_json()
        with mock.patch.object(quiz_tokens, "_now", return_value=t0 + 15):
            answer = client.post("/api/game/compare/answer",
                                 json=_compare_body(round_, _winner(round_))).get_json()
        self.assertTrue(answer["correct"])  # niente controllo del tempo
        with mock.patch.object(quiz_tokens, "_now", return_value=t0 + 3600):
            response = client.post("/api/game/leaderboard",
                                   json={"token": answer["token"], "nickname": "Allenamento"})
        self.assertEqual(response.status_code, 400)

    def test_client_difficulty_is_ignored(self):
        client = app.test_client()
        state = quiz_tokens.new_state("compare")
        state["s"] = 6
        round_ = client.get("/api/game/compare/round?difficulty=0&token="
                            + quiz_tokens.sign_state(state)).get_json()
        self.assertEqual(round_["difficulty"], 2)

    def test_fifteen_instant_rounds_are_rejected_in_leaderboard(self):
        client = app.test_client()
        token = None
        for _ in range(15):
            round_ = client.get("/api/game/compare/round?token=" + (token or "")).get_json()
            token = client.post("/api/game/compare/answer",
                                json=_compare_body(round_, _winner(round_))).get_json()["token"]
        response = client.post("/api/game/leaderboard", json={"token": token, "nickname": "Razzo"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "score_missing")


class ModalitaDelGiornoTest(Base):
    """La sfida del giorno ha modalita' di token proprie (`compare_daily`,
    `order_daily`): il suo token non entra nelle serie ne' nella classifica, e quello
    di una serie non si rilega a un altro puzzle (R1 punti 3 e 14)."""

    def _sessioni(self):
        client = app.test_client()
        compare = client.get("/api/game/compare/daily/session?level=regioni").get_json()
        order = client.get("/api/game/order/daily/session?level=regioni").get_json()
        return client, compare, order

    def test_peek_state_rifiuta_i_token_della_sfida_del_giorno(self):
        _, compare, order = self._sessioni()
        self.assertIsNone(quiz_tokens.peek_state(compare["token"]))
        self.assertIsNone(quiz_tokens.peek_state(order["token"]))

    def test_la_classifica_a_serie_rifiuta_i_token_della_sfida_del_giorno(self):
        client, compare, order = self._sessioni()
        for token in (compare["token"], order["token"]):
            with self.subTest(token=token[:8]):
                r = client.post("/api/game/leaderboard", json={"token": token, "nickname": "Robot"})
                self.assertEqual((r.status_code, r.get_json()["error"]), (400, "token_invalid"))

    def test_il_round_a_serie_non_rilega_il_token_della_sfida_del_giorno(self):
        client, compare, order = self._sessioni()
        sid_compare = quiz_tokens.load_state(compare["token"], "compare_daily")["sid"]
        sid_order = quiz_tokens.load_state(order["token"], "order_daily")["sid"]
        r = client.get("/api/game/compare/round?token=" + compare["token"]).get_json()
        stato = quiz_tokens.load_state(r["token"], "compare")
        self.assertNotEqual(stato["sid"], sid_compare)
        self.assertEqual((stato["q"], stato["s"]), (1, 0))
        r = client.get("/api/game/order/round?count=5&token=" + order["token"]).get_json()
        self.assertNotEqual(quiz_tokens.load_state(r["token"], "order")["sid"], sid_order)

    def test_le_risposte_a_serie_non_contano_il_token_della_sfida_del_giorno(self):
        client, compare, order = self._sessioni()
        r = client.post("/api/game/order/answer", json={
            "token": order["token"], "indicator_id": order["indicator"]["id"], "year": order["indicator"]["year"],
            "region_keys": [t["key"] for t in order["territories"]]})
        corpo = r.get_json()
        self.assertIsNone(corpo.get("session"))
        q = compare["questions"][0]
        r = client.post("/api/game/compare/answer", json={
            "token": compare["token"], "indicator_id": q["indicator"]["id"], "year": q["indicator"]["year"],
            "region_a_key": q["a"]["key"], "region_b_key": q["b"]["key"], "choice": "region_a"})
        self.assertIsNone(r.get_json().get("session"))

    def test_la_sessione_del_giorno_di_ordina_non_riprende_un_token(self):
        client, _, order = self._sessioni()
        again = client.get("/api/game/order/daily/session?level=regioni&token=" + order["token"]).get_json()
        self.assertNotEqual(quiz_tokens.load_state(again["token"], "order_daily")["sid"],
                            quiz_tokens.load_state(order["token"], "order_daily")["sid"])

    def test_un_token_di_serie_non_vale_nella_sfida_del_giorno_di_chi_e_maggiore(self):
        client = app.test_client()
        serie = client.get("/api/game/compare/round").get_json()
        sessione = client.get("/api/game/compare/daily/session?level=regioni").get_json()
        r = client.post("/api/game/compare/daily/answer", json={
            "token": serie["token"], "puzzle_id": sessione["puzzle_id"], "q": 0, "choice": "region_a"})
        self.assertEqual((r.status_code, r.get_json()["error"]), (400, "token_invalid"))


class StoreTest(Base):
    def test_daily_score_refuses_second_attempt(self):
        self.assertTrue(player_stats.record_daily_score("u1", "compare", "2026-09-30", 7))
        self.assertFalse(player_stats.record_daily_score("u1", "compare", "2026-09-30", 9))
        self.assertTrue(player_stats.record_daily_score("u1", "order", "2026-09-30", 3))
        self.assertTrue(player_stats.record_daily_score("u2", "compare", "2026-09-30", 3))
        self.assertFalse(player_stats.record_daily_score("u1", "compare", "30/09/2026", 3))

    def test_claim_round_is_single_use_and_old_rows_are_cleaned(self):
        from app.models import QuizAnswered
        self.assertTrue(quiz_tokens.claim_round("sid-x", 1))
        self.assertFalse(quiz_tokens.claim_round("sid-x", 1))
        self.assertTrue(quiz_tokens.claim_round("sid-x", 2))
        with session_scope() as s:
            s.query(QuizAnswered).filter_by(sid="sid-x", q=1).update({"answered_at": "2020-01-01T00:00:00Z"})
        self.assertTrue(quiz_tokens.claim_round("sid-y", 1))  # la scrittura pulisce le righe vecchie
        with session_scope() as s:
            self.assertIsNone(s.get(QuizAnswered, {"sid": "sid-x", "q": 1}))
            self.assertIsNotNone(s.get(QuizAnswered, {"sid": "sid-x", "q": 2}))

    def test_v1_token_opens_a_new_session(self):
        state = quiz_tokens.new_state("compare")
        state["v"] = 1
        self.assertEqual(quiz_tokens.load_state(quiz_tokens.sign_state(state), "compare")["s"], 0)
        self.assertNotEqual(quiz_tokens.load_state(quiz_tokens.sign_state(state), "compare")["sid"], state["sid"])


class AnswerRateLimitTest(Base):
    def test_ip_limit_on_answers(self):
        client = app.test_client()
        codes = [client.post("/api/game/order/answer", json={}).status_code for _ in range(121)]
        self.assertEqual(codes[:120], [400] * 120)
        self.assertEqual(codes[120], 429)

    def test_signed_sid_limit_on_answers(self):
        client = app.test_client()
        token = quiz_tokens.sign_state(quiz_tokens.new_state("compare"))
        codes = [client.post("/api/game/compare/answer", json={"token": token}).status_code
                 for _ in range(46)]
        self.assertEqual(codes[45], 429)
        self.assertNotIn(429, codes[:45])


class PathTest(Base):
    def _pool_by_family(self):
        families = {}
        for entry in quiz._quiz_indicators():
            ident = entry["id"]
            family = ident.split(":")[0] if ":" in ident else "ter"
            families.setdefault(family, entry)
        return families

    def test_path_in_compare_and_order_for_every_family(self):
        families = self._pool_by_family()
        self.assertTrue({"ter", "bes", "multiscopo", "eur"} <= set(families), sorted(families))
        for family, entry in families.items():
            fields = quiz._indicator_fields(entry)
            self.assertTrue(fields.get("path", "").startswith("/indicatore/"), family)
            distinct = []
            seen = set()
            for row in entry["ranking"]:
                if row["value"] not in seen:
                    seen.add(row["value"])
                    distinct.append(row["region_key"])
            compare = quiz.evaluate_compare(entry["id"], entry["year"], distinct[0], distinct[-1], "region_a")
            self.assertEqual(compare["indicator"]["path"], fields["path"], family)
            order = quiz.evaluate_order(entry["id"], entry["year"], distinct[:3])
            self.assertEqual(order["indicator"]["path"], fields["path"], family)

    def test_territorial_path_is_canonical(self):
        ter = next(e for e in quiz._quiz_indicators() if ":" not in e["id"])
        self.assertIn("/ter-", quiz._indicator_fields(ter)["path"])


class ClientIpTest(Base):
    def _post(self, client, xff):
        return client.post("/api/game/leaderboard", json={"token": "garbage", "nickname": "X"},
                           headers={"X-Forwarded-For": xff})

    def test_forged_xff_does_not_change_the_bucket(self):
        client = app.test_client()
        for i in range(5):
            self.assertEqual(self._post(client, f"10.0.0.{i}").status_code, 400)
        self.assertEqual(self._post(client, "10.0.0.99").status_code, 429)

    def test_on_cloud_run_the_trusted_hop_is_the_last_one(self):
        client = app.test_client()
        with mock.patch.dict(os.environ, {"K_SERVICE": "divarioitalia"}):
            for i in range(5):
                self.assertEqual(self._post(client, f"10.0.0.{i}, 203.0.113.7").status_code, 400)
            self.assertEqual(self._post(client, "10.9.9.9, 203.0.113.7").status_code, 429)
            cache.delete("rl:lb:203.0.113.7")


class DietroCloudflareTest(unittest.TestCase):
    """L'IP del client quando Cloud Run sta dietro Cloudflare (app/client_ip.py)."""

    EDGE = "172.69.9.50"  # un edge Cloudflare visto nei log di produzione

    def test_ultimo_hop_cloudflare_si_usa_cf_connecting_ip(self):
        self.assertEqual(client_ip.ip_del_client(f"1.2.3.4, 198.51.100.9, {self.EDGE}", "198.51.100.9"), "198.51.100.9")

    def test_senza_cf_connecting_ip_o_con_valore_non_valido_si_resta_sull_edge(self):
        self.assertEqual(client_ip.ip_del_client(self.EDGE, None), self.EDGE)
        self.assertEqual(client_ip.ip_del_client(self.EDGE, "non-un-ip"), self.EDGE)

    def test_chiamata_diretta_a_run_app_non_legge_cf_connecting_ip(self):
        # L'ultimo hop non e' Cloudflare: chiunque puo' aver scritto l'header.
        self.assertEqual(client_ip.ip_del_client("10.1.1.1, 203.0.113.7", "8.8.8.8"), "203.0.113.7")

    def test_senza_forwarded_for_non_c_e_un_hop(self):
        self.assertIsNone(client_ip.ip_del_client("", "8.8.8.8"))

    def test_gli_intervalli_contengono_i_cloudflare_dei_log_di_produzione(self):
        for ip in ("172.71.120.17", "104.22.148.71", "108.162.241.215", "162.158.217.74", "2606:4700::1"):
            self.assertTrue(client_ip.e_cloudflare(ip), ip)
        self.assertFalse(client_ip.e_cloudflare("203.0.113.7"))

    def test_due_giocatori_dietro_lo_stesso_edge_hanno_secchi_diversi(self):
        client = app.test_client()
        with mock.patch.dict(os.environ, {"K_SERVICE": "divarioitalia"}):
            for i in range(5):
                r = client.post("/api/game/leaderboard", json={"token": "garbage", "nickname": "X"},
                                headers={"X-Forwarded-For": f"9.9.9.9, {self.EDGE}", "CF-Connecting-IP": "198.51.100.50"})
                self.assertEqual(r.status_code, 400)
            limitato = client.post("/api/game/leaderboard", json={"token": "garbage", "nickname": "X"},
                                   headers={"X-Forwarded-For": f"9.9.9.9, {self.EDGE}", "CF-Connecting-IP": "198.51.100.50"})
            altro = client.post("/api/game/leaderboard", json={"token": "garbage", "nickname": "X"},
                                headers={"X-Forwarded-For": f"9.9.9.9, {self.EDGE}", "CF-Connecting-IP": "198.51.100.51"})
            cache.delete("rl:lb:198.51.100.50")
            cache.delete("rl:lb:198.51.100.51")
        self.assertEqual(limitato.status_code, 429)
        self.assertEqual(altro.status_code, 400)


if __name__ == "__main__":
    unittest.main()
