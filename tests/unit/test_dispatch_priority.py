"""Fase F opt-in: la preemption per priorita' nel dispatcher.

Senza `priorities` il comportamento e' l'ordine di catena, identico a prima.
Con `priorities`, una pratica urgente (sopra soglia) scavalca l'ordine di catena,
ma solo se il suo stadio ha davvero lavoro in coda, e solo sopra la soglia: sotto,
la scoperta non viene affamata.
"""

import unittest

from scripts import pipeline_dispatch as pd

# hunter (a monte) ha lavoro, reviewer (a valle) ha una pratica urgente
QUEUES = {"scout": 0, "hunter": 3, "promoter": 0, "curator": 0,
          "writer": 0, "reviewer": 1, "verificatore": 0}


class PriorityPreemption(unittest.TestCase):
    def test_without_priorities_it_is_chain_order(self):
        plan = pd.decide(queues=QUEUES)
        self.assertEqual(plan["stage"], "hunter")

    def test_urgent_practice_preempts_chain_order(self):
        plan = pd.decide(queues=QUEUES, priorities={"reviewer": 120.0, "hunter": 5.0})
        self.assertEqual(plan["stage"], "reviewer")
        self.assertIn("urgente", plan["reason"])

    def test_below_threshold_keeps_chain_order(self):
        plan = pd.decide(queues=QUEUES, priorities={"reviewer": 45.0, "hunter": 5.0})
        self.assertEqual(plan["stage"], "hunter")

    def test_urgent_stage_without_queue_work_does_not_preempt(self):
        # curator e' urgente ma non ha coda: niente lancio fantasma
        plan = pd.decide(queues=QUEUES, priorities={"curator": 200.0})
        self.assertEqual(plan["stage"], "hunter")

    def test_highest_urgent_wins_across_stages(self):
        queues = dict(QUEUES, curator=1)
        plan = pd.decide(queues=queues, priorities={"curator": 105.0, "reviewer": 130.0})
        self.assertEqual(plan["stage"], "reviewer")

    def test_open_pr_still_blocks_everything(self):
        plan = pd.decide(queues=QUEUES, pr_state="letto",
                         open_prs=[{"number": 9, "branch": "b", "title": "", "perche": ""}],
                         priorities={"reviewer": 999.0})
        self.assertIsNone(plan["stage"])


if __name__ == "__main__":
    unittest.main()
