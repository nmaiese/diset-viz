"""Le pagine aggiunte per le issue #25, #26, #27, #28, #31.

Un file per il gruppo, invece di quattro blocchi sparsi in test_app.py: qui si
guarda a cosa il lettore e il crawler ricevono davvero da /divari-regionali,
/confronto, /ricerca e dalla vista provinciale, non a come sono costruite.
"""

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
        # Il campo di ricerca dell'header, quello della barra mobile e la
        # SearchAction dello schema puntano tutti alla stessa pagina. Sul
        # chrome 2026 i primi due sono form GET veri, quindi la ricerca
        # funziona anche senza JavaScript.
        self.assertIn('class="hdr__search desktop-only" role="search" action="/ricerca"', home)
        self.assertIn('class="msearch mobile-only" role="search" action="/ricerca"', home)
        self.assertIn("/ricerca?q={search_term_string}", home)

        # Le pagine non ancora migrate usano ancora il masthead legacy, con lo
        # stesso punto di arrivo. Questa riga sparisce con l'ultima migrazione.
        blog = client.get("/blog").data.decode("utf-8")
        self.assertIn('class="masthead__search" href="/ricerca"', blog)
        self.assertIn('<form action="/ricerca" method="get" role="search">', blog)


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

            # I dati provinciali ci sono, e sono piu delle venti regioni.
            province_rows = html.count('class="ranking-row"')
            region_rows = regional.data.decode("utf-8").count('class="ranking-row"')
            self.assertEqual(region_rows, 20, base)
            self.assertGreater(province_rows, 90, base)

            # Il selettore del territorio in evidenza è un select: su mobile è il
            # menu a tendina con cui si sceglie una provincia.
            self.assertIn('aria-label="Provincia in evidenza"', html)
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

        for path in ("/", "/divari-regionali"):
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


if __name__ == "__main__":
    unittest.main()
