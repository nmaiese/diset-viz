"""La pagina di "Dov'è la provincia?" senza Flask: la costante dei confini, i gruppi di
sagome, le frasi fisse, i template e il foglio del client.

Le guardie sui fogli del gioco (`test_css_tokens`, `test_game_motion`) cercano solo i
`frontend/src/game/*.css`, non le sottocartelle: il foglio della mappa sta in
`frontend/src/game/mappa/` e senza questo file nessuna guardia lo leggerebbe. Qui gli si
applicano le stesse tre regole (niente colori scritti, movimento solo con `no-preference`,
ogni `--game-*` esiste nei due temi)."""

import re
import unittest
from pathlib import Path

from app import game_daily, game_mappa, game_mappa_page, sources
from app.design import maps
from tests.unit import test_css_tokens as css_tokens
from tests.unit import test_game_motion as game_motion

RADICE = Path(__file__).resolve().parents[2]
TEMPLATE = RADICE / "app" / "templates" / "game_mappa.html"
PARTIAL = RADICE / "app" / "templates" / "_mappa_muta.html"
FOGLIO = RADICE / "frontend" / "src" / "game" / "mappa" / "mappa.css"
VIETATI = "—–;…"


def _senza_commenti_jinja(testo):
    return re.sub(r"\{#.*?#\}", "", testo, flags=re.S)


class ConfiniTest(unittest.TestCase):
    def test_i_confini_non_sono_una_famiglia_di_indicatori(self):
        """`SOURCES` alimenta `FAMILY_BY_ACRONYM` e l'espressione regolare dei codici negli URL."""
        self.assertNotIn("PROVINCE_BOUNDARIES", sources.SOURCES)
        self.assertNotIn("openpolis", {m["institution"].lower() for m in sources.SOURCES.values()})
        self.assertFalse(any("openpolis" in a for a in sources.FAMILY_BY_ACRONYM))

    def test_la_costante_ha_i_campi_che_la_riga_compone(self):
        b = sources.PROVINCE_BOUNDARIES
        for campo in ("institution", "institution_url", "redistributor", "redistributor_url",
                      "license_label", "license_url", "vintage"):
            self.assertTrue(b.get(campo), campo)
        self.assertTrue(b["institution_url"].startswith("https://www.istat.it/"))
        self.assertTrue(b["license_url"].endswith("/by/4.0/deed.it"))

    def test_la_riga_di_attribuzione_e_quella_decisa_e_ha_tre_link(self):
        riga = str(game_mappa_page.attribution("Divario Italia"))
        testo = re.sub(r"<[^>]+>", "", riga)
        self.assertEqual(
            testo,
            "Confini delle province: Istat (CC BY 4.0), ridistribuiti da openpolis, "
            "semplificati e riproiettati da Divario Italia.")
        self.assertEqual(
            re.findall(r'<a href="([^"]+)">([^<]+)</a>', riga),
            [("https://www.istat.it/classificazione/confini-delle-unita-amministrative-a-fini-statistici/", "Istat"),
             ("https://creativecommons.org/licenses/by/4.0/deed.it", "CC BY 4.0"),
             ("https://github.com/openpolis/geojson-italy", "openpolis")])

    def test_semplificati_e_vero(self):
        """La parola e' ammessa solo finche' lo script dei tracciati semplifica davvero."""
        script = (RADICE / "design" / "v1" / "tools" / "province_map.py").read_text(encoding="utf-8")
        self.assertIn("def simplify(", script)


class SardegnaTest(unittest.TestCase):
    def test_la_frase_ha_il_numero_del_pool(self):
        totale = len(game_daily.province_pool())
        frase = game_mappa_page.sardinia_note(totale)
        self.assertTrue(frase.startswith(f"La mappa mostra le {totale} province in vigore fino al 31 dicembre 2025, "
                                         "con i confini Istat del 2023. "))
        self.assertIn("Dal 1° gennaio 2026 la Sardegna ha un nuovo assetto, con due città metropolitane e sei province", frase)
        self.assertIn("l'Istat conta 110 unità territoriali: in questa mappa la Sardegna è ancora quella precedente.", frase)
        for carattere in VIETATI:
            self.assertNotIn(carattere, frase)

    def test_nessun_testo_dice_che_le_107_sono_le_province_attuali(self):
        frase = game_mappa_page.sardinia_note(107)
        self.assertNotIn("province delle statistiche", frase)


