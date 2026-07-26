"""Golden dump of every indicator's numeric aggregates, as computed today.

The indicator page is being rebuilt around a single view model
(``app.indicator_view``) shared by all four source families. The layout and the
prose change on purpose, so an HTML comparison would be useless as a guard. The
numbers must not change at all, and that is what this fixture pins.

Run before the refactor to record the baseline, then let
``tests/test_indicator_view.py`` assert that the new model reproduces it:

    .venv/bin/python -m scripts.dump_indicator_stats

Only fields the current code paths already produce are recorded. The unified
model adds aggregates the quality-of-life families never had (median-vs-mean
spread, gap ratio, biggest movers); those are additive and deliberately
unpinned, because there is no previous value to preserve.
"""

import json
from pathlib import Path

from app import profiles, sources
from app.atlas_catalog import get_atlas_catalog, get_atlas_indicator, get_atlas_indicator_year
from app.bes_data import get_bes_indicator_page
from app.data import indicator_trend_stats, indicator_year_over_year_stats
from app.multiscopo_data import get_multiscopo_indicator_page

FIXTURE = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "indicator_stats_golden.json"

# Float noise below this is not a behaviour change. Six decimals is far tighter
# than anything the page prints (two decimals) while staying stable across
# platforms and Python versions.
PRECISION = 6


def _round(value):
    return round(value, PRECISION) if isinstance(value, float) else value


def _annual(annual):
    """The year-over-year fields the templates actually read."""
    if not annual:
        return None
    return {
        "year": annual["year"],
        "previous_year": annual["previous_year"],
        "common_count": annual["common_count"],
        "previous_avg": _round(annual["previous_avg"]),
        "current_avg": _round(annual["current_avg"]),
        "average_delta": _round(annual["average_delta"]),
        "increase_count": annual["increase_count"],
        "decrease_count": annual["decrease_count"],
        "stable_count": annual["stable_count"],
    }


def _atlas_level(indicator_id):
    """Replicates _render_atlas_indicator (app/views.py) exactly."""
    payload = get_atlas_indicator(indicator_id)
    if payload is None:
        return None
    meta = payload["metadata"]
    year = meta["year_max"]
    direction = (meta.get("explain") or {}).get("direction")
    values = get_atlas_indicator_year(indicator_id, year)["values"]
    if direction in ("lower_better", "higher_worse"):
        values = list(reversed(values))
    scoreable = direction in profiles.SCOREABLE_DIRECTIONS
    best = values[0] if values and scoreable else None
    worst = values[-1] if values and scoreable else None
    stats = indicator_trend_stats(payload, year, values, best, worst)
    return {
        "year_max": year,
        "count": stats["year_count"],
        "mean": _round(stats["year_avg"]),
        "median": _round(stats["median"]),
        "gap_abs": _round(stats["gap_abs"]),
        "gap_ratio": _round(stats["gap_ratio"]),
        "best": best["region"] if best else None,
        "worst": worst["region"] if worst else None,
        "above_avg": stats["above_avg_count"],
        "below_avg": stats["below_avg_count"],
        "year_min_avg": _round(stats["year_min_avg"]),
        "avg_change_abs": _round(stats["avg_change_abs"]),
        "avg_change_pct": _round(stats["avg_change_pct"]),
        "gap_trend": _round(stats["gap_trend"]),
        "annual": _annual(indicator_year_over_year_stats(payload, year)),
    }


def _qol_levels(page):
    """Replicates get_bes_indicator_page / get_multiscopo_indicator_page.

    These families expose one payload per territorial level and compute a
    narrower set of aggregates than the atlas path, so only those are pinned.
    """
    levels = {}
    for level in page["level_payloads"]:
        observations = level["observations"]
        levels[level["level"]] = {
            "year_max": level["year_max"],
            "count": level["count_latest"],
            "coverage": _round(level["coverage_latest"]),
            "mean": _round(level["mean"]),
            "median": _round(level["median"]),
            "first": observations[0]["territory"] if observations else None,
            "last": observations[-1]["territory"] if observations else None,
            "annual": _annual(level["annual_change"]),
        }
    return levels


def build():
    golden = {}
    for item in get_atlas_catalog()["indicators"]:
        level = _atlas_level(item["id"])
        if level is not None:
            golden[str(item["id"])] = {"levels": {"regione": level}}

    for family, loader in (("bes", get_bes_indicator_page), ("multiscopo", get_multiscopo_indicator_page)):
        for raw_id in _family_ids(family):
            page = loader(raw_id)
            if page is not None:
                golden[sources.internal_id(family, raw_id)] = {"levels": _qol_levels(page)}
    return golden


def _family_ids(family):
    if family == "bes":
        from app.bes_data import all_bes_indicators
        return [item["id"] for item in all_bes_indicators()]
    from app.multiscopo_data import all_multiscopo_indicators
    return [item["id"] for item in all_multiscopo_indicators()]


if __name__ == "__main__":
    golden = build()
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(
        json.dumps(golden, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"{len(golden)} indicators -> {FIXTURE}")
