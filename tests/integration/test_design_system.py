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

4. **Le shell della SPA hanno il chrome di tutte le altre.** Testata, briciole
   e piede li rende Flask anche su `/atlante` e `/confronto`, fuori da `#root`.
   La barra in basso del telefono, il piede React e la barra di contesto con il
   selettore delle modalita' erano tre navigazioni in piu', con etichette che il
   menu non usava piu', e per disegnarle la SPA si faceva passare le rotte in
   `window.__diNav`. Se tornano non fallisce niente: si vedono solo sul telefono.
"""
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

from app import app, nav
from app.cache import cache

TEMPLATES = Path(app.root_path) / "templates"


# Le rotte servite dal bundle React. Se se ne aggiunge una va aggiunta qui, ed
# e' il punto: la lista e' il contratto. `/atlante` ne e' uscita con la pagina
# della 1.0 resa dal server (`v1/atlante.html`): `app.html` resta come suo
# ripiego, e per questo monta ancora il bundle.
SPA_ROUTES = ("/confronto",)

# Un campione di ogni famiglia di pagina servita da Jinja, cioe' quelle che
# condividono `_ds_header.html`.
JINJA_PAGES = ("/", "/blog", "/regioni", "/temi", "/metodologia",
               "/qualita-della-vita", "/quiz", "/ricerca?q=lavoro",
               "/divari-regionali", "/chi-siamo", "/privacy", "/catalogo-dati",
               "/regione/lombardia", "/province", "/provincia/lecce", "/atlante",
               "/blog/divario-turistico-nord-sud-2024",
               "/indicatore/adulti-che-partecipano-all-apprendimento-permanente-totale/ter-99")

# Tutte, shell della SPA comprese: dentro `#root` hanno la loro applicazione, ma
# testata, briciole e piede sono gli stessi template di ogni altra pagina.
MIGRATED = JINJA_PAGES + SPA_ROUTES

REPO_ROOT = Path(__file__).resolve().parents[2]
BUNDLE_JS = REPO_ROOT / "app" / "static" / "dist" / "assets" / "index.js"
BUNDLE_CSS = REPO_ROOT / "app" / "static" / "dist" / "assets" / "index.css"
SPA_SOURCE = REPO_ROOT / "frontend" / "src" / "main.jsx"
SPA_STYLES = REPO_ROOT / "frontend" / "src" / "styles.css"

VOID_ELEMENTS = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input",
                           "link", "meta", "source", "track", "wbr"})


class _AncestorProbe(HTMLParser):
    """Per ogni elemento con un `id`, e per il primo `<footer>`, gli `id` degli
    elementi che lo contengono.

    L'ordine nel sorgente non basta a dire dove sta un elemento: un piede
    incluso per sbaglio dentro `#root` viene comunque dopo `id="root"`, e React
    lo cancella al montaggio. Una chiusura mancante chiude anche cio' che le sta
    dentro, come fa il browser, quindi un annidamento sbagliato si vede come un
    antenato in piu' e la prova va in rosso, non in verde.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.ancestors = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        keys = ["#" + attributes["id"]] if attributes.get("id") else []
        if tag == "footer":
            keys.append("footer")
        for key in keys:
            self.ancestors.setdefault(key, [ident for _, ident in self.stack if ident])
        if tag not in VOID_ELEMENTS:
            self.stack.append((tag, attributes.get("id")))

    def handle_endtag(self, tag):
        for depth in range(len(self.stack) - 1, -1, -1):
            if self.stack[depth][0] == tag:
                del self.stack[depth:]
                return


