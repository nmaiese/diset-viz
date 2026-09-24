"""Le pagine aggiunte per le issue #25, #26, #27, #28, #31.

Un file per il gruppo, invece di quattro blocchi sparsi in test_app.py: qui si
guarda a cosa il lettore e il crawler ricevono davvero da /divari-regionali,
/confronto, /ricerca e dalla vista provinciale, non a come sono costruite.
"""

import json
import re
import unittest
from html import unescape
from pathlib import Path

from app import app


INDEX_HEADER = "index, follow, max-snippet:-1, max-image-preview:large"

# Le quattro tipografie che content/STYLE.md vieta nel testo visibile.
FORBIDDEN_CHARS = ("—", "–", "…", ";")


def visible_text(html):
    """Il testo che il lettore vede: via script, style, tag ed entità."""
    stripped = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    return unescape(re.sub(r"<[^>]+>", " ", stripped))


def meta_content(html, name):
    match = re.search(rf'<meta name="{name}" content="([^"]*)"', html)
    return unescape(match.group(1)).strip() if match else None


class ConfrontoPageTest(unittest.TestCase):
    """Issue #31: il comparatore ha una URL pubblica sua, e risponde 200."""

    def test_confronto_is_a_real_page(self):
        client = app.test_client()
        response = client.get("/confronto")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Robots-Tag"], INDEX_HEADER)

        html = response.data.decode("utf-8")
        self.assertIn("<title>Confronta le regioni italiane</title>", html)
        self.assertIn('rel="canonical" href="https://divarioitalia.it/confronto"', html)
        self.assertIn('property="og:title" content="Confronta le regioni italiane"', html)
        self.assertIn('property="og:url" content="https://divarioitalia.it/confronto"', html)
        self.assertIn("BreadcrumbList", html)
        description = meta_content(html, "description")
        self.assertTrue(description)
        self.assertLessEqual(len(description), 155)

        # Il bundle monta la vista confronto perché il template lo dichiara: la
        # SPA non conosce le rotte Flask.
        self.assertIn('window.__diInitialView = "confronto"', html)
        self.assertIn('id="root"', html)

    def test_confronto_works_without_javascript(self):
        client = app.test_client()
        html = client.get("/confronto").data.decode("utf-8")

        # Il fallback server-rendered porta un confronto vero, non una pagina vuota:
        # tre regioni con valore, unita e posizione in classifica.
        self.assertIn("spa-seo-fallback", html)
        self.assertRegex(html, r"\d+ª su \d+")
        links = sorted(set(re.findall(r'href="(/indicatore/[^"]+)"', html)))
        self.assertGreaterEqual(len(links), 3)
        for path in links:
            self.assertEqual(client.get(path).status_code, 200, path)

    def test_compare_tool_has_one_public_url(self):
        client = app.test_client()
        self.assertIn(b"/confronto", client.get("/sitemap.xml").data)

        # Nessun template rimanda piu allo stato SPA: due URL per uno strumento
        # sono due pagine da mantenere e una canonica da spiegare.
        templates = Path(app.root_path) / "templates"
        for template in templates.glob("*.html"):
            self.assertNotIn(
                "/atlante?view=confronto",
                template.read_text(encoding="utf-8"),
                f"{template.name} punta ancora allo stato SPA invece che a /confronto",
            )