class GruppiTest(unittest.TestCase):
    def setUp(self):
        self.gruppi = game_mappa_page.region_groups()
        self.pool = game_daily.province_pool()

    def test_venti_regioni_e_ogni_provincia_una_volta(self):
        self.assertEqual(len(self.gruppi), 20)
        chiavi = [k for g in self.gruppi for k in g["provinces"]]
        self.assertEqual(sorted(chiavi), sorted(p["key"] for p in self.pool))
        self.assertEqual(len(chiavi), len(set(chiavi)))

    def test_ogni_regione_ha_un_tracciato(self):
        """Le chiavi di regione divergono facilmente (`valle-d-aosta`, `trentino-alto-adige`)."""
        for g in self.gruppi:
            with self.subTest(regione=g["key"]):
                self.assertIn(g["key"], maps.REGION_PATHS)
                self.assertTrue(g["provinces"])

    def test_il_riquadro_e_quello_di_maps_zoom(self):
        for g in self.gruppi:
            with self.subTest(regione=g["key"]):
                self.assertEqual(g["viewbox"], maps.zoom(g["key"])["viewbox"])
                x, y, w, h = (float(v) for v in g["viewbox"].split())
                self.assertGreater(w, 0)
                self.assertGreater(h, 0)

    def test_il_centroide_di_ogni_provincia_sta_nel_riquadro_della_sua_regione(self):
        """Dopo il primo tocco sulla regione la provincia da trovare e' sempre visibile."""
        for g in self.gruppi:
            x0, y0, w, h = (float(v) for v in g["viewbox"].split())
            for chiave in g["provinces"]:
                p = next(p for p in self.pool if p["key"] == chiave)
                with self.subTest(provincia=chiave):
                    self.assertTrue(x0 <= p["x"] <= x0 + w and y0 <= p["y"] <= y0 + h,
                                    f"{chiave} fuori dal riquadro di {g['key']}")


class ElencoTest(unittest.TestCase):
    def test_l_elenco_e_alfabetico_e_completo(self):
        elenco = game_mappa_page.page("Divario Italia")["list"]
        nomi = [e["name"].casefold() for e in elenco]
        self.assertEqual(nomi, sorted(nomi))
        self.assertEqual({e["key"] for e in elenco}, {p["key"] for p in game_daily.province_pool()})
        self.assertEqual(len(elenco), len(game_daily.province_pool()))

    def test_le_forme_ufficiali_vengono_dal_backend(self):
        elenco = {e["key"]: e for e in game_mappa_page.page("Divario Italia")["list"]}
        for chiave, ufficiale in game_mappa.OFFICIAL_NAMES.items():
            self.assertEqual(elenco[chiave]["official_name"], ufficiale)
        self.assertNotIn("OFFICIAL_NAMES", vars(game_mappa_page))
        self.assertNotIn("NOMI_UFFICIALI", vars(game_mappa_page))


class TemplateTest(unittest.TestCase):
    """Il template non scrive niente che venga dai dati."""

    def setUp(self):
        self.testo = _senza_commenti_jinja(TEMPLATE.read_text(encoding="utf-8")
                                           + PARTIAL.read_text(encoding="utf-8"))
        self.espressioni_tolte = re.sub(r"\{\{.*?\}\}|\{%.*?%\}", "", self.testo, flags=re.S)

    def test_nessun_nome_di_provincia_scritto_a_mano(self):
        """Con confini di parola e maiuscole esatte: "Roma" e' una provincia, e "ora di Roma" una frase."""
        per_nome = {p["name"] for p in game_daily.province_pool()}
        trovati = [n for n in per_nome if re.search(rf"(?<!\w){re.escape(n)}(?!\w)", self.espressioni_tolte)]
        self.assertEqual(trovati, [])

    def test_nessun_numero_di_province_scritto_a_mano(self):
        self.assertIsNone(re.search(r"\b107\b|\b110\b", self.espressioni_tolte))

    def test_nessuna_fonte_scritta_a_mano(self):
        for istituto in ("Istat", "Eurostat", "openpolis"):
            self.assertNotIn(istituto, self.espressioni_tolte)

    def test_nessuna_coordinata_della_risposta(self):
        """Nessun centro, nessuna coordinata di provincia: i centri si leggono dal DOM."""
        self.assertIsNone(re.search(r'data-(x|y|cx|cy|centro|center)\b', self.testo))

    def test_le_sagome_hanno_etichetta_neutra(self):
        sagome = re.findall(r"<use class=\"prov-tile\"[^>]*>", self.testo)
        self.assertEqual(len(sagome), 1)  # il ciclo, una volta
        self.assertIn('aria-label="Provincia"', sagome[0])

    def test_nessun_blocco_dello_zoom_e_nessun_user_scalable(self):
        self.assertNotIn("user-scalable", self.testo)


