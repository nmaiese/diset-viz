from app import app
from app.cache import cache
from app.blog import SITE_NAME, SITE_URL, all_tags, get_post, get_posts
from app.data import get_catalog, get_indicator, get_indicator_year, get_rows, search_indicators

from flask import Response, abort, render_template, request, send_from_directory, url_for
from flask.json import jsonify

import csv, os

from app import config


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


@app.route("/sitemap.xml")
def sitemap():
    pages = [
        {"loc": f"{SITE_URL}/", "priority": "1.0"},
        {"loc": f"{SITE_URL}/blog", "priority": "0.8"},
        {"loc": f"{SITE_URL}/privacy", "priority": "0.4"},
    ]
    for post in get_posts():
        pages.append({
            "loc": post["url"],
            "lastmod": post["date"].isoformat(),
            "priority": "0.7",
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
