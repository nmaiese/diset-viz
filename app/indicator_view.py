"""One view model for every indicator page, whatever the source family.

Before this module the same entity was rendered by two templates against two
different shapes: the atlas path (territorial, Eurostat) handed the template
``stats``/``best``/``worst`` over a single regional series, while the
quality-of-life path (BES, Multiscopo) handed it ``level_payloads`` over one or
two territorial levels. The prose macros were shared, the data was not, and the
two pages drifted.

``build_indicator_view`` collapses that into a single shape:

    meta     everything about the indicator that does not depend on a territory
    levels   one entry per territorial level, each self-contained (its own years,
             observations, aggregates and year-over-year comparison)

The heavy lifting already existed and is reused rather than reimplemented:
``get_atlas_indicator`` (app/atlas_catalog.py) already normalizes metadata and
the regional series across all four families, and ``indicator_trend_stats`` /
``indicator_year_over_year_stats`` (app/data.py) are already family-agnostic.
What was missing was a place to put them together, plus the provincial level,
which only the BES loader knew how to read.

Two consequences worth knowing:

- BES and Multiscopo pages gain aggregates they never had (median, gap and gap
  ratio, biggest movers, gap trend). Nothing they had changes: that is pinned by
  ``tests/integration/test_indicator_view.py`` against a fixture dumped from the old code.
- Provinces have no profile page (there is no ``/provincia/<key>`` route), so a
  level declares whether its territories are linkable rather than the template
  guessing from the level name.
"""

import functools

from app import profiles, sources
from app.atlas_catalog import get_atlas_indicator, get_atlas_catalog
from app.bes_data import all_bes_indicators, get_bes_indicator_page, get_bes_rows, get_bes_territories
from app.data import indicator_trend_stats, indicator_year_over_year_stats
from app.external_data import freshness_label, freshness_status
from app.multiscopo_data import all_multiscopo_indicators
from app.indicator_notes import (
    annual_change_framing,
    change_unit_label,
    cover_bars,
    is_percentage_unit,
    region_choropleth_colors,
    trend_framing,
    value_unit_label,
)

# Colour ramp for the choropleth. It used to be declared twice, in the view's
# explore payload and again in the stylesheet's legend gradient; the page now
# reads it from here so the map and its legend cannot drift apart.
MAP_RAMP = {"from": [0xE7, 0xEC, 0xF3], "to": [0x15, 0x23, 0x3B]}

# Territorial levels, in the order the cockpit offers them. `profile_path`
# is the prefix of the territory's own page, or None when it has none.
LEVELS = {
    "regione": {
        "label": "Regioni",
        "singular": "regione",
        "plural": "regioni",
        "profile_path": "/regione/",
        "has_map": True,
    },
    "provincia": {
        "label": "Province",
        "singular": "provincia",
        "plural": "province",
        "profile_path": None,
        "has_map": False,
    },
}

RELATED_LIMIT = 8


def build_indicator_view(family, raw_id):
    """Normalized view model for one indicator, or None if it does not exist.

    `family` is a key of ``sources.SOURCES`` ("territorial", "eurostat", "bes",
    "multiscopo"); `raw_id` is the id as it appears in the URL, without the
    family prefix.
    """
    indicator_id = sources.internal_id(family, raw_id)
    payload = get_atlas_indicator(indicator_id)

    if payload is None:
        # Province-only BES series: they never enter the atlas catalog (no
        # regional coverage to canonicalize), but they still have a page.
        if family != "bes":
            return None
        page = get_bes_indicator_page(raw_id)
        if page is None:
            return None
        return _view_from_bes_only(family, raw_id, page)

    meta = _build_meta(family, raw_id, payload["metadata"])
    levels = [_level_from_series("regione", payload, meta)]
    if family == "bes":
        provincial = _provincial_level(raw_id, meta)
        if provincial is not None:
            levels.append(provincial)

    return _assemble(meta, levels)


def _assemble(meta, levels):
    levels = [level for level in levels if level is not None and level["observations"]]
    if not levels:
        return None
    for level in levels:
        level["explain"] = _explain_for_level(meta, level["key"], len(levels))
    meta["year_min"] = min(level["year_min"] for level in levels)
    meta["year_max"] = max(level["year_max"] for level in levels)
    meta["freshness_status"] = freshness_status(meta["year_max"])
    meta["freshness_label"] = freshness_label(meta["freshness_status"])
    related, siblings = _theme_neighbours(meta)
    for level in levels:
        level["query_map"] = _query_map(meta, level)
    return {
        "meta": meta,
        "levels": levels,
        "default_level": levels[0]["key"],
        "related": related,
        "siblings": siblings,
        "explore": _explore_payload(meta, levels),
    }


