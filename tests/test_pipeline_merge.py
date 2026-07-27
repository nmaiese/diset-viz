"""Il passo di merge, e la bugia che sostituisce.

Il contratto diceva a tre stadi di chiudere con `gh pr merge --auto`, convinto
che `--auto` parcheggiasse la PR fino ai check verdi. Su questo repo non lo fa:
`allow_auto_merge` e' falso e `master` non e' protetto, quindi `gh` fonde subito.
Una PR sonda e' stata fusa con il job `python` ancora `IN_PROGRESS`.

Ogni test qui costruisce prima il caso cattivo, perche' e' l'unico che conta: un
passo di merge che fonde quando non deve non lo scopri guardandolo funzionare.
Nessun test parla con la rete o con `gh`: il comando esterno e' iniettato.
"""

import json
from pathlib import Path
import unittest

from scripts import pipeline_merge


def fake_gh(checks=None, merge_ok=True, script=None):
    """Un finto `gh`. `script` e' una lista di risposte successive a `pr checks`,
    cosi' un test puo' descrivere una CI che parte gialla e finisce verde."""
    calls = []
    pending = list(script or [])

    def runner(argv, cwd=None):
        calls.append(argv)
        if argv[:3] == ["gh", "pr", "checks"]:
            rows = pending.pop(0) if pending else checks
            if rows is None:
                return 1, "no checks reported on the 'x' branch"
            return 0, json.dumps([{"name": n, "bucket": b} for n, b in rows.items()])
        if argv[:3] == ["gh", "pr", "merge"]:
            return (0, "merged") if merge_ok else (1, "merge failed")
        return 0, ""

    runner.calls = calls
    return runner


GREEN = {"merge": "checks", "ok": True, "checks": []}
AUTO = {"merge": "auto", "ok": True, "checks": []}
RED = {"merge": "blocked", "ok": False, "checks": [{"check": "perimetro", "ok": False}]}


def merged_prs(runner):
    return [a[3] for a in runner.calls if a[:3] == ["gh", "pr", "merge"]]


class ABlockedGateIsNotAdvice(unittest.TestCase):
    def test_it_refuses_to_merge(self):
        runner = fake_gh(checks={"python": "pass"})
        result = pipeline_merge.decide("writer", 1, verdict=RED, runner=runner, log=lambda *_: None)
        self.assertFalse(result["merged"])
        self.assertEqual(result["outcome"], "blocked")
        self.assertEqual(merged_prs(runner), [], "ha fuso con il cancello rosso")

    def test_it_says_which_check_failed(self):
        result = pipeline_merge.decide("writer", 1, verdict=RED, runner=fake_gh(), log=lambda *_: None)
        self.assertIn("perimetro", result["detail"])


class ChecksHasToActuallyWait(unittest.TestCase):
    """Il difetto vero, quello che il repo aveva davvero: fondere mentre la CI gira."""

    def test_a_pending_check_does_not_merge(self):
        runner = fake_gh(script=[{"python": "pending", "frontend": "pass"}])
        slept = []
        result = pipeline_merge.decide(
            "curator", 7, verdict=GREEN, runner=runner, sleep=slept.append,
            log=lambda *_: None,
        )
        # La sequenza di risposte finisce, quindi il polling scade: l'importante
        # e' che in nessun momento abbia fuso con un check ancora in corso.
        self.assertEqual(merged_prs(runner), [])
        self.assertFalse(result["merged"])

    def test_it_merges_once_the_checks_go_green(self):
        runner = fake_gh(script=[
            {"python": "pending", "frontend": "pending"},
            {"python": "pending", "frontend": "pass"},
            {"python": "pass", "frontend": "pass"},
        ])
        result = pipeline_merge.decide(
            "curator", 7, verdict=GREEN, runner=runner, sleep=lambda _: None,
            log=lambda *_: None,
        )
        self.assertTrue(result["merged"])
        self.assertEqual(merged_prs(runner), ["7"])

    def test_a_failed_check_is_a_refusal_not_a_wait(self):
        runner = fake_gh(checks={"python": "fail", "frontend": "pass"})
        result = pipeline_merge.decide(
            "curator", 7, verdict=GREEN, runner=runner, sleep=lambda _: None,
            log=lambda *_: None,
        )
        self.assertFalse(result["merged"])
        self.assertEqual(result["outcome"], "stopped")
        self.assertIn("python", result["detail"])
        self.assertEqual(merged_prs(runner), [])

    def test_no_checks_at_all_is_a_refusal(self):
        """'checks' senza check non e' una promozione ad 'auto'. Se la CI non
        parte, la politica non e' soddisfacibile e la PR resta aperta."""
        runner = fake_gh(checks=None)
        result = pipeline_merge.decide(
            "hunter", 3, verdict=GREEN, runner=runner, sleep=lambda _: None,
            log=lambda *_: None,
        )
        self.assertFalse(result["merged"])
        self.assertIn("nessun check", result["detail"])
        self.assertEqual(merged_prs(runner), [])

    def test_a_cancelled_check_does_not_count_as_passed(self):
        runner = fake_gh(checks={"python": "cancel", "frontend": "pass"})
        result = pipeline_merge.decide(
            "hunter", 3, verdict=GREEN, runner=runner, sleep=lambda _: None,
            log=lambda *_: None,
        )
        self.assertFalse(result["merged"])
        self.assertEqual(merged_prs(runner), [])


