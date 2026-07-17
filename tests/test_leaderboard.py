import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import app, config, leaderboard, quiz, quiz_tokens
from app.cache import cache


class LeaderboardTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp()
        self._original_db = config.LEADERBOARD_DB
        config.LEADERBOARD_DB = str(Path(self._tmp_dir) / "leaderboard.sqlite3")
        # Il rate limiter di _rate_limit_ok vive nella stessa cache in-process
        # del catalogo (Flask-Caching SimpleCache): un cache.clear() pulirebbe
        # anche il pool quiz memoizzato, rendendo ogni test enormemente più
        # lento. Il test client usa sempre lo stesso IP fittizio, quindi
        # basta invalidare la sua chiave di rate limit.
        cache.delete("rl:lb:127.0.0.1")

    def tearDown(self):
        config.LEADERBOARD_DB = self._original_db
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


class TokenChainTest(LeaderboardTestBase):
    def test_compare_token_chain_tracks_streak_and_resets_on_wrong(self):
        client = app.test_client()

        def play_round(token):
            round_ = client.get(f"/api/game/compare/round?difficulty=0&token={token or ''}").get_json()
            values = {
                row["region_key"]: row["value"]
                for row in quiz._quiz_indicator_payload(
                    round_["indicator"]["id"], round_["indicator"]["year"]
                )["values"]
            }
            key_a, key_b = round_["region_a"]["region_key"], round_["region_b"]["region_key"]
            winner = "region_a" if values[key_a] > values[key_b] else "region_b"
            return round_, winner

        round_1, winner_1 = play_round(None)
        answer_1 = client.post("/api/game/compare/answer", json={
            "indicator_id": round_1["indicator"]["id"], "year": round_1["indicator"]["year"],
            "region_a_key": round_1["region_a"]["region_key"], "region_b_key": round_1["region_b"]["region_key"],
            "choice": winner_1, "token": round_1["token"],
        }).get_json()
        self.assertEqual(answer_1["session"], {"streak": 1, "best": 1, "rounds": 1})
        self.assertIsNotNone(answer_1["token"])

        round_2, winner_2 = play_round(answer_1["token"])
        loser_2 = "region_b" if winner_2 == "region_a" else "region_a"
        answer_2 = client.post("/api/game/compare/answer", json={
            "indicator_id": round_2["indicator"]["id"], "year": round_2["indicator"]["year"],
            "region_a_key": round_2["region_a"]["region_key"], "region_b_key": round_2["region_b"]["region_key"],
            "choice": loser_2, "token": round_2["token"],
        }).get_json()
        self.assertEqual(answer_2["session"], {"streak": 0, "best": 1, "rounds": 2})

    def test_order_token_tracks_perfect_streak(self):
        client = app.test_client()
        round_ = client.get("/api/game/order/round?count=3&token=").get_json()
        values = {
            row["region_key"]: row["value"]
            for row in quiz._quiz_indicator_payload(
                round_["indicator"]["id"], round_["indicator"]["year"]
            )["values"]
        }
        keys = [r["region_key"] for r in round_["regions"]]
        perfect = sorted(keys, key=lambda key: values[key], reverse=True)
        answer = client.post("/api/game/order/answer", json={
            "indicator_id": round_["indicator"]["id"], "year": round_["indicator"]["year"],
            "region_keys": perfect, "token": round_["token"],
        }).get_json()
        self.assertEqual(answer["session"], {"streak": 1, "best": 1, "rounds": 1})

    def test_tampered_token_yields_no_session_but_game_still_works(self):
        client = app.test_client()
        round_ = client.get("/api/game/compare/round?difficulty=0").get_json()
        values = {
            row["region_key"]: row["value"]
            for row in quiz._quiz_indicator_payload(
                round_["indicator"]["id"], round_["indicator"]["year"]
            )["values"]
        }
        key_a, key_b = round_["region_a"]["region_key"], round_["region_b"]["region_key"]
        winner = "region_a" if values[key_a] > values[key_b] else "region_b"
        tampered = round_["token"][:-2] + "zz"
        answer = client.post("/api/game/compare/answer", json={
            "indicator_id": round_["indicator"]["id"], "year": round_["indicator"]["year"],
            "region_a_key": key_a, "region_b_key": key_b, "choice": winner, "token": tampered,
        }).get_json()
        self.assertTrue(answer["correct"])
        self.assertIsNone(answer["session"])
        self.assertIsNone(answer["token"])

    def test_fp_mismatch_across_rounds_yields_no_session(self):
        client = app.test_client()
        round_a = client.get("/api/game/compare/round?difficulty=0").get_json()
        round_b = client.get(f"/api/game/compare/round?difficulty=0&token={round_a['token']}").get_json()
        # Risponde ai campi del round B usando il token legato al round A.
        answer = client.post("/api/game/compare/answer", json={
            "indicator_id": round_b["indicator"]["id"], "year": round_b["indicator"]["year"],
            "region_a_key": round_b["region_a"]["region_key"], "region_b_key": round_b["region_b"]["region_key"],
            "choice": "region_a", "token": round_a["token"],
        }).get_json()
        self.assertIsNone(answer["session"])

    def test_replaying_the_same_answer_is_idempotent(self):
        client = app.test_client()
        round_ = client.get("/api/game/compare/round?difficulty=0").get_json()
        values = {
            row["region_key"]: row["value"]
            for row in quiz._quiz_indicator_payload(
                round_["indicator"]["id"], round_["indicator"]["year"]
            )["values"]
        }
        key_a, key_b = round_["region_a"]["region_key"], round_["region_b"]["region_key"]
        winner = "region_a" if values[key_a] > values[key_b] else "region_b"
        body = {
            "indicator_id": round_["indicator"]["id"], "year": round_["indicator"]["year"],
            "region_a_key": key_a, "region_b_key": key_b, "choice": winner, "token": round_["token"],
        }
        first = client.post("/api/game/compare/answer", json=body).get_json()
        second = client.post("/api/game/compare/answer", json=body).get_json()
        self.assertEqual(first["session"], second["session"])
        self.assertEqual(first["token"], second["token"])