def _build_meta(family, raw_id, source_meta):
    """Everything that does not depend on a territorial level.

    Fields the atlas catalog leaves empty for the quality-of-life families
    (institution, freshness) are filled here, so the template never has to know
    which family it is rendering.
    """
    name = source_meta["name"]
    explain = source_meta.get("explain") or {}
    direction = explain.get("direction") or source_meta.get("direction")
    return {
        "id": source_meta["id"],
        "raw_id": raw_id,
        "family": family,
        "family_label": source_meta.get("catalog_family_label") or sources.family_label(family),
        "name": name,
        "unit": source_meta.get("unit"),
        "value_unit": value_unit_label(name, source_meta.get("unit")),
        "change_unit": change_unit_label(name, source_meta.get("unit")),
        # True for "%" and for "punti percentuali". Prose must then express a
        # change in points, never as a relative percentage: "da 49,99% a 54,87%,
        # il 9,8% in piu" puts two unrelated percentages in one sentence.
        "percentage_like": is_percentage_unit(source_meta.get("unit")),
        "direction": direction,
        "scoreable": direction in profiles.SCOREABLE_DIRECTIONS,
        "explain": explain,
        "theme": source_meta.get("theme"),
        "theme_path": profiles.theme_path(source_meta["theme"]) if source_meta.get("theme") else None,
        "source_theme": source_meta.get("source_theme"),
        "macro_area": source_meta.get("macro_area"),
        "source": source_meta.get("source"),
        # Never None: the province-only BES series carry no catalog metadata, and
        # a page that cannot name its source is worse than one naming the family.
        "source_label": (
            source_meta.get("source_label")
            or source_meta.get("source")
            or sources.family_label(family)
        ),
        "source_url": source_meta.get("source_url"),
        "source_data_url": source_meta.get("source_data_url"),
        # The exact SDMX series behind a Multiscopo indicator, so a reader can
        # go and pull the same numbers rather than trust ours.
        "source_dataflow": source_meta.get("source_dataflow"),
        "institution": source_meta.get("institution") or sources.family_institution(family),
        # No blanket default: a family that declares no licence renders none.
        "license_url": source_meta.get("license_url") or sources.family_license_url(family),
        "archive": source_meta.get("archive"),
        "quality_life_scored": source_meta.get("quality_life_scored", False),
        "quality_life_category_label": source_meta.get("quality_life_category_label"),
        "indexable": _is_indexable(family, raw_id, source_meta),
        # The catalog already computed the canonical path for every family, and
        # the families do not agree on the slug: the atlas truncates it at 80
        # characters, the quality-of-life ones do not. Rebuilding it here silently
        # moved six long-named BES indicators to a URL the sitemap does not list
        # and every existing link 301s away from. Defer, never recompute.
        "canonical_path": source_meta.get("path")
        or sources.indicator_url(family, raw_id, profiles.indicator_slug(name)),
        "downloads": _downloads(source_meta["id"]),
    }


@functools.lru_cache(maxsize=2)
def _family_indexability(family):
    """{raw_id: indexable} as the family's own catalog computes it."""
    if family == "bes":
        return {item["id"]: bool(item["indexable"]) for item in all_bes_indicators()}
    return {item["id"]: bool(item["indexable"]) for item in all_multiscopo_indicators()}


def _is_indexable(family, raw_id, source_meta):
    """One indexability answer, applying each family's own rule unchanged.

    The two rules are genuinely different: the atlas wants complete regional
    coverage, no gender variant and a recent year, while the quality-of-life
    families want 80% coverage in the latest year. The sitemap
    (app/views.py) still branches on the family catalog's own `indexable` flag,
    so reading anything else here puts 47 BES and Multiscopo pages out of step
    with the sitemap that lists them. Picking between the rules is all this does.
    """
    if family in ("bes", "multiscopo"):
        return _family_indexability(family).get(raw_id, False)
    return profiles.is_search_indexable_indicator(source_meta)


def _downloads(indicator_id):
    """CSV/JSON endpoints exposed by the shared atlas catalog."""
    return {
        "csv": f"/download/indicator/{indicator_id}.csv",
        "json": f"/download/indicator/{indicator_id}.json",
    }


