"""Il monitoraggio: la vista di lettura sul dossier per-indicatore.

Nucleo puro (`board`, `headline`): ogni test costruisce un dossier sintetico,
senza toccare il disco. I battiti si provano su una cartella temporanea, con
`now` iniettato cosi' la staleness e' deterministica."""

import tempfile
import unittest

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

    def test_recent_history_is_newest_first_and_capped(self):
        runs = [{"at": f"2026-07-{d:02d}T09:00:00+00:00", "stage": "writer",
                 "outcome": "merged", "summary": f"run {d}", "run_id": f"r{d}"}
                for d in range(1, 20)]
        b = pipeline_monitor.board({}, runs=runs, today=self.TODAY, recent=5)
        self.assertEqual(len(b["recent"]), 5)
        self.assertEqual(b["recent"][0]["run_id"], "r19")  # il piu' recente


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


if __name__ == "__main__":
    unittest.main()
