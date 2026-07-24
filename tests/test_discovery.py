"""Discovery pipeline tests (pure stdlib: no Flask, runs in the hunter's env).

Covers the staging queue schema, the priority policy (fresh + regional first),
the conservative dedup classifier, the Eurostat adapter's NUTS2->region collapse
and freshest-honest-year logic, and the hunter/integrator round trip through a
temporary queue so production data is never touched.
"""

import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import discovery, eurostat_source, discover_candidates, promote_candidates


class FreshnessAndScoring(unittest.TestCase):
    def test_freshness_bands_match_external_layer(self):
        self.assertEqual(discovery.freshness_status(2025), "current")
        self.assertEqual(discovery.freshness_status(2023), "recent")
        self.assertEqual(discovery.freshness_status(2020), "dated")
        self.assertEqual(discovery.freshness_status(2019), "stale")
        self.assertEqual(discovery.freshness_status(None), "unknown")

    def test_priority_prefers_fresh_regional_new(self):
        fresh_regional_new = discovery.priority_score({
            "freshness_status": "current", "territory_level": "regione",
            "coverage": 1.0, "definition_match": "new",
        })
        stale_provincial_dup = discovery.priority_score({
            "freshness_status": "stale", "territory_level": "provincia",
            "coverage": 0.5, "definition_match": "exact",
        })
        self.assertGreater(fresh_regional_new, stale_provincial_dup)

    def test_regional_outranks_identical_provincial(self):
        base = {"freshness_status": "recent", "coverage": 1.0, "definition_match": "new"}
        self.assertGreater(
            discovery.priority_score({**base, "territory_level": "regione"}),
            discovery.priority_score({**base, "territory_level": "provincia"}),
        )


class DedupClassifier(unittest.TestCase):
    def test_new_when_no_overlap(self):
        index = [("1", "Numero di biblioteche pubbliche", discovery.normalize_name("Numero di biblioteche pubbliche"))]
        match, dup = discovery.classify_definition_match("Spesa in ricerca e sviluppo sul PIL", index)
        self.assertEqual(match, "new")
        self.assertEqual(dup, "")

    def test_overlap_flags_compatible_with_id(self):
        index = [("901", "PIL pro capite ai prezzi di mercato", discovery.normalize_name("PIL pro capite ai prezzi di mercato"))]
        match, dup = discovery.classify_definition_match("PIL pro capite ai prezzi di mercato (Eurostat)", index)
        self.assertIn(match, {"compatible", "proxy"})
        self.assertEqual(dup, "901")

    def test_never_claims_exact(self):
        index = [("901", "PIL pro capite", discovery.normalize_name("PIL pro capite"))]
        match, _ = discovery.classify_definition_match("PIL pro capite", index)
        self.assertNotEqual(match, "exact")


class EurostatAdapter(unittest.TestCase):
    def test_parse_collapses_bolzano_trento(self):
        doc = eurostat_source.fetch_dataset("rd_e_gerdreg", offline=True)
        regional = eurostat_source.parse_regional(doc)
        # 20 regions max, Trentino present once (Bolzano+Trento merged).
        self.assertLessEqual(len(regional), 20)
        self.assertIn("trentino-alto-adige", regional)
        for region_key in regional:
            self.assertIn(region_key, eurostat_source.REGION_NAMES)

    def test_best_recent_year_respects_coverage(self):
        doc = eurostat_source.fetch_dataset("nama_10r_2gdp", offline=True)
        regional = eurostat_source.parse_regional(doc)
        year, coverage, present = eurostat_source.best_recent_year(regional)
        self.assertIsNotNone(year)
        self.assertGreaterEqual(coverage, eurostat_source.MIN_COVERAGE)
        self.assertLessEqual(len(present), 20)

    def test_discover_produces_regional_candidate(self):
        raw = eurostat_source.discover("rd_e_gerdreg", offline=True)
        self.assertEqual(raw["territory_level"], "regione")
        self.assertEqual(raw["source"], "eurostat_regional")
        self.assertTrue(raw["year_max"])
        self.assertGreater(float(raw["coverage"]), 0.0)

    def test_normalized_rows_use_decimal_comma(self):
        rows = eurostat_source.normalized_rows("rd_e_gerdreg", offline=True)
        self.assertTrue(rows)
        self.assertTrue(all(row["region_key"] in eurostat_source.REGION_NAMES for row in rows))
        self.assertTrue(any("," in row["value"] for row in rows))


