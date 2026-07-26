"""The gate, tested by the failures it has to catch.

A gate that has only ever returned green is not a gate, it is a formality. Every
test here builds the bad input first and asserts the gate refuses it, then
builds the good one and asserts it passes. The asymmetry is deliberate: the
whole point of this file is that an autonomous stage cannot talk its way past a
check, so the check has to be shown saying no.

Pure stdlib and side-effect free. Nothing here reads or writes the committed
queues: every check takes its rows as an argument for exactly this reason.
"""

import unittest

from scripts import pipeline_gate


class BlastRadius(unittest.TestCase):
    """The check that makes the rest safe to automate.

    An agent's prompt can be edited, misread or ignored. The path list lives in
    the repo, so a writer that decides to "just fix" a view module fails here,
    before its reasoning is ever read.
    """

    def test_a_stage_that_edits_application_code_is_refused(self):
        check = pipeline_gate.check_blast_radius(
            "writer",
            ["app/static/data/indicator_texts.json", "app/views.py"],
        )
        self.assertFalse(check.ok)
        self.assertIn("app/views.py", check.detail)

    def test_a_stage_inside_its_perimeter_passes(self):
        check = pipeline_gate.check_blast_radius(
            "writer", ["app/static/data/indicator_texts.json"]
        )
        self.assertTrue(check.ok, check.detail)

    def test_the_perimeters_do_not_overlap_where_it_would_matter(self):
        """The writer and the hunter must not be able to touch each other's work.

        The run journal is the one deliberate exception, and it is shared on
        purpose: every stage records what it did, including the runs that produce
        nothing else, which are exactly the runs that would otherwise vanish.
        Stated as a test because the lists are short enough that widening one by
        hand looks harmless in a diff.
        """
        shared = {pipeline_gate.RUN_JOURNAL}
        writer = set(pipeline_gate.STAGE_PATHS["writer"]) - shared
        hunter = set(pipeline_gate.STAGE_PATHS["hunter"]) - shared
        self.assertEqual(writer & hunter, set())

    def test_every_stage_can_write_the_run_journal(self):
        """A stage that cannot record its run is a stage nobody can observe, and
        the gate would block it for trying."""
        for stage, paths in pipeline_gate.STAGE_PATHS.items():
            self.assertIn(pipeline_gate.RUN_JOURNAL, paths, stage)

    def test_every_stage_declares_a_merge_policy(self):
        self.assertEqual(
            sorted(pipeline_gate.STAGE_PATHS), sorted(pipeline_gate.MERGE_POLICY)
        )
        for stage, policy in pipeline_gate.MERGE_POLICY.items():
            self.assertIn(policy, ("auto", "checks", "manual"), stage)

    def test_admitting_a_source_is_never_automatic(self):
        """Which institution and licence appear on a public page stays a human
        decision. If this ever flips, it should flip in a diff someone read."""
        self.assertEqual(pipeline_gate.MERGE_POLICY["scout"], "manual")


class HunterDecisions(unittest.TestCase):
    def test_a_decision_without_a_written_reason_is_refused(self):
        check = pipeline_gate.check_hunter_decisions(
            [{"candidate_id": "eurostat_regional:x", "triage_status": "approved", "triage_notes": ""}]
        )
        self.assertFalse(check.ok)
        self.assertIn("eurostat_regional:x", check.detail)

    def test_a_motivated_decision_passes(self):
        check = pipeline_gate.check_hunter_decisions(
            [{
                "candidate_id": "eurostat_regional:x",
                "triage_status": "approved",
                "triage_notes": "Regionale, copertura 20 su 20, serie nuova.",
                "definition_match": "new",
                "coverage": "1.0",
                "license": "CC BY 4.0 (Eurostat)",
            }]
        )
        self.assertTrue(check.ok, check.detail)

    def test_an_untouched_candidate_needs_no_reason(self):
        """`new` is the absence of a decision, and `promoted` is written by the
        promotion script, not by a judgement. Neither owes an explanation."""
        check = pipeline_gate.check_hunter_decisions(
            [
                {"candidate_id": "a", "triage_status": "new", "triage_notes": ""},
                {"candidate_id": "b", "triage_status": "promoted", "triage_notes": ""},
            ]
        )
        self.assertTrue(check.ok, check.detail)

    def test_an_approval_below_the_coverage_floor_is_refused(self):
        """The hunter approves on its own now, so the things that make a series
        unusable have to be refusable without reading its reasoning. Twelve
        regions out of twenty cannot carry a claim about Italy."""
        check = pipeline_gate.check_hunter_decisions(
            [{
                "candidate_id": "eurostat_regional:sparse",
                "triage_status": "approved",
                "triage_notes": "sembra interessante",
                "definition_match": "new",
                "coverage": "0.6",
                "license": "CC BY 4.0",
            }]
        )
        self.assertFalse(check.ok)
        self.assertIn("copertura", check.detail)

    def test_an_approval_without_a_licence_is_refused(self):
        check = pipeline_gate.check_hunter_decisions(
            [{
                "candidate_id": "eurostat_regional:x",
                "triage_status": "approved",
                "triage_notes": "regionale, copertura piena",
                "definition_match": "new",
                "coverage": "1.0",
                "license": "",
            }]
        )
        self.assertFalse(check.ok)
        self.assertIn("licenza", check.detail)

    def test_the_floor_only_binds_approvals(self):
        """A rejected candidate is allowed to be as thin as it likes: recording
        why it was refused is exactly what the queue is for."""
        check = pipeline_gate.check_hunter_decisions(
            [{
                "candidate_id": "eurostat_regional:sparse",
                "triage_status": "rejected",
                "triage_notes": "copertura 12 regioni su 20, non regge un confronto nazionale",
                "definition_match": "new",
                "coverage": "0.6",
                "license": "",
            }]
        )
        self.assertTrue(check.ok, check.detail)

    def test_exact_is_never_claimed_automatically(self):
        check = pipeline_gate.check_hunter_decisions(
            [{
                "candidate_id": "eurostat_regional:x",
                "triage_status": "approved",
                "triage_notes": "sembra la stessa serie",
                "definition_match": "exact",
            }]
        )
        self.assertFalse(check.ok)
        self.assertIn("exact", check.detail)


