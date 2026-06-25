from app import app
from app.cache import cache
from app.blog import SITE_NAME, SITE_URL, all_tags, get_post, get_posts
from app.data import get_catalog, get_indicator, get_indicator_year, get_rows, search_indicators
from app import profiles
from app import quality_life as ql

from flask import Response, abort, redirect, render_template, request, send_from_directory, url_for
from flask.json import jsonify

import csv, json, os, re

from app import config


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

@cache.memoize(timeout=100)
@app.route("/data")
def data():
    data = get_all_data()
    return jsonify(data)


@cache.cached(timeout=300)
@app.route("/")
def main():
    return render_template('app.html')


@cache.cached(timeout=300)
@app.route("/legacy")
def legacy():
    return render_template('legacy.html')


@cache.cached(timeout=300)
@app.route("/legacy-reddito")
def legacy_reddito():
    return render_template('legacy_reddito.html')


@app.route("/api/catalog")
def catalog():
    return jsonify(get_catalog())


@app.route("/api/search")
def search():
    return jsonify({
        "results": search_indicators(
            query=request.args.get("q", ""),
            theme=request.args.get("theme"),
        )
    })


@app.route("/api/indicator/<indicator_id>")
def indicator(indicator_id):
    payload = get_indicator(indicator_id)
    if payload is None:
        abort(404)
    return jsonify(payload)


@app.route("/api/indicator/<indicator_id>/year/<int:year>")
def indicator_year(indicator_id, year):
    payload = get_indicator_year(indicator_id, year)
    if payload is None:
        abort(404)
    return jsonify(payload)


@app.post("/api/events")
def analytics_event():
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


@app.route("/indicatore/<slug>")
def indicator_page(slug):
    match = re.match(r"^(\d+)(?:-.*)?$", slug)
    if not match:
        abort(404)
    indicator_id = match.group(1)
    payload = get_indicator(indicator_id)
    if payload is None:
        abort(404)

    meta = payload["metadata"]
    canonical_path = profiles.indicator_path(indicator_id, meta["name"])
    if f"/indicatore/{slug}" != canonical_path:
        return redirect(canonical_path, code=301)

    year = meta["year_max"]
    year_view = get_indicator_year(indicator_id, year)

    # Order the ranking so #1 is the best-performing region for this indicator's
    # direction; for contextual indicators "best" is undefined, so keep raw order.
    direction = (meta.get("explain") or {}).get("direction")
    values = year_view["values"]  # already sorted by value desc
    if direction in ("lower_better", "higher_worse"):
        values = list(reversed(values))
    scoreable = direction in profiles.SCOREABLE_DIRECTIONS
    best = values[0] if values and scoreable else None
    worst = values[-1] if values and scoreable else None

    return render_template(
        "indicator_page.html",
        meta=meta,
        values=values,
        best=best,
        worst=worst,
        year=year,
        theme_path=profiles.theme_path(meta["theme"]),
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}{canonical_path}",
    )


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


@app.route("/tema/<theme_slug>")
def theme_page(theme_slug):
    profile = profiles.theme_profile(theme_slug)
    if profile is None:
        abort(404)
    return render_template(
        "theme_page.html",
        profile=profile,
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/tema/{theme_slug}",
    )


@app.route("/regioni")
def regions_index():
    return render_template(
        "regions_index.html",
        regions=profiles.all_regions_index(),
        overview=profiles.regions_overview(),
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/regioni",
    )


@app.route("/temi")
def themes_index():
    groups = profiles.themes_by_macro_area()
    total = sum(group["indicator_count"] for group in groups)
    return render_template(
        "themes_index.html",
        groups=groups,
        total=total,
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/temi",
    )


def _quality_life_profile_arg():
    """Resolve the requested profile slug from ?profilo= (or ?profile=)."""
    return request.args.get("profilo") or request.args.get("profile") or ql.DEFAULT_PROFILE


