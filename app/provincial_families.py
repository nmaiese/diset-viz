"""Adapter unico per indicatori esterni pubblicati a livello provinciale.

Il layer esterno resta separato dai CSV BES. Questo modulo usa il manifesto per
livello come contratto delle decisioni editoriali e restituisce la stessa forma
territory-neutral che usa ``indicator_view``.
"""

from __future__ import annotations

from collections import defaultdict
from functools import lru_cache

from app import bes_data, external_data, profiles, sources
from app.data import REGION_ORDER, _parse_number
from app.profiles import SCOREABLE_DIRECTIONS
from app.taxonomy import CANONICAL_CATEGORIES, category_metadata, category_path


PROVINCE_LEVEL = "provincia"
REGION_LEVEL = "regione"
PUBLIC_LEVELS = (REGION_LEVEL, PROVINCE_LEVEL)
MIN_PUBLIC_YEAR = 2023
MIN_PUBLIC_COVERAGE = 0.8
MIN_SCOREABLE_TERRITORIES = 3


def _as_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "si"}


def _family_raw(target):
    family, raw_id = sources.split_internal_id(target)
    if family not in sources.EXTERNAL_FAMILIES or not sources.SOURCES[family]["internal_prefix"]:
        return None
    return family, raw_id


def _territories(level):
    if level == PROVINCE_LEVEL:
        return {key: info["name"] for key, info in bes_data.get_bes_territories(level).items()}
    return {profiles.region_key_for(name): name for name in REGION_ORDER}


def _fail(message):
    raise ValueError(f"contratto indicatore esterno: {message}")


def _number(value, context):
    parsed = _parse_number(value)
    if parsed is None:
        _fail(f"valore illeggibile ({context}): {value!r}")
    return parsed


def _check_level(row):
    level = row.get("territory_level", "")
    if level not in PUBLIC_LEVELS:
        _fail(f"livello {level!r} non ammesso per {row.get('target_indicator_id')!r}")
    if _family_raw(row.get("target_indicator_id", "")) is None:
        _fail(f"target_indicator_id non registrato: {row.get('target_indicator_id')!r}")


def _validate(rows, levels):
    level_by_key = {}
    for manifest in levels:
        target = manifest.get("target_indicator_id", "")
        level = manifest.get("territory_level", "")
        _check_level({"target_indicator_id": target, "territory_level": level})
        key = (target, level)
        if key in level_by_key:
            _fail(f"manifesto duplicato per {target} / {level}")
        if not manifest.get("name") or not manifest.get("theme"):
            _fail(f"manifesto incompleto per {target} / {level}")
        if manifest.get("direction") not in (*SCOREABLE_DIRECTIONS, "contextual"):
            _fail(f"verso non ammesso per {target} / {level}")
        category = manifest.get("quality_life_category")
        if category not in CANONICAL_CATEGORIES:
            _fail(f"categoria non mappata {category!r} per {target} / {level}")
        try:
            int(manifest["year_min"])
            int(manifest["year_max"])
            float(manifest["coverage_latest"])
            int(manifest["territory_count_latest"])
        except (KeyError, TypeError, ValueError) as error:
            _fail(f"numeri illeggibili nel manifesto {target} / {level}: {error}")
        level_by_key[key] = manifest

    seen = {}
    accepted = []
    for row in rows:
        if row.get("territory_level") != PROVINCE_LEVEL:
            continue
        target = row.get("target_indicator_id", "")
        key = (target, PROVINCE_LEVEL)
        manifest = level_by_key.get(key)
        if manifest is None:
            # Le righe regionali storiche e i candidati non pubblicati non sono
            # materiale del catalogo provinciale.
            continue
        _check_level(row)
        territory_key = row.get("territory_code", "")
        expected_name = _territories(PROVINCE_LEVEL).get(territory_key)
        if expected_name is None:
            _fail(f"provincia sconosciuta {territory_key!r} per {target}")
        if row.get("territory_name", "").strip() != expected_name:
            _fail(f"nome provincia non coerente per {territory_key}: {row.get('territory_name')!r}")
        for field in (
            "name", "theme", "quality_life_category", "direction", "source_dataset",
            "source_indicator_id", "source_url", "license", "definition_match",
        ):
            if row.get(field, "") and row.get(field) != manifest.get(field):
                _fail(f"metadato {field} divergente per {target} / {PROVINCE_LEVEL}")
        try:
            year = int(row["year"])
        except (KeyError, TypeError, ValueError) as error:
            _fail(f"anno illeggibile per {target}: {error}")
        value = _number(row.get("value"), f"{target}/{territory_key}/{year}")
        observation_key = (target, territory_key, year)
        if observation_key in seen:
            if seen[observation_key] != value:
                _fail(f"osservazione duplicata con valori diversi: {observation_key}")
            _fail(f"osservazione duplicata: {observation_key}")
        seen[observation_key] = value
        accepted.append({
            "id": target,
            "family": _family_raw(target)[0],
            "raw_id": _family_raw(target)[1],
            "year": year,
            "value": value,
            "region": row["territory_name"],
            "region_key": territory_key,
            "territory": row["territory_name"],
            "territory_key": territory_key,
            "unit": row.get("unit", ""),
        })
    return level_by_key, accepted


@lru_cache(maxsize=1)
def _index():
    manifests = external_data.get_external_levels()
    rows = external_data.get_external_rows()
    level_by_key, province_rows = _validate(rows, manifests)
    rows_by_target = defaultdict(list)
    for row in province_rows:
        rows_by_target[(row["family"], row["raw_id"])].append(row)
    return level_by_key, dict(rows_by_target)


