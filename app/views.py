from app import app
from app.cache import cache
from app.blog import SITE_NAME, SITE_URL, all_tags, get_post, get_posts
from app.data import (
    get_catalog,
    get_indicator,
    get_indicator_year,
    get_rows,
    indicator_trend_stats,
    indicator_year_over_year_stats,
)
from app.atlas_catalog import (
    all_atlas_themes_index,
    atlas_themes_by_macro_area,
    get_atlas_catalog,
    get_atlas_indicator,
    get_atlas_indicator_year,
    get_atlas_theme_profile,
    search_atlas_indicators,
)
from app import profiles
from app import seo_policy
from app import indicator_notes
from app import quality_life_bes as qb
from app import bes_data
from app import multiscopo_data
from app import external_manifest
from app import game
from app import quiz
from app import quiz_tokens
from app import leaderboard
from app import moderation

from flask import Response, abort, make_response, redirect, render_template, request, send_from_directory, url_for
from flask.json import jsonify

import csv, hmac, io, json, os, re, time

from app import config


_HOME_FEATURED_INDICATORS = ("901", "104", "105", "910")

# Indicators shown as the selectable choropleth in the homepage map hero.
# Same flagship set used elsewhere (llms.txt, the /atlante SEO fallback), so
# "featured" means the same thing everywhere on the site.
_HOME_MAP_INDICATORS = _HOME_FEATURED_INDICATORS

# Indicators behind the "Storie dai dati" cards: real, already-published
# indicators (three overlap with existing blog posts) with a declared
# higher_better/lower_better direction, so "guida"/"resta indietro" framing is
# supported by the data instead of asserted for a contextual indicator.
_HOME_STORY_INDICATORS = ("901", "408", "910", "102")

# "Confronta" preview: a North / Centre / South contrast on three scoreable
# indicators (PIL pro capite, NEET, speranza di vita), so bars and ranking are
# something the data supports rather than a placeholder.
_HOME_COMPARE_INDICATORS = ("901", "408", "910")
_HOME_COMPARE_REGIONS = ("lombardia", "lazio", "campania")
_HOME_COMPARE_COLORS = ("var(--ink)", "var(--accent)", "var(--positive-ink)")


def _client_ip():
    """IP del client, rispettando X-Forwarded-For dietro il proxy Cloud Run."""
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _rate_limit_ok(bucket, limit, window_s):
    """Rate limit a finestra fissa, in-process, appoggiato alla cache dell'app.
    Per-worker (leggermente lasco con più worker), senza dipendenze esterne né Redis:
    sufficiente a frenare lo spam su un endpoint pubblico di logging."""
    now = time.time()
    key = f"rl:{bucket}"
    entry = cache.get(key)
    if entry is None or now - entry[0] >= window_s:
        cache.set(key, (now, 1), timeout=window_s)
        return True
    start, count = entry
    if count >= limit:
        return False
    cache.set(key, (start, count + 1), timeout=window_s)
    return True


@app.template_filter("it_num")
def it_num(value, decimals=1):
    """Format a number Italian-style: dot thousands, comma decimals."""
    if value is None:
        return "n.d."
    try:
        formatted = f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return str(value)
    return formatted.replace(",", "§").replace(".", ",").replace("§", ".")


@cache.memoize(timeout=100)
def get_all_data():
    filepath = os.path.join(os.path.dirname(__file__), 'static/data/Assoluti_Regione.csv')
    with open(filepath, 'r', encoding='utf8') as f:
        reader = csv.DictReader(f, delimiter=";")
        data = list(reader)
    return data

@app.route("/data")
@cache.cached(timeout=100)
def data():
    data = get_all_data()
    return jsonify(data)


@app.route("/")
@cache.cached(timeout=300, query_string=True)
def home():
    indicators = get_catalog()["indicators"]
    total_indicators = len(indicators)
    return render_template(
        "home.html",
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/",
        total_indicators=total_indicators,
        year_min=min(item["year_min"] for item in indicators),
        year_max=max(item["year_max"] for item in indicators),
        map_hero=_home_map_hero(),
        capabilities=_home_capabilities(total_indicators),
        stories=_home_story_cards(),
        themes_preview=_home_themes_preview(),
        compare_preview=_home_compare_preview(),
        qol=_home_qol_preview(),
        quiz_games=_home_quiz_games(),
        posts=get_posts()[:3],
    )


@app.route("/atlante")
@cache.cached(timeout=300)
def atlante():
    return render_template('app.html', featured_indicators=_home_featured_indicator_links())


@app.route("/legacy")
@cache.cached(timeout=300)
def legacy():
    return render_template('legacy.html')


@app.route("/legacy-reddito")
@cache.cached(timeout=300)
def legacy_reddito():
    return render_template('legacy_reddito.html')


@app.route("/api/catalog")
def catalog():
    return jsonify(get_atlas_catalog())


@app.route("/api/external-indicators/manifest")
def external_indicator_manifest_api():
    return jsonify({"manifest": external_manifest.rows()})


@app.route("/api/search")
def search():
    return jsonify({
        "results": search_atlas_indicators(
            query=request.args.get("q", ""),
            theme=request.args.get("theme"),
        )
    })


@app.route("/api/indicator/<indicator_id>")
def indicator(indicator_id):
    payload = get_atlas_indicator(indicator_id)
    if payload is None:
        abort(404)
    return jsonify(payload)


@app.route("/api/indicator/<indicator_id>/year/<int:year>")
def indicator_year(indicator_id, year):
    payload = get_atlas_indicator_year(indicator_id, year)
    if payload is None:
        abort(404)
    return jsonify(payload)


@app.post("/api/events")
def analytics_event():
    # Endpoint pubblico che scrive nei log: senza limite è vulnerabile a spam/abuso.
    if not _rate_limit_ok(f"events:{_client_ip()}", limit=30, window_s=60):
        abort(429)

    payload = request.get_json(silent=True) or {}
    name = _clean_event_name(payload.get("name"))
    if not name:
        abort(400)

    event = {
        "name": name,
        "path": _clean_event_value(payload.get("path")),
        "title": _clean_event_value(payload.get("title")),
        "params": _clean_event_params(payload.get("params")),
    }
    app.logger.info("analytics_event %s", json.dumps(event, ensure_ascii=False, sort_keys=True))
    return ("", 204)


@app.route("/blog")
def blog_index():
    return render_template(
        "blog_list.html",
        posts=get_posts(),
        tags=all_tags(),
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/blog",
    )


@app.route("/blog/<slug>")
def blog_post(slug):
    post = get_post(slug)
    if post is None:
        abort(404)
    post = dict(post)
    if post.get("indicator"):
        indicator_payload = get_atlas_indicator(post["indicator"])
        if indicator_payload:
            meta = indicator_payload["metadata"]
            post["indicator_path"] = meta["path"]
            post["indicator_meta"] = meta
    related = [p for p in get_posts() if p["slug"] != slug][:3]
    return render_template(
        "blog_post.html",
        post=post,
        related=related,
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=post["url"],
    )


