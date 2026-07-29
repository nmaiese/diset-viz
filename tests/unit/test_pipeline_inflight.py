"""La fotografia delle PR aperte, e la classificazione che regge il cruscotto.

Niente rete: il `runner` di `pipeline_merge` e' iniettato, e la parte pura
(`build_snapshot`) si prova passando dict. Il punto e' che il cruscotto distingua
in-corsa, rossa e verde, e che ignori le PR fuori da `automation/*`.
"""

import unittest

from scripts import pipeline_inflight as inflight


class BuildSnapshotIsPure(unittest.TestCase):
    def test_it_keeps_only_automation_branches(self):
        pulls = [
            {"number": 1, "head": {"ref": "automation/producer-2026-07-29-abcd"}, "title": "t1"},
            {"number": 2, "head": {"ref": "feature/qualcosa"}, "title": "t2"},
        ]
        snap = inflight.build_snapshot(pulls, {})
        self.assertEqual([p["pr"] for p in snap], [1])
        self.assertEqual(snap[0]["role"], "producer")

    def test_it_classifies_ci_from_the_check_buckets(self):
        pulls = [
            {"number": 10, "head": {"ref": "automation/producer-2026-07-29-a"}, "title": "verde"},
            {"number": 11, "head": {"ref": "automation/producer-2026-07-29-b"}, "title": "rossa"},
            {"number": 12, "head": {"ref": "automation/producer-2026-07-29-c"}, "title": "corsa"},
            {"number": 13, "head": {"ref": "automation/producer-2026-07-29-d"}, "title": "nessuna"},
        ]
        details = {
            10: {"states": {"python": "pass", "gate": "pass"}},
            11: {"states": {"python": "pass", "gate": "fail"}},
            12: {"states": {"python": "pending"}},
            13: {"states": {}},
        }
        by_pr = {p["pr"]: p["ci"] for p in inflight.build_snapshot(pulls, details)}
        self.assertEqual(by_pr[10], "verde")
        self.assertEqual(by_pr[11], "rossa")
        self.assertEqual(by_pr[12], "in-corsa")
        self.assertEqual(by_pr[13], "nessuna")

    def test_a_cancelled_check_is_not_green(self):
        # `cancel` non e' fra i bucket passanti: il merge lo rifiuterebbe, quindi
        # il cruscotto non deve mostrarlo verde.
        pulls = [{"number": 20, "head": {"ref": "automation/producer-2026-07-29-x"}}]
        details = {20: {"states": {"python": "pass", "gate": "cancel"}}}
        self.assertEqual(inflight.build_snapshot(pulls, details)[0]["ci"], "rossa")

    def test_run_id_comes_from_body_then_branch(self):
        from_body = inflight.build_snapshot(
            [{"number": 1, "head": {"ref": "automation/producer-2026-07-29-abcd"},
              "body": "Lavoro.\nrun_id: producer-20260729T101010Z-abcd\n"}], {})[0]
        self.assertEqual(from_body["run_id"], "producer-20260729T101010Z-abcd")
        from_branch = inflight.build_snapshot(
            [{"number": 2, "head": {"ref": "automation/verificatore-2026-07-29-c0de"},
              "body": ""}], {})[0]
        self.assertEqual(from_branch["run_id"], "verificatore-2026-07-29-c0de")

    def test_mergeable_is_a_word_from_the_per_pr_detail(self):
        # La mergeabilita' arriva dal dettaglio per-PR, non dalla lista (che non la
        # porta): una lista senza dettaglio da' "?", non un falso "si"/"no".
        pulls = [
            {"number": 1, "head": {"ref": "automation/a-b"}},
            {"number": 2, "head": {"ref": "automation/a-c"}},
            {"number": 3, "head": {"ref": "automation/a-d"}},
        ]
        details = {1: {"mergeable": True}, 2: {"mergeable": False}, 3: {}}
        rows = inflight.build_snapshot(pulls, details)
        self.assertEqual([r["mergeable"] for r in rows], ["si", "no", "?"])


class OpenRunsReadsRestWithoutGhRepo(unittest.TestCase):
    """Come il merge, legge le PR dallo slug ricavato dal remote proxato, senza
    `GH_REPO`, sulla superficie REST."""

    def _runner(self):
        import json

        calls = []

        def runner(argv, cwd=None):
            calls.append(argv)
            if argv[:2] == ["git", "remote"]:
                return 0, "http://local_proxy@127.0.0.1:41729/git/nmaiese/diset-viz\n"
            if argv[:2] != ["gh", "api"]:
                return 0, ""
            path = argv[-1]
            if "pulls?state=open" in path:
                return 0, json.dumps([
                    {"number": 7, "head": {"ref": "automation/producer-2026-07-29-abcd", "sha": "s7"},
                     "title": "produttore", "mergeable": True},
                    {"number": 8, "head": {"ref": "dependabot/x", "sha": "s8"}, "title": "bot"},
                ])
            if "/check-runs" in path:
                return 0, json.dumps({"check_runs": [
                    {"name": "python", "status": "completed", "conclusion": "success"}]})
            if path.endswith("/status") or "/status?" in path:
                return 0, json.dumps({"statuses": []})
            if "/pulls/" in path:
                return 0, json.dumps({
                    "head": {"sha": "s7", "ref": "automation/producer-2026-07-29-abcd"},
                    "mergeable": True})
            return 0, "{}"

        runner.calls = calls
        return runner

    def test_it_returns_only_the_automation_pr_with_its_ci(self):
        import os

        self.assertNotIn("GH_REPO", os.environ)
        snap = inflight.open_runs(runner=self._runner())
        self.assertEqual([p["pr"] for p in snap], [7])
        self.assertEqual(snap[0]["ci"], "verde")
        self.assertEqual(snap[0]["mergeable"], "si")

    def test_a_github_failure_raises_instead_of_returning_empty(self):
        # Un fallimento non e' "nessuna PR aperta": confonderli farebbe cancellare
        # la fotografia al primo intoppo transitorio di GitHub o del proxy.
        def runner(argv, cwd=None):
            if argv[:2] == ["git", "remote"]:
                return 0, "http://local_proxy@127.0.0.1:41729/git/nmaiese/diset-viz\n"
            if "pulls?state=open" in argv[-1]:
                return 1, "HTTP 502: Bad Gateway"
            return 0, "{}"
        with self.assertRaises(RuntimeError):
            inflight.open_runs(runner=runner)

    def test_a_per_pr_failure_also_raises_not_degrades_to_no_checks(self):
        # La lista riesce, ma la GET per-PR fallisce: non si degrada a "nessuna"
        # (che cancellerebbe uno stato rosso vero), si solleva e si tiene la
        # fotografia precedente.
        import json

        def runner(argv, cwd=None):
            if argv[:2] == ["git", "remote"]:
                return 0, "http://local_proxy@127.0.0.1:41729/git/nmaiese/diset-viz\n"
            path = argv[-1]
            if "pulls?state=open" in path:
                return 0, json.dumps([
                    {"number": 7, "head": {"ref": "automation/producer-2026-07-29-abcd"},
                     "title": "produttore"}])
            if "/pulls/" in path:
                return 1, "HTTP 502: Bad Gateway"
            return 0, "{}"
        with self.assertRaises(RuntimeError):
            inflight.open_runs(runner=runner)


if __name__ == "__main__":
    unittest.main()
