import unittest
import csv
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from unittest import mock

from app import app
from app.data import REGION_ORDER
from app import config, game, game_daily, quiz_tokens
from app.cache import cache
from app.game_daily import today_rome


def setUpModule():
    cache.delete("rl:ans:ip:127.0.0.1")


class CompareHelperTest(unittest.TestCase):
    def test_comparison_describes_the_guess_relative_to_the_mystery(self):
        # "higher" deve significare "il valore indovinato è più alto di quello
        # misterioso": il frontend mostra questo esito subito dopo il valore
        # del tentativo (vedi frontend/src/game/main.jsx), quindi il verso
        # deve riferirsi al tentativo, non al mistero.
        self.assertEqual(game._compare(mystery_value=10, guess_value=15), "higher")
        self.assertEqual(game._compare(mystery_value=15, guess_value=10), "lower")
        self.assertEqual(game._compare(mystery_value=10, guess_value=10), "equal")
        self.assertEqual(game._compare(mystery_value=10, guess_value=None), "unknown")
        self.assertEqual(game._compare(mystery_value=None, guess_value=10), "unknown")


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
        for href in (b"/quiz/indovina-la-regione", b"/quiz/chi-e-maggiore", b"/quiz/ordina", b"/quiz/province-italiane"):
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
            "id", "name", "theme", "macro_area", "unit", "description",
            "value_explanation", "reading", "year", "value", "rank",
            "region_count", "source_label", "source_url", "path",
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
        # Il verso riportato deve corrispondere al confronto reale fra il
        # valore del tentativo e quello (nascosto) della regione misteriosa.
        if entry["comparison"] != "unknown":
            clue = puzzle["clues"][0]
            mystery_value = clue["value"]
            guess_value = entry["guess_value"]
            if entry["comparison"] == "equal":
                self.assertAlmostEqual(guess_value, mystery_value)
            elif entry["comparison"] == "higher":
                self.assertGreater(guess_value, mystery_value)
            else:
                self.assertLess(guess_value, mystery_value)
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
        today = today_rome()

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

        today = today_rome()
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
        tomorrow = (today_rome() + timedelta(days=1)).isoformat()
        response = client.post("/api/game/guess", json={
            "puzzle_id": f"daily:{tomorrow}", "region_key": "lombardia", "attempt": 1,
        })
        self.assertEqual(response.status_code, 400)


class _OrologioFisso(datetime):
    """`datetime` con `now()` fissato alle 23:30 UTC del 30 settembre 2026,
    quando a Roma (CEST) e' gia' l'1 ottobre."""

    @classmethod
    def now(cls, tz=None):
        fisso = datetime(2026, 9, 30, 23, 30, tzinfo=timezone.utc)
        return fisso.astimezone(tz) if tz else fisso.replace(tzinfo=None)


