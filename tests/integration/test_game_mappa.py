"""La sfida del giorno di "Dov'è la provincia?" (`app/game_mappa.py` e le rotte
`/api/game/map/daily/*`): apertura minima, valutazione del server, round monouso,
giorno di Roma, punteggio dell'account e contatore delle partite finite.

Le funzioni pure (fasce, storia, esito, nomi) sono in
`tests/unit/test_game_mappa_puro.py`."""

import json
import os
import re
import shutil
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from app import app, config, game_daily, game_mappa, quiz_tokens
from app.cache import cache

T0 = 1_800_000_000.0
ROME = game_daily.ROMA
# Estate: a Roma e' gia' il 6 ottobre (UTC+2). Inverno: l'ora solare inizia il 25
# ottobre 2026, alle 22:30 UTC del 5 novembre a Roma e' ancora il 5 (UTC+1).
SUMMER_2230 = datetime(2026, 10, 5, 22, 30, tzinfo=timezone.utc)
WINTER_2230 = datetime(2026, 11, 5, 22, 30, tzinfo=timezone.utc)
SUNDAY = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
REVEALING = ("chosen", "right", "distance_km", "direction")


def _clock(now):
    """Fissa il giorno di Roma visto dal modulo su un istante."""
    return mock.patch.object(game_mappa, "oggi_roma", return_value=game_daily.oggi_roma(now))


def _decode(token):
    return quiz_tokens._serializer().loads(token)


def _same_region_other(key):
    provinces = game_daily.province_pool()
    region = next(p["region"] for p in provinces if p["key"] == key)
    return next(p["key"] for p in provinces if p["region"] == region and p["key"] != key)


def _other_region(key):
    provinces = game_daily.province_pool()
    region = next(p["region"] for p in provinces if p["key"] == key)
    return next(p["key"] for p in provinces if p["region"] != region)


class Base(unittest.TestCase):
    def setUp(self):
        self._saved = (config.SUPABASE_JWT_SECRET, config.SUPABASE_URL, config.LEADERBOARD_DB)
        config.SUPABASE_JWT_SECRET = "test-jwt-secret"
        config.SUPABASE_URL = ""
        self._tmp = tempfile.mkdtemp()
        config.LEADERBOARD_DB = str(Path(self._tmp) / "m.sqlite3")
        self._clear_limits()
        self.client = app.test_client()
        self.clock = _clock(SUNDAY)
        self.clock.start()

    def tearDown(self):
        self.clock.stop()
        config.SUPABASE_JWT_SECRET, config.SUPABASE_URL, config.LEADERBOARD_DB = self._saved
        shutil.rmtree(self._tmp, ignore_errors=True)
        self._clear_limits()

    @staticmethod
    def _clear_limits():
        cache.delete("rl:ans:ip:127.0.0.1")

    def _open(self, level="italia", mode="map", now=T0):
        with mock.patch.object(quiz_tokens, "_now", return_value=now):
            response = self.client.get(f"/api/game/map/daily/session?level={level}&mode={mode}")
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()

    def _keys(self, session):
        return game_mappa.daily_provinces(date.fromisoformat(session["date"]), session["level"])

    def _answer(self, session, index, key, token=None, now=T0, field=None):
        field = field or ("region_key" if session["mode"] == "list" else "province_key")
        with mock.patch.object(quiz_tokens, "_now", return_value=now):
            return self.client.post("/api/game/map/daily/answer", json={
                "puzzle_id": session["puzzle_id"], "q": index, field: key,
                "token": session["token"] if token is None else token,
            })

    def _play(self, session, pick=None, step=2.0):
        """Gioca le dieci domande, con `pick(indice, chiave giusta)` come risposta
        (la giusta se manca) e l'orologio che avanza di `step` secondi a domanda.
        Ritorna le risposte."""
        keys = self._keys(session)
        token, now, answers = session["token"], T0, []
        for index, right in enumerate(keys):
            now += step
            choice = pick(index, right) if pick else right
            response = self._answer(session, index, choice, token=token, now=now)
            self.assertEqual(response.status_code, 200, (index, response.get_json()))
            answers.append(response.get_json())
            token = answers[-1]["token"]
        return answers

    def _assert_reveals_nothing(self, response):
        body = response.get_json()
        self.assertNotEqual(response.status_code, 200)
        for field in REVEALING:
            self.assertNotIn(field, body, body)


