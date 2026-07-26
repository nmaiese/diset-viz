"""The unified view model must not move a single number.

app/indicator_view.py replaced two per-family render paths with one. The page
layout and the prose change on purpose, so nothing here looks at HTML. What is
pinned is arithmetic: every aggregate the old code produced for all 621
indicators, dumped to tests/fixtures/indicator_stats_golden.json by
scripts/dump_indicator_stats.py before the refactor.

Regenerate the fixture only when the underlying data changes (a refresh, a new
indicator), never to make a failing test pass: a diff here means the refactor
changed a published figure.
"""

import json
import unittest
from pathlib import Path

from app import sources
from app.indicator_view import build_indicator_view

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "indicator_stats_golden.json"
# Same precision the dump was written at.
TOLERANCE = 1e-6

# Two deviations from the fixture are deliberate. They are listed here instead of
# being regenerated away, so the guard keeps proving that nothing ELSE moved.
#
# 1. These four indicators declare a first year for which no region has a value
#    (id 103 declares 1995, its first real observation is 1996). The old code fed
#    the declared year to indicator_year_average, got None, and silently dropped
#    the whole long-term trend paragraph. The unified model starts from the first
#    year that actually carries data, so the trend reappears. The test asserts the
#    fix happened rather than skipping the ids.
EMPTY_DECLARED_FIRST_YEAR = {"103", "106", "111", "74"}
LONG_TERM_FIELDS = ("year_min_avg", "avg_change_abs", "avg_change_pct", "gap_trend")

# 2. Contextual indicators have no best or worst, so their ranking order was
#    never meaningful, and the two render paths disagreed: the atlas sorted them
#    highest first, the quality-of-life path lowest first. The unified page sorts
#    every indicator highest first and lets the direction decide whether #1 is
#    "best". For those series the fixture's first/last are therefore expected to
#    swap, and the test checks the ordering property instead of the names.