class DivariRegionaliPageTest(unittest.TestCase):
    """Issue #25: l'hub sui divari, con una tesi e numeri veri."""

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.response = cls.client.get("/divari-regionali")
        cls.html = cls.response.data.decode("utf-8")

    def test_page_responds_and_is_indexable(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertEqual(self.response.headers["X-Robots-Tag"], INDEX_HEADER)
        self.assertIn('rel="canonical" href="https://divarioitalia.it/divari-regionali"', self.html)
        self.assertIn("BreadcrumbList", self.html)
        self.assertIn(b"/divari-regionali", self.client.get("/sitemap.xml").data)

    def test_metadata_within_serp_budget(self):
        title = unescape(re.search(r"<title>(.*?)</title>", self.html, re.S).group(1)).strip()
        description = meta_content(self.html, "description")
        self.assertLessEqual(len(title), 60, title)
        self.assertIn("Divari regionali", title)
        self.assertGreaterEqual(len(description), 110, description)
        self.assertLessEqual(len(description), 155, description)

    def test_links_to_at_least_fifteen_indicator_pages(self):
        links = sorted(set(re.findall(r'href="(/indicatore/[^"]+)"', self.html)))
        self.assertGreaterEqual(len(links), 15, links)
        for path in links:
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_links_every_region_profile_and_the_compare_tool(self):
        regions = sorted(set(re.findall(r'href="(/regione/[^"]+)"', self.html)))
        self.assertEqual(len(regions), 20, regions)
        self.assertIn('href="/confronto"', self.html)
        self.assertIn("Confronta le tue regioni", self.html)

    def test_shows_the_three_partitions_with_the_interactive_map(self):
        for area in ("Nord", "Centro", "Mezzogiorno"):
            self.assertIn(f'id="divari-{area.lower()}"', self.html)
        # Stesso componente mappa della home: selettore, colori per regione, readout.
        self.assertIn('id="home-map-data"', self.html)
        self.assertIn('action="/divari-regionali"', self.html)
        self.assertIn("home-map.js", self.html)

    def test_numbers_come_from_the_data(self):
        from app import divari

        view = divari.build_divari_view()
        self.assertIsNotNone(view)
        # La tesi della pagina è un conto, non un'opinione: le tre ripartizioni
        # in testa sommano agli indicatori confrontati.
        self.assertEqual(sum(view["tally"].values()), view["scanned"])
        self.assertGreater(view["scanned"], 100)
        self.assertGreater(view["tally"]["Centro"], 0)
        self.assertGreater(view["tally"]["Mezzogiorno"], 0)
        self.assertIn(str(view["scanned"]), self.html)
        self.assertIn(str(view["tally"]["Nord"]), self.html)
        # Ogni divario del set curato ha le tre medie di ripartizione.
        for divario in view["core"] + view["others"]:
            for area in ("Nord", "Centro", "Mezzogiorno"):
                self.assertIn(area, divario["areas"])
                self.assertIsNotNone(divario["areas"][area]["mean"])

    def test_indicator_selector_changes_the_map(self):
        from app import divari

        other = divari.MAP_DIVARI[1]
        html = self.client.get(f"/divari-regionali?indicator={other}").data.decode("utf-8")
        self.assertEqual(self.client.get(f"/divari-regionali?indicator={other}").status_code, 200)
        self.assertIn(f'value="{other}" selected', html)
        # Un id fuori dal set curato non cambia la mappa, non rompe la pagina.
        fallback = self.client.get("/divari-regionali?indicator=non-esiste")
        self.assertEqual(fallback.status_code, 200)

    def test_visible_prose_follows_the_style_guide(self):
        text = visible_text(self.html)
        for char in FORBIDDEN_CHARS:
            self.assertNotIn(char, text, f"tipografia vietata da content/STYLE.md: {char!r}")
        # La pagina dichiara il limite del metodo invece di nasconderlo.
        self.assertIn("medie semplici", text)
        self.assertIn("non pesate per popolazione", text)

    def test_the_simple_mean_is_never_called_national(self):
        """docs/INDICATOR_PAGES.md: una media semplice di valori regionali non è
        la media Italia. Qui la media di venti regioni guida ogni "meglio o
        peggio", quindi chiamarla nazionale sarebbe un numero dichiarato falso."""
        text = visible_text(self.html)
        self.assertIn("media delle venti regioni", text)
        self.assertNotIn("Media Italia", text)
        # L'unica occorrenza ammessa è la frase del metodo che spiega perché la
        # pagina non usa quel nome.
        self.assertEqual(text.count("media nazionale"), 1, "solo la nota di metodo può nominarla")
        self.assertIn('mai "media nazionale"', text)
        self.assertNotIn("Media nazionale", text)

    def test_every_mean_uses_a_year_with_all_twenty_regions(self):
        from app import divari
        from app.atlas_catalog import get_atlas_indicator, get_atlas_indicator_year

        view = divari.build_divari_view()
        for divario in view["core"] + view["others"]:
            covered = sum(area["regions"] for area in divario["areas"].values())
            self.assertEqual(covered, 20, f'{divario["name"]}: media su {covered} regioni')

        # Un anno finale parziale non viene mediato: si scende all'ultimo completo.
        # 144 (presa in carico degli anziani) pubblica il 2022 con 19 regioni.
        partial = "144"
        meta = get_atlas_indicator(partial)["metadata"]
        latest = {
            row["region_key"]
            for row in get_atlas_indicator_year(partial, meta["year_max"])["values"]
            if row.get("value") is not None
        }
        self.assertLess(len(latest), 20, "il caso di prova non è piu parziale, scegline un altro")
        year, values = divari._full_coverage_year(partial, meta["year_max"])
        self.assertIsNotNone(year)
        self.assertLess(year, meta["year_max"])
        self.assertEqual(len({row["region_key"] for row in values if row.get("value") is not None}), 20)

        # E l'anno usato nel conto della tesi è quello, non year_max.
        scanned = {row["id"]: row for row in divari._scan_catalog()}
        self.assertEqual(scanned[partial]["year"], year)


class SearchPageTest(unittest.TestCase):
    """Issue #26: ricerca interna server-rendered, fuori dall'indice per scelta."""

    def test_search_is_noindex_follow_in_header_and_meta(self):
        client = app.test_client()
        response = client.get("/ricerca?q=neet")
        self.assertEqual(response.status_code, 200)
        # L'after_request mette "index, follow" su tutto quello che non si
        # dichiara: header e meta devono dire la stessa cosa.
        self.assertEqual(response.headers["X-Robots-Tag"], "noindex, follow")
        html = response.data.decode("utf-8")
        self.assertEqual(meta_content(html, "robots"), "noindex, follow")
        self.assertIn('rel="canonical" href="https://divarioitalia.it/ricerca?q=neet"', html)

        # Fuori dalla sitemap, ma non bloccata in robots.txt: una pagina
        # disallow non fa leggere il suo noindex. Confronto sulla <loc> esatta,
        # perché "/tema/ricerca-innovazione-e-digitale" contiene la stessa
        # sottostringa ed è una pagina vera, che in sitemap deve restare.
        sitemap = client.get("/sitemap.xml").data.decode("utf-8")
        self.assertNotIn("<loc>https://divarioitalia.it/ricerca</loc>", sitemap)
        self.assertNotIn("divarioitalia.it/ricerca?", sitemap)
        self.assertNotIn("Disallow: /ricerca", client.get("/robots.txt").data.decode("utf-8"))

    def test_results_are_html_from_both_catalog_and_blog(self):
        client = app.test_client()
        html = client.get("/ricerca?q=neet").data.decode("utf-8")
        self.assertIn("Indicatore", html)
        self.assertIn("Articolo", html)
        indicator_links = set(re.findall(r'href="(/indicatore/[^"]+)"', html))
        blog_links = set(re.findall(r'href="(/blog/[^"]+)"', html))
        self.assertTrue(indicator_links)
        self.assertTrue(blog_links)
        for path in list(indicator_links) + list(blog_links):
            self.assertEqual(client.get(path).status_code, 200, path)

    def test_pagination_caps_at_fifty_results(self):
        client = app.test_client()
        first = client.get("/ricerca?q=tasso").data.decode("utf-8")
        self.assertLessEqual(first.count('class="search-result"'), 50)
        self.assertIn("pagina=2", first)
        second = client.get("/ricerca?q=tasso&pagina=2").data.decode("utf-8")
        self.assertIn("Pagina 2 di", second)
        # Una pagina oltre l'ultima non 404: torna sull'ultima.
        self.assertEqual(client.get("/ricerca?q=tasso&pagina=99").status_code, 200)
        self.assertEqual(client.get("/ricerca?q=tasso&pagina=cinque").status_code, 200)

    def test_empty_and_missing_query_still_render(self):
        client = app.test_client()
        empty = client.get("/ricerca")
        self.assertEqual(empty.status_code, 200)
        self.assertIn("Cerca nel catalogo", empty.data.decode("utf-8"))
        nothing = client.get("/ricerca?q=zzzznessunrisultato").data.decode("utf-8")
        self.assertIn("Nessun risultato", nothing)

    def test_site_search_entry_points_lead_to_the_page(self):
        client = app.test_client()
        home = client.get("/").data.decode("utf-8")
        # Il campo di ricerca dell'header, quello del cassetto del telefono, la
        # lente e la SearchAction dello schema puntano tutti alla stessa
        # pagina. I due campi sono form GET veri e la lente un link, quindi la
        # ricerca funziona anche senza JavaScript.
        self.assertIn('class="hdr__search desktop-only" role="search" action="/ricerca"', home)
        self.assertIn('class="msearch mobile-only" role="search" action="/ricerca"', home)
        self.assertIn('class="iconbtn hdr__searchlink" href="/ricerca"', home)
        self.assertIn("/ricerca?q={search_term_string}", home)

        # E ogni altra pagina ha lo stesso punto di arrivo, perche' ormai
        # servono tutte lo stesso chrome: il masthead legacy non esiste piu'.
        blog = client.get("/blog").data.decode("utf-8")
        self.assertIn('class="hdr__search desktop-only" role="search" action="/ricerca"', blog)
        self.assertIn('class="msearch mobile-only" role="search" action="/ricerca"', blog)
        # Il vecchio punto d'ingresso non e' rimasto accanto al nuovo: due
        # ricerche nella stessa pagina sono due comportamenti da tenere
        # allineati, ed e' esattamente cio' che la migrazione toglieva.
        self.assertNotIn('class="masthead__search"', blog)


class ProvinceViewTest(unittest.TestCase):
    """Issue #27, path A: la vista provinciale è uno stato, non una pagina nuova."""

    @staticmethod
    def indicators_with_province_level(limit=3):
        from app import bes_data, indicator_view

        found = []
        for item in bes_data.all_bes_indicators():
            view = indicator_view.build_indicator_view("bes", str(item["id"]))
            if view and any(level["key"] == "provincia" for level in view["levels"]):
                found.append(view)
            if len(found) >= limit:
                break
        return found

    def test_three_indicators_serve_the_provincial_level(self):
        client = app.test_client()
        views = self.indicators_with_province_level()
        self.assertEqual(len(views), 3)

        for view in views:
            base = view["meta"]["canonical_path"]
            regional = client.get(base)
            provincial = client.get(f"{base}?livello=provincia")
            self.assertEqual(provincial.status_code, 200, base)

            html = provincial.data.decode("utf-8")
            # Stato di esplorazione: noindex, follow, e canonica sulla vista base.
            self.assertEqual(provincial.headers["X-Robots-Tag"], "noindex, follow", base)
            self.assertEqual(meta_content(html, "robots"), "noindex, follow", base)
            self.assertIn(f'rel="canonical" href="https://divarioitalia.it{base}"', html)

            # I dati provinciali ci sono, e sono piu delle venti regioni: una riga
            # della classifica per territorio, server-rendered.
            province_rows = len(re.findall(r'<tr data-key="', html))
            region_rows = len(re.findall(r'<tr data-key="', regional.data.decode("utf-8")))
            self.assertEqual(region_rows, 20, base)
            self.assertGreater(province_rows, 90, base)

            # Il selettore del territorio in evidenza è un select: su mobile è il
            # menu a tendina con cui si sceglie una provincia.
            self.assertIn("Trova la tua provincia", html)
            self.assertIn("data-territory", html)
            self.assertIn('href="' + base + '?livello=provincia"', regional.data.decode("utf-8"))

    def test_provincial_level_has_no_map_by_design(self):
        from app import indicator_view

        view = self.indicators_with_province_level(limit=1)[0]
        levels = {level["key"]: level for level in view["levels"]}
        self.assertTrue(levels["regione"]["has_map"])
        # Path A: nessuna mappa a 107 province. Classifica e serie storica bastano.
        self.assertFalse(levels["provincia"]["has_map"])
        self.assertIsNone(levels["provincia"]["map_colors"])
        self.assertIn("provincia", indicator_view.LEVELS)


class MapAccessibilityTest(unittest.TestCase):
    """Issue #28: la mappa dice quale dato disegna, non solo che è una mappa."""

    def test_server_rendered_maps_name_the_indicator(self):
        from app import bes_data, profiles
        from app.data import get_catalog

        client = app.test_client()
        catalog = get_catalog()["indicators"]
        sample = next(item for item in catalog if profiles.is_search_indexable_indicator(item))
        indicator_html = client.get(profiles.indicator_path(sample["id"], sample["name"])).data.decode("utf-8")
        self.assertIn(f'aria-label="Mappa cliccabile delle regioni italiane per {sample["name"]}"', indicator_html)

        # La home cambia indicatore a ogni visita, e solo quello regionale ha
        # la mappa: la si chiede fissando l'indicatore.
        for path in ("/?indicatore=ter-901", "/divari-regionali"):
            html = client.get(path).data.decode("utf-8")
            label = re.search(r'aria-label="(Mappa cliccabile delle regioni italiane[^"]*)"', html)
            self.assertIsNotNone(label, path)
            # Non l'etichetta generica del partial: nomina l'indicatore e l'anno.
            self.assertNotEqual(label.group(1), "Mappa cliccabile delle regioni italiane", path)
            self.assertRegex(label.group(1), r"per .+, \d{4}$", path)

        qol = client.get("/qualita-della-vita/classifica/regioni").data.decode("utf-8")
        self.assertIn("aria-label=\"Mappa cliccabile delle regioni italiane per punteggio", qol)
        self.assertTrue(bes_data.all_bes_indicators())

    def test_react_map_takes_a_label_and_keeps_the_legend_hidden(self):
        source = (Path(app.root_path).parent / "frontend" / "src" / "main.jsx").read_text(encoding="utf-8")
        # Il contenitore accetta un'etichetta e ha ancora role="img": le path
        # sotto restano presentazionali, quindi l'etichetta è l'unica voce.
        self.assertIn('aria-label={label || "Mappa delle regioni italiane"}', source)
        self.assertIn('role="img"', source)
        # Ogni chiamata passa un'etichetta che nomina il dato.
        call_labels = re.findall(r"label=\{?[`\"]([^`\"]*)", source)
        self.assertGreaterEqual(len([lab for lab in call_labels if "Mappa cliccabile" in lab]), 4)
        # La legenda resta fuori dalla lettura assistita per scelta: gli stessi
        # valori stanno nella classifica accanto.
        self.assertIn('className="map-legend" aria-hidden="true"', source)


class PathScopedViewTest(unittest.TestCase):
    """Una vista che possiede una URL non può essere lasciata via ?view=."""

    def test_every_exit_from_a_path_view_is_a_real_navigation(self):
        source = (Path(app.root_path).parent / "frontend" / "src" / "main.jsx").read_text(encoding="utf-8")
        self.assertIn('window.__diInitialView || null', source)
        # Cambio di modalità e apertura di una regione: entrambi escono da
        # /confronto navigando, invece di lasciare /confronto?view=qualcos-altro.
        self.assertIn('window.location.assign(mode === "regioni" ? "/atlante?view=regioni" : "/atlante")', source)
        self.assertIn('window.location.assign(`/atlante?view=regioni&rk=${encodeURIComponent(key)}`)', source)
        # Il bundle servito contiene davvero il gancio: il template lo usa.
        bundle = Path(app.root_path) / "static" / "dist" / "assets" / "index.js"
        self.assertIn("__diInitialView", bundle.read_text(encoding="utf-8"))


class SitemapTest(unittest.TestCase):
    """Cosa entra e cosa resta fuori dalla sitemap, e perché."""

    def test_new_public_pages_are_in_the_sitemap_and_search_is_not(self):
        client = app.test_client()
        sitemap = client.get("/sitemap.xml").data.decode("utf-8")
        locs = set(re.findall(r"<loc>([^<]+)</loc>", sitemap))

        for path in ("/", "/divari-regionali", "/confronto"):
            self.assertIn(f"https://divarioitalia.it{path}", locs, path)
        # La ricerca interna è noindex per scelta, quindi non si annuncia.
        self.assertNotIn("https://divarioitalia.it/ricerca", locs)
        # Le sole query sono profili autonomi della classifica.
        for loc in locs:
            if "?" in loc:
                self.assertRegex(loc, r"/qualita-della-vita/classifica/(regioni|province)\?profilo=[a-z_]+$")
        # Ogni pagina annunciata risponde 200 ed è indicizzabile.
        for path in ("/divari-regionali", "/confronto"):
            response = client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertEqual(response.headers["X-Robots-Tag"], INDEX_HEADER, path)


class IDatiStrutturatiDegliHub(unittest.TestCase):
    """Ogni hub dichiara l'elenco che mostra, e ogni URL elencata risponde.

    `/regioni` era l'unico hub del sito senza un solo blocco JSON-LD, mentre la
    sua `<ol>` delle venti regioni e' esattamente un `ItemList`. La regola di
    `.claude/rules/app.md` e' che il blocco vale solo dove la pagina visibile
    lo sostiene, quindi il test guarda tutte e due le cose insieme: il blocco
    c'e', e le URL che dichiara esistono davvero.
    """

    HUB = {"/regioni": 20, "/temi": 12}

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def _blocchi(self, percorso):
        html = self.client.get(percorso).get_data(as_text=True)
        return [json.loads(b) for b in re.findall(
            r'<script type="application/ld\+json">\s*(.*?)\s*</script>', html, re.S)]

    def test_ogni_hub_dichiara_il_suo_elenco(self):
        for percorso, attesi in self.HUB.items():
            with self.subTest(percorso=percorso):
                tipi = {b.get("@type") for b in self._blocchi(percorso)}
                self.assertIn("ItemList", tipi)
                self.assertIn("BreadcrumbList", tipi)
                elenco = next(b for b in self._blocchi(percorso) if b["@type"] == "ItemList")
                self.assertEqual(len(elenco["itemListElement"]), attesi)
                self.assertEqual(elenco["numberOfItems"], attesi)

    def test_le_posizioni_sono_progressive_e_senza_buchi(self):
        for percorso in self.HUB:
            with self.subTest(percorso=percorso):
                elenco = next(b for b in self._blocchi(percorso) if b["@type"] == "ItemList")
                posizioni = [v["position"] for v in elenco["itemListElement"]]
                self.assertEqual(posizioni, list(range(1, len(posizioni) + 1)))

    def test_ogni_url_elencata_risponde(self):
        """Un `ItemList` che punta a una pagina che non c'e' e' peggio di niente."""
        for percorso in self.HUB:
            elenco = next(b for b in self._blocchi(percorso) if b["@type"] == "ItemList")
            for voce in elenco["itemListElement"]:
                rotta = voce["url"].split("divarioitalia.it", 1)[-1]
                with self.subTest(percorso=percorso, voce=voce["name"]):
                    self.assertEqual(self.client.get(rotta).status_code, 200, rotta)


if __name__ == "__main__":
    unittest.main()


class LaPaginaTemaRisponde(unittest.TestCase):
    """La pagina tema era un elenco di link e non prendeva clic.

    Il test guarda cosa riceve chi arriva da una ricerca: una risposta in cima,
    una classifica con venti link a regioni, gli indicatori in gerarchia invece
    che in un muro di schede uguali, e un'uscita. Piu' i due temi su cui la
    classifica non si puo' calcolare, dove la pagina deve **non** fingerla.
    """

    TEMA = "/tema/lavoro-e-conciliazione"

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()
        cls.html = cls.client.get(cls.TEMA).get_data(as_text=True)

    def test_la_classifica_porta_venti_link_a_regione(self):
        """E' l'equity che prima la pagina non passava a nessuno: venti profili
        regione erano orfani, e il tema non li nominava."""
        regioni = sorted(set(re.findall(r'href="(/regione/[^"]+)"', self.html)))
        self.assertEqual(len(regioni), 20, regioni)
        for percorso in regioni:
            self.assertEqual(self.client.get(percorso).status_code, 200, percorso)

    def test_la_mappa_e_colorata_dalla_rampa_del_design_system(self):
        """Un colore cotto qui non seguirebbe il tema scuro."""
        fills = re.findall(r'\.theme-map \[data-key="[^"]+"\]\{fill:([^}]+)\}', self.html)
        self.assertEqual(len(fills), 20, fills)
        for fill in fills:
            self.assertRegex(fill.strip(), r"^var\(--seq-[1-6]\)$")

    def test_la_pagina_dichiara_il_metodo_invece_di_nasconderlo(self):
        testo = visible_text(self.html)
        self.assertIn("media semplice", testo)
        self.assertIn("Non è una classifica ufficiale", testo)

    def test_gli_indicatori_in_evidenza_non_sono_varianti_della_stessa_misura(self):
        """Ordinando per sola solidita' uscivano cinque schede che erano quattro
        varianti della stessa cosa: tutte complete, tutte aggiornate, tutte che
        dicono al lettore lo stesso."""
        from app import atlas_catalog, views

        profilo = atlas_catalog.get_atlas_theme_profile("lavoro-e-conciliazione")
        scelti = views._theme_featured(profilo)
        misure = [views._misura_di(i["name"]) for i in scelti]
        self.assertEqual(len(misure), len(set(misure)), misure)

    def test_c_e_un_uscita_in_fondo(self):
        """Era l'unica pagina del sito senza blocco finale."""
        self.assertIn('class="theme-next"', self.html)
        self.assertIn("indicator-cta", self.html)

    def test_il_titolo_e_la_descrizione_stanno_nel_budget(self):
        from app import atlas_catalog

        for voce in atlas_catalog.all_atlas_themes_index():
            html = self.client.get(voce["path"]).get_data(as_text=True)
            titolo = unescape(re.search(r"<title>(.*?)</title>", html, re.S).group(1)).strip()
            descrizione = meta_content(html, "description")
            with self.subTest(tema=voce["theme"]):
                self.assertLessEqual(len(titolo), 60, titolo)
                self.assertLessEqual(len(descrizione), 155, descrizione)
                self.assertGreaterEqual(len(descrizione), 80, descrizione)

    def test_dove_la_classifica_non_si_calcola_la_pagina_non_la_finge(self):
        from app import atlas_catalog, profiles

        senza = [v for v in atlas_catalog.all_atlas_themes_index()
                 if not profiles.theme_standings(v["theme"])["rated"]]
        if not senza:
            self.skipTest("tutti i temi hanno una classifica")
        for voce in senza:
            html = self.client.get(voce["path"]).get_data(as_text=True)
            with self.subTest(tema=voce["theme"]):
                self.assertNotIn('class="theme-standings"', html)
                self.assertNotIn("ItemList", html)
                self.assertIn("non esce una classifica regionale", visible_text(html))

    def test_la_variante_markdown_porta_la_stessa_risposta(self):
        """HTML e Markdown sono lo stesso documento alla stessa URL: una
        variante senza la risposta principale e' un'altra pagina col canonico
        di questa."""
        testo = self.client.get(
            self.TEMA, headers={"Accept": "text/markdown"}).get_data(as_text=True)
        self.assertIn("## Le regioni su questo tema", testo)
        self.assertEqual(testo.count("/regione/"), 20)

    def test_la_prosa_visibile_segue_la_guida_di_stile(self):
        testo = visible_text(self.html)
        for vietato in FORBIDDEN_CHARS:
            self.assertNotIn(vietato, testo, f"tipografia vietata: {vietato!r}")


class LaClassificaQualitaDellaVitaPortaDaQualcheParte(unittest.TestCase):
    """Venti regioni e 103 province erano testo nudo.

    La pagina sta in posizione 4,1 per "classifica regioni italiane per
    qualita' della vita" ed era un vicolo cieco: il territorio si leggeva e
    non si apriva. Le province non hanno un profilo, quindi li' la porta e' la
    colonna della regione.
    """

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def test_ogni_regione_in_classifica_apre_il_suo_profilo(self):
        html = self.client.get("/qualita-della-vita/classifica/regioni").get_data(as_text=True)
        link = sorted(set(re.findall(r'href="(/regione/[^"]+)"', html)))
        self.assertEqual(len(link), 20, link)
        for percorso in link:
            self.assertEqual(self.client.get(percorso).status_code, 200, percorso)

    def test_le_province_aprono_la_loro_regione(self):
        html = self.client.get("/qualita-della-vita/classifica/province").get_data(as_text=True)
        link = sorted(set(re.findall(r'href="(/regione/[^"]+)"', html)))
        self.assertGreaterEqual(len(link), 18, link)
        for percorso in link:
            self.assertEqual(self.client.get(percorso).status_code, 200, percorso)

    def test_un_territorio_senza_profilo_non_prende_un_link_finto(self):
        """`region_key_for` slugifica qualunque stringa: da "Provincia Autonoma
        Bolzano" usciva un link a una pagina che non esiste. Si valida contro
        le regioni vere, non contro il fatto che una chiave sia uscita."""
        html = self.client.get("/qualita-della-vita/classifica/province").get_data(as_text=True)
        self.assertNotIn("/regione/provincia-autonoma", html)


class LaPaginaRegioneChiudeLaMaglia(unittest.TestCase):
    """Tema e regione erano due elenchi che non si nominavano a vicenda.

    La pagina tema dice da tempo "su questo tema il Molise e' 17esimo". La
    pagina regione elencava i suoi temi con il solo conteggio degli indicatori,
    quindi il lettore arrivato da un tema non ritrovava il numero da cui veniva,
    e il collegamento fra le due pagine restava a senso unico.
    """

    def setUp(self):
        self.client = app.test_client()

    def test_ogni_tema_classificato_porta_il_suo_rango(self):
        html = self.client.get("/regione/molise").get_data(as_text=True)
        self.assertRegex(html, r"\d+ª su 20")

    def test_il_rango_e_lo_stesso_che_dichiara_la_pagina_tema(self):
        """Due percorsi che calcolano la stessa cosa devono dare lo stesso
        numero, se no una delle due pagine mente."""
        from app import profiles

        profilo = profiles.region_profile("molise")
        for riga in profilo["theme_table"]:
            if not riga["rank"]:
                continue
            with self.subTest(tema=riga["theme"]):
                classifica = profiles.theme_standings(riga["theme"])
                atteso = next(r["rank"] for r in classifica["rows"]
                              if r["region_key"] == "molise")
                self.assertEqual(riga["rank"], atteso)

    def test_un_tema_che_non_si_classifica_non_si_inventa_una_posizione(self):
        from app import profiles

        profilo = profiles.region_profile("molise")
        for riga in profilo["theme_table"]:
            if not riga["rated"]:
                self.assertIsNone(riga["rank"], riga["theme"])

    def test_l_itemlist_elenca_solo_i_temi_che_hanno_un_rango(self):
        html = self.client.get("/regione/molise").get_data(as_text=True)
        blocchi = [json.loads(b) for b in
                   re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]
        liste = [b for b in blocchi if b.get("@type") == "ItemList"]
        self.assertEqual(len(liste), 1)
        from app import profiles

        con_rango = [t for t in profiles.region_profile("molise")["theme_table"] if t["rank"]]
        self.assertEqual(liste[0]["numberOfItems"], len(con_rango))
        self.assertEqual(len(liste[0]["itemListElement"]), len(con_rango))

    def test_il_ritratto_usa_il_percentile_grezzo_non_il_punteggio_orientato(self):
        """La figura ha per assi "il valore piu' basso" e "il valore piu' alto":
        un punteggio orientato metterebbe il punto dalla parte sbagliata su ogni
        indicatore dove il valore basso e' quello buono."""
        from app import profiles

        profilo = profiles.region_profile("molise")
        per_nome = {e["name"]: e for e in profilo["top_excels"] + profilo["top_lags"]}
        self.assertTrue(profilo["portrait_rows"])
        for nome, quota in profilo["portrait_rows"]:
            with self.subTest(indicatore=nome):
                self.assertEqual(quota, per_nome[nome]["percentile"])

    def test_il_gemello_markdown_porta_la_stessa_tabella(self):
        testo = self.client.get(
            "/regione/molise", headers={"Accept": "text/markdown"}).get_data(as_text=True)
        self.assertIn("## Tutti i temi, con la posizione fra le 20 regioni", testo)
        self.assertIn(" su 20 |", testo)


class IlPercorsoVisibileEQuelloDichiarato(unittest.TestCase):
    """`BreadcrumbList` e `<nav>` devono dire la stessa cosa.

    Erano cinque forme scritte a mano in nove template, e i due pezzi stavano a
    settanta righe di distanza nello stesso file: la scheda indicatore
    dichiarava Home > Temi > tema > indicatore e a schermo si leggeva
    "Temi / tema". Il catalogo dati mostrava un percorso e non lo dichiarava,
    quattro pagine lo dichiaravano e non lo mostravano, e la pagina tema
    linkava un'ancora di `/temi` che non e' mai esistita.

    Adesso la lista e' una sola per pagina e questi due percorsi ne escono.
    """

    PAGINE = (
        "/regioni", "/temi", "/tema/lavoro-e-conciliazione", "/regione/molise",
        "/indicatore/pil-pro-capite/ter-901", "/qualita-della-vita/classifica/regioni",
        "/divari-regionali", "/quiz", "/quiz/indovina-la-regione", "/metodologia",
        "/confronto", "/catalogo-dati", "/province", "/provincia/lecce",
        "/qualita-della-vita",
    )

    def setUp(self):
        self.client = app.test_client()

    def _percorsi(self, path):
        html = self.client.get(path).get_data(as_text=True)
        nav = re.search(r'<nav[^>]*aria-label="Percorso".*?</nav>', html, re.S)
        visibile = None
        if nav:
            voci = [unescape(v).strip() for v in re.findall(r">([^<>]+)</(?:a|span)>", nav.group(0))]
            visibile = [v for v in voci if v and v != "/"]
        dichiarato = None
        for blocco in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
            documento = json.loads(blocco)
            if documento.get("@type") == "BreadcrumbList":
                dichiarato = [e["name"] for e in documento["itemListElement"]]
        return visibile, dichiarato

    def test_il_visibile_e_il_dichiarato_coincidono(self):
        for path in self.PAGINE:
            with self.subTest(path=path):
                visibile, dichiarato = self._percorsi(path)
                self.assertIsNotNone(visibile, f"{path}: nessun percorso visibile")
                self.assertIsNotNone(dichiarato, f"{path}: nessun BreadcrumbList")
                self.assertEqual(visibile, dichiarato)

    def test_ogni_percorso_parte_da_home_e_finisce_sulla_pagina(self):
        for path in self.PAGINE:
            with self.subTest(path=path):
                _, dichiarato = self._percorsi(path)
                self.assertEqual(dichiarato[0], "Home")
                self.assertGreaterEqual(len(dichiarato), 2)

    def test_l_ultima_voce_non_e_un_link(self):
        """Lo schema vuole `item` sull'ultima voce, l'occhio non vuole un link
        alla pagina su cui si trova gia'."""
        for path in self.PAGINE:
            with self.subTest(path=path):
                html = self.client.get(path).get_data(as_text=True)
                nav = re.search(r'<nav[^>]*aria-label="Percorso".*?</nav>', html, re.S)
                self.assertIn('class="breadcrumb__here"', nav.group(0))

    def test_ogni_voce_del_percorso_risponde(self):
        """Un percorso che porta a un 404 e' peggio di nessun percorso."""
        for path in self.PAGINE:
            html = self.client.get(path).get_data(as_text=True)
            nav = re.search(r'<nav[^>]*aria-label="Percorso".*?</nav>', html, re.S)
            for href in re.findall(r'href="([^"]+)"', nav.group(0)):
                with self.subTest(path=path, href=href):
                    self.assertEqual(self.client.get(href).status_code, 200)

    def test_una_sola_lista_per_pagina(self):
        """Due `<nav aria-label="Percorso">` sulla stessa pagina sono un percorso
        doppio a schermo e due punti di riferimento con lo stesso nome per chi
        naviga con la tastiera. `/divari-regionali` ne aveva due: il macro nuovo
        sopra il `nav.divari-crumbs` che c'era gia', e si leggevano uno sotto
        l'altro con due separatori diversi."""
        for path in self.PAGINE:
            with self.subTest(path=path):
                html = self.client.get(path).get_data(as_text=True)
                self.assertEqual(len(re.findall(r'<nav[^>]*aria-label="Percorso"', html)), 1)

    def test_il_separatore_ha_spazio_da_tutte_e_due_le_parti(self):
        """In pagina si leggeva `Home /Temi /Reddito, inclusione e accessibilita'`.

        Lo spazio prima della barra sta nel markup, quello dopo se lo mangiava
        il `{%- endif %}` del macro. Non lo vede nessuna delle prove qui sopra,
        perche' confrontano i nomi dopo aver tolto i tag, ed e' esattamente il
        tipo di difetto che si vede solo guardando la pagina.
        """
        for path in self.PAGINE:
            with self.subTest(path=path):
                html = self.client.get(path).get_data(as_text=True)
                nav = re.search(r'<nav[^>]*aria-label="Percorso".*?</nav>', html, re.S).group(0)
                self.assertNotIn("</span><a", nav)
                self.assertNotIn("</span><span", nav)

    def test_l_ancora_della_macro_area_esiste_davvero(self):
        """La pagina tema linkava `/temi#reddito-inclusione-e-accessibilità`,
        che `/temi` non ha mai emesso: lo slug era calcolato nel template con
        `lower | replace`, non con `slugify_taxonomy`."""
        tema = self.client.get("/tema/lavoro-e-conciliazione").get_data(as_text=True)
        nav = re.search(r'<nav[^>]*aria-label="Percorso".*?</nav>', tema, re.S).group(0)
        ancore = [h for h in re.findall(r'href="(/temi#[^"]+)"', nav)]
        self.assertTrue(ancore)
        temi = self.client.get("/temi").get_data(as_text=True)
        for ancora in ancore:
            with self.subTest(ancora=ancora):
                self.assertIn(f'id="{ancora.split("#", 1)[1]}"', temi)


class LePagineProvincia(unittest.TestCase):
    """103 province misurate e nessuna con una pagina.

    Il sito le classifica tutte nella qualita' della vita, e il commento che
    costruisce quella classifica lo diceva: "Le province non hanno un profilo,
    ma la loro regione si', quindi il nome della regione diventa la porta".
    Cioe' chi cercava "qualita' della vita provincia di Lecce" arrivava, nel
    migliore dei casi, su una tabella di 103 righe. Il dato c'era tutto:
    mancava la superficie.
    """

    @classmethod
    def setUpClass(cls):
        from app import province_profile

        cls.province = province_profile
        cls.chiavi = province_profile.chiavi()

    def setUp(self):
        self.client = app.test_client()

    def test_ce_ne_sono_centosette(self):
        """Erano 103: una regex della pipeline scartava i codici IT1xx di
        Monza e della Brianza, Fermo, Barletta-Andria-Trani e Sud Sardegna."""
        self.assertEqual(len(self.chiavi), 107)

    def test_rispondono_tutte(self):
        for chiave in self.chiavi:
            with self.subTest(provincia=chiave):
                self.assertEqual(self.client.get(f"/provincia/{chiave}").status_code, 200)

    def test_una_chiave_inventata_fa_404(self):
        self.assertEqual(self.client.get("/provincia/atlantide").status_code, 404)

    def test_titolo_e_descrizione_stanno_nel_budget(self):
        """Il nome piu' lungo, "Verbano-Cusio-Ossola", portava il titolo a
        sessantaquattro: li' cade la coda "per qualita' della vita"."""
        for chiave in self.chiavi:
            with self.subTest(provincia=chiave):
                html = self.client.get(f"/provincia/{chiave}").get_data(as_text=True)
                titolo = unescape(re.search(r"<title>(.*?)</title>", html, re.S).group(1))
                descrizione = unescape(
                    re.search(r'<meta name="description" content="(.*?)"', html, re.S).group(1))
                self.assertLessEqual(len(titolo), 60, titolo)
                self.assertLessEqual(len(descrizione), 160, descrizione)
                self.assertIn("province", titolo)

    def test_una_sola_intestazione_e_un_canonico_che_punta_a_se(self):
        for chiave in self.chiavi[:12]:
            with self.subTest(provincia=chiave):
                html = self.client.get(f"/provincia/{chiave}").get_data(as_text=True)
                self.assertEqual(len(re.findall(r"<h1[^>]*>", html)), 1)
                canonico = re.search(r'<link rel="canonical" href="([^"]+)"', html).group(1)
                self.assertTrue(canonico.endswith(f"/provincia/{chiave}"), canonico)

    def test_dichiarano_percorso_e_dataset(self):
        for chiave in self.chiavi[:12]:
            with self.subTest(provincia=chiave):
                html = self.client.get(f"/provincia/{chiave}").get_data(as_text=True)
                tipi = [json.loads(b).get("@type")
                        for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]
                self.assertIn("BreadcrumbList", tipi)
                self.assertIn("Dataset", tipi)

    def test_stanno_tutte_in_sitemap(self):
        sitemap = self.client.get("/sitemap.xml").get_data(as_text=True)
        for chiave in self.chiavi:
            with self.subTest(provincia=chiave):
                self.assertIn(f"/provincia/{chiave}<", sitemap)

    def test_la_classifica_porta_a_ognuna(self):
        """Le righe erano testo nudo, su una pagina che sta in posizione 4,1
        per la sua query principale."""
        html = self.client.get("/qualita-della-vita/classifica/province").get_data(as_text=True)
        link = set(re.findall(r'href="(/provincia/[a-z0-9-]+)"', html))
        self.assertEqual(len(link), len(self.chiavi))
        for percorso in sorted(link)[:10]:
            with self.subTest(percorso=percorso):
                self.assertEqual(self.client.get(percorso).status_code, 200)

    def test_la_pagina_porta_alla_sua_regione(self):
        html = self.client.get("/provincia/lecce").get_data(as_text=True)
        self.assertIn('href="/regione/puglia"', html)

    def test_bolzano_e_trento_non_inventano_una_regione(self):
        """Dichiarano "Provincia Autonoma Bolzano", che slugificata darebbe un
        link a una pagina che non esiste: e' lo stesso controllo della
        classifica, e per la stessa ragione."""
        for chiave in ("bolzano", "trento"):
            with self.subTest(provincia=chiave):
                html = self.client.get(f"/provincia/{chiave}").get_data(as_text=True)
                for percorso in re.findall(r'href="(/regione/[a-z0-9-]+)"', html):
                    self.assertEqual(self.client.get(percorso).status_code, 200, percorso)

    def test_la_variante_markdown_porta_la_stessa_risposta(self):
        """HTML e Markdown sono lo stesso documento alla stessa URL: se la
        variante non porta posizione e punteggio e' una pagina diversa sotto lo
        stesso canonico."""
        for chiave in ("lecce", "trieste"):
            with self.subTest(provincia=chiave):
                markdown = self.client.get(
                    f"/provincia/{chiave}", headers={"Accept": "text/markdown"}).get_data(as_text=True)
                profilo = self.province.profilo(chiave)
                self.assertIn(f"{profilo['rank']}ª su {profilo['total']}", markdown)
                # Il punteggio scritto come nell'HTML, con la virgola: il
                # `str(score)` di prima fissava il punto decimale.
                self.assertIn(app.jinja_env.filters["it_num"](profilo["score"]), markdown)
                self.assertIn("## Le dimensioni", markdown)


class ItaliaRegioneProvincia(unittest.TestCase):
    """Le province sono il terzo livello della geografia del sito.

    Il 22/9/2026 le linkavano in mediana 7 pagine, contro le 611 di una
    regione: arrivava un link solo dalla classifica e dalle altre province.
    Nessuna regione linkava le sue, non c'era un indice, e la briciola le
    metteva sotto la qualita' della vita.
    """

    @classmethod
    def setUpClass(cls):
        from app import profiles, province_profile
        cls.client = app.test_client()
        with app.app_context():
            cls.chiavi = province_profile.chiavi()
            cls.per_regione = province_profile.by_region()
            cls.regioni = profiles.regions_overview()

    def _link(self, percorso, prefisso="/provincia/"):
        html = self.client.get(percorso).get_data(as_text=True)
        return set(re.findall(rf'href="({re.escape(prefisso)}[a-z0-9-]+)"', html))

    def test_l_indice_porta_a_ogni_provincia(self):
        self.assertEqual(self.client.get("/province").status_code, 200)
        self.assertEqual(self._link("/province"), {f"/provincia/{k}" for k in self.chiavi})

    def test_ogni_regione_porta_alle_sue_province(self):
        for chiave_regione, province in self.per_regione.items():
            with self.subTest(regione=chiave_regione):
                self.assertTrue(province, f"{chiave_regione} senza province")
                self.assertTrue({p["path"] for p in province} <= self._link(f"/regione/{chiave_regione}"))

    def test_ogni_provincia_porta_alla_sua_regione(self):
        regione_di = {p["key"]: k for k, province in self.per_regione.items() for p in province}
        for chiave in self.chiavi:
            with self.subTest(provincia=chiave):
                self.assertIn(f"/regione/{regione_di[chiave]}",
                              self._link(f"/provincia/{chiave}", "/regione/"))

    def test_provincia_senza_chiave_porta_all_indice(self):
        for percorso in ("/provincia", "/provincia/"):
            with self.subTest(percorso=percorso):
                risposta = self.client.get(percorso)
                self.assertEqual(risposta.status_code, 301)
                self.assertTrue(risposta.headers["Location"].endswith("/province"))

    def test_l_indice_e_nel_menu_nella_sitemap_e_in_markdown(self):
        from app import nav
        territori = next(voce for voce in nav.PRIMARY if voce.get("key") == "territori")
        self.assertIn("/province", [voce["path"] for voce in territori["group"]])
        self.assertIn("/province<", self.client.get("/sitemap.xml").get_data(as_text=True))
        markdown = self.client.get("/province", headers={"Accept": "text/markdown"}).get_data(as_text=True)
        self.assertIn(f"# Le {len(self.chiavi)} province italiane", markdown)

    def test_la_regione_si_chiama_allo_stesso_modo_dappertutto(self):
        """Il Trentino era "Provincia Autonoma Bolzano" per le sue province."""
        from app import province_profile
        nome = self.regioni["trentino-alto-adige"]["region"]
        for chiave in ("bolzano", "trento"):
            with self.subTest(provincia=chiave):
                self.assertEqual(province_profile.profilo(chiave)["region"], nome)

    def test_l_api_della_regione_porta_le_province(self):
        dati = self.client.get("/api/region/puglia").get_json()
        self.assertEqual({p["key"] for p in dati["provinces"]},
                         {p["key"] for p in self.per_regione["puglia"]})


class LeProvincePerLeMacchine(unittest.TestCase):
    """llms.txt, llms-full.txt, SKILL.md, OpenAPI e i Markdown non nominavano
    le province: un modello che leggeva il sito non sapeva che esistessero."""

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def test_llms_e_llms_full_portano_le_province(self):
        from app import province_profile
        self.assertIn("/province)", self.client.get("/llms.txt").get_data(as_text=True))
        completo = self.client.get("/llms-full.txt").get_data(as_text=True)
        self.assertIn("## Province", completo)
        with app.app_context():
            for chiave in province_profile.chiavi():
                self.assertIn(f"/provincia/{chiave})", completo)

    def test_lo_skill_e_l_openapi_portano_le_province(self):
        skill = self.client.get("/.well-known/agent-skills/query-divario-italia/SKILL.md").get_data(as_text=True)
        self.assertIn("/provincia/<key>", skill)
        self.assertIn("/province", skill)
        percorsi = self.client.get("/openapi.json").get_json()["paths"]
        for percorso in ("/api/quality-life/{level}/rankings", "/api/quality-life/{level}/{key}"):
            self.assertIn(percorso, percorsi)

    def test_la_scheda_in_markdown_lega_i_territori_e_dice_l_altro_livello(self):
        """HTML e Markdown sono lo stesso documento: la tabella HTML lega ogni
        riga al profilo, e il selettore porta alle province."""
        base = "/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001"
        regioni = self.client.get(base, headers={"Accept": "text/markdown"}).get_data(as_text=True)
        self.assertRegex(regioni, r"\| \[[^]]+\]\(\S*/regione/[a-z-]+\) \|")
        self.assertIn(f"{base}?livello=provincia", regioni)
        province = self.client.get(base + "?livello=provincia", headers={"Accept": "text/markdown"}).get_data(as_text=True)
        self.assertGreaterEqual(province.count("/provincia/"), 100)
        self.assertIn(f"{base}?livello=regione", province)

    def test_la_provincia_in_markdown_porta_le_sorelle(self):
        markdown = self.client.get("/provincia/lecce", headers={"Accept": "text/markdown"}).get_data(as_text=True)
        self.assertIn("## Le province della Puglia", markdown)
        for sorella in ("bari", "barletta-andria-trani", "brindisi", "foggia", "taranto"):
            self.assertIn(f"/provincia/{sorella})", markdown)
        self.assertIn("Lecce (questa pagina)", markdown)
        self.assertIn("/province\n", markdown + "\n")

    def test_llms_full_e_lo_skill_dicono_dove_stanno_i_valori_per_provincia(self):
        completo = self.client.get("/llms-full.txt").get_data(as_text=True)
        self.assertIn("bes-01SAL001?livello=provincia", completo)
        skill = self.client.get("/.well-known/agent-skills/query-divario-italia/SKILL.md").get_data(as_text=True)
        self.assertIn("?livello=provincia", skill)

    def test_home_e_metodologia_in_markdown_portano_le_province(self):
        for percorso in ("/", "/metodologia"):
            with self.subTest(pagina=percorso):
                markdown = self.client.get(percorso, headers={"Accept": "text/markdown"}).get_data(as_text=True)
                self.assertIn("/province)", markdown)

    def test_la_qualita_della_vita_parla_di_regioni_e_province(self):
        html = self.client.get("/qualita-della-vita").get_data(as_text=True)
        self.assertIn("<h1>Qualità della vita nelle regioni e nelle province italiane</h1>", html)
        self.assertNotIn("in revisione", html)
        self.assertIn('href="/province"', html)

    def test_la_faq_dichiarata_e_quella_che_si_legge(self):
        """Il JSON-LD della FAQ era scritto senza accenti ("qualita", "Si"),
        la pagina con: due testi diversi per la stessa risposta."""
        import html as html_lib
        import json
        pagina = self.client.get("/metodologia").get_data(as_text=True)
        faq = next(json.loads(b) for b in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', pagina, re.DOTALL) if '"FAQPage"' in b)
        visibile = html_lib.unescape(re.sub(r"<[^>]+>", "", pagina[pagina.index('class="prose faq"'):]))
        visibile = " ".join(visibile.split())
        for voce in faq["mainEntity"]:
            with self.subTest(domanda=voce["name"]):
                self.assertIn(voce["name"], visibile)
                self.assertIn(" ".join(voce["acceptedAnswer"]["text"].split()), visibile)


class LaHomePortaAlleProvince(unittest.TestCase):
    """La home contava "20 regioni" scritto a mano in sei posti, e dalla home
    non si arrivava a nessuna provincia."""

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.html = cls.client.get("/").get_data(as_text=True)

    def test_la_home_porta_all_indice_e_alle_province(self):
        self.assertIn('href="/province"', self.html)
        self.assertRegex(self.html, r'href="/provincia/[a-z0-9-]+"')

    def test_regioni_e_province_hanno_anteprima_e_indice(self):
        """La fascia dei territori porta a una regione e a una provincia (quelle
        estratte a caso) e ai due indici, e ogni link e' una pagina che
        risponde. Il podio della qualita' della vita, che faceva lo stesso,
        non c'e' piu': la home non svela la classifica."""
        blocco = self.html[self.html.index('id="territori"'):self.html.index('id="temi"')]
        link = set(re.findall(r'<h4 class="terr__name"><a href="(/(?:regione|provincia)/[a-z0-9-]+)"', blocco))
        self.assertTrue(any(h.startswith("/regione/") for h in link), link)
        self.assertTrue(any(h.startswith("/provincia/") for h in link), link)
        self.assertIn('href="/regioni"', blocco)
        self.assertIn('href="/province"', blocco)
        for percorso in link:
            with self.subTest(percorso=percorso):
                self.assertEqual(self.client.get(percorso).status_code, 200)

    def test_i_conteggi_dei_territori_non_sono_scritti_a_mano(self):
        from pathlib import Path
        for nome in ("home.html", "region_page.html", "v1/home.html", "v1/regione.html"):
            testo = (Path(app.root_path) / "templates" / nome).read_text(encoding="utf-8")
            testo = re.sub(r"\{#.*?#\}", "", testo, flags=re.DOTALL)
            with self.subTest(template=nome):
                self.assertNotRegex(testo, r"\b(?:20|venti) regioni\b")
                self.assertNotRegex(testo, r"<strong>20</strong>")
        from app import province_profile
        totale = province_profile.total()
        self.assertIn(f'<data class="n n--count" value="{totale}">{totale}</data> province', self.html)


class IRimandiAllAtlanteDiconoIlVero(unittest.TestCase):
    """Ogni rimando all'atlante porta dove dice.

    La pagina tema diceva "58 indicatori" e "Aprili nell'atlante", e l'atlante
    si apriva senza filtro, sulle serie complete di tutti i temi. La scheda
    diceva "Apri l'indicatore nell'atlante", che non apre nessuna scheda. La
    porta della home prometteva la mappa "anno per anno", che l'atlante non ha.
    `/regioni` portava a `?view=regioni`, che ripete le pagine regione.

    Il conto rifa' il filtro di `AtlasView` (`frontend/src/main.jsx`): il nome
    del tema confrontato con `item.theme` del catalogo, e senza `partial=1`
    solo le serie complete.
    """

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    @staticmethod
    def _rimandi(html):
        """I link all'atlante nel corpo della pagina, fuori da testata e piede."""
        corpo = re.search(r"<(article|main)\b.*?</\1>", html, re.DOTALL).group(0)
        return [unescape(h) for h in re.findall(r'href="(/atlante[^"]*)"', corpo)]

    @staticmethod
    def _cosa_mostra_l_atlante(link):
        from urllib.parse import parse_qs, urlsplit

        from app.atlas_catalog import get_atlas_catalog

        query = parse_qs(urlsplit(link).query)
        tema = query["theme"][0]
        parziali = query.get("partial") == ["1"]
        return [i for i in get_atlas_catalog()["indicators"]
                if i["theme"] == tema and (parziali or i["complete"])]

    def test_la_pagina_tema_apre_l_atlante_sui_suoi_indicatori(self):
        from app import atlas_catalog

        for voce in atlas_catalog.all_atlas_themes_index():
            html = self.client.get(voce["path"]).get_data(as_text=True)
            dichiarati = int(re.search(r"<small>Indicatori</small><strong>(\d+)</strong>", html).group(1))
            rimandi = self._rimandi(html)
            with self.subTest(tema=voce["theme"]):
                self.assertEqual(len(rimandi), 2, rimandi)
                for link in rimandi:
                    self.assertEqual(len(self._cosa_mostra_l_atlante(link)), dichiarati, link)

    def test_la_scheda_apre_l_atlante_sul_suo_tema(self):
        """Anche le serie regionali fuori dal catalogo dell'atlante (qui la
        speranza di vita, BES) hanno un tema che l'atlante conosce."""
        for percorso in ("/indicatore/tasso-di-turisticita/ter-105",
                         "/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001"):
            html = self.client.get(percorso, follow_redirects=True).get_data(as_text=True)
            rimandi = self._rimandi(html)
            with self.subTest(scheda=percorso):
                self.assertNotIn("Apri l'indicatore nell'atlante", visible_text(html))
                self.assertEqual(len(rimandi), 1, rimandi)
                self.assertTrue(self._cosa_mostra_l_atlante(rimandi[0]), rimandi[0])

    def test_ogni_scheda_regionale_ha_un_tema_che_l_atlante_conosce(self):
        """La prova qui sopra guarda due schede: questa le guarda tutte.

        Il link della scheda al livello regione e' `atlas_theme_url(meta.theme)`.
        Le serie BES fuori dal catalogo dell'atlante prendono il tema da
        `category_name` o `domain_name` (`app/indicator_view.py`): una serie
        nuova con un dominio che il catalogo non conosce aprirebbe un atlante
        con la lista vuota, e un tema vuoto l'atlante intero sotto la voce "Gli
        indicatori del tema". Nessuna richiesta HTTP: la proiezione e' in cache."""
        from app import indicator_universe
        from app.atlas_catalog import get_atlas_catalog

        themes = {i["theme"] for i in get_atlas_catalog()["indicators"]}
        regional = [r for r in indicator_universe.projection()
                    if any(level["key"] == "regione" for level in r["levels"])]
        self.assertTrue(regional)
        unknown = sorted(f"{r['family']}:{r['raw_id']} ({r['meta'].get('theme')!r})"
                         for r in regional
                         if not r["meta"].get("theme") or r["meta"]["theme"] not in themes)
        self.assertEqual(unknown, [])

    def test_la_porta_della_home_dice_quanti_indicatori_apre(self):
        """La porta diceva "594 indicatori" e apriva una lista di 447: senza
        `partial=1` l'atlante mostra solo le serie complete. Il conto si rifa'
        sul catalogo, non su `catalog_summary`, che e' lo stesso numero che la
        porta legge."""
        from app import cache
        from app.atlas_catalog import get_atlas_catalog
        from app.design import numfmt

        indicators = get_atlas_catalog()["indicators"]
        complete = sum(1 for i in indicators if i["complete"])
        cache.clear()
        html = self.client.get("/").get_data(as_text=True)
        door = re.search(r'<a href="/atlante"><b>[^<]*</b><span>([^<]*)</span>', html).group(1)
        self.assertIn(f"{numfmt.text(len(indicators), 0)} indicatori", door)
        self.assertIn(f"{numfmt.text(complete, 0)} con i dati completi", door)

    def test_la_scheda_provinciale_non_porta_all_atlante(self):
        """L'atlante e' regionale: dalle province portava a una pagina senza province."""
        html = self.client.get("/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001?livello=provincia",
                               follow_redirects=True).get_data(as_text=True)
        self.assertEqual(self._rimandi(html), [])

    def test_l_indice_delle_regioni_non_porta_alla_vista_regione_della_spa(self):
        html = self.client.get("/regioni").get_data(as_text=True)
        self.assertNotIn("view=regioni", html)

    def test_la_home_non_promette_la_mappa_anno_per_anno(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("anno per anno", visible_text(html))
        for fascia in ("quiz", "storie"):
            if f'id="{fascia}"' not in html:
                continue
            with self.subTest(fascia=fascia):
                testa = re.search(rf'id="{fascia}".*?<p class="zone__lead">(.*?)</p>', html, re.DOTALL).group(1)
                self.assertIn('<a href="/atlante">atlante</a>', testa)
