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

from scripts import (
    discovery, eurostat_source, istat_regional_source,
    discover_candidates, promote_candidates,
)


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

    def test_existing_index_ids_carry_their_family(self):
        """A raw id is only unique inside a family, so a match on a BES or
        Multiscopo series has to name the family or the promotion step cannot
        tell which indicator it means."""
        index = discovery.build_existing_index()
        by_prefix = {
            "bes:": sum(1 for i, _, _ in index if i.startswith("bes:")),
            "multiscopo:": sum(1 for i, _, _ in index if i.startswith("multiscopo:")),
        }
        for prefix, count in by_prefix.items():
            self.assertGreater(count, 0, f"no {prefix} entries in the index")
        # The territorial family owns the unprefixed namespace.
        self.assertTrue(any(i.isdigit() for i, _, _ in index))

    def test_promotion_refuses_a_candidate_id_that_lies_about_its_source(self):
        """Found end-to-end: the dataset merge is keyed on the source series, so
        a queue row whose candidate_id no longer matches its own source fields
        overwrites and retargets another candidate's series, silently removing a
        live atlas entry. The queue is hand-edited in the review PR, so the
        mismatch has to fail before anything is written."""
        from scripts import promote_candidates

        good = {"candidate_id": "eurostat_regional:rd_e_gerdreg",
                "source": "eurostat_regional", "source_indicator_id": "rd_e_gerdreg"}
        promote_candidates._check_candidate_id(good)  # non solleva

        lying = dict(good, candidate_id="eurostat_regional:qualcos_altro")
        with self.assertRaises(SystemExit):
            promote_candidates._check_candidate_id(lying)

    def test_promotion_refuses_an_unqualified_duplicate_target(self):
        from scripts import promote_candidates

        candidate = {
            "candidate_id": "eurostat_regional:x",
            "definition_match": "compatible",
            "duplicate_of": "10AMB014",  # a BES id without its family
            "source_indicator_id": "x",
        }
        with self.assertRaises(SystemExit):
            promote_candidates._target_id(candidate)

        candidate["duplicate_of"] = "bes:10AMB014"
        self.assertEqual(promote_candidates._target_id(candidate), "bes:10AMB014")


class EurostatAdapter(unittest.TestCase):
    def test_parse_weights_bolzano_trento(self):
        doc = eurostat_source.fetch_dataset("rd_e_gerdreg", offline=True)
        weights = eurostat_source.fetch_weights(offline=True)
        regional = eurostat_source.parse_regional(doc, "weighted", weights)
        # Trentino present once (Bolzano+Trento combined by population weight),
        # 20 regions, and the value sits between the two provincial figures.
        self.assertIn("trentino-alto-adige", regional)
        self.assertEqual(len(regional), 20)
        for region_key in regional:
            self.assertIn(region_key, eurostat_source.REGION_NAMES)
        tv = regional["trentino-alto-adige"]["2023"]
        self.assertGreater(tv, 1.0)
        self.assertLess(tv, 1.3)

    def test_weighted_needs_weights_else_drops_split(self):
        # Without weights the split region cannot be combined honestly: dropped,
        # never silently averaged.
        doc = eurostat_source.fetch_dataset("rd_e_gerdreg", offline=True)
        regional = eurostat_source.parse_regional(doc, "weighted", weights=None)
        self.assertNotIn("trentino-alto-adige", regional)

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
            self.assertEqual(len(discovered), len(eurostat_source.EUROSTAT_SERIES))
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

    def test_retargeting_a_series_moves_its_manifest_entry(self):
        """Found end-to-end. Confirming a match in the review PR (editing
        duplicate_of on an already promoted candidate) is the documented way a
        series changes target. The data rows follow the new target, so the
        manifest entry has to follow too: keying it on the target as well left
        the old entry behind, still claiming status=integrated for an indicator
        with no data. Placeholder entries carry no source and must survive."""
        with TemporaryDirectory() as tmp:
            self._patched_queue(tmp)
            discover_candidates.run("eurostat_regional", offline=True)
            rows = discovery.read_candidates()
            for row in rows:
                if row["candidate_id"] == "eurostat_regional:rd_e_gerdreg":
                    row["triage_status"] = "approved"
            discovery.write_candidates(rows)

            out_ds = Path(tmp) / "external.csv"
            out_mf = Path(tmp) / "manifest.csv"
            promote_candidates.run(offline=True, out_dataset=out_ds, out_manifest=out_mf)

            # Un segnaposto senza fonte, come quelli reali (status=unavailable).
            with out_mf.open(encoding="utf-8", newline="") as handle:
                manifest = list(csv.DictReader(handle, delimiter=";"))
            placeholder = {c: "" for c in promote_candidates.MANIFEST_COLUMNS}
            placeholder.update({"target_indicator_id": "999", "status": "unavailable"})
            manifest.append(placeholder)
            with out_mf.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=promote_candidates.MANIFEST_COLUMNS,
                                        delimiter=";", lineterminator="\n")
                writer.writeheader()
                writer.writerows(manifest)

            # Un umano conferma il match: la stessa serie ora aggancia un BES.
            rows = discovery.read_candidates()
            for row in rows:
                if row["candidate_id"] == "eurostat_regional:rd_e_gerdreg":
                    row.update({"definition_match": "compatible",
                                "duplicate_of": "bes:01SAL002",
                                "triage_status": "approved"})
            discovery.write_candidates(rows)
            promote_candidates.run(offline=True, out_dataset=out_ds, out_manifest=out_mf)

            with out_mf.open(encoding="utf-8", newline="") as handle:
                manifest = list(csv.DictReader(handle, delimiter=";"))
            for_series = [r for r in manifest if r["source_indicator_id"] == "rd_e_gerdreg"]
            self.assertEqual(len(for_series), 1, "the manifest entry was duplicated, not moved")
            self.assertEqual(for_series[0]["target_indicator_id"], "bes:01SAL002")
            self.assertEqual(
                [r for r in manifest if r["target_indicator_id"] == "eur:rd_e_gerdreg"], [],
                "stale entry left behind for the old target",
            )
            self.assertEqual(
                len([r for r in manifest if not r["source"] and not r["source_indicator_id"]]), 1,
                "the source-less placeholder entry was collapsed",
            )