class AutoDoesNotWait(unittest.TestCase):
    """Prosa sola, e la suite l'ha gia' girata il cancello: aspettare la CI qui
    servirebbe solo a far scadere una sessione cloud."""

    def test_it_merges_without_looking_at_the_checks(self):
        runner = fake_gh(checks={"python": "pending"})
        result = pipeline_merge.decide("writer", 9, verdict=AUTO, runner=runner, log=lambda *_: None)
        self.assertTrue(result["merged"])
        self.assertEqual(merged_prs(runner), ["9"])


class TheOutcomeIsAlwaysReportable(unittest.TestCase):
    """Ogni uscita deve poter diventare una riga di diario, o una run che si
    ferma resta invisibile come prima."""

    def test_every_outcome_is_a_word_the_journal_knows(self):
        from scripts import pipeline_log

        runners = {
            "blocked": (RED, fake_gh()),
            "stopped": (GREEN, fake_gh(checks={"python": "fail"})),
            "merged": (AUTO, fake_gh()),
            "error": (AUTO, fake_gh(merge_ok=False)),
        }
        for expected, (verdict, runner) in runners.items():
            result = pipeline_merge.decide(
                "writer", 1, verdict=verdict, runner=runner, sleep=lambda _: None,
                log=lambda *_: None,
            )
            self.assertEqual(result["outcome"], expected)
            self.assertIn(result["outcome"], pipeline_log.OUTCOMES)

    def test_dry_run_leaves_the_pull_request_open(self):
        runner = fake_gh(checks={"python": "pass", "frontend": "pass"})
        result = pipeline_merge.decide(
            "curator", 5, verdict=GREEN, runner=runner, sleep=lambda _: None,
            dry_run=True, log=lambda *_: None,
        )
        self.assertFalse(result["merged"])
        self.assertEqual(result["outcome"], "pr-open")
        self.assertEqual(merged_prs(runner), [])


class TheVerdictIsNotTakenFromTheCaller(unittest.TestCase):
    def test_the_gate_runs_when_no_verdict_is_given(self):
        """Un passo di merge che si fida del rapporto dell'agente sul proprio
        cancello non protegge niente: e' esattamente il momento che un agente
        che ha sbagliato salterebbe."""
        seen = {}

        def fake_gate(stage, skip_tests=False, cwd=None):
            seen["stage"] = stage
            return RED

        original = pipeline_merge.pipeline_gate.run
        pipeline_merge.pipeline_gate.run = fake_gate
        try:
            result = pipeline_merge.decide("reviewer", 2, runner=fake_gh(), log=lambda *_: None)
        finally:
            pipeline_merge.pipeline_gate.run = original
        self.assertEqual(seen["stage"], "reviewer")
        self.assertFalse(result["merged"])


def journalling_gh(checks=None, merge_ok=True, push_failures=0):
    """Come `fake_gh`, ma tiene anche il conto dei comandi git del diario e sa
    far perdere le prime N corse al push, che e' il caso che conta."""
    runner = fake_gh(checks=checks, merge_ok=merge_ok)
    inner, state = runner, {"pushes": 0, "rows": []}

    def wrapper(argv, cwd=None):
        if argv[:2] == ["git", "push"]:
            state["pushes"] += 1
            if state["pushes"] <= push_failures:
                return 1, "rejected: non-fast-forward"
            return 0, ""
        if argv[:2] == ["git", "commit"]:
            # La riga e' gia' stata scritta nel worktree: la leggiamo da li',
            # perche' e' quello che finira' davvero su master.
            path = Path(cwd) / "data" / "pipeline" / "runs.jsonl"
            if path.exists():
                state["rows"] = [json.loads(x) for x in
                                 path.read_text(encoding="utf-8").splitlines() if x.strip()]
            return 0, ""
        if argv[:2] == ["git", "rev-parse"]:
            return 0, "abc1234\n"
        return inner(argv, cwd=cwd)

    wrapper.calls = inner.calls
    wrapper.state = state
    return wrapper


