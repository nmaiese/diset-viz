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


class TheTickLandsOnMasterFromAnyBranch(unittest.TestCase):
    """Il difetto per cui i tick non sono mai arrivati su master, e come e' chiuso.

    La sessione della Routine sta **sempre** su un branch `claude/*`, mai su
    master. La vecchia forma rifiutava se HEAD non era master, quindi da li' non
    pubblicava mai niente: la guardia proteggeva da `git push origin HEAD:master`
    (che avrebbe spinto il branch intero) ma di fatto bloccava sempre. Ora il push
    non passa da HEAD: si costruisce un commit **sopra origin/master** con dentro
    **solo** la riga del tick, e lo si spinge da qualunque branch. L'invariante
    'non spinge altro che se stesso' vale per costruzione, non per guardia.
    """

    ENTRY = {"run_id": "dispatch-20260727T090000Z-aaaa", "at": "2026-07-27T09:00:00+00:00"}
    REL = "data/pipeline/runs/dispatch-20260727T090000Z-aaaa.json"

    def runner(self, push_fails_first=0):
        calls = []
        state = {"pushes": 0}

        def fake(argv, cwd=None, env=None):
            calls.append({"argv": argv, "env": env})
            if argv[:2] == ["git", "write-tree"]:
                return 0, "t" * 40 + "\n"
            if argv[:2] == ["git", "commit-tree"]:
                return 0, "c" * 40 + "\n"
            if argv[:3] == ["git", "push", "origin"]:
                state["pushes"] += 1
                if state["pushes"] <= push_fails_first:
                    return 1, "non-fast-forward"
                return 0, ""
            return 0, ""

        fake.calls = calls
        return fake

    def _argvs(self, runner):
        return [c["argv"] for c in runner.calls]

    def test_it_pushes_a_commit_built_on_master_never_head(self):
        runner = self.runner()
        ok = pipeline_dispatch.commit_tick(self.ENTRY, runner=runner, log=lambda *_: None)
        self.assertTrue(ok)
        argvs = self._argvs(runner)
        self.assertIn(["git", "read-tree", "origin/master"], argvs)
        self.assertIn(["git", "add", "--", self.REL], argvs)
        self.assertIn(
            ["git", "commit-tree", "t" * 40, "-p", "origin/master", "-m",
             "Diario: giro a vuoto del dispatch, 2026-07-27"], argvs)
        self.assertIn(["git", "push", "origin", f"{'c' * 40}:master"], argvs)
        self.assertNotIn(["git", "push", "origin", "HEAD:master"], argvs)

    def test_it_does_not_gate_on_the_working_branch(self):
        """Non chiede nemmeno su che branch e': il branch di lavoro non entra
        nella decisione, quindi funziona identico da master e da un `claude/*`."""
        runner = self.runner()
        ok = pipeline_dispatch.commit_tick(self.ENTRY, runner=runner, log=lambda *_: None)
        self.assertTrue(ok)
        self.assertFalse(any(a[:2] == ["git", "rev-parse"] for a in self._argvs(runner)))

    def test_only_the_named_file_enters_the_commit(self):
        """L'indice parte da origin/master e ci si aggiunge SOLO la riga, contro un
        indice temporaneo: gli altri file non committati dell'albero non entrano
        perche' non vengono mai aggiunti."""
        runner = self.runner()
        pipeline_dispatch.commit_tick(self.ENTRY, runner=runner, log=lambda *_: None)
        adds = [c for c in runner.calls if c["argv"][:2] == ["git", "add"]]
        self.assertEqual([c["argv"] for c in adds], [["git", "add", "--", self.REL]])
        self.assertIn("GIT_INDEX_FILE", adds[0]["env"])

    def test_it_retries_the_push_on_a_lost_race(self):
        """Chi perde la corsa si ricostruisce sopra un origin/master ri-fetchato e
        ritenta: ogni tentativo e' un nuovo commit-tree, non un rebase."""
        runner = self.runner(push_fails_first=1)
        ok = pipeline_dispatch.commit_tick(self.ENTRY, runner=runner, log=lambda *_: None)
        self.assertTrue(ok)
        argvs = self._argvs(runner)
        self.assertEqual(sum(a[:3] == ["git", "push", "origin"] for a in argvs), 2)
        self.assertEqual(argvs.count(["git", "fetch", "origin", "master"]), 2)


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


class TheProofsLandOnMasterFromAnyBranch(unittest.TestCase):
    """Le prove di pubblicazione arrivano su master con lo stesso meccanismo del
    tick: un commit costruito sopra origin/master con dentro solo le prove, spinto
    da qualunque branch. Prima la guardia 'solo su master' non le faceva mai
    arrivare, perche' la sessione non e' mai su master."""

    REL = "data/pipeline/pubblicazioni/ter-651__regione__abc.json"

    def runner(self, push_fails_first=0):
        calls = []
        state = {"pushes": 0}

        def fake(argv, cwd=None, env=None):
            calls.append({"argv": argv, "env": env})
            if argv[:2] == ["git", "write-tree"]:
                return 0, "t" * 40 + "\n"
            if argv[:2] == ["git", "commit-tree"]:
                return 0, "c" * 40 + "\n"
            if argv[:3] == ["git", "push", "origin"]:
                state["pushes"] += 1
                if state["pushes"] <= push_fails_first:
                    return 1, "non-fast-forward"
                return 0, ""
            return 0, ""

        fake.calls = calls
        return fake

    def _argvs(self, runner):
        return [c["argv"] for c in runner.calls]

    def test_it_pushes_a_commit_built_on_master_never_head(self):
        runner = self.runner()
        ok = pipeline_dispatch._commit_proofs([self.REL], runner=runner, log=lambda *_: None)
        self.assertTrue(ok)
        argvs = self._argvs(runner)
        self.assertIn(["git", "read-tree", "origin/master"], argvs)
        self.assertIn(["git", "add", "--", self.REL], argvs)
        self.assertIn(["git", "push", "origin", f"{'c' * 40}:master"], argvs)
        self.assertNotIn(["git", "push", "origin", "HEAD:master"], argvs)

    def test_it_does_not_gate_on_the_working_branch(self):
        runner = self.runner()
        ok = pipeline_dispatch._commit_proofs([self.REL], runner=runner, log=lambda *_: None)
        self.assertTrue(ok)
        self.assertFalse(any(a[:2] == ["git", "rev-parse"] for a in self._argvs(runner)))

    def test_more_than_one_proof_rides_the_same_commit(self):
        other = "data/pipeline/pubblicazioni/ter-14__regione__def.json"
        runner = self.runner()
        ok = pipeline_dispatch._commit_proofs([self.REL, other], runner=runner, log=lambda *_: None)
        self.assertTrue(ok)
        adds = [c["argv"] for c in runner.calls if c["argv"][:2] == ["git", "add"]]
        # entrambe le prove nello stesso add, e un solo push
        self.assertEqual(adds, [["git", "add", "--", other, self.REL]])
        self.assertEqual(sum(a[:3] == ["git", "push", "origin"] for a in self._argvs(runner)), 1)

    def test_it_retries_the_push_on_a_lost_race(self):
        runner = self.runner(push_fails_first=1)
        ok = pipeline_dispatch._commit_proofs([self.REL], runner=runner, log=lambda *_: None)
        self.assertTrue(ok)
        argvs = self._argvs(runner)
        self.assertEqual(sum(a[:3] == ["git", "push", "origin"] for a in argvs), 2)
        self.assertEqual(argvs.count(["git", "fetch", "origin", "master"]), 2)


if __name__ == "__main__":
    unittest.main()