class GiornoDiRomaTest(unittest.TestCase):
    """Fra le 22:00 e la mezzanotte UTC server e client concordano sul giorno:
    il server gira in UTC, il giocatore vive a Roma."""

    def setUp(self):
        patcher = mock.patch("app.game_daily.datetime", _OrologioFisso)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = app.test_client()

    def test_daily_e_il_giorno_di_roma(self):
        payload = self.client.get("/api/game/daily").get_json()
        self.assertEqual(payload["date"], "2026-10-01")
        self.assertEqual(payload["puzzle_id"], "daily:2026-10-01")
        self.assertEqual(payload["number"], game.puzzle_number(date(2026, 10, 1)))
        # La prossima sfida e' la mezzanotte di Roma del 2 ottobre: 22:00 UTC dell'1.
        self.assertEqual(payload["next_puzzle_at"], "2026-10-01T22:00:00+00:00")

    def test_archivio_e_guess_accettano_il_giorno_di_roma(self):
        self.assertEqual(self.client.get("/api/game/daily/2026-10-01").status_code, 200)
        self.assertEqual(self.client.get("/api/game/daily/2026-10-02").status_code, 404)
        giusto = self.client.post("/api/game/guess", json={
            "puzzle_id": "daily:2026-10-01", "region_key": "lombardia", "attempt": 1,
        })
        self.assertEqual(giusto.status_code, 200)
        futuro = self.client.post("/api/game/guess", json={
            "puzzle_id": "daily:2026-10-02", "region_key": "lombardia", "attempt": 1,
        })
        self.assertEqual(futuro.status_code, 400)

    def test_la_sfida_di_ieri_a_pagina_aperta_a_mezzanotte_e_410(self):
        """La pagina e' rimasta aperta oltre la mezzanotte di Roma: il client della sfida del
        giorno manda ancora `daily:ieri`. Il server lo dice (`puzzle_changed`) invece di
        valutare in silenzio un tentativo che non conta per nessuno."""
        ieri = {"puzzle_id": "daily:2026-09-30", "region_key": "lombardia", "attempt": 1}
        risposta = self.client.post("/api/game/guess", json={**ieri, "mode": "daily"})
        self.assertEqual(risposta.status_code, 410)
        self.assertEqual(risposta.get_json(), {"error": "puzzle_changed"})
        oggi = self.client.post("/api/game/guess", json={
            "puzzle_id": "daily:2026-10-01", "region_key": "lombardia", "attempt": 1, "mode": "daily",
        })
        self.assertEqual(oggi.status_code, 200)

    def test_l_archivio_e_i_client_di_prima_continuano_a_giocare_le_sfide_passate(self):
        """Il contratto non si restringe: senza `mode` (un bundle vecchio) o con `mode:
        "archive"` una daily passata si valuta come prima."""
        ieri = {"puzzle_id": "daily:2026-09-30", "region_key": "lombardia", "attempt": 1}
        for corpo in (ieri, {**ieri, "mode": "archive"}, {**ieri, "mode": "practice"}):
            with self.subTest(corpo=corpo):
                self.assertEqual(self.client.post("/api/game/guess", json=corpo).status_code, 200)

    def test_il_410_non_apre_una_porta_sul_futuro_ne_sull_input_rotto(self):
        futuro = self.client.post("/api/game/guess", json={
            "puzzle_id": "daily:2026-10-02", "region_key": "lombardia", "attempt": 1, "mode": "daily",
        })
        self.assertEqual(futuro.status_code, 400)
        rotto = self.client.post("/api/game/guess", json={
            "puzzle_id": "daily:2026-09-30", "region_key": "atlantide", "attempt": 1, "mode": "daily",
        })
        self.assertEqual(rotto.status_code, 400)

    def test_la_lista_dell_archivio_parte_da_ieri_di_roma(self):
        giorni = [p["date"] for p in self.client.get("/api/game/archive").get_json()["puzzles"]]
        self.assertEqual(giorni[0], "2026-09-30")
        self.assertNotIn("2026-10-01", giorni)

    def test_le_sfide_a_livelli_sono_quelle_di_roma(self):
        for gioco in ("compare", "order"):
            payload = self.client.get(f"/api/game/{gioco}/daily").get_json()
            self.assertEqual(payload["date"], "2026-10-01", gioco)
            self.assertEqual(payload["puzzle_id"], "daily:2026-10-01", gioco)
            self.assertEqual(payload["next_puzzle_at"], "2026-10-01T22:00:00+00:00", gioco)

    def test_le_vecchie_soluzioni_non_cambiano_col_passaggio_al_giorno_di_roma(self):
        # Il numero della sfida e la regione dipendono solo dalla data.
        self.assertEqual(game.puzzle_number(game.GAME_EPOCH), 1)
        self.assertEqual(game.region_for_puzzle("daily:2026-07-15"), "Lazio")


class SoluzioniPrimaDelCutoverTest(unittest.TestCase):
    def test_le_regioni_servite_dal_codice_di_prima_non_cambiano(self):
        """Le soluzioni da GAME_EPOCH a oggi, calcolate con la formula
        originale, coincidono con quelle del codice nuovo."""
        import random

        giorno = game.GAME_EPOCH
        # Dal cutover in poi le soluzioni escono dall'HMAC, e la formula di prima non vale.
        ultimo = min(today_rome(), game_daily.SEED_CUTOVER - timedelta(days=1))
        while giorno <= ultimo:
            ciclo, pos = divmod((giorno - game.GAME_EPOCH).days, len(REGION_ORDER))
            regioni = list(REGION_ORDER)
            random.Random(f"divario-regioni-cycle-{ciclo}").shuffle(regioni)
            puzzle_id, _ = game.daily_puzzle_id(giorno)
            self.assertEqual(game.region_for_puzzle(puzzle_id), regioni[pos], giorno)
            giorno += timedelta(days=1)