@app.route("/privacy")
def privacy():
    return render_template(
        "privacy.html",
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/privacy",
    )


@app.route("/metodologia")
def methodology():
    return render_template(
        "methodology.html",
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/metodologia",
    )


@app.route("/indicatore/<slug>")
def indicator_page(slug):
    match = re.match(r"^(\d+)(?:-.*)?$", slug)
    if not match:
        abort(404)
    indicator_id = match.group(1)
    payload = get_atlas_indicator(indicator_id)
    if payload is None:
        abort(404)

    meta = payload["metadata"]
    canonical_path = profiles.indicator_path(indicator_id, meta["name"])
    if f"/indicatore/{slug}" != canonical_path:
        return redirect(canonical_path, code=301)

    year = meta["year_max"]
    year_view = get_atlas_indicator_year(indicator_id, year)

    # Order the ranking so #1 is the best-performing region for this indicator's
    # direction; for contextual indicators "best" is undefined, so keep raw order.
    direction = (meta.get("explain") or {}).get("direction")
    values = year_view["values"]  # already sorted by value desc
    if direction in ("lower_better", "higher_worse"):
        values = list(reversed(values))
    scoreable = direction in profiles.SCOREABLE_DIRECTIONS
    best = values[0] if values and scoreable else None
    worst = values[-1] if values and scoreable else None

    plain = (meta.get("explain") or {}).get("plain", "")
    stats = indicator_trend_stats(payload, year, values, best, worst)
    annual_change = indicator_year_over_year_stats(payload, year)
    trend_note = indicator_notes.trend_framing(direction, stats["avg_change_pct"])
    annual_note = indicator_notes.annual_change_framing(
        meta["name"],
        direction,
        annual_change["average_delta"] if annual_change else None,
    )
    is_indexable = profiles.is_search_indexable_indicator(meta)
    map_colors = indicator_notes.region_choropleth_colors(values)
    spark_points = indicator_notes.sparkline_points(meta.get("spark") or [], width=1200, height=140)
    cover_bars = indicator_notes.cover_bars(values, best, worst, scoreable)

    # Full year x region matrix embedded in the page so the client hydrates the
    # ranking, map and readout in place, on this one canonical URL, without any
    # extra fetch. The last-year ranking above stays server-rendered as the
    # crawlable fallback: the explore controls only enhance it.
    region_names = {}
    matrix = {}
    for row in payload["series"]:
        if row["value"] is None:
            continue
        region_names.setdefault(row["region_key"], row["region"])
        matrix.setdefault(str(row["year"]), {})[row["region_key"]] = row["value"]
    explore_data = {
        "id": meta["id"],
        "unit": indicator_notes.value_unit_label(meta["name"], meta["unit"]),
        "years": meta["years"],
        "yearMin": meta["year_min"],
        "yearMax": meta["year_max"],
        "defaultYear": year,
        "direction": direction,
        "higherBetter": direction not in ("lower_better", "higher_worse"),
        "scoreable": scoreable,
        "canonical": canonical_path,
        "regions": [
            {"key": key, "name": name}
            for key, name in sorted(region_names.items(), key=lambda kv: kv[1])
        ],
        "matrix": matrix,
        "ramp": {"from": [0xE7, 0xEC, 0xF3], "to": [0x15, 0x23, 0x3B]},
    }

    # Exploration states (?anno=, ?regione=) are the same object, not a new page:
    # they never enter the index or sitemap and the canonical stays the base URL.
    explore_state = seo_policy.has_explore_params(request.args)
    noindex = (not is_indexable) or explore_state

    response = make_response(render_template(
        "indicator_page.html",
        meta=meta,
        values=values,
        best=best,
        worst=worst,
        year=year,
        stats=stats,
        cover_bars=cover_bars,
        annual_change=annual_change,
        annual_note=annual_note,
        trend_note=trend_note,
        is_indexable=is_indexable,
        noindex=noindex,
        explore_data=explore_data,
        map_colors=map_colors,
        spark_points=spark_points,
        page_intro=indicator_notes.indicator_page_intro(
            plain,
            meta["year_min"],
            meta["year_max"],
            len(meta["regions"]),
        ),
        value_unit=indicator_notes.value_unit_label(meta["name"], meta["unit"]),
        change_unit=indicator_notes.change_unit_label(meta["name"], meta["unit"]),
        seo_title=indicator_notes.seo_title(meta["name"], SITE_NAME),
        seo_description=indicator_notes.seo_description(
            plain,
            meta["year_max"],
            len(meta["regions"]),
            name=meta["name"],
        ),
        theme_path=profiles.theme_path(meta["theme"]),
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}{canonical_path}",
    ))
    if noindex:
        response.headers["X-Robots-Tag"] = "noindex, follow"
    return response


@app.route("/regione/<region_key>")
def region_page(region_key):
    profile = profiles.region_profile(region_key)
    if profile is None:
        abort(404)
    return render_template(
        "region_page.html",
        profile=profile,
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/regione/{region_key}",
    )


@app.route("/api/regions/overview")
def regions_overview_api():
    """Compact per-region summary for the SPA 'per regione' selection map.

    Same source as the /regioni page; no overall regional score is exposed here.
    """
    return jsonify(profiles.regions_overview())


@app.route("/api/region/<region_key>")
def region_api(region_key):
    """JSON del profilo regione, per la vista 'per regione' della SPA.

    Riusa la stessa funzione che alimenta la pagina server /regione/<key>, così
    atlante interattivo e pagina SEO restano coerenti su un'unica fonte dati.
    L'after_request in app/__init__.py aggiunge già X-Robots-Tag: noindex.
    """
    profile = profiles.region_profile(region_key)
    if profile is None:
        abort(404)
    return jsonify(profile)


@app.route("/tema/<theme_slug>")
def theme_page(theme_slug):
    profile = get_atlas_theme_profile(theme_slug)
    if profile is None:
        abort(404)
    if request.path != profile["theme_path"]:
        return redirect(profile["theme_path"], code=301)
    return render_template(
        "theme_page.html",
        profile=profile,
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}{profile['theme_path']}",
    )


@app.route("/regioni")
def regions_index():
    overview = profiles.regions_overview()
    regions = list(overview.values())
    return render_template(
        "regions_index.html",
        regions=regions,
        overview=overview,
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/regioni",
    )


@app.route("/temi")
def themes_index():
    groups = atlas_themes_by_macro_area()
    total = sum(group["indicator_count"] for group in groups)
    return render_template(
        "themes_index.html",
        groups=groups,
        total=total,
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/temi",
    )


# User-facing URL level (plural) -> engine level (singular).
URL_LEVEL = {"regioni": "regione", "province": "provincia"}


def _quality_life_profile_arg():
    """Resolve the requested profile slug from ?profilo= (or ?profile=)."""
    return request.args.get("profilo") or request.args.get("profile") or qb.DEFAULT_PROFILE


def _profile_suffix(slug):
    return "" if slug == qb.DEFAULT_PROFILE else f"?profilo={slug}"