class IstatRegionalAdapter(unittest.TestCase):
    def test_parse_regional_combines_bolzano_trento(self):
        rows = istat_regional_source.fetch_rows("OLDAGEDEPR", offline=True)
        regional = istat_regional_source.parse_regional(rows, "OLDAGEDEPR")
        # 20 regions, Trentino present once (Bolzano+Trento combined by weight),
        # its value sitting between the two provincial figures.
        self.assertEqual(len(regional), istat_regional_source.REGION_COUNT)
        self.assertIn(istat_regional_source.TRENTINO_NAME, regional)
        parts = {}
        for row in rows:
            if row["DATA_TYPE"] == "OLDAGEDEPR" and row["REF_AREA"] in istat_regional_source.TRENTINO_PARTS:
                parts.setdefault(row["TIME_PERIOD"], {})[row["REF_AREA"]] = float(row["OBS_VALUE"])
        year = max(istat_regional_source.parse_regional(rows, "OLDAGEDEPR")[istat_regional_source.TRENTINO_NAME])
        combined = regional[istat_regional_source.TRENTINO_NAME][year]
        lo, hi = sorted(parts[year].values())
        self.assertGreaterEqual(combined, lo)
        self.assertLessEqual(combined, hi)

    def test_best_recent_year_respects_coverage(self):
        rows = istat_regional_source.fetch_rows("DEPENDRATE", offline=True)
        regional = istat_regional_source.parse_regional(rows, "DEPENDRATE")
        year, coverage, present = istat_regional_source.best_recent_year(regional)
        self.assertIsNotNone(year)
        self.assertGreaterEqual(coverage, istat_regional_source.MIN_COVERAGE)
        self.assertLessEqual(len(present), istat_regional_source.REGION_COUNT)

    def test_discover_produces_regional_candidate(self):
        raw = istat_regional_source.discover("OLDAGEDEPR", offline=True)
        self.assertEqual(raw["territory_level"], "regione")
        self.assertEqual(raw["source"], "istat_demografia")
        self.assertEqual(raw["source_dataset"], istat_regional_source.DATAFLOW)
        self.assertTrue(raw["year_max"])
        self.assertGreater(float(raw["coverage"]), 0.0)

    def test_normalized_rows_use_decimal_comma(self):
        rows = istat_regional_source.normalized_rows("OLDAGEDEPR", offline=True)
        self.assertTrue(rows)
        self.assertTrue(any("," in row["value"] for row in rows))

    def test_hunter_discovers_new_istat_candidates(self):
        with TemporaryDirectory() as tmp:
            discovery.CANDIDATES_PATH = Path(tmp) / "candidates.csv"
            discovered, _ = discover_candidates.run("istat_demografia", offline=True)
            self.assertEqual(len(discovered), len(istat_regional_source.ISTAT_SERIES))
            for cand in discovered:
                self.assertEqual(cand["source"], "istat_demografia")
                self.assertEqual(cand["territory_level"], "regione")
                self.assertEqual(cand["triage_status"], "new")


if __name__ == "__main__":
    unittest.main()
