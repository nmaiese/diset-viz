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

        data = client.get("/data")
        self.assertEqual(data.status_code, 200)
        rows = data.get_json()
        self.assertGreater(len(rows), 0)
        self.assertIn("Indicatore", rows[0])

    def test_filtered_api_routes(self):
        client = app.test_client()

        catalog = client.get("/api/catalog")
        self.assertEqual(catalog.status_code, 200)
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

        robots = client.get("/robots.txt")
        self.assertEqual(robots.status_code, 200)
        self.assertIn(b"Sitemap:", robots.data)

        privacy = client.get("/privacy")
        self.assertEqual(privacy.status_code, 200)
        self.assertIn(b"Privacy e cookie", privacy.data)

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

    def test_funding_choices_force_script_precedes_adsense_loader(self):
        from app import config

        client = app.test_client()
        original_client = config.ADSENSE_CLIENT
        original_force = config.FORCE_FUNDING_CHOICES_CMP
        try:
            config.ADSENSE_CLIENT = "ca-pub-1234567890123456"
            config.FORCE_FUNDING_CHOICES_CMP = True
            home = client.get("/")
            self.assertEqual(home.status_code, 200)
            html = home.data.decode("utf-8")
            force_index = html.index("googlefc.controlledMessagingFunction")
            loader_index = html.index("pagead2.googlesyndication.com/pagead/js/adsbygoogle.js")
            self.assertLess(force_index, loader_index)
            self.assertIn("message.proceed(true)", html)
            self.assertIn("window.__diUsesFundingChoicesCmp = true", html)
            self.assertNotIn("gtag('consent', 'default'", html)
            self.assertNotIn("window.diApplyGoogleConsent('denied')", html)
        finally:
            config.ADSENSE_CLIENT = original_client
            config.FORCE_FUNDING_CHOICES_CMP = original_force

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