class SessionTest(Base):
    def test_exact_shape_at_each_level_and_mode(self):
        common = {"puzzle_id", "number", "date", "next_puzzle_at", "level", "level_label",
                  "mode", "total", "points_max", "question", "token"}
        italia = self._open("italia", "map")
        self.assertEqual(set(italia), common)
        self.assertEqual(set(italia["question"]), {"index", "name", "label"})
        self.assertEqual((italia["total"], italia["points_max"], italia["question"]["index"]), (10, 20, 0))
        self.assertEqual(italia["puzzle_id"], "daily:2026-10-11")
        self.assertEqual(italia["number"], game_daily.numero_sfida(date(2026, 10, 11)))
        self.assertEqual(italia["level_label"], "Tutta Italia")

        regione = self._open("regione", "map")
        self.assertEqual(set(regione), common)
        self.assertEqual(set(regione["question"]), {"index", "name", "label", "region", "region_key"})

        elenco = self._open("italia", "list")
        self.assertEqual(set(elenco), common | {"regions"})
        self.assertEqual(elenco["points_max"], 10)
        self.assertEqual(len(elenco["regions"]), 20)
        self.assertEqual(set(elenco["regions"][0]), {"key", "name"})
        self.assertIn({"key": "puglia", "name": "Puglia"}, elenco["regions"])

    def test_unknown_level_or_mode_and_list_with_region_level_are_400(self):
        for query in ("level=europa", "mode=voce", "level=regione&mode=list", "level=&mode=map"):
            response = self.client.get(f"/api/game/map/daily/session?{query}")
            self.assertEqual(response.status_code, 400, query)
            self.assertEqual(response.get_json(), {"error": "bad_request"})

    def test_opening_has_no_coordinates_no_answer_and_no_other_name_of_the_day(self):
        for level, mode in game_mappa.SCORE_GAMES:
            session = self._open(level, mode)
            keys = self._keys(session)
            without_token = {k: v for k, v in session.items() if k not in ("token", "regions")}
            text = json.dumps(without_token, ensure_ascii=False)
            decoded = json.dumps(_decode(session["token"]), ensure_ascii=False)
            for field in ("x", "y", "w", "h", "area", "provinces", "start_view", "viewbox", "key\""):
                self.assertNotIn(f'"{field}', text, (level, mode, field))
            # Nessun numero con decimali: le coordinate del viewBox lo sono tutte.
            self.assertIsNone(re.search(r"\d+\.\d+", text), (level, mode))
            if level == "italia":
                self.assertNotIn(keys[0], text)
                self.assertNotIn("region", session["question"])
            names = {p["key"]: game_mappa.display_name(p) for p in game_daily.province_pool()}
            for other in keys[1:]:
                self.assertNotIn(names[other], text, (level, mode, other))
                self.assertNotIn(names[other], decoded, (level, mode, other))
                self.assertNotIn(other, decoded, (level, mode, other))
            self.assertNotIn(keys[0], decoded)
            if mode == "list":
                self.assertEqual({tuple(r) for r in session["regions"]}, {("key", "name")})

    def test_every_opening_is_a_new_session(self):
        one, two = self._open(), self._open()
        self.assertNotEqual(_decode(one["token"])["sid"], _decode(two["token"])["sid"])

    def test_the_token_mode_is_refused_by_the_leaderboard(self):
        self.assertIsNone(quiz_tokens.peek_state(self._open()["token"]))

    def test_session_rate_limit(self):
        codes = [self.client.get("/api/game/map/daily/session?level=europa").status_code for _ in range(121)]
        self.assertEqual(codes[:120], [400] * 120)
        self.assertEqual(codes[120], 429)


class SeedTest(Base):
    def test_503_without_seed_in_production(self):
        session = self._open()
        env = {k: v for k, v in os.environ.items() if k != "GAME_SEED_KEY"}
        env["K_SERVICE"] = "divarioitalia"
        with mock.patch.dict(os.environ, env, clear=True):
            opened = self.client.get("/api/game/map/daily/session")
            answered = self._answer(session, 0, "lecce")
        self.assertEqual(opened.status_code, 503)
        self.assertEqual(opened.get_json(), {"error": "seed_unavailable"})
        self.assertEqual(answered.status_code, 503)
        self._assert_reveals_nothing(answered)


class SameForEveryoneTest(Base):
    def test_same_day_same_challenge_and_two_levels_differ(self):
        one, two = self._open(), self._open()
        self.assertEqual(one["question"], two["question"])
        self.assertEqual(self._keys(one), self._keys(two))
        self.assertNotEqual(set(self._keys(one)), set(self._keys(self._open("regione"))))

    def test_list_mode_asks_the_same_ten_provinces(self):
        self.assertEqual(self._keys(self._open("italia", "list")), self._keys(self._open("italia", "map")))