class QueueRoundTrip(unittest.TestCase):
    def setUp(self):
        self._original_path = discovery.CANDIDATES_PATH

    def tearDown(self):
        discovery.CANDIDATES_PATH = self._original_path

    def _patched_queue(self, tmp):
        # scripts share the same discovery module object, so one reassignment
        # redirects the queue everywhere (path is resolved at call time).
        path = Path(tmp) / "candidates.csv"
        discovery.CANDIDATES_PATH = path
        return path

    def test_hunter_writes_ranked_queue(self):
        with TemporaryDirectory() as tmp:
            path = self._patched_queue(tmp)
            discovered, merged = discover_candidates.run("eurostat_regional", offline=True)
            self.assertEqual(len(discovered), 2)
            rows = discovery.read_candidates(path)
            scores = [float(r["priority_score"]) for r in rows]
            self.assertEqual(scores, sorted(scores, reverse=True))
            self.assertTrue(all(r["triage_status"] == "new" for r in rows))

    def test_upsert_preserves_human_triage(self):
        reviewed = [{
            "candidate_id": "eurostat_regional:rd_e_gerdreg",
            "triage_status": "rejected", "triage_notes": "duplica un BES",
            "priority_score": "0.5",
        }]
        fresh = [{
            "candidate_id": "eurostat_regional:rd_e_gerdreg", "name": "x",
            "year_max": "2024", "coverage": 1.0, "freshness_status": "recent",
            "definition_match": "new", "territory_level": "regione",
            "priority_score": 0.9,
        }]
        merged = discovery.upsert_candidates(reviewed, fresh)
        entry = next(m for m in merged if m["candidate_id"] == "eurostat_regional:rd_e_gerdreg")
        self.assertEqual(entry["triage_status"], "rejected")
        self.assertEqual(entry["triage_notes"], "duplica un BES")
        self.assertEqual(entry["year_max"], "2024")  # data refreshed

    def test_promote_acts_only_on_approved(self):
        with TemporaryDirectory() as tmp:
            self._patched_queue(tmp)
            discover_candidates.run("eurostat_regional", offline=True)
            # Nothing approved yet -> no promotion.
            result = promote_candidates.run(offline=True, dry_run=True)
            self.assertEqual(result["approved"], 0)

            # Approve one candidate, then promote to temp outputs.
            rows = discovery.read_candidates()
            for row in rows:
                if row["candidate_id"] == "eurostat_regional:nama_10r_2gdp":
                    row["triage_status"] = "approved"
            discovery.write_candidates(rows)

            out_ds = Path(tmp) / "external.csv"
            out_mf = Path(tmp) / "manifest.csv"
            result = promote_candidates.run(offline=True, out_dataset=out_ds, out_manifest=out_mf)
            self.assertEqual(result["approved"], 1)
            self.assertGreater(result["dataset_rows"], 0)

            with out_ds.open(encoding="utf-8", newline="") as handle:
                ds_rows = list(csv.DictReader(handle, delimiter=";"))
            # GDP is a proxy of id 901 -> enriches that target, never score-eligible.
            self.assertTrue(all(r["target_indicator_id"] == "901" for r in ds_rows))
            self.assertTrue(all(r["score_eligible"] == "false" for r in ds_rows))
            with out_mf.open(encoding="utf-8", newline="") as handle:
                mf_rows = list(csv.DictReader(handle, delimiter=";"))
            self.assertTrue(all(r["status"] == "proposed" for r in mf_rows))

    def test_promote_new_indicator_gets_eur_namespace(self):
        with TemporaryDirectory() as tmp:
            self._patched_queue(tmp)
            discover_candidates.run("eurostat_regional", offline=True)
            rows = discovery.read_candidates()
            for row in rows:
                if row["candidate_id"] == "eurostat_regional:rd_e_gerdreg":  # definition_match == new
                    row["triage_status"] = "approved"
            discovery.write_candidates(rows)

            out_ds = Path(tmp) / "external.csv"
            out_mf = Path(tmp) / "manifest.csv"
            promote_candidates.run(offline=True, out_dataset=out_ds, out_manifest=out_mf)
            with out_ds.open(encoding="utf-8", newline="") as handle:
                ds_rows = list(csv.DictReader(handle, delimiter=";"))
            # A genuinely new series becomes a standalone atlas entry under eur:.
            self.assertTrue(all(r["target_indicator_id"] == "eur:rd_e_gerdreg" for r in ds_rows))
            self.assertTrue(all(r["atlas_eligible"] == "true" for r in ds_rows))
            self.assertTrue(all(r["score_eligible"] == "false" for r in ds_rows))


if __name__ == "__main__":
    unittest.main()
