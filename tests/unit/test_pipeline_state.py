"""Lo store vivo del cruscotto: battiti e PR aperte, con la loro scadenza.

Non è la rotta (quella la prova test_pipeline_dashboard_route): qui si prova lo
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


class PipelineOutcomeStore(unittest.TestCase):
    """Lo snapshot di stato per indicatore: durevole (non scade), l'ultimo vince,
    ma uno più vecchio non sovrascrive uno più recente."""

    def setUp(self):
        self._saved = config.LEADERBOARD_DB
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        config.LEADERBOARD_DB = str(Path(self._tmp.name) / "state.sqlite3")

    def tearDown(self):
        config.LEADERBOARD_DB = self._saved

    def _snap(self, **over):
        snap = {"state": "pubblicata", "type": "esistente", "entered_at": "2026-07-01",
                "completed_stages": ["writer", "reviewer", "verificatore"],
                "required_stages": ["writer", "reviewer", "verificatore"],
                "flags": {"article_complete": True, "vintage": 2023},
                "published": True, "verification_valid": True,
                "score_eligible": True, "error_class": None, "motivo": "",
                "priority": 20.0}
        snap.update(over)
        return snap

    def test_roundtrip_deserializes_structures_and_tristate(self):
        pipeline_state.record_outcome("167", "verificatore-x", self._snap(),
                                      at="2026-08-04T14:00:00+00:00")
        got = pipeline_state.outcomes_by_indicator()["167"]
        self.assertEqual(got["state"], "pubblicata")
        self.assertEqual(got["completed_stages"], ["writer", "reviewer", "verificatore"])
        self.assertEqual(got["flags"], {"article_complete": True, "vintage": 2023})
        self.assertIs(got["published"], True)
        self.assertIs(got["verification_valid"], True)
        self.assertEqual(got["priority"], 20.0)
        self.assertEqual(got["run_id"], "verificatore-x")

    def test_last_write_wins_on_the_same_indicator(self):
        pipeline_state.record_outcome("167", "r1", self._snap(state="in-lavorazione"),
                                      at="2026-08-04T14:00:00+00:00")
        pipeline_state.record_outcome("167", "r2", self._snap(state="pubblicata"),
                                      at="2026-08-04T15:00:00+00:00")
        self.assertEqual(pipeline_state.outcomes_by_indicator()["167"]["state"],
                         "pubblicata")

    def test_an_older_snapshot_does_not_clobber_a_newer_one(self):
        pipeline_state.record_outcome("167", "r2", self._snap(state="pubblicata"),
                                      at="2026-08-04T15:00:00+00:00")
        pipeline_state.record_outcome("167", "r1", self._snap(state="in-lavorazione"),
                                      at="2026-08-04T14:00:00+00:00")   # arriva dopo, ma più vecchio
        self.assertEqual(pipeline_state.outcomes_by_indicator()["167"]["state"],
                         "pubblicata")

    def test_a_missing_table_is_an_empty_map(self):
        # Nessuna scrittura, nessuna tabella creata: la board non deve cadere.
        self.assertEqual(pipeline_state.outcomes_by_indicator(), {})

    def test_an_outcome_is_durable_and_does_not_expire(self):
        pipeline_state.record_outcome("167", "r1", self._snap(),
                                      at="2026-01-01T00:00:00+00:00",
                                      now="2026-01-01T00:00:00+00:00")
        # mesi dopo, senza finestra di freschezza: ancora presente.
        self.assertIn("167", pipeline_state.outcomes_by_indicator())

    def test_a_missing_indicator_is_a_value_error(self):
        with self.assertRaises(ValueError):
            pipeline_state.record_outcome("", "r1", self._snap())

    def test_a_non_numeric_priority_degrades_to_zero(self):
        # Una riga con `priority` non numerica non deve zittire l'intera mappa.
        pipeline_state.record_outcome("167", "r1", self._snap(priority="non-numerica"))
        self.assertEqual(pipeline_state.outcomes_by_indicator()["167"]["priority"], 0.0)

    def test_a_tristate_none_survives_the_roundtrip(self):
        pipeline_state.record_outcome("999", "r1",
                                      self._snap(published=None, verification_valid=None))
        got = pipeline_state.outcomes_by_indicator()["999"]
        self.assertIsNone(got["published"])
        self.assertIsNone(got["verification_valid"])


if __name__ == "__main__":
    unittest.main()
