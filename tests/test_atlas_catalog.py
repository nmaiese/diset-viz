import unittest

from app import app
from app.atlas_catalog import (
    BES_ID_PREFIX,
    catalog_summary,
    get_atlas_catalog,
    get_atlas_theme_profile,
)
from app.bes_data import get_bes_manifest
from app.data import get_catalog
from app.multiscopo_data import get_multiscopo_manifest
from app.quality_life_config import QUALITY_LIFE_CATEGORIES
from app.taxonomy import CANONICAL_CATEGORIES, DUPLICATE_BES_IDS, MACRO_AREA_ORDER


class CatalogSummaryTest(unittest.TestCase):
    """One catalog, one size. The public surfaces used to quote three different
    totals for it: the home counted the territorial family alone, the themes
    beside it aggregated everything, and the quality-of-life page summed BES
    plus territorial while dropping Multiscopo and Eurostat."""

    def test_summary_matches_the_federated_catalog(self):
        summary = catalog_summary()
        indicators = get_atlas_catalog()["indicators"]
        self.assertEqual(summary["total"], len(indicators))
        self.assertEqual(
            sum(family["indicator_count"] for family in summary["families"]),
            summary["total"],
        )

    def setUp(self):
        # The home view is cached, and another test fills that cache with a
        # stub body. Start from a clean cache so we read the real page.
        from app import cache

        cache.clear()

    def test_home_and_quality_life_quote_the_same_catalog_size(self):
        from app.quality_life_bes import build_bes_ranking

        total = catalog_summary()["total"]
        methodology = build_bes_ranking("regione", "standard")["methodology"]
        self.assertEqual(methodology["manifest_indicators_total"], total)
        # The score is a subset of that catalog, never the whole of it.
        self.assertLess(methodology["score_indicators_total"], total)

        html = app.test_client().get("/").data.decode("utf-8")
        self.assertIn(f"{total} indicatori", html)

    def test_public_copy_names_every_institution_in_the_catalog(self):
        from app import sources

        summary = catalog_summary()
        expected = {
            sources.family_institution(family["id"]) for family in summary["families"]
        }
        for institution in expected:
            self.assertIn(institution, summary["institutions_label"])

        for path in ("/", "/qualita-della-vita/classifica/regioni"):
            html = app.test_client().get(path).data.decode("utf-8")
            for institution in expected:
                self.assertIn(institution, html, f"{institution} missing from {path}")