class FoglioTest(unittest.TestCase):
    def setUp(self):
        self.testo = re.sub(r"/\*.*?\*/", "", FOGLIO.read_text(encoding="utf-8"), flags=re.S)

    def test_nessun_colore_scritto(self):
        self.assertEqual(re.findall(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(", self.testo), [])

    def test_nessuna_sequenza_di_escape_letterale(self):
        self.assertNotIn("\\n", self.testo)

    def test_il_movimento_sta_dentro_no_preference(self):
        trovate = game_motion._blocchi(FOGLIO.read_text(encoding="utf-8"))
        self.assertTrue(trovate, "il foglio non ha movimento: la guardia non guarda piu' niente")
        for contesto, proprieta, _, dentro, reduce in trovate:
            with self.subTest(contesto=contesto, proprieta=proprieta):
                self.assertTrue(dentro or reduce)

    def test_i_token_del_gioco_esistono_nei_due_temi(self):
        sistema = css_tokens.SISTEMA.read_text(encoding="utf-8")
        chiaro = {n for n in css_tokens._nomi(css_tokens._corpi(sistema, r"^:root\s*\{")) if n.startswith("--game-")}
        scuro = {n for n in css_tokens._nomi(css_tokens._corpi(sistema, r'^\[data-theme="dark"\]\s*\{'))
                 if n.startswith("--game-")}
        usati = set(re.findall(r"var\((--game-[a-z-]+)", self.testo))
        self.assertEqual(usati - chiaro, set())
        self.assertEqual(usati - scuro, set())

    def test_l_animazione_di_viewbox_non_c_e(self):
        """Il viewBox non si anima in CSS: lo cambia il client, di colpo."""
        self.assertNotIn("viewBox", self.testo)


CLIENT_DIR = RADICE / "frontend" / "src" / "game" / "mappa"
VITE = RADICE / "frontend" / "vite.config.js"


def _senza_commenti_js(testo):
    testo = re.sub(r"/\*.*?\*/", "", testo, flags=re.S)
    return "\n".join(re.sub(r"(^|\s)//.*$", "", riga) for riga in testo.splitlines())


class ClienteTest(unittest.TestCase):
    """Le regole del tocco e della fonte che nessun test del browser vede se si rompono."""

    def setUp(self):
        self.sorgenti = {f.name: _senza_commenti_js(f.read_text(encoding="utf-8"))
                         for f in sorted(CLIENT_DIR.glob("*.js")) + sorted(CLIENT_DIR.glob("*.jsx"))}
        self.mappa = self.sorgenti["mappaMuta.js"]

    def test_il_tocco_e_solo_un_click_sull_svg(self):
        """Mai `pointerdown` ne' `touchstart`: lo scorrimento e il pinch restano del browser. Mai
        `getScreenCTM` (su iOS Safari non e' verificato): il bersaglio e' la sagoma colpita."""
        for nome, testo in self.sorgenti.items():
            with self.subTest(file=nome):
                self.assertIsNone(re.search(r"pointer(down|up|move)|touch(start|move|end)|getScreenCTM|user-scalable", testo))
        self.assertEqual(len(re.findall(r'addEventListener\("click"', self.mappa)), 1)
        self.assertIn("closest(\"[data-region]\")", self.mappa)
        self.assertIn("closest(\"[data-key]\")", self.mappa)

    def test_preventdefault_solo_sui_tasti(self):
        """Un `preventDefault` su un evento di tocco bloccherebbe lo scorrimento: ce n'e' solo
        nel gestore della tastiera, per le frecce, Invio e Esc."""
        gestore_tasti = self.mappa[self.mappa.index("function alTasto"):self.mappa.index('svg.addEventListener("click"')]
        self.assertEqual(self.mappa.count("preventDefault"), gestore_tasti.count("preventDefault"))
        self.assertGreater(gestore_tasti.count("preventDefault"), 0)

    def test_nessun_import_da_guess_e_nessuna_fonte_scritta(self):
        for nome, testo in self.sorgenti.items():
            with self.subTest(file=nome):
                self.assertNotIn("guess/", testo)
                for istituto in ("Istat", "Eurostat", "openpolis"):
                    self.assertNotIn(istituto, testo)

    def test_i_numeri_non_sono_cablati(self):
        """Il numero di domande e il massimo vengono dal server: nel client non c'e' `total: 10`."""
        for nome, testo in self.sorgenti.items():
            with self.subTest(file=nome):
                self.assertIsNone(re.search(r"total\s*:\s*10\b|points_max\s*:\s*20\b", testo))

    def test_la_mappa_non_blocca_il_pinch(self):
        css = FOGLIO.read_text(encoding="utf-8")
        self.assertIn("touch-action: manipulation", css)
        self.assertNotIn("touch-action: none", css)

    def test_l_entry_e_registrato_e_la_pagina_lo_carica(self):
        vite = VITE.read_text(encoding="utf-8")
        self.assertIn('"quiz-mappa": resolve(__dirname, "src/game/entries/mappa.jsx")', vite)
        self.assertTrue((RADICE / "frontend" / "src" / "game" / "entries" / "mappa.jsx").exists())
        pagina = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("dist/assets/quiz-mappa.js", pagina)
        self.assertIn("dist/assets/quiz-mappa.css", pagina)

    def test_conferma_non_e_disabled(self):
        """Un bottone `disabled` non prende il focus: Tab deve poter raggiungere Conferma."""
        azioni = self.sorgenti["Azioni.jsx"]
        self.assertIn("aria-disabled", azioni)
        self.assertNotRegex(azioni, r"(?<![-\w])disabled=")

    def test_il_testo_dell_interfaccia_non_ha_caratteri_vietati(self):
        """I testi visibili del client, fuori dai commenti: niente `—`, `–`, `...` fatti di tre puntini
        unicode. Il `;` e' sintassi nel codice e si guarda nei testi di `partita.test.mjs`."""
        for nome, testo in self.sorgenti.items():
            with self.subTest(file=nome):
                for carattere in "—–…":
                    self.assertNotIn(carattere, testo)


if __name__ == "__main__":
    unittest.main()
