import unittest

from app import app
from app import quality_life as ql
from app.quality_life_config import QUALITY_LIFE_CATEGORIES, QUALITY_LIFE_PROFILES


class QualityLifePagesTest(unittest.TestCase):
    def test_quality_life_pages_respond(self):
        client = app.test_client()

        index = client.get("/qualita-della-vita")
        self.assertEqual(index.status_code, 200)
        self.assertIn(b"Qualit", index.data)
        self.assertIn(b"application/ld+json", index.data)

        ranking = client.get("/qualita-della-vita/classifica")
        self.assertEqual(ranking.status_code, 200)
        self.assertIn(b"Lombardia", ranking.data)

        ranking_profile = client.get("/qualita-della-vita/classifica?profilo=giovani")
        self.assertEqual(ranking_profile.status_code, 200)

        # Unknown profile on the HTML page is a 404, not a silent fallback.
        self.assertEqual(client.get("/qualita-della-vita/classifica?profilo=nope").status_code, 404)

        methodology = client.get("/qualita-della-vita/metodologia")
        self.assertEqual(methodology.status_code, 200)
        self.assertIn("Sole 24 Ore".encode("utf-8"), methodology.data)

    def test_classifica_shows_category_scores(self):
        # "score categorie principali" must be visible text, not only tooltips.
        html = app.test_client().get("/qualita-della-vita/classifica").data.decode("utf-8")
        self.assertIn("quality-chip__score", html)
        top = ql.build_quality_life_ranking("standard")["ranking"][0]
        strongest = top["strongest_categories"][0]
        self.assertIn(strongest["name"], html)
        self.assertIn(f">{round(strongest['score'])}</b>", html)

    def test_quality_life_api_ranking_responds(self):
        client = app.test_client()

        rankings = client.get("/api/quality-life/rankings")
        self.assertEqual(rankings.status_code, 200)
        payload = rankings.get_json()
        for key in ("ranking", "profile", "categories", "methodology"):
            self.assertIn(key, payload)
        self.assertEqual(payload["profile"]["slug"], "standard")
        self.assertEqual(len(payload["ranking"]), 20)

        # Every indicator surfaced is fully traceable.
        sample = payload["ranking"][0]["top_positive_indicators"][0]
        for field in ("id", "name", "theme", "score", "path", "year_max", "direction"):
            self.assertIn(field, sample)

        profiles = client.get("/api/quality-life/profiles")
        self.assertEqual(profiles.status_code, 200)
        self.assertGreater(len(profiles.get_json()["profiles"]), 0)

        categories = client.get("/api/quality-life/categories")
        self.assertEqual(categories.status_code, 200)
        self.assertGreater(len(categories.get_json()["categories"]), 0)

        named = client.get("/api/quality-life/rankings/opportunita")
        self.assertEqual(named.status_code, 200)
        self.assertEqual(named.get_json()["profile"]["slug"], "opportunita")
        self.assertEqual(client.get("/api/quality-life/rankings/nope").status_code, 404)

    def test_quality_life_region_profile_responds(self):
        client = app.test_client()

        region = client.get("/api/quality-life/region/lombardia")
        self.assertEqual(region.status_code, 200)
        payload = region.get_json()
        self.assertEqual(payload["region"]["region_key"], "lombardia")
        self.assertGreaterEqual(payload["region"]["rank"], 1)
        self.assertLessEqual(payload["region"]["rank"], 20)

        self.assertEqual(client.get("/api/quality-life/region/atlantide").status_code, 404)
        self.assertEqual(
            client.get("/api/quality-life/region/lombardia?profilo=nope").status_code, 404
        )

    def test_quality_life_profiles_have_valid_weights(self):
        category_slugs = set(QUALITY_LIFE_CATEGORIES)
        for slug, config in QUALITY_LIFE_PROFILES.items():
            normalised = ql.normalize_weights(config["weights"])
            self.assertAlmostEqual(sum(normalised.values()), 1.0, places=6)
            # Every weighted category exists.
            for category in config["weights"]:
                self.assertIn(category, category_slugs)

    def test_quality_life_scores_are_in_range(self):
        payload = ql.build_quality_life_ranking("standard")
        for row in payload["ranking"]:
            self.assertGreaterEqual(row["score"], 0)
            self.assertLessEqual(row["score"], 100)
            self.assertGreaterEqual(row["coverage"], 0.0)
            self.assertLessEqual(row["coverage"], 1.0)
            for category_score in row["category_scores"].values():
                self.assertGreaterEqual(category_score, 0)
                self.assertLessEqual(category_score, 100)

    def test_quality_life_ranking_is_sorted(self):
        payload = ql.build_quality_life_ranking("standard")
        scores = [row["score"] for row in payload["ranking"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual([row["rank"] for row in payload["ranking"]], list(range(1, 21)))

    def test_quality_life_categories_not_empty_for_standard_profile(self):
        payload = ql.build_quality_life_ranking("standard")
        counts = payload["methodology"]["indicator_counts"]
        # The standard profile weights every category, so each must carry data.
        for category in QUALITY_LIFE_CATEGORIES:
            self.assertGreater(counts.get(category, 0), 0)
        self.assertEqual(payload["methodology"]["quality_checks"]["empty_categories"], [])

    def test_quality_life_sitemap_contains_pages(self):
        sitemap = app.test_client().get("/sitemap.xml").data
        self.assertIn(b"/qualita-della-vita", sitemap)
        self.assertIn(b"/qualita-della-vita/classifica", sitemap)
        self.assertIn(b"/qualita-della-vita/metodologia", sitemap)

    def test_existing_routes_still_work(self):
        client = app.test_client()
        self.assertEqual(client.get("/legacy").status_code, 200)
        self.assertEqual(client.get("/legacy-reddito").status_code, 200)
        self.assertEqual(client.get("/data").status_code, 200)
        self.assertEqual(client.get("/api/catalog").status_code, 200)


if __name__ == "__main__":
    unittest.main()
