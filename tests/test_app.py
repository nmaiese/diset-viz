import csv
import unittest
from pathlib import Path

from app import app


class AppSmokeTest(unittest.TestCase):
    def test_routes_respond(self):
        client = app.test_client()

        home = client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertEqual(home.headers["Referrer-Policy"], "strict-origin-when-cross-origin")
        self.assertEqual(home.headers["Strict-Transport-Security"], "max-age=31536000; includeSubDomains")
        csp = home.headers["Content-Security-Policy"]
        self.assertIn("script-src", csp)
        self.assertIn("script-src-elem", csp)
        self.assertIn("connect-src", csp)
        self.assertIn("https://www.googletagmanager.com", csp)
        self.assertIn("https://tagmanager.google.com", csp)
        self.assertIn("https://www.google-analytics.com", csp)
        self.assertIn("https://fonts.googleapis.com", csp)
        self.assertIn("https://ssl.gstatic.com", csp)
        self.assertIn("https://www.gstatic.com", csp)
        self.assertIn("https://www.google.it", csp)
        self.assertIn("https://ep1.adtrafficquality.google", csp)
        self.assertIn("https://ep2.adtrafficquality.google", csp)
        self.assertIn("frame-src", csp)
        self.assertIn("https://tpc.googlesyndication.com", csp)
        self.assertIn(b'id="root"', home.data)
        self.assertIn(b"/metodologia", home.data)
        self.assertIn(b"Indicatori territoriali in evidenza", home.data)

        legacy = client.get("/legacy")
        self.assertEqual(legacy.status_code, 200)
        self.assertIn(b"draw_charts", legacy.data)

        legacy_reddito = client.get("/legacy-reddito")
        self.assertEqual(legacy_reddito.status_code, 200)
        self.assertIn(b"federalismo fiscale", legacy_reddito.data)

        data = client.get("/data")
        self.assertEqual(data.status_code, 200)
        self.assertIn("noindex", data.headers["X-Robots-Tag"])
        rows = data.get_json()
        self.assertGreater(len(rows), 0)
        self.assertIn("Indicatore", rows[0])

    def test_filtered_api_routes(self):
        client = app.test_client()

        catalog = client.get("/api/catalog")
        self.assertEqual(catalog.status_code, 200)
        self.assertIn("noindex", catalog.headers["X-Robots-Tag"])
        catalog_payload = catalog.get_json()
        self.assertIn("featured_indicator_id", catalog_payload)
        self.assertGreater(len(catalog_payload["indicators"]), 0)

        sample = catalog_payload["indicators"][0]
        for field in ("region_count", "completeness", "complete", "spark", "explain"):
            self.assertIn(field, sample)
        self.assertIsInstance(sample["complete"], bool)
        self.assertGreaterEqual(sample["completeness"], 0.0)
        self.assertLessEqual(sample["completeness"], 1.0)
        self.assertIsInstance(sample["spark"], list)
        self.assertLessEqual(len(sample["spark"]), 24)
        self.assertTrue(any(item["complete"] for item in catalog_payload["indicators"]))
        for item in catalog_payload["indicators"]:
            self.assertIn("explain", item)
            for field in ("plain", "example", "reading", "caveat", "direction"):
                self.assertIn(field, item["explain"])
                self.assertTrue(item["explain"][field])

        indicator_id = catalog_payload["featured_indicator_id"]
        indicator = client.get(f"/api/indicator/{indicator_id}")
        self.assertEqual(indicator.status_code, 200)
        indicator_payload = indicator.get_json()
        self.assertIn("metadata", indicator_payload)
        self.assertIn("series", indicator_payload)
        self.assertIn("explain", indicator_payload["metadata"])
        self.assertLess(len(str(indicator_payload)), 500000)

        year = indicator_payload["metadata"]["year_max"]
        values = client.get(f"/api/indicator/{indicator_id}/year/{year}")
        self.assertEqual(values.status_code, 200)
        values_payload = values.get_json()
        self.assertEqual(values_payload["year"], year)
        self.assertLessEqual(len(values_payload["values"]), 20)

        search = client.get("/api/search?q=turismo")
        self.assertEqual(search.status_code, 200)
        self.assertIn("results", search.get_json())

    def test_region_api(self):
        client = app.test_client()

        region = client.get("/api/region/lombardia")
        self.assertEqual(region.status_code, 200)
        self.assertIn("noindex", region.headers["X-Robots-Tag"])
        payload = region.get_json()
        self.assertEqual(payload["region"], "Lombardia")
        self.assertEqual(payload["region_key"], "lombardia")
        for field in ("theme_table", "themes_strong", "themes_weak",
                      "top_excels", "top_lags", "similar_regions", "all_indicators"):
            self.assertIn(field, payload)
        self.assertGreater(len(payload["theme_table"]), 0)

        self.assertEqual(client.get("/api/region/atlantide").status_code, 404)

    def test_blog_routes(self):
        from app.blog import get_posts

        client = app.test_client()

        listing = client.get("/blog")
        self.assertEqual(listing.status_code, 200)
        self.assertIn(b"Divario Italia", listing.data)

        posts = get_posts()
        self.assertGreater(len(posts), 0)
        slug = posts[0]["slug"]

        post = client.get(f"/blog/{slug}")
        self.assertEqual(post.status_code, 200)
        self.assertIn(b"application/ld+json", post.data)
        self.assertIn(b'property="og:type" content="article"', post.data)
        self.assertIn(b"/static/img/", post.data)

        missing = client.get("/blog/does-not-exist")
        self.assertEqual(missing.status_code, 404)
        self.assertIn(b"Pagina non trovata", missing.data)
        self.assertIn(b'content="noindex, follow"', missing.data)

    def test_blog_post_updated_field_drives_date_modified(self):
        import tempfile
        from pathlib import Path
        from unittest import mock

        from app import blog, cache

        fixtures = {
            "with-update.md": (
                "---\ntitle: Con aggiornamento\ndate: 2026-06-01\nupdated: 2026-06-15\n---\nBody.\n"
            ),
            "no-update.md": "---\ntitle: Senza aggiornamento\ndate: 2026-06-01\n---\nBody.\n",
            "stale-update.md": (
                "---\ntitle: Aggiornamento antecedente\ndate: 2026-06-01\nupdated: 2026-05-01\n---\nBody.\n"
            ),
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            for name, content in fixtures.items():
                (tmp_dir / name).write_text(content, encoding="utf-8")

            with mock.patch.object(blog, "POSTS_DIR", tmp_dir):
                cache.cache.clear()
                posts = {p["title"]: p for p in blog.get_posts()}
                cache.cache.clear()

        self.assertEqual(posts["Con aggiornamento"]["date_modified"].isoformat(), "2026-06-15")
        self.assertEqual(posts["Senza aggiornamento"]["date_modified"], posts["Senza aggiornamento"]["date"])
        # An `updated` earlier than `date` is a frontmatter mistake, not a real
        # freshness signal - fall back to `date` rather than regress dateModified.
        self.assertEqual(posts["Aggiornamento antecedente"]["date_modified"], posts["Aggiornamento antecedente"]["date"])

    def test_seo_routes(self):
        client = app.test_client()

        sitemap = client.get("/sitemap.xml")
        self.assertEqual(sitemap.status_code, 200)
        self.assertIn("xml", sitemap.headers["Content-Type"])
        self.assertIn(b"/blog", sitemap.data)
        self.assertIn(b"/metodologia", sitemap.data)
        self.assertNotIn(b"/data", sitemap.data)

        robots = client.get("/robots.txt")
        self.assertEqual(robots.status_code, 200)
        robots_text = robots.data.decode("utf-8")
        self.assertIn("Sitemap:", robots_text)
        self.assertIn("Disallow: /api/", robots_text)
        self.assertIn("Disallow: /data", robots_text)
        # Single source of truth (Cloudflare managed injection disabled): the
        # content signals and AI-bot blocklist live in the app, and there must be
        # exactly one "User-agent: *" group (no duplicate from a managed prepend).
        self.assertIn("Content-Signal: search=yes,ai-train=no", robots_text)
        self.assertIn("User-agent: ClaudeBot", robots_text)
        self.assertIn("User-agent: Google-Extended", robots_text)
        self.assertEqual(robots_text.count("User-agent: *"), 1)

        privacy = client.get("/privacy")
        self.assertEqual(privacy.status_code, 200)
        self.assertIn(b"Privacy e cookie", privacy.data)

        methodology = client.get("/metodologia")
        self.assertEqual(methodology.status_code, 200)
        self.assertIn(b"Metodologia e fonti", methodology.data)
        self.assertIn(b"application/ld+json", methodology.data)

    def test_canonical_host_and_public_404(self):
        client = app.test_client()

        redirect = client.get("/", base_url="https://www.divarioitalia.it", follow_redirects=False)
        self.assertEqual(redirect.status_code, 301)
        self.assertEqual(redirect.headers["Location"], "https://divarioitalia.it/")
        self.assertEqual(redirect.headers["Strict-Transport-Security"], "max-age=31536000; includeSubDomains")

        missing = client.get("/pagina-che-non-esiste")
        self.assertEqual(missing.status_code, 404)
        self.assertIn(b"Pagina non trovata", missing.data)
        self.assertIn("noindex", missing.headers["X-Robots-Tag"])

        api_missing = client.get("/api/indicator/not-found")
        self.assertEqual(api_missing.status_code, 404)
        self.assertIn("noindex", api_missing.headers["X-Robots-Tag"])
        self.assertEqual(api_missing.get_json()["error"], "not_found")

    def test_public_pages_get_explicit_index_header(self):
        from app.data import get_catalog, get_indicator
        from app import profiles

        client = app.test_client()
        expected = "index, follow, max-snippet:-1, max-image-preview:large"
        for path in (
            "/", "/regioni", "/temi", "/qualita-della-vita",
            "/qualita-della-vita/classifica/regioni",
            "/qualita-della-vita/metodologia", "/metodologia", "/blog",
        ):
            self.assertEqual(client.get(path).headers.get("X-Robots-Tag"), expected, path)

        catalog = get_catalog()
        sample = next(item for item in catalog["indicators"] if profiles.is_search_indexable_indicator(item))
        indicator_path = profiles.indicator_path(sample["id"], sample["name"])
        self.assertTrue(profiles.is_search_indexable_indicator(get_indicator(str(sample["id"]))["metadata"]))
        self.assertEqual(client.get(indicator_path).headers.get("X-Robots-Tag"), expected)
        self.assertEqual(client.get("/regione/lombardia").headers.get("X-Robots-Tag"), expected)
        theme_slug = next(iter(profiles._theme_slug_map()))
        self.assertEqual(client.get(f"/tema/{theme_slug}").headers.get("X-Robots-Tag"), expected)

    def test_noindex_paths_unaffected_by_default_index_header(self):
        client = app.test_client()
        for path in ("/data", "/legacy", "/legacy-reddito", "/download/quality-life/regioni"):
            self.assertIn("noindex", client.get(path).headers["X-Robots-Tag"])
        self.assertIn("noindex", client.get("/api/catalog").headers["X-Robots-Tag"])

    def test_404_header_is_not_overwritten_by_default_index_header(self):
        client = app.test_client()
        self.assertEqual(client.get("/pagina-che-non-esiste").headers["X-Robots-Tag"], "noindex, follow")
        self.assertEqual(
            client.get("/api/indicator/not-found").headers["X-Robots-Tag"],
            "noindex, nofollow, noarchive",
        )

    def test_seo_landing_pages(self):
        from app.data import get_catalog
        from app import profiles

        client = app.test_client()

        catalog = get_catalog()
        sample = next(item for item in catalog["indicators"] if profiles.is_search_indexable_indicator(item))
        path = profiles.indicator_path(sample["id"], sample["name"])

        indicator = client.get(path)
        self.assertEqual(indicator.status_code, 200)
        self.assertIn(b"application/ld+json", indicator.data)
        self.assertIn(b'"@type": "Dataset"', indicator.data)
        self.assertIn(b"DataDownload", indicator.data)
        self.assertIn(sample["name"].encode("utf-8"), indicator.data)

        csv_download = client.get(f"/download/indicator/{sample['id']}.csv")
        self.assertEqual(csv_download.status_code, 200)
        self.assertIn("text/csv", csv_download.headers["Content-Type"])
        self.assertIn("noindex", csv_download.headers["X-Robots-Tag"])
        self.assertIn(b"indicator_id,indicator,theme,region", csv_download.data)
        json_download = client.get(f"/download/indicator/{sample['id']}.json")
        self.assertEqual(json_download.status_code, 200)
        self.assertIn("noindex", json_download.headers["X-Robots-Tag"])
        self.assertIn("metadata", json_download.get_json())

        # Non-canonical slug 301s to the canonical path.
        wrong = client.get(f"/indicatore/{sample['id']}-slug-sbagliato")
        self.assertEqual(wrong.status_code, 301)
        self.assertTrue(wrong.headers["Location"].endswith(path))

        non_indexable = next(item for item in catalog["indicators"] if not profiles.is_search_indexable_indicator(item))
        non_indexable_path = profiles.indicator_path(non_indexable["id"], non_indexable["name"])
        non_indexable_page = client.get(non_indexable_path)
        self.assertEqual(non_indexable_page.status_code, 200)
        self.assertIn(b'content="noindex, follow"', non_indexable_page.data)
        self.assertEqual(non_indexable_page.headers["X-Robots-Tag"], "noindex, follow")
        sitemap = client.get("/sitemap.xml").data.decode("utf-8")
        self.assertIn(path, sitemap)
        self.assertNotIn(non_indexable_path, sitemap)

        self.assertEqual(client.get("/indicatore/9999999").status_code, 404)
        self.assertEqual(client.get("/indicatore/abc").status_code, 404)

        region = client.get("/regione/lombardia")
        self.assertEqual(region.status_code, 200)
        self.assertIn(b"Lombardia", region.data)
        self.assertIn(b"application/ld+json", region.data)
        self.assertEqual(client.get("/regione/atlantide").status_code, 404)

        theme_slug = next(iter(profiles._theme_slug_map()))
        theme = client.get(f"/tema/{theme_slug}")
        self.assertEqual(theme.status_code, 200)
        self.assertIn(b"application/ld+json", theme.data)
        self.assertEqual(client.get("/tema/non-esiste").status_code, 404)

        self.assertEqual(client.get("/regioni").status_code, 200)
        self.assertEqual(client.get("/temi").status_code, 200)

        sitemap = client.get("/sitemap.xml").data
        self.assertIn(b"/regione/lombardia", sitemap)
        self.assertIn(b"/tema/", sitemap)
        self.assertIn(b"/indicatore/", sitemap)
        self.assertNotIn(non_indexable_path.encode("utf-8"), sitemap)

    def test_dataset_jsonld_spatial_coverage_and_license(self):
        import json
        import re

        from app.data import get_catalog
        from app import profiles

        client = app.test_client()
        sample = next(item for item in get_catalog()["indicators"] if profiles.is_search_indexable_indicator(item))
        pages = {
            "indicator": client.get(profiles.indicator_path(sample["id"], sample["name"])).data.decode("utf-8"),
            "region": client.get("/regione/lombardia").data.decode("utf-8"),
            "ranking": client.get("/qualita-della-vita/classifica/regioni").data.decode("utf-8"),
        }
        for name, html in pages.items():
            self.assertIn('"license": "https://creativecommons.org/licenses/by/3.0/it/"', html, name)
            self.assertNotIn('"@type": "Country"', html, name)
            self.assertNotIn('"@type": "AdministrativeArea"', html, name)
            for block in re.findall(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', html, re.S):
                json.loads(block)

    def test_indicator_page_has_data_derived_depth(self):
        from app.data import get_catalog
        from app import profiles

        client = app.test_client()
        sample = next(
            i for i in get_catalog()["indicators"]
            if i["explain"]["direction"] in ("higher_better", "lower_better", "higher_worse")
            and i["year_min"] != i["year_max"]
        )
        path = profiles.indicator_path(sample["id"], sample["name"])
        html = client.get(path).data.decode("utf-8")
        self.assertGreaterEqual(html.count("<h2"), 3)
        self.assertGreaterEqual(html.count("<h3"), 3)
        self.assertIn("data-callout", html)
        # The cascade fix: analysis h2s inside .page-indicator's .prose section must
        # get the full article-style treatment, not the compact .page-ranking one.
        css_path = Path(app.root_path) / "static" / "css" / "site.css"
        self.assertIn(".page .prose h2", css_path.read_text(encoding="utf-8"))

    def test_indicator_trend_stats(self):
        from app.data import indicator_trend_stats, indicator_year_average

        payload = {
            "metadata": {"id": "1", "name": "Tasso di occupazione", "unit": "percentuale", "year_min": 2020, "year_max": 2022},
            "series": [
                {"year": 2020, "region": "Lombardia", "region_key": "lombardia", "value": 60.0},
                {"year": 2020, "region": "Calabria", "region_key": "calabria", "value": 40.0},
                {"year": 2022, "region": "Lombardia", "region_key": "lombardia", "value": 66.0},
                {"year": 2022, "region": "Calabria", "region_key": "calabria", "value": 44.0},
            ],
        }
        values = [row for row in payload["series"] if row["year"] == 2022]
        best, worst = values[0], values[1]
        stats = indicator_trend_stats(payload, 2022, values, best, worst)

        self.assertEqual(stats["year_avg"], 55.0)
        self.assertEqual(stats["year_min_avg"], 50.0)
        self.assertAlmostEqual(stats["avg_change_pct"], 10.0)
        self.assertEqual(stats["gap_abs"], 22.0)
        self.assertAlmostEqual(stats["gap_ratio"], 66.0 / 44.0)

        # A "differenza tra..." indicator never gets a "N times" ratio: it's already
        # a gap, not a magnitude that can be honestly expressed as a multiple.
        gap_payload = dict(payload)
        gap_payload["metadata"] = dict(payload["metadata"], name="Differenza tra tasso di occupazione maschile e femminile")
        gap_stats = indicator_trend_stats(gap_payload, 2022, values, best, worst)
        self.assertIsNone(gap_stats["gap_ratio"])

        # Single-year series: no trend claim, avg falls back to the only year available.
        single_year_payload = {
            "metadata": {"id": "2", "name": "Indicatore", "unit": "percentuale", "year_min": 2022, "year_max": 2022},
            "series": values,
        }
        single_stats = indicator_trend_stats(single_year_payload, 2022, values, best, worst)
        self.assertFalse(single_stats["has_multi_year"])
        self.assertIsNone(single_stats["avg_change_pct"])
        self.assertEqual(single_stats["year_avg"], 55.0)

        self.assertIsNone(indicator_year_average(payload["series"], 2021))

        # lower_better/higher_worse indicators pick "best" as the *smaller* value
        # (views.py reverses the ranking for these directions) - the gap must still
        # come out as a positive magnitude, never a signed (best - worst) number.
        reversed_stats = indicator_trend_stats(payload, 2022, values, best=worst, worst=best)
        self.assertEqual(reversed_stats["gap_abs"], 22.0)
        self.assertAlmostEqual(reversed_stats["gap_ratio"], 66.0 / 44.0)

        # Median/dispersion and the "biggest movers" with an honest kind label.
        # Mixed-direction fixture: Lombardia rises, Calabria falls, Lazio rises less.
        mixed_payload = {
            "metadata": {"id": "3", "name": "Indicatore misto", "unit": "percentuale", "year_min": 2020, "year_max": 2022},
            "series": [
                {"year": 2020, "region": "Lombardia", "region_key": "lombardia", "value": 60.0},
                {"year": 2020, "region": "Calabria", "region_key": "calabria", "value": 40.0},
                {"year": 2020, "region": "Lazio", "region_key": "lazio", "value": 50.0},
                {"year": 2022, "region": "Lombardia", "region_key": "lombardia", "value": 70.0},
                {"year": 2022, "region": "Calabria", "region_key": "calabria", "value": 30.0},
                {"year": 2022, "region": "Lazio", "region_key": "lazio", "value": 52.0},
            ],
        }
        mixed_values = [row for row in mixed_payload["series"] if row["year"] == 2022]
        mixed_best = next(row for row in mixed_values if row["region"] == "Lombardia")
        mixed_worst = next(row for row in mixed_values if row["region"] == "Calabria")
        mixed_stats = indicator_trend_stats(mixed_payload, 2022, mixed_values, mixed_best, mixed_worst)

        self.assertEqual(mixed_stats["median"], 52.0)
        # Mean is 50.67: Lombardia (70) and Lazio (52) beat it, only Calabria (30) doesn't.
        self.assertEqual(mixed_stats["above_avg_count"], 2)
        self.assertEqual(mixed_stats["below_avg_count"], 1)
        self.assertEqual(mixed_stats["region_highest_delta"]["region"], "Lombardia")
        self.assertEqual(mixed_stats["region_highest_delta"]["kind"], "aumento")
        self.assertEqual(mixed_stats["region_lowest_delta"]["region"], "Calabria")
        self.assertEqual(mixed_stats["region_lowest_delta"]["kind"], "calo")
        # Best (Lombardia) - worst (Calabria) gap widened from 20 (2020) to 40 (2022).
        self.assertEqual(mixed_stats["year_min_gap_abs"], 20.0)
        self.assertEqual(mixed_stats["gap_trend"], 20.0)

        # Same-direction fixture: every region rises, just by different amounts - the
        # "lowest delta" region must never be mislabeled as a decrease.
        rising_payload = {
            "metadata": {"id": "4", "name": "Indicatore in crescita ovunque", "unit": "euro", "year_min": 2020, "year_max": 2022},
            "series": [
                {"year": 2020, "region": "Lombardia", "region_key": "lombardia", "value": 100.0},
                {"year": 2020, "region": "Calabria", "region_key": "calabria", "value": 50.0},
                {"year": 2022, "region": "Lombardia", "region_key": "lombardia", "value": 130.0},
                {"year": 2022, "region": "Calabria", "region_key": "calabria", "value": 60.0},
            ],
        }
        rising_values = [row for row in rising_payload["series"] if row["year"] == 2022]
        rising_stats = indicator_trend_stats(rising_payload, 2022, rising_values)
        self.assertEqual(rising_stats["region_highest_delta"]["kind"], "aumento")
        self.assertEqual(rising_stats["region_lowest_delta"]["region"], "Calabria")
        self.assertEqual(rising_stats["region_lowest_delta"]["kind"], "aumento")
        self.assertGreater(rising_stats["region_lowest_delta"]["delta"], 0)

        # Fewer than two regions in common across the two years: no honest "biggest
        # movers" comparison is possible, both must be None rather than duplicated.
        single_common_payload = {
            "metadata": {"id": "5", "name": "Indicatore", "unit": "euro", "year_min": 2020, "year_max": 2022},
            "series": [
                {"year": 2020, "region": "Lombardia", "region_key": "lombardia", "value": 100.0},
                {"year": 2022, "region": "Lombardia", "region_key": "lombardia", "value": 110.0},
            ],
        }
        single_common_values = [row for row in single_common_payload["series"] if row["year"] == 2022]
        single_common_stats = indicator_trend_stats(single_common_payload, 2022, single_common_values)
        self.assertIsNone(single_common_stats["region_highest_delta"])
        self.assertIsNone(single_common_stats["region_lowest_delta"])

    def test_trend_framing(self):
        from app.indicator_notes import trend_framing

        self.assertEqual(trend_framing("higher_better", None), "")
        self.assertEqual(trend_framing("higher_better", 0.5), "un andamento sostanzialmente stabile")
        self.assertEqual(trend_framing("higher_better", 5.0), "un miglioramento diffuso")
        self.assertEqual(trend_framing("higher_better", -5.0), "un peggioramento diffuso")
        self.assertEqual(trend_framing("lower_better", -5.0), "un miglioramento diffuso")
        self.assertEqual(trend_framing("lower_better", 5.0), "un peggioramento diffuso")
        self.assertEqual(trend_framing("higher_worse", 5.0), "un peggioramento diffuso")
        self.assertEqual(trend_framing("contextual", 5.0), "un aumento")
        self.assertEqual(trend_framing("contextual", -5.0), "una diminuzione")

    def test_region_profile_is_coherent(self):
        from app import profiles

        # Northern industrial regions should cluster together, southern ones too.
        lombardia = profiles.region_profile("lombardia")
        self.assertIsNotNone(lombardia)
        self.assertGreater(lombardia["scored_count"], 0)
        similar = {s["region_key"] for s in lombardia["similar_regions"]}
        self.assertTrue(similar & {"piemonte", "veneto", "emilia-romagna"})
        # Theme scores stay within the normalised 0..1 range.
        for theme in lombardia["theme_table"]:
            self.assertGreaterEqual(theme["score"], 0.0)
            self.assertLessEqual(theme["score"], 1.0)

    def test_macro_areas_cover_every_theme(self):
        from app.data import get_catalog

        catalog = get_catalog()
        # Every theme is mapped to a real macro-area (never the "Altro" fallback).
        for theme in catalog["themes"]:
            self.assertTrue(theme["macro_area"])
            self.assertNotEqual(theme["macro_area"], "Altro")
        for item in catalog["indicators"]:
            self.assertTrue(item["macro_area"])
        # The rollup exists and its counts add up to the catalog total.
        self.assertIn("macro_areas", catalog)
        self.assertTrue(catalog["macro_areas"])
        total = sum(area["indicator_count"] for area in catalog["macro_areas"])
        self.assertEqual(total, len(catalog["indicators"]))

    def test_region_explorer_and_movement(self):
        from app import profiles

        profile = profiles.region_profile("campania")
        indicators = profile["all_indicators"]
        self.assertTrue(indicators)
        contextual_seen = False
        for item in indicators:
            if item["rank"] is not None:
                self.assertGreaterEqual(item["rank"], 1)
                self.assertLessEqual(item["rank"], item["region_count"])
                self.assertIsNotNone(item["score"])
            else:
                # Contextual indicators stay visible but carry no score or movement.
                contextual_seen = True
                self.assertIsNone(item["score"])
                self.assertIsNone(item["movement"])
            if item["movement"] is not None:
                self.assertGreaterEqual(item["movement"], -19)
                self.assertLessEqual(item["movement"], 19)
        self.assertTrue(contextual_seen)

        gains, losses = profile["movement_gains"], profile["movement_losses"]
        self.assertTrue(all(g["movement"] > 0 for g in gains))
        self.assertTrue(all(l["movement"] < 0 for l in losses))
        self.assertEqual(gains, sorted(gains, key=lambda g: g["movement"], reverse=True))
        self.assertEqual(losses, sorted(losses, key=lambda l: l["movement"]))

    def test_core_set_is_complete_and_recent(self):
        from app.data import get_catalog
        from app import profiles

        core = [i for i in get_catalog()["indicators"] if profiles.is_core(i)]
        self.assertTrue(core)
        for item in core:
            self.assertTrue(item["complete"])
            self.assertGreaterEqual(item["year_max"], profiles.CORE_MIN_YEAR)

    def test_curated_direction_overrides_heuristic(self):
        from app.indicator_notes import direction_for

        # A gender employment gap: smaller is better, not "higher better".
        self.assertEqual(direction_for("57", "Differenza tra tasso di occupazione maschile e femminile"), "lower_better")
        # Energy covered by cogeneration is positive, not a pressure.
        self.assertEqual(direction_for("378", "Consumi di energia coperti da cogenerazione"), "higher_better")
        # Early school leaving is negative.
        self.assertEqual(direction_for("102", "Giovani che abbandonano"), "lower_better")
        # INVALSI: share of students NOT reaching a sufficient level is negative.
        self.assertEqual(direction_for("623", "Competenza alfabetica non adeguata"), "lower_better")
        # Share of students with high competence is positive.
        self.assertEqual(direction_for("111", "Studenti con elevate competenze in lettura"), "higher_better")

    def test_regions_map_data_matches_geometry(self):
        from app import profiles

        overview = profiles.regions_overview()
        keys = {r["region_key"] for r in profiles.all_regions_index()}
        self.assertEqual(set(overview), keys)
        for entry in overview.values():
            self.assertNotIn("score", entry)
            self.assertNotIn("rank", entry)
            self.assertNotIn("rank_total", entry)
        # The pre-projected SVG partial must cover exactly the same region keys.
        from pathlib import Path
        svg = (Path(app.root_path) / "templates" / "_italy_map.html").read_text(encoding="utf-8")
        import re
        svg_keys = set(re.findall(r'data-key="([^"]+)"', svg))
        self.assertEqual(svg_keys, keys)

    def test_ads_txt_uses_adsense_env(self):
        from app import config

        client = app.test_client()
        original_client = config.ADSENSE_CLIENT
        try:
            config.ADSENSE_CLIENT = ""
            self.assertEqual(client.get("/ads.txt").status_code, 404)

            config.ADSENSE_CLIENT = "ca-pub-1234567890123456"
            ads = client.get("/ads.txt")
            self.assertEqual(ads.status_code, 200)
            self.assertIn(b"google.com, pub-1234567890123456, DIRECT", ads.data)
        finally:
            config.ADSENSE_CLIENT = original_client

    def test_gtm_consent_default_precedes_gtm_and_adsense(self):
        from app import config

        client = app.test_client()
        original_client = config.ADSENSE_CLIENT
        original_gtm = config.GOOGLE_TAG_MANAGER_ID
        try:
            config.GOOGLE_TAG_MANAGER_ID = "GTM-PZ45BG7D"
            config.ADSENSE_CLIENT = "ca-pub-1234567890123456"
            home = client.get("/")
            self.assertEqual(home.status_code, 200)
            html = home.data.decode("utf-8")
            consent_index = html.index("gtag('consent', 'default'")
            gtm_index = html.index("googletagmanager.com/gtm.js?id=")
            loader_index = html.index("pagead2.googlesyndication.com/pagead/js/adsbygoogle.js")
            self.assertLess(consent_index, gtm_index)
            self.assertLess(consent_index, loader_index)
            self.assertIn("'analytics_storage': 'denied'", html)
            self.assertIn("'wait_for_update': 2000", html)
            self.assertIn("gtag('set', 'ads_data_redaction', true)", html)
            self.assertIn("GTM-PZ45BG7D", html)
            self.assertIn("googletagmanager.com/ns.html?id=GTM-PZ45BG7D", html)
            self.assertNotIn("event: 'page_view'", html)
            self.assertNotIn("googletagmanager.com/gtag/js", html)
            self.assertNotIn("diSendGoogleEvent", html)
            self.assertNotIn("googlefc.controlledMessagingFunction", html)
            self.assertNotIn("diApplyGoogleConsent", html)

            blog = client.get("/blog")
            self.assertEqual(blog.status_code, 200)
            blog_html = blog.data.decode("utf-8")
            self.assertIn("event: 'page_view'", blog_html)
            self.assertIn("page_type: window.location.pathname.indexOf('/blog') === 0 ? 'blog' : 'server'", blog_html)
        finally:
            config.ADSENSE_CLIENT = original_client
            config.GOOGLE_TAG_MANAGER_ID = original_gtm

    def test_privacy_page_exposes_iubenda_preferences_button(self):
        from app import config

        client = app.test_client()
        original_gtm = config.GOOGLE_TAG_MANAGER_ID
        try:
            config.GOOGLE_TAG_MANAGER_ID = "GTM-PZ45BG7D"
            privacy = client.get("/privacy")
            self.assertEqual(privacy.status_code, 200)
            html = privacy.data.decode("utf-8")
            self.assertIn("diOpenConsentPreferences", html)
            self.assertIn("Gestisci preferenze cookie", html)
            self.assertNotIn("data-funding-choices-revoke", html)
            self.assertNotIn("showRevocationMessage", html)
        finally:
            config.GOOGLE_TAG_MANAGER_ID = original_gtm

    def test_internal_event_endpoint_accepts_anonymous_events(self):
        client = app.test_client()

        event = client.post("/api/events", json={
            "name": "select_indicator",
            "path": "/?indicator=105",
            "title": "Divario Italia",
            "params": {
                "indicator_id": "105",
                "enabled": True,
                "nested": {"ignored": True},
            },
        })
        self.assertEqual(event.status_code, 204)

        self.assertEqual(client.post("/api/events", json={"name": "bad-name!"}).status_code, 400)

    def test_parse_number_rejects_non_finite(self):
        from app.data import _parse_number

        self.assertEqual(_parse_number("1.234,5"), 1234.5)
        self.assertIsNone(_parse_number("INF"))
        self.assertIsNone(_parse_number("-INF"))
        self.assertIsNone(_parse_number(""))
        self.assertIsNone(_parse_number("-"))

    def test_catalog_is_strict_json(self):
        import json

        from app.data import get_catalog

        # allow_nan=False raises if any NaN/Infinity slipped into the payload,
        # which would make the browser's JSON.parse fail.
        json.dumps(get_catalog(), allow_nan=False)

    def test_seo_metadata_within_budget(self):
        from app.data import get_catalog
        from app.indicator_notes import seo_title, seo_description

        indicators = get_catalog()["indicators"]
        for item in indicators:
            title = seo_title(item["name"], "Divario Italia")
            desc = seo_description(item["explain"]["plain"], item["year_max"], len(item["regions"]))
            # SERP budgets: titles stay readable, descriptions are not truncated by Google.
            self.assertLessEqual(len(title), 60, f"title too long for {item['id']}: {title}")
            self.assertGreaterEqual(len(title), 8, f"title too short for {item['id']}: {title}")
            self.assertLessEqual(len(desc), 155, f"desc too long for {item['id']}: {desc}")
            self.assertEqual(title, title.strip())
            self.assertNotIn(" per per ", title)  # no doubled connector before the tail
            self.assertNotIn(", per regione", title)  # no dangling comma before the tail
            # Title must not end on a dangling connector word.
            last = title.replace(" · Divario Italia", "").split()[-1].lower()
            self.assertNotIn(last, {"di", "del", "della", "dei", "delle", "per", "e", "a", "da", "in"}, title)
            # Description keeps whole sentences and ends with the data vintage.
            self.assertIn("Dati Istat", desc)
            self.assertTrue(desc.rstrip().endswith("."), desc)

        by_id = {i["id"]: i for i in indicators}
        # Gender siblings (189 maschi / 190 femmine) must not collapse to one title.
        if {"189", "190"} <= set(by_id):
            self.assertNotEqual(
                seo_title(by_id["189"]["name"], "Divario Italia"),
                seo_title(by_id["190"]["name"], "Divario Italia"),
            )

    def test_dataset_schema(self):
        dataset = Path(app.root_path) / "static" / "data" / "Assoluti_Regione.csv"
        expected_columns = [
            "idIndicatore",
            "Territorio",
            "Tema",
            "Indicatore",
            "UDM",
            "Fonte",
            "Archivio",
            "Anno",
            "Livello/Variazione",
            "Dato",
            "Benchmark",
            "Area",
        ]

        with dataset.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            self.assertEqual(reader.fieldnames, expected_columns)
            first_row = next(reader)

        self.assertEqual(first_row["Area"], "Regione")
        self.assertEqual(first_row["Fonte"], "Istat")
        self.assertTrue(first_row["Dato"])


class HardeningTest(unittest.TestCase):
    def test_home_is_actually_cached(self):
        """Con i decorator nell'ordine corretto, il corpo della view / non viene
        ricomputato a ogni richiesta."""
        from unittest import mock
        from app import cache

        cache.clear()
        with mock.patch("app.views.render_template", return_value="OK") as rt:
            client = app.test_client()
            client.get("/")
            client.get("/")
            client.get("/")
            self.assertEqual(rt.call_count, 1)

    def test_events_rate_limited(self):
        """L'endpoint pubblico /api/events blocca lo spam con 429 oltre la soglia."""
        from app import cache

        cache.clear()
        client = app.test_client()
        codes = [
            client.post("/api/events", json={"name": "unit_test"}).status_code
            for _ in range(35)
        ]
        self.assertEqual(codes.count(204), 30)
        self.assertTrue(codes.count(429) >= 1)


if __name__ == "__main__":
    unittest.main()