@app.route("/download/indicator/<indicator_id>.csv")
def indicator_download_csv(indicator_id):
    payload = get_atlas_indicator(indicator_id)
    if payload is None:
        abort(404)
    meta = payload["metadata"]
    rows = []
    for point in payload["series"]:
        rows.append({
            "indicator_id": indicator_id,
            "indicator": meta["name"],
            "theme": meta["theme"],
            "region": point["region"],
            "region_key": point["region_key"],
            "year": point["year"],
            "value": point["value"],
            "unit": meta["unit"],
            "source": meta["source_label"] or meta["source"],
            "source_url": meta["source_url"],
        })
    return _csv_response(
        rows,
        ["indicator_id", "indicator", "theme", "region", "region_key", "year", "value", "unit", "source", "source_url"],
        f"divario-italia-indicatore-{indicator_id}.csv",
    )


@app.route("/download/indicator/<indicator_id>.json")
def indicator_download_json(indicator_id):
    payload = get_atlas_indicator(indicator_id)
    if payload is None:
        abort(404)
    return jsonify(payload)


@app.route("/download/quality-life/<url_level>")
def quality_life_download_csv(url_level):
    level = URL_LEVEL.get(url_level)
    if level is None:
        abort(404)
    payload = qb.build_bes_ranking(level, _quality_life_profile_arg())
    if payload is None:
        abort(404)
    rows = [_quality_life_export_row(row, payload) for row in payload["ranking"]]
    return _csv_response(
        rows,
        ["level", "profile", "rank", "territory", "territory_key", "region", "score", "delta_rank", "coverage"],
        f"divario-italia-qualita-vita-{url_level}-{payload['profile']['slug']}.csv",
    )


@app.route("/download/quality-life/<url_level>.json")
def quality_life_download_json(url_level):
    level = URL_LEVEL.get(url_level)
    if level is None:
        abort(404)
    payload = qb.build_bes_ranking(level, _quality_life_profile_arg())
    if payload is None:
        abort(404)
    return jsonify(payload)


def _quality_life_export_row(row, payload):
    return {
        "level": payload["level"],
        "profile": payload["profile"]["slug"],
        "rank": row["rank"],
        "territory": row["name"],
        "territory_key": row["key"],
        "region": row.get("region") or "",
        "score": row["score"],
        "delta_rank": row["delta_rank"],
        "coverage": row["coverage"],
    }


def _csv_response(rows, fieldnames, filename):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    response = Response(buffer.getvalue(), mimetype="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@app.route("/api/quality-life/profiles")
def quality_life_profiles_api():
    return jsonify({"profiles": qb.get_quality_life_profiles()})


@app.route("/api/quality-life/categories")
def quality_life_categories_api():
    return jsonify({"categories": qb.get_quality_life_categories()})


@app.route("/api/quality-life/<url_level>/rankings")
def quality_life_level_rankings_api(url_level):
    level = URL_LEVEL.get(url_level)
    if level is None:
        abort(404)
    payload = qb.build_bes_ranking(level, _quality_life_profile_arg())
    if payload is None:
        abort(404)
    return jsonify(payload)


@app.route("/api/quality-life/<url_level>/rankings/<profile_slug>")
def quality_life_level_ranking_profile_api(url_level, profile_slug):
    level = URL_LEVEL.get(url_level)
    if level is None:
        abort(404)
    payload = qb.build_bes_ranking(level, profile_slug)
    if payload is None:
        abort(404)
    return jsonify(payload)


@app.route("/api/quality-life/<url_level>/<territory_key>")
def quality_life_level_territory_api(url_level, territory_key):
    level = URL_LEVEL.get(url_level)
    if level is None:
        abort(404)
    payload = qb.build_bes_territory(level, territory_key, _quality_life_profile_arg())
    if payload is None:
        abort(404)
    return jsonify(payload)


# Back-compat aliases for the previous regional API paths.
@app.route("/api/quality-life/rankings")
def quality_life_rankings_api_legacy():
    payload = qb.build_bes_ranking("regione", _quality_life_profile_arg())
    return jsonify(payload) if payload else abort(404)


@app.route("/api/quality-life/rankings/<profile_slug>")
def quality_life_rankings_profile_api_legacy(profile_slug):
    payload = qb.build_bes_ranking("regione", profile_slug)
    return jsonify(payload) if payload else abort(404)


@app.route("/api/quality-life/region/<region_key>")
def quality_life_region_api_legacy(region_key):
    payload = qb.build_bes_territory("regione", region_key, _quality_life_profile_arg())
    return jsonify(payload) if payload else abort(404)


@app.route("/qualita-della-vita")
def quality_life_index():
    preview = qb.build_bes_ranking(URL_LEVEL["regioni"], qb.DEFAULT_PROFILE)
    preview_rows = preview["ranking"][:3] if preview else []
    return render_template(
        "quality_life_index.html",
        categories=qb.get_quality_life_categories(),
        profiles=qb.get_quality_life_profiles(),
        default_profile=qb.DEFAULT_PROFILE,
        preview_rows=preview_rows,
        has_province_data=qb.has_bes_data(URL_LEVEL["province"]),
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/qualita-della-vita",
    )


@app.route("/qualita-della-vita/classifica/<url_level>")
def quality_life_classifica(url_level):
    level = URL_LEVEL.get(url_level)
    if level is None:
        abort(404)
    slug = _quality_life_profile_arg()
    payload = qb.build_bes_ranking(level, slug)
    if payload is None:
        abort(404)
    quality_map_data = (
        {
            row["key"]: {"name": row["name"], "score": it_num(row["score"]), "rank": row["rank"]}
            for row in payload["ranking"]
        }
        if level == "regione" else {}
    )
    return render_template(
        "quality_life_classifica.html",
        data=payload,
        quality_map_data=quality_map_data,
        url_level=url_level,
        profiles=qb.get_quality_life_profiles(),
        active_profile=slug,
        default_profile=qb.DEFAULT_PROFILE,
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/qualita-della-vita/classifica/{url_level}{_profile_suffix(slug)}",
    )


@app.route("/qualita-della-vita/classifica")
def quality_life_classifica_redirect():
    return redirect(f"/qualita-della-vita/classifica/regioni{_profile_suffix(_quality_life_profile_arg())}", code=301)


@app.route("/qualita-della-vita/province")
def quality_life_province_redirect():
    return redirect(f"/qualita-della-vita/classifica/province{_profile_suffix(_quality_life_profile_arg())}", code=301)


@app.route("/qualita-della-vita/indicatore/<indicator_id>/<slug>")
def quality_life_indicator(indicator_id, slug):
    indicator = bes_data.get_bes_indicator_page(indicator_id)
    if indicator is None:
        abort(404)
    canonical_path = bes_data.bes_indicator_path(indicator_id, indicator["name"])
    if request.path != canonical_path:
        return redirect(canonical_path, code=301)
    territory_label = bes_data.bes_territory_label(indicator)
    response = make_response(render_template(
        "quality_life_indicator.html",
        indicator=indicator,
        territory_label=territory_label,
        source_breadcrumb_path="/qualita-della-vita/metodologia#indicatori-bes",
        source_breadcrumb_label="Indicatori BES",
        coverage_note_scope="sia per le regioni sia per le province",
        domain_label="Dominio BES",
        source_label="Istat, sistema BES",
        domain_prose="al dominio BES",
        seo_title=bes_data.bes_seo_title(indicator["name"], SITE_NAME, territory_label),
        seo_description=bes_data.bes_seo_description(
            indicator["name"],
            indicator["explain"]["plain"],
            territory_label,
        ),
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}{canonical_path}",
    ))
    if not indicator["indexable"]:
        response.headers["X-Robots-Tag"] = "noindex, follow"
    return response