def ancestor_ids(html):
    probe = _AncestorProbe()
    probe.feed(html)
    probe.close()
    return probe.ancestors


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
        for famiglia in ("Sofia Sans", "Sofia Sans Semi Condensed"):
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
        # guasto che si vede solo con la tastiera. Sulle due shell della SPA il
        # bersaglio mancava: il link c'era, l'id no.
        for path in MIGRATED:
            with self.subTest(path=path):
                html = self._html(path)
                self.assertIn('href="#contenuto"', html)
                self.assertIn('id="contenuto"', html)

    # --- la rampa dei dati -------------------------------------------------
    def test_the_indicator_map_uses_the_design_system_ramp(self):
        """La mappa si dipinge per classe (`q1`..`q6`), e le classi leggono
        `var(--seq-N)`: `--seq-1..6` sono ridefinite nel tema scuro, e un colore
        cotto nel markup lascerebbe la mappa sulla rampa chiara con il resto
        della pagina scuro. Prima le regole erano un `<style>` in pagina con i
        `var()`; nella 1.0 stanno in components.css.
        """
        html = self._html(
            "/indicatore/adulti-che-partecipano-all-apprendimento-permanente-totale/ter-99"
        )
        mappa = re.search(r'<div class="map[^"]*" data-map>.*?</svg>', html, re.S)
        self.assertIsNotNone(mappa, "la scheda non disegna la mappa")
        classi = re.findall(r'<path d="[^"]+" data-key="[^"]+"[^>]*class="(q[1-6])', mappa.group(0))
        self.assertGreaterEqual(len(classi), 15, "la mappa dell'indicatore non dipinge le regioni")
        self.assertNotRegex(mappa.group(0), r'fill="#|fill:\s*#', "colore cotto nella mappa")
        css = self._statico("/static/css/ds/components.css").decode("utf-8")
        for passo in range(1, 7):
            self.assertIn(f".q{passo} {{ fill: var(--seq-{passo})", css)

    def test_the_legacy_blue_ramp_is_gone_from_the_migrated_pages(self):
        # `#15233b` era il navy dell'identita' vecchia. Sopravvive solo nelle
        # pagine non migrate, mai in quelle che dichiarano il design system.
        for path in MIGRATED:
            with self.subTest(path=path):
                self.assertNotIn("#15233b", self._html(path).lower())


if __name__ == "__main__":
    unittest.main()


class LaNavigazioneEUnaSola(unittest.TestCase):
    """Le voci stavano in due posti e divergevano.

    `_ds_header.html` per le pagine Flask, `frontend/src/main.jsx` a mano per la
    testata React: dall'atlante non si raggiungevano `/confronto` ne'
    `/divari-regionali`, la qualita' della vita portava all'indice invece che
    alla classifica, e le stesse sezioni si chiamavano "Quiz Italia" e "Blog"
    da una parte, "Quiz" e "Storie" dall'altra. Nessuna di queste cose fa
    fallire niente: si vedono solo aprendo le due testate una accanto all'altra.

    Adesso `app/nav.py` decide e disegna solo Flask: la SPA non ha piu' nessuna
    navigazione sua, e nemmeno riceve le voci. Testata, briciole e piede di
    `/atlante` e `/confronto` sono gli stessi template di ogni altra pagina.
    """

    def setUp(self):
        self.client = app.test_client()
        cache.clear()

    def test_ogni_voce_di_menu_porta_a_una_pagina_che_esiste(self):
        """Una voce rotta non fa fallire niente e la trova solo chi ci clicca."""
        for percorso in nav.paths():
            with self.subTest(percorso=percorso):
                self.assertEqual(self.client.get(percorso).status_code, 200)

    def test_la_testata_flask_non_elenca_voci_per_conto_suo(self):
        sorgente = (TEMPLATES / "_ds_header.html").read_text(encoding="utf-8")
        cuciti = re.findall(r'<a href="(/[^"#]*)"', sorgente)
        # Resta il logo, che porta alla home e non e' una voce di menu.
        self.assertEqual([h for h in cuciti if h != "/"], [],
                         "la testata e' tornata a elencare le voci a mano")

    def test_il_bundle_non_manda_da_nessuna_parte_che_il_menu_non_conosca(self):
        """La barra del telefono mandava a `/qualita-della-vita`, la testata
        alla classifica: due pagine diverse per la stessa voce a seconda del
        dispositivo. La barra non c'e' piu', ma un link scritto nel bundle deve
        restare una rotta che il menu conosce."""
        sorgente = SPA_SOURCE.read_text(encoding="utf-8")
        noti = set(nav.paths()) | {"/"}
        for rotta in sorted(set(re.findall(r'href="(/[^"{]*)"', sorgente))):
            with self.subTest(rotta=rotta):
                self.assertIn(rotta, noti,
                              "main.jsx manda a una rotta che app/nav.py non dichiara")

    def test_il_cassetto_del_telefono_non_perde_voci_per_strada(self):
        """Sul telefono il cassetto e' l'unica navigazione che si vede, e ogni
        destinazione del menu e del piede ci deve stare. Il gruppo "Altro" si
        ricava da `nav.drawer_other()`: una voce che non sta in una tendina
        finisce li', senza che nessuno debba ricordarsela."""
        html = self.client.get("/").get_data(as_text=True)
        cassetto = re.search(r'<div class="drawer" id="ds-drawer".*?</header>', html, re.S)
        self.assertIsNotNone(cassetto)
        rotte = re.findall(r'href="(/[^"]*)"', cassetto.group(0))
        for percorso in nav.paths():
            with self.subTest(percorso=percorso):
                self.assertIn(percorso, rotte, "il cassetto ha perso una voce")
        self.assertEqual(rotte.count("/metodologia"), 1)


