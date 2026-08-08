"""La rotta /_pipeline: il cruscotto interno, protetto e noindex, e il suo vivo.

Gira il client Flask reale, quindi è un test d'integrazione: costruisce il
board dai file veri del repo. Verifica lo stato, l'header noindex, la protezione
a token, e l'endpoint di ingest dei battiti (il vivo, scritto sul backend
mutabile: SQLite in test, Supabase Postgres in produzione) con il suo segreto."""

import importlib
import json
import os
import tempfile
import unittest
from pathlib import Path


class PipelineDashboardRoute(unittest.TestCase):
    def setUp(self):
        # Il client va costruito con l'ambiente voluto: ricarico config e views
        # così la view legge i token di questo test, non quelli del processo.
        # Salvo e ripristino l'ambiente per non sporcare gli altri test.
        self._saved = {k: os.environ.get(k) for k in
                       ("PIPELINE_TOKEN", "PIPELINE_INGEST_TOKEN", "LEADERBOARD_DB")}
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        # Il vivo vive nello stesso SQLite della leaderboard: un DB temporaneo,
        # così il test non tocca (né dipende da) quello reale.
        os.environ["LEADERBOARD_DB"] = str(Path(self._tmp.name) / "state.sqlite3")

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._reload()

    def _reload(self):
        from app import config
        importlib.reload(config)
        from app import views
        views.config = config
        from app import pipeline_state
        pipeline_state.config = config
        return config

    def _client(self, token="", ingest_token=""):
        os.environ.pop("PIPELINE_TOKEN", None)
        os.environ.pop("PIPELINE_INGEST_TOKEN", None)
        if token:
            os.environ["PIPELINE_TOKEN"] = token
        if ingest_token:
            os.environ["PIPELINE_INGEST_TOKEN"] = ingest_token
        self._reload()
        from app import app
        return app.test_client()

    # --- il cruscotto ---------------------------------------------------------

    def test_open_when_no_token_is_configured(self):
        r = self._client().get("/_pipeline")
        self.assertEqual(r.status_code, 200)

    def test_is_noindex(self):
        r = self._client().get("/_pipeline")
        self.assertIn("noindex", r.headers.get("X-Robots-Tag", ""))

    def test_it_shows_the_headline_and_the_chain_state(self):
        body = self._client().get("/_pipeline").get_data(as_text=True)
        self.assertIn("headline", body)
        self.assertIn("Catena editoriale", body)
        self.assertTrue(any(s in body for s in
                            ("bloccat", "pronti al lavoro", "in pari")))

    def test_it_shows_the_per_indicator_explorer_with_run_history(self):
        body = self._client().get("/_pipeline").get_data(as_text=True)
        # la sezione esaustiva per-indicatore, il filtro e le colonne del dettaglio
        self.assertIn("Tutti gli indicatori", body)
        self.assertIn("filtraIndicatori", body)
        self.assertIn("cosa ha fatto l'agente", body)
        self.assertIn('details class="ind"', body)

    def test_it_exposes_the_whole_indicator_journey_and_next_action(self):
        body = self._client().get("/_pipeline").get_data(as_text=True)
        self.assertIn("Il flusso completo", body)
        self.assertIn("Ammissione", body)
        self.assertIn("Produzione", body)
        self.assertIn("Verifica", body)
        self.assertIn("Pubblicazione", body)
        self.assertIn("Prossima azione", body)
        self.assertIn("Percorso completo", body)
        self.assertIn("Attività più recente", body)

    def test_it_shows_readable_indicator_names_not_only_internal_ids(self):
        body = self._client().get("/_pipeline").get_data(as_text=True)
        self.assertIn("Produttività del lavoro in agricoltura", body)
        self.assertIn('data-id="1"', body)

    def test_a_published_indicator_links_to_its_page(self):
        # Costruito dai file veri: se un indicatore risulta pubblicato sul sito,
        # la sua riga porta il link canonico alla pagina; se nessuno lo è, il
        # test non ha nulla da provare e passa (lo stato di pubblicazione è dato
        # vivo, non un invariante del repo).
        from scripts import pipeline_monitor
        rows = pipeline_monitor.load_board()["rows"]
        published = [r for r in rows if r.get("published") is True]
        if not published:
            self.skipTest("nessun indicatore risulta pubblicato sul sito ora")
        body = self._client().get("/_pipeline").get_data(as_text=True)
        self.assertIn("pagina pubblicata", body)
        self.assertIn("/indicatore/", body)

    def test_a_token_locks_it(self):
        client = self._client(token="segreto123")
        self.assertEqual(client.get("/_pipeline").status_code, 404)
        self.assertEqual(client.get("/_pipeline?token=sbagliato").status_code, 404)
        self.assertEqual(client.get("/_pipeline?token=segreto123").status_code, 200)

    # --- l'ingest dei battiti (il vivo) --------------------------------------

    def test_ingest_needs_the_secret(self):
        client = self._client(ingest_token="ingest-xyz")
        payload = {"action": "beat", "run_id": "producer-1", "role": "producer",
                   "indicator": "ter-999"}
        # senza header, o con header sbagliato: 404, non 403 (non conferma di esistere)
        self.assertEqual(client.post("/_pipeline/beat", json=payload).status_code, 404)
        self.assertEqual(
            client.post("/_pipeline/beat", json=payload,
                        headers={"X-Pipeline-Key": "sbagliato"}).status_code, 404)
        ok = client.post("/_pipeline/beat", json=payload,
                         headers={"X-Pipeline-Key": "ingest-xyz"})
        self.assertEqual(ok.status_code, 200)

    def test_ingest_is_off_when_no_secret_is_configured(self):
        # Senza segreto l'endpoint è 404 anche con un header qualsiasi: in locale
        # e finché il segreto non è provisionato, l'ingest è semplicemente spento.
        client = self._client(ingest_token="")
        r = client.post("/_pipeline/beat", json={"action": "beat", "run_id": "x"},
                        headers={"X-Pipeline-Key": "qualsiasi"})
        self.assertEqual(r.status_code, 404)

    def test_a_beat_then_a_pr_snapshot_show_up_on_the_dashboard(self):
        client = self._client(ingest_token="ingest-xyz")
        hdr = {"X-Pipeline-Key": "ingest-xyz"}
        client.post("/_pipeline/beat", headers=hdr, json={
            "action": "beat", "run_id": "producer-20260729T101010Z-abcd",
            "role": "producer", "indicator": "ter-777", "stage": "producer"})
        client.post("/_pipeline/beat", headers=hdr, json={
            "action": "prs", "prs": [{
                "pr": 321, "branch": "automation/producer-2026-07-29-abcd",
                "run_id": "producer-20260729T101010Z-abcd", "role": "producer",
                "ci": "rossa", "mergeable": "no", "title": "produttore ter-777"}]})
        body = client.get("/_pipeline").get_data(as_text=True)
        self.assertIn("ter-777", body)      # il battito in volo
        self.assertIn("#321", body)          # la PR aperta
        self.assertIn("rossa", body)         # lo stato CI

    def test_closing_a_beat_removes_it(self):
        client = self._client(ingest_token="ingest-xyz")
        hdr = {"X-Pipeline-Key": "ingest-xyz"}
        client.post("/_pipeline/beat", headers=hdr, json={
            "action": "beat", "run_id": "r-1", "role": "producer", "indicator": "ter-888"})
        self.assertIn("ter-888", client.get("/_pipeline").get_data(as_text=True))
        client.post("/_pipeline/beat", headers=hdr, json={"action": "close", "run_id": "r-1"})
        self.assertNotIn("ter-888", client.get("/_pipeline").get_data(as_text=True))

    def test_tokens_are_stored_durably_and_gated_by_the_secret(self):
        client = self._client(ingest_token="ingest-xyz")
        from app import pipeline_state
        # segreto sbagliato -> 404, come i battiti
        self.assertEqual(
            client.post("/_pipeline/beat", json={"action": "tokens", "run_id": "r", "tokens": 9},
                        headers={"X-Pipeline-Key": "sbagliato"}).status_code, 404)
        # col segreto giusto scrive
        ok = client.post("/_pipeline/beat", headers={"X-Pipeline-Key": "ingest-xyz"},
                         json={"action": "tokens", "run_id": "producer-1", "tokens": 46121,
                               "indicator": "ter-178", "stage": "producer"})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(pipeline_state.tokens_by_run()["producer-1"]["tokens"], 46121)
        # e un token vecchio NON scade come un battito: la telemetria è storia
        pipeline_state.record_tokens("producer-old", 12345, now="2026-01-01T00:00:00+00:00")
        self.assertEqual(pipeline_state.tokens_by_run()["producer-old"]["tokens"], 12345)

    def test_tokens_show_up_per_step_on_the_dashboard(self):
        client = self._client(ingest_token="ingest-xyz")
        from scripts import pipeline_monitor
        from app import pipeline_state
        # un run_id reale dalla storia di un indicatore committato, col suo
        # bersaglio: i token si attribuiscono solo dove il record combacia.
        target, run_id = None, None
        for row in pipeline_monitor.load_board()["rows"]:
            if row.get("runs"):
                target, run_id = row["id"], row["runs"][0]["run_id"]
                break
        if not run_id:
            self.skipTest("nessuna run nel dossier committato")
        pipeline_state.record_tokens(run_id, 46121, indicator=target, stage="producer")
        body = client.get("/_pipeline").get_data(as_text=True)
        self.assertIn("46,121", body)   # formattato coi separatori delle migliaia

    def test_a_bad_action_is_a_clean_400(self):
        client = self._client(ingest_token="ingest-xyz")
        r = client.post("/_pipeline/beat", headers={"X-Pipeline-Key": "ingest-xyz"},
                        json={"action": "boh"})
        self.assertEqual(r.status_code, 400)

    def test_an_outcome_is_stored_durably_and_gated_by_the_secret(self):
        client = self._client(ingest_token="ingest-xyz")
        from app import pipeline_state
        payload = {"action": "outcome", "indicator": "167",
                   "run_id": "verificatore-r1", "at": "2026-08-04T14:00:00+00:00",
                   "state": "pubblicata", "published": True,
                   "completed_stages": ["writer", "reviewer", "verificatore"],
                   "flags": {"article_complete": True}}
        # segreto sbagliato -> 404, come i battiti
        self.assertEqual(
            client.post("/_pipeline/beat", json=payload,
                        headers={"X-Pipeline-Key": "sbagliato"}).status_code, 404)
        # col segreto giusto scrive, e si rilegge deserializzato
        ok = client.post("/_pipeline/beat", json=payload,
                         headers={"X-Pipeline-Key": "ingest-xyz"})
        self.assertEqual(ok.status_code, 200)
        got = pipeline_state.outcomes_by_indicator()["167"]
        self.assertEqual(got["state"], "pubblicata")
        self.assertEqual(got["completed_stages"], ["writer", "reviewer", "verificatore"])
        # un outcome vecchio NON scade come un battito: è storia finché il
        # committato non lo raggiunge.
        pipeline_state.record_outcome("999", "r-old", {"state": "pubblicata"},
                                      now="2026-01-01T00:00:00+00:00",
                                      at="2026-01-01T00:00:00+00:00")
        self.assertIn("999", pipeline_state.outcomes_by_indicator())

    def test_an_outcome_without_the_indicator_is_a_clean_400(self):
        client = self._client(ingest_token="ingest-xyz")
        r = client.post("/_pipeline/beat", headers={"X-Pipeline-Key": "ingest-xyz"},
                        json={"action": "outcome", "run_id": "r1"})   # manca indicator
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