@app.route("/qualita-della-vita/indicatore/multiscopo-<indicator_id>/<slug>")
def quality_life_multiscopo_indicator(indicator_id, slug):
    indicator = multiscopo_data.get_multiscopo_indicator_page(indicator_id)
    if indicator is None:
        abort(404)
    canonical_path = f"/qualita-della-vita/indicatore/multiscopo-{indicator_id}/{profiles.slugify(indicator['name'])}"
    if request.path != canonical_path:
        return redirect(canonical_path, code=301)
    territory_label = bes_data.bes_territory_label(indicator)
    response = make_response(render_template(
        "quality_life_indicator.html",
        indicator=indicator,
        territory_label=territory_label,
        source_breadcrumb_path="/qualita-della-vita/metodologia",
        source_breadcrumb_label="Indagine Multiscopo",
        coverage_note_scope="per le regioni",
        domain_label="Tema Istat",
        source_label="Istat, Indagine Multiscopo sulle famiglie",
        domain_prose="al tema Istat",
        seo_title=bes_data.bes_seo_title(indicator["name"], SITE_NAME, territory_label),
        seo_description=bes_data.bes_seo_description(
            indicator["name"],
            indicator["explain"]["plain"],
            territory_label,
        ),
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}{canonical_path}",
    ))
    if not indicator["indexable"]:
        response.headers["X-Robots-Tag"] = "noindex, follow"
    return response


@app.route("/qualita-della-vita/metodologia")
def quality_life_methodology():
    regioni = qb.build_bes_ranking("regione", qb.DEFAULT_PROFILE)
    province = qb.build_bes_ranking("provincia", qb.DEFAULT_PROFILE)
    return render_template(
        "quality_life_methodology.html",
        methodology_regioni=regioni["methodology"] if regioni else None,
        methodology_province=province["methodology"] if province else None,
        categories=qb.get_quality_life_categories(),
        profiles=qb.get_quality_life_profiles(),
        quality_life_indicators=[
            item for item in get_atlas_catalog()["indicators"]
            if item["quality_life_scored"]
        ],
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/qualita-della-vita/metodologia",
    )


@app.route("/gioco")
def game_page_legacy_redirect():
    return redirect("/quiz", code=301)


@app.route("/gioco/chi-e-maggiore")
def game_compare_page_legacy_redirect():
    return redirect("/quiz/chi-e-maggiore", code=301)


@app.route("/gioco/ordina")
def game_order_page_legacy_redirect():
    return redirect("/quiz/ordina", code=301)


@app.route("/quiz")
def game_hub_page():
    return render_template(
        "game_hub.html",
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/quiz",
    )


@app.route("/quiz/indovina-la-regione")
def game_page():
    return render_template(
        "game.html",
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/quiz/indovina-la-regione",
    )


@app.route("/quiz/chi-e-maggiore")
def game_compare_page():
    return render_template(
        "game_compare.html",
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/quiz/chi-e-maggiore",
    )


@app.route("/quiz/ordina")
def game_order_page():
    return render_template(
        "game_order.html",
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/quiz/ordina",
    )


@app.route("/quiz/classifica")
def game_leaderboard_page():
    return render_template(
        "game_leaderboard.html",
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/quiz/classifica",
    )


def _session_summary(session):
    if session is None:
        return None
    return {"streak": session["streak"], "best": session["best"], "rounds": session["rounds"]}


@app.route("/api/game/compare/round")
def game_compare_round_api():
    difficulty = request.args.get("difficulty", "0")
    result = quiz.compare_round(difficulty)
    state = quiz_tokens.load_state(request.args.get("token"), "compare")
    keys = [result["region_a"]["region_key"], result["region_b"]["region_key"]]
    result["token"] = quiz_tokens.bind_round(
        state, result["indicator"]["id"], result["indicator"]["year"], keys, result["difficulty"]
    )
    return jsonify(result)


@app.post("/api/game/compare/answer")
def game_compare_answer_api():
    payload = request.get_json(silent=True) or {}
    result = quiz.evaluate_compare(
        payload.get("indicator_id"),
        payload.get("year"),
        payload.get("region_a_key"),
        payload.get("region_b_key"),
        payload.get("choice"),
    )
    if result is None:
        abort(400)
    state = quiz_tokens.load_state(payload.get("token"), "compare")
    keys = [payload.get("region_a_key"), payload.get("region_b_key")]
    session, token = quiz_tokens.apply_answer(
        state, payload.get("indicator_id"), payload.get("year"), keys, result["correct"]
    )
    result["session"] = _session_summary(session)
    result["token"] = token
    return jsonify(result)


@app.route("/api/game/order/round")
def game_order_round_api():
    try:
        count = int(request.args.get("count", ""))
    except ValueError:
        abort(400)
    result = quiz.order_round(count)
    if result is None:
        abort(400)
    state = quiz_tokens.load_state(request.args.get("token"), "order")
    keys = [r["region_key"] for r in result["regions"]]
    result["token"] = quiz_tokens.bind_round(
        state, result["indicator"]["id"], result["indicator"]["year"], keys, count, count=count
    )
    return jsonify(result)


@app.post("/api/game/order/answer")
def game_order_answer_api():
    payload = request.get_json(silent=True) or {}
    region_keys = payload.get("region_keys")
    result = quiz.evaluate_order(
        payload.get("indicator_id"),
        payload.get("year"),
        region_keys,
    )
    if result is None:
        abort(400)
    state = quiz_tokens.load_state(payload.get("token"), "order")
    is_perfect = result["score"] == result["total"]
    session, token = quiz_tokens.apply_answer(
        state, payload.get("indicator_id"), payload.get("year"), region_keys or [], is_perfect
    )
    result["session"] = _session_summary(session)
    result["token"] = token
    return jsonify(result)


@app.route("/api/game/leaderboard")
def leaderboard_get_api():
    mode = request.args.get("mode", "")
    period = request.args.get("period", "all")
    if mode not in leaderboard.MODES:
        return jsonify({"error": "bad_mode"}), 400
    if period not in leaderboard.PERIODS:
        return jsonify({"error": "bad_period"}), 400
    try:
        limit = int(request.args.get("limit", leaderboard.DEFAULT_LIMIT))
    except ValueError:
        limit = leaderboard.DEFAULT_LIMIT
    entries = leaderboard.top(mode, period, limit)
    return jsonify({"mode": mode, "period": period, "entries": entries})