class ElencoGiocoTest(unittest.TestCase):
    def test_integrita_del_csv(self):
        righe = game_daily.game_indicators()
        self.assertGreaterEqual(len(righe), 60)
        self.assertLessEqual(len(righe), 100)
        ids = [r["id"] for r in righe]
        self.assertEqual(len(ids), len(set(ids)))
        from app import bes_data, quiz

        pool = {p["id"] for p in quiz._quiz_indicators()}
        manifesto = bes_data.get_bes_manifest("provincia")
        for r in righe:
            self.assertTrue(r["unit"].strip(), r["id"])
            self.assertTrue(r["name"].strip(), r["id"])
            self.assertTrue(r["regione"] or r["provincia"], r["id"])
            self.assertFalse(set(r["name"] + r["unit"] + r["note"]) & set(";\u2014\u2013\u2026"), r["id"])
            if r["regione"]:
                self.assertIn(r["id"], pool, r["id"])
            if r["provincia"]:
                info = manifesto.get(game_daily.provincial_id(r["id"]))
                self.assertIsNotNone(info, r["id"])
                self.assertEqual(info["coverage_latest"], 1.0, r["id"])
                self.assertGreaterEqual(info["year_max"], 2022, r["id"])

    def test_il_flag_provincia_segue_il_manifesto(self):
        """`n_province_latest == 107` e `year_max >= 2022`, come dice la regola
        di prodotto, guardando il manifesto grezzo."""
        with open("app/static/data/province_manifest.csv", encoding="utf-8", newline="") as handle:
            manifesto = {r["id"]: r for r in csv.DictReader(handle, delimiter=";")}
        for r in game_daily.game_indicators():
            if r["provincia"]:
                riga = manifesto[game_daily.provincial_id(r["id"])]
                self.assertEqual(int(riga["n_province_latest"]), 107, r["id"])
                self.assertGreaterEqual(int(riga["year_max"]), 2022, r["id"])


