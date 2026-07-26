"""Curator layer: direction evidence and the publish (apply) step.

Pure stdlib. The apply step is exercised against temporary CSVs so production
data is never touched.
"""

import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import curate, apply_curation


class CuratorWorklistEmpties(unittest.TestCase):
    """A curated indicator must leave the worklist, whatever the verdict was.

    The queue used to key on `score_eligible`, so `contextual` (a final and
    common verdict) never cleared it: a scheduled curator would have re-reviewed
    the same indicator and opened a PR for it every run, forever.
    """

    ROWS = [
        {"target_indicator_id": "dem:X", "atlas_eligible": "true", "score_eligible": "false"},
        {"target_indicator_id": "eur:Y", "atlas_eligible": "true", "score_eligible": "true"},
        {"target_indicator_id": "eur:Z", "atlas_eligible": "true", "score_eligible": "false"},
        {"target_indicator_id": "901", "atlas_eligible": "true", "score_eligible": "false"},
    ]

    def test_a_contextual_decision_clears_the_worklist(self):
        decisions = [{"target_indicator_id": "dem:X", "reviewed_direction": "contextual",
                      "score_eligible": "false"}]
        left = curate.uncurated_targets(self.ROWS, decisions)
        self.assertNotIn("dem:X", left)
        self.assertIn("eur:Z", left, "an unreviewed one stays")

    def test_an_enriching_target_is_not_a_curator_job(self):
        """Bare numeric ids enrich an existing indicator, they are not entries."""
        self.assertNotIn("901", curate.uncurated_targets(self.ROWS, []))

    def test_every_external_family_is_visible_to_the_curator(self):
        left = curate.uncurated_targets(self.ROWS, [])
        self.assertIn("dem:X", left)
        self.assertIn("eur:Y", left)


DATASET_HEADER = ";".join(apply_curation.EXTERNAL_COLUMNS)
MANIFEST_HEADER = ";".join(apply_curation.MANIFEST_COLUMNS)


def _dataset_row(region, value):
    cols = {c: "" for c in apply_curation.EXTERNAL_COLUMNS}
    cols.update({
        "source": "eurostat_regional", "source_dataset": "demo", "source_indicator_id": "demo",
        "target_indicator_id": "eur:demo", "name": "Indicatore demo", "territory_level": "regione",
        "territory_code": region.lower(), "territory_name": region, "year": "2023", "value": value,
        "unit": "%", "theme": "Ricerca e sviluppo (Eurostat)", "quality_life_category": "ricerca_innovazione_digitale",
        "direction": "contextual", "definition_match": "new", "atlas_eligible": "true",
        "profile_eligible": "false", "score_eligible": "false", "coverage": "1.0",
    })
    return ";".join(cols[c] for c in apply_curation.EXTERNAL_COLUMNS)


class DirectionEvidenceTest(unittest.TestCase):
    def test_ranks_regions_on_latest_year(self):
        rows = [
            {"target_indicator_id": "eur:demo", "name": "x", "unit": "%", "year": "2023",
             "value": v, "coverage": "1.0", "direction": "higher_better",
             "quality_life_category": "ricerca_innovazione_digitale", "definition_match": "new",
             "territory_name": name}
            for name, v in [("Alta", "2,0"), ("Media", "1,0"), ("Bassa", "0,5")]
        ]
        ev = curate.direction_evidence("eur:demo", rows)
        self.assertEqual(ev["highest"][0][0], "Alta")
        self.assertEqual(ev["lowest"][-1][0], "Bassa")
        self.assertEqual(ev["proposed_direction"], "higher_better")


