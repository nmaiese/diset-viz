"""End-to-end discovery pipeline: hunter -> promote -> curate -> apply, as one chain.

The per-stage tests (test_discovery, test_curation) each cover a link. Nothing
tied the whole automation together, so a regression that only shows up when the
stages run in sequence (a promoted series that loses its history before curation,
a curated indicator that never reaches status=integrated) would pass every
existing test. This walks a real candidate the full way on temporary files, so
committed data is never touched, and asserts the invariants the scheduled agents
rely on.

Pure stdlib + the app's data layer for the final atlas-resolution check.
"""

import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import discovery, discover_candidates, promote_candidates, curate, apply_curation

REGION_COUNT = 20  # the 20 Italian regions the atlas is keyed on


def _write_semicolon(path, header, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        handle.write(header + "\n")
        for row in rows:
            handle.write(row + "\n")


class FullChainEurostatNewIndicator(unittest.TestCase):
    """A genuinely new Eurostat series (rd_e_gerdreg) taken from discovery all the
    way to a score-eligible, integrated atlas entry with its full history."""

    TARGET = "eur:rd_e_gerdreg"
    SERIES = "rd_e_gerdreg"

    def setUp(self):
        self._original_path = discovery.CANDIDATES_PATH

    def tearDown(self):
        discovery.CANDIDATES_PATH = self._original_path

    def _patched_queue(self, tmp):
        path = Path(tmp) / "candidates.csv"
        discovery.CANDIDATES_PATH = path
        return path

    def _curation_file(self, tmp):
        path = Path(tmp) / "curation.csv"
        header = ";".join(curate.CURATION_COLUMNS)
        cols = {c: "" for c in curate.CURATION_COLUMNS}
        cols.update({
            "target_indicator_id": self.TARGET,
            "source": "eurostat_regional",
            "source_indicator_id": self.SERIES,
            "name": "Spesa in ricerca e sviluppo sul PIL (Eurostat, NUTS2)",
            "reviewed_direction": "higher_better",
            "direction_verdict": "confermato",
            "reviewed_category": "ricerca_innovazione_digitale",
            "score_eligible": "true",
            "description": "Quanto ogni regione investe in ricerca e sviluppo sul PIL.",
            "value_explanation": "Percentuale del PIL regionale.",
            "reviewer_notes": "Verso confermato dai dati.",
            "reviewed_at": "2026-07-24",
        })
        _write_semicolon(path, header, [";".join(cols[c] for c in curate.CURATION_COLUMNS)])
        return path

    def test_new_series_flows_from_discovery_to_integrated_with_full_history(self):
        with TemporaryDirectory() as tmp:
            self._patched_queue(tmp)
            out_ds = Path(tmp) / "external.csv"
            out_mf = Path(tmp) / "manifest.csv"
            out_desc = Path(tmp) / "descriptions.csv"

            # --- STAGE 1: hunter discovers the candidate into the queue ---------
            discovered, _ = discover_candidates.run("eurostat_regional", offline=True)
            self.assertIn(
                self.SERIES, [c["source_indicator_id"] for c in discovered],
                "hunter did not surface the pilot series",
            )
            queued = {c["candidate_id"]: c for c in discovery.read_candidates()}
            cand = queued[f"eurostat_regional:{self.SERIES}"]
            self.assertEqual(cand["triage_status"], "new")
            self.assertEqual(cand["definition_match"], "new")

            # --- human gate: approve it -----------------------------------------
            rows = discovery.read_candidates()
            for row in rows:
                if row["candidate_id"] == f"eurostat_regional:{self.SERIES}":
                    row["triage_status"] = "approved"
            discovery.write_candidates(rows)

            # --- STAGE 2: promotion writes the external layer -------------------
            result = promote_candidates.run(offline=True, out_dataset=out_ds, out_manifest=out_mf)
            self.assertEqual(result["approved"], 1)

            with out_ds.open(encoding="utf-8", newline="") as handle:
                ds_rows = [r for r in csv.DictReader(handle, delimiter=";")
                           if r["target_indicator_id"] == self.TARGET]
            self.assertTrue(ds_rows, "promotion wrote no rows for the new target")

            # FULL HISTORICAL SERIES, not just the latest year. Every year the
            # source covers must land, each with all 20 regions, so the atlas
            # scheda has its multi-year chart. A regression to last-year-only
            # would leave one year here.
            years = sorted({int(r["year"]) for r in ds_rows})
            self.assertGreater(len(years), 1, f"only one year promoted: {years}")
            for year in years:
                regions = {r["territory_name"] for r in ds_rows if int(r["year"]) == year}
                self.assertEqual(
                    len(regions), REGION_COUNT,
                    f"year {year} has {len(regions)} regions, expected {REGION_COUNT}",
                )
            self.assertEqual(len(ds_rows), len(years) * REGION_COUNT)

            # promotion never pre-empts review: proposed, not integrated/scored.
            self.assertTrue(all(r["atlas_eligible"] == "true" for r in ds_rows))
            self.assertTrue(all(r["score_eligible"] == "false" for r in ds_rows))
            with out_mf.open(encoding="utf-8", newline="") as handle:
                mf_entry = next(r for r in csv.DictReader(handle, delimiter=";")
                                if r["target_indicator_id"] == self.TARGET)
            self.assertEqual(mf_entry["status"], "proposed")

            # --- STAGE 3: curation direction evidence, then apply ---------------
            evidence = curate.direction_evidence(self.TARGET, curate.read_external(out_ds))
            self.assertIsNotNone(evidence)
            self.assertEqual(evidence["proposed_direction"], "higher_better")

            curation = self._curation_file(tmp)
            applied = apply_curation.run(
                dataset=out_ds, manifest=out_mf, descriptions=out_desc, curation_path=curation,
            )
            self.assertEqual(applied["score_eligible"], 1)

            with out_ds.open(encoding="utf-8", newline="") as handle:
                ds_after = [r for r in csv.DictReader(handle, delimiter=";")
                            if r["target_indicator_id"] == self.TARGET]
            # curation flips the flags but must not drop any of the history.
            self.assertEqual(len(ds_after), len(years) * REGION_COUNT,
                             "curation changed the row count of the series")
            self.assertTrue(all(r["direction"] == "higher_better" for r in ds_after))
            self.assertTrue(all(r["score_eligible"] == "true" for r in ds_after))
            with out_mf.open(encoding="utf-8", newline="") as handle:
                mf_after = next(r for r in csv.DictReader(handle, delimiter=";")
                                if r["target_indicator_id"] == self.TARGET)
            self.assertEqual(mf_after["status"], "integrated")
            self.assertEqual(mf_after["score_eligible"], "true")
            with out_desc.open(encoding="utf-8", newline="") as handle:
                self.assertTrue(list(csv.DictReader(handle, delimiter=";")),
                                "curated description was not written")


if __name__ == "__main__":
    unittest.main()