def _query_map(meta, level):
    """Question-shaped paths into the page, backed only by this level's data.

    This is navigation, not a second prose layer.  Keeping the requested year
    and territorial vocabulary here means the template cannot advertise an
    answer for a year or level different from the cockpit it is rendering.
    """
    questions = [
        {"intent": "definizione", "label": f"Che cosa misura {meta['name']}?", "target": "sezione-definizione"},
        {"intent": "dato", "label": f"Qual è il dato più recente, nel {level['year_max']}?", "target": "esplora"},
        {"intent": "classifica", "label": f"Qual è la classifica delle {level['plural']} nel {level['year_max']}?", "target": "classifica-dati"},
    ]
    # Year-over-year framing, only when there is a previous year to compare to.
    if level["annual_change"]:
        questions.append({
            "intent": "confronto",
            "label": f"Che cosa è cambiato dal {level['annual_change']['previous_year']} al {level['year_max']}?",
            "target": "sezione-dinamica",
        })
    # The long trend, only when the level spans more than one year: a single-year
    # series cannot answer "come e cambiato dal 2005 al 2005".
    if level["year_min"] != level["year_max"]:
        questions.append({"intent": "andamento", "label": f"Come è cambiato dal {level['year_min']} al {level['year_max']}?", "target": "serie-storica"})
    questions.append({"intent": "metodologia", "label": "Come sono calcolati confronti e medie?", "target": "fonti-verifica"})
    # Downloads serve the regional series only, so the intent lives on the
    # regional level alone, matching what the cockpit actually offers.
    if meta.get("downloads") and level["key"] == "regione":
        questions.append({"intent": "download", "label": "Dove posso scaricare la serie?", "target": "download-dati"})
    return questions


def _level_from_series(key, payload, meta):
    """Build a level from an atlas-shaped payload ({metadata, series})."""
    return _build_level(key, payload["series"], meta, territory_total=None, coverage=None)


@functools.lru_cache(maxsize=2)
def _bes_series_by_indicator(level):
    """All BES rows for a level, indexed by indicator id.

    get_bes_rows returns one flat list of every observation (roughly 48k rows at
    the provincial level). Filtering it per indicator turns a page render into a
    full scan, and building every page into a quadratic one, so the split happens
    once per process, like the other on-disk loaders.

    Rows are aliased to the region field names the aggregate helpers in
    app/data.py expect, so those stay untouched and family-agnostic.
    """
    by_indicator = {}
    for row in get_bes_rows(level):
        if row["value"] is None or not row["territory_key"]:
            continue
        by_indicator.setdefault(row["id"], []).append({
            "year": row["year"],
            "value": row["value"],
            "region": row["territory"],
            "region_key": row["territory_key"],
        })
    return by_indicator


def _provincial_level(raw_id, meta):
    """The BES provincial series, which lives outside the atlas layer."""
    rows = _bes_series_by_indicator("provincia").get(raw_id)
    if not rows:
        return None
    return _build_level(
        "provincia", rows, meta, territory_total=len(get_bes_territories("provincia")), coverage=None
    )


# The exact phrases app/indicator_notes.py emits for the territorial level, and
# what each becomes on the other level. Whole phrases, not the bare noun: a
# substitution on the word alone turned "in tutti i territori regionali" into
# "in tutti i regioni" on every territorial page, because the article and the
# agreement belong to the phrase.
_LEVEL_PHRASES = {
    "scope": {
        "regione": ("in tutte le province", "in tutte le regioni"),
        "provincia": ("in tutte le regioni", "in tutte le province"),
    },
    "caveat": {
        "regione": ("Il confronto tra province", "Il confronto tra regioni"),
        "provincia": ("Il confronto tra regioni", "Il confronto tra province"),
    },
}


def _explain_for_level(meta, level_key, level_count):
    """`meta.explain` with the two level-dependent sentences retargeted.

    `explain` is built once per indicator and stored on `meta`, but two of its
    fields name a territorial level: `scope` ("il confronto applica la stessa
    definizione in tutte le regioni") and `caveat` ("il confronto tra regioni
    descrive una differenza osservata"). On the 34 BES indicators that also have
    provinces, both sentences said "regioni" above a cockpit of 103 provinces,
    in the composed article that is the only one those pages can show.

    The rule the rest of this model follows: anything level-specific belongs to
    `levels`, never to `meta`.

    A single-level indicator is left exactly as it is. There is nothing to
    retarget there, and rewriting it would only be a chance to get the Italian
    wrong on 393 pages that were never affected by the bug.
    """
    explain = dict(meta.get("explain") or {})
    if not explain or level_count < 2:
        return explain
    for field, by_level in _LEVEL_PHRASES.items():
        text = explain.get(field)
        source, target = by_level.get(level_key, (None, None))
        if text and source and source in text:
            explain[field] = text.replace(source, target)
    return explain


