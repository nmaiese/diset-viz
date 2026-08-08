"""Il vocabolario della pratica editoriale come regole verificabili.

Puro, senza disco e senza app: prova le transizioni ammesse, gli stadi
obbligatori, i tetti di retry e l'ordine di priorità di docs/EDITORIAL_PRACTICE.md.
"""

import unittest

from scripts import practice_model as m


class Vocabulary(unittest.TestCase):
    def test_states_and_outcomes_are_finite_and_disjoint(self):
        self.assertEqual(len(set(m.STATES)), len(m.STATES))
        self.assertEqual(len(set(m.TERMINAL_OUTCOMES)), len(m.TERMINAL_OUTCOMES))
        self.assertIn("pubblicata", m.TERMINAL_OUTCOMES)
        self.assertNotIn("fusa", m.STATES)  # merge = pubblicazione, niente stato intermedio

    def test_every_type_has_an_entry_stage_and_required_stages(self):
        for ptype in m.PRACTICE_TYPES:
            self.assertIn(ptype, m.ENTRY_STAGE)
            self.assertIn(ptype, m.REQUIRED_STAGES)


class Transitions(unittest.TestCase):
    def test_merge_publishes(self):
        # Merge = pubblicazione: pronta-al-merge va diritta a pubblicata, senza
        # uno stato `fusa` intermedio né una verifica-sito.
        self.assertTrue(m.can_transition("pronta-al-merge", "pubblicata"))
        self.assertFalse(m.can_transition("pronta-al-merge", "fusa"))

    def test_no_implicit_jump_to_published(self):
        # Non si pubblica saltando il cancello (§4): la coppia non esiste.
        self.assertFalse(m.can_transition("in-lavorazione", "pubblicata"))
        self.assertFalse(m.can_transition("proposta", "pubblicata"))

    def test_closed_is_terminal(self):
        self.assertTrue(m.is_terminal_state("chiusa"))
        self.assertFalse(any(frm == "chiusa" for frm, _ in m.TRANSITIONS))

    def test_all_transitions_are_between_known_states(self):
        for frm, to in m.TRANSITIONS:
            self.assertIn(frm, m.STATES)
            self.assertIn(to, m.STATES)


class RequiredStages(unittest.TestCase):
    def test_next_required_walks_chain_order(self):
        self.assertEqual(m.next_required_stage("nuovo", []), "curator")
        self.assertEqual(m.next_required_stage("nuovo", ["curator", "writer"]), "reviewer")
        self.assertEqual(m.next_required_stage("nuovo",
                         ["curator", "writer", "reviewer", "verificatore"]), None)

    def test_a_type_with_one_stage_completes(self):
        self.assertEqual(m.next_required_stage("revisione", []), "reviewer")
        self.assertIsNone(m.next_required_stage("revisione", ["reviewer"]))


class ErrorTaxonomy(unittest.TestCase):
    def test_transient_retries_up_to_ceiling(self):
        self.assertFalse(m.retry_exhausted("transitorio", 2))
        self.assertTrue(m.retry_exhausted("transitorio", 3))

    def test_reentry_classes_never_exhaust(self):
        self.assertIsNone(m.retry_ceiling("editoriale"))
        self.assertFalse(m.retry_exhausted("cambiamento-in-corsa", 99))

    def test_terminal_and_external_change_do_not_auto_retry(self):
        self.assertEqual(m.retry_ceiling("terminale"), 0)
        self.assertEqual(m.retry_ceiling("ripetibile-dopo-cambio-esterno"), 0)
        self.assertTrue(m.retry_exhausted("terminale", 0))

    def test_unknown_class_is_treated_as_terminal(self):
        self.assertEqual(m.retry_ceiling("boh"), 0)


class Priority(unittest.TestCase):
    def _p(self, **flags_and_fields):
        base = {"flags": {}, "state": "in-lavorazione", "type": "nuovo",
                "completed_stages": [], "score_eligible": False,
                "entered_at": "2026-01-01", "attempts": 0}
        base.update(flags_and_fields)
        return m.priority_score(base, "2026-01-01")

    def test_public_error_outranks_a_fresh_practice(self):
        refuted = self._p(flags={"open_smentita": True}, state="pubblicata")
        fresh = self._p(completed_stages=[])
        self.assertGreater(refuted, fresh)

    def test_proximity_to_publication_raises_priority(self):
        near = self._p(completed_stages=["curator", "writer", "reviewer"])
        far = self._p(completed_stages=["curator"])
        self.assertGreater(near, far)

    def test_failed_attempts_lower_priority(self):
        many = self._p(attempts=3)
        none = self._p(attempts=0)
        self.assertLess(many, none)

    def test_stale_data_on_scored_indicator_weighs_more(self):
        scored = self._p(flags={"stale_vintage": True}, score_eligible=True)
        unscored = self._p(flags={"stale_vintage": True}, score_eligible=False)
        self.assertGreater(scored, unscored)

    def test_older_practice_outranks_a_younger_twin(self):
        old = m.priority_score(
            {"flags": {}, "state": "in-lavorazione", "type": "nuovo",
             "completed_stages": [], "score_eligible": False,
             "entered_at": "2026-01-01", "attempts": 0}, "2026-03-01")
        young = m.priority_score(
            {"flags": {}, "state": "in-lavorazione", "type": "nuovo",
             "completed_stages": [], "score_eligible": False,
             "entered_at": "2026-02-28", "attempts": 0}, "2026-03-01")
        self.assertGreater(old, young)


class PracticeId(unittest.TestCase):
    def test_round_trip_with_a_hyphenated_indicator(self):
        pid = m.practice_id("bes:09PAE009-N25", "nuovo", 1)
        self.assertEqual(pid, "bes:09PAE009-N25#nuovo-1")
        self.assertEqual(m.parse_practice_id(pid), ("bes:09PAE009-N25", "nuovo", 1))

    def test_unknown_type_is_refused(self):
        with self.assertRaises(ValueError):
            m.practice_id("dem:X", "inventato", 1)


if __name__ == "__main__":
    unittest.main()
