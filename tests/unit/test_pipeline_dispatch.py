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



class NothingToDoIsNotAFailure(unittest.TestCase):
    """Tre uscite, non due, e la terza esiste per non far suonare l'allarme ogni
    ora. Una catena a code vuote e' ferma per il motivo giusto: se il codice di
    uscita non distinguesse quel caso da un guasto, la Routine registrerebbe un
    errore a ogni ora di riposo, e un allarme che suona sempre non e' un
    allarme."""

    def run_with(self, plan_or_error):
        """Lancia la CLI con una decisione finta, e ritorna il codice di uscita."""
        import contextlib
        import io

        real = pipeline_dispatch.decide
        if isinstance(plan_or_error, Exception):
            def fake(**kwargs):
                raise plan_or_error
        else:
            def fake(**kwargs):
                return plan_or_error
        pipeline_dispatch.decide = fake
        try:
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                return pipeline_dispatch.cli(["--json"])
        finally:
            pipeline_dispatch.decide = real

    def plan(self, stage):
        return {"stage": stage, "agent": "source-scout" if stage else None,
                "reason": "motivo", "waiting": 1 if stage else 0,
                "queues": {}, "open_prs": [], "pr_state": "letto",
                "run_id": "scout-x-0000"}

    def test_a_stage_to_launch_exits_zero(self):
        self.assertEqual(self.run_with(self.plan("scout")), 0)

    def test_an_empty_chain_exits_one(self):
        self.assertEqual(self.run_with(self.plan(None)), 1)

    def test_a_broken_dispatcher_exits_two(self):
        self.assertEqual(self.run_with(RuntimeError("il catalogo non si legge")), 2)

    def test_a_bad_flag_stays_a_usage_error(self):
        """`SystemExit` passa attraverso: un flag sbagliato deve restare un
        errore d'uso, non diventare un 2 che sembra un guasto del catalogo."""
        import contextlib
        import io

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                pipeline_dispatch.cli(["--flag-che-non-esiste"])


class TheTickNeverPushesAnythingButItself(unittest.TestCase):
    """Il difetto piu' pericoloso dell'intera modifica, trovato rileggendola.

    `git push origin HEAD:master` spinge su master **tutto** cio' che sta sotto
    HEAD. Lanciato da un branch di lavoro non pubblicherebbe una riga di
    diario: pubblicherebbe quel branch intero, senza cancello, senza CI e senza
    pull request. Il dispatcher gira su un checkout fresco di master e li' non
    succede, ma "di solito non succede" e' la premessa sbagliata per un comando
    che non si puo' disfare.
    """

    ENTRY = {"run_id": "dispatch-20260727T090000Z-aaaa", "at": "2026-07-27T09:00:00+00:00"}
    REL = "data/pipeline/runs/dispatch-20260727T090000Z-aaaa.json"

    def runner(self, branch="master", dirty=()):
        calls = []

        def fake(argv, cwd=None):
            calls.append(argv)
            if argv[:2] == ["git", "rev-parse"]:
                return 0, branch + "\n"
            if argv[:2] == ["git", "status"]:
                return 0, "".join(f"?? {path}\n" for path in dirty)
            return 0, ""

        fake.calls = calls
        return fake

    def test_it_refuses_when_head_is_not_master(self):
        runner = self.runner(branch="claude/una-modifica")
        ok = pipeline_dispatch.commit_tick(
            self.ENTRY, runner=runner, log=lambda *_: None)
        self.assertFalse(ok)
        self.assertNotIn(["git", "push", "origin", "HEAD:master"], runner.calls)

    def test_it_refuses_when_the_tree_carries_anything_else(self):
        """Su master ma con altro non committato, il push porterebbe via anche
        quello alla prima passata di `git add` di qualcun altro."""
        runner = self.runner(dirty=[self.REL, "app/views.py"])
        ok = pipeline_dispatch.commit_tick(
            self.ENTRY, runner=runner, log=lambda *_: None)
        self.assertFalse(ok)
        self.assertNotIn(["git", "push", "origin", "HEAD:master"], runner.calls)

    def test_it_pushes_when_master_carries_only_the_tick(self):
        runner = self.runner(dirty=[self.REL])
        ok = pipeline_dispatch.commit_tick(
            self.ENTRY, runner=runner, log=lambda *_: None)
        self.assertTrue(ok)
        self.assertIn(["git", "push", "origin", "HEAD:master"], runner.calls)
        self.assertIn(["git", "add", self.REL], runner.calls)


