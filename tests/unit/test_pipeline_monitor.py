"""Il monitoraggio: la vista di lettura sul dossier per-indicatore.

Nucleo puro (`board`, `headline`): ogni test costruisce un dossier sintetico,
senza toccare il disco. I battiti si provano su una cartella temporanea, con
`now` iniettato cosi' la staleness e' deterministica."""

import tempfile
import unittest
from pathlib import Path

from scripts import pipeline_monitor


def practice(code, *, state="in-lavorazione", flags=None, completed=(),
             required=("curator", "writer", "reviewer", "verificatore"),
             priority=0.0, entered_at="2026-07-01"):
    return {
        "id": code, "state": state, "flags": dict(flags or {}),
        "completed_stages": list(completed), "required_stages": tuple(required),
        "priority": priority, "entered_at": entered_at, "error_class": None,
    }


class Board(unittest.TestCase):
    TODAY = "2026-07-28"

    def test_headline_names_the_stuck_first(self):
        dossier = {
            "ter-1": practice("ter-1", state="invalidata",
                              flags={"open_smentita": True}, entered_at="2026-07-26"),
            "ter-2": practice("ter-2", completed=["curator"], priority=5.0),
        }
        b = pipeline_monitor.board(dossier, today=self.TODAY)
        self.assertIn("1 indicatore bloccato", b["headline"])
        self.assertIn("ter-1", b["headline"])
        self.assertIn("smentita", b["headline"])
        self.assertEqual([r["id"] for r in b["stuck"]], ["ter-1"])

    def test_headline_when_nothing_is_stuck(self):
        dossier = {"ter-2": practice("ter-2", completed=["curator"], priority=5.0)}
        b = pipeline_monitor.board(dossier, today=self.TODAY)
        self.assertIn("pronti al lavoro", b["headline"])
        self.assertEqual(b["stuck"], [])            # la forma "fermi" non scatta

    def test_headline_when_chain_is_idle(self):
        dossier = {"ter-3": practice("ter-3", state="pubblicata",
                                     completed=["curator", "writer", "reviewer", "verificatore"])}
        b = pipeline_monitor.board(dossier, today=self.TODAY)
        self.assertIn("in pari", b["headline"])

    def test_rows_map_the_next_role_from_the_ready_stage(self):
        dossier = {
            "ter-w": practice("ter-w", completed=["curator"]),                 # writer -> producer
            "ter-v": practice("ter-v", completed=["curator", "writer", "reviewer"]),  # verificatore
        }
        b = pipeline_monitor.board(dossier, today=self.TODAY)
        roles = {r["id"]: r["next_role"] for r in b["rows"]}
        self.assertEqual(roles["ter-w"], "producer")
        self.assertEqual(roles["ter-v"], "verificatore")

    def test_totals_count_every_state(self):
        dossier = {
            "a": practice("a", state="in-lavorazione", completed=["curator"]),
            "b": practice("b", state="pubblicata"),
            "c": practice("c", state="in-lavorazione", completed=["curator"]),
        }
        b = pipeline_monitor.board(dossier, today=self.TODAY)
        self.assertEqual(b["totals"]["in-lavorazione"], 2)
        self.assertEqual(b["totals"]["pubblicata"], 1)

    def test_rows_carry_stages_published_and_per_indicator_run_history(self):
        d = practice("ter-x", state="fusa",
                     completed=["curator", "writer", "reviewer"], priority=3.0)
        d.update({"published": True, "verification_valid": True,
                  "runs": ["producer-r1", "verificatore-r2"]})
        runs = [
            {"run_id": "producer-r1", "stage": "writer", "outcome": "merged",
             "summary": "scritto e firmato", "at": "2026-07-02T09:00:00+00:00",
             "model": "claude-opus-4-8", "duration_seconds": 120},
            {"run_id": "verificatore-r2", "stage": "verificatore", "outcome": "merged",
             "summary": "36 controllate, 0 smentite", "at": "2026-07-05T09:00:00+00:00",
             "model": "claude-opus-4-8", "duration_seconds": 90},
            {"run_id": "altro-r3", "stage": "writer", "outcome": "merged",
             "summary": "un'altra run non collegata", "at": "2026-07-06T09:00:00+00:00"},
        ]
        b = pipeline_monitor.board({"ter-x": d}, runs=runs, today=self.TODAY)
        row = b["rows"][0]
        self.assertEqual(row["completed_stages"], ["curator", "writer", "reviewer"])
        self.assertIs(row["published"], True)
        self.assertIs(row["verification_valid"], True)
        # solo le run in d["runs"], unite per run_id, la piu' recente prima
        self.assertEqual([r["run_id"] for r in row["runs"]],
                         ["verificatore-r2", "producer-r1"])
        self.assertEqual(row["runs"][0]["summary"], "36 controllate, 0 smentite")
        self.assertEqual(row["runs"][0]["duration_seconds"], 90)
        self.assertEqual(row["runs"][1]["model"], "claude-opus-4-8")
        self.assertNotIn("altro-r3", [r["run_id"] for r in row["runs"]])

    def test_a_run_id_without_a_collapsed_run_is_skipped_not_crashed(self):
        d = practice("ter-y", completed=["curator"])
        d["runs"] = ["mancante-r9"]
        b = pipeline_monitor.board({"ter-y": d}, runs=[], today=self.TODAY)
        self.assertEqual(b["rows"][0]["runs"], [])

    def test_recent_history_is_newest_first_and_capped(self):
        runs = [{"at": f"2026-07-{d:02d}T09:00:00+00:00", "stage": "writer",
                 "outcome": "merged", "summary": f"run {d}", "run_id": f"r{d}"}
                for d in range(1, 20)]
        b = pipeline_monitor.board({}, runs=runs, today=self.TODAY, recent=5)
        self.assertEqual(len(b["recent"]), 5)
        self.assertEqual(b["recent"][0]["run_id"], "r19")  # il piu' recente

    def test_a_fused_indicator_names_the_site_step_instead_of_looking_finished(self):
        d = practice("ter-fusa", state="fusa",
                     completed=["curator", "writer", "reviewer", "verificatore"])
        d.update({"published": None, "verification_valid": True})
        row = pipeline_monitor.board({"ter-fusa": d}, today=self.TODAY)["rows"][0]
        self.assertEqual(row["phase"], "pubblicazione")
        self.assertEqual(row["next_step"]["owner"], "passo del sito")
        self.assertIn("prova di pubblicazione", row["next_step"]["label"])
        self.assertEqual(row["progress"], 75)

    def test_an_open_smentita_is_an_explicit_producer_action(self):
        d = practice("ter-bad", state="invalidata", flags={"open_smentita": True},
                     completed=["writer", "reviewer", "verificatore"],
                     required=["writer", "reviewer", "verificatore"])
        d.update({"verification_valid": True, "timeline": []})
        b = pipeline_monitor.board({"ter-bad": d}, today=self.TODAY)
        row = b["rows"][0]
        self.assertEqual(row["next_step"]["kind"], "attention")
        self.assertEqual(row["next_step"]["owner"], "produttore")
        self.assertEqual(row["lifecycle"][1]["status"], "issue")
        self.assertEqual(b["metrics"]["attention"], 1)

    def test_the_row_keeps_the_complete_timeline_and_operational_run_detail(self):
        d = practice("ter-x", completed=["writer"], required=["writer", "reviewer", "verificatore"])
        d.update({
            "timeline": [{"at": "2026-07-01", "stage": "writer", "kind": "scritta",
                          "detail": "prima versione"}],
            "runs": ["producer-r1"],
        })
        runs = [{"run_id": "producer-r1", "stage": "producer", "outcome": "merged",
                 "summary": "articolo scritto", "detail": ["controllati 20 territori"],
                 "at": "2026-07-02T09:00:00+00:00", "trigger": "launch", "pr": "42"}]
        row = pipeline_monitor.board({"ter-x": d}, runs=runs, today=self.TODAY)["rows"][0]
        self.assertEqual(row["timeline"][0]["stage_label"], "Scrittura")
        self.assertEqual(row["runs"][0]["detail"], ["controllati 20 territori"])
        self.assertEqual(row["runs"][0]["trigger"], "launch")
        self.assertEqual(row["last_activity"]["label"], "articolo scritto")

    def test_live_and_pr_state_are_joined_back_to_the_indicator(self):
        d = practice("ter-live", completed=["writer"], required=["writer", "reviewer", "verificatore"])
        d["runs"] = ["producer-live"]
        beat = {"indicator": "ter-live", "run_id": "producer-live", "role": "producer",
                "since": "2026-07-28T10:00:00+00:00"}
        pr = {"run_id": "producer-live", "pr": 77, "ci": "in-corsa"}
        row = pipeline_monitor.board({"ter-live": d}, heartbeats=[beat], open_runs=[pr],
                                     today=self.TODAY)["rows"][0]
        self.assertEqual(row["in_flight"][0]["run_id"], "producer-live")
        self.assertEqual(row["open_prs"][0]["pr"], 77)


