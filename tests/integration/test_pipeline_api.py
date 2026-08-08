"""I due endpoint JSON della dashboard nella console: catalogo e cronologia.

Il calcolo sotto (`load_board`, `runs_timeline`) è già coperto altrove; qui si
prova solo il wrapper authed. Il confine è la mail admin: anonimo e non-admin
vedono un 404 (non 403: un endpoint interno non conferma di esistere), l'admin
vede la shape attesa.

Il test che conta è `test_admin_then_anonymous`: è la rete contro chi un domani
rimettesse `@cache.cached` sulla view, che corto-circuiterebbe il corpo su un hit
di cache e servirebbe il dato all'anonimo. Verifica che l'auth gira sempre prima
del calcolo, qualunque sia il backend di cache (qui NullCache), mockando l'helper
del payload: l'anonimo non deve mai raggiungerlo."""

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import jwt

from app import app, config

_SECRET = "test-jwt-secret"
_ADMIN = "boss@example.com"


def _token(email, sub="uuid-x"):
    payload = {"sub": sub, "email": email, "aud": "authenticated",
               "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    return jwt.encode(payload, _SECRET, algorithm="HS256")


class PipelineApiAuthTest(unittest.TestCase):
    def setUp(self):
        self._saved = (config.SUPABASE_JWT_SECRET, config.SUPABASE_URL,
                       config.MONITOR_ADMIN_EMAIL)
        config.SUPABASE_JWT_SECRET = _SECRET
        config.SUPABASE_URL = ""
        config.MONITOR_ADMIN_EMAIL = _ADMIN

    def tearDown(self):
        (config.SUPABASE_JWT_SECRET, config.SUPABASE_URL,
         config.MONITOR_ADMIN_EMAIL) = self._saved

    def _admin_headers(self):
        return {"Authorization": "Bearer " + _token(_ADMIN)}

    # --- il confine mail-admin, su entrambi gli endpoint ---------------------

    def test_anonymous_is_404(self):
        c = app.test_client()
        self.assertEqual(c.get("/_pipeline/api/board").status_code, 404)
        self.assertEqual(c.get("/_pipeline/api/runs").status_code, 404)

    def test_non_admin_is_404(self):
        c = app.test_client()
        h = {"Authorization": "Bearer " + _token("other@example.com")}
        self.assertEqual(c.get("/_pipeline/api/board", headers=h).status_code, 404)
        self.assertEqual(c.get("/_pipeline/api/runs", headers=h).status_code, 404)

    def test_board_admin_shape(self):
        r = app.test_client().get("/_pipeline/api/board", headers=self._admin_headers())
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        for key in ("rows", "totals", "phase_totals", "metrics", "headline"):
            self.assertIn(key, data)
        self.assertIsInstance(data["rows"], list)

    def test_runs_admin_shape(self):
        r = app.test_client().get("/_pipeline/api/runs", headers=self._admin_headers())
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn("runs", data)
        self.assertIn("totals", data)
        self.assertIsInstance(data["runs"], list)
        for key in ("tokens_by_stage", "tokens_by_indicator", "runs_by_outcome",
                    "tokens_by_day"):
            self.assertIn(key, data["totals"])

    def test_noindex_header_on_json(self):
        # Prefisso /_pipeline: l'after_request timbra noindex anche sul JSON, non
        # l'"index, follow" di default.
        r = app.test_client().get("/_pipeline/api/board", headers=self._admin_headers())
        self.assertIn("noindex", r.headers.get("X-Robots-Tag", ""))

    # --- la rete contro il buco di cache -------------------------------------

    def test_admin_then_anonymous(self):
        """Un admin scalda il payload, l'anonimo che segue resta 404 e non tocca
        mai l'helper. Con `@cache.cached` sulla view questo cadrebbe."""
        with mock.patch("app.views._pipeline_board_payload",
                        return_value={"rows": [], "totals": {}}) as payload:
            c = app.test_client()
            self.assertEqual(c.get("/_pipeline/api/board",
                                   headers=self._admin_headers()).status_code, 200)
            payload.assert_called()
            payload.reset_mock()
            self.assertEqual(c.get("/_pipeline/api/board").status_code, 404)
            payload.assert_not_called()


class PipelineApiLiveOverlay(unittest.TestCase):
    """L'overlay vivo (gli snapshot che gli agenti POSTano al merge) si riflette
    sul catalogo senza redeploy, e si ritira quando il committato lo raggiunge."""

    def setUp(self):
        self._saved = (config.SUPABASE_JWT_SECRET, config.SUPABASE_URL,
                       config.MONITOR_ADMIN_EMAIL, config.LEADERBOARD_DB)
        config.SUPABASE_JWT_SECRET = _SECRET
        config.SUPABASE_URL = ""
        config.MONITOR_ADMIN_EMAIL = _ADMIN
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        config.LEADERBOARD_DB = str(Path(self._tmp.name) / "state.sqlite3")

    def tearDown(self):
        (config.SUPABASE_JWT_SECRET, config.SUPABASE_URL,
         config.MONITOR_ADMIN_EMAIL, config.LEADERBOARD_DB) = self._saved

    def _admin_headers(self):
        return {"Authorization": "Bearer " + _token(_ADMIN)}

    def test_a_live_outcome_shows_on_the_board_without_a_deploy(self):
        from app import pipeline_state
        from app.cache import cache
        from scripts import pipeline_monitor
        # `_pipeline_board_payload` è memoizzato (30s): azzero così la richiesta
        # ricalcola sul DB di questo test e non su un payload scaldato altrove.
        cache.clear()
        # un indicatore reale che il committato NON dà ancora pubblicato
        target = next((r for r in pipeline_monitor.load_board()["rows"]
                       if r.get("published") is not True and r.get("id")), None)
        self.assertIsNotNone(target)
        tid = target["id"]
        pipeline_state.record_outcome(tid, "outcome-int-r1", {
            "state": "pubblicata", "published": True, "verification_valid": True,
            "completed_stages": ["writer", "reviewer", "verificatore"],
            "required_stages": ["writer", "reviewer", "verificatore"],
            "flags": {"article_complete": True}}, at="2026-08-04T14:00:00+00:00")
        r = app.test_client().get("/_pipeline/api/board", headers=self._admin_headers())
        self.assertEqual(r.status_code, 200)
        rows = {row["id"]: row for row in r.get_json()["rows"]}
        self.assertIs(rows[tid]["published"], True)
        self.assertEqual(rows[tid]["state"], "pubblicata")

    def test_an_outcome_already_committed_is_reconciled_away(self):
        from app import pipeline_state
        from scripts import pipeline_monitor
        row = next((r for r in pipeline_monitor.load_board()["rows"]
                    if r.get("runs")), None)
        if not row:
            self.skipTest("nessuna run nel dossier committato")
        tid, run_id, committed_state = row["id"], row["runs"][0]["run_id"], row["state"]
        # un outcome con QUEL run_id (già su master) e uno stato diverso: ignorato.
        pipeline_state.record_outcome(tid, run_id, {"state": "in-quarantena"},
                                      at="2026-08-04T14:00:00+00:00")
        rows = {r["id"]: r for r in pipeline_monitor.load_board(
            outcomes=pipeline_state.outcomes_by_indicator())["rows"]}
        self.assertEqual(rows[tid]["state"], committed_state)


if __name__ == "__main__":
    unittest.main()
