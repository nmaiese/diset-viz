"""Le guardie sui fogli di stile: difetti che non fanno fallire niente.

Ognuna nasce da un guasto vero trovato riprendendo il design system 2026, e
ognuna e' del tipo che non si vede in una PR e non rompe nessun test:

1. una riga con `\\n` scritti come due caratteri invece che a capo. Il CSS li
   tokenizza come identificatori, il selettore diventa invalido e il browser
   **scarta l'intera regola**. Era successo a `.viz-grid.has-no-map`, e le 67
   pagine a livello provincia rendevano la classifica schiacciata in meta'
   pagina con la colonna della mappa vuota.
2. un token di movimento dichiarato solo dentro `body.ds`. Uno pseudo-elemento
   di view transition e' figlio della radice, non di `<body>`, quindi da li'
   quei `var()` non risolvono e la dissolvenza fra pagine cade a `0s`.
3. il `:root` di ripiego della SPA che smette di essere ripiego. Vale finche'
   il design system ripunta ogni nome che dichiara: il giorno che ne aggiunge
   uno che il design system non conosce, quel valore vecchio arriva a schermo.
"""
import re
import unittest
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
SITE = RADICE / "app" / "static" / "css" / "site.css"
SPA = RADICE / "frontend" / "src" / "styles.css"
GIOCO = RADICE / "frontend" / "src" / "game" / "game.css"
SISTEMA = RADICE / "app" / "static" / "css" / "ds" / "system.css"
CHROME = RADICE / "app" / "static" / "css" / "ds" / "chrome.css"
COMPONENTS = RADICE / "app" / "static" / "css" / "ds" / "components.css"
REGION_SHEET = RADICE / "app" / "static" / "css" / "ds" / "pages" / "regione.css"
PROVINCE_SHEET = RADICE / "app" / "static" / "css" / "ds" / "pages" / "provincia.css"

FOGLI = (SITE, SPA, GIOCO, SISTEMA, CHROME)

# I token che le view transition leggono dalla radice del documento.
MOVIMENTO_IN_RADICE = ("--dur", "--ease-out")


def _corpi(testo, intestazione):
    """I corpi dei blocchi la cui intestazione combacia a inizio riga.

    Si contano le graffe invece di fermarsi alla prima chiusa: dentro un
    `:root` ci stanno `@media` annidati, e una regex pigra li taglierebbe a
    meta'. Si ancora a inizio riga perche' `body.ds` compare anche dentro i
    commenti, e un `find()` ingenuo aggancia quelli.
    """
    corpi = []
    for m in re.finditer(intestazione, testo, re.M):
        i = testo.index("{", m.start()) + 1
        profondita, j = 1, i
        while profondita and j < len(testo):
            if testo[j] == "{":
                profondita += 1
            elif testo[j] == "}":
                profondita -= 1
            j += 1
        corpi.append(testo[i:j - 1])
    return corpi


def _nomi(corpi):
    nomi = set()
    for corpo in corpi:
        nomi |= set(re.findall(r"(--[A-Za-z0-9-]+)\s*:", corpo))
    return nomi