class LeaderboardStoreTest(LeaderboardTestBase):
    def test_submit_upserts_only_when_score_improves(self):
        leaderboard.submit("compare", "sid-1", "Anna", 3, {})
        leaderboard.submit("compare", "sid-1", "Anna", 2, {})  # peggiore, ignorato
        top = leaderboard.top("compare", "all", 10)
        self.assertEqual(len(top), 1)
        self.assertEqual(top[0]["score"], 3)

        leaderboard.submit("compare", "sid-1", "Anna", 5, {})  # migliore, sostituisce
        top = leaderboard.top("compare", "all", 10)
        self.assertEqual(top[0]["score"], 5)

    def test_top_orders_by_score_desc_then_earliest(self):
        leaderboard.submit("compare", "sid-a", "Bruno", 4, {})
        leaderboard.submit("compare", "sid-b", "Carla", 7, {})
        leaderboard.submit("compare", "sid-c", "Dario", 7, {})
        top = leaderboard.top("compare", "all", 10)
        self.assertEqual([row["nickname"] for row in top], ["Carla", "Dario", "Bruno"])
        self.assertEqual([row["rank"] for row in top], [1, 2, 3])

    def test_period_week_excludes_old_rows(self):
        leaderboard.submit("compare", "sid-recent", "Elena", 3, {})
        leaderboard.submit("compare", "sid-old", "Fabio", 9, {})
        conn = sqlite3.connect(config.LEADERBOARD_DB)
        conn.execute(
            "UPDATE scores SET created_at = datetime('now', '-30 days') WHERE session_id = 'sid-old'"
        )
        conn.commit()
        conn.close()

        week = leaderboard.top("compare", "week", 10)
        self.assertEqual([row["nickname"] for row in week], ["Elena"])
        everything = leaderboard.top("compare", "all", 10)
        self.assertEqual(len(everything), 2)

    def test_limit_is_clamped(self):
        for i in range(5):
            leaderboard.submit("order", f"sid-{i}", f"Player{i}", i + 1, {"count": 3})
        self.assertEqual(len(leaderboard.top("order", "all", 999)), 5)
        with self.assertRaises(ValueError):
            leaderboard.top("bad-mode", "all", 10)
        with self.assertRaises(ValueError):
            leaderboard.top("order", "bad-period", 10)


