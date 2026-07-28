"""La rotta /_pipeline: il cruscotto interno, protetto e noindex.

Gira il client Flask reale, quindi e' un test d'integrazione: costruisce il
board dai file veri del repo. Verifica lo stato, l'header noindex e la
protezione a token."""

import importlib
import os
import unittest


class PipelineDashboardRoute(unittest.TestCase):
    def setUp(self):
        # Il client va costruito con l'ambiente voluto: ricarico config e views
        # cosi' la view legge il PIPELINE_TOKEN di questo test, non quello del
        # processo. Salvo e ripristino l'ambiente per non sporcare gli altri test.
        self._saved = os.environ.get("PIPELINE_TOKEN")

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("PIPELINE_TOKEN", None)
        else:
            os.environ["PIPELINE_TOKEN"] = self._saved
        from app import config
        importlib.reload(config)
        from app import views
        views.config = config

    def _client(self, token=""):
        if token:
            os.environ["PIPELINE_TOKEN"] = token
        else:
            os.environ.pop("PIPELINE_TOKEN", None)
        from app import config
        importlib.reload(config)
        from app import views
        views.config = config
        from app import app
        return app.test_client()

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
        # la frase in testa e' una delle tre forme note
        self.assertTrue(any(s in body for s in
                            ("bloccat", "pronti al lavoro", "in pari")))

    def test_a_token_locks_it(self):
        client = self._client(token="segreto123")
        self.assertEqual(client.get("/_pipeline").status_code, 404)
        self.assertEqual(client.get("/_pipeline?token=sbagliato").status_code, 404)
        self.assertEqual(client.get("/_pipeline?token=segreto123").status_code, 200)


if __name__ == "__main__":
    unittest.main()