class AnswerTest(Base):
    def test_exact_region_miss_are_two_one_zero(self):
        session = self._open()
        right = self._keys(session)[0]
        near, far = _same_region_other(right), _other_region(right)
        token = session["token"]

        exact = self._answer(session, 0, right).get_json()
        self.assertEqual((exact["esito"], exact["points"], exact["distance_km"], exact["direction"]),
                         ("exact", 2, None, None))
        self.assertEqual(exact["score"], {"points": 2, "max": 20, "answered": 1})

        # Lo stesso round con un'altra sessione per gli altri due esiti.
        for choice, result, points in ((near, "region", 1), (far, "miss", 0)):
            session = self._open()
            body = self._answer(session, 0, choice).get_json()
            self.assertEqual((body["esito"], body["points"]), (result, points))
            km, direction = game_daily.distanza_km_direzione(choice, right)
            self.assertEqual((body["distance_km"], body["direction"]), (km, direction))
        self.assertNotEqual(token, session["token"])

    def test_answer_shape(self):
        session = self._open("regione")
        right = self._keys(session)[0]
        body = self._answer(session, 0, _same_region_other(right)).get_json()
        self.assertEqual(set(body), {"index", "esito", "points", "score", "chosen", "right", "distance_km",
                                     "direction", "finished", "next_question", "token"})
        self.assertEqual(set(body["chosen"]), {"key", "name", "region", "path"})
        self.assertEqual(set(body["right"]), {"key", "name", "region", "region_key", "path"})
        self.assertEqual(body["right"]["key"], right)
        self.assertEqual(body["right"]["path"], f"/provincia/{right}")
        self.assertFalse(body["finished"])
        self.assertEqual(set(body["next_question"]), {"index", "name", "label", "region", "region_key"})
        self.assertEqual(body["next_question"]["index"], 1)

    def test_out_of_region_choice_at_region_level_is_accepted_with_zero(self):
        session = self._open("regione")
        right = self._keys(session)[0]
        response = self._answer(session, 0, _other_region(right))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["points"], 0)

    def test_sardinian_provinces_can_be_chosen(self):
        session = self._open()
        response = self._answer(session, 0, "sud-sardegna")
        self.assertEqual(response.status_code, 200)

    def test_level_in_the_body_is_ignored(self):
        session = self._open("italia")
        right = self._keys(session)[0]
        with mock.patch.object(quiz_tokens, "_now", return_value=T0):
            response = self.client.post("/api/game/map/daily/answer", json={
                "puzzle_id": session["puzzle_id"], "q": 0, "province_key": right,
                "level": "regione", "mode": "list", "token": session["token"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["points"], 2)

    def test_list_mode_one_point_for_the_right_region(self):
        session = self._open("italia", "list")
        right = self._keys(session)[0]
        region_key = next(p["region_key"] for p in game_daily.province_pool() if p["key"] == right)
        wrong = "molise" if region_key != "molise" else "puglia"
        good = self._answer(session, 0, region_key).get_json()
        self.assertEqual((good["esito"], good["points"], good["distance_km"], good["direction"]),
                         ("exact", 1, None, None))
        self.assertEqual(good["chosen"]["path"], f"/regione/{region_key}")
        self.assertEqual(good["score"]["max"], 10)
        bad = self._answer(self._open("italia", "list"), 0, wrong).get_json()
        self.assertEqual((bad["esito"], bad["points"]), ("miss", 0))

    def test_list_mode_refuses_a_province_key(self):
        session = self._open("italia", "list")
        response = self._answer(session, 0, self._keys(session)[0], field="province_key")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "bad_request"})

    def test_the_next_question_is_bound_by_the_answer(self):
        session = self._open()
        keys = self._keys(session)
        first = self._answer(session, 0, keys[0]).get_json()
        second = self._answer(session, 1, keys[1], token=first["token"])
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.get_json()["score"]["points"], 4)


