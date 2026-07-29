"""Lo store vivo del cruscotto: battiti e PR aperte, con la loro scadenza.

Non e' la rotta (quella la prova test_pipeline_dashboard_route): qui si prova lo
store da solo, in particolare che una sessione caduta senza chiudere non resti in
pagina per sempre (la soglia dei battiti su file, riportata sul SQLite)."""

import tempfile
import unittest
from pathlib import Path

from app import config, pipeline_state


class PipelineStateStore(unittest.TestCase):
    def setUp(self):
        self._saved = config.LEADERBOARD_DB
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        config.LEADERBOARD_DB = str(Path(self._tmp.name) / "state.sqlite3")

    def tearDown(self):
        config.LEADERBOARD_DB = self._saved

    def test_a_fresh_beat_is_live_a_stale_one_is_not(self):
        pipeline_state.record_beat("r-fresh", role="producer", indicator="ter-1",
                                   now="2026-07-29T12:00:00+00:00")
        pipeline_state.record_beat("r-old", role="producer", indicator="ter-2",
                                   now="2026-07-29T00:00:00+00:00")
        live = pipeline_state.live(now="2026-07-29T12:01:00+00:00", stale_hours=6)
        ids = [b["indicator"] for b in live["beats"]]
        self.assertIn("ter-1", ids)      # 1 minuto fa
        self.assertNotIn("ter-2", ids)   # 12 ore fa, oltre la soglia

    def test_close_removes_a_beat(self):
        pipeline_state.record_beat("r-1", role="producer", indicator="ter-9",
                                   now="2026-07-29T12:00:00+00:00")
        pipeline_state.close_beat("r-1")
        live = pipeline_state.live(now="2026-07-29T12:00:30+00:00")
        self.assertEqual(live["beats"], [])

    def test_replace_prs_is_a_full_swap(self):
        pipeline_state.replace_prs(
            [{"pr": 1, "branch": "automation/a-b", "ci": "verde"}],
            now="2026-07-29T12:00:00+00:00")
        pipeline_state.replace_prs(
            [{"pr": 2, "branch": "automation/a-c", "ci": "rossa"}],
            now="2026-07-29T12:00:05+00:00")
        live = pipeline_state.live(now="2026-07-29T12:00:10+00:00")
        self.assertEqual([p["pr"] for p in live["prs"]], [2])

    def test_a_beat_upsert_replaces_the_previous_one(self):
        pipeline_state.record_beat("r-1", role="producer", indicator="ter-a",
                                   now="2026-07-29T12:00:00+00:00")
        pipeline_state.record_beat("r-1", role="producer", indicator="ter-b",
                                   now="2026-07-29T12:00:10+00:00")
        live = pipeline_state.live(now="2026-07-29T12:00:20+00:00")
        self.assertEqual([b["indicator"] for b in live["beats"]], ["ter-b"])

    def test_beats_and_prs_are_separated(self):
        pipeline_state.record_beat("r-1", role="producer", indicator="ter-a",
                                   now="2026-07-29T12:00:00+00:00")
        pipeline_state.replace_prs([{"pr": 5, "branch": "automation/a-b"}],
                                   now="2026-07-29T12:00:00+00:00")
        live = pipeline_state.live(now="2026-07-29T12:00:10+00:00")
        self.assertEqual(len(live["beats"]), 1)
        self.assertEqual(len(live["prs"]), 1)


if __name__ == "__main__":
    unittest.main()