class SfidaDelGiornoLivelliTest(unittest.TestCase):
    CHIAVE = "chiave-di-prova-per-i-test"

    def setUp(self):
        patcher = mock.patch.dict(os.environ, {"GAME_SEED_KEY": self.CHIAVE})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.giorni = [date(2026, 10, 1) + timedelta(days=i) for i in range(7)]  # giovedi' + una settimana

    def test_compare_ha_dieci_coppie_valide_a_ogni_livello_e_giorno(self):
        for giorno in self.giorni:
            for livello in game_daily.LEVELS:
                sfida = game_daily.daily_compare(giorno, livello)
                self.assertEqual(len(sfida["pairs"]), 10, (giorno, livello))
                for coppia in sfida["pairs"]:
                    self.assertNotEqual(coppia["a"]["key"], coppia["b"]["key"])
                    self.assertTrue(coppia["indicator"]["unit"])
                    if livello == "stessa_regione":
                        self.assertEqual(coppia["a"]["region"], sfida["region"])
                        self.assertEqual(coppia["b"]["region"], sfida["region"])

    def test_order_ha_cinque_territori_distinti_a_ogni_livello_e_giorno(self):
        for giorno in self.giorni:
            for livello in game_daily.LEVELS:
                sfida = game_daily.daily_order(giorno, livello)
                chiavi = [t["key"] for t in sfida["territories"]]
                self.assertEqual(len(set(chiavi)), 5, (giorno, livello))
                if livello == "stessa_regione":
                    self.assertIn(sfida["region"], game_daily.eligible_regions(5))
                    self.assertTrue(all(t["region"] == sfida["region"] for t in sfida["territories"]))

    def test_ogni_regione_idonea_e_ogni_livello_hanno_indicatori_a_sufficienza(self):
        """La chiave di produzione decide quale regione esce ogni giorno: nessuna
        regione idonea puo' restare senza indicatori, o quel giorno sarebbe un 500."""
        rng = game_daily.random.Random(0)
        giorno = self.giorni[0]
        for gioco, minimo, distinti in (("compare", game_daily.MIN_PROVINCES_COMPARE, 2), ("order", game_daily.MIN_PROVINCES_ORDER, 5)):
            for regione in game_daily.eligible_regions(minimo):
                utili = game_daily._candidates(
                    "stessa_regione", "province", lambda r, regione=regione: r["region"] == regione, distinti, rng
                )
                soglia = game_daily.COMPARE_PAIRS if gioco == "compare" else 1
                self.assertGreaterEqual(len(utili), soglia, (gioco, regione))
            for livello, ambito in (("regioni", "regioni"), ("province", "province")):
                utili = game_daily._candidates(livello, ambito, lambda r: True, distinti, rng)
                self.assertGreaterEqual(len(utili), 10, (gioco, livello))
        self.assertTrue(giorno)

    def test_ogni_regione_idonea_esce_davvero_come_sfida(self):
        """Forza ogni regione idonea come regione del giorno e costruisce il payload."""
        for gioco, minimo, funzione in (
            ("compare", game_daily.MIN_PROVINCES_COMPARE, game_daily.daily_compare),
            ("order", game_daily.MIN_PROVINCES_ORDER, game_daily.daily_order),
        ):
            for regione in game_daily.eligible_regions(minimo):
                # La sfida e' in cache per (giorno, livello, chiave): con la regione
                # forzata va ricalcolata, e poi tolta, perche' la cache non la tenga.
                game_daily._compare.cache_clear()
                game_daily._order.cache_clear()
                with mock.patch.object(game_daily, "eligible_regions", lambda minimo, r=regione: [r]):
                    sfida = funzione(self.giorni[0], "stessa_regione")
                game_daily._compare.cache_clear()
                game_daily._order.cache_clear()
                self.assertEqual(sfida["region"], regione, gioco)
                elementi = sfida["pairs"] if gioco == "compare" else sfida["territories"]
                self.assertTrue(elementi, (gioco, regione))

    def test_compare_stessa_regione_usa_regioni_con_almeno_tre_province(self):
        for giorno in self.giorni:
            self.assertIn(game_daily.daily_compare(giorno, "stessa_regione")["region"], game_daily.eligible_regions(3))

    def test_le_sfide_sono_deterministiche_e_dipendono_dalla_chiave(self):
        giorno = self.giorni[0]
        for funzione in (game_daily.daily_compare, game_daily.daily_order):
            self.assertEqual(funzione(giorno, "province"), funzione(giorno, "province"))
            self.assertNotEqual(funzione(giorno, "province"), funzione(giorno, "province", key="altra-chiave"))
            self.assertNotEqual(funzione(giorno, "regioni"), funzione(giorno + timedelta(days=1), "regioni"))

    def test_i_payload_non_rivelano_valori(self):
        for livello in game_daily.LEVELS:
            for sfida in (
                game_daily.daily_compare(self.giorni[0], livello),
                game_daily.daily_order(self.giorni[0], livello),
            ):
                testo = json.dumps(sfida)
                self.assertNotIn('"value"', testo)
                self.assertNotIn('"rank"', testo)
                self.assertNotIn('"solution"', testo)

    def test_la_difficolta_cresce_da_lunedi_a_domenica(self):
        lunedi, domenica = date(2026, 10, 5), date(2026, 10, 11)
        self.assertEqual((lunedi.weekday(), domenica.weekday()), (0, 6))
        self.assertEqual(game_daily.daily_compare(lunedi, "regioni")["difficulty"], 0)
        self.assertEqual(game_daily.daily_compare(domenica, "regioni")["difficulty"], 4)
        self.assertEqual(list(game_daily.WEEKDAY_DIFFICULTY), sorted(game_daily.WEEKDAY_DIFFICULTY))

        def rapporti(giorno, livello):
            ritorno = []
            for coppia in game_daily.daily_compare(giorno, livello)["pairs"]:
                ind = next(i for i in game_daily.game_indicators() if i["id"] == coppia["indicator"]["id"])
                ambito = "regioni" if livello == "regioni" else "province"
                _, righe = game_daily._indicator_rows(ind, ambito)
                distinti = sorted({r["value"] for r in righe}, reverse=True)
                valori = {r["key"]: r["value"] for r in righe}
                gap = abs(distinti.index(valori[coppia["a"]["key"]]) - distinti.index(valori[coppia["b"]["key"]]))
                ritorno.append(gap / (len(distinti) - 1))
            return ritorno

        for livello in ("regioni", "province"):
            for r in rapporti(lunedi, livello):
                self.assertGreaterEqual(r, 0.5, livello)
            for r in rapporti(domenica, livello):
                self.assertLessEqual(r, 0.25, livello)

    def test_rotte_giornaliere(self):
        client = app.test_client()
        for gioco, chiave in (("compare", "pairs"), ("order", "territories")):
            risposta = client.get(f"/api/game/{gioco}/daily?level=province")
            self.assertEqual(risposta.status_code, 200)
            payload = risposta.get_json()
            self.assertEqual(payload["puzzle_id"], f"daily:{today_rome().isoformat()}")
            self.assertEqual(payload["level"], "province")
            self.assertTrue(payload["next_puzzle_at"].endswith("+00:00"))
            self.assertIn(chiave, payload)
            self.assertEqual(client.get(f"/api/game/{gioco}/daily").get_json()["level"], "regioni")
            self.assertEqual(client.get(f"/api/game/{gioco}/daily?level=pianeti").status_code, 400)
            # Nessuna data a scelta del client: il parametro non esiste.
            self.assertEqual(client.get(f"/api/game/{gioco}/daily?date=2030-01-01").get_json()["date"], today_rome().isoformat())


