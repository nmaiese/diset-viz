import unittest
import re
from html import unescape

from app import app, sources
from app import quality_life_bes as qb
from app.atlas_catalog import get_atlas_indicator
from app.bes_data import (
    all_bes_indicators,
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

        # La metodologia qualità della vita è stata unificata in /metodologia:
        # la vecchia URL fa 301 verso la sezione ancorata.
        redirect = client.get("/qualita-della-vita/metodologia")
        self.assertEqual(redirect.status_code, 301)
        self.assertIn("/metodologia", redirect.headers.get("Location", ""))
        methodology = client.get("/qualita-della-vita/metodologia", follow_redirects=True)
        self.assertEqual(methodology.status_code, 200)
        self.assertIn("Sole 24 Ore".encode("utf-8"), methodology.data)
        self.assertIn("z-score".encode("utf-8"), methodology.data)

    def test_quality_life_copy_uses_z_score_consistently(self):
        client = app.test_client()
        for path in (
            "/qualita-della-vita",
            "/qualita-della-vita/classifica/regioni",
            "/metodologia",
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
        # BES indicators render through the same template as every other family
        # now, so the checks are on the shared article skeleton rather than on
        # the wording of the old quality-of-life page.
        self.assertIn(b'id="sezione-dinamica"', page.data)
        self.assertIn(b'class="indicator-cockpit"', page.data)
        self.assertIn("media semplice".encode("utf-8"), page.data)
        self.assertIn(b"/metodologia#media-semplice", page.data)

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

    def test_sparse_latest_years_do_not_enter_the_score(self):
        for level in ("regione", "provincia"):
            matrix, _ = qb._matrix_and_meta(level)
            self.assertFalse(any(indicator_id.endswith("06POL001P") for indicator_id in matrix))

    def test_regional_score_uses_the_federated_indicator_selection(self):
        matrix, meta = qb._matrix_and_meta("regione")
        self.assertGreaterEqual(len(matrix), 200)
        families = set(item["source_family"] for item in meta.values())
        self.assertLessEqual({"bes", "territorial", "multiscopo"}, families)
        self.assertLessEqual(families, {"bes", "territorial", "multiscopo", *sources.EXTERNAL_FAMILIES})
        # Each external indicator is attributed to the family its id belongs
        # to, never to Eurostat by default.
        for indicator_id, item in meta.items():
            family = sources.split_internal_id(indicator_id)[0]
            if family in sources.EXTERNAL_FAMILIES:
                self.assertEqual(item["source_family"], family, indicator_id)
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

    def test_no_phenomenon_enters_the_score_twice_under_two_families(self):
        """The methodology promises exact name duplicates are counted once. The
        universe is federated, so the guarantee has to hold across every family,
        not only between BES and territorial."""
        from app.data import get_catalog
        from app.quality_life_selection import (
            _normalise_name,
            regional_quality_life_selection,
        )

        names = {}
        catalog = {item["id"]: item for item in get_catalog()["indicators"]}
        for indicator_id in regional_quality_life_selection():
            payload = get_atlas_indicator(indicator_id)
            raw = (payload["metadata"]["name"] if payload
                   else catalog[indicator_id]["name"])
            name = _normalise_name(raw)
            self.assertNotIn(
                name, names,
                f"{indicator_id} duplicates {names.get(name)} in the score",
            )
            names[name] = indicator_id

    def test_a_later_family_cannot_re_add_a_name_already_scored(self):
        """Guards the accumulating used_names: a Eurostat series named like an
        already selected indicator must not be added a second time."""
        from unittest import mock

        from app import quality_life_selection as qls

        first_id = next(iter(qls.regional_quality_life_selection()))
        payload = get_atlas_indicator(first_id)
        if payload is None:
            self.skipTest("no resolvable indicator to clone")
        clone = {
            "eur:clone_of_an_existing_name": {
                "name": payload["metadata"]["name"],
                "category": "reddito_accessibilita",
                "direction": "higher_better",
                "coverage": 1.0,
                "year_max": 2024,
            }
        }
        qls.regional_quality_life_selection.cache_clear()
        try:
            with mock.patch.object(qls, "has_external_data", return_value=True), \
                 mock.patch.object(qls, "external_regional_scoreables", return_value=clone):
                selection = qls.regional_quality_life_selection()
            self.assertNotIn("eur:clone_of_an_existing_name", selection)
        finally:
            qls.regional_quality_life_selection.cache_clear()

    def test_every_external_family_enters_the_regional_score_under_its_own_name(self):
        """The engine used to load only ids it took for Eurostat and to write
        "eurostat" as the source of every external indicator. Any registered
        external family must enter the matrix and keep its own attribution."""
        from unittest import mock

        regions = list(qb.get_bes_territories("regione"))
        for family in ("eurostat", "mef", "istat_demografia", "aci"):
            with self.subTest(family=family):
                public_id = sources.internal_id(family, "prova-famiglia")
                payload = {
                    "metadata": {
                        "raw_id": "prova-famiglia", "name": f"Serie di prova {family}",
                        "theme": "Reddito e ricchezza", "source_theme": "Reddito",
                        "year_max": 2024, "unit": "%", "path": f"/indicatore/prova/{family}",
                    },
                    "series": [
                        {"region_key": key, "year": 2024, "value": float(index)}
                        for index, key in enumerate(regions)
                    ],
                }
                info = {"name": payload["metadata"]["name"], "category": "reddito_accessibilita",
                        "direction": "higher_better", "coverage": 1.0, "year_max": 2024}
                with mock.patch.object(qb, "regional_quality_life_selection",
                                       return_value={public_id: "reddito_accessibilita"}), \
                     mock.patch.object(qb, "has_external_data", return_value=True), \
                     mock.patch.object(qb, "external_regional_scoreables", return_value={public_id: info}), \
                     mock.patch.object(qb, "get_external_atlas_indicator", return_value=payload):
                    matrix, meta = qb._matrix_and_meta.uncached("regione")
                self.assertIn(public_id, matrix)
                self.assertEqual(meta[public_id]["source_family"], family)

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
    LEVELS = {"regione": ("regioni", 20), "provincia": ("province", 107)}

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

    def test_profile_canonicals_match_indexability_and_sitemap(self):
        client = app.test_client()
        sitemap = unescape(client.get("/sitemap.xml").get_data(as_text=True))
        locs = re.findall(r"<loc>([^<]+)</loc>", sitemap)
        self.assertEqual(len(locs), len(set(locs)))

        profiles = [profile["slug"] for profile in qb.get_quality_life_profiles()]
        for url_level in ("regioni", "province"):
            for slug in profiles:
                suffix = "" if slug == qb.DEFAULT_PROFILE else f"?profilo={slug}"
                path = f"/qualita-della-vita/classifica/{url_level}{suffix}"
                expected = f"https://divarioitalia.it{path}"
                response = client.get(path)
                html = response.get_data(as_text=True)
                self.assertEqual(response.status_code, 200, path)
                self.assertIn(f'rel="canonical" href="{expected}"', html, path)
                self.assertFalse(response.headers["X-Robots-Tag"].startswith("noindex"), path)
                self.assertIn(expected, locs, path)

            invalid = f"/qualita-della-vita/classifica/{url_level}?profilo=inesistente"
            self.assertEqual(client.get(invalid).status_code, 404)
            self.assertNotIn(f"https://divarioitalia.it{invalid}", locs)

            alias = f"/qualita-della-vita/classifica/{url_level}?profile=giovani"
            alias_response = client.get(alias)
            self.assertEqual(alias_response.status_code, 200)
            self.assertTrue(alias_response.headers["X-Robots-Tag"].startswith("noindex"))

    def _provincial_matrix_with_fixture(self, **level_overrides):
        """Provincial matrix and ranking with the synthetic MEF series loaded,
        its levels manifest overridden (e.g. scoreable, direction)."""
        from unittest import mock

        from app import external_data, provincial_families
        from tests.fixtures import external_mef

        levels = [{**row, **level_overrides} for row in external_mef.levels()]
        # Il loader vuole lo stesso verso nelle righe e nel manifesto dei livelli.
        rows = [{**row, "direction": levels[0]["direction"]} for row in external_mef.rows()]
        memoized = (qb._matrix_and_meta, qb._indicators_by_category, qb._ranking_keys, qb.build_bes_ranking)

        def reset():
            provincial_families.cache_clear()
            for function in memoized:
                qb.cache.delete_memoized(function)

        reset()
        try:
            with mock.patch.object(external_data, "get_external_rows", return_value=rows), \
                 mock.patch.object(external_data, "get_external_levels", return_value=levels):
                matrix, meta = qb._matrix_and_meta("provincia")
                ranking = qb.build_bes_ranking("provincia", qb.DEFAULT_PROFILE)
        finally:
            reset()
        return external_mef.TARGET, matrix, meta, ranking

    def test_non_scoreable_external_series_stay_out_of_the_provincial_score(self):
        target, matrix, meta, ranking = self._provincial_matrix_with_fixture(
            scoreable="false", direction="higher_better")
        self.assertNotIn(target, matrix)
        self.assertNotIn(target, meta)
        self.assertEqual(set(ranking["methodology"]["source_counts"]), {"bes"})
        ids = {e["id"] for row in ranking["ranking"]
               for e in row["top_positive_indicators"] + row["top_negative_indicators"]}
        self.assertNotIn(target, ids)

    def test_a_contextual_series_stays_out_even_if_marked_scoreable(self):
        target, matrix, _, _ = self._provincial_matrix_with_fixture(
            scoreable="true", direction="contextual")
        self.assertNotIn(target, matrix)

    def test_a_scoreable_external_series_enters_after_bes_under_its_family(self):
        target, matrix, meta, ranking = self._provincial_matrix_with_fixture(
            scoreable="true", direction="higher_better")
        self.assertIn(target, matrix)
        provinces = set(qb.get_bes_territories("provincia"))
        self.assertLessEqual(set(matrix[target]), provinces)
        self.assertGreaterEqual(len(matrix[target]), 100)
        self.assertEqual(meta[target]["source_family"], "mef")
        self.assertEqual(meta[target]["category"], "reddito_accessibilita")
        # Il MEF ha anche il livello regionale: dalla classifica si atterra sulle province.
        self.assertTrue(meta[target]["path"].endswith("/province"), meta[target]["path"])
        method = ranking["methodology"]
        self.assertEqual(method["source_counts"]["mef"], 1)
        self.assertIn(sources.family_label("mef"), method["source"])
        self.assertEqual(method["catalog_institutions"], sources.institutions_label({"bes", "mef"}))
        self.assertEqual(method["score_indicators_total"], len(matrix))

    def test_legacy_regional_api_alias(self):
        client = app.test_client()
        self.assertEqual(client.get("/api/quality-life/rankings").status_code, 200)
        self.assertEqual(client.get("/api/quality-life/region/lombardia").status_code, 200)


if __name__ == "__main__":
    unittest.main()
