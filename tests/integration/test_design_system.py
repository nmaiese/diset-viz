"""La migrazione al design system 2026, e i due modi in cui puo' rompersi.

Non sorveglia l'aspetto, che non e' cosa da test: sorveglia le due invarianti
che, saltando, non fanno fallire niente e si vedono solo aprendo il sito.

1. **Le due shell dell'atlante si migrano insieme.** `app.html` e
   `confronto.html` montano lo STESSO bundle React. Se una delle due perde
   `class="ds"` o il foglio del design system, la stessa applicazione si vede in
   due palette diverse a seconda della URL da cui la si apre, e nessuna pagina
   e' rotta abbastanza da accorgersene.

2. **La migrazione resta opt-in.** Una pagina non ancora migrata deve restare
   esattamente com'era. Il modo silenzioso di sbagliare e' il contrario di
   quello che si teme: non "la pagina nuova non e' migrata", ma "il chrome
   nuovo e' finito addosso a venti pagine che nessuno ha guardato".
"""
import re
import unittest

from app import app
from app.cache import cache


# Le shell che montano il bundle dell'atlante. Se se ne aggiunge una terza va
# aggiunta qui, ed e' il punto: la lista e' il contratto.
SPA_ROUTES = ("/atlante", "/confronto")

# Pagine gia' migrate, e pagine che devono restare sul chrome legacy.
MIGRATED = ("/", "/atlante", "/confronto",
            "/indicatore/adulti-che-partecipano-all-apprendimento-permanente-totale/ter-99")
LEGACY = ("/blog", "/regioni", "/temi", "/metodologia", "/qualita-della-vita")


class DesignSystemMigration(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        cache.clear()

    def _html(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, path)
        return response.get_data(as_text=True)

    # --- 1. le shell dell'atlante -----------------------------------------
    def test_every_spa_shell_is_migrated_together(self):
        for path in SPA_ROUTES:
            with self.subTest(path=path):
                html = self._html(path)
                self.assertRegex(html, r'<body[^>]*class="[^"]*\bds\b',
                                 f"{path}: manca class=ds sul body")
                self.assertIn("css/ds/system.css", html,
                              f"{path}: manca il foglio del design system")

    def test_no_spa_shell_is_left_behind(self):
        # Il bundle si monta solo dalle shell dichiarate sopra. Una terza shell
        # aggiunta senza migrarla e' il modo in cui l'invariante 1 si rompe.
        import pathlib
        templates = pathlib.Path(app.root_path) / "templates"
        mounting = sorted(
            p.name for p in templates.glob("*.html")
            if "dist/assets/index.js" in p.read_text(encoding="utf-8")
        )
        self.assertEqual(mounting, ["app.html", "confronto.html"],
                         "una shell monta l'atlante ma non e' fra quelle sorvegliate")

    def test_the_spa_shells_carry_the_2026_fonts(self):
        for path in SPA_ROUTES:
            with self.subTest(path=path):
                html = self._html(path)
                self.assertIn("Newsreader", html)
                self.assertNotIn("family=Archivo", html,
                                 f"{path}: carica ancora i font legacy")

    # --- 2. l'opt-in ------------------------------------------------------
    def test_migrated_pages_declare_the_design_system(self):
        for path in MIGRATED:
            with self.subTest(path=path):
                self.assertRegex(self._html(path), r'<body[^>]*class="[^"]*\bds\b')

    def test_unmigrated_pages_are_untouched(self):
        for path in LEGACY:
            with self.subTest(path=path):
                html = self._html(path)
                self.assertNotRegex(html, r'<body[^>]*class="[^"]*\bds\b',
                                    f"{path} non e' migrata ma ha il chrome nuovo")
                # Il chrome legacy e' ancora quello che serve la pagina.
                self.assertIn("masthead", html, f"{path}: manca il chrome legacy")

    # --- la rampa dei dati -------------------------------------------------
    def test_the_indicator_map_uses_the_design_system_ramp(self):
        """La mappa deve essere dipinta con `var(--seq-N)`, non con un colore
        cotto: `--seq-1..6` sono ridefinite nel tema scuro, e un hex nel markup
        lascerebbe la mappa sulla rampa chiara con il resto della pagina scuro.
        """
        html = self._html(
            "/indicatore/adulti-che-partecipano-all-apprendimento-permanente-totale/ter-99"
        )
        fills = re.findall(r'\.indicator-map \[data-key="[^"]+"\]\{fill:([^}]+)\}', html)
        self.assertTrue(fills, "la mappa dell'indicatore non dipinge nessuna regione")
        for fill in fills:
            self.assertRegex(fill.strip(), r"^var\(--seq-[1-6]\)$",
                             f"colore fuori dalla rampa del design system: {fill}")

    def test_the_legacy_blue_ramp_is_gone_from_the_migrated_pages(self):
        # `#15233b` era il navy dell'identita' vecchia. Sopravvive solo nelle
        # pagine non migrate, mai in quelle che dichiarano il design system.
        for path in MIGRATED:
            with self.subTest(path=path):
                self.assertNotIn("#15233b", self._html(path).lower())


if __name__ == "__main__":
    unittest.main()
