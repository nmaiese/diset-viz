import unittest
from datetime import date, datetime, timedelta

from app import app
from app.data import REGION_ORDER
from app import game


class GameTest(unittest.TestCase):
    def test_game_page_responds(self):
        client = app.test_client()
        page = client.get("/quiz/indovina-la-regione")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'id="game-root"', page.data)
        self.assertIn(b'id="game-map-frame"', page.data)
        self.assertIn(b"Indovina la Regione", page.data)

    def test_game_page_has_explicit_index_header(self):
        client = app.test_client()
        page = client.get("/quiz/indovina-la-regione")
        self.assertEqual(
            page.headers.get("X-Robots-Tag"),
            "index, follow, max-snippet:-1, max-image-preview:large",
        )

    def test_hub_page_responds(self):
        client = app.test_client()
        page = client.get("/quiz")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'id="hub-root"', page.data)
        self.assertIn("Quanto conosci l'Italia?".encode(), page.data)
        for href in (b"/quiz/indovina-la-regione", b"/quiz/chi-e-maggiore", b"/quiz/ordina"):
            self.assertIn(href, page.data)

    def test_legacy_gioco_paths_redirect_permanently(self):
        client = app.test_client()
        cases = {
            "/gioco": "/quiz",
            "/gioco/chi-e-maggiore": "/quiz/chi-e-maggiore",
            "/gioco/ordina": "/quiz/ordina",
        }
        for old, new in cases.items():
            response = client.get(old, follow_redirects=False)
            self.assertEqual(response.status_code, 301, old)
            self.assertTrue(response.headers["Location"].endswith(new), old)

    def test_sitemap_lists_game_page(self):
        client = app.test_client()
        sitemap = client.get("/sitemap.xml").data
        self.assertIn(b"/quiz<", sitemap)
        self.assertIn(b"/quiz/indovina-la-regione", sitemap)
        self.assertNotIn(b"/gioco", sitemap)

    def test_game_regions_api(self):
        client = app.test_client()
        response = client.get("/api/game/regions")
        self.assertEqual(response.status_code, 200)
        self.assertIn("noindex", response.headers["X-Robots-Tag"])
        regions = response.get_json()["regions"]
        self.assertEqual(len(regions), 20)
        for entry in regions:
            self.assertIn("region", entry)
            self.assertIn("region_key", entry)

    def test_daily_puzzle_is_deterministic_and_has_no_solution_leak(self):
        client = app.test_client()
        first = client.get("/api/game/daily").get_json()
        second = client.get("/api/game/daily").get_json()
        self.assertEqual(first, second)

        self.assertEqual(first["clues_total"], 6)
        self.assertEqual(first["attempts_total"], 6)
        self.assertIn("puzzle_id", first)
        self.assertTrue(first["puzzle_id"].startswith("daily:"))
        self.assertIn("clue", first)
        for field in (
            "id", "name", "theme", "macro_area", "unit", "year", "value", "rank",
            "region_count", "source_label", "source_url",
        ):
            self.assertIn(field, first["clue"])
        self.assertGreaterEqual(first["clue"]["rank"], 1)
        self.assertLessEqual(first["clue"]["rank"], first["clue"]["region_count"])
        # The mystery region itself never appears in the intro payload.
        self.assertNotIn("region", first)
        self.assertNotIn("region_key", first)
        self.assertNotIn("solution", first)

        # Countdown to the next release, so the client never has to guess the
        # server's timezone.
        self.assertIn("next_puzzle_at", first)
        next_at = datetime.fromisoformat(first["next_puzzle_at"])
        self.assertGreater(next_at, datetime.now(next_at.tzinfo))

    def test_practice_puzzle_has_no_number_and_is_fresh_each_time(self):
        client = app.test_client()
        first = client.get("/api/game/practice").get_json()
        second = client.get("/api/game/practice").get_json()
        self.assertIsNone(first["number"])
        self.assertIsNone(first["date"])
        self.assertTrue(first["puzzle_id"].startswith("practice:"))
        # Astronomically unlikely to collide; a repeat would signal a broken seed.
        self.assertNotEqual(first["puzzle_id"], second["puzzle_id"])

    def test_guess_flow_wrong_then_correct(self):
        client = app.test_client()
        daily = client.get("/api/game/daily").get_json()
        puzzle_id = daily["puzzle_id"]
        puzzle = game.build_puzzle(puzzle_id)
        mystery_key = puzzle["region_key"]
        wrong_key = next(k for k in (game_region_keys()) if k != mystery_key)

        wrong = client.post("/api/game/guess", json={
            "puzzle_id": puzzle_id, "region_key": wrong_key, "attempt": 1,
        }).get_json()
        self.assertFalse(wrong["correct"])
        self.assertFalse(wrong["finished"])
        # The frontend map highlighting keys off region_key, not the display name.
        self.assertEqual(wrong["region_key"], wrong_key)
        self.assertEqual(len(wrong["feedback"]), 1)
        entry = wrong["feedback"][0]
        self.assertIn(entry["comparison"], ("higher", "lower", "equal", "unknown"))
        for field in ("guess_value", "guess_rank", "mystery_rank", "region_count"):
            self.assertIn(field, entry)
        self.assertGreaterEqual(entry["mystery_rank"], 1)
        self.assertLessEqual(entry["mystery_rank"], entry["region_count"])
        self.assertGreaterEqual(entry["guess_rank"], 1)
        self.assertLessEqual(entry["guess_rank"], entry["region_count"])
        self.assertIsNotNone(wrong["next_clue"])
        self.assertIsNone(wrong["solution"])
        self.assertIsNone(wrong["ripartizione_hint"])  # only from attempt 3 onward

        third = client.post("/api/game/guess", json={
            "puzzle_id": puzzle_id, "region_key": wrong_key, "attempt": 3,
        }).get_json()
        self.assertIsNotNone(third["ripartizione_hint"])
        self.assertIn("same", third["ripartizione_hint"])

        correct = client.post("/api/game/guess", json={
            "puzzle_id": puzzle_id, "region_key": mystery_key, "attempt": 4,
        }).get_json()
        self.assertTrue(correct["correct"])
        self.assertTrue(correct["finished"])
        self.assertIsNone(correct["next_clue"])
        self.assertEqual(correct["solution"]["region_key"], mystery_key)
        self.assertEqual(len(correct["recap"]), 6)
        for row in correct["recap"]:
            for field in ("id", "name", "unit", "year", "value", "path"):
                self.assertIn(field, row)

    def test_guess_flow_exhausts_attempts_and_reveals_solution(self):
        client = app.test_client()
        daily = client.get("/api/game/daily").get_json()
        puzzle_id = daily["puzzle_id"]
        puzzle = game.build_puzzle(puzzle_id)
        mystery_key = puzzle["region_key"]
        wrong_key = next(k for k in game_region_keys() if k != mystery_key)

        last = None
        for attempt in range(1, 7):
            last = client.post("/api/game/guess", json={
                "puzzle_id": puzzle_id, "region_key": wrong_key, "attempt": attempt,
            }).get_json()
            if attempt < 6:
                self.assertFalse(last["finished"])
        self.assertTrue(last["finished"])
        self.assertFalse(last["correct"])
        self.assertEqual(last["solution"]["region_key"], mystery_key)
        self.assertEqual(len(last["recap"]), 6)

    def test_guess_rejects_invalid_input(self):
        client = app.test_client()
        daily = client.get("/api/game/daily").get_json()
        puzzle_id = daily["puzzle_id"]

        bad_region = client.post("/api/game/guess", json={
            "puzzle_id": puzzle_id, "region_key": "atlantide", "attempt": 1,
        })
        self.assertEqual(bad_region.status_code, 400)

        bad_attempt = client.post("/api/game/guess", json={
            "puzzle_id": puzzle_id, "region_key": "lombardia", "attempt": 7,
        })
        self.assertEqual(bad_attempt.status_code, 400)

        bad_puzzle = client.post("/api/game/guess", json={
            "puzzle_id": "not-a-real-id", "region_key": "lombardia", "attempt": 1,
        })
        self.assertEqual(bad_puzzle.status_code, 400)

        missing_fields = client.post("/api/game/guess", json={"puzzle_id": puzzle_id})
        self.assertEqual(missing_fields.status_code, 400)

    def test_no_daily_repeat_within_a_twenty_day_window(self):
        seen = set()
        for offset in range(20):
            puzzle_id, today = game.daily_puzzle_id(game.GAME_EPOCH + timedelta(days=offset))
            region = game.region_for_puzzle(puzzle_id)
            self.assertNotIn(region, seen)
            seen.add(region)
        self.assertEqual(len(seen), 20)

    def test_every_region_yields_six_distinct_clues(self):
        for region in REGION_ORDER:
            seed = None
            for i in range(4000):
                candidate = f"practice:{i:x}"
                if game.region_for_puzzle(candidate) == region:
                    seed = candidate
                    break
            self.assertIsNotNone(seed, region)
            puzzle = game.build_puzzle(seed)
            self.assertEqual(puzzle["region"], region)
            self.assertEqual(len(puzzle["clues"]), 6)
            ids = [c["id"] for c in puzzle["clues"]]
            self.assertEqual(len(set(ids)), 6)

    def test_ripartizione_covers_every_region(self):
        for region in REGION_ORDER:
            self.assertIn(region, game.RIPARTIZIONE)

    def test_puzzle_number_starts_at_one_on_launch_day(self):
        self.assertEqual(game.puzzle_number(game.GAME_EPOCH), 1)
        self.assertEqual(game.puzzle_number(game.GAME_EPOCH + timedelta(days=5)), 6)

    def test_archive_day_route(self):
        client = app.test_client()
        today = date.today()

        # A past (or launch-day) date is playable and carries the right puzzle number.
        past = max(today - timedelta(days=1), game.GAME_EPOCH)
        response = client.get(f"/api/game/daily/{past.isoformat()}")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["date"], past.isoformat())
        self.assertEqual(payload["number"], game.puzzle_number(past))
        self.assertEqual(payload["puzzle_id"], f"daily:{past.isoformat()}")

        # Today itself is playable through the archive route too.
        today_response = client.get(f"/api/game/daily/{today.isoformat()}")
        self.assertEqual(today_response.status_code, 200)

        # A future date must never resolve: that would leak tomorrow's answer.
        tomorrow = today + timedelta(days=1)
        future_response = client.get(f"/api/game/daily/{tomorrow.isoformat()}")
        self.assertEqual(future_response.status_code, 404)

        # Before launch: not a real puzzle.
        pre_launch = client.get(f"/api/game/daily/{(game.GAME_EPOCH - timedelta(days=1)).isoformat()}")
        self.assertEqual(pre_launch.status_code, 404)

        # Malformed dates 404 instead of raising.
        for bad in ("not-a-date", "2026-13-40", "2026-02-30"):
            self.assertEqual(client.get(f"/api/game/daily/{bad}").status_code, 404, bad)

    def test_archive_list(self):
        client = app.test_client()
        response = client.get("/api/game/archive")
        self.assertEqual(response.status_code, 200)
        puzzles = response.get_json()["puzzles"]

        today = date.today()
        for item in puzzles:
            day = date.fromisoformat(item["date"])
            self.assertLess(day, today)  # today is excluded, it's the main daily tab
            self.assertGreaterEqual(day, game.GAME_EPOCH)
            self.assertEqual(item["number"], game.puzzle_number(day))
        # Most-recent-first.
        dates = [item["date"] for item in puzzles]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_guess_rejects_future_daily_puzzle_id(self):
        """Anti-spoiler: a client must not be able to fetch tomorrow's solution
        by fabricating a future daily puzzle_id and racing to attempt 6."""
        client = app.test_client()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        response = client.post("/api/game/guess", json={
            "puzzle_id": f"daily:{tomorrow}", "region_key": "lombardia", "attempt": 1,
        })
        self.assertEqual(response.status_code, 400)


