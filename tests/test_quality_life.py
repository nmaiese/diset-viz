import unittest

from app import app
from app import quality_life_bes as qb
from app.bes_data import (
    all_bes_indicators,
    bes_seo_description,
    bes_seo_title,
    bes_territory_label,
    get_bes_manifest,
    has_bes_data,
)
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

    def test_quality_life_copy_uses_z_score_consistently(self):
        client = app.test_client()
        for path in (
            "/qualita-della-vita",
            "/qualita-della-vita/classifica/regioni",
            "/qualita-della-vita/metodologia",
        ):
            page = client.get(path)
            self.assertEqual(page.status_code, 200, path)
            text = page.data.decode("utf-8")
            self.assertIn("z-score", text, path)
            self.assertNotIn("percentile orientato", text, path)

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

    def test_every_bes_indicator_has_a_public_page(self):
        client = app.test_client()
        indicators = all_bes_indicators()
        self.assertGreaterEqual(len(indicators), 145)
        self.assertGreater(sum(item["indexable"] for item in indicators), 100)

        sample = next(item for item in indicators if item["id"] == "09PAE009-N25")
        page = client.get(sample["path"])
        self.assertEqual(page.status_code, 200)
        self.assertIn("Densità di verde storico".encode("utf-8"), page.data)
        self.assertIn("valore più alto occupa la posizione migliore".encode("utf-8"), page.data)
        self.assertIn("come è cambiato nell'ultimo aggiornamento".encode("utf-8"), page.data)
        self.assertIn("media semplice dei valori".encode("utf-8"), page.data)

        sparse = next(item for item in indicators if item["id"] == "06POL001P")
        sparse_page = client.get(sparse["path"])
        self.assertEqual(sparse_page.status_code, 200)
        self.assertEqual(sparse_page.headers["X-Robots-Tag"], "noindex, follow")

        sitemap = client.get("/sitemap.xml").data.decode("utf-8")
        self.assertIn(sample["path"], sitemap)
        self.assertNotIn(sparse["path"], sitemap)

    def test_bes_labels_units_and_directions_are_resolved(self):
        expected_province = {
            "09PAE009-N25": ("Densità di verde storico", "higher_better", "per 100 m²"),
            "10AMB018P": ("Impermeabilizzazione del suolo da copertura artificiale", "lower_better", "%"),
            "12SER003P-N25": ("Posti letto negli ospedali", "higher_better", "per 10.000 abitanti"),
        }
        manifest = get_bes_manifest("provincia")
        for indicator_id, values in expected_province.items():
            item = manifest[indicator_id]
            self.assertEqual((item["name"], item["direction"], item["unit"]), values)

        region = get_bes_manifest("regione")
        self.assertEqual(region["01SAL001"]["year_max"], 2025)
        self.assertEqual(region["01SAL001"]["direction"], "higher_better")
        self.assertEqual(region["08BSO001"]["category"], "benessere_soggettivo")

    def test_bes_metadata_stays_within_serp_budgets(self):
        titles = []
        for item in all_bes_indicators():
            territory_label = bes_territory_label(item)
            title = bes_seo_title(item["name"], "Divario Italia", territory_label)
            titles.append(title)
            self.assertLessEqual(len(title), 60)
            self.assertLessEqual(
                len(bes_seo_description(item["name"], item["explain"]["plain"], territory_label)),
                155,
            )
        self.assertEqual(len(titles), len(set(titles)))

    def test_sparse_latest_years_do_not_enter_the_score(self):
        for level in ("regione", "provincia"):
            matrix, _ = qb._matrix_and_meta(level)
            self.assertFalse(any(indicator_id.endswith("06POL001P") for indicator_id in matrix))

    def test_regional_score_uses_the_federated_indicator_selection(self):
        matrix, meta = qb._matrix_and_meta("regione")
        self.assertGreaterEqual(len(matrix), 200)
        self.assertEqual(
            set(item["source_family"] for item in meta.values()), {"bes", "territorial", "multiscopo"}
        )
        self.assertTrue(all(
            item["year_max"] >= (2025 if item["source_family"] == "bes" else 2023)
            for item in meta.values()
        ))
        ranking = qb.build_bes_ranking("regione", "standard")
        self.assertEqual(
            ranking["data_freshness"]["current"] + ranking["data_freshness"]["recent"],
            len(matrix),
        )
        self.assertGreater(ranking["methodology"]["source_counts"]["bes"], 0)
        self.assertGreater(ranking["methodology"]["source_counts"]["territorial"], 0)

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

    def test_quality_life_downloads(self):
        client = app.test_client()
        csv_resp = client.get("/download/quality-life/regioni?profilo=giovani")
        self.assertEqual(csv_resp.status_code, 200)
        self.assertIn("text/csv", csv_resp.headers["Content-Type"])
        self.assertIn("noindex", csv_resp.headers["X-Robots-Tag"])
        self.assertIn(b"level,profile,rank,territory", csv_resp.data)
        json_resp = client.get("/download/quality-life/province.json")
        self.assertEqual(json_resp.status_code, 200)
        self.assertIn("noindex", json_resp.headers["X-Robots-Tag"])
        self.assertEqual(json_resp.get_json()["level"], "provincia")


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
            methodology = payload["methodology"]
            self.assertEqual(methodology["total_indicators"], methodology["score_indicators_total"])
            self.assertEqual(methodology["score_indicators_total"], sum(methodology["indicator_counts"].values()))
            self.assertGreaterEqual(methodology["manifest_indicators_total"], methodology["score_indicators_total"])
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
            profiled_page = client.get(f"/qualita-della-vita/classifica/{url_level}?profilo=giovani")
            self.assertEqual(profiled_page.status_code, 200)
            self.assertIn(f"/qualita-della-vita/classifica/{url_level}?profilo=giovani".encode("utf-8"), profiled_page.data)

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
