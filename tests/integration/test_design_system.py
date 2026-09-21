"""Il design system 2026, e i tre modi in cui puo' tornare indietro.

Non sorveglia l'aspetto, che non e' cosa da test: sorveglia le invarianti che,
saltando, non fanno fallire niente e si vedono solo aprendo il sito.

1. **Le due shell dell'atlante si migrano insieme.** `app.html` e
   `confronto.html` montano lo STESSO bundle React. Se una delle due perde
   `class="ds"` o il foglio del design system, la stessa applicazione si vede in
   due palette diverse a seconda della URL da cui la si apre, e nessuna pagina
   e' rotta abbastanza da accorgersene.

2. **Il chrome vecchio non torna.** Finche' i due sistemi convivevano, questo
   file sorvegliava il confine: che il chrome nuovo non debordasse sulle pagine
   non ancora migrate. Quel confine non esiste piu' e la domanda si e'
   rovesciata, perche' ora il guasto e' il ritorno del masthead legacy, non la
   sua sopravvivenza.

3. **La rampa dei dati resta `var(--seq-N)`.** Un colore cotto nel markup non
   segue il tema scuro: lascia la mappa sulla scala chiara mentre il resto
   della pagina e' scuro, e nessuna pagina risulta rotta.

Le shell della SPA restano fuori dai controlli sul markup del chrome: hanno un
masthead React proprio, che porta la navigazione dentro l'applicazione senza
ricaricare. Con le altre pagine devono condividere il design system, non l'HTML.
"""
import re
import unittest

from app import app
from app.cache import cache


# Le shell che montano il bundle dell'atlante. Se se ne aggiunge una terza va
# aggiunta qui, ed e' il punto: la lista e' il contratto.
SPA_ROUTES = ("/atlante", "/confronto")

# Un campione di ogni famiglia di pagina servita da Jinja, cioe' quelle che
# condividono `_ds_header.html`.
JINJA_PAGES = ("/", "/blog", "/regioni", "/temi", "/metodologia",
               "/qualita-della-vita", "/quiz", "/ricerca?q=lavoro",
               "/divari-regionali", "/chi-siamo", "/privacy", "/catalogo-dati",
               "/regione/lombardia", "/blog/divario-turistico-nord-sud-2024",
               "/indicatore/adulti-che-partecipano-all-apprendimento-permanente-totale/ter-99")

# Tutte. Le shell della SPA hanno un chrome proprio (il masthead React, che
# porta la navigazione dentro l'applicazione senza ricaricare), quindi non
# hanno l'header di Jinja: quello che devono avere in comune con le altre e' il
# design system, non il markup.
MIGRATED = JINJA_PAGES + SPA_ROUTES


class DesignSystemMigration(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        cache.clear()

    def _html(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, path)
        return response.get_data(as_text=True)

    def _statico(self, path):
        """Un file statico, chiuso subito.

        Flask serve i file statici con un wrapper che tiene aperto il
        descrittore finche' non lo si chiude: senza `close()` la suite lascia
        dietro di se' un ResourceWarning per ogni font."""
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, path)
        try:
            return response.get_data()
        finally:
            response.close()

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
        """I nomi delle famiglie non stanno piu' nell'HTML.

        Finche' il foglio era la URL di Google, `family=Newsreader` si leggeva
        nella pagina. Adesso i font sono nostri e le famiglie stanno in
        `fonts.css`: la pagina dichiara il foglio, e il foglio le famiglie.
        La prova segue la catena invece di cercare una stringa che il difetto
        ha semplicemente spostato di file.
        """
        css = self._statico("/static/css/fonts.css").decode("utf-8")
        for famiglia in ("Newsreader", "Public Sans", "Spline Sans Mono"):
            self.assertIn(f"font-family: '{famiglia}'", css)

        for path in SPA_ROUTES:
            with self.subTest(path=path):
                html = self._html(path)
                self.assertIn("css/fonts.css", html)
                self.assertNotIn("family=Archivo", html,
                                 f"{path}: carica ancora i font legacy")
                self.assertNotIn("fonts.googleapis.com", html,
                                 f"{path}: torna a un foglio bloccante di terza parte")

    def test_ogni_font_dichiarato_esiste_e_si_scarica_una_volta_sola(self):
        """Una `src` che punta a un file che non c'e' non fallisce: il browser
        ripiega sul font di sistema e la pagina rende storta senza che niente lo
        dica. E un `preload` con una URL diversa da quella del foglio scarica lo
        stesso font due volte, che e' peggio di non precaricarlo."""
        css = self._statico("/static/css/fonts.css").decode("utf-8")
        richiamati = set(re.findall(r"url\(\.\./fonts/([^)]+)\)", css))
        self.assertTrue(richiamati)
        for nome in sorted(richiamati):
            with self.subTest(font=nome):
                self.assertGreater(len(self._statico(f"/static/fonts/{nome}")), 1000)

        for path in SPA_ROUTES + ("/",):
            with self.subTest(path=path):
                html = self._html(path)
                for href in re.findall(r'<link rel="preload" href="([^"]+)"', html):
                    self.assertNotIn("?v=", href,
                                     "il precarico non coincide con la URL del foglio")
                    self.assertIn(href.rsplit("/", 1)[1], richiamati)

    # --- 2. l'opt-in ------------------------------------------------------
    def test_migrated_pages_declare_the_design_system(self):
        for path in MIGRATED:
            with self.subTest(path=path):
                self.assertRegex(self._html(path), r'<body[^>]*class="[^"]*\bds\b')

    def test_the_legacy_chrome_is_gone_everywhere(self):
        """Il masthead legacy e il suo menu mobile non esistono piu'.

        Non e' pulizia: finche' i due chrome convivevano, una pagina poteva
        servirne uno e linkare l'altro, e nessuno se ne accorgeva. Ora ce n'e'
        uno solo, e questo test e' il posto dove si scopre se ne rispunta un
        secondo.
        """
        for path in JINJA_PAGES:
            with self.subTest(path=path):
                html = self._html(path)
                self.assertNotIn('class="mobmenu"', html)
                self.assertIn('<header class="hdr">', html)
                # Il masthead legacy di Jinja. Quello React della SPA si chiama
                # allo stesso modo ed e' un'altra cosa, per questo il confronto
                # e' sulla riga esatta del template cancellato.
                self.assertNotIn('<header class="masthead">', html)

    def test_every_page_offers_the_skip_link_target(self):
        # Lo skiplink del chrome punta a #contenuto su OGNI pagina: se una non
        # ha il bersaglio, "Vai al contenuto" non va da nessuna parte, ed e' un
        # guasto che si vede solo con la tastiera.
        for path in JINJA_PAGES:
            with self.subTest(path=path):
                html = self._html(path)
                self.assertIn('href="#contenuto"', html)
                self.assertIn('id="contenuto"', html)

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