class TheSpaShellsWearTheSiteChrome(unittest.TestCase):
    """`/atlante` e `/confronto` con la testata, le briciole e il piede del sito.

    Sul telefono l'atlante aveva una barra fissa in basso con cinque voci sue
    ("Atlante, Regioni, Qualita', Gioco, Blog", a 9,5 pixel) mentre il menu
    diceva "Storie" e "Quiz", e in fondo due piedi: uno React con la lista in
    fila e uno server con una manciata di link. La vista regione aveva una
    scheda scritta in inchiostro su fondo inchiostro, e "Vai al contenuto" non
    portava da nessuna parte. Nessuna di queste cose fa fallire una pagina.
    """

    # I resti di quello che la SPA disegnava per conto suo. Si cercano nel
    # bundle servito, non solo nel sorgente: se `dist/` resta indietro, la
    # produzione serve la barra anche con il sorgente pulito.
    GONE_FROM_BUNDLE = ("tabbar", "__diNav", "mode-switch", "context-bar",
                        "site-footer", "spa-seo-footer", "Andamento medio nazionale",
                        "switch_mode")

    def setUp(self):
        self.client = app.test_client()
        cache.clear()

    def _html(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, path)
        return response.get_data(as_text=True)

    @staticmethod
    def _footer(html):
        found = re.findall(r'<footer class="ftr">.*?</footer>', html, re.DOTALL)
        return [re.sub(r">\s+<", "><", re.sub(r"\s+", " ", f)).strip() for f in found]

    def test_the_shells_no_longer_hand_the_menu_to_the_bundle(self):
        for path in SPA_ROUTES:
            with self.subTest(path=path):
                self.assertNotIn("__diNav", self._html(path))
        self.assertFalse(hasattr(nav, "for_spa"))
        self.assertFalse(hasattr(nav, "SPA_MASTHEAD"))

    def test_the_bundle_draws_no_navigation_of_its_own(self):
        bundle = BUNDLE_JS.read_text(encoding="utf-8") + BUNDLE_CSS.read_text(encoding="utf-8")
        for leftover in self.GONE_FROM_BUNDLE:
            with self.subTest(leftover=leftover):
                self.assertNotIn(leftover, bundle, "il bundle servito ha ancora un pezzo del menu vecchio")
        source = SPA_SOURCE.read_text(encoding="utf-8")
        for leftover in ("NAV_RIPIEGO", "readNav", "navPath", "function SiteFooter",
                         "function ContextBar", "function ModeSwitch", 'className="tabbar"'):
            with self.subTest(leftover=leftover):
                self.assertNotIn(leftover, source)

    def test_one_footer_the_same_as_every_other_page(self):
        """Il piede delle shell e' lo stesso markup di una pagina qualunque:
        cosi' ogni sezione del sito, `/province` compresa, si raggiunge anche
        senza JavaScript, e non puo' tornare un secondo elenco scritto a mano."""
        reference = self._footer(self._html("/metodologia"))
        self.assertEqual(len(reference), 1)
        for path in SPA_ROUTES:
            with self.subTest(path=path):
                html = self._html(path)
                self.assertEqual(html.count("<footer"), 1, "un piede solo")
                self.assertEqual(self._footer(html), reference)
                self.assertLess(html.index('id="root"'), html.index('<footer class="ftr">'),
                                "il piede viene dopo l'applicazione")
                ancestors = ancestor_ids(html)
                self.assertIn("footer", ancestors)
                self.assertNotIn("root", ancestors["footer"],
                                 "il piede sta dentro #root: React lo cancella al montaggio")
                footer = self._footer(html)[0]
                for href in nav.paths():
                    self.assertIn(f'href="{href}"', footer)

    def test_the_skip_link_lands_on_a_static_wrapper(self):
        """Il bersaglio non puo' essere il `<main>` di React, che esiste solo
        dopo il montaggio, e due `<main>` annidati non sono ammessi. Deve
        contenere `#root`, e dopo il salto l'anello del fuoco si vede come su
        ogni pagina 1.0: una regola che lo toglie a `.spa-page` batte
        `.ds *:focus-visible`, perche' il foglio della SPA si carica dopo."""
        for path in SPA_ROUTES:
            with self.subTest(path=path):
                html = self._html(path)
                self.assertEqual(html.count("<main"), 1, "un <main> solo nell'HTML del server")
                target = re.search(r'<(\w+)[^>]*\bid="contenuto"[^>]*>', html)
                self.assertIsNotNone(target)
                self.assertNotEqual(target.group(1), "main")
                self.assertIn('tabindex="-1"', target.group(0))
                ancestors = ancestor_ids(html)
                self.assertIn("#root", ancestors)
                self.assertIn("contenuto", ancestors["#root"], "#contenuto deve contenere #root")
        for stylesheet in (SPA_STYLES, BUNDLE_CSS):
            with self.subTest(stylesheet=stylesheet.name):
                rules = re.sub(r"\s+", "", stylesheet.read_text(encoding="utf-8"))
                self.assertIsNone(re.search(r"\.spa-page:focus\{[^}]*outline:(none|0)", rules),
                                  "il salto al contenuto deve mostrare l'anello del fuoco")

    def test_the_breadcrumb_is_rendered_by_flask_above_the_app(self):
        for path in SPA_ROUTES:
            with self.subTest(path=path):
                html = self._html(path)
                self.assertEqual(html.count('aria-label="Percorso"'), 1, "un percorso solo")
                self.assertLess(html.index('aria-label="Percorso"'), html.index('id="root"'))
                self.assertIn('<nav class="breadcrumb" aria-label="Percorso"><a href="/">Home</a>', html)

    def test_the_region_call_to_action_beats_the_link_rule(self):
        """`.ds a` (0,1,1) batteva `.region-cta` (0,1,0): la scheda era scritta
        in inchiostro su fondo inchiostro. La regola vince solo sotto `.ds`."""
        stylesheet = SPA_STYLES.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"^\.region-cta\b", stylesheet, re.MULTILINE),
                          "`.region-cta` senza `.ds` perde contro `.ds a`")
        self.assertIn(".ds .region-cta {", stylesheet)
        self.assertIn(".ds .region-cta", BUNDLE_CSS.read_text(encoding="utf-8"))

    def test_the_favourites_toggle_waits_for_a_signed_in_reader(self):
        """"Solo preferiti" compariva a chiunque appena l'accesso era configurato
        sul sito, e all'anonimo dava una lista vuota."""
        source = SPA_SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("showFav={isAuthConfigured()}", source)
        self.assertIn("showFav={signedIn}", source)
        self.assertIn('const favOnly = favParam === "1" && signedIn;', source)
