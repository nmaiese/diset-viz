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
        self.assertIn(b'id="root"', home.data)

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

        self.assertEqual(client.get("/blog/does-not-exist").status_code, 404)

    def test_seo_routes(self):
        client = app.test_client()

        sitemap = client.get("/sitemap.xml")
        self.assertEqual(sitemap.status_code, 200)
        self.assertIn("xml", sitemap.headers["Content-Type"])
        self.assertIn(b"/blog", sitemap.data)
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

    def test_seo_landing_pages(self):
        from app.data import get_catalog
        from app import profiles

        client = app.test_client()

        catalog = get_catalog()
        sample = catalog["indicators"][0]
        path = profiles.indicator_path(sample["id"], sample["name"])

        indicator = client.get(path)
        self.assertEqual(indicator.status_code, 200)
        self.assertIn(b"application/ld+json", indicator.data)
        self.assertIn(b'"@type": "Dataset"', indicator.data)
        self.assertIn(sample["name"].encode("utf-8"), indicator.data)

        # Non-canonical slug 301s to the canonical path.
        wrong = client.get(f"/indicatore/{sample['id']}-slug-sbagliato")
        self.assertEqual(wrong.status_code, 301)
        self.assertTrue(wrong.headers["Location"].endswith(path))

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
        self.assertNotIn(b"/indicatore/264-aree-terrestri-protette", sitemap)

        stale = client.get("/indicatore/264-aree-terrestri-protette")
        self.assertEqual(stale.status_code, 200)
        self.assertIn(b'name="robots" content="noindex, follow"', stale.data)

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


if __name__ == "__main__":
    unittest.main()
