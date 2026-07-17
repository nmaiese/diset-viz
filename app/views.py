from app import app
from app.cache import cache
from app.blog import SITE_NAME, SITE_URL, all_tags, get_post, get_posts
from app.data import (
    get_catalog,
    get_indicator,
    get_indicator_year,
    get_rows,
    indicator_trend_stats,
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
from app import indicator_notes
from app import quality_life_bes as qb
from app import bes_data
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
@cache.cached(timeout=300)
def main():
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
        indicator_payload = get_indicator(post["indicator"])
        if indicator_payload:
            meta = indicator_payload["metadata"]
            post["indicator_path"] = profiles.indicator_path(post["indicator"], meta["name"])
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
    trend_note = indicator_notes.trend_framing(direction, stats["avg_change_pct"])
    is_indexable = profiles.is_search_indexable_indicator(meta)
    map_colors = indicator_notes.region_choropleth_colors(values)
    spark_points = indicator_notes.sparkline_points(meta.get("spark") or [])
    response = make_response(render_template(
        "indicator_page.html",
        meta=meta,
        values=values,
        best=best,
        worst=worst,
        year=year,
        stats=stats,
        trend_note=trend_note,
        is_indexable=is_indexable,
        map_colors=map_colors,
        spark_points=spark_points,
        seo_title=indicator_notes.seo_title(meta["name"], SITE_NAME),
        seo_description=indicator_notes.seo_description(plain, meta["year_max"], len(meta["regions"])),
        theme_path=profiles.theme_path(meta["theme"]),
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}{canonical_path}",
    ))
    if not is_indexable:
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
    return render_template(
        "quality_life_classifica.html",
        data=payload,
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
    response = make_response(render_template(
        "quality_life_indicator.html",
        indicator=indicator,
        seo_title=bes_data.bes_seo_title(indicator["name"], SITE_NAME),
        seo_description=bes_data.bes_seo_description(indicator["name"]),
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

_ROBOTS_CONTENT_SIGNAL = "search=yes,ai-train=no"
_ROBOTS_AI_BOTS = (
    "Amazonbot",
    "Applebot-Extended",
    "Bytespider",
    "CCBot",
    "ClaudeBot",
    "CloudflareBrowserRenderingCrawler",
    "Google-Extended",
    "GPTBot",
    "meta-externalagent",
)
# Machine endpoints and duplicate legacy dashboards kept out of the crawl.
_ROBOTS_DISALLOW_PATHS = ("/api/", "/data", "/legacy", "/legacy-reddito")


@app.route("/robots.txt")
def robots():
    lines = [_ROBOTS_CONTENT_SIGNALS_PREAMBLE, ""]
    # Single crawler group: content signals, then the path rules for all crawlers.
    lines += ["User-agent: *", f"Content-Signal: {_ROBOTS_CONTENT_SIGNAL}", "Allow: /"]
    lines += [f"Disallow: {path}" for path in _ROBOTS_DISALLOW_PATHS]
    lines.append("")
    for bot in _ROBOTS_AI_BOTS:
        lines += [f"User-agent: {bot}", "Disallow: /", ""]
    lines.append(f"Sitemap: {SITE_URL}/sitemap.xml")
    return Response("\n".join(lines) + "\n", mimetype="text/plain")


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