@app.post("/api/game/leaderboard")
def leaderboard_post_api():
    if not _rate_limit_ok(f"lb:{_client_ip()}", limit=5, window_s=60):
        return jsonify({"error": "rate_limited"}), 429

    payload = request.get_json(silent=True) or {}
    state = quiz_tokens.peek_state(payload.get("token"))
    if state is None:
        return jsonify({"error": "token_invalid"}), 400

    mode = state["m"]
    score = state.get("b", 0)
    if not score:
        return jsonify({"error": "score_missing"}), 400

    nickname, error = moderation.validate_nickname(payload.get("nickname"))
    if error:
        return jsonify({"error": error}), 400

    detail = {"count": state["c"]} if mode == "order" and state.get("c") else {}
    leaderboard.submit(mode, state["sid"], nickname, score, detail)
    rank_all, rank_week = leaderboard.ranks_for_session(mode, state["sid"])
    return jsonify({"ok": True, "mode": mode, "score": score, "rank_all": rank_all, "rank_week": rank_week})


@app.post("/api/game/leaderboard/admin/delete")
def leaderboard_admin_delete_api():
    """Rimozione manuale di una voce (moderazione), autenticata con
    SECRET_KEY invece che con un account: non c'è un pannello admin, questo
    endpoint serve solo per interventi occasionali via curl."""
    provided = request.headers.get("X-Admin-Key", "")
    if not hmac.compare_digest(provided, app.secret_key):
        abort(404)
    payload = request.get_json(silent=True) or {}
    mode = payload.get("mode")
    nickname = payload.get("nickname")
    if mode not in leaderboard.MODES or not nickname:
        return jsonify({"error": "bad_request"}), 400
    deleted = leaderboard.delete_entry(mode, nickname)
    return jsonify({"ok": True, "deleted": deleted})


@app.route("/api/game/regions")
def game_regions_api():
    return jsonify({"regions": profiles.all_regions_index()})


@app.route("/api/game/daily")
def game_daily_api():
    return jsonify(game.daily_payload())


@app.route("/api/game/daily/<iso_date>")
def game_daily_archive_api(iso_date):
    payload = game.daily_payload_for_date(iso_date)
    if payload is None:
        abort(404)
    return jsonify(payload)


@app.route("/api/game/archive")
def game_archive_api():
    return jsonify({"puzzles": game.archive_list()})


@app.route("/api/game/practice")
def game_practice_api():
    return jsonify(game.practice_payload())


@app.post("/api/game/guess")
def game_guess_api():
    payload = request.get_json(silent=True) or {}
    puzzle_id = payload.get("puzzle_id")
    region_key = payload.get("region_key")
    attempt = payload.get("attempt")
    if not isinstance(region_key, str) or not isinstance(attempt, int) or isinstance(attempt, bool):
        abort(400)
    result = game.evaluate_guess(puzzle_id, region_key, attempt)
    if result is None:
        abort(400)
    return jsonify(result)


@app.route("/sitemap.xml")
def sitemap():
    pages = [
        {"loc": f"{SITE_URL}/", "priority": "1.0"},
        {"loc": f"{SITE_URL}/atlante", "priority": "0.9"},
        {"loc": f"{SITE_URL}/blog", "priority": "0.8"},
        {"loc": f"{SITE_URL}/metodologia", "priority": "0.7"},
        {"loc": f"{SITE_URL}/regioni", "priority": "0.7"},
        {"loc": f"{SITE_URL}/temi", "priority": "0.6"},
        {"loc": f"{SITE_URL}/quiz", "priority": "0.7"},
        {"loc": f"{SITE_URL}/quiz/indovina-la-regione", "priority": "0.7"},
        {"loc": f"{SITE_URL}/quiz/chi-e-maggiore", "priority": "0.7"},
        {"loc": f"{SITE_URL}/quiz/ordina", "priority": "0.7"},
        {"loc": f"{SITE_URL}/qualita-della-vita", "priority": "0.8"},
        {"loc": f"{SITE_URL}/qualita-della-vita/classifica/regioni", "priority": "0.8"},
        {"loc": f"{SITE_URL}/qualita-della-vita/classifica/province", "priority": "0.8"},
        {"loc": f"{SITE_URL}/qualita-della-vita/metodologia", "priority": "0.6"},
        {"loc": f"{SITE_URL}/privacy", "priority": "0.4"},
    ]
    for post in get_posts():
        pages.append({
            "loc": post["url"],
            "lastmod": post.get("date_modified", post["date"]).isoformat(),
            "priority": "0.7",
        })
    for region in profiles.all_regions_index():
        pages.append({"loc": f"{SITE_URL}{region['path']}", "priority": "0.7"})
    for theme in all_atlas_themes_index():
        pages.append({"loc": f"{SITE_URL}{theme['path']}", "priority": "0.5"})
    for item in get_catalog()["indicators"]:
        if not profiles.is_search_indexable_indicator(item):
            continue
        pages.append({
            "loc": f"{SITE_URL}{profiles.indicator_path(item['id'], item['name'])}",
            "lastmod": f"{item['year_max']}-12-31",
            "priority": "0.6",
        })
    for item in bes_data.all_bes_indicators():
        if not item["indexable"]:
            continue
        pages.append({
            "loc": f"{SITE_URL}{item['path']}",
            "lastmod": f"{item['year_max']}-12-31",
            "priority": "0.6",
        })
    if multiscopo_data.has_multiscopo_data():
        for item in multiscopo_data.all_multiscopo_indicators():
            if not item["indexable"]:
                continue
            pages.append({
                "loc": f"{SITE_URL}{item['path']}",
                "lastmod": f"{item['year_max']}-12-31",
                "priority": "0.6",
            })
    xml = render_template("sitemap.xml", pages=pages)
    return Response(xml, mimetype="application/xml")


# Content-Signals preamble + AI-bot blocklist. These were previously injected by
# Cloudflare's managed robots.txt; kept here so robots.txt has a single source of
# truth after the Cloudflare managed injection is disabled (2026-07-01). To change
# the Content-Signal policy or the AI-bot list, edit these constants.
_ROBOTS_CONTENT_SIGNALS_PREAMBLE = """\
# As a condition of accessing this website, you agree to abide by the following
# content signals:

# (a)  If a Content-Signal = yes, you may collect content for the corresponding
#      use.
# (b)  If a Content-Signal = no, you may not collect content for the
#      corresponding use.
# (c)  If the website operator does not include a Content-Signal for a
#      corresponding use, the website operator neither grants nor restricts
#      permission via Content-Signal with respect to the corresponding use.

# The content signals and their meanings are:

# search:   building a search index and providing search results (e.g., returning
#           hyperlinks and short excerpts from your website's contents). Search does not
#           include providing AI-generated search summaries.
# ai-input: inputting content into one or more AI models (e.g., retrieval
#           augmented generation, grounding, or other real-time taking of content for
#           generative AI search answers).
# ai-train: training or fine-tuning AI models.

# ANY RESTRICTIONS EXPRESSED VIA CONTENT SIGNALS ARE EXPRESS RESERVATIONS OF
# RIGHTS UNDER ARTICLE 4 OF THE EUROPEAN UNION DIRECTIVE 2019/790 ON COPYRIGHT
# AND RELATED RIGHTS IN THE DIGITAL SINGLE MARKET."""

