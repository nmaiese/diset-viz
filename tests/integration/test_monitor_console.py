"""La console di monitoraggio e il keep-alive (Fase 4).

La console non e' gated da un segreto in URL: la serve a chiunque (noindex), ma
la vera guardia e' la RLS su Postgres, che senza la mail admin nel JWT non
restituisce righe. Qui si prova solo il guscio (rotta, noindex, redirect del
sottodominio) e che il keep-alive risponda sempre 200."""

import unittest

from app import app


class MonitorConsoleTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_console_renders_and_is_noindex(self):
        r = self.client.get("/_pipeline/console")
        self.assertEqual(r.status_code, 200)
        self.assertIn("noindex", r.headers.get("X-Robots-Tag", ""))
        self.assertIn(b"monitor-root", r.data)
        self.assertIn(b"monitor.js", r.data)

    def test_keepalive_is_ok_and_noindex(self):
        r = self.client.get("/_keepalive")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["ok"])
        self.assertIn("noindex", r.headers.get("X-Robots-Tag", ""))

    def test_monitor_subdomain_root_redirects_to_console(self):
        r = self.client.get("/", headers={"Host": "monitor.divarioitalia.it"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.headers["Location"].endswith("/_pipeline/console"))

    def test_apex_root_is_not_redirected_to_console(self):
        r = self.client.get("/", headers={"Host": "divarioitalia.it"})
        self.assertEqual(r.status_code, 200)


if __name__ == "__main__":
    unittest.main()
