"""Il passo del sito, ora in `verify_publication` (era nel dispatcher ritirato).

Verifica gli indicatori fusi e scrive le prove senza lanciare un agente; un sito
che non conferma non scrive niente; le prove arrivano su master con un commit
costruito sopra origin/master, spinto da qualunque branch. Nessun test qui tocca
la rete o git davvero: il fetcher e il runner sono iniettati."""

import tempfile
import unittest

from scripts import verify_publication


class ThePublishStepObservesTheSite(unittest.TestCase):
    """Il passo del sito: verifica gli indicatori fusi e scrive le prove. Un sito
    che non conferma non scrive niente, e le prove si committano a parte."""

    def _fusa_indicator(self):
        queue = verify_publication.publication_queue()
        if not queue:
            self.skipTest("nessun indicatore in stato fusa da verificare")
        return queue[0]["id"]

    def test_a_confirming_site_writes_a_proof(self):
        from scripts import indicator_store
        ind = self._fusa_indicator()
        entry = indicator_store.read(ind)
        sig = verify_publication.page_signature(entry)

        def good_fetcher(url):
            return f"<html><body><p>{sig['snippet']} ...</p><p>anno {sig['vintage']}</p></body></html>"

        root = tempfile.mkdtemp()
        summary = verify_publication.publish_step(
            fetcher=good_fetcher, proofs_root=root, do_commit=False)
        self.assertGreaterEqual(summary["prove_scritte"], 1)
        self.assertTrue(any(c["ok"] for c in summary["checked"]))

    def test_an_unreachable_site_writes_nothing(self):
        def dead_fetcher(url):
            raise OSError("giu'")

        root = tempfile.mkdtemp()
        summary = verify_publication.publish_step(
            fetcher=dead_fetcher, proofs_root=root, do_commit=False)
        self.assertEqual(summary["prove_scritte"], 0)
        # ne' successo ne' fallimento: ogni controllo e' irraggiungibile (ok None)
        self.assertTrue(all(c["ok"] is None for c in summary["checked"]))

    def test_a_wrong_version_writes_nothing(self):
        def stale_fetcher(url):
            return "<html><body>una pagina che non porta ne' lead ne' anno</body></html>"

        root = tempfile.mkdtemp()
        summary = verify_publication.publish_step(
            fetcher=stale_fetcher, proofs_root=root, do_commit=False)
        self.assertEqual(summary["prove_scritte"], 0)


class TheProofsLandOnMasterFromAnyBranch(unittest.TestCase):
    """Le prove arrivano su master con un commit costruito sopra origin/master con
    dentro solo le prove, spinto da qualunque branch. La sessione non e' mai su
    master, quindi il push non passa da HEAD: l'invariante 'non spinge altro che
    se stesso' vale per costruzione."""

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
        ok = verify_publication.commit_proofs([self.REL], runner=runner, log=lambda *_: None)
        self.assertTrue(ok)
        argvs = self._argvs(runner)
        self.assertIn(["git", "read-tree", "origin/master"], argvs)
        self.assertIn(["git", "add", "--", self.REL], argvs)
        self.assertIn(["git", "push", "origin", f"{'c' * 40}:master"], argvs)
        self.assertNotIn(["git", "push", "origin", "HEAD:master"], argvs)

    def test_it_does_not_gate_on_the_working_branch(self):
        runner = self.runner()
        ok = verify_publication.commit_proofs([self.REL], runner=runner, log=lambda *_: None)
        self.assertTrue(ok)
        self.assertFalse(any(a[:2] == ["git", "rev-parse"] for a in self._argvs(runner)))

    def test_more_than_one_proof_rides_the_same_commit(self):
        other = "data/pipeline/pubblicazioni/ter-14__regione__def.json"
        runner = self.runner()
        ok = verify_publication.commit_proofs([self.REL, other], runner=runner, log=lambda *_: None)
        self.assertTrue(ok)
        adds = [c["argv"] for c in runner.calls if c["argv"][:2] == ["git", "add"]]
        # entrambe le prove nello stesso add, e un solo push
        self.assertEqual(adds, [["git", "add", "--", other, self.REL]])
        self.assertEqual(sum(a[:3] == ["git", "push", "origin"] for a in self._argvs(runner)), 1)

    def test_it_retries_the_push_on_a_lost_race(self):
        runner = self.runner(push_fails_first=1)
        ok = verify_publication.commit_proofs([self.REL], runner=runner, log=lambda *_: None)
        self.assertTrue(ok)
        argvs = self._argvs(runner)
        self.assertEqual(sum(a[:3] == ["git", "push", "origin"] for a in argvs), 2)
        self.assertEqual(argvs.count(["git", "fetch", "origin", "master"]), 2)


if __name__ == "__main__":
    unittest.main()