# search + real-time AI grounding (ai-input) are permitted so generative answer
# engines can cite the atlas, while model training (ai-train) stays reserved.
_ROBOTS_CONTENT_SIGNAL = "search=yes,ai-input=yes,ai-train=no"
# Generative answer engines allowed to fetch pages for real-time citation and
# grounding. These are the retrieval/citation crawlers, not the training ones:
# unblocking them is what makes the site eligible to be surfaced in AI answers.
_ROBOTS_AI_ANSWER_BOTS = (
    "OAI-SearchBot",
    "ChatGPT-User",
    "PerplexityBot",
    "Perplexity-User",
    "Claude-SearchBot",
    "Claude-User",
    "Google-Extended",
)
# AI training crawlers kept blocked so the ai-train=no reservation stays
# enforceable. Anthropic and OpenAI split retrieval from training by user agent,
# so ClaudeBot/GPTBot are blocked here while their answer bots above are allowed.
_ROBOTS_AI_TRAINING_BOTS = (
    "Amazonbot",
    "Applebot-Extended",
    "Bytespider",
    "CCBot",
    "ClaudeBot",
    "CloudflareBrowserRenderingCrawler",
    "GPTBot",
    "meta-externalagent",
)
# Machine endpoints and duplicate legacy dashboards kept out of the crawl.
_ROBOTS_DISALLOW_PATHS = ("/api/", "/data", "/legacy", "/legacy-reddito")


@app.route("/robots.txt")
def robots():
    lines = [_ROBOTS_CONTENT_SIGNALS_PREAMBLE, ""]
    # Default group: content signals, then the shared path rules for all crawlers.
    lines += ["User-agent: *", f"Content-Signal: {_ROBOTS_CONTENT_SIGNAL}", "Allow: /"]
    lines += [f"Disallow: {path}" for path in _ROBOTS_DISALLOW_PATHS]
    lines.append("")
    # Answer-engine group: one group for all citation crawlers, so each reads its
    # own rules (ai-input allowed) and inherits the same crawl boundaries as "*".
    lines += [f"User-agent: {bot}" for bot in _ROBOTS_AI_ANSWER_BOTS]
    lines += [f"Content-Signal: {_ROBOTS_CONTENT_SIGNAL}", "Allow: /"]
    lines += [f"Disallow: {path}" for path in _ROBOTS_DISALLOW_PATHS]
    lines.append("")
    for bot in _ROBOTS_AI_TRAINING_BOTS:
        lines += [f"User-agent: {bot}", "Disallow: /", ""]
    lines.append(f"# Curated index for language models: {SITE_URL}/llms.txt")
    lines.append(f"# Extended corpus for language models: {SITE_URL}/llms-full.txt")
    lines.append(f"Sitemap: {SITE_URL}/sitemap.xml")
    return Response("\n".join(lines) + "\n", mimetype="text/plain")


@app.route("/llms.txt")
def llms_txt():
    """Curated Markdown index for language models (llmstxt.org convention).

    Generated from the live catalog and blog so the entry points, featured
    indicators and recent articles a generative engine sees stay in sync with
    the site instead of drifting from a hand-maintained file.
    """
    featured = _home_featured_indicator_links()
    recent_posts = get_posts()[:8]
    lines = [
        "# Divario Italia",
        "",
        "> Atlante degli indicatori territoriali Istat: confronto tra regioni "
        "italiane su economia, lavoro, demografia, salute e qualita della vita, "
        "con serie storiche, fonti verificate e dati aperti in CSV e JSON.",
        "",
        "Divario Italia (divarioitalia.it) pubblica i dati Istat sullo sviluppo "
        "dei territori italiani. Ogni pagina indicatore espone la definizione, "
        "l'ultimo anno disponibile, la copertura regionale, la fonte primaria e "
        "i download strutturati. I numeri provengono dalla Banca dati "
        "territoriale per le politiche di sviluppo di Istat e dal BES dei "
        "Territori. I contenuti sono citabili con attribuzione a \"Divario "
        "Italia\" e alla fonte Istat.",
        "",
        "## Sezioni principali",
        f"- [Atlante degli indicatori]({SITE_URL}/atlante): mappa interattiva e catalogo regionale degli indicatori territoriali.",
        f"- [Regioni]({SITE_URL}/regioni): profilo di ogni regione italiana con i suoi indicatori chiave.",
        f"- [Temi]({SITE_URL}/temi): indicatori raggruppati per area, da economia e lavoro a demografia, salute e istruzione.",
        f"- [Qualita della vita]({SITE_URL}/qualita-della-vita): classifiche di regioni e province con pesi e metodo dichiarati.",
        f"- [Metodologia e fonti]({SITE_URL}/metodologia): metodo, fonti Istat, criteri di qualita e limiti dei confronti.",
        f"- [Blog]({SITE_URL}/blog): analisi data-driven sui divari territoriali, con numeri verificati e link all'atlante.",
        "",
        "## Indicatori in evidenza",
    ]
    for item in featured:
        summary = " ".join((item.get("summary") or "").split())
        detail = f" {summary}" if summary else ""
        lines.append(
            f"- [{item['name']}]({SITE_URL}{item['path']}):{detail} Ultimo anno {item['year']}, tema {item['theme']}."
        )
    lines += ["", "## Articoli recenti"]
    for post in recent_posts:
        description = " ".join((post.get("description") or "").split())
        detail = f": {description}" if description else ""
        lines.append(f"- [{post['title']}]({post['url']}){detail}")
    lines += [
        "",
        "## Note per i modelli linguistici",
        "- Fonte primaria: Istat, Banca dati territoriale per le politiche di sviluppo e BES dei Territori.",
        "- Licenza dei dati: Creative Commons BY 3.0 IT. Cita \"Divario Italia\" e la fonte Istat.",
        f"- Dati strutturati per indicatore: {SITE_URL}/download/indicator/<id>.csv e {SITE_URL}/download/indicator/<id>.json.",
        f"- Indice completo delle pagine: {SITE_URL}/sitemap.xml.",
        f"- Versione estesa con definizioni e classifiche complete: {SITE_URL}/llms-full.txt.",
        "- I confronti descrivono differenze osservate, non rapporti di causa. Anni e coperture possono variare tra indicatori.",
        "",
    ]
    return Response("\n".join(lines) + "\n", content_type="text/plain; charset=utf-8")