class QuizCompareTest(unittest.TestCase):
    def test_compare_page_responds_without_map(self):
        client = app.test_client()
        page = client.get("/quiz/chi-e-maggiore")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'id="compare-root"', page.data)
        self.assertNotIn(b'id="game-map-frame"', page.data)

    def test_compare_round_shape_and_no_value_leak(self):
        import json

        client = app.test_client()
        response = client.get("/api/game/compare/round?difficulty=2")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        for field in ("id", "name", "theme", "macro_area", "unit", "year", "source_label", "source_url"):
            self.assertIn(field, payload["indicator"])
        self.assertTrue(payload["indicator"]["source_url"].startswith("http"))
        self.assertEqual(payload["difficulty"], 2)
        self.assertNotEqual(payload["region_a"]["region_key"], payload["region_b"]["region_key"])
        self.assertNotIn('"value"', json.dumps(payload))
        # La descrizione si rivela solo alla risposta, non nel round.
        self.assertNotIn("description", payload["indicator"])

    def test_compare_rounds_use_core_indicators_with_distinct_values(self):
        from app import quiz
        from app.data import get_catalog, get_indicator_year
        from app import profiles

        core_ids = {item["id"] for item in get_catalog()["indicators"] if profiles.is_core(item)}
        for _ in range(40):
            round_ = quiz.compare_round(4)
            self.assertIn(round_["indicator"]["id"], core_ids)
            payload = get_indicator_year(round_["indicator"]["id"], round_["indicator"]["year"])
            values = {row["region_key"]: row["value"] for row in payload["values"]}
            value_a = values[round_["region_a"]["region_key"]]
            value_b = values[round_["region_b"]["region_key"]]
            self.assertNotEqual(value_a, value_b)

    def test_compare_difficulty_narrows_value_gap(self):
        from app import quiz
        from app.data import get_indicator_year

        def value_index_gap(round_):
            # Distanza tra i due valori nella lista dei valori DISTINTI
            # dell'indicatore (non il rank grezzo, che con i pareggi non è
            # un indice affidabile di quanto le due regioni siano vicine).
            payload = get_indicator_year(round_["indicator"]["id"], round_["indicator"]["year"])
            distinct = sorted({row["value"] for row in payload["values"]}, reverse=True)
            values = {row["region_key"]: row["value"] for row in payload["values"]}
            idx_a = distinct.index(values[round_["region_a"]["region_key"]])
            idx_b = distinct.index(values[round_["region_b"]["region_key"]])
            return abs(idx_a - idx_b), len(distinct)

        easy_ratios, hard_ratios = [], []
        for _ in range(40):
            gap, n = value_index_gap(quiz.compare_round(0))
            easy_ratios.append(gap / (n - 1))
            gap, n = value_index_gap(quiz.compare_round(4))
            hard_ratios.append(gap / (n - 1))

        # Livello 0 garantisce coppie lontane in proporzione, livello 4 quasi adiacenti.
        self.assertGreater(sum(easy_ratios) / len(easy_ratios), sum(hard_ratios) / len(hard_ratios))
        self.assertGreaterEqual(min(easy_ratios), 0.6)
        self.assertLessEqual(max(hard_ratios), 0.2)

    def test_compare_round_never_loops_forever(self):
        """Guardia di non regressione: compare_round e order_round non devono
        più contenere un retry non limitato (bug che ha causato un hang reale
        in sessione, azzerato riscrivendo la selezione senza tentativo-ed-errore)."""
        import inspect

        from app import quiz

        self.assertNotIn("while True", inspect.getsource(quiz.compare_round))
        self.assertNotIn("while True", inspect.getsource(quiz.order_round))

    def test_compare_answer_flow(self):
        from app.data import get_indicator_year

        client = app.test_client()
        round_ = client.get("/api/game/compare/round?difficulty=0").get_json()
        indicator_id = round_["indicator"]["id"]
        year = round_["indicator"]["year"]
        key_a = round_["region_a"]["region_key"]
        key_b = round_["region_b"]["region_key"]
        values = {row["region_key"]: row["value"] for row in get_indicator_year(indicator_id, year)["values"]}
        winner = "region_a" if values[key_a] > values[key_b] else "region_b"
        loser = "region_b" if winner == "region_a" else "region_a"

        def answer(choice):
            return client.post("/api/game/compare/answer", json={
                "indicator_id": indicator_id, "year": year,
                "region_a_key": key_a, "region_b_key": key_b, "choice": choice,
            }).get_json()

        right = answer(winner)
        self.assertTrue(right["correct"])
        self.assertEqual(right["winner"], winner)
        self.assertEqual(right["region_a"]["value"], values[key_a])
        self.assertTrue(right["indicator"]["description"])
        self.assertTrue(right["indicator"]["source_url"].startswith("http"))
        self.assertTrue(right["indicator"]["source_label"])

        wrong = answer(loser)
        self.assertFalse(wrong["correct"])

        timeout = answer("timeout")
        self.assertFalse(timeout["correct"])
        self.assertEqual(timeout["winner"], winner)
        self.assertIsNotNone(timeout["region_b"]["value"])

    def test_compare_answer_rejects_invalid_input(self):
        client = app.test_client()
        round_ = client.get("/api/game/compare/round").get_json()
        base = {
            "indicator_id": round_["indicator"]["id"],
            "year": round_["indicator"]["year"],
            "region_a_key": round_["region_a"]["region_key"],
            "region_b_key": round_["region_b"]["region_key"],
        }

        for overrides in (
            {"choice": "boh"},
            {"choice": "region_a", "region_a_key": "atlantide"},
            {"choice": "region_a", "indicator_id": "9999999"},
            {"choice": "region_a", "region_b_key": base["region_a_key"]},
            {"choice": "region_a", "year": 1500},
        ):
            payload = {**base, **overrides}
            response = client.post("/api/game/compare/answer", json=payload)
            self.assertEqual(response.status_code, 400, payload)

        self.assertEqual(client.post("/api/game/compare/answer", json={}).status_code, 400)