class MasterHasToLearnHowItEnded(unittest.TestCase):
    """Il buco che questo chiude e' doppio, e la meta' peggiore non e' il merge.

    Una run rifiutata scrive la propria riga su un branch che non si fonde mai,
    quindi da master non si vede: la run dello scout del 26 luglio esiste, dice
    `blocked`, e vive su `automation/scout-2026-07-26` dove nessuno strumento la
    legge. Master non sa distinguerla da una run mai avvenuta.
    """

    def test_a_refusal_is_recorded_on_master(self):
        runner = journalling_gh()
        pipeline_merge.decide("scout", 41, verdict=RED, runner=runner, log=lambda *_: None)
        rows = runner.state["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["outcome"], "blocked")
        self.assertEqual(rows[0]["pr"], 41)
        self.assertEqual(rows[0]["branch"], "master")

    def test_checks_that_never_conclude_are_recorded_too(self):
        runner = journalling_gh(checks=None)
        pipeline_merge.decide("curator", 7, verdict=GREEN, runner=runner,
                              sleep=lambda _: None, log=lambda *_: None)
        self.assertEqual([r["outcome"] for r in runner.state["rows"]], ["stopped"])

    def test_a_merge_is_recorded_on_master(self):
        runner = journalling_gh(checks={"python": "pass"})
        pipeline_merge.decide("hunter", 45, verdict=GREEN, runner=runner,
                              sleep=lambda _: None, log=lambda *_: None)
        rows = runner.state["rows"]
        self.assertEqual([r["outcome"] for r in rows], ["merged"])
        self.assertEqual(rows[0]["gate"], "checks")

    def test_a_pull_request_left_open_writes_nothing(self):
        """`pr-open` non e' un esito terminale: la PR resta aperta e la riga che
        l'agente ha gia' committato dentro di essa la descrive bene. Scriverne
        una seconda su master direbbe che e' finita quando non e' finita."""
        runner = journalling_gh(checks={"python": "pass"})
        pipeline_merge.decide("writer", 9, verdict=AUTO, runner=runner,
                              dry_run=True, log=lambda *_: None)
        self.assertEqual(runner.state["rows"], [])
        self.assertEqual(runner.state["pushes"], 0)

    def test_a_lost_push_race_is_retried(self):
        """Due stadi che finiscono insieme si contendono la coda del registro.
        Il ritentativo rilegge origin/master, che intanto porta la riga
        dell'altro, e ci va dietro: su un file in coda e' sempre corretto."""
        runner = journalling_gh(checks={"python": "pass"}, push_failures=1)
        pipeline_merge.decide("hunter", 45, verdict=GREEN, runner=runner,
                              sleep=lambda _: None, log=lambda *_: None)
        self.assertEqual(runner.state["pushes"], 2)
        self.assertEqual([r["outcome"] for r in runner.state["rows"]], ["merged"])

    def test_it_never_writes_into_the_agents_own_tree(self):
        """L'albero dell'agente e' su un branch appena cancellato dal remoto.
        Toccarlo per scrivere una riga di log e' un modo di perdere lavoro."""
        runner = journalling_gh(checks={"python": "pass"})
        pipeline_merge.decide("hunter", 45, verdict=GREEN, runner=runner,
                              sleep=lambda _: None, log=lambda *_: None)
        for argv in runner.calls:
            self.assertNotIn(argv[:2], ([  "git", "checkout"], ["git", "switch"]))
            self.assertNotIn(argv[:2], (["git", "reset"],))

    def test_a_journal_failure_does_not_undo_the_merge(self):
        """Il merge e' gia' avvenuto. Se il diario non si scrive la run resta
        valida, e l'unica cosa che cambia e' che va detto forte."""
        runner = journalling_gh(checks={"python": "pass"}, push_failures=99)
        said = []
        result = pipeline_merge.decide("hunter", 45, verdict=GREEN, runner=runner,
                                       sleep=lambda _: None, log=said.append)
        self.assertTrue(result["merged"])
        self.assertTrue(any("DIARIO NON SCRITTO" in s for s in said))

    def test_the_journal_can_be_turned_off(self):
        runner = journalling_gh(checks={"python": "pass"})
        pipeline_merge.decide("hunter", 45, verdict=GREEN, runner=runner,
                              sleep=lambda _: None, log=lambda *_: None, journal=False)
        self.assertEqual(runner.state["pushes"], 0)


if __name__ == "__main__":
    unittest.main()