class AnOpenPullRequestIsRecognisedByWhatItTouches(unittest.TestCase):
    """Il nome del branch e' una convenzione che nessuna guardia impone, quindi
    da solo non basta a riconoscere una run in corso. Una run su un branch
    chiamato altrimenti sarebbe invisibile, e il dispatcher lancerebbe un
    secondo stadio addosso al primo: il guasto tornerebbe in silenzio."""

    def runner(self, prs, files_by_pr):
        import json as _json

        def fake(argv, cwd=None):
            if argv[:3] == ["git", "remote", "get-url"]:
                return 0, "https://github.com/nmaiese/diset-viz.git\n"
            path = argv[-1]
            if "/pulls?" in path:
                return 0, _json.dumps(prs)
            for number, files in files_by_pr.items():
                if f"/pulls/{number}/files" in path:
                    return 0, _json.dumps([{"filename": f} for f in files])
            return 1, ""

        return fake

    def pr(self, number, branch):
        return {"number": number, "head": {"ref": branch}, "title": "t"}

    def test_the_convention_still_works(self):
        runner = self.runner([self.pr(1, "automation/writer-2026-07-27")], {})
        state, prs = pipeline_dispatch.open_chain_prs(runner=runner)
        self.assertEqual(state, "letto")
        self.assertEqual([p["number"] for p in prs], [1])

    def test_a_chain_run_on_an_odd_branch_is_still_caught(self):
        runner = self.runner(
            [self.pr(2, "claude/lavoro-in-corso")],
            {2: ["content/indicators/ter__920.json", "data/pipeline/runs/x.json"]},
        )
        _, prs = pipeline_dispatch.open_chain_prs(runner=runner)
        self.assertEqual([p["number"] for p in prs], [2])
        self.assertIn("perimetro", prs[0]["perche"])

    def test_a_humans_pull_request_does_not_block_the_chain(self):
        """L'altra meta': se qualunque pull request aperta bloccasse il
        dispatcher, una PR umana lasciata li' fermerebbe la catena per sempre."""
        runner = self.runner(
            [self.pr(3, "claude/refactor")],
            {3: ["app/views.py", "content/indicators/ter__920.json"]},
        )
        _, prs = pipeline_dispatch.open_chain_prs(runner=runner)
        self.assertEqual(prs, [])


class ThePublishStepObservesTheSite(unittest.TestCase):
    """Il passo del sito: verifica gli indicatori fusi e scrive le prove, senza
    lanciare un agente. Un sito che non conferma non scrive niente, e le prove si
    committano solo con le stesse guardie del tick."""

    def _fusa_indicator(self):
        from scripts import verify_publication
        queue = verify_publication.publication_queue()
        if not queue:
            self.skipTest("nessun indicatore in stato fusa da verificare")
        return queue[0]["id"]

    def test_a_confirming_site_writes_a_proof(self):
        import tempfile
        from scripts import indicator_store, verify_publication
        ind = self._fusa_indicator()
        entry = indicator_store.read(ind)
        sig = verify_publication.page_signature(entry)

        def good_fetcher(url):
            return f"<html><body><p>{sig['snippet']} ...</p><p>anno {sig['vintage']}</p></body></html>"

        root = tempfile.mkdtemp()
        summary = pipeline_dispatch.publish_step(
            fetcher=good_fetcher, proofs_root=root, do_commit=False)
        self.assertGreaterEqual(summary["prove_scritte"], 1)
        self.assertTrue(any(c["ok"] for c in summary["checked"]))

    def test_an_unreachable_site_writes_nothing(self):
        import tempfile

        def dead_fetcher(url):
            raise OSError("giu'")

        root = tempfile.mkdtemp()
        summary = pipeline_dispatch.publish_step(
            fetcher=dead_fetcher, proofs_root=root, do_commit=False)
        self.assertEqual(summary["prove_scritte"], 0)
        # ne' successo ne' fallimento: ogni controllo e' irraggiungibile (ok None)
        self.assertTrue(all(c["ok"] is None for c in summary["checked"]))

    def test_a_wrong_version_writes_nothing(self):
        import tempfile

        def stale_fetcher(url):
            return "<html><body>una pagina che non porta ne' lead ne' anno</body></html>"

        root = tempfile.mkdtemp()
        summary = pipeline_dispatch.publish_step(
            fetcher=stale_fetcher, proofs_root=root, do_commit=False)
        self.assertEqual(summary["prove_scritte"], 0)