def _llms_indicator_full_block(indicator_id):
    """Full-text block for one indicator: definition, source and live ranking.

    Reuses the same catalog loaders and direction ordering as the indicator
    landing page, so the numbers a model reads here match the published page.
    """
    payload = get_atlas_indicator(indicator_id)
    if payload is None:
        return None
    meta = payload["metadata"]
    explain = meta.get("explain") or {}
    year = meta["year_max"]
    year_view = get_atlas_indicator_year(indicator_id, year)
    values = year_view["values"]  # sorted by value desc
    if explain.get("direction") in ("lower_better", "higher_worse"):
        values = list(reversed(values))
    unit = meta.get("unit") or ""
    path = profiles.indicator_path(indicator_id, meta["name"])
    lines = [f"### {meta['name']}", f"{SITE_URL}{path}", ""]
    if explain.get("plain"):
        lines.append(explain["plain"])
    if explain.get("reading"):
        lines.append(f"Come si legge: {explain['reading']}")
    if explain.get("caveat"):
        lines.append(f"Limite: {explain['caveat']}")
    lines.append(
        f"Fonte: {meta.get('source', 'Istat')}. Unita di misura: {unit or 'n.d.'}. "
        f"Copertura: {meta['year_min']}-{meta['year_max']}, {len(meta['regions'])} regioni."
    )
    lines += ["", f"Classifica {year} (posizione. regione: valore):"]
    for position, row in enumerate(values, 1):
        lines.append(f"{position}. {row['region']}: {it_num(row['value'], 2)} {unit}".rstrip())
    lines.append("")
    return "\n".join(lines)


@app.route("/llms-full.txt")
def llms_full_txt():
    """Extended Markdown corpus for language models: full indicator text.

    Where /llms.txt is a curated map, this file carries the full definition and
    the complete regional ranking of the flagship indicators plus a compact
    catalogue of every indexable indicator, so a model can ground an answer in a
    single fetch without crawling each page.
    """
    lines = [
        "# Divario Italia, testo esteso per i modelli linguistici",
        "",
        "> Definizioni complete e classifiche regionali degli indicatori "
        "territoriali Istat pubblicati su divarioitalia.it. I numeri coincidono "
        "con le pagine indicatore del sito. Cita \"Divario Italia\" e la fonte "
        "Istat.",
        "",
        "## Metodologia in breve",
        "La fonte primaria e la Banca dati territoriale per le politiche di "
        "sviluppo di Istat, integrata dal BES e dal BES dei Territori per la "
        "qualita della vita. Ogni indicatore ha una direzione dichiarata: per "
        "alcuni un valore piu alto e positivo, per altri e negativo, per altri "
        "serve solo come contesto. I confronti descrivono differenze osservate "
        "tra territori e non dimostrano da soli un rapporto di causa. Anni e "
        "coperture possono variare tra indicatori. Licenza dei dati: Creative "
        "Commons BY 3.0 IT.",
        "",
        "## Indicatori in evidenza, testo completo",
    ]
    for indicator_id in _HOME_FEATURED_INDICATORS:
        block = _llms_indicator_full_block(indicator_id)
        if block:
            lines.append(block)

    lines.append("## Catalogo completo degli indicatori indicizzabili")
    lines.append("")
    for item in get_catalog()["indicators"]:
        if not profiles.is_search_indexable_indicator(item):
            continue
        plain = " ".join(((item.get("explain") or {}).get("plain") or "").split())
        path = profiles.indicator_path(item["id"], item["name"])
        detail = f" {plain}" if plain else ""
        lines.append(
            f"- [{item['name']}]({SITE_URL}{path}): tema {item['theme']}, "
            f"unita {item.get('unit') or 'n.d.'}, copertura {item['year_min']}-{item['year_max']}.{detail}"
        )
    lines.append("")
    return Response("\n".join(lines) + "\n", content_type="text/plain; charset=utf-8")


@app.route("/ads.txt")
def ads_txt():
    if not config.ADSENSE_CLIENT:
        abort(404)
    pub = config.ADSENSE_CLIENT.replace("ca-", "")
    return Response(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n", mimetype="text/plain")


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'img/favicon.ico', mimetype='image/vnd.microsoft.icon')


def _home_featured_indicator_links():
    by_id = {str(item["id"]): item for item in get_catalog()["indicators"]}
    featured = []
    for indicator_id in _HOME_FEATURED_INDICATORS:
        item = by_id.get(indicator_id)
        if not item or not profiles.is_search_indexable_indicator(item):
            continue
        featured.append({
            "name": item["name"],
            "theme": item["theme"],
            "year": item["year_max"],
            "path": profiles.indicator_path(item["id"], item["name"]),
            "summary": (item.get("explain") or {}).get("plain", ""),
        })
    return featured


def _home_map_hero():
    """Data for the homepage's interactive choropleth: a curated indicator
    picker (same flagship set as _HOME_FEATURED_INDICATORS), the chosen
    indicator's per-region colors, and a JSON tooltip payload for the hover/
    click behaviour in home-map.js. The indicator choice lives in ?indicator=
    so picking one is a plain link, no JS required to change the map."""
    by_id = {str(item["id"]): item for item in get_catalog()["indicators"]}
    options = [
        {"id": indicator_id, "name": by_id[indicator_id]["name"]}
        for indicator_id in _HOME_MAP_INDICATORS
        if indicator_id in by_id
    ]
    requested = request.args.get("indicator")
    selected_id = requested if requested in _HOME_MAP_INDICATORS and requested in by_id else _HOME_MAP_INDICATORS[0]

    payload = get_atlas_indicator(selected_id)
    meta = payload["metadata"]
    year = meta["year_max"]
    values = get_atlas_indicator_year(selected_id, year)["values"]
    direction = (meta.get("explain") or {}).get("direction")
    ranked = list(reversed(values)) if direction in ("lower_better", "higher_worse") else values
    unit = indicator_notes.value_unit_label(meta["name"], meta.get("unit"))
    total = len(ranked)

    tooltip_data = {
        row["region_key"]: {
            "name": row["region"],
            "value": it_num(row["value"], 2),
            "unit": unit,
            "rank": position,
            "total": total,
        }
        for position, row in enumerate(ranked, 1)
    }

    return {
        "options": options,
        "selected_id": selected_id,
        "indicator_name": meta["name"],
        "theme": meta["theme"],
        "year": year,
        "colors": indicator_notes.region_choropleth_colors(values),
        "tooltip_data": tooltip_data,
    }


def _home_capabilities(total_indicators):
    return [
        {
            "kicker": "Atlante",
            "title": f"{total_indicators} indicatori esplorabili",
            "body": "Tutti gli indicatori Istat delle politiche di sviluppo, per tema e completezza.",
            "href": "/atlante",
            "cta": "Apri l'atlante",
        },
        {
            "kicker": "Regioni",
            "title": "Schede regione",
            "body": "Punti di forza, punti deboli e ranking tematico per tutte le 20 regioni.",
            "href": "/regioni",
            "cta": "Sfoglia le regioni",
        },
        {
            "kicker": "Confronta",
            "title": "Regione contro regione",
            "body": "Metti a confronto due o tre regioni su qualsiasi indicatore, con mappa e serie storica.",
            "href": "/atlante?view=confronto",
            "cta": "Confronta ora",
        },
        {
            "kicker": "Temi",
            "title": "Aree e temi",
            "body": "Economia, lavoro, salute, ambiente: ogni tema raccoglie i suoi indicatori in una pagina.",
            "href": "/temi",
            "cta": "Scopri i temi",
        },
        {
            "kicker": "Qualità della vita",
            "title": "Classifica composita",
            "body": "Un indice sperimentale che unisce salute, lavoro, istruzione e ambiente.",
            "href": "/qualita-della-vita",
            "cta": "Vedi la classifica",
        },
        {
            "kicker": "Quiz",
            "title": "Metti alla prova quello che sai",
            "body": "Tre giochi rapidi sui dati Istat, con una classifica settimanale.",
            "href": "/quiz",
            "cta": "Gioca ora",
        },
    ]