class ErrorsTest(Base):
    def test_errors_in_order_and_none_reveals_anything(self):
        session = self._open()
        right = self._keys(session)[0]
        compare_token = quiz_tokens.bind_round(quiz_tokens.load_state(None, "compare_daily"), "x", 2020, ["a"], "regioni")
        cases = [
            ({"puzzle_id": "daily:2026-10-10"}, 400, "puzzle_changed"),
            ({"token": None}, 400, "token_invalid"),
            ({"token": "rotto"}, 400, "token_invalid"),
            ({"token": compare_token}, 400, "token_invalid"),
            ({"q": 1}, 400, "token_invalid"),
            ({"q": "0"}, 400, "token_invalid"),
            ({"q": True}, 400, "token_invalid"),
            ({"q": 10}, 400, "token_invalid"),
            ({"province_key": "atlantide"}, 400, "bad_request"),
            ({"province_key": None}, 400, "bad_request"),
        ]
        for change, status, error in cases:
            body = {"puzzle_id": session["puzzle_id"], "q": 0, "province_key": right, "token": session["token"]}
            body.update(change)
            response = self.client.post("/api/game/map/daily/answer", json=body)
            self.assertEqual((response.status_code, response.get_json()), (status, {"error": error}), change)
            self._assert_reveals_nothing(response)

    def test_a_bad_key_does_not_burn_the_round_and_the_round_is_claimed_once(self):
        session = self._open()
        right = self._keys(session)[0]
        self.assertEqual(self._answer(session, 0, "atlantide").status_code, 400)
        self.assertEqual(self._answer(session, 0, right).status_code, 200)
        again = self._answer(session, 0, right)
        self.assertEqual(again.status_code, 409)
        self.assertEqual(again.get_json(), {"error": "round_already_answered"})
        self._assert_reveals_nothing(again)

    def test_a_replay_does_not_move_the_score(self):
        session = self._open()
        keys = self._keys(session)
        first = self._answer(session, 0, _other_region(keys[0])).get_json()
        self.assertEqual(self._answer(session, 0, keys[0]).status_code, 409)
        second = self._answer(session, 1, keys[1], token=first["token"]).get_json()
        self.assertEqual(second["score"]["points"], 2)

    def test_answer_token_cannot_answer_the_same_question_again(self):
        session = self._open()
        first = self._answer(session, 0, self._keys(session)[0]).get_json()
        response = self._answer(session, 0, self._keys(session)[0], token=first["token"])
        self.assertEqual(response.get_json(), {"error": "token_invalid"})

    def test_yesterdays_token_is_refused_today(self):
        with _clock(SUNDAY - timedelta(days=1)):
            yesterday = self._open()
        with _clock(SUNDAY):
            today = self._open()
            response = self._answer(today, 0, self._keys(today)[0], token=yesterday["token"])
        self.assertEqual(response.get_json(), {"error": "token_invalid"})
        self._assert_reveals_nothing(response)

    def test_a_token_older_than_twelve_hours_says_so(self):
        # L'orologio di itsdangerous (che firma e controlla l'eta' del token) fermo
        # su T0 all'apertura: a 11 ore il token vale ancora, a 13 no.
        with mock.patch("itsdangerous.timed.time.time", return_value=T0):
            session = self._open()
        right = self._keys(session)[0]
        later = T0 + 13 * 3600
        with mock.patch("itsdangerous.timed.time.time", return_value=later):
            response = self._answer(session, 0, right, now=later)
        self.assertEqual((response.status_code, response.get_json()), (400, {"error": "session_expired"}))
        self._assert_reveals_nothing(response)
        with mock.patch("itsdangerous.timed.time.time", return_value=T0 + 11 * 3600):
            response = self._answer(session, 0, right, now=T0 + 11 * 3600)
        self.assertEqual(response.status_code, 200)

    def test_answer_rate_limit(self):
        codes = [self.client.post("/api/game/map/daily/answer", json={}).status_code for _ in range(121)]
        self.assertEqual(codes[:120], [400] * 120)
        self.assertEqual(codes[120], 429)


class RomeDayTest(Base):
    def test_summer_2230_utc_is_already_tomorrow_in_rome(self):
        with _clock(SUMMER_2230):
            session = self._open()
        self.assertEqual(session["date"], "2026-10-06")

    def test_winter_2230_utc_is_still_today_in_rome(self):
        with _clock(WINTER_2230):
            session = self._open()
        self.assertEqual(session["date"], "2026-11-05")
        self.assertEqual(session["next_puzzle_at"], "2026-11-05T23:00:00+00:00")

    def test_midnight_between_opening_and_answer_gives_puzzle_changed(self):
        for midnight in (datetime(2026, 10, 6, 0, 0, tzinfo=ROME), datetime(2026, 11, 6, 0, 0, tzinfo=ROME)):
            with _clock(midnight - timedelta(seconds=10)):
                session = self._open()
                right = self._keys(session)[0]
            with _clock(midnight + timedelta(seconds=5)):
                response = self._answer(session, 0, right)
            self.assertEqual(response.get_json(), {"error": "puzzle_changed"}, midnight)
            self._assert_reveals_nothing(response)