class TheProofsNeverPushAnythingButThemselves(unittest.TestCase):
    """Il push diretto delle prove ha le stesse guardie del tick: un file per
    record e nome che nessun altro sceglie, ma solo su master e solo se l'albero
    non porta altro."""

    REL = "data/pipeline/pubblicazioni/ter-651__regione__abc.json"

    def runner(self, branch="master", dirty=()):
        calls = []

        def fake(argv, cwd=None):
            calls.append(argv)
            if argv[:2] == ["git", "rev-parse"]:
                return 0, branch + "\n"
            if argv[:2] == ["git", "status"]:
                return 0, "".join(f"?? {path}\n" for path in dirty)
            return 0, ""

        fake.calls = calls
        return fake

    def test_it_refuses_when_head_is_not_master(self):
        runner = self.runner(branch="claude/una-modifica", dirty=[self.REL])
        ok = pipeline_dispatch._commit_proofs([self.REL], runner=runner, log=lambda *_: None)
        self.assertFalse(ok)
        self.assertNotIn(["git", "push", "origin", "HEAD:master"], runner.calls)

    def test_it_refuses_when_the_tree_carries_anything_else(self):
        runner = self.runner(dirty=[self.REL, "app/views.py"])
        ok = pipeline_dispatch._commit_proofs([self.REL], runner=runner, log=lambda *_: None)
        self.assertFalse(ok)
        self.assertNotIn(["git", "push", "origin", "HEAD:master"], runner.calls)

    def test_it_pushes_when_master_carries_only_the_proofs(self):
        runner = self.runner(dirty=[self.REL])
        ok = pipeline_dispatch._commit_proofs([self.REL], runner=runner, log=lambda *_: None)
        self.assertTrue(ok)
        self.assertIn(["git", "push", "origin", "HEAD:master"], runner.calls)

    def test_it_retries_the_push_after_a_rebase(self):
        """Il difetto che Codex ha visto: il commit deve stare fuori dal ciclo.
        Dopo un rebase riuscito la prova e' gia' committata, quindi un secondo
        `git commit` non stagerebbe niente ed uscirebbe non-zero (qui simulato),
        e la vecchia forma tornava senza mai ripushare. Ora committa una volta e
        ritenta solo il push."""
        calls = []
        state = {"pushes": 0, "commits": 0}

        def fake(argv, cwd=None):
            calls.append(argv)
            if argv[:2] == ["git", "rev-parse"]:
                return 0, "master\n"
            if argv[:2] == ["git", "status"]:
                return 0, f"?? {self.REL}\n"
            if argv[:2] == ["git", "commit"]:
                state["commits"] += 1
                # il secondo commit non ha niente da committare, come git vero
                return (0, "") if state["commits"] == 1 else (1, "nothing to commit")
            if argv[:3] == ["git", "push", "origin"]:
                state["pushes"] += 1
                return (0, "") if state["pushes"] >= 2 else (1, "non-fast-forward")
            return 0, ""

        ok = pipeline_dispatch._commit_proofs([self.REL], runner=fake, log=lambda *_: None)
        self.assertTrue(ok)
        self.assertEqual(state["commits"], 1)  # committato una volta sola
        self.assertEqual(state["pushes"], 2)   # ripushato dopo il rebase
        self.assertIn(["git", "rebase", "origin/master"], calls)


if __name__ == "__main__":
    unittest.main()
