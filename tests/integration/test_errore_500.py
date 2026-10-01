"""La pagina 500: in italiano, noindex, e un handler 500 che non solleva mai."""

import unittest
from unittest import mock

from werkzeug.exceptions import InternalServerError

from app import app

PAGINA = "/contatti"


def _guasto(*_args, **_kwargs):
    raise RuntimeError("guasto di prova")


def _client():
    # Senza questo il client di test rilancia l'eccezione invece di passarla
    # all'handler, e non proveremmo cio' che vede un visitatore.
    app.config["PROPAGATE_EXCEPTIONS"] = False
    return app.test_client()


class PaginaCinquecentoTest(unittest.TestCase):
    def setUp(self):
        self._propagate = app.config.get("PROPAGATE_EXCEPTIONS")
        self.addCleanup(app.config.__setitem__, "PROPAGATE_EXCEPTIONS", self._propagate)

    def _risposta(self, path=PAGINA, endpoint=None):
        client = _client()
        endpoint = endpoint or app.url_map.bind("localhost").match(path)[0]
        with mock.patch.dict(app.view_functions, {endpoint: _guasto}):
            with self.assertLogs(app.logger, level="ERROR"):
                return client.get(path)

    def test_un_errore_vero_da_la_pagina_italiana_con_il_sito_attorno(self):
        r = self._risposta()
        self.assertEqual(r.status_code, 500)
        html = r.get_data(as_text=True)
        self.assertIn('<html lang="it"', html)
        self.assertIn("Qualcosa non ha funzionato", html)
        self.assertIn('href="/"', html)
        self.assertIn('href="/ricerca"', html)
        self.assertIn("Riprova", html)
        # Testata e piede del sito, come la 404.
        self.assertIn("<header", html)
        self.assertIn("<footer", html)
        self.assertNotIn("Internal Server Error", html)

    def test_noindex_in_header_e_nel_markup(self):
        r = self._risposta()
        self.assertEqual(r.headers["X-Robots-Tag"], "noindex, follow")
        html = r.get_data(as_text=True)
        self.assertIn('<meta name="robots" content="noindex, follow">', html)
        self.assertEqual(html.count('name="robots"'), 1)
        self.assertNotIn('rel="canonical"', html)

    def test_abort_500_senza_eccezione_da_la_stessa_pagina(self):
        def _abort():
            raise InternalServerError()

        client = _client()
        with mock.patch.dict(app.view_functions, {"contatti": _abort}):
            r = client.get(PAGINA)
        self.assertEqual(r.status_code, 500)
        self.assertIn("Qualcosa non ha funzionato", r.get_data(as_text=True))

    def test_se_il_template_solleva_resta_un_testo_italiano_500(self):
        client = _client()
        reale = app.jinja_env.get_or_select_template

        def _rotto(name, *a, **k):
            if name == "500.html":
                raise RuntimeError("template rotto")
            return reale(name, *a, **k)

        with mock.patch.dict(app.view_functions, {"contatti": _guasto}):
            with mock.patch.object(app.jinja_env, "get_or_select_template", _rotto):
                with self.assertLogs(app.logger, level="ERROR") as log:
                    r = client.get(PAGINA)
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.mimetype, "text/plain")
        testo = r.get_data(as_text=True)
        self.assertIn("Riprova", testo)
        self.assertIn("home", testo)
        self.assertNotIn("Internal Server Error", testo)
        self.assertEqual(r.headers["X-Robots-Tag"], "noindex, follow")
        self.assertTrue(any("handler 500" in m for m in log.output))

    def test_sotto_api_resta_json(self):
        client = _client()
        endpoint = app.url_map.bind("localhost").match("/api/favorites")[0]
        with mock.patch.dict(app.view_functions, {endpoint: _guasto}):
            with self.assertLogs(app.logger, level="ERROR"):
                r = client.get("/api/favorites")
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.get_json(), {"error": "internal_error"})
        self.assertIn("noindex", r.headers["X-Robots-Tag"])

    def test_atlante_con_la_vista_guasta_resta_500_e_porta_la_pagina_nuova(self):
        r = self._risposta("/atlante")
        self.assertEqual(r.status_code, 500)
        self.assertIn("Qualcosa non ha funzionato", r.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
