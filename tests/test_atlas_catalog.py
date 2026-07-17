import unittest

from app import app
from app.atlas_catalog import BES_ID_PREFIX, get_atlas_catalog, get_atlas_theme_profile
from app.bes_data import get_bes_manifest
from app.data import get_catalog


class FederatedAtlasCatalogTest(unittest.TestCase):
    def test_catalog_adds_every_regional_bes_indicator_without_mutating_legacy_catalog(self):
        legacy = get_catalog()
        federated = get_atlas_catalog()
        bes_count = len(get_bes_manifest("regione"))

        self.assertEqual(len(federated["indicators"]), len(legacy["indicators"]) + bes_count)
        self.assertFalse(any(str(item["id"]).startswith(BES_ID_PREFIX) for item in legacy["indicators"]))
        self.assertEqual(
            sum(area["indicator_count"] for area in federated["macro_areas"]),
            len(federated["indicators"]),
        )
        families = {item["id"]: item["indicator_count"] for item in federated["source_families"]}
        self.assertEqual(families["territorial"], len(legacy["indicators"]))
        self.assertEqual(families["bes"], bes_count)
        self.assertTrue(any(item["complete"] for item in federated["indicators"] if item["catalog_family"] == "bes"))
        scored = [item for item in federated["indicators"] if item["quality_life_scored"]]
        self.assertGreaterEqual(len(scored), 200)
        self.assertEqual({item["catalog_family"] for item in scored}, {"bes", "territorial"})
        self.assertTrue(all(item["quality_life_category_label"] for item in scored))

    def test_theme_pages_use_the_same_federated_catalog(self):
        client = app.test_client()
        profile = get_atlas_theme_profile("benessere-soggettivo")
        self.assertIsNotNone(profile)
        self.assertTrue(any(item["id"].startswith(BES_ID_PREFIX) for item in profile["indicators"]))
        page = client.get("/tema/benessere-soggettivo")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Qualità della vita".encode("utf-8"), page.data)

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
        self.assertTrue(payload["metadata"]["path"].startswith("/qualita-della-vita/indicatore/"))
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