class PaginaProvinciaTest(unittest.TestCase):
    def test_pagina_risponde_con_un_solo_h1_e_canonical(self):
        client = app.test_client()
        pagina = client.get("/quiz/indovina-la-provincia")
        self.assertEqual(pagina.status_code, 200)
        html = pagina.get_data(as_text=True)
        self.assertEqual(len(re.findall(r"<h1[\s>]", html)), 1)
        self.assertIn(f'<link rel="canonical" href="{config.SITE_URL}/quiz/indovina-la-provincia"', html)
        self.assertIn('id="game-root"', html)
        self.assertIn("province italiane", html)
        giochi = [
            json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        ]
        gioco = next(d for d in giochi if d.get("@type") == "Game")
        self.assertEqual(gioco["creator"]["name"], "Divario Italia")

    def test_pagina_e_in_sitemap_con_priorita(self):
        sitemap = app.test_client().get("/sitemap.xml").get_data(as_text=True)
        self.assertRegex(
            sitemap,
            re.escape(f"<loc>{config.SITE_URL}/quiz/indovina-la-provincia</loc>") + r"\s*(?:<lastmod>[^<]*</lastmod>\s*)?<priority>0.7</priority>",
        )

    def test_page_type_game(self):
        from app import page_types

        self.assertEqual(page_types.page_type("/quiz/indovina-la-provincia"), "game")


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
        # La difficolta' la decide la serie del token, non la query.
        state = quiz_tokens.new_state("compare")
        state["s"] = 6
        response = client.get("/api/game/compare/round?token=" + quiz_tokens.sign_state(state))
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        for field in (
            "id", "name", "theme", "macro_area", "unit", "year",
            "source_label", "source_url", "description", "value_explanation", "path",
        ):
            self.assertIn(field, payload["indicator"])
        self.assertTrue(payload["indicator"]["source_url"].startswith("http"))
        self.assertEqual(payload["difficulty"], 2)
        self.assertNotEqual(payload["region_a"]["region_key"], payload["region_b"]["region_key"])
        self.assertNotIn('"value"', json.dumps(payload))
        # La spiegazione non rivela i valori e accompagna subito la domanda.
        self.assertTrue(payload["indicator"]["description"])
        self.assertTrue(payload["indicator"]["value_explanation"])

    def test_compare_rounds_use_core_indicators_with_distinct_values(self):
        from app import quiz
        from app.data import get_catalog
        from app import profiles

        core_ids = {item["id"] for item in get_catalog()["indicators"] if profiles.is_core(item)}
        core_ids.update(item["id"] for item in quiz._bes_quiz_indicators())
        core_ids.update(item["id"] for item in quiz._multiscopo_quiz_indicators())
        core_ids.update(item["id"] for item in quiz._eurostat_quiz_indicators())
        for _ in range(40):
            round_ = quiz.compare_round(4)
            self.assertIn(round_["indicator"]["id"], core_ids)
            payload = quiz._quiz_indicator_payload(
                round_["indicator"]["id"], round_["indicator"]["year"]
            )
            values = {row["region_key"]: row["value"] for row in payload["values"]}
            value_a = values[round_["region_a"]["region_key"]]
            value_b = values[round_["region_b"]["region_key"]]
            self.assertNotEqual(value_a, value_b)

    def test_compare_difficulty_narrows_value_gap(self):
        from app import quiz
        def value_index_gap(round_):
            # Distanza tra i due valori nella lista dei valori DISTINTI
            # dell'indicatore (non il rank grezzo, che con i pareggi non è
            # un indice affidabile di quanto le due regioni siano vicine).
            payload = quiz._quiz_indicator_payload(
                round_["indicator"]["id"], round_["indicator"]["year"]
            )
            distinct = sorted({row["value"] for row in payload["values"]}, reverse=True)
            values = {row["region_key"]: row["value"] for row in payload["values"]}
            idx_a = distinct.index(values[round_["region_a"]["region_key"]])
            idx_b = distinct.index(values[round_["region_b"]["region_key"]])
            return abs(idx_a - idx_b), len(distinct)

        easy_ratios, hard_ratios = [], []
        for _ in range(120):
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
        from app import quiz

        client = app.test_client()

        def answer(pick):
            """Un round nuovo senza timer (un `timeout` subito vale) e la risposta col
            suo token: senza un round legato la risposta e' un 400."""
            round_ = client.get("/api/game/compare/round?difficulty=0&timer=0").get_json()
            indicator_id, year = round_["indicator"]["id"], round_["indicator"]["year"]
            key_a, key_b = round_["region_a"]["region_key"], round_["region_b"]["region_key"]
            values = {
                row["region_key"]: row["value"]
                for row in quiz._quiz_indicator_payload(indicator_id, year)["values"]
            }
            winner = "region_a" if values[key_a] > values[key_b] else "region_b"
            loser = "region_b" if winner == "region_a" else "region_a"
            choice = {"winner": winner, "loser": loser, "timeout": "timeout"}[pick]
            body = client.post("/api/game/compare/answer", json={
                "indicator_id": indicator_id, "year": year, "token": round_["token"],
                "region_a_key": key_a, "region_b_key": key_b, "choice": choice,
            }).get_json()
            return body, winner, values[key_a]

        right, winner, value_a = answer("winner")
        self.assertTrue(right["correct"])
        self.assertEqual(right["winner"], winner)
        self.assertEqual(right["region_a"]["value"], value_a)
        self.assertTrue(right["indicator"]["description"])
        self.assertTrue(right["indicator"]["value_explanation"])
        self.assertTrue(right["indicator"]["source_url"].startswith("http"))
        self.assertTrue(right["indicator"]["source_label"])

        wrong, _, _ = answer("loser")
        self.assertFalse(wrong["correct"])

        timeout, winner, _ = answer("timeout")
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
            "token": round_["token"],
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
            self.assertTrue(payload["indicator"]["description"])
            self.assertTrue(payload["indicator"]["value_explanation"])

        for bad in ("2", "6", "x", ""):
            self.assertEqual(client.get(f"/api/game/order/round?count={bad}").status_code, 400, bad)

    def test_order_answer_perfect_reversed_and_partial(self):
        from app import quiz

        client = app.test_client()

        def answer(arrange):
            """Un round nuovo e la risposta col suo token, nell'ordine che `arrange`
            ricava da quello giusto: un round si risponde una volta sola."""
            round_ = client.get("/api/game/order/round?count=3").get_json()
            indicator_id = round_["indicator"]["id"]
            year = round_["indicator"]["year"]
            keys = [r["region_key"] for r in round_["regions"]]
            values = {
                row["region_key"]: row["value"]
                for row in quiz._quiz_indicator_payload(indicator_id, year)["values"]
            }
            perfect = sorted(keys, key=lambda key: values[key], reverse=True)
            body = client.post("/api/game/order/answer", json={
                "indicator_id": indicator_id, "year": year, "region_keys": arrange(perfect),
                "token": round_["token"],
            }).get_json()
            return body, perfect, indicator_id

        full, perfect, indicator_id = answer(lambda perfect: perfect)
        self.assertEqual(full["score"], 3)
        self.assertEqual(full["total"], 3)
        self.assertTrue(all(p["correct"] for p in full["positions"]))
        self.assertEqual([r["region_key"] for r in full["correct_order"]], perfect)
        self.assertTrue(full["indicator"]["description"])
        self.assertTrue(full["indicator"]["value_explanation"])
        self.assertTrue(full["indicator"]["source_url"].startswith("http"))
        self.assertEqual(full["indicator"]["id"], indicator_id)

        reversed_resp, _, _ = answer(lambda perfect: list(reversed(perfect)))
        self.assertLess(reversed_resp["score"], 3)
        for pos in reversed_resp["positions"]:
            self.assertIsNotNone(pos["value"])
            self.assertGreaterEqual(pos["correct_position"], 1)
            self.assertLessEqual(pos["correct_position"], 3)

        # Credito parziale: scambiando solo le ultime due resta giusta la prima.
        partial, _, _ = answer(lambda perfect: [perfect[0], perfect[2], perfect[1]])
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

        base = {"indicator_id": indicator_id, "year": year, "token": round_["token"]}
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
        self.assertIn(b"/quiz/province-italiane", sitemap)