class FederatedAtlasCatalogTest(unittest.TestCase):
    def test_catalog_adds_every_non_duplicate_regional_bes_indicator_without_mutating_legacy_catalog(self):
        from app.eurostat_atlas import all_eurostat_indicators

        legacy = get_catalog()
        federated = get_atlas_catalog()
        bes_count = len(get_bes_manifest("regione")) - len(DUPLICATE_BES_IDS)
        multiscopo_count = len(get_multiscopo_manifest())
        eurostat_count = len(all_eurostat_indicators())

        self.assertEqual(
            len(federated["indicators"]),
            len(legacy["indicators"]) + bes_count + multiscopo_count + eurostat_count,
        )
        self.assertFalse(any(str(item["id"]).startswith(BES_ID_PREFIX) for item in legacy["indicators"]))
        self.assertEqual(
            sum(area["indicator_count"] for area in federated["macro_areas"]),
            len(federated["indicators"]),
        )
        families = {item["id"]: item["indicator_count"] for item in federated["source_families"]}
        self.assertEqual(families["territorial"], len(legacy["indicators"]))
        self.assertEqual(families["bes"], bes_count)
        self.assertEqual(families["multiscopo"], multiscopo_count)
        self.assertTrue(any(item["complete"] for item in federated["indicators"] if item["catalog_family"] == "bes"))
        scored = [item for item in federated["indicators"] if item["quality_life_scored"]]
        self.assertGreaterEqual(len(scored), 200)
        self.assertEqual(
            {item["catalog_family"] for item in scored}, {"bes", "territorial", "multiscopo", "eurostat"}
        )
        self.assertTrue(all(item["quality_life_category_label"] for item in scored))

    def test_exact_duplicate_bes_indicators_are_excluded_from_general_browsing(self):
        """These BES ids are the same Istat series (identical name and values) as an
        existing territorial indicator. They must not show up twice in the general
        catalog, so only the territorial id is kept for browsing/search/quiz."""
        federated = get_atlas_catalog()
        federated_ids = {str(item["id"]) for item in federated["indicators"]}
        for raw_id in DUPLICATE_BES_IDS:
            self.assertNotIn(f"{BES_ID_PREFIX}{raw_id}", federated_ids)

        from collections import Counter

        name_counts = Counter(item["name"].strip().lower() for item in federated["indicators"])
        duplicate_names = {
            "speranza di vita alla nascita",
            "coste marine balneabili",
            "disponibilità di verde urbano",
            "emigrazione ospedaliera in altra regione",
            "irregolarità nella distribuzione dell'acqua",
            "competenza alfabetica non adeguata (studenti classi iii scuola secondaria primo grado)",
            "competenza numerica non adeguata (studenti classi iii scuola secondaria primo grado)",
        }
        for name in duplicate_names:
            self.assertEqual(name_counts[name], 1, f"{name!r} still appears more than once in the atlas catalog")

    def test_theme_pages_use_the_same_federated_catalog(self):
        client = app.test_client()
        profile = get_atlas_theme_profile("benessere-soggettivo")
        self.assertIsNotNone(profile)
        self.assertTrue(any(item["id"].startswith(BES_ID_PREFIX) for item in profile["indicators"]))
        page = client.get("/tema/benessere-soggettivo")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Qualità della vita".encode("utf-8"), page.data)

    def test_public_taxonomy_is_shared_and_preserves_source_themes(self):
        catalog = get_atlas_catalog()
        self.assertEqual(len(catalog["themes"]), 12)
        self.assertEqual(len(catalog["macro_areas"]), 4)
        self.assertEqual(tuple(area["name"] for area in catalog["macro_areas"]), MACRO_AREA_ORDER)
        self.assertEqual(tuple(QUALITY_LIFE_CATEGORIES), tuple(CANONICAL_CATEGORIES))
        self.assertTrue(all(item["source_theme"] for item in catalog["indicators"]))
        # Named, not just asserted false. A promoted indicator brings its source
        # theme with it, and an unregistered theme falls through to "Altro": the
        # indicator then vanishes from the macro-area totals while still being in
        # the catalog. That is the failure a scheduled run produces, so the
        # message has to say which theme to add to CANONICAL_CATEGORIES rather
        # than "True is not false".
        unmapped = sorted({
            item["source_theme"] for item in catalog["indicators"]
            if item["macro_area"] == "Altro"
        })
        self.assertEqual(
            unmapped, [],
            "temi senza categoria (aggiungerli a CANONICAL_CATEGORIES[...]['themes'] "
            f"in app/taxonomy.py): {unmapped}",
        )
        self.assertEqual(
            sum(area["indicator_count"] for area in catalog["macro_areas"]),
            len(catalog["indicators"]),
            "ogni indicatore deve stare in una macro-area",
        )

    def test_duplicate_source_theme_urls_redirect_to_one_canonical_page(self):
        client = app.test_client()
        for source_slug in ("sicurezza", "legalita-e-sicurezza"):
            response = client.get(f"/tema/{source_slug}")
            self.assertEqual(response.status_code, 301)
            self.assertTrue(response.headers["Location"].endswith("/tema/sicurezza-e-legalita"))
        canonical = client.get("/tema/sicurezza-e-legalita")
        self.assertEqual(canonical.status_code, 200)
        self.assertIn("Legalità e sicurezza, Sicurezza".encode("utf-8"), canonical.data)

    def test_namespaced_bes_indicator_uses_the_standard_atlas_api_contract(self):
        client = app.test_client()
        catalog = client.get("/api/catalog").get_json()
        item = next(entry for entry in catalog["indicators"] if entry["id"].startswith(BES_ID_PREFIX))

        response = client.get(f"/api/indicator/{item['id']}")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["metadata"]["id"], item["id"])
        self.assertEqual(payload["metadata"]["catalog_family"], "bes")
        self.assertEqual(payload["metadata"]["source_label"], "Istat, BES nazionale, aggiornamento intermedio 2026")
        self.assertTrue(payload["metadata"]["path"].startswith("/indicatore/"))
        self.assertTrue(payload["metadata"]["path"].rsplit("/", 1)[-1].startswith("bes-"))
        self.assertEqual(client.get(payload["metadata"]["path"]).status_code, 200)
        self.assertTrue(payload["series"])
        self.assertLessEqual(len(payload["metadata"]["regions"]), 20)

        year = payload["metadata"]["year_max"]
        year_response = client.get(f"/api/indicator/{item['id']}/year/{year}")
        self.assertEqual(year_response.status_code, 200)
        self.assertEqual(year_response.get_json()["year"], year)
        self.assertEqual(client.get(f"/download/indicator/{item['id']}.json").status_code, 200)

        search = client.get("/api/search?q=benessere+soggettivo").get_json()["results"]
        self.assertTrue(any(entry["id"].startswith(BES_ID_PREFIX) for entry in search))

    def test_unknown_namespaced_indicator_is_404(self):
        client = app.test_client()
        self.assertEqual(client.get("/api/indicator/bes:does-not-exist").status_code, 404)