def _build_level(key, series, meta, territory_total, coverage):
    conf = LEVELS[key]
    series = [row for row in series if row.get("value") is not None]
    years = sorted({row["year"] for row in series})
    if not years:
        return None
    year_min, year_max = years[0], years[-1]

    # The aggregate helpers read year_min/year_max off the metadata, and a level
    # has its own range: BES regional data can be a year ahead of provincial.
    level_payload = {
        "metadata": {**meta, "year_min": year_min, "year_max": year_max},
        "series": series,
    }

    # #1 is the best performer for this indicator's direction. Contextual
    # indicators have no "best", so best/worst stay None and the order is simply
    # highest first.
    #
    # Ties are broken by name, deliberately. Both old paths let tied territories
    # fall in whatever order the CSV happened to list them, and one of them then
    # reversed the list, which flips tied rows again. That made the "best region"
    # printed on the page, and quoted in the analyst text, depend on row order in
    # a data file. Alphabetical is arbitrary too, but it is stable across
    # reloads and reproducible for whoever fact-checks the sentence.
    descending = meta["direction"] not in ("lower_better", "higher_worse")
    observations = sorted(
        (row for row in series if row["year"] == year_max),
        key=lambda row: (-row["value"] if descending else row["value"], row["region"]),
    )
    best = observations[0] if observations and meta["scoreable"] else None
    worst = observations[-1] if observations and meta["scoreable"] else None

    stats = indicator_trend_stats(level_payload, year_max, observations, best, worst)
    annual_change = indicator_year_over_year_stats(level_payload, year_max)

    territories = {}
    matrix = {}
    for row in series:
        territories.setdefault(row["region_key"], row["region"])
        matrix.setdefault(str(row["year"]), {})[row["region_key"]] = row["value"]

    if coverage is None and territory_total:
        coverage = len(observations) / territory_total if territory_total else None

    return {
        "key": key,
        "label": conf["label"],
        "singular": conf["singular"],
        "plural": conf["plural"],
        "profile_path": conf["profile_path"],
        "has_map": conf["has_map"],
        # Retargeted once the level list is known (see _scope_levels): a level
        # cannot tell on its own whether the indicator has a second one.
        "explain": dict(meta.get("explain") or {}),
        "years": years,
        "year_min": year_min,
        "year_max": year_max,
        "observations": [_territory(row) for row in observations],
        "best": _territory(best),
        "worst": _territory(worst),
        "stats": _normalize_stats(stats),
        "annual_change": _normalize_annual(annual_change),
        "annual_note": annual_change_framing(
            meta["name"], meta["direction"], annual_change["average_delta"] if annual_change else None
        ),
        "trend_note": trend_framing(meta["direction"], stats["avg_change_pct"]),
        "coverage": coverage,
        "territory_total": territory_total or len(territories),
        "territories": [
            {"key": tkey, "name": name}
            for tkey, name in sorted(territories.items(), key=lambda item: item[1])
        ],
        # Which territory the cockpit opens on. It has to be one explicit value:
        # the server rendered the ranking leader while the script fell back to
        # territories[0], which is alphabetical, so the focus tile visibly
        # changed the moment the page hydrated. The leader is the more
        # informative default.
        "default_territory": _territory(observations[0]) if observations else None,
        "matrix": matrix,
        "map_colors": region_choropleth_colors(observations) if conf["has_map"] else None,
        "cover_bars": cover_bars(observations, best, worst, meta["scoreable"]) if conf["has_map"] else None,
        "bar_max": max((row["value"] for row in observations), default=0),
    }


def _territory(row):
    """Territory-neutral row: the model says `key`/`name`, never `region`."""
    if not row:
        return None
    return {
        "key": row.get("region_key") or row.get("territory_key"),
        "name": row.get("region") or row.get("territory"),
        "value": row.get("value"),
    }


