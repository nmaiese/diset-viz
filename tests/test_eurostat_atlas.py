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
        self.assertTrue(entry["path"].startswith("/indicatore/"))
        self.assertTrue(entry["path"].endswith("/eur-rd_e_gerdreg"))
        # The Eurostat family is offered as a source filter with a plain label.
        families = {f["id"]: f["label"] for f in catalog["source_families"]}
        self.assertEqual(families.get("eurostat"), "Eurostat, statistiche regionali")

    def test_api_and_page_and_sitemap(self):
        payload = get_atlas_indicator("eur:rd_e_gerdreg")
        self.assertIsNotNone(payload)
        meta = payload["metadata"]
        self.assertEqual(meta["explain"]["direction"], "higher_better")
        # Full historical series: multiple years, all 20 regions each year, and
        # Trentino Alto Adige present (Bolzano+Trento population-weighted).
        self.assertGreater(meta["year_max"], meta["year_min"])
        self.assertEqual(len({r["region_key"] for r in payload["series"]}), 20)
        self.assertIn("trentino-alto-adige", {r["region_key"] for r in payload["series"]})
        self.assertGreater(len(meta["spark"]), 1)

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


class EveryExternalFamilyIsReachable(unittest.TestCase):
    """One test per family, over every surface a promoted indicator touches.

    Adding the second external family (istat_demografia) found the same bug in
    five places at once: `eur:` was pinned as a literal in the atlas dispatcher,
    the quiz payload router, the quality-of-life selection, the curator worklist
    and the editorial lookup. Each one failed differently. The quiz was the worst
    of them, because the indicator entered the pool and then returned a null
    payload mid-round.

    So this is deliberately generic: it walks the families the registry declares,
    not the ones that existed when it was written, and a family added tomorrow is
    covered the day it lands.
    """

    @classmethod
    def setUpClass(cls):
        from app import sources
        from app.eurostat_atlas import all_eurostat_indicators

        by_family = {}
        for item in all_eurostat_indicators():
            by_family.setdefault(item["catalog_family"], item)
        cls.by_family = by_family
        cls.declared = [
            family for family in sources.EXTERNAL_FAMILIES
            if family in by_family
        ]

    def test_more_than_one_family_is_actually_exercised(self):
        """Otherwise the generality above is untested and drifts back."""
        self.assertGreater(len(self.declared), 1, self.by_family.keys())

    def test_each_family_resolves_renders_and_is_labelled_by_its_own_institution(self):
        from app import sources

        client = app.test_client()
        for family in self.declared:
            item = self.by_family[family]
            with self.subTest(family=family, id=item["id"]):
                payload = get_atlas_indicator(item["id"])
                self.assertIsNotNone(payload, "the atlas dispatcher must resolve it")
                meta = payload["metadata"]
                self.assertEqual(meta["institution"], sources.family_institution(family))
                self.assertEqual(meta["source_label"], sources.family_label(family))
                self.assertTrue(meta["license"], "a public page must state its licence")
                code = sources.indicator_code(family, meta["raw_id"])
                self.assertIn(code, meta["path"])
                self.assertEqual(client.get(meta["path"]).status_code, 200)
                self.assertNotEqual(meta["macro_area"], "Altro", meta["theme"])

    def test_each_family_builds_a_quiz_payload_when_it_is_in_the_pool(self):
        from app import quiz

        pool = {item["id"]: item for item in quiz._quiz_indicators()}
        for family in self.declared:
            item = self.by_family[family]
            entry = pool.get(item["id"])
            if entry is None:
                continue  # legitimately out of the pool (too few distinct values)
            with self.subTest(family=family, id=item["id"]):
                payload = quiz._quiz_indicator_payload(entry["id"], entry["year"])
                self.assertIsNotNone(payload, "in the pool but with no payload crashes a round")
                self.assertTrue(payload["values"])

    def test_each_family_is_visible_to_the_editorial_layer(self):
        from app import indicator_texts

        for family in self.declared:
            item = self.by_family[family]
            with self.subTest(family=family, id=item["id"]):
                article = indicator_texts.build_article(item["id"])
                self.assertEqual(
                    [s["role"] for s in article["sections"]],
                    list(indicator_texts.ROLE_ORDER),
                )

    def test_each_family_is_counted_in_the_catalog_families(self):
        counts = {f["id"]: f["indicator_count"] for f in get_atlas_catalog()["source_families"]}
        for family in self.declared:
            with self.subTest(family=family):
                self.assertGreater(counts.get(family, 0), 0)


if __name__ == "__main__":
    unittest.main()
