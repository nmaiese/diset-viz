"""Il worktree privato di una run, e la contesa che toglie.

Dieci agenti in volo nella stessa working directory si contendevano HEAD, indice
e branch corrente: un `git checkout -b` altrui bastava a far sparire il lavoro
gia' committato di un altro. Questi test non parlano con git vero: il `runner` e'
iniettato, cosi' si prova la **sequenza** dei comandi, che e' dove sta la
correttezza (fetch prima, poi worktree sul branch della run).
"""

import unittest

from scripts import pipeline_workspace as ws


class Runner:
    """Un finto git che registra gli argv e risponde ok, salvo dove chiesto."""

    def __init__(self, fail_on=None):
        self.calls = []
        self.fail_on = fail_on or ()

    def __call__(self, argv, cwd=None):
        self.calls.append(argv)
        if self.fail_on and tuple(argv[:len(self.fail_on)]) == self.fail_on:
            return 1, "boom"
        return 0, ""


class TheBranchIsUniquePerRun(unittest.TestCase):
    """La collisione su un nome condiviso era la causa dei branch spostati sotto
    i piedi: due run dello stesso ruolo nello stesso giorno devono avere branch
    diversi, e la differenza viene dal suffisso unico del run_id."""

    def test_two_runs_same_role_same_day_get_different_branches(self):
        a = ws.branch_name("producer", "producer-20260729T101010Z-aaaa", today="2026-07-29")
        b = ws.branch_name("producer", "producer-20260729T101011Z-bbbb", today="2026-07-29")
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith("automation/producer-2026-07-29-"))
        self.assertTrue(b.endswith("bbbb"))

    def test_it_stays_under_the_automation_namespace(self):
        # il cancello in CI e la guardia per-agente riconoscono automation/*.
        name = ws.branch_name("verificatore", "verificatore-20260729T101010Z-c0de",
                              today="2026-07-29")
        self.assertTrue(name.startswith("automation/"))


class OpeningIsolatesTheRun(unittest.TestCase):
    def test_it_fetches_master_then_adds_the_worktree(self):
        runner = Runner()
        path = ws.open_workspace("producer", "producer-20260729T101010Z-abcd",
                                 runner=runner, today="2026-07-29", root="/tmp/runs")
        # fetch prima di tutto: la run parte da master aggiornato, non da HEAD.
        self.assertEqual(runner.calls[0], ["git", "fetch", "origin", "master"])
        add = [c for c in runner.calls if c[:3] == ["git", "worktree", "add"]]
        self.assertEqual(len(add), 1)
        argv = add[0]
        self.assertIn("-b", argv)
        branch = argv[argv.index("-b") + 1]
        self.assertTrue(branch.startswith("automation/producer-2026-07-29-"))
        self.assertIn("origin/master", argv)
        self.assertTrue(path.endswith("producer-20260729T101010Z-abcd"))

    def test_a_transient_fetch_lock_is_retried_until_it_succeeds(self):
        # Il fetch perde la corsa sul ref remoto condiviso ("cannot lock ref")
        # un paio di volte, poi il lock del sibling si libera e riesce: si procede.
        # Solo un fetch NOSTRO riuscito prova che il ref e' fresco.
        fails = {"n": 2}

        def runner(argv, cwd=None):
            if argv[:2] == ["git", "fetch"]:
                if fails["n"] > 0:
                    fails["n"] -= 1
                    return 1, "cannot lock ref refs/remotes/origin/master"
                return 0, ""
            runner.calls.append(argv)
            return 0, ""
        runner.calls = []
        ws.open_workspace("producer", "run-1", runner=runner, root="/tmp/runs",
                          sleep=lambda _: None)
        self.assertIn(["git", "worktree", "add"], [c[:3] for c in runner.calls])

    def test_a_persistent_fetch_failure_is_loud(self):
        # Il fetch non riesce mai (rete/auth, o lock che non si libera): non si
        # parte da un origin/master non verificato fresco, si fallisce l'apertura.
        runner = Runner(fail_on=("git", "fetch"))
        with self.assertRaises(RuntimeError):
            ws.open_workspace("producer", "run-1", runner=runner, sleep=lambda _: None)

    def test_a_failed_worktree_add_is_loud(self):
        runner = Runner(fail_on=("git", "worktree", "add"))
        with self.assertRaises(RuntimeError):
            ws.open_workspace("producer", "run-1", runner=runner)

    def test_here_opens_a_branch_in_place_without_a_worktree(self):
        runner = Runner()
        ws.open_workspace("producer", "producer-20260729T101010Z-abcd",
                          runner=runner, today="2026-07-29", here=True)
        self.assertNotIn(["git", "worktree", "add"],
                         [c[:3] for c in runner.calls])
        checkout = [c for c in runner.calls if c[:2] == ["git", "checkout"]]
        self.assertEqual(len(checkout), 1)
        self.assertIn("-b", checkout[0])


class ClosingRemovesAndPrunes(unittest.TestCase):
    def test_it_removes_the_worktree_then_prunes(self):
        runner = Runner()
        ws.close_workspace("producer-20260729T101010Z-abcd", runner=runner, root="/tmp/runs")
        kinds = [c[:3] for c in runner.calls]
        self.assertIn(["git", "worktree", "remove"], kinds)
        self.assertIn(["git", "worktree", "prune"], kinds)
        remove = [c for c in runner.calls if c[:3] == ["git", "worktree", "remove"]][0]
        self.assertIn("--force", remove)


if __name__ == "__main__":
    unittest.main()