class IndicatorLabels(unittest.TestCase):
    def test_names_come_from_committed_catalog_manifests(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "app/static/data"
            path.mkdir(parents=True)
            (path / "external_indicator_manifest.csv").write_text(
                "target_indicator_id;target_indicator_name\n1;Produttivita agricola\n", encoding="utf-8")
            (path / "bes_regione_manifest.csv").write_text(
                "id;name\n10AMB002;Consumo materiale interno\n", encoding="utf-8")
            (path / "multiscopo_regione_manifest.csv").write_text(
                "id;name\nMULTI_TEST;Indicatore test\n", encoding="utf-8")
            labels = pipeline_monitor.indicator_labels(root=root)
        self.assertEqual(labels["1"]["name"], "Produttivita agricola")
        self.assertEqual(labels["bes:10AMB002"]["family"], "BES")
        self.assertEqual(labels["multiscopo:MULTI_TEST"]["name"], "Indicatore test")


class AttributeTokens(unittest.TestCase):
    """I token vanno solo all'indicatore bersaglio, non ai confronti."""

    def test_tokens_go_to_the_target_not_to_comparison_indicators(self):
        # v-1 compare nella storia di ter-1 (bersaglio) e di ter-2 (citato come
        # confronto): il costo e' di ter-1 soltanto, e il record lo dice.
        rows = [
            {"id": "ter-1", "runs": [{"run_id": "v-1"}]},
            {"id": "ter-2", "runs": [{"run_id": "v-1"}]},
        ]
        tokens = {"v-1": {"tokens": 5000, "indicator": "ter-1"}}
        pipeline_monitor.attribute_tokens(rows, tokens)
        self.assertEqual(rows[0]["runs"][0]["tokens"], 5000)   # bersaglio
        self.assertEqual(rows[0]["tokens_total"], 5000)
        self.assertIsNone(rows[1]["runs"][0]["tokens"])        # confronto, niente inflazione
        self.assertIsNone(rows[1]["tokens_total"])

    def test_a_batch_run_without_a_target_is_not_attributed(self):
        rows = [{"id": "ter-1", "runs": [{"run_id": "adm-1"}]}]
        tokens = {"adm-1": {"tokens": 9000, "indicator": ""}}  # ammissione batch
        pipeline_monitor.attribute_tokens(rows, tokens)
        self.assertIsNone(rows[0]["runs"][0]["tokens"])
        self.assertIsNone(rows[0]["tokens_total"])


class Heartbeats(unittest.TestCase):
    def test_write_read_clear_roundtrip(self):
        root = tempfile.mkdtemp()
        pipeline_monitor.write_heartbeat("producer", "producer-abc", "ter-16",
                                         root=root, now="2026-07-28T10:00:00+00:00")
        live = pipeline_monitor.read_heartbeats(root=root, now="2026-07-28T10:30:00+00:00")
        self.assertEqual(len(live), 1)
        self.assertEqual(live[0]["indicator"], "ter-16")
        self.assertEqual(live[0]["role"], "producer")
        pipeline_monitor.clear_heartbeat("producer-abc", root=root)
        self.assertEqual(pipeline_monitor.read_heartbeats(root=root,
                         now="2026-07-28T10:30:00+00:00"), [])

    def test_a_stale_heartbeat_is_dropped(self):
        root = tempfile.mkdtemp()
        pipeline_monitor.write_heartbeat("producer", "producer-old", "ter-9",
                                         root=root, now="2026-07-20T10:00:00+00:00")
        # otto giorni dopo: oltre la soglia, la sessione e' considerata caduta
        live = pipeline_monitor.read_heartbeats(root=root, now="2026-07-28T10:00:00+00:00")
        self.assertEqual(live, [])

    def test_two_roles_in_flight_do_not_collide(self):
        root = tempfile.mkdtemp()
        pipeline_monitor.write_heartbeat("producer", "producer-1", "ter-1",
                                         root=root, now="2026-07-28T10:00:00+00:00")
        pipeline_monitor.write_heartbeat("verificatore", "verificatore-2", "ter-2",
                                         root=root, now="2026-07-28T10:00:00+00:00")
        live = pipeline_monitor.read_heartbeats(root=root, now="2026-07-28T10:05:00+00:00")
        self.assertEqual({h["run_id"] for h in live}, {"producer-1", "verificatore-2"})


class PostTokens(unittest.TestCase):
    """Il POST del consumo token: paga best effort, payload giusto."""

    def _capture(self):
        import json as _json
        captured = {}

        class FakeResp:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False

        def opener(req, timeout=None):
            captured["url"] = req.full_url
            captured["body"] = _json.loads(req.data.decode("utf-8"))
            return FakeResp()

        return captured, opener

    def test_post_tokens_builds_a_tokens_payload(self):
        captured, opener = self._capture()
        ok = pipeline_monitor.post_tokens(
            "producer-r1", 46121, indicator="ter-178", stage="producer",
            role="producer", url="https://divarioitalia.it", token="k", opener=opener)
        self.assertTrue(ok)
        self.assertTrue(captured["url"].endswith("/_pipeline/beat"))
        body = captured["body"]
        self.assertEqual(body["action"], "tokens")
        self.assertEqual(body["run_id"], "producer-r1")
        self.assertEqual(body["tokens"], 46121)
        self.assertEqual(body["indicator"], "ter-178")
        self.assertEqual(body["stage"], "producer")

    def test_post_tokens_is_silent_without_env(self):
        # senza url/segreto (ne' argomenti ne' ambiente) non fa nulla, e lo dice
        import os
        saved = {k: os.environ.pop(k, None) for k in ("PIPELINE_INGEST_URL", "PIPELINE_INGEST_TOKEN")}
        try:
            self.assertFalse(pipeline_monitor.post_tokens("r", 1))
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v


if __name__ == "__main__":
    unittest.main()