class IndizioCollegatoTest(unittest.TestCase):
    """Il nome dell'indizio porta alla scheda dell'indicatore anche durante la
    partita, non solo nel recap di fine partita."""

    def test_clue_fields_espone_il_link_canonico(self):
        from app import profiles

        puzzle = game.build_puzzle("daily:2026-08-01")
        self.assertEqual(len(puzzle["clues"]), 6)
        for clue in puzzle["clues"]:
            self.assertEqual(clue["path"], profiles.indicator_path(clue["id"], clue["name"]))
            self.assertTrue(clue["path"].startswith("/indicatore/"), clue["path"])

    def test_il_primo_indizio_e_il_successivo_portano_path(self):
        client = app.test_client()
        daily = client.get("/api/game/daily").get_json()
        self.assertTrue(daily["clue"]["path"].startswith("/indicatore/"))
        sbagliata = next(k for k in game_region_keys() if k != game.build_puzzle(daily["puzzle_id"])["region_key"])
        risposta = client.post("/api/game/guess", json={
            "puzzle_id": daily["puzzle_id"], "region_key": sbagliata, "attempt": 1,
        }).get_json()
        self.assertTrue(risposta["next_clue"]["path"].startswith("/indicatore/"))
        self.assertEqual(risposta["recap"], None)

    def test_il_recap_passa_i_testi_di_che_cosa_misura(self):
        puzzle = game.build_puzzle("daily:2026-08-01")
        for clue in puzzle["clues"]:
            riga = game._recap_entry(clue)
            for campo in ("description", "value_explanation", "reading"):
                self.assertIn(campo, riga)
            self.assertTrue(riga["description"], clue["id"])


@unittest.skipUnless(shutil.which("node"), "serve node per provare la logica della serie")
class SerieAGiorniTest(unittest.TestCase):
    """La logica pura di Indovina (serie a giorni, messaggi di Provincia, rete) sta in `guess/*.js`
    e la provano i `guess/*.test.mjs` con `node --test`."""

    def test_serie_js(self):
        prove = sorted((Path(__file__).resolve().parents[2] / "frontend" / "src" / "game" / "guess").glob("*.test.mjs"))
        self.assertIn("provincia.test.mjs", {p.name for p in prove})
        esito = subprocess.run(
            ["node", "--test", *map(str, prove)], capture_output=True, text=True, timeout=60, check=False
        )
        self.assertEqual(esito.returncode, 0, esito.stdout + esito.stderr)


def game_region_keys():
    from app import profiles

    return [profiles.region_key_for(region) for region in REGION_ORDER]


if __name__ == "__main__":
    unittest.main()