class FogliDiStileTest(unittest.TestCase):
    def test_nessuna_sequenza_di_escape_letterale(self):
        """Un `\\n` di due caratteri fa scartare la regola che lo contiene."""
        for foglio in FOGLI:
            with self.subTest(foglio=foglio.name):
                self.assertNotIn("\\n", foglio.read_text(encoding="utf-8"))

    def test_il_movimento_delle_view_transition_sta_nella_radice(self):
        """`::view-transition-group(root)` non vede i token di `body.ds`."""
        testo = SISTEMA.read_text(encoding="utf-8")
        radice = _nomi(_corpi(testo, r"^:root\s*\{"))
        for token in MOVIMENTO_IN_RADICE:
            with self.subTest(token=token):
                self.assertIn(token, radice)

    def test_chi_usa_quei_token_li_trova(self):
        """Il foglio che anima la view transition e quello che la dichiara.

        La regola sta in `chrome.css`, che caricano tutte le pagine: in
        `site.css` non la vedevano ne' le shell della SPA ne' le pagine 1.0."""
        site = CHROME.read_text(encoding="utf-8")
        self.assertIn("::view-transition-group(root)", site)
        sistema = SISTEMA.read_text(encoding="utf-8")
        radice = _nomi(_corpi(sistema, r"^:root\s*\{"))
        usati = set(re.findall(r"var\((--[A-Za-z0-9-]+)\)",
                               "".join(_corpi(site, r"^::view-transition-group\(root\)\s*\{"))))
        self.assertTrue(usati, "la regola non usa nessun token: il test non guarda piu' niente")
        self.assertEqual(usati - radice, set())

    def test_il_ripiego_della_spa_resta_un_ripiego(self):
        """Ogni nome del `:root` della SPA deve essere ripuntato dal sistema.

        `--masthead-h` e' l'eccezione dichiarata: e' un'altezza, non un colore,
        e vale lo stesso valore da entrambe le parti.
        """
        spa = _nomi(_corpi(SPA.read_text(encoding="utf-8"), r"^:root\s*\{"))
        sistema = SISTEMA.read_text(encoding="utf-8")
        coperti = _nomi(_corpi(sistema, r"^body\.ds\s*\{")) | _nomi(_corpi(sistema, r"^:root\s*\{"))
        self.assertEqual(spa - coperti - {"--masthead-h"}, set())

    def test_spa_rules_bake_no_colour(self):
        """Nel foglio della SPA un colore sta solo nel `:root` di ripiego.

        Un esadecimale o un `rgba()` in una regola non segue il tema scuro: il
        bollino "Qualita' della vita" dell'atlante restava grigio chiaro sulla
        pagina scura, e la scheda della regione passava a un blu scuro fisso al
        passaggio del mouse. Anche il ripiego dentro un `var()` conta: e' un
        colore del sistema vecchio che aspetta solo che il token manchi.
        """
        text = SPA.read_text(encoding="utf-8")
        without_comments = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        root_match = re.search(r"^:root\s*\{", without_comments, re.MULTILINE)
        self.assertIsNotNone(root_match)
        end = without_comments.index("}", root_match.end())
        rules = without_comments[:root_match.start()] + without_comments[end + 1:]
        baked = re.findall(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(", rules)
        self.assertEqual(baked, [], "colori cotti in frontend/src/styles.css fuori dal :root")

    def test_il_telaio_vecchio_non_ha_piu_regole(self):
        """Nessuna pagina rende piu' `.masthead`, `.mobmenu` o `.nav-underline`.

        Le shell della SPA non caricano nemmeno `site.css`, quindi quelle regole
        stavano li' senza raggiungere un solo elemento. La SPA tiene le sue in
        `frontend/src/styles.css`, che e' un altro foglio e un altro bundle.
        """
        site = SITE.read_text(encoding="utf-8")
        for morto in (".masthead", ".mobmenu", ".nav-underline", ".brand-mark"):
            with self.subTest(selettore=morto):
                self.assertIsNone(re.search(rf"^{re.escape(morto)}[\s,:{{]", site, re.M))

    def test_wide_stacked_tables_repeat_the_stack_block(self):
        """Le tabelle larghe si impilano con lo stesso blocco delle altre.

        `.stackwrap--wide` ("Tutti gli indicatori" di regione e provincia)
        diventa blocchi sotto i 720 pixel invece che sotto i 560, e la soglia di
        un contenitore non si passa per variabile: il corpo e' scritto due
        volte. Se uno dei due cambia da solo, fra 560 e 720 pixel quelle tabelle
        prendono un'impaginazione che nessuno ha guardato. E le regole di pagina
        che valgono solo a blocchi devono chiedere lo stesso contenitore: a 560
        la regione perdeva il filetto fra un tema e l'altro proprio nella fascia
        dove le righe sono gia' blocchi.
        """
        components = COMPONENTS.read_text(encoding="utf-8")

        def normalized(body):
            body = re.sub(r"/\*.*?\*/", "", body, flags=re.DOTALL)
            return re.sub(r"\s+", " ", body).strip()

        narrow = [b for b in _corpi(components, r"^@container \(max-width: 560px\) \{")
                  if ".table--stack thead" in b]
        wide = _corpi(components, r"^@container stackwide \(max-width: 719px\) \{")
        self.assertEqual(len(narrow), 1)
        self.assertEqual(len(wide), 1)
        self.assertEqual(normalized(wide[0]), normalized(narrow[0]))
        self.assertIn(".stackwrap--wide { container-name: stackwide; }", components)

        for sheet, selector in ((REGION_SHEET, ".regione-area"), (PROVINCE_SHEET, ".provincia-table")):
            text = sheet.read_text(encoding="utf-8")
            with self.subTest(foglio=sheet.name):
                at_560 = [b for b in _corpi(text, r"^@container \(max-width: 560px\) \{") if selector in b]
                self.assertEqual(at_560, [], f"{selector} a blocchi deve chiedere stackwide, non i 560 pixel")
                self.assertTrue(any(selector in b for b in _corpi(text, r"^@container stackwide \(max-width: 719px\) \{")))

    def test_la_barra_in_alto_tiene_il_suo_nome_di_transizione(self):
        """Senza `view-transition-name` la testata si dissolve col resto."""
        self.assertIn("view-transition-name: masthead", CHROME.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
