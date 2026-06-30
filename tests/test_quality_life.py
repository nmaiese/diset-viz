import unittest

from app import app
from app import quality_life_bes as qb
from app.bes_data import has_bes_data
from app.quality_life import normalize_weights
from app.quality_life_config import QUALITY_LIFE_CATEGORIES, QUALITY_LIFE_PROFILES


class QualityLifeStaticTest(unittest.TestCase):
    def test_index_and_methodology_respond(self):
        client = app.test_client()
        index = client.get("/qualita-della-vita")
        self.assertEqual(index.status_code, 200)
        self.assertIn(b"application/ld+json", index.data)

        methodology = client.get("/qualita-della-vita/metodologia")
        self.assertEqual(methodology.status_code, 200)
        self.assertIn("Sole 24 Ore".encode("utf-8"), methodology.data)
        self.assertIn("z-score".encode("utf-8"), methodology.data)

    def test_api_profiles_and_categories(self):
        client = app.test_client()
        profiles = client.get("/api/quality-life/profiles")
        self.assertEqual(profiles.status_code, 200)
        self.assertGreater(len(profiles.get_json()["profiles"]), 0)
        categories = client.get("/api/quality-life/categories")
        self.assertEqual(categories.status_code, 200)
        self.assertEqual(len(categories.get_json()["categories"]), len(QUALITY_LIFE_CATEGORIES))

    def test_profiles_have_valid_weights(self):
        for config in QUALITY_LIFE_PROFILES.values():
            normalised = normalize_weights(config["weights"])
            self.assertAlmostEqual(sum(normalised.values()), 1.0, places=6)
            for category in config["weights"]:
                self.assertIn(category, QUALITY_LIFE_CATEGORIES)

    def test_legacy_redirects(self):
        client = app.test_client()
        for path, target in [
            ("/qualita-della-vita/classifica", "/qualita-della-vita/classifica/regioni"),
            ("/qualita-della-vita/province", "/qualita-della-vita/classifica/province"),
        ]:
            resp = client.get(path)
            self.assertEqual(resp.status_code, 301)
            self.assertTrue(resp.headers["Location"].endswith(target))

    def test_sitemap_contains_both_levels(self):
        sitemap = app.test_client().get("/sitemap.xml").data
        self.assertIn(b"/qualita-della-vita/classifica/regioni", sitemap)
        self.assertIn(b"/qualita-della-vita/classifica/province", sitemap)

    def test_invalid_level_is_404(self):
        client = app.test_client()
        self.assertEqual(client.get("/qualita-della-vita/classifica/comuni").status_code, 404)
        self.assertEqual(client.get("/api/quality-life/comuni/rankings").status_code, 404)

    def test_existing_routes_still_work(self):
        client = app.test_client()
        self.assertEqual(client.get("/legacy").status_code, 200)
        self.assertEqual(client.get("/data").status_code, 200)
        self.assertEqual(client.get("/api/catalog").status_code, 200)
        self.assertEqual(client.get("/regione/lombardia").status_code, 200)


class QualityLifeBesEngineTest(unittest.TestCase):
    LEVELS = {"regione": ("regioni", 20), "provincia": ("province", 103)}

    def test_levels_present(self):
        for level in self.LEVELS:
            self.assertTrue(has_bes_data(level), f"missing BES data for {level}")

    def test_ranking_payload_and_scores(self):
        for level, (url_level, count) in self.LEVELS.items():
            payload = qb.build_bes_ranking(level, "standard")
            self.assertIsNotNone(payload)
            for key in ("ranking", "profile", "categories", "champions",
                        "category_rankings", "methodology", "level"):
                self.assertIn(key, payload)
            self.assertEqual(len(payload["ranking"]), count, level)
            scores = [r["score"] for r in payload["ranking"]]
            self.assertEqual(scores, sorted(scores, reverse=True))
            self.assertEqual([r["rank"] for r in payload["ranking"]], list(range(1, count + 1)))
            for row in payload["ranking"]:
                self.assertGreaterEqual(row["score"], 0)
                self.assertLessEqual(row["score"], 100)
                self.assertIn("delta_rank", row)
            self.assertTrue(payload["champions"])

    def test_delta_rank_is_zero_for_standard_and_moves_otherwise(self):
        # Standard vs itself: every delta is 0.
        std = qb.build_bes_ranking("provincia", "standard")
        self.assertTrue(all(r["delta_rank"] == 0 for r in std["ranking"]))
        # A different profile must move at least one province.
        servizi = qb.build_bes_ranking("provincia", "servizi")
        self.assertTrue(any(r["delta_rank"] != 0 for r in servizi["ranking"]))
        # Deltas net to zero (it is a re-ranking of the same set).
        self.assertEqual(sum(r["delta_rank"] for r in servizi["ranking"]), 0)

    def test_http_rankings_and_territory(self):
        client = app.test_client()
        cases = [("regioni", "lombardia"), ("province", "milano")]
        for url_level, key in cases:
            page = client.get(f"/qualita-della-vita/classifica/{url_level}")
            self.assertEqual(page.status_code, 200)
            self.assertEqual(client.get(f"/qualita-della-vita/classifica/{url_level}?profilo=giovani").status_code, 200)

            api = client.get(f"/api/quality-life/{url_level}/rankings")
            self.assertEqual(api.status_code, 200)
            self.assertEqual(api.get_json()["level"], "regione" if url_level == "regioni" else "provincia")
            self.assertEqual(client.get(f"/api/quality-life/{url_level}/rankings/nope").status_code, 404)

            one = client.get(f"/api/quality-life/{url_level}/{key}")
            self.assertEqual(one.status_code, 200)
            self.assertEqual(one.get_json()["territory"]["key"], key)
            self.assertEqual(client.get(f"/api/quality-life/{url_level}/atlantide").status_code, 404)

    def test_legacy_regional_api_alias(self):
        client = app.test_client()
        self.assertEqual(client.get("/api/quality-life/rankings").status_code, 200)
        self.assertEqual(client.get("/api/quality-life/region/lombardia").status_code, 200)


if __name__ == "__main__":
    unittest.main()