class ApplyCurationTest(unittest.TestCase):
    def _setup(self, tmp, decision):
        # Everything (including the curation file) lives under tmp and is passed
        # explicitly, so the committed data/discovery/curation.csv is never touched.
        ds = Path(tmp) / "external.csv"
        mf = Path(tmp) / "manifest.csv"
        desc = Path(tmp) / "desc.csv"
        curation = Path(tmp) / "curation.csv"
        ds.write_text(DATASET_HEADER + "\n" + _dataset_row("Lazio", "1,0") + "\n"
                      + _dataset_row("Molise", "0,4") + "\n", encoding="utf-8")
        mf_cols = {c: "" for c in apply_curation.MANIFEST_COLUMNS}
        mf_cols.update({"target_indicator_id": "eur:demo", "target_indicator_name": "Indicatore demo",
                        "source": "eurostat_regional", "source_indicator_id": "demo",
                        "definition_match": "new", "direction": "contextual",
                        "score_eligible": "false", "status": "proposed"})
        mf.write_text(MANIFEST_HEADER + "\n" + ";".join(mf_cols[c] for c in apply_curation.MANIFEST_COLUMNS) + "\n",
                      encoding="utf-8")
        curate.write_curation([decision], path=curation)
        return ds, mf, desc, curation

    def test_apply_flips_score_and_direction_and_writes_description(self):
        with TemporaryDirectory() as tmp:
            ds, mf, desc, curation = self._setup(tmp, {
                "target_indicator_id": "eur:demo", "reviewed_direction": "higher_better",
                "direction_verdict": "confermato", "reviewed_category": "ricerca_innovazione_digitale",
                "score_eligible": "true", "description": "Testo rivisto.", "value_explanation": "Unita.",
                "reviewer_notes": "ok", "reviewed_at": "2026-07-24",
            })
            result = apply_curation.run(dataset=ds, manifest=mf, descriptions=desc, curation_path=curation)
            self.assertEqual(result["score_eligible"], 1)

            with ds.open(encoding="utf-8", newline="") as h:
                ds_rows = list(csv.DictReader(h, delimiter=";"))
            self.assertTrue(all(r["direction"] == "higher_better" for r in ds_rows))
            self.assertTrue(all(r["score_eligible"] == "true" for r in ds_rows))
            with mf.open(encoding="utf-8", newline="") as h:
                mf_row = next(csv.DictReader(h, delimiter=";"))
            self.assertEqual(mf_row["status"], "integrated")
            self.assertEqual(mf_row["score_eligible"], "true")
            with desc.open(encoding="utf-8", newline="") as h:
                desc_row = next(csv.DictReader(h, delimiter=";"))
            self.assertEqual(desc_row["plain"], "Testo rivisto.")

    def test_a_decision_only_touches_its_own_source_series(self):
        """Two sources can enrich the same indicator. Reviewing one of them must
        not rewrite the direction and the score flag of the other, which nobody
        has looked at."""
        reviewed = {
            "target_indicator_id": "eur:demo", "source": "eurostat_regional",
            "source_indicator_id": "demo", "reviewed_direction": "higher_better",
            "score_eligible": "true", "reviewed_at": "2026-07-24",
        }
        rows = [
            {"target_indicator_id": "eur:demo", "source": "eurostat_regional",
             "source_indicator_id": "demo", "direction": "contextual",
             "score_eligible": "false"},
            {"target_indicator_id": "eur:demo", "source": "altra_fonte",
             "source_indicator_id": "altra", "direction": "contextual",
             "score_eligible": "false"},
        ]
        dataset, manifest, _ = apply_curation.apply([reviewed], rows, [], [])
        self.assertEqual(dataset[0]["direction"], "higher_better")
        self.assertEqual(dataset[0]["score_eligible"], "true")
        self.assertEqual(dataset[1]["direction"], "contextual")
        self.assertEqual(dataset[1]["score_eligible"], "false")

    def test_two_descriptions_for_one_target_are_a_conflict(self):
        decisions = [
            {"target_indicator_id": "eur:demo", "source": "a", "source_indicator_id": "1",
             "reviewed_direction": "higher_better", "description": "Prima versione.",
             "reviewed_at": "2026-07-24"},
            {"target_indicator_id": "eur:demo", "source": "b", "source_indicator_id": "2",
             "reviewed_direction": "higher_better", "description": "Seconda versione.",
             "reviewed_at": "2026-07-24"},
        ]
        with self.assertRaises(SystemExit):
            apply_curation.apply(decisions, [], [], [])

    def test_score_eligible_requires_scoreable_direction(self):
        with TemporaryDirectory() as tmp:
            ds, mf, desc, curation = self._setup(tmp, {
                "target_indicator_id": "eur:demo", "reviewed_direction": "contextual",
                "score_eligible": "true", "reviewed_at": "2026-07-24",
            })
            with self.assertRaises(SystemExit):
                apply_curation.run(dataset=ds, manifest=mf, descriptions=desc, curation_path=curation)


if __name__ == "__main__":
    unittest.main()