class QuizOrderTest(unittest.TestCase):
    def test_order_page_responds_without_map(self):
        client = app.test_client()
        page = client.get("/quiz/ordina")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'id="order-root"', page.data)
        self.assertNotIn(b'id="game-map-frame"', page.data)

    def test_order_round_counts_and_no_value_leak(self):
        import json

        client = app.test_client()
        for count in (3, 5):
            response = client.get(f"/api/game/order/round?count={count}")
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertEqual(payload["count"], count)
            self.assertEqual(len(payload["regions"]), count)
            keys = [r["region_key"] for r in payload["regions"]]
            self.assertEqual(len(set(keys)), count)
            self.assertNotIn('"value"', json.dumps(payload))
            for field in ("source_label", "source_url"):
                self.assertIn(field, payload["indicator"])
            self.assertNotIn("description", payload["indicator"])

        for bad in ("2", "6", "x", ""):
            self.assertEqual(client.get(f"/api/game/order/round?count={bad}").status_code, 400, bad)

    def test_order_answer_perfect_reversed_and_partial(self):
        from app.data import get_indicator_year

        client = app.test_client()
        round_ = client.get("/api/game/order/round?count=3").get_json()
        indicator_id = round_["indicator"]["id"]
        year = round_["indicator"]["year"]
        keys = [r["region_key"] for r in round_["regions"]]
        values = {row["region_key"]: row["value"] for row in get_indicator_year(indicator_id, year)["values"]}
        perfect = sorted(keys, key=lambda key: values[key], reverse=True)

        def answer(order):
            return client.post("/api/game/order/answer", json={
                "indicator_id": indicator_id, "year": year, "region_keys": order,
            })

        full = answer(perfect).get_json()
        self.assertEqual(full["score"], 3)
        self.assertEqual(full["total"], 3)
        self.assertTrue(all(p["correct"] for p in full["positions"]))
        self.assertEqual([r["region_key"] for r in full["correct_order"]], perfect)
        self.assertTrue(full["indicator"]["description"])
        self.assertTrue(full["indicator"]["source_url"].startswith("http"))
        self.assertEqual(full["indicator"]["id"], indicator_id)

        reversed_resp = answer(list(reversed(perfect))).get_json()
        self.assertLess(reversed_resp["score"], 3)
        for pos in reversed_resp["positions"]:
            self.assertIsNotNone(pos["value"])
            self.assertGreaterEqual(pos["correct_position"], 1)
            self.assertLessEqual(pos["correct_position"], 3)

        # Credito parziale: scambiando solo le ultime due resta giusta la prima.
        swapped = [perfect[0], perfect[2], perfect[1]]
        partial = answer(swapped).get_json()
        self.assertEqual(partial["score"], 1)
        self.assertTrue(partial["positions"][0]["correct"])

    def test_order_answer_rejects_invalid_input(self):
        client = app.test_client()
        round_ = client.get("/api/game/order/round?count=3").get_json()
        indicator_id = round_["indicator"]["id"]
        year = round_["indicator"]["year"]
        keys = [r["region_key"] for r in round_["regions"]]

        def answer(payload):
            return client.post("/api/game/order/answer", json=payload)

        base = {"indicator_id": indicator_id, "year": year}
        self.assertEqual(answer({**base, "region_keys": [keys[0], keys[0], keys[1]]}).status_code, 400)
        self.assertEqual(answer({**base, "region_keys": ["atlantide", keys[0], keys[1]]}).status_code, 400)
        self.assertEqual(answer({**base, "region_keys": keys[:2]}).status_code, 400)
        self.assertEqual(answer({"indicator_id": "9999999", "year": year, "region_keys": keys}).status_code, 400)
        self.assertEqual(answer({}).status_code, 400)

    def test_sitemap_lists_quiz_pages(self):
        client = app.test_client()
        sitemap = client.get("/sitemap.xml").data
        self.assertIn(b"/quiz/chi-e-maggiore", sitemap)
        self.assertIn(b"/quiz/ordina", sitemap)


def game_region_keys():
    from app import profiles

    return [profiles.region_key_for(region) for region in REGION_ORDER]


if __name__ == "__main__":
    unittest.main()
