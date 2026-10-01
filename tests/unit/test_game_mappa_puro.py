"""Le funzioni pure di "Dov'è la provincia?" (`app/game_mappa.py`): nomi, fasce,
storia della sfida del giorno, esito e punteggio, distanza. Senza Flask e senza DB:
la chiave del seed e' sempre quella di sviluppo, passata esplicitamente."""

import os
import unittest
from datetime import date, timedelta
from unittest import mock

from app import game_daily, game_mappa
from app.game_mappa import (
    LEVELS,
    MAP_EPOCH,
    MIX,
    POINTS,
    QUESTIONS,
    WINDOW_DAYS,
    daily_provinces,
    display_name,
    outcome,
    pool,
    size_bands,
)

KEY = game_daily.CHIAVE_SVILUPPO
MONDAY = date(2026, 10, 5)
SUNDAY = date(2026, 10, 11)

# Il test d'oro. Le dieci province di tre giorni fissi, con la chiave di sviluppo, e
# un'impronta delle fasce. Se cambia, cambiano le sfide di tutti i giorni da
# `MAP_EPOCH` in poi, OGGI compreso, e chi sta giocando prende `token_invalid`. Se il
# cambio e' voluto (dati nuovi, `MIX`, finestra, regola delle fasce), `MAP_EPOCH` si
# porta al giorno del cambio e questi valori si riscrivono nello stesso commit.
GOLDEN_BANDS = {"italia": "91bd3cd8f69f", "regione": "f339cd83fbf8"}
GOLDEN = {
    (date(2026, 10, 5), "italia"): (
        "pavia", "bari", "salerno", "vicenza", "belluno", "modena", "ancona", "padova",
        "campobasso", "reggio-emilia"),
    (date(2026, 10, 5), "regione"): (
        "torino", "salerno", "belluno", "grosseto", "l-aquila", "bari", "teramo",
        "forli-cesena", "pesaro-e-urbino", "pordenone"),
    (date(2026, 10, 11), "italia"): (
        "bologna", "trapani", "pordenone", "rovigo", "rimini", "prato",
        "monza-e-della-brianza", "novara", "imperia", "pescara"),
    (date(2026, 10, 11), "regione"): (
        "palermo", "padova", "chieti", "avellino", "lucca", "brindisi", "vibo-valentia",
        "crotone", "milano", "imperia"),
    (date(2026, 12, 31), "italia"): (
        "modena", "alessandria", "palermo", "genova", "treviso", "verbano-cusio-ossola",
        "vercelli", "rimini", "biella", "ragusa"),
    (date(2026, 12, 31), "regione"): (
        "foggia", "verona", "siena", "trapani", "avellino", "pisa", "piacenza", "prato",
        "rimini", "como"),
}


def _province(key):
    return {p["key"]: p for p in game_daily.province_pool()}[key]


class NamesTest(unittest.TestCase):
    def test_aosta_is_shown_with_its_region(self):
        self.assertEqual(display_name(_province("aosta")), "Aosta (Valle d'Aosta)")

    def test_other_names_are_those_of_the_codes_file(self):
        self.assertEqual(display_name(_province("lecce")), "Lecce")
        self.assertEqual(display_name(_province("monza-e-della-brianza")), "Monza e della Brianza")

    def test_reggio_is_never_alone(self):
        names = [display_name(p) for p in game_daily.province_pool()]
        self.assertNotIn("Reggio", names)
        self.assertIn("Reggio Calabria", names)
        self.assertIn("Reggio Emilia", names)

    def test_static_list_has_107_provinces_in_alphabetical_order_with_official_forms(self):
        entries = game_mappa.static_list()
        self.assertEqual(len(entries), 107)
        self.assertEqual([e["name"] for e in entries], sorted((e["name"] for e in entries), key=str.casefold))
        official = {e["key"]: e["official_name"] for e in entries}
        self.assertEqual(official["bolzano"], "Bolzano/Bozen")
        self.assertEqual(official["reggio-emilia"], "Reggio nell'Emilia")
        self.assertEqual(official["aosta"], "Valle d'Aosta/Vallée d'Aoste")
        self.assertEqual(official["lecce"], "Lecce")
        for entry in entries:
            self.assertEqual(entry["path"], "/provincia/" + entry["key"])


