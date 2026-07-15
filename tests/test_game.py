import unittest
from datetime import date, timedelta

from app import app
from app.data import REGION_ORDER
from app import game


class GameTest(unittest.TestCase):
    def test_game_page_responds(self):
        client = app.test_client()
        page = client.get("/gioco")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'id="game-root"', page.data)
        self.assertIn(b'id="game-map-frame"', page.data)
        self.assertIn(b"Indovina la Regione", page.data)

    def test_game_page_has_explicit_index_header(self):
        client = app.test_client()
        page = client.get("/gioco")
        self.assertEqual(
            page.headers.get("X-Robots-Tag"),
            "index, follow, max-snippet:-1, max-image-preview:large",
        )

    def test_sitemap_lists_game_page(self):
        client = app.test_client()
        sitemap = client.get("/sitemap.xml")
        self.assertIn(b"/gioco", sitemap.data)

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
        for field in ("id", "name", "theme", "macro_area", "unit", "year", "value"):
            self.assertIn(field, first["clue"])
        # The mystery region itself never appears in the intro payload.
        self.assertNotIn("region", first)
        self.assertNotIn("region_key", first)
        self.assertNotIn("solution", first)

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
        self.assertEqual(len(wrong["feedback"]), 1)
        self.assertIn(wrong["feedback"][0]["comparison"], ("higher", "lower", "equal", "unknown"))
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


def game_region_keys():
    from app import profiles

    return [profiles.region_key_for(region) for region in REGION_ORDER]


if __name__ == "__main__":
    unittest.main()