class FinishTest(Base):
    def _scores(self):
        from sqlalchemy import select
        from app.db import session_scope
        from app.models import DailyScore
        with session_scope() as s:
            return [(r.auth_id, r.gioco, r.data, r.punteggio)
                    for r in s.execute(select(DailyScore)).scalars().all()]

    def _counter(self):
        from app.db import session_scope
        from app.models import DailyCounter
        with session_scope() as s:
            return {(r.gioco, r.data, r.punteggio): r.conteggio for r in s.query(DailyCounter).all()}

    def _login(self, sub):
        import jwt
        credential = jwt.encode(
            {"sub": sub, "email": "m@example.com", "aud": "authenticated",
             "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "test-jwt-secret", algorithm="HS256")
        self.client.environ_base["HTTP_AUTHORIZATION"] = "Bearer " + credential

    def test_last_answer_carries_the_summary(self):
        session = self._open()
        answers = self._play(session, pick=lambda i, right: right if i % 2 == 0 else _other_region(right))
        last = answers[-1]
        self.assertTrue(last["finished"])
        self.assertIsNone(last["next_question"])
        self.assertEqual(set(last["summary"]), {"puzzle_id", "number", "date", "next_puzzle_at", "score",
                                                "esiti", "achievements"})
        self.assertEqual(last["summary"]["esiti"], ["exact", "miss"] * 5)
        self.assertEqual(last["summary"]["score"], {"points": 10, "max": 20, "answered": 10})
        self.assertEqual(last["summary"]["achievements"], [])
        self.assertTrue(all("summary" not in a for a in answers[:-1]))
        after = self._answer(session, 9, self._keys(session)[9], token=last["token"])
        self.assertEqual(after.get_json(), {"error": "token_invalid"})

    def test_logged_in_plausible_game_records_once_per_day(self):
        self._login("uuid-mappa-1")
        session = self._open()
        last = self._play(session)[-1]
        self.assertEqual(self._scores(), [("uuid-mappa-1", "mappa", "2026-10-11", 20)])
        self.assertIsInstance(last["summary"]["achievements"], list)
        self._play(self._open(), pick=lambda i, right: _other_region(right))
        self.assertEqual(self._scores(), [("uuid-mappa-1", "mappa", "2026-10-11", 20)])

    def test_each_level_and_mode_has_its_own_game(self):
        self._login("uuid-mappa-2")
        self._play(self._open("regione"))
        session = self._open("italia", "list")
        regions = {p["key"]: p["region_key"] for p in game_daily.province_pool()}
        self._play(session, pick=lambda i, right: regions[right])
        self.assertEqual(sorted(self._scores()), [
            ("uuid-mappa-2", "mappa_elenco", "2026-10-11", 10),
            ("uuid-mappa-2", "mappa_regione", "2026-10-11", 20),
        ])

    def test_anonymous_records_nothing_for_the_account(self):
        self._play(self._open())
        self.assertEqual(self._scores(), [])

    def test_an_implausible_game_is_not_recorded(self):
        self._login("uuid-mappa-3")
        self._play(self._open(), step=0.1)
        self.assertEqual(self._scores(), [])

    def test_the_counter_counts_every_finished_game(self):
        self._play(self._open())
        self._login("uuid-mappa-4")
        self._play(self._open(), step=0.1)
        self._play(self._open("regione"), pick=lambda i, right: _other_region(right))
        self.assertEqual(self._counter(), {
            ("mappa", "2026-10-11", 20): 2,
            ("mappa_regione", "2026-10-11", 0): 1,
        })

    def test_the_counter_is_not_touched_before_the_end(self):
        session = self._open()
        self._answer(session, 0, self._keys(session)[0])
        self.assertEqual(self._counter(), {})

    def test_a_failing_score_table_does_not_break_the_answer(self):
        self._login("uuid-mappa-5")
        from app import player_stats
        with mock.patch.object(player_stats, "record_daily_score", side_effect=RuntimeError("giu'")):
            with self.assertLogs(app.logger, level="ERROR"):
                last = self._play(self._open())[-1]
        self.assertTrue(last["finished"])


if __name__ == "__main__":
    unittest.main()
