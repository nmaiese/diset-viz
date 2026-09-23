"""Ogni link interno risponde 200 senza redirect, e ogni ancora esiste.

Le 103 pagine provincia sono uscite con 513 link in 404 e 929 in 301, anche
nella loro forma Markdown, e la prova che doveva accorgersene passava: cercava
i link con `href="(/[a-z0-9/_.-]+)"`, che non vede i due punti di
`ter-bes:<id>`, e accettava i 301. Questa la sostituisce, con le funzioni di
`scripts/audit_link_interni.py`, che fa lo stesso controllo su tutta la sitemap.

Le pagine sono tutte le province, in HTML e in Markdown, piu' una pagina per
tipo: e' dove un costruttore di link rifatto a mano si vede per primo.
"""
import unittest

from app import app, bes_data, indicator_view, province_profile
from app.agent_discovery import markdown_available
from app.cache import cache
from scripts.audit_link_interni import LinkChecker, extract_links

PAGINE_PER_TIPO = (
    "/",
    "/regioni",
    "/regione/puglia",
    "/regione/trentino-alto-adige",
    "/regione/valle-d-aosta",
    "/qualita-della-vita",
    "/qualita-della-vita/classifica/province",
    "/qualita-della-vita/classifica/province?profilo=giovani",
    "/qualita-della-vita/classifica/regioni",
    # Una scheda con due livelli, nelle sue due viste, e una solo provinciale.
    "/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001",
    "/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001?livello=provincia",
    "/indicatore/medici-specialisti/bes-12SER002P",
    "/temi",
    "/tema/lavoro-e-conciliazione",
    "/catalogo-dati",
    "/metodologia",
    "/blog/pil-pro-capite-regioni-divario-2024",
    "/ricerca?q=lecce",
    "/quiz/ordina",
    "/llms.txt",
    "/llms-full.txt",
    "/api/quality-life/province/lecce",
)


class OgniLinkInternoRisponde(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.checker = LinkChecker(app.test_client())
        with app.app_context():
            cls.province = [f"/provincia/{chiave}" for chiave in province_profile.chiavi()]

    @classmethod
    def tearDownClass(cls):
        # La cache dei test e' una SimpleCache con soglia 500: 103 province e le
        # loro destinazioni la riempiono, e le voci nuove sfratterebbero quelle
        # delle prove che girano dopo (commit 1928310, da 52 a 168 secondi).
        cache.clear()

    def _nessun_guasto(self, percorso, markdown=False):
        guasti = self.checker.broken(percorso, markdown=markdown)
        self.assertEqual(guasti, [], f"{percorso}{' [md]' if markdown else ''}")

    def test_le_province_in_html(self):
        self.assertGreaterEqual(len(self.province), 103)
        for percorso in self.province:
            with self.subTest(pagina=percorso):
                self._nessun_guasto(percorso)

    def test_le_province_in_markdown(self):
        for percorso in self.province:
            with self.subTest(pagina=percorso):
                self._nessun_guasto(percorso, markdown=True)

    def test_una_pagina_per_tipo(self):
        for percorso in PAGINE_PER_TIPO:
            with self.subTest(pagina=percorso):
                self._nessun_guasto(percorso)
                if markdown_available(percorso.split("?")[0]):
                    self._nessun_guasto(percorso, markdown=True)

    def test_la_prova_vede_i_link_che_la_vecchia_non_vedeva(self):
        """Il motivo per cui questa prova esiste, fissato: i due punti, le
        maiuscole e la query non la fanno piu' diventare cieca."""
        html = ('<a href="/indicatore/x/ter-bes:07SIC004P">a</a>'
                '<a href="/indicatore/x/bes-01SAL001?livello=provincia#territorio-lecce">b</a>')
        self.assertEqual(
            extract_links(html, "text/html"),
            {"/indicatore/x/ter-bes:07SIC004P",
             "/indicatore/x/bes-01SAL001?livello=provincia#territorio-lecce"})
        markdown = "URL canonica: https://divarioitalia.it/provincia/lecce\n[Puglia](/regione/puglia)"
        self.assertEqual(extract_links(markdown, "text/markdown"), {"/provincia/lecce", "/regione/puglia"})

    def test_un_json_ld_illeggibile_e_un_guasto(self):
        """Un blocco JSON-LD che non si legge non si salta: i suoi link non
        sarebbero controllati e la prova darebbe verde."""
        rotto = ('<script type="application/ld+json">'
                 '{"url": "/pagina-che-non-esiste",}</script>')
        with self.assertRaisesRegex(ValueError, "JSON-LD non valido"):
            extract_links(rotto, "text/html")


class IlLinkAUnaSchedaBesENeHaUnoSolo(unittest.TestCase):
    def test_bes_path_e_il_canonico_della_scheda(self):
        """`bes_path` e' il solo costruttore di link a una scheda BES: per ogni id
        dei due manifest deve dare esattamente il canonico che la scheda dichiara.
        Lo slug dal nome provinciale dava un 301 su tre schede."""
        with app.app_context():
            ids = set(bes_data.get_bes_manifest("regione")) | set(bes_data.get_bes_manifest("provincia"))
            for raw_id in sorted(ids):
                with self.subTest(indicatore=raw_id):
                    vista = indicator_view.build_indicator_view("bes", raw_id)
                    self.assertIsNotNone(vista)
                    self.assertEqual(bes_data.bes_path(raw_id), vista["meta"]["canonical_path"])
                    self.assertEqual(bes_data.bes_path(f"bes:{raw_id}"), vista["meta"]["canonical_path"])

    def test_un_id_sconosciuto_e_un_errore(self):
        with app.app_context(), self.assertRaises(LookupError):
            bes_data.bes_path("NONESISTE")


if __name__ == "__main__":
    unittest.main()