class PoolAndBandsTest(unittest.TestCase):
    def test_sardinian_provinces_are_never_asked(self):
        sardinia = {p["key"] for p in game_daily.province_pool() if p["region"] == "Sardegna"}
        self.assertEqual(len(sardinia), 5)
        for level in LEVELS:
            self.assertFalse(sardinia & set(pool(level)), level)

    def test_pool_sizes(self):
        self.assertEqual(len(pool("italia")), 102)
        self.assertEqual(len(pool("regione")), 93)

    def test_region_level_only_regions_with_three_provinces(self):
        eligible = set(game_daily.regioni_idonee(3))
        for key in pool("regione"):
            self.assertIn(_province(key)["region"], eligible)
        self.assertNotIn("aosta", pool("regione"))
        self.assertNotIn("matera", pool("regione"))

    def test_bands_split_the_pool_in_thirds_from_large_to_small(self):
        areas = game_mappa._areas()
        for level, sizes in (("italia", [34, 34, 34]), ("regione", [31, 31, 31])):
            bands = size_bands(level)
            self.assertEqual([len(b) for b in bands], sizes)
            self.assertEqual(sorted(k for b in bands for k in b), sorted(pool(level)))
            for larger, smaller in zip(bands, bands[1:]):
                self.assertGreaterEqual(min(areas[k] for k in larger), max(areas[k] for k in smaller))


class DailyTest(unittest.TestCase):
    def test_ten_distinct_keys_from_the_pool(self):
        for level in LEVELS:
            for offset in range(14):
                keys = daily_provinces(MAP_EPOCH + timedelta(days=offset), level, KEY)
                self.assertEqual(len(keys), QUESTIONS)
                self.assertEqual(len(set(keys)), QUESTIONS)
                self.assertTrue(set(keys) <= set(pool(level)))

    def test_mix_follows_the_day_of_the_week(self):
        for day in (MONDAY, SUNDAY, MONDAY + timedelta(days=3)):
            counts = MIX[game_daily.DIFFICOLTA_SETTIMANA[day.weekday()]]
            for level in LEVELS:
                keys = daily_provinces(day, level, KEY)
                bands = size_bands(level)
                expected = [i for i, n in enumerate(counts) for _ in range(n)]
                found = [next(i for i, band in enumerate(bands) if k in band) for k in keys]
                self.assertEqual(found, expected, (day, level))
        self.assertEqual(MIX[game_daily.DIFFICOLTA_SETTIMANA[MONDAY.weekday()]], (6, 4, 0))
        self.assertEqual(MIX[game_daily.DIFFICOLTA_SETTIMANA[SUNDAY.weekday()]], (1, 3, 6))

    def test_deterministic_and_the_same_after_clearing_the_cache(self):
        before = daily_provinces(SUNDAY, "italia", KEY)
        game_mappa._history.cache_clear()
        self.assertEqual(daily_provinces(SUNDAY, "italia", KEY), before)

    def test_a_day_computed_cold_is_the_day_inside_a_longer_history(self):
        game_mappa._history.cache_clear()
        cold = daily_provinces(SUNDAY, "regione", KEY)
        longer = game_mappa._history(SUNDAY + timedelta(days=30), "regione", KEY)
        self.assertEqual(longer[(SUNDAY - MAP_EPOCH).days], cold)

    def test_another_key_and_another_level_give_another_challenge(self):
        self.assertNotEqual(daily_provinces(SUNDAY, "italia", KEY), daily_provinces(SUNDAY, "italia", "altra"))
        self.assertNotEqual(set(daily_provinces(SUNDAY, "italia", KEY)), set(daily_provinces(SUNDAY, "regione", KEY)))

    def test_no_province_comes_back_within_the_window_for_five_years(self):
        until = MAP_EPOCH + timedelta(days=5 * 365)
        for level in LEVELS:
            history = game_mappa._history(until, level, KEY)
            self.assertEqual(len(history), (until - MAP_EPOCH).days + 1)
            for i, picks in enumerate(history):
                recent = {k for previous in history[max(0, i - WINDOW_DAYS):i] for k in previous}
                self.assertFalse(recent & set(picks), (level, i))

    def test_a_day_before_the_epoch_still_has_a_challenge(self):
        keys = daily_provinces(MAP_EPOCH - timedelta(days=1), "italia", KEY)
        self.assertEqual(len(set(keys)), QUESTIONS)

    def test_the_seed_key_is_resolved_before_the_cache(self):
        daily_provinces(SUNDAY, "italia", KEY)
        game_daily.chiave_seed()  # in locale non solleva
        env = {k: v for k, v in os.environ.items() if k != "GAME_SEED_KEY"}
        env["K_SERVICE"] = "divarioitalia"
        with mock.patch.dict(os.environ, env, clear=True):
            game_mappa._history(SUNDAY, "italia", game_daily.CHIAVE_SVILUPPO)
            with self.assertRaises(game_daily.ChiaveSeedMancante):
                daily_provinces(SUNDAY, "italia")

    def test_unknown_level_raises(self):
        with self.assertRaises(ValueError):
            daily_provinces(SUNDAY, "europa", KEY)