class LeaderboardApiTest(LeaderboardTestBase):
    def _stream_to_best(self, client, wins):
        """Gioca `wins` round corretti di fila a 'Chi è maggiore?' e
        restituisce il token finale con quello streak come record."""
        token = None
        for _ in range(wins):
            round_ = client.get(f"/api/game/compare/round?difficulty=0&token={token or ''}").get_json()
            values = {
                row["region_key"]: row["value"]
                for row in quiz._quiz_indicator_payload(
                    round_["indicator"]["id"], round_["indicator"]["year"]
                )["values"]
            }
            key_a, key_b = round_["region_a"]["region_key"], round_["region_b"]["region_key"]
            winner = "region_a" if values[key_a] > values[key_b] else "region_b"
            answer = client.post("/api/game/compare/answer", json={
                "indicator_id": round_["indicator"]["id"], "year": round_["indicator"]["year"],
                "region_a_key": key_a, "region_b_key": key_b, "choice": winner, "token": round_["token"],
            }).get_json()
            token = answer["token"]
        return token

    def test_submit_flow_returns_rank_and_get_lists_entry(self):
        client = app.test_client()
        token = self._stream_to_best(client, 2)
        response = client.post("/api/game/leaderboard", json={"token": token, "nickname": "Giulia"})
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["mode"], "compare")
        self.assertEqual(body["score"], 2)
        self.assertEqual(body["rank_all"], 1)
        self.assertEqual(body["rank_week"], 1)

        listing = client.get("/api/game/leaderboard?mode=compare&period=all").get_json()
        self.assertEqual(listing["entries"][0]["nickname"], "Giulia")
        self.assertEqual(listing["entries"][0]["score"], 2)

    def test_submit_rejects_missing_or_tampered_token(self):
        client = app.test_client()
        response = client.post("/api/game/leaderboard", json={"token": "not-a-real-token", "nickname": "Bob"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "token_invalid")

    def test_submit_rejects_zero_score_session(self):
        client = app.test_client()
        state = quiz_tokens.new_state("compare")
        token = quiz_tokens.sign_state(state)  # nessuna risposta ancora data: best = 0
        response = client.post("/api/game/leaderboard", json={"token": token, "nickname": "Zero"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "score_missing")

    def test_submit_rejects_invalid_and_blocked_nicknames(self):
        client = app.test_client()
        token = self._stream_to_best(client, 1)
        for bad_nick, expected_error in (
            ("a", "nickname_invalid"),
            ("x" * 20, "nickname_invalid"),
            ("<script>", "nickname_invalid"),
            ("cazzo", "nickname_blocked"),
        ):
            response = client.post("/api/game/leaderboard", json={"token": token, "nickname": bad_nick})
            self.assertEqual(response.status_code, 400, bad_nick)
            self.assertEqual(response.get_json()["error"], expected_error, bad_nick)

    def test_submit_rate_limited_after_five_per_minute(self):
        client = app.test_client()
        for _ in range(5):
            response = client.post("/api/game/leaderboard", json={"token": "garbage", "nickname": "X"})
            self.assertEqual(response.status_code, 400)
        sixth = client.post("/api/game/leaderboard", json={"token": "garbage", "nickname": "X"})
        self.assertEqual(sixth.status_code, 429)

    def test_get_rejects_bad_mode_and_period(self):
        client = app.test_client()
        self.assertEqual(client.get("/api/game/leaderboard?mode=bogus&period=all").status_code, 400)
        self.assertEqual(client.get("/api/game/leaderboard?mode=compare&period=bogus").status_code, 400)

    def test_get_has_noindex_header(self):
        client = app.test_client()
        response = client.get("/api/game/leaderboard?mode=compare&period=all")
        self.assertIn("noindex", response.headers["X-Robots-Tag"])


class LeaderboardPageTest(LeaderboardTestBase):
    def test_page_responds_with_noindex(self):
        client = app.test_client()
        response = client.get("/quiz/classifica")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'id="leaderboard-root"', response.data)
        self.assertIn("noindex", response.headers["X-Robots-Tag"])
        self.assertIn(b'name="robots" content="noindex', response.data)

    def test_page_excluded_from_sitemap(self):
        client = app.test_client()
        sitemap = client.get("/sitemap.xml").data
        self.assertNotIn(b"/quiz/classifica", sitemap)


class LeaderboardAdminDeleteTest(LeaderboardTestBase):
    def test_delete_requires_correct_admin_key(self):
        leaderboard.submit("compare", "sid-mod", "Spam", 3, {})
        client = app.test_client()

        wrong_key = client.post(
            "/api/game/leaderboard/admin/delete",
            headers={"X-Admin-Key": "not-the-secret"},
            json={"mode": "compare", "nickname": "Spam"},
        )
        self.assertEqual(wrong_key.status_code, 404)

        no_key = client.post("/api/game/leaderboard/admin/delete", json={"mode": "compare", "nickname": "Spam"})
        self.assertEqual(no_key.status_code, 404)

        self.assertEqual(len(leaderboard.top("compare", "all", 10)), 1)

    def test_delete_removes_matching_entry(self):
        leaderboard.submit("compare", "sid-mod", "Spam", 3, {})
        leaderboard.submit("compare", "sid-keep", "Anna", 5, {})
        client = app.test_client()

        response = client.post(
            "/api/game/leaderboard/admin/delete",
            headers={"X-Admin-Key": app.secret_key},
            json={"mode": "compare", "nickname": "Spam"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["deleted"], 1)

        remaining = leaderboard.top("compare", "all", 10)
        self.assertEqual([row["nickname"] for row in remaining], ["Anna"])


if __name__ == "__main__":
    unittest.main()