def _normalize_stats(stats):
    """Rename the region-flavoured mover fields to the neutral territory shape.

    app/data.py speaks "region" because it predates provincial data. Renaming it
    there would touch the whole atlas; renaming it here keeps one vocabulary in
    the template.
    """
    out = dict(stats)
    for field in ("region_highest_delta", "region_lowest_delta"):
        mover = out.pop(field)
        out[field.replace("region_", "")] = (
            {**_territory(mover), "delta": mover["delta"], "kind": mover["kind"]} if mover else None
        )
    return out


def _normalize_annual(annual):
    if not annual:
        return None
    out = dict(annual)
    for field in ("largest_increases", "largest_decreases"):
        out[field] = [
            {
                **_territory(change),
                "delta": change["delta"],
                "kind": change["kind"],
                "previous_value": change["previous_value"],
                "current_value": change["current_value"],
            }
            for change in annual[field]
        ]
    return out


def _view_from_bes_only(family, raw_id, page):
    """Meta for the BES series the atlas catalog does not carry.

    These have no regional coverage to canonicalize, so the atlas layer skips
    them, but they are reachable pages and must render like everything else.
    """
    meta = _build_meta(family, raw_id, {
        **page,
        "catalog_family_label": sources.family_label(family),
        "theme": page.get("category_name") or page.get("domain_name"),
    })
    # A province-only BES series is outside get_atlas_indicator, which owns the
    # two generic download routes. Do not publish links that would return 404.
    meta["downloads"] = None
    levels = []
    for level in page["level_payloads"]:
        if level["level"] == "provincia":
            built = _provincial_level(raw_id, meta)
        else:
            rows = _bes_series_by_indicator("regione").get(raw_id)
            built = _build_level("regione", rows, meta, territory_total=None, coverage=None) if rows else None
        if built is not None:
            built["coverage"] = level["coverage_latest"]
            built["territory_total"] = level["territory_total"]
            levels.append(built)
    levels.sort(key=lambda level: 0 if level["key"] == "regione" else 1)
    return _assemble(meta, levels)


def _theme_neighbours(meta):
    """Other indicators of the same theme: a related table plus prev/next."""
    if not meta.get("theme"):
        return [], {"prev": None, "next": None}
    siblings = _theme_siblings(meta["theme"])
    index = next((i for i, item in enumerate(siblings) if str(item["id"]) == str(meta["id"])), None)
    prev_item = siblings[index - 1] if index else None
    next_item = siblings[index + 1] if index is not None and index < len(siblings) - 1 else None
    related = [item for item in siblings if str(item["id"]) != str(meta["id"])][:RELATED_LIMIT]
    return related, {"prev": prev_item, "next": next_item}


@functools.lru_cache(maxsize=16)
def _theme_siblings(theme):
    return sorted(
        (
            {
                "id": item["id"],
                "name": item["name"],
                "path": item["path"],
                "direction": (item.get("explain") or {}).get("direction"),
                "year_max": item["year_max"],
                "unit": item.get("unit"),
                # La sparkline delle card usa la stessa serie (media nazionale
                # ridotta a 24 punti) gia' calcolata nel catalogo; `latest` e'
                # l'ultimo punto, l'ordine di grandezza che accompagna la curva.
                "spark": item.get("spark") or [],
                "latest": (item["spark"][-1]["value"]
                           if item.get("spark") else None),
            }
            for item in get_atlas_catalog()["indicators"]
            if item["theme"] == theme
        ),
        key=lambda item: item["name"].lower(),
    )


def _explore_payload(meta, levels):
    """Everything the cockpit script needs, on the page, without a second fetch.

    One entry per level so switching between regions and provinces is a client
    side state change on the same canonical URL, not a navigation.
    """
    return {
        "id": meta["id"],
        "unit": meta["value_unit"],
        "changeUnit": meta["change_unit"],
        "direction": meta["direction"],
        "higherBetter": meta["direction"] not in ("lower_better", "higher_worse"),
        "scoreable": meta["scoreable"],
        "ramp": MAP_RAMP,
        "defaultLevel": levels[0]["key"],
        "levels": [
            {
                "key": level["key"],
                "label": level["label"],
                "singular": level["singular"],
                "plural": level["plural"],
                "profilePath": level["profile_path"],
                "hasMap": level["has_map"],
                "years": level["years"],
                "yearMin": level["year_min"],
                "yearMax": level["year_max"],
                "defaultYear": level["year_max"],
                "territories": level["territories"],
                "defaultTerritory": (level["default_territory"] or {}).get("key"),
                "matrix": level["matrix"],
            }
            for level in levels
        ],
    }