class GoldenTest(unittest.TestCase):
    """Rende visibile ogni cambio che sposta le sfide (vedi `GOLDEN`)."""

    def test_bands_fingerprint(self):
        for level, fingerprint in GOLDEN_BANDS.items():
            self.assertEqual(game_mappa.bands_fingerprint(level), fingerprint, level)

    def test_three_fixed_days(self):
        for (day, level), keys in GOLDEN.items():
            self.assertEqual(daily_provinces(day, level, KEY), keys, (day, level))

    def test_epoch_and_constants(self):
        self.assertEqual(MAP_EPOCH, date(2026, 10, 1))
        self.assertEqual(WINDOW_DAYS, 6)
        self.assertEqual(MIX, {0: (6, 4, 0), 1: (4, 4, 2), 2: (3, 4, 3), 3: (2, 4, 4), 4: (1, 3, 6)})


class OutcomeTest(unittest.TestCase):
    def test_exact_region_miss(self):
        self.assertEqual(outcome("lecce", "lecce"), "exact")
        self.assertEqual(outcome("brindisi", "lecce"), "region")
        self.assertEqual(outcome("matera", "lecce"), "miss")

    def test_no_tolerance_beyond_the_region(self):
        self.assertEqual(outcome("gorizia", "trieste"), "region")
        self.assertEqual(outcome("milano", "monza-e-della-brianza"), "region")
        # Piacenza confina con Lodi ma e' in un'altra regione: zero punti.
        self.assertEqual(outcome("piacenza", "lodi"), "miss")

    def test_points(self):
        self.assertEqual(POINTS, {"exact": 2, "region": 1, "miss": 0})
        self.assertEqual(game_mappa.points_max("map"), 20)
        self.assertEqual(game_mappa.points_max("list"), 10)

    def test_list_outcome_is_the_region_of_the_province(self):
        self.assertEqual(game_mappa.list_outcome("puglia", "lecce"), "exact")
        self.assertEqual(game_mappa.list_outcome("basilicata", "lecce"), "miss")
        self.assertEqual(game_mappa.list_outcome("valle-d-aosta", "aosta"), "exact")


class QuestionTest(unittest.TestCase):
    def test_question_shapes(self):
        with mock.patch.object(game_daily, "chiave_seed", return_value=KEY):
            italia = game_mappa.question(SUNDAY, "italia", "map", 0)
            regione = game_mappa.question(SUNDAY, "regione", "map", 0)
            elenco = game_mappa.question(SUNDAY, "italia", "list", 0)
        self.assertEqual(set(italia), {"index", "name", "label"})
        self.assertEqual(italia["label"], f"Dov'è {italia['name']}?")
        self.assertEqual(set(regione), {"index", "name", "label", "region", "region_key"})
        self.assertEqual(regione["label"], f"Dov'è {regione['name']}? Si trova in {regione['region']}.")
        self.assertEqual(elenco["label"], f"In quale regione si trova {elenco['name']}?")
        for text in (italia["label"], regione["label"], elenco["label"]):
            for forbidden in ("—", "–", ";", "…"):
                self.assertNotIn(forbidden, text)


class DistanceTest(unittest.TestCase):
    def test_distance_is_an_estimate_from_the_chosen_to_the_right_one(self):
        km, direction = game_daily.distanza_km_direzione("brindisi", "lecce")
        self.assertTrue(20 <= km <= 60, km)
        self.assertIn(direction, ("S", "SE"))
        self.assertEqual(game_daily.distanza_km_direzione("lecce", "lecce"), (0, None))


if __name__ == "__main__":
    unittest.main()
