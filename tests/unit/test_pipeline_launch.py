"""Il lanciatore per-indicatore: che cosa lancia, per chi, e in che ordine.

Nucleo puro: ogni test costruisce un dossier sintetico (la forma di
`practice_timeline.reconstruct`) e code finte, senza toccare il disco. Coniare i
run_id e' iniettato, cosi' l'uscita e' deterministica."""

import unittest

from scripts import pipeline_launch


def practice(code, *, state="in-lavorazione", flags=None, completed=(),
             required=("curator", "writer", "reviewer", "verificatore"),
             priority=0.0):
    return {
        "id": code,
        "state": state,
        "flags": dict(flags or {}),
        "completed_stages": list(completed),
        "required_stages": tuple(required),
        "priority": priority,
    }


def _mint(role):
    # Deterministico: nessun timestamp, cosi' il test confronta stringhe fisse.
    return f"{role}-RUNID"


class PlanLaunches(unittest.TestCase):
    def test_a_writer_ready_indicator_is_one_producer_launch(self):
        dossier = {"ter-5": practice("ter-5", completed=["curator"], priority=7.0)}
        plan = pipeline_launch.plan_launches(dossier, {}, mint=_mint)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["role"], "producer")
        self.assertEqual(plan[0]["agent"], "producer")
        self.assertEqual(plan[0]["indicator"], "ter-5")
        self.assertEqual(plan[0]["scope"], "indicatore")
        self.assertEqual(plan[0]["run_id"], "producer-RUNID")

    def test_a_signed_unverified_indicator_goes_to_the_verificatore(self):
        dossier = {"ter-9": practice("ter-9",
                                     completed=["curator", "writer", "reviewer"],
                                     priority=3.0)}
        plan = pipeline_launch.plan_launches(dossier, {}, mint=_mint)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["role"], "verificatore")
        self.assertEqual(plan[0]["agent"], "indicator-verifier")
        self.assertEqual(plan[0]["indicator"], "ter-9")

    def test_the_source_queue_lights_up_the_admissions_batch(self):
        # Le proposte di fonti non sono indicatori nel dossier: si leggono dalle code.
        plan = pipeline_launch.plan_launches({}, {"scout": 50, "hunter": 0,
                                                  "promoter": 0}, mint=_mint)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["role"], "admissions")
        self.assertEqual(plan[0]["agent"], "admissions")
        self.assertIsNone(plan[0]["indicator"])
        self.assertEqual(plan[0]["scope"], "batch")
        self.assertIn("50", plan[0]["reason"])

    def test_an_uncountable_upstream_queue_still_launches_admissions(self):
        # None conta come lavoro, come ovunque nella catena: meglio andarci a vedere.
        plan = pipeline_launch.plan_launches({}, {"scout": None, "hunter": 0,
                                                  "promoter": 0}, mint=_mint)
        self.assertEqual([item["role"] for item in plan], ["admissions"])

    def test_a_public_smentita_preempts_everything(self):
        dossier = {
            "ter-1": practice("ter-1", state="invalidata",
                              flags={"open_smentita": True},
                              completed=["curator", "writer", "reviewer", "verificatore"],
                              required=("reviewer", "verificatore"), priority=100.0),
            "ter-2": practice("ter-2", completed=["curator"], priority=5.0),
        }
        plan = pipeline_launch.plan_launches(dossier, {"scout": 50, "hunter": 0,
                                                       "promoter": 0}, mint=_mint)
        # smentita (100) prima, poi il produttore fresco (5), poi l'ammissione (0).
        self.assertEqual(plan[0]["indicator"], "ter-1")
        self.assertEqual(plan[0]["role"], "producer")   # il reviewer e' fuso nel produttore
        self.assertEqual(plan[-1]["role"], "admissions")
        self.assertEqual([item["priority"] for item in plan], [100.0, 5.0, 0.0])

    def test_two_producer_indicators_are_two_parallel_launches(self):
        dossier = {
            "ter-3": practice("ter-3", completed=["curator"], priority=4.0),
            "ter-4": practice("ter-4", completed=["curator"], priority=6.0),
        }
        plan = pipeline_launch.plan_launches(dossier, {}, mint=_mint)
        self.assertEqual(len(plan), 2)
        self.assertEqual({item["indicator"] for item in plan}, {"ter-3", "ter-4"})
        # ordinati per priorita' decrescente
        self.assertEqual([item["indicator"] for item in plan], ["ter-4", "ter-3"])

    def test_blocked_and_terminal_practices_are_not_launched(self):
        dossier = {
            "ter-6": practice("ter-6", state="bloccata", flags={"needs_info": True}),
            "ter-7": practice("ter-7", state="chiusa", flags={"rejected": True}),
            "ter-8": practice("ter-8", state="pubblicata",
                              completed=["curator", "writer", "reviewer", "verificatore"]),
        }
        plan = pipeline_launch.plan_launches(dossier, {}, mint=_mint)
        self.assertEqual(plan, [])

    def test_a_proposta_reinforces_admissions_without_a_second_launch(self):
        dossier = {"eur-x": practice("eur-x", state="proposta",
                                     flags={"approved_candidate": True},
                                     completed=[], priority=12.0)}
        plan = pipeline_launch.plan_launches(dossier, {"scout": 0, "hunter": 0,
                                                       "promoter": 0}, mint=_mint)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["role"], "admissions")
        # la priorita' della batch e' quella della proposta piu' urgente
        self.assertEqual(plan[0]["priority"], 12.0)

    def test_nothing_ready_is_an_empty_plan(self):
        plan = pipeline_launch.plan_launches({}, {"scout": 0, "hunter": 0,
                                                  "promoter": 0}, mint=_mint)
        self.assertEqual(plan, [])


if __name__ == "__main__":
    unittest.main()
