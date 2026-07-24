"""Phase 2: Eurostat regional indicators as first-class atlas entries.

A genuinely new external indicator (no Istat counterpart) becomes a standalone
atlas indicator: it is in the federated catalog, has its own unified URL, renders
the same map/ranking page, is searchable and listed in the sitemap, and carries a
plain user-facing source label. Enriching overlaps stay attached to the Istat id
they point at, never duplicated as a separate catalog entry.
"""

import unittest

from app import app
from app.atlas_catalog import get_atlas_catalog, get_atlas_indicator
from app.eurostat_atlas import all_eurostat_indicators, has_eurostat_data


class EurostatAtlasFamilyTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_pilot_data_present(self):
        self.assertTrue(has_eurostat_data())
        ids = {item["id"] for item in all_eurostat_indicators()}
        self.assertIn("eur:rd_e_gerdreg", ids)

    def test_standalone_indicator_in_federated_catalog(self):
        catalog = get_atlas_catalog()
        entry = next(i for i in catalog["indicators"] if i["id"] == "eur:rd_e_gerdreg")
        self.assertEqual(entry["catalog_family"], "eurostat")
        self.assertEqual(entry["catalog_family_label"], "Eurostat, statistiche regionali")
        self.assertEqual(entry["theme"], "Ricerca, innovazione e digitale")
        self.assertTrue(entry["path"].startswith("/indicatore/eur-rd_e_gerdreg/"))
        # The Eurostat family is offered as a source filter with a plain label.
        families = {f["id"]: f["label"] for f in catalog["source_families"]}
        self.assertEqual(families.get("eurostat"), "Eurostat, statistiche regionali")

    def test_api_and_page_and_sitemap(self):
        payload = get_atlas_indicator("eur:rd_e_gerdreg")
        self.assertIsNotNone(payload)
        self.assertEqual(payload["metadata"]["explain"]["direction"], "higher_better")
        self.assertEqual(len(payload["series"]), 20)

        path = payload["metadata"]["path"]
        self.assertEqual(self.client.get(path).status_code, 200)
        self.assertEqual(
            self.client.get("/indicatore/eur-rd_e_gerdreg").status_code, 301  # missing slug -> canonical
        )
        sitemap = self.client.get("/sitemap.xml").data.decode("utf-8")
        self.assertIn(path, sitemap)

    def test_enriching_overlap_is_not_a_separate_entry(self):
        # The Eurostat GDP series is a proxy of territorial 901: it enriches 901
        # and must NOT appear as its own catalog entry.
        ids = {item["id"] for item in all_eurostat_indicators()}
        self.assertNotIn("eur:nama_10r_2gdp", ids)

    def test_scored_after_curation(self):
        # The pilot R&D indicator has been curated (verso confirmed, score_eligible),
        # so it now contributes to the regional quality-of-life score.
        entry = next(i for i in get_atlas_catalog()["indicators"] if i["id"] == "eur:rd_e_gerdreg")
        self.assertTrue(entry["quality_life_scored"])
        self.assertEqual(entry["quality_life_category"], "ricerca_innovazione_digitale")
        # Reviewed description overrides the auto-generated one.
        payload = get_atlas_indicator("eur:rd_e_gerdreg")
        self.assertIn("investe in ricerca e sviluppo", payload["metadata"]["explain"]["plain"])


if __name__ == "__main__":
    unittest.main()
