"""Il telefono: scripts/audit_viewport.cjs contro l'app, in un server locale.

Quattro pagine che coprono le forme del sito (home, scheda, regione, atlante),
a 390x844, 320x640 e 844x390 in contesto touch: niente scorrimento di lato,
barre ferme sotto il 25% dello schermo in verticale e il 35% in orizzontale,
controlli da 44 pixel, ancore sotto le barre, nessun errore JavaScript. Le
soglie e il perche' stanno nello script.

Serve Playwright per Node e un Chromium: dove mancano la prova si salta
dicendolo, come quella dei gradini con node. `PLAYWRIGHT_NODE_PATH` dice dove
cercare il modulo, se non e' fra quelli di Node.
"""

import os
import shutil
import subprocess
import threading
import unittest
from pathlib import Path

from werkzeug.serving import make_server

from app import app

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit_viewport.cjs"
PAGES = "/,/indicatore/tasso-di-turisticita/ter-105,/regione/campania,/atlante"


def _node_env() -> dict | None:
    if not shutil.which("node"):
        return None
    env = dict(os.environ)
    extra = os.environ.get("PLAYWRIGHT_NODE_PATH")
    if extra:
        env["NODE_PATH"] = os.pathsep.join(p for p in (extra, env.get("NODE_PATH")) if p)
    found = subprocess.run(["node", "-e", "require.resolve('playwright')"], env=env, capture_output=True)
    return env if found.returncode == 0 else None


NODE_ENV = _node_env()


@unittest.skipUnless(NODE_ENV, "Playwright per Node non c'e': l'audit del telefono non si puo' eseguire")
class IlTelefono(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server("127.0.0.1", 0, app, threaded=True)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_le_pagine_chiave_reggono_sul_telefono(self):
        done = subprocess.run(["node", str(SCRIPT), "--base", self.base, "--pagine", PAGES],
                              env=NODE_ENV, capture_output=True, text=True, timeout=900)
        if done.returncode == 2:
            self.skipTest(done.stderr.strip())
        self.assertEqual(done.returncode, 0, "\n" + done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