@app.route("/api/quality-life/profiles")
def quality_life_profiles_api():
    return jsonify({"profiles": ql.get_quality_life_profiles()})


@app.route("/api/quality-life/categories")
def quality_life_categories_api():
    return jsonify({"categories": ql.get_quality_life_categories()})


@app.route("/api/quality-life/rankings")
def quality_life_rankings_api():
    payload = ql.build_quality_life_ranking(_quality_life_profile_arg())
    if payload is None:
        abort(404)
    return jsonify(payload)


@app.route("/api/quality-life/rankings/<profile_slug>")
def quality_life_ranking_profile_api(profile_slug):
    payload = ql.build_quality_life_ranking(profile_slug)
    if payload is None:
        abort(404)
    return jsonify(payload)


@app.route("/api/quality-life/region/<region_key>")
def quality_life_region_api(region_key):
    payload = ql.build_quality_life_region_profile(region_key, _quality_life_profile_arg())
    if payload is None:
        abort(404)
    return jsonify(payload)


@app.route("/qualita-della-vita")
def quality_life_index():
    return render_template(
        "quality_life_index.html",
        categories=ql.get_quality_life_categories(),
        profiles=ql.get_quality_life_profiles(),
        default_profile=ql.DEFAULT_PROFILE,
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/qualita-della-vita",
    )


@app.route("/qualita-della-vita/classifica")
def quality_life_ranking():
    slug = _quality_life_profile_arg()
    payload = ql.build_quality_life_ranking(slug)
    if payload is None:
        abort(404)
    suffix = "" if slug == ql.DEFAULT_PROFILE else f"?profilo={slug}"
    return render_template(
        "quality_life_ranking.html",
        data=payload,
        profiles=ql.get_quality_life_profiles(),
        active_profile=slug,
        default_profile=ql.DEFAULT_PROFILE,
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/qualita-della-vita/classifica{suffix}",
    )


@app.route("/qualita-della-vita/metodologia")
def quality_life_methodology():
    payload = ql.build_quality_life_ranking(ql.DEFAULT_PROFILE)
    return render_template(
        "quality_life_methodology.html",
        methodology=payload["methodology"],
        categories=ql.get_quality_life_categories(),
        profiles=ql.get_quality_life_profiles(),
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/qualita-della-vita/metodologia",
    )


@app.route("/sitemap.xml")
def sitemap():
    pages = [
        {"loc": f"{SITE_URL}/", "priority": "1.0"},
        {"loc": f"{SITE_URL}/blog", "priority": "0.8"},
        {"loc": f"{SITE_URL}/regioni", "priority": "0.7"},
        {"loc": f"{SITE_URL}/temi", "priority": "0.6"},
        {"loc": f"{SITE_URL}/qualita-della-vita", "priority": "0.8"},
        {"loc": f"{SITE_URL}/qualita-della-vita/classifica", "priority": "0.8"},
        {"loc": f"{SITE_URL}/qualita-della-vita/metodologia", "priority": "0.6"},
        {"loc": f"{SITE_URL}/privacy", "priority": "0.4"},
    ]
    for post in get_posts():
        pages.append({
            "loc": post["url"],
            "lastmod": post["date"].isoformat(),
            "priority": "0.7",
        })
    for region in profiles.all_regions_index():
        pages.append({"loc": f"{SITE_URL}{region['path']}", "priority": "0.7"})
    for theme in profiles.all_themes_index():
        pages.append({"loc": f"{SITE_URL}{theme['path']}", "priority": "0.5"})
    for item in get_catalog()["indicators"]:
        pages.append({
            "loc": f"{SITE_URL}{profiles.indicator_path(item['id'], item['name'])}",
            "lastmod": f"{item['year_max']}-12-31",
            "priority": "0.6",
        })
    xml = render_template("sitemap.xml", pages=pages)
    return Response(xml, mimetype="application/xml")


@app.route("/robots.txt")
def robots():
    body = f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n"
    return Response(body, mimetype="text/plain")


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