class CurationDecisions(unittest.TestCase):
    def test_score_eligible_on_a_contextual_verso_is_refused(self):
        """The failure this exists for: a dependency ratio has no better, so
        orienting a z-score by it produces a ranking that means nothing."""
        check = pipeline_gate.check_curation_decisions(
            [{
                "target_indicator_id": "dem:OLDAGEDEPR",
                "reviewed_direction": "contextual",
                "score_eligible": "true",
                "reviewed_at": "2026-07-26",
            }]
        )
        self.assertFalse(check.ok)
        self.assertIn("dem:OLDAGEDEPR", check.detail)

    def test_a_contextual_indicator_out_of_the_score_passes(self):
        check = pipeline_gate.check_curation_decisions(
            [{
                "target_indicator_id": "dem:OLDAGEDEPR",
                "reviewed_direction": "contextual",
                "score_eligible": "false",
                "reviewed_at": "2026-07-26",
            }]
        )
        self.assertTrue(check.ok, check.detail)

    def test_a_directional_verso_may_enter_the_score(self):
        check = pipeline_gate.check_curation_decisions(
            [{
                "target_indicator_id": "eur:rd_e_gerdreg",
                "reviewed_direction": "higher_better",
                "score_eligible": "true",
                "reviewed_at": "2026-07-24",
            }]
        )
        self.assertTrue(check.ok, check.detail)

    def test_a_decision_with_no_date_is_refused(self):
        """`reviewed_at` is what the re-entry rule reads to decide whether a
        decision is still current, so an undated one silently freezes."""
        check = pipeline_gate.check_curation_decisions(
            [{
                "target_indicator_id": "eur:rd_e_gerdreg",
                "reviewed_direction": "higher_better",
                "score_eligible": "true",
                "reviewed_at": "",
            }]
        )
        self.assertFalse(check.ok)


class ChecksThatCannotRunAreNotPasses(unittest.TestCase):
    """The weakest thing a gate can do is report green because it looked away.

    `check_writer_vintage` needs the app view model. On a fresh cloud checkout
    that import fails, and returning a pass there would hand `merge: auto` to a
    writer whose prose is pinned to a year the data has not reached. The drift
    guard in the suite only fires when a vintage falls *behind*, so nothing else
    would ever notice.
    """

    def test_an_unverifiable_vintage_blocks_instead_of_passing(self):
        original = pipeline_gate.changed_text_keys
        pipeline_gate.changed_text_keys = lambda base=None, cwd=None: ["eur:fake"]
        try:
            import builtins

            real_import = builtins.__import__

            def refuse_app(name, *args, **kwargs):
                if name.startswith("app"):
                    raise ModuleNotFoundError("no app here")
                return real_import(name, *args, **kwargs)

            builtins.__import__ = refuse_app
            try:
                check = pipeline_gate.check_writer_vintage()
            finally:
                builtins.__import__ = real_import
        finally:
            pipeline_gate.changed_text_keys = original
        self.assertFalse(check.ok, "un controllo che non puo' girare non e' un controllo superato")
        self.assertIn("venv", check.detail)

    def test_nothing_to_verify_is_still_a_pass(self):
        """Precision matters: a stage that touched no article owes no vintage."""
        original = pipeline_gate.changed_text_keys
        pipeline_gate.changed_text_keys = lambda base=None, cwd=None: []
        try:
            check = pipeline_gate.check_writer_vintage()
        finally:
            pipeline_gate.changed_text_keys = original
        self.assertTrue(check.ok, check.detail)


class Verdict(unittest.TestCase):
    def test_a_red_check_leaves_no_merge_mode(self):
        """There is nothing to negotiate between "the checks failed" and "but
        only a little", so a blocked verdict does not carry the stage's policy."""
        verdict = pipeline_gate.build_verdict(
            "writer", ["app/views.py"], [pipeline_gate.Check("finto", False, "rosso")]
        )
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["merge"], "blocked")

    def test_a_green_writer_may_merge_on_its_own(self):
        verdict = pipeline_gate.build_verdict(
            "writer", [pipeline_gate.INDICATOR_TEXTS], [pipeline_gate.Check("finto", True)]
        )
        self.assertTrue(verdict["ok"])
        self.assertEqual(verdict["merge"], "auto")

    def test_a_green_curator_waits_for_the_remote_checks(self):
        verdict = pipeline_gate.build_verdict(
            "curator", [pipeline_gate.CURATION], [pipeline_gate.Check("finto", True)]
        )
        self.assertEqual(verdict["merge"], "checks")


if __name__ == "__main__":
    unittest.main()