def _level_info(manifest, observations):
    years = sorted({row["year"] for row in observations})
    if not years:
        years = [int(manifest["year_min"]), int(manifest["year_max"])]
    latest = int(manifest["year_max"])
    count = sum(row["year"] == latest for row in observations)
    return {
        "key": manifest["territory_level"],
        "label": "Province" if manifest["territory_level"] == PROVINCE_LEVEL else "Regioni",
        "year_min": int(manifest["year_min"]),
        "year_max": latest,
        "coverage_latest": float(manifest["coverage_latest"]),
        "territory_count_latest": int(manifest["territory_count_latest"]),
        "count_latest": count,
        "indexable": (
            int(manifest["year_max"]) >= MIN_PUBLIC_YEAR
            and float(manifest["coverage_latest"]) >= MIN_PUBLIC_COVERAGE
            and count >= MIN_SCOREABLE_TERRITORIES
        ),
        "observations": observations,
    }


@lru_cache(maxsize=1)
def all_indicators():
    """Catalogo cross-family delle serie esterne con livello provinciale."""
    level_by_key, rows_by_target = _index()
    keys = sorted(set((family, raw_id) for family, raw_id in rows_by_target))
    output = []
    for family, raw_id in keys:
        target = sources.internal_id(family, raw_id)
        manifests = {
            level: manifest
            for (manifest_target, level), manifest in level_by_key.items()
            if manifest_target == target
        }
        province = rows_by_target[(family, raw_id)]
        province_manifest = manifests[PROVINCE_LEVEL]
        category = CANONICAL_CATEGORIES[province_manifest["quality_life_category"]]
        category_info = category_metadata(province_manifest["theme"])
        metadata = {
            "id": target,
            "raw_id": raw_id,
            "family": family,
            "name": province_manifest["name"],
            "theme": category_info["theme"],
            "source_theme": province_manifest["theme"],
            "quality_life_category": province_manifest["quality_life_category"],
            "quality_life_category_label": category["name"],
            "macro_area": category["macro_area"],
            "theme_path": category_path(province_manifest["quality_life_category"]),
            "unit": province[0].get("unit", "") if province else "",
            "direction": province_manifest["direction"],
            "scoreable": _as_bool(province_manifest["scoreable"]),
            "sample_survey": _as_bool(province_manifest.get("sample_survey")),
            "source": sources.family_label(family),
            "source_label": sources.family_label(family),
            "source_url": province_manifest["source_url"],
            "license": province_manifest["license"],
            "license_url": sources.family_license_url(family),
            "institution": sources.family_institution(family),
            "catalog_family": family,
            "catalog_family_label": sources.family_label(family),
            "path": sources.indicator_url(family, raw_id, profiles.indicator_slug(province_manifest["name"])),
            "indexable": any(_level_info(manifest, province if level == PROVINCE_LEVEL else [])['indexable']
                              for level, manifest in manifests.items()),
        }
        levels = {}
        for level, manifest in manifests.items():
            observations = province if level == PROVINCE_LEVEL else []
            levels[level] = _level_info(manifest, observations)
        metadata["year_min"] = min(info["year_min"] for info in levels.values())
        metadata["year_max"] = max(info["year_max"] for info in levels.values())
        output.append({"metadata": metadata, "levels": levels, "series": province})
    return output


def _entry(family, raw_id):
    return next((item for item in all_indicators()
                 if item["metadata"]["family"] == family and item["metadata"]["raw_id"] == raw_id), None)


def has_data():
    return bool(all_indicators())


def indicator_page(family, raw_id):
    """Meta e livelli di una serie esterna provinciale."""
    return _entry(family, raw_id)


def series(family, raw_id, level=PROVINCE_LEVEL):
    entry = _entry(family, raw_id)
    if entry is None or level != PROVINCE_LEVEL:
        return []
    return [dict(row) for row in entry["series"]]


def scoreables():
    """Serie provinciali ammesse allo scoring, dopo tutti i gate espliciti."""
    return [
        item for item in all_indicators()
        if item["metadata"]["scoreable"]
        and item["metadata"]["direction"] in SCOREABLE_DIRECTIONS
        and item["levels"][PROVINCE_LEVEL]["indexable"]
        and item["levels"][PROVINCE_LEVEL]["coverage_latest"] >= MIN_PUBLIC_COVERAGE
        and item["levels"][PROVINCE_LEVEL]["year_max"] >= MIN_PUBLIC_YEAR
    ]


def indicators_for_province(province_key):
    """Valori, rango, movimento e fonte per una provincia."""
    output = []
    for item in all_indicators():
        meta = item["metadata"]
        rows = item["series"]
        by_year = defaultdict(dict)
        for row in rows:
            by_year[row["year"]][row["region_key"]] = row["value"]
        years = sorted(year for year, values in by_year.items() if province_key in values)
        if not years:
            continue
        year = years[-1]
        values = by_year[year]
        reverse = meta["direction"] not in ("lower_better", "higher_worse")
        ordered = sorted(values.items(), key=lambda pair: (-pair[1] if reverse else pair[1], pair[0]))
        rank = next(index for index, pair in enumerate(ordered, start=1) if pair[0] == province_key)
        previous = by_year[years[-2]].get(province_key) if len(years) > 1 else None
        output.append({
            "id": meta["id"], "name": meta["name"], "theme": meta["theme"],
            "unit": meta["unit"], "direction": meta["direction"], "value": values[province_key],
            "year": year, "year_from": years[0], "rank": rank,
            "province_count": len(values), "movement": None if previous is None else values[province_key] - previous,
            "source": meta["source_label"], "source_url": meta["source_url"],
            "path": sources.level_path(meta["path"], PROVINCE_LEVEL, PROVINCE_LEVEL),
        })
    return sorted(output, key=lambda row: (row["rank"], row["name"]))


def cache_clear():
    _index.cache_clear()
    all_indicators.cache_clear()