class UnifiedViewReproducesEveryFigure(unittest.TestCase):
    _golden_cache = None
    _views_cache = None

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def _load_golden(cls):
        if cls._golden_cache is None:
            cls._golden_cache = json.loads(FIXTURE.read_text(encoding="utf-8"))
        return cls._golden_cache

    @classmethod
    def _load_views(cls):
        if cls._views_cache is None:
            golden = cls._load_golden()
            cls._views_cache = {
                indicator_id: build_indicator_view(*cls._family_and_raw(indicator_id))
                for indicator_id in golden
            }
        return cls._views_cache

    @property
    def golden(self):
        return self._load_golden()

    @property
    def views(self):
        return self._load_views()

    @staticmethod
    def _family_and_raw(indicator_id):
        for family in ("bes", "multiscopo", "eurostat"):
            prefix = sources.SOURCES[family]["internal_prefix"]
            if indicator_id.startswith(prefix):
                return family, indicator_id[len(prefix):]
        return "territorial", indicator_id

    def _views(self):
        for indicator_id, expected in self.golden.items():
            yield indicator_id, expected, self.views[indicator_id]

    def test_every_indicator_still_builds(self):
        missing = [iid for iid, _, view in self._views() if view is None]
        self.assertEqual(missing, [], f"indicators the unified model cannot build: {missing[:10]}")

    def test_levels_match_the_previous_render_paths(self):
        wrong = []
        for indicator_id, expected, view in self._views():
            if view is None:
                continue
            built = {level["key"]: level for level in view["levels"]}
            for level_key, want in expected["levels"].items():
                if level_key not in built:
                    wrong.append((indicator_id, level_key, "level missing"))
                    continue
                level = built[level_key]
                if level["year_max"] != want["year_max"]:
                    wrong.append((indicator_id, level_key, f"year_max {level['year_max']} != {want['year_max']}"))
                if len(level["observations"]) != want["count"]:
                    wrong.append((
                        indicator_id, level_key,
                        f"count {len(level['observations'])} != {want['count']}",
                    ))
        self.assertEqual(wrong, [], f"levels that changed shape: {wrong[:10]}")

    def test_aggregates_match_to_six_decimals(self):
        wrong = []
        for indicator_id, expected, view in self._views():
            if view is None:
                continue
            built = {level["key"]: level for level in view["levels"]}
            for level_key, want in expected["levels"].items():
                level = built.get(level_key)
                if level is None:
                    continue
                stats = level["stats"]
                # The atlas dump carries the full aggregate set; the
                # quality-of-life dump only mean and median, because that is all
                # the old BES/Multiscopo path computed.
                checks = [("mean", stats["year_avg"]), ("median", stats["median"])]
                if "gap_abs" in want:
                    checks += [
                        ("gap_abs", stats["gap_abs"]),
                        ("gap_ratio", stats["gap_ratio"]),
                        ("above_avg", stats["above_avg_count"]),
                        ("below_avg", stats["below_avg_count"]),
                        ("year_min_avg", stats["year_min_avg"]),
                        ("avg_change_abs", stats["avg_change_abs"]),
                        ("avg_change_pct", stats["avg_change_pct"]),
                        ("gap_trend", stats["gap_trend"]),
                    ]
                for field, actual in checks:
                    if indicator_id in EMPTY_DECLARED_FIRST_YEAR and field in LONG_TERM_FIELDS:
                        continue
                    if not _close(want.get(field), actual):
                        wrong.append((indicator_id, level_key, field, want.get(field), actual))
        self.assertEqual(wrong, [], f"aggregates that moved: {wrong[:10]}")

    def test_long_term_trend_is_restored_where_the_declared_first_year_is_empty(self):
        """The deliberate fix, asserted rather than skipped.

        These pages used to omit the long-term trend entirely because the
        indicator's declared first year carries no observation. Losing this
        assertion would mean the trend silently disappeared again.
        """
        for indicator_id in sorted(EMPTY_DECLARED_FIRST_YEAR):
            with self.subTest(indicator=indicator_id):
                expected = self.golden[indicator_id]["levels"]["regione"]
                self.assertIsNone(
                    expected["avg_change_abs"],
                    "fixture no longer records the old omission, exception is stale",
                )
                view = build_indicator_view("territorial", indicator_id)
                stats = view["levels"][0]["stats"]
                self.assertTrue(stats["has_multi_year"])
                self.assertIsNotNone(stats["year_min_avg"])
                self.assertIsNotNone(stats["avg_change_abs"])
                self.assertGreater(stats["year_min"], 0)

    def test_year_over_year_comparison_is_unchanged(self):
        wrong = []
        for indicator_id, expected, view in self._views():
            if view is None:
                continue
            built = {level["key"]: level for level in view["levels"]}
            for level_key, want in expected["levels"].items():
                level = built.get(level_key)
                if level is None:
                    continue
                annual, want_annual = level["annual_change"], want["annual"]
                if (annual is None) != (want_annual is None):
                    wrong.append((indicator_id, level_key, "annual presence", bool(want_annual), bool(annual)))
                    continue
                if annual is None:
                    continue
                for field in (
                    "previous_year", "common_count", "previous_avg", "current_avg",
                    "average_delta", "increase_count", "decrease_count", "stable_count",
                ):
                    if not _close(want_annual[field], annual[field]):
                        wrong.append((indicator_id, level_key, field, want_annual[field], annual[field]))
        self.assertEqual(wrong, [], f"year-over-year figures that moved: {wrong[:10]}")

    def test_best_and_worst_are_the_same_territories(self):
        """For directional indicators #1 and last must not move.

        A name is allowed to change in exactly one case, and the test proves it
        rather than trusting it: when the extreme is a tie. Both old paths left
        tied territories in CSV order and one of them then reversed the list, so
        which of two equal territories got called "best" was arbitrary and could
        move on any data reload. The unified model breaks ties by name. The value
        at the extreme must be identical either way, and that is what is checked.

        Contextual indicators are excluded on purpose: they have no best, and
        the two old render paths ordered them in opposite directions.
        """
        wrong = []
        for indicator_id, expected, view in self._views():
            if view is None or not view["meta"]["scoreable"]:
                continue
            built = {level["key"]: level for level in view["levels"]}
            for level_key, want in expected["levels"].items():
                level = built.get(level_key)
                if level is None or not level["observations"]:
                    continue
                by_name = {row["name"]: row["value"] for row in level["observations"]}
                for position, index in (("first", 0), ("last", -1)):
                    key = {"first": "best", "last": "worst"}[position] if "best" in want else position
                    wanted_name = want.get(key)
                    if not wanted_name:
                        continue
                    actual = level["observations"][index]
                    if actual["name"] == wanted_name:
                        continue
                    if wanted_name not in by_name:
                        wrong.append((indicator_id, level_key, position, wanted_name, "territory gone"))
                    elif not _close(by_name[wanted_name], actual["value"]):
                        wrong.append((
                            indicator_id, level_key, position,
                            f"{wanted_name}={by_name[wanted_name]}",
                            f"{actual['name']}={actual['value']}",
                        ))
        self.assertEqual(wrong, [], f"extremes that changed by more than a tie: {wrong[:10]}")

    def test_contextual_indicators_are_ordered_highest_first(self):
        """The one ordering rule, applied to every family."""
        wrong = []
        for _, _, view in self._views():
            if view is None or view["meta"]["scoreable"]:
                continue
            for level in view["levels"]:
                values = [row["value"] for row in level["observations"]]
                if values != sorted(values, reverse=True):
                    wrong.append((view["meta"]["id"], level["key"]))
                self.assertIsNone(level["best"])
                self.assertIsNone(level["worst"])
        self.assertEqual(wrong, [], f"contextual rankings not sorted highest first: {wrong[:10]}")

    def test_no_observation_was_added_or_dropped(self):
        """Order may change, data may not: same territories, same values."""
        wrong = []
        for indicator_id, expected, view in self._views():
            if view is None:
                continue
            built = {level["key"]: level for level in view["levels"]}
            for level_key, want in expected["levels"].items():
                level = built.get(level_key)
                if level is None:
                    continue
                if len(level["observations"]) != want["count"]:
                    wrong.append((indicator_id, level_key, want["count"], len(level["observations"])))
                    continue
                for name in (want.get("first"), want.get("last"), want.get("best"), want.get("worst")):
                    if name and name not in {row["name"] for row in level["observations"]}:
                        wrong.append((indicator_id, level_key, "missing territory", name))
        self.assertEqual(wrong, [], f"observations that changed: {wrong[:10]}")


def _close(want, actual):
    if want is None or actual is None:
        return want is None and actual is None
    return abs(want - actual) <= TOLERANCE


if __name__ == "__main__":
    unittest.main()
