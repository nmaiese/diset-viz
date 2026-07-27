"""Il dispatcher: un tick, uno stadio.

Il guasto che chiude e' doppio, e le due meta' si somigliano poco. La prima e'
che le dipendenze della catena sono di dato mentre la schedulazione era di
calendario: il curatore girava il giovedi' comunque, a vuoto se a monte non era
successo niente, con sei giorni di ritardo se era successo il venerdi' prima.
La seconda e' che due stadi potevano girare insieme, e nessuno aspettava
nessuno.

Nessun test qui tocca git, GitHub o il catalogo: `decide` prende lo stato come
argomento proprio perche' la decisione sia provabile senza il mondo intorno.
"""

import unittest

from scripts import pipeline_dispatch


VUOTE = {stage: 0 for stage in pipeline_dispatch.STAGE_ORDER}


def queues(**kwargs):
    state = dict(VUOTE)
    state.update(kwargs)
    return state


class OneTickOneStage(unittest.TestCase):
    def test_it_picks_the_first_stage_with_work_in_chain_order(self):
        """L'ordine e' la catena, e non e' una preferenza estetica: quello che
        produce uno stadio a monte diventa la coda di quello a valle, quindi
        servire prima il monte porta piu' lavoro alla catena intera."""
        plan = pipeline_dispatch.decide(queues(curator=2, reviewer=300))
        self.assertEqual(plan["stage"], "curator")
        self.assertEqual(plan["agent"], "indicator-curator")

    def test_it_never_names_more_than_one_stage(self):
        plan = pipeline_dispatch.decide(queues(scout=1, hunter=1, writer=1, reviewer=1))
        self.assertEqual(plan["stage"], "scout")

    def test_an_empty_chain_launches_nothing_and_says_so(self):
        plan = pipeline_dispatch.decide(queues())
        self.assertIsNone(plan["stage"])
        self.assertIn("vuote", plan["reason"])

    def test_a_queue_nobody_could_count_is_treated_as_work(self):
        """Chi chiama non sa distinguere "niente da fare" da "nessuno ha
        contato". Mandarci un agente costa una run, saltarlo costa un buco
        silenzioso, ed e' la stessa scelta che fa `pipeline_status`."""
        plan = pipeline_dispatch.decide(queues(writer=None))
        self.assertEqual(plan["stage"], "writer")
        self.assertIn("non calcolabile", plan["reason"])

    def test_the_plan_carries_a_run_id_the_stage_can_use(self):
        plan = pipeline_dispatch.decide(queues(reviewer=5))
        self.assertTrue(plan["run_id"].startswith("reviewer-"))


class AnOpenPullRequestIsARunStillInFlight(unittest.TestCase):
    """Lanciare un secondo stadio mentre il primo aspetta i check vuol dire due
    run che partono da due basi diverse, e la seconda a fondersi trova un master
    che non aveva davanti."""

    PR = [{"number": 54, "branch": "automation/writer-2026-07-27", "title": "x"}]

    def test_it_refuses_while_a_chain_pull_request_is_open(self):
        plan = pipeline_dispatch.decide(
            queues(reviewer=300), open_prs=self.PR, pr_state="letto")
        self.assertIsNone(plan["stage"])
        self.assertIn("#54", plan["reason"])

    def test_it_proceeds_when_the_check_ran_and_found_nothing_open(self):
        plan = pipeline_dispatch.decide(
            queues(reviewer=300), open_prs=[], pr_state="letto")
        self.assertEqual(plan["stage"], "reviewer")

    def test_an_unreadable_pr_list_does_not_pass_for_an_empty_one(self):
        """`ignoto` e lista vuota portano a decisioni opposte, quindi il codice
        deve tenerli distinti. Qui il dispatcher lancia lo stesso, ma lo stato
        resta scritto nel piano e la CLI lo dice a voce alta: un controllo che
        passa perche' non ha potuto girare va almeno dichiarato."""
        plan = pipeline_dispatch.decide(
            queues(reviewer=300), open_prs=[], pr_state="ignoto")
        self.assertEqual(plan["stage"], "reviewer")
        self.assertEqual(plan["pr_state"], "ignoto")


class TheStageListIsNotCopied(unittest.TestCase):
    def test_it_reads_the_order_and_the_agents_from_pipeline_status(self):
        """Due elenchi di stadi in due file sono due elenchi che divergono, e
        questo repo ha gia' perso settimane per una regola ricopiata invece che
        indicata."""
        from scripts import pipeline_status

        self.assertIs(pipeline_dispatch.STAGE_ORDER, pipeline_status.STAGE_ORDER)
        self.assertIs(pipeline_dispatch.AGENT_OF, pipeline_status.AGENT_OF)

    def test_every_stage_it_can_name_has_an_agent(self):
        for stage in pipeline_dispatch.STAGE_ORDER:
            self.assertIn(stage, pipeline_dispatch.AGENT_OF, stage)


class TheTickIsRecordedOnlyWhenItSaysSomething(unittest.TestCase):
    """Un battito orario committato a ogni giro sarebbe ottomila file l'anno
    per dire una cosa sola. La riga serve in un caso solo, e va detta una volta
    al giorno: quando il dispatcher gira e **non** lancia niente, perche' quello
    e' l'unico caso in cui nessun altro lascia traccia."""

    def plan(self, stage=None):
        return {"stage": stage, "agent": "x" if stage else None,
                "reason": "motivo", "waiting": 0}

    def entry(self, at, stage="dispatch"):
        return {"stage": stage, "outcome": "nothing", "summary": "x", "at": at}

    def today(self):
        from datetime import datetime, timezone

        return datetime(2026, 7, 27, 14, 0, tzinfo=timezone.utc)

    def test_a_launch_does_not_need_its_own_row(self):
        """La prova che la catena ha girato la lascia lo stadio lanciato."""
        worth, why = pipeline_dispatch.tick_is_worth_recording(
            self.plan("writer"), [], today=self.today())
        self.assertFalse(worth)
        self.assertIn("la scrive quello", why)

    def test_the_first_empty_round_of_the_day_is_recorded(self):
        worth, _ = pipeline_dispatch.tick_is_worth_recording(
            self.plan(), [], today=self.today())
        self.assertTrue(worth)

    def test_the_second_empty_round_of_the_day_is_not(self):
        entries = [self.entry("2026-07-27T09:00:00+00:00")]
        worth, why = pipeline_dispatch.tick_is_worth_recording(
            self.plan(), entries, today=self.today())
        self.assertFalse(worth)
        self.assertIn("2026-07-27", why)

    def test_yesterdays_round_does_not_cover_today(self):
        entries = [self.entry("2026-07-26T09:00:00+00:00")]
        worth, _ = pipeline_dispatch.tick_is_worth_recording(
            self.plan(), entries, today=self.today())
        self.assertTrue(worth)

    def test_another_stages_row_today_is_not_a_dispatch_tick(self):
        """Il silenzio da misurare e' quello del dispatcher. Una run del
        revisore dice che il revisore ha girato, non che il dispatcher lo abbia
        guardato."""
        entries = [self.entry("2026-07-27T09:00:00+00:00", stage="reviewer")]
        worth, _ = pipeline_dispatch.tick_is_worth_recording(
            self.plan(), entries, today=self.today())
        self.assertTrue(worth)


if __name__ == "__main__":
    unittest.main()
