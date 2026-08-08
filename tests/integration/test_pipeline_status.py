"""The cross-stage view, tested where it can mislead.

`pipeline_status` is the first command every agent runs, so its failure mode is
not a crash: it is answering "nothing to do" when the truth is "nothing to do
*here*, because the work is stuck upstream". These tests pin the two properties
that keep that answer honest, plus the graceful degradation that lets a cold
cloud checkout run it before it has a venv.
"""

import unittest

from scripts import pipeline_status


class TheChainReadsInOrder(unittest.TestCase):
    def test_the_stages_are_listed_in_the_order_work_flows(self):
        """Printed out of order, an idle downstream queue reads as "finished"
        when the real answer is two stages above it."""
        self.assertEqual(
            pipeline_status.STAGE_ORDER,
            ["scout", "hunter", "promoter", "curator", "writer", "reviewer",
             "verificatore"],
        )

    def test_every_stage_names_the_agent_that_owns_it(self):
        for stage in pipeline_status.STAGE_ORDER:
            self.assertIn(stage, pipeline_status.AGENT_OF, stage)
            self.assertIn(stage, pipeline_status.BUILDERS, stage)

    def test_the_next_stage_is_the_first_one_with_work(self):
        status = pipeline_status.build_status()
        stages = status["stages"]
        expected = next((s["stage"] for s in stages if s["waiting"]), None)
        self.assertEqual(status["next_stage"], expected)

    def test_an_empty_chain_names_no_next_stage(self):
        """Distinguishing "finished" from "blocked" is the whole point, so the
        empty case has to be explicit rather than an arbitrary first row."""
        status = pipeline_status.build_status(["promoter"])
        if status["total_waiting"] == 0:
            self.assertIsNone(status["next_stage"])


class ItRunsOnAColdCheckout(unittest.TestCase):
    def test_every_stage_reports_a_command_and_a_next_action(self):
        for entry in pipeline_status.build_status()["stages"]:
            self.assertTrue(entry["next"], entry["stage"])
            self.assertTrue(entry["command"], entry["stage"])
            self.assertIsInstance(entry["waiting"], int, entry["stage"])

    def test_the_app_backed_stages_degrade_instead_of_crashing(self):
        """The writer's catalogue backlog and the reviewer's reading order need
        the app view model. On a fresh checkout that import fails, and a status
        command that dies there would be useless exactly when it is needed."""
        for builder in (pipeline_status._catalogue_editorial_state, pipeline_status._reading_order):
            state = builder()
            self.assertIn("disponibile", state)
            if not state["disponibile"]:
                self.assertTrue(state.get("motivo"))


class ThePublisherIsGone(unittest.TestCase):
    """Rimossa la verifica-sito (merge = pubblicazione), il `publisher` non esiste
    più come stadio né come coda: la vista degli stadi non lo nomina."""

    def test_the_publisher_is_not_among_the_ordered_stages(self):
        stages = [s["stage"] for s in pipeline_status.build_status()["stages"]]
        self.assertNotIn("publisher", stages)
        self.assertNotIn("publisher", pipeline_status.queue_sizes())
        self.assertNotIn("publisher", pipeline_status.STAGE_ORDER)


if __name__ == "__main__":
    unittest.main()