def _home_story_cards():
    """Real 'chi guida, chi resta indietro' highlights for the homepage,
    limited to indicators with a declared higher_better/lower_better
    direction so the framing is something the data actually supports."""
    cards = []
    for indicator_id in _HOME_STORY_INDICATORS:
        payload = get_atlas_indicator(indicator_id)
        if payload is None:
            continue
        meta = payload["metadata"]
        year = meta["year_max"]
        values = get_atlas_indicator_year(indicator_id, year)["values"]
        direction = (meta.get("explain") or {}).get("direction")
        ranked = list(reversed(values)) if direction in ("lower_better", "higher_worse") else values
        best, worst = ranked[0], ranked[-1]
        unit = indicator_notes.value_unit_label(meta["name"], meta.get("unit"))
        if direction == "lower_better":
            note = (
                f"{worst['region']} resta indietro con {it_num(worst['value'], 2)} {unit}, "
                f"{best['region']} fa meglio di tutte."
            )
        else:
            note = (
                f"{best['region']} guida con {it_num(best['value'], 2)} {unit}, "
                f"{worst['region']} chiude a {it_num(worst['value'], 2)} {unit}."
            )
        cards.append({
            "theme": meta["theme"],
            "name": meta["name"],
            "value": it_num(best["value"], 2),
            "unit": unit,
            "best_region": best["region"],
            "year": year,
            "note": note,
            "spark_points": indicator_notes.sparkline_points(meta.get("spark") or [], width=84, height=36),
            "path": profiles.indicator_path(indicator_id, meta["name"]),
        })
    return cards


def _home_qol_preview():
    payload = qb.build_bes_ranking("regione", qb.DEFAULT_PROFILE)
    if payload is None:
        return None
    ranking = payload["ranking"]
    return {
        "top5": ranking[:5],
        "bottom3": list(reversed(ranking[-3:])),
        "spread": it_num(ranking[0]["score"] - ranking[-1]["score"]),
        "leader": ranking[0]["name"],
        "last": ranking[-1]["name"],
    }


def _home_themes_preview():
    """'Temi e aree' cards: for each macro-area, its indicator/theme counts plus
    the region in front and the region trailing, computed as the mean oriented
    score across the area's scoreable indicators (best = 1.0). Purely derived
    from the data, no placeholder leaders."""
    matrix = profiles._percentile_matrix()
    meta = profiles._indicator_meta()
    cards = []
    for group in atlas_themes_by_macro_area():
        area = group["macro_area"]
        totals = {}  # region_key -> [sum_oriented, count]
        for ind_id, by_region in matrix.items():
            info = meta.get(ind_id)
            if not info or info["macro_area"] != area:
                continue
            direction = info["direction"]
            if direction not in profiles.SCOREABLE_DIRECTIONS:
                continue
            for region_key, percentile in by_region.items():
                oriented = profiles._oriented(percentile, direction)
                acc = totals.setdefault(region_key, [0.0, 0])
                acc[0] += oriented
                acc[1] += 1
        ranked = sorted(
            ((key, total / n) for key, (total, n) in totals.items() if n),
            key=lambda kv: kv[1],
            reverse=True,
        )
        if not ranked:
            continue
        cards.append({
            "area": area,
            "count": group["indicator_count"],
            "theme_count": len(group["themes"]),
            "themes": [t["theme"] for t in group["themes"][:4]],
            "best": profiles.region_name(ranked[0][0]),
            "worst": profiles.region_name(ranked[-1][0]),
        })
    return cards


def _home_compare_preview():
    """'Confronta' preview: three real regions across three scoreable indicators,
    with a bar filled by oriented position (best = full) and the real ranking."""
    rows = []
    for indicator_id in _HOME_COMPARE_INDICATORS:
        payload = get_atlas_indicator(indicator_id)
        if payload is None:
            continue
        meta = payload["metadata"]
        year = meta["year_max"]
        values = get_atlas_indicator_year(indicator_id, year)["values"]
        direction = (meta.get("explain") or {}).get("direction")
        invert = direction in ("lower_better", "higher_worse")
        ranked = list(reversed(values)) if invert else values
        rank_by_key = {row["region_key"]: pos for pos, row in enumerate(ranked, 1)}
        value_by_key = {row["region_key"]: row["value"] for row in values}
        vals = [row["value"] for row in values]
        low, high = min(vals), max(vals)
        span = (high - low) or 1
        unit = indicator_notes.value_unit_label(meta["name"], meta.get("unit"))
        entries = []
        for key, color in zip(_HOME_COMPARE_REGIONS, _HOME_COMPARE_COLORS):
            if key not in value_by_key:
                continue
            fraction = (value_by_key[key] - low) / span
            if invert:
                fraction = 1 - fraction
            entries.append({
                "name": profiles.region_name(key),
                "value": it_num(value_by_key[key], 2),
                "unit": unit,
                "rank": rank_by_key[key],
                "total": len(ranked),
                "pct": max(6, round(fraction * 100)),
                "color": color,
            })
        if entries:
            rows.append({"theme": meta["theme"], "name": meta["name"], "entries": entries})
    if not rows:
        return None
    legend = [
        {"name": profiles.region_name(key), "color": color}
        for key, color in zip(_HOME_COMPARE_REGIONS, _HOME_COMPARE_COLORS)
    ]
    return {"legend": legend, "rows": rows}


def _home_quiz_games():
    return [
        {
            "name": "Indovina la Regione",
            "desc": "Mappa e indizi Istat che si sbloccano a ogni tentativo sbagliato. Sei tentativi.",
            "meta": "circa 2 minuti",
            "href": "/quiz/indovina-la-regione",
        },
        {
            "name": "Chi è maggiore?",
            "desc": "Due regioni, un indicatore. Scegli quale ha il valore più alto.",
            "meta": "testa a testa",
            "href": "/quiz/chi-e-maggiore",
        },
        {
            "name": "Ordina le regioni",
            "desc": "Cinque regioni da ordinare dal valore più alto al più basso, con credito parziale.",
            "meta": "credito parziale",
            "href": "/quiz/ordina",
        },
    ]


def _clean_event_name(value):
    value = str(value or "")[:64]
    return value if re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]*", value) else ""


def _clean_event_params(value):
    if not isinstance(value, dict):
        return {}
    params = {}
    for key, raw in value.items():
        clean_key = _clean_event_name(key)
        if not clean_key:
            continue
        clean_value = _clean_event_value(raw)
        if clean_value != "":
            params[clean_key] = clean_value
        if len(params) >= 12:
            break
    return params


def _clean_event_value(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if value is None:
        return ""
    return " ".join(str(value).split())[:160]
