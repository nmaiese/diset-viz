import csv
import re
import unittest
from html import unescape
from pathlib import Path

from app import app


class AppSmokeTest(unittest.TestCase):
    def test_routes_respond(self):
        client = app.test_client()

        home = client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertEqual(home.headers["Referrer-Policy"], "strict-origin-when-cross-origin")
        self.assertEqual(home.headers["Strict-Transport-Security"], "max-age=31536000; includeSubDomains")
        csp = home.headers["Content-Security-Policy"]
        self.assertIn("script-src", csp)
        self.assertIn("script-src-elem", csp)
        self.assertIn("connect-src", csp)
        self.assertIn("https://www.googletagmanager.com", csp)
        self.assertIn("https://tagmanager.google.com", csp)
        self.assertIn("https://www.google-analytics.com", csp)
        # I font se li serve il sito: su una pagina del design system i due
        # domini di Google non devono piu' comparire. Restano su /legacy,
        # che monta Mukta da fonts.googleapis.com e non si tocca.
        self.assertNotIn("https://fonts.googleapis.com", csp)
        self.assertNotIn("https://fonts.gstatic.com", csp)
        self.assertIn("https://ssl.gstatic.com", csp)
        self.assertIn("https://www.gstatic.com", csp)
        self.assertIn("https://www.google.it", csp)
        self.assertIn("https://ep1.adtrafficquality.google", csp)
        self.assertIn("https://ep2.adtrafficquality.google", csp)
        self.assertIn("https://cdn.iubenda.com", csp)
        self.assertIn("https://www.iubenda.com", csp)
        self.assertIn("frame-src", csp)
        self.assertIn("https://tpc.googlesyndication.com", csp)
        # La home della 1.0: token, testata condivisa e il CSS della sua pagina.
        self.assertIn(b'<body class="ds sitechrome">', home.data)
        self.assertIn(b"css/ds/system.css", home.data)
        self.assertIn(b"css/ds/pages/home.css", home.data)
        self.assertIn(b'data-v1="home"', home.data)
        self.assertIn("L'Italia, regione per regione.".encode("utf-8"), home.data)
        self.assertIn(b"/atlante", home.data)
        # Il masthead legacy non deve sopravvivere accanto a quello nuovo.
        self.assertNotIn(b'<header class="masthead">', home.data)
        self.assertIn(b'class="hdr__bar"', home.data)
        # Ogni modulo si disegna su dati veri, non su segnaposto e lato server:
        # la striscia del divario ha i suoi punti, la classifica le sue righe,
        # i temi le loro aree, i territori un'anteprima vera. Senza JavaScript
        # la pagina resta leggibile. La qualita' della vita e' una porta verso
        # la sua pagina, non una classifica.
        self.assertIn(b'class="strip__dot', home.data)
        self.assertIn(b"data-rank-body", home.data)
        self.assertIn(b'class="home-area"', home.data)
        self.assertIn(b'class="terr__card"', home.data)
        self.assertIn(b'href="/qualita-della-vita"', home.data)
        self.assertNotIn(b'class="home-podium"', home.data)
        # L'indicatore in evidenza cambia a ogni visita: la mappa si controlla
        # fissandolo. Venti regioni colorate per classe della rampa.
        regionale = client.get("/?indicatore=ter-901")
        self.assertEqual(len(re.findall(
            rb'data-key="[a-z-]+" data-name="[^"]*" data-value="[^"]*" class="q[1-6]', regionale.data)), 20)

        atlante = client.get("/atlante")
        self.assertEqual(atlante.status_code, 200)
        self.assertIn(b'id="root"', atlante.data)
        self.assertIn(b"/metodologia", atlante.data)
        self.assertIn(b"Indicatori territoriali in evidenza", atlante.data)

        legacy = client.get("/legacy")
        self.assertEqual(legacy.status_code, 200)
        self.assertIn(b"draw_charts", legacy.data)

        legacy_reddito = client.get("/legacy-reddito")
        self.assertEqual(legacy_reddito.status_code, 200)
        self.assertIn(b"federalismo fiscale", legacy_reddito.data)

        # /data is the legacy dashboard's full dataset (~46 MB of JSON uncompressed).
        # It must stay a JSON array and stay noindex, but the route now serves it
        # gzipped with browser caching, so assert the compressed path and validate
        # only a small decompressed prefix instead of parsing the whole payload.
        data = client.get("/data", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(data.status_code, 200)
        self.assertIn("noindex", data.headers["X-Robots-Tag"])
        self.assertEqual(data.headers.get("Content-Encoding"), "gzip")
        self.assertIn("max-age", data.headers.get("Cache-Control", ""))
        self.assertLess(len(data.data), 10_000_000)  # gzipped, well under the raw ~46 MB
        import zlib
        head = zlib.decompressobj(zlib.MAX_WBITS | 16).decompress(data.data, 300).decode("utf-8", "ignore")
        self.assertTrue(head.lstrip().startswith("[{"))
        self.assertIn("Indicatore", head)

    def test_filtered_api_routes(self):
        client = app.test_client()

        catalog = client.get("/api/catalog")
        self.assertEqual(catalog.status_code, 200)
        self.assertIn("noindex", catalog.headers["X-Robots-Tag"])
        catalog_payload = catalog.get_json()
        self.assertIn("featured_indicator_id", catalog_payload)
        self.assertGreater(len(catalog_payload["indicators"]), 0)

        sample = catalog_payload["indicators"][0]
        for field in ("region_count", "completeness", "complete", "spark", "explain"):
            self.assertIn(field, sample)
        self.assertIsInstance(sample["complete"], bool)
        self.assertGreaterEqual(sample["completeness"], 0.0)
        self.assertLessEqual(sample["completeness"], 1.0)
        self.assertIsInstance(sample["spark"], list)
        self.assertLessEqual(len(sample["spark"]), 24)
        self.assertTrue(any(item["complete"] for item in catalog_payload["indicators"]))
        for item in catalog_payload["indicators"]:
            self.assertIn("explain", item)
            for field in ("plain", "example", "reading", "caveat", "direction"):
                self.assertIn(field, item["explain"])
                self.assertTrue(item["explain"][field])

        indicator_id = catalog_payload["featured_indicator_id"]
        indicator = client.get(f"/api/indicator/{indicator_id}")
        self.assertEqual(indicator.status_code, 200)
        indicator_payload = indicator.get_json()
        self.assertIn("metadata", indicator_payload)
        self.assertIn("series", indicator_payload)
        self.assertIn("explain", indicator_payload["metadata"])
        self.assertLess(len(str(indicator_payload)), 500000)

        year = indicator_payload["metadata"]["year_max"]
        values = client.get(f"/api/indicator/{indicator_id}/year/{year}")
        self.assertEqual(values.status_code, 200)
        values_payload = values.get_json()
        self.assertEqual(values_payload["year"], year)
        self.assertLessEqual(len(values_payload["values"]), 20)

        search = client.get("/api/search?q=turismo")
        self.assertEqual(search.status_code, 200)
        self.assertIn("results", search.get_json())

    def test_region_api(self):
        client = app.test_client()

        region = client.get("/api/region/lombardia")
        self.assertEqual(region.status_code, 200)
        self.assertIn("noindex", region.headers["X-Robots-Tag"])
        payload = region.get_json()
        self.assertEqual(payload["region"], "Lombardia")
        self.assertEqual(payload["region_key"], "lombardia")
        for field in ("theme_table", "themes_strong", "themes_weak",
                      "top_excels", "top_lags", "similar_regions", "all_indicators"):
            self.assertIn(field, payload)
        self.assertGreater(len(payload["theme_table"]), 0)

        self.assertEqual(client.get("/api/region/atlantide").status_code, 404)

    def test_blog_routes(self):
        from app.blog import get_posts

        client = app.test_client()

        listing = client.get("/blog")
        self.assertEqual(listing.status_code, 200)
        self.assertIn(b"Divario Italia", listing.data)

        posts = get_posts()
        self.assertGreater(len(posts), 0)
        slug = posts[0]["slug"]

        post = client.get(f"/blog/{slug}")
        self.assertEqual(post.status_code, 200)
        self.assertIn(b"application/ld+json", post.data)
        self.assertIn(b'property="og:type" content="article"', post.data)
        self.assertIn(b"/static/img/", post.data)

        missing = client.get("/blog/does-not-exist")
        self.assertEqual(missing.status_code, 404)
        self.assertIn(b"Pagina non trovata", missing.data)
        self.assertIn(b'content="noindex, follow"', missing.data)

    def test_every_published_post_has_a_valid_indicator_page_and_cover(self):
        # Il catalogo dell'atlante, non app.data: un post puo' dichiarare un
        # indicatore di qualunque famiglia (`indicator: bes-SDG-311`), come
        # documenta app/blog.py, e app.data conosce solo i territoriali.
        from app.atlas_catalog import get_atlas_indicator
        from app.blog import get_posts

        client = app.test_client()
        for post in get_posts():
            self.assertTrue(post.get("indicator"), post["slug"])
            payload = get_atlas_indicator(str(post["indicator"]))
            self.assertIsNotNone(payload, post["slug"])
            indicator_path = payload["metadata"]["path"]
            self.assertEqual(client.get(indicator_path).status_code, 200, post["slug"])
            cover = Path(app.root_path) / "static" / post["cover"].removeprefix("/static/")
            self.assertTrue(cover.is_file(), post["slug"])
            self.assertTrue(post.get("cover_alt"), post["slug"])

    def test_blog_post_updated_field_drives_date_modified(self):
        import tempfile
        from pathlib import Path
        from unittest import mock

        from app import blog, cache

        fixtures = {
            "with-update.md": (
                "---\ntitle: Con aggiornamento\ndate: 2026-06-01\nupdated: 2026-06-15\n---\nBody.\n"
            ),
            "no-update.md": "---\ntitle: Senza aggiornamento\ndate: 2026-06-01\n---\nBody.\n",
            "stale-update.md": (
                "---\ntitle: Aggiornamento antecedente\ndate: 2026-06-01\nupdated: 2026-05-01\n---\nBody.\n"
            ),
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            for name, content in fixtures.items():
                (tmp_dir / name).write_text(content, encoding="utf-8")

            with mock.patch.object(blog, "POSTS_DIR", tmp_dir):
                cache.cache.clear()
                posts = {p["title"]: p for p in blog.get_posts()}
                cache.cache.clear()

        self.assertEqual(posts["Con aggiornamento"]["date_modified"].isoformat(), "2026-06-15")
        self.assertEqual(posts["Senza aggiornamento"]["date_modified"], posts["Senza aggiornamento"]["date"])
        # An `updated` earlier than `date` is a frontmatter mistake, not a real
        # freshness signal - fall back to `date` rather than regress dateModified.
        self.assertEqual(posts["Aggiornamento antecedente"]["date_modified"], posts["Aggiornamento antecedente"]["date"])

    def test_seo_routes(self):
        client = app.test_client()

        sitemap = client.get("/sitemap.xml")
        self.assertEqual(sitemap.status_code, 200)
        self.assertIn("xml", sitemap.headers["Content-Type"])
        self.assertIn(b"/blog", sitemap.data)
        self.assertIn(b"/metodologia", sitemap.data)
        self.assertNotIn(b"/data", sitemap.data)

        robots = client.get("/robots.txt")
        self.assertEqual(robots.status_code, 200)
        robots_text = robots.data.decode("utf-8")
        self.assertIn("Sitemap:", robots_text)
        self.assertIn("Disallow: /api/", robots_text)
        self.assertIn("Disallow: /data", robots_text)
        # Single source of truth (Cloudflare managed injection disabled): the
        # content signals and AI-bot rules live in the app, and there must be
        # exactly one "User-agent: *" group (no duplicate from a managed prepend).
        # Real-time grounding (ai-input) is allowed for citation while training
        # (ai-train) stays reserved.
        self.assertIn("Content-Signal: search=yes,ai-input=yes,ai-train=no", robots_text)
        # Training crawlers stay blocked, answer/citation crawlers are allowed.
        self.assertIn("User-agent: ClaudeBot", robots_text)
        self.assertIn("User-agent: GPTBot", robots_text)
        self.assertIn("User-agent: OAI-SearchBot", robots_text)
        self.assertIn("User-agent: PerplexityBot", robots_text)
        self.assertIn("User-agent: Google-Extended", robots_text)
        self.assertEqual(robots_text.count("User-agent: *"), 1)
        # llms.txt is advertised and served as a curated index for models.
        self.assertIn("/llms.txt", robots_text)
        llms = client.get("/llms.txt")
        self.assertEqual(llms.status_code, 200)
        self.assertIn(b"# Divario Italia", llms.data)
        self.assertIn(b"Istat", llms.data)
        self.assertIn("/llms-full.txt", robots_text)
        llms_full = client.get("/llms-full.txt")
        self.assertEqual(llms_full.status_code, 200)
        self.assertIn(b"Classifica", llms_full.data)
        self.assertIn(b"Catalogo completo", llms_full.data)

        privacy = client.get("/privacy")
        self.assertEqual(privacy.status_code, 200)
        self.assertIn(b"Privacy e cookie", privacy.data)

        methodology = client.get("/metodologia")
        self.assertEqual(methodology.status_code, 200)
        self.assertIn(b"Metodologia e fonti", methodology.data)
        self.assertIn(b"application/ld+json", methodology.data)

    def test_llms_catalog_matches_indexable_indicator_sitemap(self):
        client = app.test_client()
        sitemap = client.get("/sitemap.xml").get_data(as_text=True)
        llms_full = client.get("/llms-full.txt").get_data(as_text=True)
        # Ogni pagina di livello, senza stato: la `/province` di una scheda a
        # due livelli e' una pagina in piu', e sta nei due indici solo se e'
        # indicizzabile (`indicator_universe.level_pages`).
        indicator_url = re.compile(r"https://divarioitalia\.it/indicatore/[^<)\s?]+")

        sitemap_indicators = set(indicator_url.findall(sitemap))
        llms_indicators = set(indicator_url.findall(llms_full))
        self.assertTrue(sitemap_indicators)
        self.assertEqual(sitemap_indicators, llms_indicators)
        views = {url for url in llms_indicators if url.endswith("/province")}
        self.assertEqual(len(views), 17)
        self.assertLessEqual(views, sitemap_indicators)
        self.assertNotIn("?livello=", llms_full)
        self.assertEqual(len(sitemap_indicators), sitemap.count("<loc>https://divarioitalia.it/indicatore/"))

        for field in ("famiglia ", "fonte ", "unita ", "copertura ", "definizione: "):
            self.assertIn(field, llms_full)
        for family in (
            "Istat, indicatori territoriali",
            "Istat, benessere e qualità della vita",
            "Istat, vita quotidiana delle famiglie",
            "Eurostat, statistiche regionali",
        ):
            self.assertIn(f"famiglia {family}", llms_full)
        self.assertIn("Download: CSV https://divarioitalia.it/download/indicator/", llms_full)
        self.assertIn("; JSON https://divarioitalia.it/download/indicator/", llms_full)

    def test_llms_download_examples_are_concrete(self):
        llms = app.test_client().get("/llms.txt").get_data(as_text=True)
        self.assertNotIn("<id>", llms)
        urls = re.findall(
            r"https://divarioitalia\.it/download/indicator/[^\s.]+\.(?:csv|json)",
            llms,
        )
        self.assertGreaterEqual(len(urls), 2)
        for url in urls:
            response = app.test_client().get(url.removeprefix("https://divarioitalia.it"))
            self.assertEqual(response.status_code, 200, url)

    def test_canonical_host_and_public_404(self):
        client = app.test_client()

        redirect = client.get("/", base_url="https://www.divarioitalia.it", follow_redirects=False)
        self.assertEqual(redirect.status_code, 301)
        self.assertEqual(redirect.headers["Location"], "https://divarioitalia.it/")
        self.assertEqual(redirect.headers["Strict-Transport-Security"], "max-age=31536000; includeSubDomains")

        missing = client.get("/pagina-che-non-esiste")
        self.assertEqual(missing.status_code, 404)
        self.assertIn(b"Pagina non trovata", missing.data)
        self.assertIn("noindex", missing.headers["X-Robots-Tag"])

        api_missing = client.get("/api/indicator/not-found")
        self.assertEqual(api_missing.status_code, 404)
        self.assertIn("noindex", api_missing.headers["X-Robots-Tag"])
        self.assertEqual(api_missing.get_json()["error"], "not_found")

    def test_public_pages_get_explicit_index_header(self):
        from app.data import get_catalog, get_indicator
        from app import profiles

        client = app.test_client()
        expected = "index, follow, max-snippet:-1, max-image-preview:large"
        for path in (
            "/", "/atlante", "/regioni", "/temi", "/qualita-della-vita",
            "/qualita-della-vita/classifica/regioni",
            "/metodologia", "/blog",
        ):
            self.assertEqual(client.get(path).headers.get("X-Robots-Tag"), expected, path)

        catalog = get_catalog()
        sample = next(item for item in catalog["indicators"] if profiles.is_search_indexable_indicator(item))
        indicator_path = profiles.indicator_path(sample["id"], sample["name"])
        self.assertTrue(profiles.is_search_indexable_indicator(get_indicator(str(sample["id"]))["metadata"]))
        self.assertEqual(client.get(indicator_path).headers.get("X-Robots-Tag"), expected)
        self.assertEqual(client.get("/regione/lombardia").headers.get("X-Robots-Tag"), expected)
        from app.atlas_catalog import get_atlas_catalog
        theme_path = get_atlas_catalog()["themes"][0]["path"]
        self.assertEqual(client.get(theme_path).headers.get("X-Robots-Tag"), expected)

    def test_noindex_paths_unaffected_by_default_index_header(self):
        client = app.test_client()
        for path in ("/data", "/legacy", "/legacy-reddito", "/download/quality-life/regioni"):
            self.assertIn("noindex", client.get(path).headers["X-Robots-Tag"])
        self.assertIn("noindex", client.get("/api/catalog").headers["X-Robots-Tag"])

    def test_404_header_is_not_overwritten_by_default_index_header(self):
        client = app.test_client()
        self.assertEqual(client.get("/pagina-che-non-esiste").headers["X-Robots-Tag"], "noindex, follow")
        self.assertEqual(
            client.get("/api/indicator/not-found").headers["X-Robots-Tag"],
            "noindex, nofollow, noarchive",
        )

    def test_seo_landing_pages(self):
        from app.data import get_catalog
        from app import profiles

        client = app.test_client()

        catalog = get_catalog()
        sample = next(item for item in catalog["indicators"] if profiles.is_search_indexable_indicator(item))
        path = profiles.indicator_path(sample["id"], sample["name"])

        indicator = client.get(path)
        self.assertEqual(indicator.status_code, 200)
        self.assertIn(b"application/ld+json", indicator.data)
        self.assertIn(b'"@type": "Dataset"', indicator.data)
        self.assertIn(b"DataDownload", indicator.data)
        self.assertIn(sample["name"].encode("utf-8"), indicator.data)

        csv_download = client.get(f"/download/indicator/{sample['id']}.csv")
        self.assertEqual(csv_download.status_code, 200)
        self.assertIn("text/csv", csv_download.headers["Content-Type"])
        self.assertIn("noindex", csv_download.headers["X-Robots-Tag"])
        self.assertIn(b"indicator_id,indicator,theme,region", csv_download.data)
        json_download = client.get(f"/download/indicator/{sample['id']}.json")
        self.assertEqual(json_download.status_code, 200)
        self.assertIn("noindex", json_download.headers["X-Robots-Tag"])
        self.assertIn("metadata", json_download.get_json())

        # Non-canonical slug 301s to the canonical path.
        wrong = client.get(f"/indicatore/{sample['id']}-slug-sbagliato")
        self.assertEqual(wrong.status_code, 301)
        self.assertTrue(wrong.headers["Location"].endswith(path))

        non_indexable = next(item for item in catalog["indicators"] if not profiles.is_search_indexable_indicator(item))
        non_indexable_path = profiles.indicator_path(non_indexable["id"], non_indexable["name"])
        non_indexable_page = client.get(non_indexable_path)
        self.assertEqual(non_indexable_page.status_code, 200)
        self.assertIn(b'content="noindex, follow"', non_indexable_page.data)
        self.assertEqual(non_indexable_page.headers["X-Robots-Tag"], "noindex, follow")
        sitemap = client.get("/sitemap.xml").data.decode("utf-8")
        self.assertIn(path, sitemap)
        self.assertNotIn(non_indexable_path, sitemap)

        self.assertEqual(client.get("/indicatore/9999999").status_code, 404)
        self.assertEqual(client.get("/indicatore/abc").status_code, 404)

        region = client.get("/regione/lombardia")
        self.assertEqual(region.status_code, 200)
        self.assertIn(b"Lombardia", region.data)
        self.assertIn(b"application/ld+json", region.data)
        self.assertEqual(client.get("/regione/atlantide").status_code, 404)

        from app.atlas_catalog import get_atlas_catalog
        theme = client.get(get_atlas_catalog()["themes"][0]["path"])
        self.assertEqual(theme.status_code, 200)
        self.assertIn(b"application/ld+json", theme.data)
        self.assertEqual(client.get("/tema/non-esiste").status_code, 404)

        self.assertEqual(client.get("/regioni").status_code, 200)
        self.assertEqual(client.get("/temi").status_code, 200)

        sitemap = client.get("/sitemap.xml").data
        self.assertIn(b"/regione/lombardia", sitemap)
        self.assertIn(b"/tema/", sitemap)
        self.assertIn(b"/indicatore/", sitemap)
        self.assertNotIn(non_indexable_path.encode("utf-8"), sitemap)

    def test_dataset_jsonld_spatial_coverage_and_license(self):
        import json
        import re

        from app.data import get_catalog
        from app import profiles

        client = app.test_client()
        sample = next(item for item in get_catalog()["indicators"] if profiles.is_search_indexable_indicator(item))
        pages = {
            "indicator": client.get(profiles.indicator_path(sample["id"], sample["name"])).data.decode("utf-8"),
            "region": client.get("/regione/lombardia").data.decode("utf-8"),
            "ranking": client.get("/qualita-della-vita/classifica/regioni").data.decode("utf-8"),
        }
        for name, html in pages.items():
            if name == "ranking":
                # The regional ranking can combine Istat and Eurostat, so its JSON-LD
                # license must reflect both rather than claim Istat-only. Istat is
                # CC BY 4.0 (istat.it/note-legali), like Eurostat.
                self.assertRegex(
                    html,
                    r'"license": "(https://creativecommons\.org/licenses/by/4\.0/'
                    r'|CC BY 4\.0 \(Istat\) e CC BY 4\.0 \(Eurostat\))"',
                    name,
                )
            else:
                self.assertIn('"license": "https://creativecommons.org/licenses/by/4.0/"', html, name)
            self.assertNotIn('"@type": "Country"', html, name)
            self.assertNotIn('"@type": "AdministrativeArea"', html, name)
            for block in re.findall(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', html, re.S):
                json.loads(block)

    def test_license_is_stated_the_same_way_on_every_surface(self):
        """Every page that names the licence in prose must name the one in
        `app/sources.py`, and none may still carry an older deed.

        The JSON-LD test above covers the machine-readable claim only. When Istat
        turned out to be CC BY 4.0 and not CC BY 3.0 IT, the fix landed on the
        structured data and left the methodology FAQ and both llms.txt files
        telling readers, and language models, the opposite."""
        from app import sources

        client = app.test_client()
        surfaces = {
            "/metodologia": client.get("/metodologia").data.decode("utf-8"),
            "/llms.txt": client.get("/llms.txt").data.decode("utf-8"),
            "/llms-full.txt": client.get("/llms-full.txt").data.decode("utf-8"),
        }
        for path, body in surfaces.items():
            self.assertIn(sources.LICENSE_LABEL, body, path)
            # No stale deed anywhere, in prose or in a URL.
            self.assertNotIn("BY 3.0", body, path)
            self.assertNotIn("licenses/by/3", body, path)

        # And the registry itself stays coherent: every family declares a deed,
        # spelled with the same version the URL points at.
        for family, meta in sources.SOURCES.items():
            self.assertTrue(meta.get("license"), family)
            self.assertEqual(meta.get("license_url"), sources.LICENSE_URL, family)
            self.assertIn("4.0", meta["license"], family)

    def test_indicator_page_has_data_derived_depth(self):
        from app.data import get_catalog
        from app import profiles

        client = app.test_client()
        sample = next(
            i for i in get_catalog()["indicators"]
            if i["explain"]["direction"] in ("higher_better", "lower_better", "higher_worse")
            and i["year_min"] != i["year_max"]
        )
        path = profiles.indicator_path(sample["id"], sample["name"])
        html = client.get(path).data.decode("utf-8")
        # Depth is carried by the article: four ordered sections, present on every
        # indicator whether an editor has written them or the page composed them
        # from the data. A missing role means the skeleton broke, which is the one
        # thing that would make 621 pages inconsistent again.
        self.assertIn('class="indicator-article', html)
        # I tre ruoli sostanziali sono sempre H2; la definizione può abitare il
        # blocco "Come leggere" invece di aprire l'articolo (sezioni variabili).
        for role in ("quadro", "dinamica", "limiti"):
            self.assertIn(f'id="sezione-{role}"', html)
        self.assertTrue('id="sezione-definizione"' in html or 'id="come-leggere"' in html)
        # L'apparato "Fonti e verifica" è un unico blocco di specifiche.
        self.assertIn("apparatus-specs", html)
        # Numbers live in the cockpit, once. The blocks that used to repeat them
        # further down the page must not come back.
        self.assertIn('class="indicator-cockpit"', html)
        self.assertNotIn("I numeri, in breve", html)
        self.assertNotIn("numbers-tile", html)
        # The cascade fix: analysis h2s inside .page-indicator's .prose section must
        # get the full article-style treatment, not the compact .page-ranking one.
        css_path = Path(app.root_path) / "static" / "css" / "site.css"
        self.assertIn(".page .prose h2", css_path.read_text(encoding="utf-8"))

    def test_indicator_page_explains_latest_change_and_gender_gap_scope(self):
        client = app.test_client()
        # Legacy single-segment territorial URL 301s to the unified acronym form.
        response = client.get(
            "/indicatore/61-differenza-tra-tasso-di-attivita-maschile-e-femminile",
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        # The latest change is told in the "dinamica" section as movement across
        # territories. The mean's own before/after is not repeated there: the
        # cockpit KPI already carries it, and printing it twice is the duplication
        # this layout removes.
        self.assertIn("tra il 2024 e il 2025", html)
        self.assertIn("il valore è diminuito in 14 regioni, è aumentato in 6", html)
        self.assertIn("il divario medio tra i due tassi si è ridotto", html)
        # A gap between two rates covers both populations, and the page must not
        # narrow that perimeter to one sex.
        self.assertIn("sia la popolazione femminile sia quella maschile", html)
        self.assertNotIn("Il perimetro riguarda la popolazione maschile", html)
        # A simple mean of regional values is never a national indicator.
        self.assertNotIn("Media Italia", html)
        self.assertNotIn("media nazionale", html)

    def test_every_legacy_indicator_has_explanatory_and_annual_context(self):
        from app.data import get_catalog, get_indicator, indicator_year_over_year_stats

        generic_percentage = (
            "Un valore di 20 indica che la misura equivale al 20% del totale "
            "definito dalla fonte."
        )
        for item in get_catalog()["indicators"]:
            explain = item["explain"]
            for field in ("plain", "example", "scope", "reading", "caveat"):
                self.assertTrue(explain[field].strip(), f"{item['id']} missing {field}")
            self.assertNotEqual(explain["example"], generic_percentage, item["id"])

            payload = get_indicator(item["id"])
            annual = indicator_year_over_year_stats(payload)
            if item["year_min"] == item["year_max"]:
                self.assertIsNone(annual, item["id"])
                continue
            self.assertIsNotNone(annual, item["id"])
            self.assertGreater(annual["common_count"], 0, item["id"])
            self.assertLess(annual["previous_year"], annual["year"], item["id"])

    def test_indicator_trend_stats(self):
        from app.data import (
            indicator_trend_stats,
            indicator_year_average,
            indicator_year_over_year_stats,
        )

        payload = {
            "metadata": {"id": "1", "name": "Tasso di occupazione", "unit": "percentuale", "year_min": 2020, "year_max": 2022},
            "series": [
                {"year": 2020, "region": "Lombardia", "region_key": "lombardia", "value": 60.0},
                {"year": 2020, "region": "Calabria", "region_key": "calabria", "value": 40.0},
                {"year": 2022, "region": "Lombardia", "region_key": "lombardia", "value": 66.0},
                {"year": 2022, "region": "Calabria", "region_key": "calabria", "value": 44.0},
            ],
        }
        values = [row for row in payload["series"] if row["year"] == 2022]
        best, worst = values[0], values[1]
        stats = indicator_trend_stats(payload, 2022, values, best, worst)

        self.assertEqual(stats["year_avg"], 55.0)
        self.assertEqual(stats["year_min_avg"], 50.0)
        self.assertAlmostEqual(stats["avg_change_pct"], 10.0)
        self.assertEqual(stats["gap_abs"], 22.0)
        self.assertAlmostEqual(stats["gap_ratio"], 66.0 / 44.0)

        # A "differenza tra..." indicator never gets a "N times" ratio: it's already
        # a gap, not a magnitude that can be honestly expressed as a multiple.
        gap_payload = dict(payload)
        gap_payload["metadata"] = dict(payload["metadata"], name="Differenza tra tasso di occupazione maschile e femminile")
        gap_stats = indicator_trend_stats(gap_payload, 2022, values, best, worst)
        self.assertIsNone(gap_stats["gap_ratio"])

        # Single-year series: no trend claim, avg falls back to the only year available.
        single_year_payload = {
            "metadata": {"id": "2", "name": "Indicatore", "unit": "percentuale", "year_min": 2022, "year_max": 2022},
            "series": values,
        }
        single_stats = indicator_trend_stats(single_year_payload, 2022, values, best, worst)
        self.assertFalse(single_stats["has_multi_year"])
        self.assertIsNone(single_stats["avg_change_pct"])
        self.assertEqual(single_stats["year_avg"], 55.0)

        self.assertIsNone(indicator_year_average(payload["series"], 2021))

        annual = indicator_year_over_year_stats(payload)
        self.assertEqual(annual["previous_year"], 2020)
        self.assertEqual(annual["year"], 2022)
        self.assertEqual(annual["year_gap"], 2)
        self.assertEqual(annual["common_count"], 2)
        self.assertEqual(annual["previous_avg"], 50.0)
        self.assertEqual(annual["current_avg"], 55.0)
        self.assertEqual(annual["increase_count"], 2)
        self.assertEqual(annual["decrease_count"], 0)
        self.assertIsNone(indicator_year_over_year_stats(single_year_payload))

        # lower_better/higher_worse indicators pick "best" as the *smaller* value
        # (views.py reverses the ranking for these directions) - the gap must still
        # come out as a positive magnitude, never a signed (best - worst) number.
        reversed_stats = indicator_trend_stats(payload, 2022, values, best=worst, worst=best)
        self.assertEqual(reversed_stats["gap_abs"], 22.0)
        self.assertAlmostEqual(reversed_stats["gap_ratio"], 66.0 / 44.0)

        # Coverage changes: both means use only territories present in both
        # years, so the comparison does not mix different territorial bases.
        partial_payload = {
            "metadata": {"year_min": 2020, "year_max": 2021},
            "series": [
                {"year": 2020, "region": "A", "region_key": "a", "value": 10.0},
                {"year": 2020, "region": "B", "region_key": "b", "value": 20.0},
                {"year": 2021, "region": "A", "region_key": "a", "value": 12.0},
            ],
        }
        partial = indicator_year_over_year_stats(partial_payload)
        self.assertEqual(partial["common_count"], 1)
        self.assertFalse(partial["same_coverage"])
        self.assertEqual(partial["previous_avg"], 10.0)
        self.assertEqual(partial["current_avg"], 12.0)

        # Median/dispersion and the "biggest movers" with an honest kind label.
        # Mixed-direction fixture: Lombardia rises, Calabria falls, Lazio rises less.
        # Five regions report, above the small-N gate, so median and the mean split
        # are computed (below the gate they are suppressed - see the N=2 case below).
        mixed_payload = {
            "metadata": {"id": "3", "name": "Indicatore misto", "unit": "percentuale", "year_min": 2020, "year_max": 2022},
            "series": [
                {"year": 2020, "region": "Lombardia", "region_key": "lombardia", "value": 60.0},
                {"year": 2020, "region": "Calabria", "region_key": "calabria", "value": 40.0},
                {"year": 2020, "region": "Lazio", "region_key": "lazio", "value": 50.0},
                {"year": 2020, "region": "Veneto", "region_key": "veneto", "value": 55.0},
                {"year": 2020, "region": "Sicilia", "region_key": "sicilia", "value": 45.0},
                {"year": 2022, "region": "Lombardia", "region_key": "lombardia", "value": 70.0},
                {"year": 2022, "region": "Calabria", "region_key": "calabria", "value": 30.0},
                {"year": 2022, "region": "Lazio", "region_key": "lazio", "value": 52.0},
                {"year": 2022, "region": "Veneto", "region_key": "veneto", "value": 58.0},
                {"year": 2022, "region": "Sicilia", "region_key": "sicilia", "value": 44.0},
            ],
        }
        mixed_values = [row for row in mixed_payload["series"] if row["year"] == 2022]
        mixed_best = next(row for row in mixed_values if row["region"] == "Lombardia")
        mixed_worst = next(row for row in mixed_values if row["region"] == "Calabria")
        mixed_stats = indicator_trend_stats(mixed_payload, 2022, mixed_values, mixed_best, mixed_worst)

        # 2022 values 70,30,52,58,44 -> sorted 30,44,52,58,70 -> median 52.
        self.assertEqual(mixed_stats["median"], 52.0)
        # Mean is 50.8: Lombardia (70), Lazio (52) and Veneto (58) beat it; Calabria
        # (30) and Sicilia (44) do not.
        self.assertEqual(mixed_stats["above_avg_count"], 3)
        self.assertEqual(mixed_stats["below_avg_count"], 2)
        self.assertEqual(mixed_stats["region_highest_delta"]["region"], "Lombardia")
        self.assertEqual(mixed_stats["region_highest_delta"]["kind"], "aumento")
        self.assertEqual(mixed_stats["region_lowest_delta"]["region"], "Calabria")
        self.assertEqual(mixed_stats["region_lowest_delta"]["kind"], "calo")
        # Best (Lombardia) - worst (Calabria) gap widened from 20 (2020) to 40 (2022).
        self.assertEqual(mixed_stats["year_min_gap_abs"], 20.0)
        self.assertEqual(mixed_stats["gap_trend"], 20.0)

        # Small-N gate: with only two regions reporting, a median / mean split is
        # statistical theatre. Those fields are suppressed (None), but the honest
        # mean and min-max gap are still computed for the page.
        small_n_payload = {
            "metadata": {"id": "3b", "name": "Indicatore misto", "unit": "percentuale", "year_min": 2022, "year_max": 2022},
            "series": [
                {"year": 2022, "region": "Lombardia", "region_key": "lombardia", "value": 70.0},
                {"year": 2022, "region": "Calabria", "region_key": "calabria", "value": 30.0},
            ],
        }
        small_n_values = [row for row in small_n_payload["series"] if row["year"] == 2022]
        small_n_best = next(row for row in small_n_values if row["region"] == "Lombardia")
        small_n_worst = next(row for row in small_n_values if row["region"] == "Calabria")
        small_n_stats = indicator_trend_stats(small_n_payload, 2022, small_n_values, small_n_best, small_n_worst)
        self.assertIsNone(small_n_stats["median"])
        self.assertIsNone(small_n_stats["above_avg_count"])
        self.assertIsNone(small_n_stats["below_avg_count"])
        self.assertEqual(small_n_stats["year_avg"], 50.0)
        self.assertEqual(small_n_stats["gap_abs"], 40.0)

        # Same-direction fixture: every region rises, just by different amounts - the
        # "lowest delta" region must never be mislabeled as a decrease.
        rising_payload = {
            "metadata": {"id": "4", "name": "Indicatore in crescita ovunque", "unit": "euro", "year_min": 2020, "year_max": 2022},
            "series": [
                {"year": 2020, "region": "Lombardia", "region_key": "lombardia", "value": 100.0},
                {"year": 2020, "region": "Calabria", "region_key": "calabria", "value": 50.0},
                {"year": 2022, "region": "Lombardia", "region_key": "lombardia", "value": 130.0},
                {"year": 2022, "region": "Calabria", "region_key": "calabria", "value": 60.0},
            ],
        }
        rising_values = [row for row in rising_payload["series"] if row["year"] == 2022]
        rising_stats = indicator_trend_stats(rising_payload, 2022, rising_values)
        self.assertEqual(rising_stats["region_highest_delta"]["kind"], "aumento")
        self.assertEqual(rising_stats["region_lowest_delta"]["region"], "Calabria")
        self.assertEqual(rising_stats["region_lowest_delta"]["kind"], "aumento")
        self.assertGreater(rising_stats["region_lowest_delta"]["delta"], 0)

        # Fewer than two regions in common across the two years: no honest "biggest
        # movers" comparison is possible, both must be None rather than duplicated.
        single_common_payload = {
            "metadata": {"id": "5", "name": "Indicatore", "unit": "euro", "year_min": 2020, "year_max": 2022},
            "series": [
                {"year": 2020, "region": "Lombardia", "region_key": "lombardia", "value": 100.0},
                {"year": 2022, "region": "Lombardia", "region_key": "lombardia", "value": 110.0},
            ],
        }
        single_common_values = [row for row in single_common_payload["series"] if row["year"] == 2022]
        single_common_stats = indicator_trend_stats(single_common_payload, 2022, single_common_values)
        self.assertIsNone(single_common_stats["region_highest_delta"])
        self.assertIsNone(single_common_stats["region_lowest_delta"])

    def test_trend_framing(self):
        from app.indicator_notes import trend_framing

        self.assertEqual(trend_framing("higher_better", None), "")
        self.assertEqual(trend_framing("higher_better", 0.5), "un andamento sostanzialmente stabile")
        self.assertEqual(trend_framing("higher_better", 5.0), "una variazione media favorevole")
        self.assertEqual(trend_framing("higher_better", -5.0), "una variazione media sfavorevole")
        self.assertEqual(trend_framing("lower_better", -5.0), "una variazione media favorevole")
        self.assertEqual(trend_framing("lower_better", 5.0), "una variazione media sfavorevole")
        self.assertEqual(trend_framing("higher_worse", 5.0), "una variazione media sfavorevole")
        self.assertEqual(trend_framing("contextual", 5.0), "un aumento")
        self.assertEqual(trend_framing("contextual", -5.0), "una diminuzione")

    def test_region_profile_is_coherent(self):
        from app import profiles

        # Northern industrial regions should cluster together, southern ones too.
        lombardia = profiles.region_profile("lombardia")
        self.assertIsNotNone(lombardia)
        self.assertGreater(lombardia["scored_count"], 0)
        similar = {s["region_key"] for s in lombardia["similar_regions"]}
        self.assertTrue(similar & {"piemonte", "veneto", "emilia-romagna"})
        # Theme scores stay within the normalised 0..1 range.
        for theme in lombardia["theme_table"]:
            self.assertGreaterEqual(theme["score"], 0.0)
            self.assertLessEqual(theme["score"], 1.0)

    def test_macro_areas_cover_every_theme(self):
        from app.data import get_catalog

        catalog = get_catalog()
        # Every theme is mapped to a real macro-area (never the "Altro" fallback).
        for theme in catalog["themes"]:
            self.assertTrue(theme["macro_area"])
            self.assertNotEqual(theme["macro_area"], "Altro")
        for item in catalog["indicators"]:
            self.assertTrue(item["macro_area"])
        # The rollup exists and its counts add up to the catalog total.
        self.assertIn("macro_areas", catalog)
        self.assertTrue(catalog["macro_areas"])
        total = sum(area["indicator_count"] for area in catalog["macro_areas"])
        self.assertEqual(total, len(catalog["indicators"]))

    def test_region_explorer_and_movement(self):
        from app import profiles

        profile = profiles.region_profile("campania")
        indicators = profile["all_indicators"]
        self.assertTrue(indicators)
        contextual_seen = False
        for item in indicators:
            if item["rank"] is not None:
                self.assertGreaterEqual(item["rank"], 1)
                self.assertLessEqual(item["rank"], item["region_count"])
                self.assertIsNotNone(item["score"])
            else:
                # Contextual indicators stay visible but carry no score or movement.
                contextual_seen = True
                self.assertIsNone(item["score"])
                self.assertIsNone(item["movement"])
            if item["movement"] is not None:
                self.assertGreaterEqual(item["movement"], -19)
                self.assertLessEqual(item["movement"], 19)
        self.assertTrue(contextual_seen)

        gains, losses = profile["movement_gains"], profile["movement_losses"]
        self.assertTrue(all(g["movement"] > 0 for g in gains))
        self.assertTrue(all(l["movement"] < 0 for l in losses))
        self.assertEqual(gains, sorted(gains, key=lambda g: g["movement"], reverse=True))
        self.assertEqual(losses, sorted(losses, key=lambda l: l["movement"]))

    def test_core_set_is_complete_and_recent(self):
        from app.data import get_catalog
        from app import profiles

        core = [i for i in get_catalog()["indicators"] if profiles.is_core(i)]
        self.assertTrue(core)
        for item in core:
            self.assertTrue(item["complete"])
            self.assertGreaterEqual(item["year_max"], profiles.CORE_MIN_YEAR)

    def test_curated_direction_overrides_heuristic(self):
        from app.indicator_notes import direction_for

        # A gender employment gap: smaller is better, not "higher better".
        self.assertEqual(direction_for("57", "Differenza tra tasso di occupazione maschile e femminile"), "lower_better")
        # Energy covered by cogeneration is positive, not a pressure.
        self.assertEqual(direction_for("378", "Consumi di energia coperti da cogenerazione"), "higher_better")
        # Early school leaving is negative.
        self.assertEqual(direction_for("102", "Giovani che abbandonano"), "lower_better")
        # INVALSI: share of students NOT reaching a sufficient level is negative.
        self.assertEqual(direction_for("623", "Competenza alfabetica non adeguata"), "lower_better")
        # Share of students with high competence is positive.
        self.assertEqual(direction_for("111", "Studenti con elevate competenze in lettura"), "higher_better")
        # Burned forest area is an environmental pressure.
        self.assertEqual(direction_for("514", "Superficie boscata percorsa dal fuoco"), "lower_better")
        # An absolute count of people at risk also reflects regional population.
        self.assertEqual(direction_for("285", "Persone a rischio di povertà"), "contextual")
        # Research collaboration is a positive capacity indicator.
        self.assertEqual(direction_for("417", "Imprese che collaborano in attività di R&S"), "higher_better")

    def test_regions_map_data_matches_geometry(self):
        from app import profiles

        overview = profiles.regions_overview()
        keys = {r["region_key"] for r in profiles.all_regions_index()}
        self.assertEqual(set(overview), keys)
        for entry in overview.values():
            self.assertNotIn("score", entry)
            self.assertNotIn("rank", entry)
            self.assertNotIn("rank_total", entry)
        # The pre-projected SVG partial must cover exactly the same region keys.
        from pathlib import Path
        svg = (Path(app.root_path) / "templates" / "_italy_map.html").read_text(encoding="utf-8")
        import re
        svg_keys = set(re.findall(r'data-key="([^"]+)"', svg))
        self.assertEqual(svg_keys, keys)

    def test_ads_txt_is_available_without_adsense_env(self):
        client = app.test_client()
        from app import config

        original_client = config.ADSENSE_CLIENT
        try:
            config.ADSENSE_CLIENT = ""
            ads = client.get("/ads.txt")
            self.assertEqual(ads.status_code, 200)
            self.assertEqual(ads.mimetype, "text/plain")
            self.assertEqual(
                ads.data,
                b"google.com, pub-6806451730012282, DIRECT, f08c47fec0942fa0\n",
            )
            ads.close()
        finally:
            config.ADSENSE_CLIENT = original_client

    def test_gtm_consent_default_precedes_gtm_and_adsense(self):
        from app import config

        client = app.test_client()
        original_client = config.ADSENSE_CLIENT
        original_gtm = config.GOOGLE_TAG_MANAGER_ID
        try:
            config.GOOGLE_TAG_MANAGER_ID = "GTM-PZ45BG7D"
            config.ADSENSE_CLIENT = "ca-pub-1234567890123456"
            atlante = client.get("/atlante")
            self.assertEqual(atlante.status_code, 200)
            html = atlante.data.decode("utf-8")
            consent_index = html.index("gtag('consent', 'default'")
            gtm_index = html.index("googletagmanager.com/gtm.js?id=")
            loader_index = html.index("pagead2.googlesyndication.com/pagead/js/adsbygoogle.js")
            self.assertLess(consent_index, gtm_index)
            self.assertLess(consent_index, loader_index)
            self.assertIn("'analytics_storage': 'denied'", html)
            self.assertIn("'wait_for_update': 2000", html)
            self.assertIn("gtag('set', 'ads_data_redaction', true)", html)
            self.assertIn("GTM-PZ45BG7D", html)
            self.assertIn("googletagmanager.com/ns.html?id=GTM-PZ45BG7D", html)
            # /atlante still mounts the React SPA, which fires its own page_view
            # once mounted, so the server-rendered page_view push stays off there
            # (TRACK_SERVER_PAGE_VIEW = false in app.html) to avoid double-counting.
            self.assertNotIn("event: 'page_view'", html)
            self.assertNotIn("googletagmanager.com/gtag/js", html)
            self.assertNotIn("diSendGoogleEvent", html)
            self.assertNotIn("googlefc.controlledMessagingFunction", html)
            self.assertNotIn("diApplyGoogleConsent", html)

            # The homepage and /blog are both plain server-rendered pages (no
            # SPA to track its own page view), so both get the default push.
            home = client.get("/")
            self.assertEqual(home.status_code, 200)
            home_html = home.data.decode("utf-8")
            self.assertIn("event: 'page_view'", home_html)
            self.assertIn("page_type: window.location.pathname.indexOf('/blog') === 0 ? 'blog' : 'server'", home_html)

            blog = client.get("/blog")
            self.assertEqual(blog.status_code, 200)
            blog_html = blog.data.decode("utf-8")
            self.assertIn("event: 'page_view'", blog_html)
            self.assertIn("page_type: window.location.pathname.indexOf('/blog') === 0 ? 'blog' : 'server'", blog_html)
        finally:
            config.ADSENSE_CLIENT = original_client
            config.GOOGLE_TAG_MANAGER_ID = original_gtm

    def test_privacy_page_exposes_iubenda_preferences_button(self):
        from app import config

        client = app.test_client()
        original_gtm = config.GOOGLE_TAG_MANAGER_ID
        try:
            config.GOOGLE_TAG_MANAGER_ID = "GTM-PZ45BG7D"
            privacy = client.get("/privacy")
            self.assertEqual(privacy.status_code, 200)
            html = privacy.data.decode("utf-8")
            self.assertIn("diOpenConsentPreferences", html)
            self.assertIn("Gestisci preferenze cookie", html)
            self.assertNotIn("data-funding-choices-revoke", html)
            self.assertNotIn("showRevocationMessage", html)
        finally:
            config.GOOGLE_TAG_MANAGER_ID = original_gtm

    def test_internal_event_endpoint_accepts_anonymous_events(self):
        client = app.test_client()

        event = client.post("/api/events", json={
            "name": "select_indicator",
            "path": "/?indicator=105",
            "title": "Divario Italia",
            "params": {
                "indicator_id": "105",
                "enabled": True,
                "nested": {"ignored": True},
            },
        })
        self.assertEqual(event.status_code, 204)

        self.assertEqual(client.post("/api/events", json={"name": "bad-name!"}).status_code, 400)

    def test_parse_number_rejects_non_finite(self):
        from app.data import _parse_number

        self.assertEqual(_parse_number("1.234,5"), 1234.5)
        self.assertIsNone(_parse_number("INF"))
        self.assertIsNone(_parse_number("-INF"))
        self.assertIsNone(_parse_number(""))
        self.assertIsNone(_parse_number("-"))

    def test_catalog_is_strict_json(self):
        import json

        from app.data import get_catalog

        # allow_nan=False raises if any NaN/Infinity slipped into the payload,
        # which would make the browser's JSON.parse fail.
        json.dumps(get_catalog(), allow_nan=False)

    def test_authored_title_de_boilerplates_within_budget(self):
        """Un titolo autorato in lingua comune sostituisce il boilerplate
        "per regione", tiene la marca se ci sta, e rispetta lo stesso budget."""
        from app.indicator_notes import authored_seo_title, _TITLE_MAX
        short = authored_seo_title("Dove si lavora di più nella ricerca", "Divario Italia")
        self.assertEqual(short, "Dove si lavora di più nella ricerca · Divario Italia")
        self.assertLessEqual(len(short), _TITLE_MAX)
        self.assertNotIn("per regione", short)
        # Un titolo autorato lungo non sfora: si taglia a frase intera, senza marca.
        longtitle = ("Dove nascono più imprese e dove invece il tessuto produttivo "
                     "resta fermo da anni interi in questa lunga analisi.")
        clamped = authored_seo_title(longtitle, "Divario Italia")
        self.assertLessEqual(len(clamped), _TITLE_MAX)
        self.assertEqual("", authored_seo_title("", "Divario Italia"))

    def test_an_authored_h1_and_title_replace_the_derived_ones(self):
        import unittest.mock
        from app import indicator_texts
        authored = {
            "level": "regione", "lead": "Un lead.", "vintage": 2023,
            "h1": "Dove si vive a lungo dopo i 65 anni",
            "seo_title": "Dove si vive a lungo dopo i 65 anni",
            "sections": [{"role": r, "h": None, "body": f"Corpo {r}."}
                         for r in ("definizione", "quadro", "dinamica", "limiti")],
        }
        from app import app as flask_app
        with unittest.mock.patch.object(indicator_texts, "get_text", lambda _id: authored):
            html = flask_app.test_client().get(
                "/indicatore/eta-media-della-popolazione/ter-920",
                follow_redirects=True).get_data(as_text=True)
        self.assertIn("Dove si vive a lungo dopo i 65 anni", html)
        self.assertIn("<title>Dove si vive a lungo dopo i 65 anni · Divario Italia</title>", html)
        self.assertNotIn("Eta media della popolazione per regione", html)

    def test_the_markdown_projection_carries_the_authored_h1(self):
        """La proiezione markdown è una rappresentazione di prima classe della
        stessa pagina: dare all'agente il nome amministrativo mentre il lettore
        HTML legge il titolo in lingua comune sono due pagine allo stesso URL."""
        import unittest.mock
        from app import indicator_texts
        from app import app as flask_app
        authored = {
            "level": "regione", "lead": "Un lead.", "vintage": 2023,
            "h1": "Dove si vive a lungo dopo i 65 anni",
            "sections": [{"role": r, "h": None, "body": f"Corpo {r}."}
                         for r in ("definizione", "quadro", "dinamica", "limiti")],
        }
        with unittest.mock.patch.object(indicator_texts, "get_text", lambda _id: authored):
            body = flask_app.test_client().get(
                "/indicatore/eta-media-della-popolazione/ter-920",
                headers={"Accept": "text/markdown"},
                follow_redirects=True).get_data(as_text=True)
        self.assertIn("# Dove si vive a lungo dopo i 65 anni", body)

    def test_the_markdown_keeps_the_official_series_name(self):
        """Con un H1 autorato il nome amministrativo sparisce dal titolo, e nella
        proiezione markdown non ricompare da nessun'altra parte (la pagina HTML
        ce l'ha nel blocco "Dato originale"): un agente leggerebbe cifre e fonte
        senza sapere quale serie sta leggendo."""
        import unittest.mock
        from app import indicator_texts
        from app import app as flask_app
        authored = {
            "level": "regione", "lead": "Un lead.", "vintage": 2023,
            "h1": "Dove si vive a lungo dopo i 65 anni",
            "sections": [{"role": r, "h": None, "body": f"Corpo {r}."}
                         for r in ("definizione", "quadro", "dinamica", "limiti")],
        }
        with unittest.mock.patch.object(indicator_texts, "get_text", lambda _id: authored):
            body = flask_app.test_client().get(
                "/indicatore/eta-media-della-popolazione/ter-920",
                headers={"Accept": "text/markdown"},
                follow_redirects=True).get_data(as_text=True)
        self.assertIn("# Dove si vive a lungo dopo i 65 anni", body)
        self.assertIn("- Serie: Eta media della popolazione", body)

    def test_an_authored_title_still_disambiguates_a_duplicate_bes_series(self):
        """Le serie BES duplicate misurano lo stesso fenomeno della gemella
        territoriale e restano indicizzabili: titolarle in lingua comune è
        proprio il caso in cui le due finiscono con lo stesso `<title>`."""
        from app.indicator_notes import authored_seo_title, _TITLE_MAX
        titled = authored_seo_title("Dove si vive a lungo dopo i 65 anni",
                                    "Divario Italia", source_qualifier="Bes")
        self.assertIn("(Bes)", titled)
        self.assertLessEqual(len(titled), _TITLE_MAX)
        plain = authored_seo_title("Dove si vive a lungo dopo i 65 anni", "Divario Italia")
        self.assertNotEqual(plain, titled)

    def test_a_banned_character_in_a_title_is_caught(self):
        """I titoli sono l'unico testo della pagina che le guardie deterministiche
        non guardavano: un em-dash in un `h1` sarebbe stato pubblicato con la
        suite verde."""
        from scripts import prose_lint
        entry = {
            "h1": "Dove si vive a lungo — dopo i 65 anni",
            "seo_title": "Dove si vive a lungo, per regione",
            "lead": "Un lead.", "sections": [{"role": "quadro", "body": "Corpo."}],
        }
        fields = dict(prose_lint.prose_fields(entry))
        self.assertIn("h1", fields)
        self.assertIn("seo_title", fields)
        # Il carattere vietato è ora dentro il perimetro della guardia.
        self.assertTrue([f for f, text in fields.items() if "—" in text])

    def test_seo_metadata_within_budget(self):
        from app.data import get_catalog
        from app.indicator_notes import seo_title, seo_description
        from app import profiles

        indicators = get_catalog()["indicators"]
        for item in indicators:
            title = seo_title(item["name"], "Divario Italia")
            desc = seo_description(
                item["explain"]["plain"],
                item["year_max"],
                len(item["regions"]),
                name=item["name"],
            )
            # SERP budgets: titles stay readable, descriptions are not truncated by Google.
            self.assertLessEqual(len(title), 60, f"title too long for {item['id']}: {title}")
            self.assertGreaterEqual(len(title), 8, f"title too short for {item['id']}: {title}")
            self.assertLessEqual(len(desc), 155, f"desc too long for {item['id']}: {desc}")
            self.assertEqual(title, title.strip())
            self.assertNotIn(" per per ", title)  # no doubled connector before the tail
            self.assertNotIn(", per regione", title)  # no dangling comma before the tail
            # Title must not end on a dangling connector word.
            last = title.replace(" · Divario Italia", "").split()[-1].lower()
            self.assertNotIn(last, {"di", "del", "della", "dei", "delle", "per", "e", "a", "da", "in"}, title)
            # Description keeps whole sentences and ends with the data vintage.
            self.assertIn("Dati Istat", desc)
            self.assertTrue(desc.rstrip().endswith("."), desc)

        by_id = {i["id"]: i for i in indicators}
        indexable_titles = [
            seo_title(item["name"], "Divario Italia")
            for item in indicators
            if profiles.is_search_indexable_indicator(item)
        ]
        indexable_descriptions = [
            seo_description(
                item["explain"]["plain"],
                item["year_max"],
                len(item["regions"]),
                name=item["name"],
            )
            for item in indicators
            if profiles.is_search_indexable_indicator(item)
        ]
        self.assertEqual(len(indexable_titles), len(set(indexable_titles)))
        self.assertEqual(len(indexable_descriptions), len(set(indexable_descriptions)))
        # Gender siblings (189 maschi / 190 femmine) must not collapse to one title.
        if {"189", "190"} <= set(by_id):
            self.assertNotEqual(
                seo_title(by_id["189"]["name"], "Divario Italia"),
                seo_title(by_id["190"]["name"], "Divario Italia"),
            )

    def test_a_long_authored_title_keeps_what_distinguishes_it(self):
        """Due titoli lunghi che aprono sulla stessa frase non possono diventare
        lo stesso `<title>`: ciò che li distingue sta in fondo, quindi in fondo
        si tiene."""
        from app.indicator_notes import authored_seo_title, _TITLE_MAX
        common = "Il divario fra Nord e Sud in questa lunghissima analisi "
        first = authored_seo_title(common + "sulla natalita regionale")
        second = authored_seo_title(common + "sulla mortalita regionale")
        self.assertNotEqual(first, second)
        for title in (first, second):
            self.assertLessEqual(len(title), _TITLE_MAX)
            self.assertEqual(title.count("("), title.count(")"))
        # E una parola sola più lunga del budget non lo sfora comunque.
        self.assertLessEqual(len(authored_seo_title("A" * 200)), _TITLE_MAX)

    def test_shortening_never_leaves_a_dangling_parenthesis(self):
        """Il taglio a caratteri può cadere dentro una parentesi dell'autore e
        portarsi via solo metà della coppia: incastonato in `testa (coda)`
        diventa il titolo malformato che la guardia promette di non far uscire.
        Testa e coda si bilanciano entrambe, e la coda resta quella che
        distingue."""
        from app.indicator_notes import authored_seo_title, _TITLE_MAX
        cases = [
            "Titolo comune abbastanza lungo per doverlo tagliare (qualificatore editoriale molto lungo)",
            "Titolo (uno) e poi (due) e ancora (tre) con una coda lunghissima che sfora il budget",
            "Apertura (parentesi mai chiusa nella prima meta del titolo lunghissimo che sfora",
        ]
        for text in cases:
            with self.subTest(text=text[:30]):
                title = authored_seo_title(text)
                self.assertLessEqual(len(title), _TITLE_MAX)
                self.assertEqual(title.count("("), title.count(")"), title)
                self.assertEqual(title, title.strip())

    def test_seo_title_keeps_scale_level_distinct(self):
        # Regression for the multiscopo satisfaction-level family: 11 pages
        # ("pari a 0".."pari a 10"), each with the same trailing "(scala 0-10)"
        # parenthetical, used to truncate to one identical <title> for all of
        # them (the digit sat past the 60-char budget, only the shared scale
        # marker survived).
        from app.indicator_notes import seo_title

        names = [
            f"Persone di 14 anni e più con un livello di soddisfazione per la "
            f"vita pari a {level} (scala 0-10)"
            for level in range(11)
        ]
        titles = [seo_title(name, "Divario Italia") for name in names]
        self.assertEqual(len(titles), len(set(titles)), titles)
        for title in titles:
            self.assertLessEqual(len(title), 60, title)

    def test_seo_title_source_qualifier_disambiguates_duplicate_bes(self):
        # A BES id in taxonomy.DUPLICATE_BES_IDS is hidden from browsing but its
        # page stays indexable, so it must not share a <title> with the
        # territorial series it duplicates.
        from app.indicator_notes import seo_title
        from app import sources

        qualifier = sources.family_short_label("bes")
        plain = seo_title("Speranza di vita alla nascita", "Divario Italia")
        qualified = seo_title(
            "Speranza di vita alla nascita", "Divario Italia", source_qualifier=qualifier,
        )
        self.assertNotEqual(plain, qualified)
        self.assertLessEqual(len(qualified), 60, qualified)  # same budget as every other title
        self.assertIn(qualifier.split()[0], qualified)  # institution context survives truncation

    def test_all_duplicate_bes_titles_are_unique_and_within_budget(self):
        # Every id in taxonomy.DUPLICATE_BES_IDS gets a qualified title (see
        # views._render_indicator). None may exceed the 60-char budget, and two
        # ids sharing a truncated core (e.g. "Competenza numerica"/"alfabetica")
        # must not collapse onto the same qualified title either.
        from app.bes_data import get_bes_rows
        from app.indicator_notes import seo_title
        from app.taxonomy import DUPLICATE_BES_IDS
        from app import sources

        qualifier = sources.family_short_label("bes")
        names = {}
        for row in get_bes_rows("regione"):
            if row["id"] in DUPLICATE_BES_IDS and row["id"] not in names:
                names[row["id"]] = row["name"]
        self.assertEqual(set(names), DUPLICATE_BES_IDS)

        titles = {
            raw_id: seo_title(name, "Divario Italia", source_qualifier=qualifier)
            for raw_id, name in names.items()
        }
        for raw_id, title in titles.items():
            self.assertLessEqual(len(title), 60, f"{raw_id}: {title}")
        self.assertEqual(len(titles), len(set(titles.values())), titles)

    def test_public_game_and_editorial_metadata_within_budget(self):
        client = app.test_client()
        paths = (
            "/quiz/chi-e-maggiore",
            "/quiz/ordina",
            "/quiz",
            "/quiz/indovina-la-regione",
            "/qualita-della-vita/classifica/regioni",
            "/qualita-della-vita/classifica/province?profilo=accessibilita",
            "/qualita-della-vita/classifica/regioni?profilo=accessibilita",
            "/blog/divario-turistico-nord-sud-2024",
            "/blog/divario-genere-occupazione-regioni-2024",
            "/blog/servizi-infanzia-regioni-2023",
            # Longest region/theme names in the catalog: the tightest budget fits.
            "/regione/friuli-venezia-giulia",
            "/regione/trentino-alto-adige",
            "/tema/reddito-inclusione-e-accessibilita",
        )
        for path in paths:
            response = client.get(path)
            self.assertEqual(response.status_code, 200, path)
            html = response.data.decode("utf-8")
            title_match = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
            description_match = re.search(
                r'<meta name="description" content="([^"]*)"', html
            )
            self.assertIsNotNone(title_match, path)
            self.assertIsNotNone(description_match, path)
            title = unescape(title_match.group(1)).strip()
            description = unescape(description_match.group(1)).strip()
            self.assertLessEqual(len(title), 60, f"title too long for {path}: {title}")
            self.assertLessEqual(
                len(description), 155, f"description too long for {path}: {description}"
            )

    def test_dataset_schema(self):
        dataset = Path(app.root_path) / "static" / "data" / "Assoluti_Regione.csv"
        expected_columns = [
            "idIndicatore",
            "Territorio",
            "Tema",
            "Indicatore",
            "UDM",
            "Fonte",
            "Archivio",
            "Anno",
            "Livello/Variazione",
            "Dato",
            "Benchmark",
            "Area",
        ]

        with dataset.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            self.assertEqual(reader.fieldnames, expected_columns)
            first_row = next(reader)

        self.assertEqual(first_row["Area"], "Regione")
        self.assertEqual(first_row["Fonte"], "Istat")
        self.assertTrue(first_row["Dato"])


class ITitoliCheSiLeggonoSuGoogle(unittest.TestCase):
    """La catena vera di `seo_titles.page_title`, su tutto il catalogo indicizzabile.

    Una pagina e' una coppia (indicatore, livello), e qui si misurano le coppie
    **vive**: ogni pagina di livello indicizzabile (`indicator_universe.level_pages`),
    cioe' la base di ogni scheda e le `/province` indicizzabili. Titolo,
    descrizione e Dataset escono dalle stesse chiamate di `_render_indicator`,
    qualificatore di fonte compreso (`views._source_qualifier`): le due prove
    che c'erano prima guardavano `indicator_notes.seo_title` e
    `authored_seo_title` per conto loro, cioe' una catena che la scheda non usa
    piu', e non avrebbero visto una collisione del titolo servito.

    Nessuna collisione e' ammessa. Le due che stavano dichiarate qui (598 e 599,
    910 e bes:01SAL001) sono sparite: la prima col nome breve curato
    (`indicator_notes.SHORT_NAMES`), la seconda perche' la pagina vera passa il
    qualificatore che la prova di prima non passava.
    """

    @classmethod
    def setUpClass(cls):
        from app import (
            indicator_texts,
            indicator_universe,
            indicator_view,
            seo_titles,
            views,
        )

        cls.titoli = {}
        cls.descrizioni = {}
        cls.dataset = {}
        for voce in indicator_universe.level_pages():
            base = voce["meta"]
            vista = indicator_view.build_indicator_view(base["family"], str(base["raw_id"]))
            meta = vista["meta"]
            level = next(lv for lv in vista["levels"] if lv["key"] == voce["level"]["key"])
            # La chiave e' il path: la base e la `/province` di una scheda
            # sono due pagine, con lo stesso id.
            chiave = voce["path"]
            articolo = indicator_texts.build_article(meta["id"], level["key"])
            # Le chiamate sono le stesse che fa `_render_indicator`, incluso
            # il lead composto come ultima spiaggia: senza quello la descrizione
            # torna `None` sulle serie `contextual` senza pezzo, e il test
            # misurerebbe una pagina che il sito non serve.
            lead = articolo["lead"] or indicator_texts.composed_lead(meta, level)
            qualifier = views._source_qualifier(base["family"], str(base["raw_id"]))
            cls.titoli[chiave] = seo_titles.page_title(
                articolo, meta, level, site_name="Divario Italia", source_qualifier=qualifier)
            cls.descrizioni[chiave] = seo_titles.page_description(
                articolo, meta, level, composed=lead)
            cls.dataset[chiave] = views._dataset_description(lead, meta)

    def test_nessun_titolo_sfora_il_budget_serp(self):
        for ind, titolo in self.titoli.items():
            with self.subTest(indicatore=ind):
                self.assertTrue(titolo, ind)
                self.assertLessEqual(len(titolo), 60, f"{ind}: {titolo}")
                self.assertGreaterEqual(len(titolo), 8, f"{ind}: {titolo}")
                self.assertEqual(titolo, titolo.strip())
                self.assertEqual(titolo.count("("), titolo.count(")"), f"{ind}: {titolo}")

    def test_nessuna_descrizione_sfora_il_budget_serp(self):
        for ind, descrizione in self.descrizioni.items():
            with self.subTest(indicatore=ind):
                self.assertTrue(descrizione, ind)
                self.assertLessEqual(len(descrizione), 155, f"{ind}: {descrizione}")
                self.assertTrue(descrizione.rstrip().endswith("."), f"{ind}: {descrizione}")

    def test_due_pagine_indicizzabili_non_hanno_lo_stesso_titolo(self):
        per_titolo = {}
        for ind, titolo in self.titoli.items():
            per_titolo.setdefault(titolo, set()).add(ind)
        collisioni = {titolo: ids for titolo, ids in per_titolo.items() if len(ids) > 1}
        self.assertEqual(collisioni, {})

    # Le pagine d'ingresso: le schede le misura `self.titoli`, queste no, e
    # nessuno le misurava. La home stava a 73 caratteri perche' finiva con
    # `sources_label`, che si allunga a ogni fonte nuova, e la coda tagliata era
    # proprio quella che nominava le fonti.
    HUB = ("/", "/regioni", "/temi", "/qualita-della-vita", "/regione/molise",
           "/regione/friuli-venezia-giulia", "/tema/lavoro-e-conciliazione",
           "/divari-regionali", "/blog", "/metodologia", "/catalogo-dati")

    def test_nessun_hub_sfora_il_budget_serp(self):
        from html import unescape

        client = app.test_client()
        for path in self.HUB:
            with self.subTest(path=path):
                risposta = client.get(path)
                self.assertEqual(risposta.status_code, 200, path)
                corpo = risposta.get_data(as_text=True)
                trovato = re.search(r"<title>(.*?)</title>", corpo, re.S)
                self.assertIsNotNone(trovato, f"{path} [{risposta.content_type}] {corpo[:200]!r}")
                titolo = unescape(trovato.group(1).strip())
                self.assertLessEqual(len(titolo), 60, f"{path}: {titolo}")
                self.assertTrue(titolo, path)

    def test_ogni_hub_porta_un_numero_tranne_dove_non_ha_senso(self):
        """Un hub che dice solo di che cosa parla non da' un motivo per
        cliccare piu' di quanto ne dia la scheda. Blog, metodologia e
        divari-regionali sono pagine di prosa: li' il numero non c'e'."""
        from html import unescape

        client = app.test_client()
        senza_numero = {"/blog", "/metodologia", "/divari-regionali"}
        for path in self.HUB:
            if path in senza_numero:
                continue
            with self.subTest(path=path):
                pagina = client.get(path).get_data(as_text=True)
                titolo = unescape(re.search(r"<title>(.*?)</title>", pagina, re.S).group(1))
                self.assertTrue(any(c.isdigit() for c in titolo), f"{path}: {titolo}")

    def test_la_maggioranza_dei_titoli_porta_una_cifra(self):
        """E' il punto di tutto il lavoro: un titolo che dice solo il nome della
        serie non da' un motivo per cliccare. Le pagine senza cifra sono quasi
        tutte `contextual`, dove il catalogo non espone estremi di proposito."""
        con_cifra = sum(1 for t in self.titoli.values() if any(c.isdigit() for c in t))
        self.assertGreaterEqual(con_cifra / len(self.titoli), 0.6)

    def test_nessun_titolo_dice_per_regione_sopra_dati_provinciali(self):
        """`indicator_notes._TITLE_TAIL` e' fissa: la coda ora segue il livello.

        Ogni pagina provinciale, anche la vista `/province` di una
        scheda a due livelli, e per la catena intera di `page_title`: la vista
        province dei NEET passava dal ripiego, che aveva la coda fissa, e diceva
        "per regione" mentre `answer_title` da solo era in regola.
        """
        from app import (
            indicator_texts,
            indicator_universe,
            indicator_view,
            seo_titles,
            views,
        )

        for family, raw_id in indicator_universe.all_indicator_refs():
            vista = indicator_view.build_indicator_view(family, raw_id)
            if vista is None:
                continue
            for level in vista["levels"]:
                if level["key"] != "provincia":
                    continue
                articolo = indicator_texts.build_article(vista["meta"]["id"], level["key"])
                titolo = seo_titles.page_title(
                    articolo, vista["meta"], level, site_name="Divario Italia",
                    source_qualifier=views._source_qualifier(family, raw_id))
                with self.subTest(indicatore=vista["meta"]["id"]):
                    self.assertNotIn(" per regione", titolo or "")
                    self.assertLessEqual(len(titolo), 60, titolo)

    # Le cifre come si leggono: "dal 8" e "al 0" sono italiano sbagliato, "0,00"
    # una precisione che lo zero non ha. "dal 116%" e "dal 1.022" invece sono
    # giusti (centosedici, milleventidue), e la regola non li deve vietare, e
    # nemmeno "0,004", la cifra sotto un centesimo scritta fino alla prima
    # cifra significativa.
    CIFRE_SBAGLIATE = re.compile(r"0,00(?!\d)|\b(dal|al) (0|8|11(?!\d)|1(?![\d.]))|\b(dall|all)'1(\d\d|\.\d)")

    def test_niente_caratteri_vietati_in_serp(self):
        """Gli assoluti di `content/STYLE.md` valgono anche sul testo in SERP."""
        for ind in self.titoli:
            for testo in (self.titoli[ind], self.descrizioni[ind]):
                for vietato in ("—", "–", ";", "…"):
                    with self.subTest(indicatore=ind, carattere=vietato):
                        self.assertNotIn(vietato, testo or "")
                with self.subTest(indicatore=ind, testo=testo):
                    self.assertIsNone(self.CIFRE_SBAGLIATE.search(testo or ""), testo)

    def test_la_regola_delle_cifre_non_vieta_l_italiano_giusto(self):
        for giusto in ("dal 116% al 3,9%", "dal 1.022 al 980", "dall'89,1% allo 0%",
                       "dall'11,9% all'1,3%", "dallo 0,94% al -2,6%", "da 3,4 a 0", "dallo 0,004%"):
            with self.subTest(testo=giusto):
                self.assertIsNone(self.CIFRE_SBAGLIATE.search(giusto))
        for sbagliato in ("dal 89,1%", "al 0,22%", "al 1,3%", "dal 11,9%", "da 3,4 a 0,00", "dall'116%"):
            with self.subTest(testo=sbagliato):
                self.assertIsNotNone(self.CIFRE_SBAGLIATE.search(sbagliato))

    def test_il_dataset_non_porta_markdown(self):
        """Il lead e' Markdown e il JSON-LD e' testo: in produzione quello di
        `bes-04BEC002P` diceva "A [Milano](/provincia/milano) la retribuzione"."""
        for ind, testo in self.dataset.items():
            with self.subTest(indicatore=ind):
                self.assertNotIn("](", testo)

    def test_il_dataset_reso_non_porta_markdown(self):
        """La stessa prova sulla pagina servita, perche' il template potrebbe
        prendere la descrizione da un'altra parte: le due schede il cui lead ha
        un link, lette nel JSON-LD come le legge un motore."""
        import json

        def nodi(dato):
            if isinstance(dato, list):
                for voce in dato:
                    yield from nodi(voce)
            elif isinstance(dato, dict):
                yield dato
                yield from nodi(dato.get("@graph", []))

        client = app.test_client()
        for path in ("/indicatore/retribuzione-media-annua-dei-lavoratori-dipendenti/bes-04BEC002P",
                     "/indicatore/tasso-di-occupazione-totale/ter-13"):
            with self.subTest(path=path):
                risposta = client.get(path)
                self.assertEqual(risposta.status_code, 200, path)
                corpo = risposta.get_data(as_text=True)
                blocchi = re.findall(r'<script type="application/ld\+json">(.*?)</script>', corpo, re.DOTALL)
                descrizioni = [nodo.get("description", "")
                               for blocco in blocchi for nodo in nodi(json.loads(blocco))
                               if nodo.get("@type") == "Dataset"]
                self.assertTrue(descrizioni, f"{path}: nessun Dataset nel JSON-LD")
                for descrizione in descrizioni:
                    self.assertTrue(descrizione)
                    self.assertNotIn("](", descrizione)


class HardeningTest(unittest.TestCase):
    def test_home_is_not_cached(self):
        """La home si rende a ogni richiesta: l'indicatore in evidenza cambia a
        ogni visita (`app/home_pick.py`), e una pagina tenuta cinque minuti per
        worker mostrerebbe lo stesso a tutti. Fino al 24 settembre 2026 questa
        prova diceva il contrario, quando la home era uguale per tutti e la
        cache era cio' che la teneva leggera: oggi la leggerezza la danno i
        loader in cache per processo, e a caldo la home si rende in decine di
        millisecondi."""
        from unittest import mock
        from app import cache

        cache.clear()
        try:
            with mock.patch("app.design.render_template", return_value="OK") as rt:
                client = app.test_client()
                client.get("/")
                client.get("/")
                client.get("/")
                self.assertEqual(rt.call_count, 3)
        finally:
            cache.clear()

    def test_events_rate_limited(self):
        """L'endpoint pubblico /api/events blocca lo spam con 429 oltre la soglia."""
        from app import cache

        cache.clear()
        client = app.test_client()
        codes = [
            client.post("/api/events", json={"name": "unit_test"}).status_code
            for _ in range(35)
        ]
        self.assertEqual(codes.count(204), 30)
        self.assertTrue(codes.count(429) >= 1)


class LUniversoHaUnProprietarioSolo(unittest.TestCase):
    """Chi risponde a "questa pagina va in indice" deve essere uno.

    Ce n'erano due: `indicator_view` (che la sitemap legge) e una copia dentro
    `app/views.py` scritta per il cruscotto. Non davano la stessa risposta:
    `dem:LIFEEXP65F` e `dem:LIFEEXP65M` sono varianti di genere, la sitemap non
    le pubblica, e il cruscotto le contava fra le indicizzabili. Un cruscotto che
    conta pagine che non esistono e' peggio di un cruscotto vuoto, perche' non lo
    dice. La copia e' stata cancellata: questo test e' quello che l'avrebbe
    trovata, e resta perche' la prossima nascerebbe uguale.
    """

    def test_l_universo_editoriale_e_quello_delle_pagine_pubbliche(self):
        from app import indicator_universe
        refs = indicator_universe.all_indicator_refs()
        self.assertEqual(len(refs), len(set(refs)), "un indicatore contato due volte")
        # 594 e' il catalogo dell'atlante: 40 serie BES hanno solo osservazioni
        # provinciali, quindi non ci entrano ma la loro pagina esiste.
        self.assertGreater(len(refs), 594)

    def test_le_varianti_di_genere_restano_fuori_indice(self):
        """I due casi su cui la copia cancellata sbagliava, per nome.

        Un test sui numeri totali non li avrebbe nominati, e un totale che torna
        per compensazione e' il modo in cui questa classe di difetto sopravvive
        a una suite verde."""
        # `dem` è l'acronimo dell'URL, `istat_demografia` la chiave di famiglia:
        # non coincidono, ed è la stessa trappola per cui `ims` non è `multiscopo`.
        from app import indicator_view, sources
        famiglia = sources.parse_indicator_code("dem-LIFEEXP65F")[0]
        for raw_id in ("LIFEEXP65F", "LIFEEXP65M"):
            vista = indicator_view.build_indicator_view(famiglia, raw_id)
            self.assertIsNotNone(vista, f"dem-{raw_id} non si risolve piu'")
            self.assertFalse(vista["meta"]["indexable"], f"dem-{raw_id}")
            self.assertEqual(vista["meta"]["indexable_reason"], "variante")

    def test_un_motivo_per_ogni_pagina_fuori_indice(self):
        """`variante`, `copertura` e `vecchia` si riparano in tre modi diversi:
        un motivo unico li appiattirebbe e la riga si leggerebbe come un guasto
        invece che come una scelta."""
        from app import indicator_universe
        for record in indicator_universe.projection():
            meta = record["meta"]
            if meta["indexable"]:
                self.assertIsNone(meta["indexable_reason"])
            else:
                self.assertIn(meta["indexable_reason"], ("variante", "copertura", "vecchia"))

    def test_allargare_la_passata_non_cambia_la_sitemap(self):
        """Il dedup su `canonical_path` resta **dentro** il sottoinsieme
        indicizzabile: deduplicando prima di filtrare, un non indicizzabile che
        occupa il path butterebbe fuori dalla sitemap il suo gemello."""
        from app import indicator_universe
        catalogo = indicator_universe.indexable_catalog()
        percorsi = [r["meta"]["canonical_path"] for r in catalogo]
        self.assertEqual(len(percorsi), len(set(percorsi)))
        self.assertTrue(all(r["meta"]["indexable"] for r in catalogo))
        attesi = sum(1 for r in indicator_universe.projection() if r["meta"]["indexable"])
        self.assertEqual(len(catalogo), attesi)


class TheImageShipsEverythingTheAppImports(unittest.TestCase):
    """Il guasto che si vede solo in produzione, e lì si vede tutto insieme.

    `app/indicator_texts.py` importa `scripts.indicator_store`, che possiede il
    formato degli articoli in `content/indicators/`. Lo store sta in `scripts/`
    e non in `app/` perché lo leggono anche gli script della catena, che sono
    stdlib puri e non possono importare `app/__init__.py`, il quale importa
    Flask.

    Il Dockerfile però copia solo alcune directory. Quando lo store è nato,
    `scripts/` non era fra quelle: l'immagine sarebbe morta all'avvio con un
    ModuleNotFoundError, cioè il sito giù invece di una pagina sbagliata, e
    la suite non se ne sarebbe accorta perché qui gira senza container.

    Questo test legge le importazioni vere invece di fidarsi di un elenco, così
    vale anche per la prossima directory che qualcuno deciderà di importare.
    """

    ROOT = Path(__file__).resolve().parents[2]
    # Quello che l'immagine ha comunque, senza bisogno di una COPY nel Dockerfile.
    ALWAYS_THERE = {"app", "flask", "werkzeug", "jinja2", "markdown", "yaml"}

    def _copied_dirs(self):
        text = (self.ROOT / "Dockerfile").read_text(encoding="utf-8")
        copied = set()
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("COPY ") or "--from=" in line:
                continue
            source = line.split()[1]
            if source.endswith("/"):
                copied.add(source.rstrip("/"))
        return copied

    def _top_level_imports_of_app(self):
        import ast

        found = set()
        for path in sorted((self.ROOT / "app").rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    found.update(a.name.split(".")[0] for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    found.add(node.module.split(".")[0])
        return found

    def test_every_repo_package_the_app_imports_is_copied(self):
        copied = self._copied_dirs()
        missing = []
        for name in sorted(self._top_level_imports_of_app()):
            if name in self.ALWAYS_THERE or name in copied:
                continue
            # Solo i pacchetti che stanno in questo repo: le dipendenze esterne
            # arrivano da requirements.txt, non da una COPY.
            if (self.ROOT / name / "__init__.py").exists():
                missing.append(name)
        self.assertEqual(
            missing, [],
            f"l'app importa {missing} ma il Dockerfile non li copia: "
            f"l'immagine non partirebbe. COPY presenti: {sorted(copied)}",
        )

    def test_the_store_is_the_case_that_made_this_necessary(self):
        self.assertIn("scripts", self._copied_dirs())

    def test_the_runtime_data_is_shipped(self):
        """`app/publisher.py` legge `data/source_state.json` a runtime: senza la COPY
        nel Dockerfile la data dell'ultimo aggiornamento delle fonti sparisce dalle
        pagine, un guasto che si vede solo in produzione e mai nella suite qui, che
        gira col repo intero. Fino al 5/9/2026 questo test difendeva anche il cruscotto
        `/_pipeline`, tolto con la catena editoriale: la COPY resta necessaria lo
        stesso, per un motivo diverso."""
        self.assertIn(
            "data", self._copied_dirs(),
            "il Dockerfile non copia data/: in produzione publisher.py non trova "
            "data/source_state.json e la data delle fonti sparisce.",
        )

    def test_dockerignore_keeps_runtime_state_out_of_the_image(self):
        """`COPY data/` spedisce la storia committata, ma `.gitignore` NON protegge
        il build context: solo `.dockerignore` lo fa. Un `docker build .` da un
        working tree includerebbe altrimenti `data/leaderboard.sqlite3` (email, UUID,
        nickname, preferiti: PII) e l'effimero. Qui si esige che le esclusioni di
        runtime del `.gitignore` siano specchiate nel `.dockerignore`."""
        dockerignore = (self.ROOT / ".dockerignore").read_text(encoding="utf-8").split()
        for pattern in ("data/*.sqlite3", "data/istat_cache/", "data/eurostat_cache/"):
            self.assertIn(
                pattern, dockerignore,
                f".dockerignore non esclude {pattern}: un docker build da working tree "
                f"potrebbe imbarcare stato di runtime o PII nell'immagine.",
            )


class LaCspDeiFontSegueLaPagina(unittest.TestCase):
    """Da quando i font sono self-hostati, `fonts.googleapis.com` serve a una
    pagina sola.

    Toglierlo dappertutto romperebbe `/legacy`, che carica Mukta da li' e che
    CLAUDE.md dice di non rompere: un font che non carica e' un modo di
    romperla. Quindi la CSP e' la stessa ovunque tranne i due domini dei font,
    che restano sulle sole rotte legacy.
    """

    def setUp(self):
        self.client = app.test_client()

    def test_le_pagine_nuove_non_ammettono_i_font_di_google(self):
        for path in ("/", "/temi", "/indicatore/pil-pro-capite/ter-901", "/blog"):
            with self.subTest(path=path):
                csp = self.client.get(path).headers["Content-Security-Policy"]
                self.assertNotIn("fonts.googleapis.com", csp)
                self.assertNotIn("fonts.gstatic.com", csp)

    def test_legacy_li_ammette_ancora(self):
        for path in ("/legacy", "/legacy-reddito"):
            with self.subTest(path=path):
                csp = self.client.get(path).headers["Content-Security-Policy"]
                self.assertIn("https://fonts.googleapis.com", csp)
                self.assertIn("https://fonts.gstatic.com", csp)

    def test_il_resto_della_policy_non_cambia_fra_le_due(self):
        """Solo i font: se un domani la CSP di legacy diverge su altro, e' un
        buco che nessuno ha deciso di aprire."""
        nuova = self.client.get("/").headers["Content-Security-Policy"]
        legacy = self.client.get("/legacy").headers["Content-Security-Policy"]
        pulita = legacy.replace(" https://fonts.googleapis.com", "").replace(" https://fonts.gstatic.com", "")
        self.assertEqual(pulita, nuova)


class IlFeedDelBlog(unittest.TestCase):
    """Un feed che nessuno trova non esiste, e prima le tre forme con cui si
    cerca rispondevano tutte e tre 404."""

    def setUp(self):
        self.client = app.test_client()

    def test_risponde_come_rss(self):
        risposta = self.client.get("/blog/feed.xml")
        self.assertEqual(risposta.status_code, 200)
        self.assertTrue(risposta.headers["Content-Type"].startswith("application/rss+xml"))

    def test_e_xml_valido_con_un_item_per_post(self):
        from xml.etree import ElementTree
        from app.blog import get_posts

        albero = ElementTree.fromstring(self.client.get("/blog/feed.xml").data)
        voci = albero.findall("./channel/item")
        self.assertEqual(len(voci), min(len(get_posts()), 20))
        for voce in voci:
            with self.subTest(voce=voce.findtext("title")):
                for campo in ("title", "link", "guid", "pubDate", "description"):
                    self.assertTrue((voce.findtext(campo) or "").strip(), campo)

    def test_le_date_sono_in_rfc_822(self):
        """L'ISO della sitemap qui non si legge, e un lettore che non sa
        interpretare `pubDate` tiene l'articolo in cima per sempre."""
        import email.utils
        from xml.etree import ElementTree

        albero = ElementTree.fromstring(self.client.get("/blog/feed.xml").data)
        for voce in albero.findall("./channel/item"):
            testo = voce.findtext("pubDate")
            with self.subTest(pubDate=testo):
                self.assertIsNotNone(email.utils.parsedate_to_datetime(testo))

    def test_i_link_rispondono(self):
        from xml.etree import ElementTree

        albero = ElementTree.fromstring(self.client.get("/blog/feed.xml").data)
        for voce in albero.findall("./channel/item"):
            percorso = voce.findtext("link").replace("https://divarioitalia.it", "")
            with self.subTest(percorso=percorso):
                self.assertEqual(self.client.get(percorso).status_code, 200)

    def test_le_due_forme_abbreviate_ci_portano(self):
        for path in ("/feed.xml", "/rss.xml"):
            with self.subTest(path=path):
                risposta = self.client.get(path)
                self.assertEqual(risposta.status_code, 301)
                self.assertTrue(risposta.headers["Location"].endswith("/blog/feed.xml"))

    def test_le_pagine_lo_dichiarano_in_testa(self):
        for path in ("/blog", "/blog/pil-pro-capite-regioni-divario-2024", "/temi"):
            with self.subTest(path=path):
                html = self.client.get(path).get_data(as_text=True)
                self.assertIn('type="application/rss+xml"', html)
                self.assertIn("/blog/feed.xml", html)

class NessunaAnteprimaSocialeEUnSvg(unittest.TestCase):
    """Un SVG in `og:image` vuol dire nessuna immagine.

    Facebook, LinkedIn, X, WhatsApp e Slack scartano l'SVG e mostrano il link
    nudo, e `image` dello schema `Article` vuole un raster. Il sito dichiarava
    `twitter:card=summary_large_image`, cioe' il formato fatto apposta per una
    figura grande, sopra un file che nessuno di quei lettori apre: ogni
    condivisione di ogni pagina usciva senza figura.
    """

    PAGINE = (
        "/", "/atlante", "/confronto", "/temi", "/regioni", "/province",
        "/provincia/lecce",
        "/indicatore/pil-pro-capite/ter-901", "/qualita-della-vita", "/blog",
        "/divari-regionali", "/catalogo-dati", "/metodologia",
    )

    def setUp(self):
        self.client = app.test_client()

    def _og_image(self, html):
        trovato = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        return trovato.group(1) if trovato else None

    def test_ogni_pagina_ne_dichiara_una_e_non_e_un_svg(self):
        from app.blog import get_posts

        percorsi = list(self.PAGINE) + [f"/blog/{post['slug']}" for post in get_posts()]
        for path in percorsi:
            with self.subTest(path=path):
                immagine = self._og_image(self.client.get(path).get_data(as_text=True))
                self.assertIsNotNone(immagine, f"{path}: nessuna og:image")
                self.assertFalse(immagine.endswith(".svg"), f"{path}: {immagine}")

    def test_il_file_dichiarato_esiste(self):
        from app.blog import get_posts

        percorsi = list(self.PAGINE) + [f"/blog/{post['slug']}" for post in get_posts()]
        for path in percorsi:
            with self.subTest(path=path):
                immagine = self._og_image(self.client.get(path).get_data(as_text=True))
                locale = immagine.replace("https://divarioitalia.it", "")
                self.assertEqual(self.client.get(locale).status_code, 200, locale)

    def test_le_misure_dichiarate_sono_quelle_vere(self):
        """Dichiararle sbagliate e' peggio che non dichiararle: la scheda si
        disegna sul rapporto annunciato e poi l'immagine non ci sta. Le tre
        copertine in JPG sono 1376x768 e infatti non le dichiarano."""
        from app.blog import get_posts, social_image_size

        for post in get_posts():
            with self.subTest(post=post["slug"]):
                html = self.client.get(f"/blog/{post['slug']}").get_data(as_text=True)
                larghezza = re.search(r'<meta property="og:image:width" content="(\d+)"', html)
                misura = social_image_size(post["social_image"])
                if misura is None:
                    self.assertIsNone(larghezza, post["social_image"])
                else:
                    self.assertEqual(int(larghezza.group(1)), misura[0])

    def test_la_copertina_in_pagina_resta_il_vettoriale(self):
        """Il PNG serve al social, non allo schermo: in pagina l'SVG e' piu'
        nitido e pesa meno. Dalla 1.0 un post con copertina SVG apre sulla
        striscia del divario disegnata dai dati, e la copertina compare solo
        dove la striscia non si puo' disegnare: in nessuno dei due casi lo
        schermo riceve il PNG."""
        html = self.client.get("/blog/pil-pro-capite-regioni-divario-2024").get_data(as_text=True)
        self.assertNotIn('src="/static/img/blog/pil-pro-capite.png"', html)
        self.assertTrue('src="/static/img/blog/pil-pro-capite.svg"' in html or 'class="lead-figure"' in html)

    def test_ogni_svg_di_copertina_ha_il_suo_png(self):
        """Se manca, `blog.social_image` ripiega sulla figura del sito e il post
        perde la sua: si rigenera con scripts/rasterize_og_images.py."""
        cartella = Path(__file__).resolve().parents[2] / "app" / "static" / "img"
        sorgenti = [cartella / "og-divario-italia.svg"] + sorted((cartella / "blog").glob("*.svg"))
        for sorgente in sorgenti:
            with self.subTest(sorgente=sorgente.name):
                self.assertTrue(sorgente.with_suffix(".png").exists(),
                                f"manca il PNG di {sorgente.name}")

class LaDefinizioneDellaFonteStaInTutteEDueLeForme(unittest.TestCase):
    """HTML e Markdown sono lo stesso documento alla stessa URL.

    La definizione che ne da' l'istituto (`meta["archive"]`, da
    `data/definitions/`) la pagina HTML la mostra da sempre nell'apparato. La
    proiezione markdown no: chi chiedeva `Accept: text/markdown` riceveva la
    formula che il sito si compone da se' e non la definizione della fonte,
    cioe' una pagina diversa sotto lo stesso canonico. Copre 346 delle 372
    schede indicizzabili.
    """

    SCHEDE = (
        "/indicatore/pil-pro-capite/ter-901",
        "/indicatore/numero-medio-di-figli-per-donna/ter-922",
        "/indicatore/adeguata-alimentazione-tassi-standardizzati/bes-01SAL013",
    )

    # Una delle 26 scoperte: `data/definitions/` non ha ancora il foglio delle
    # serie provinciali BES, e li' la pagina deve restare com'era.
    SENZA_DEFINIZIONE = "/indicatore/retribuzione-media-annua-dei-lavoratori-dipendenti/bes-04BEC002P"

    def setUp(self):
        self.client = app.test_client()

    def _markdown(self, path):
        return self.client.get(path, headers={"Accept": "text/markdown"}).get_data(as_text=True)

    def test_il_markdown_la_porta(self):
        for path in self.SCHEDE:
            with self.subTest(path=path):
                self.assertIn("## Definizione della fonte", self._markdown(path))

    def test_e_lo_stesso_testo_dell_html(self):
        for path in self.SCHEDE:
            with self.subTest(path=path):
                html = unescape(self.client.get(path).get_data(as_text=True))
                riga = re.search(r"<dt>Definizione della fonte</dt>\s*<dd>(.*?)<a ", html, re.S)
                self.assertIsNotNone(riga, f"{path}: l'HTML non la mostra piu'")
                testo = re.sub(r"<[^>]+>", "", riga.group(1)).strip()
                self.assertIn(testo, unescape(self._markdown(path)))

    def test_la_dichiara_anche_il_dataset(self):
        """`variableMeasured.description` e' lo slot per "che cosa misura", e
        quello che ci sta dentro la pagina lo mostra: nessuna dichiarazione che
        il visibile non sostenga."""
        import json

        for path in self.SCHEDE:
            with self.subTest(path=path):
                html = self.client.get(path).get_data(as_text=True)
                for blocco in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
                    documento = json.loads(blocco)
                    if documento.get("@type") != "Dataset":
                        continue
                    descrizione = documento["variableMeasured"].get("description")
                    self.assertTrue(descrizione)
                    self.assertIn(descrizione, unescape(html))
                    break
                else:
                    self.fail(f"{path}: nessun Dataset")

    def test_una_scheda_senza_definizione_non_inventa_la_sezione(self):
        """Le 26 scoperte sono le provinciali BES, dove `data/definitions/` non
        arriva ancora: li' ne' l'HTML ne' il markdown devono emettere un titolo
        sopra il vuoto."""
        html = self.client.get(self.SENZA_DEFINIZIONE).get_data(as_text=True)
        self.assertNotIn("Definizione della fonte", html)
        self.assertNotIn("## Definizione della fonte", self._markdown(self.SENZA_DEFINIZIONE))


class IlTemaSegueIlSistemaFinoAllaPrimaScelta(unittest.TestCase):
    """Una regola sola, in tre implementazioni che devono restare d'accordo.

    Prima: `ds-chrome.js`, il bootstrap inline e il toggle React leggevano solo
    `localStorage`, quindi chi tiene il sistema in scuro riceveva il sito
    chiaro. Peggio, il toggle React scriveva `localStorage` **al montaggio**:
    bastava passare una volta da `/atlante` perche' una preferenza di sistema
    diventasse una scelta esplicita e il sito restasse chiaro per sempre.

    La regola: una scelta esplicita vince, senza scelta decide
    `prefers-color-scheme`, e si scrive solo quando qualcuno tocca
    l'interruttore.
    """

    PAGINE = ("/", "/atlante", "/confronto", "/temi", "/blog",
              "/indicatore/pil-pro-capite/ter-901", "/qualita-della-vita")
    TEMPLATES = Path(__file__).resolve().parents[2] / "app" / "templates"
    STATICI = Path(__file__).resolve().parents[2] / "app" / "static"

    def setUp(self):
        self.client = app.test_client()

    def test_ogni_pagina_decide_il_tema_una_volta_sola(self):
        for path in self.PAGINE:
            with self.subTest(path=path):
                html = self.client.get(path).get_data(as_text=True)
                self.assertEqual(html.count("divario-theme"), 1, path)
                self.assertIn("prefers-color-scheme", html, path)

    def test_nessun_template_si_riscrive_il_bootstrap(self):
        """Erano tre copie a mano in app.html, blog_base.html e
        confronto.html: tre copie della stessa regola vanno fuori sincrono."""
        for percorso in self.TEMPLATES.glob("*.html"):
            if percorso.name == "_theme_bootstrap.html":
                continue
            with self.subTest(template=percorso.name):
                self.assertNotIn("divario-theme", percorso.read_text(encoding="utf-8"))

    def test_il_bootstrap_decide_prima_di_dipingere(self):
        """Applicato dopo il primo paint, chi legge in scuro vede un lampo di
        pagina chiara a ogni navigazione."""
        for path in self.PAGINE:
            with self.subTest(path=path):
                html = self.client.get(path).get_data(as_text=True)
                self.assertLess(html.index("divario-theme"), html.index("</head>"), path)

    def test_l_altra_implementazione_segue_la_stessa_regola(self):
        """Ne restano due: il bootstrap inline e `ds-chrome.js`."""
        sorgente = (self.STATICI / "js" / "ds-chrome.js").read_text(encoding="utf-8")
        self.assertIn("prefers-color-scheme", sorgente)

    def test_la_spa_non_decide_piu_il_tema(self):
        """C'era una terza implementazione in React, e aveva il difetto
        peggiore: scriveva `localStorage` dentro un effetto che gira anche al
        montaggio, quindi passare una volta da /atlante trasformava una
        preferenza di sistema in una scelta esplicita e teneva il sito chiaro
        per sempre.

        Esisteva perche' `ds-chrome.js` aggancia i bottoni una volta sola e la
        testata React montava dopo. Da quando la testata la rende Flask anche
        su quelle due rotte, il bottone c'e' gia' nell'HTML iniziale e quella
        ragione non c'e' piu'."""
        sorgente = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "main.jsx").read_text(encoding="utf-8")
        self.assertNotIn("divario-theme", sorgente)
        self.assertNotIn("localStorage.setItem(THEME_KEY", sorgente)

class UnaTestataSolaSuTuttoIlSito(unittest.TestCase):
    """Due testate sullo stesso dominio erano due identita'.

    Le pagine Flask rendevano `_ds_header.html` (marchio senza sottotitolo,
    tendine Esplora e Classifiche, ricerca in testata, interruttore tondo);
    `/atlante` e `/confronto` montavano una testata React con marchio corallo e
    sottotitolo, otto voci piatte, nessuna ricerca e un interruttore quadrato.
    Le voci venivano gia' dalla stessa lista, il disegno no. Adesso la testata
    e' una, la rende Flask, e React tiene solo cio' che la testata non puo'
    sapere: il pulsante di ritorno. La barra in basso del telefono, che ne era
    rimasta, se n'e' andata con le sue etichette vecchie.
    """

    PAGINE = ("/", "/atlante", "/confronto", "/temi", "/regioni", "/province",
              "/provincia/lecce", "/blog",
              "/indicatore/pil-pro-capite/ter-901", "/qualita-della-vita",
              "/divari-regionali", "/catalogo-dati", "/metodologia", "/quiz")

    def setUp(self):
        self.client = app.test_client()

    def test_ogni_pagina_ne_rende_una_e_una_sola(self):
        for path in self.PAGINE:
            with self.subTest(path=path):
                html = self.client.get(path).get_data(as_text=True)
                self.assertEqual(html.count('<header class="hdr">'), 1, path)
                self.assertIn('class="brandword"><b>Divario</b> <span>Italia</span><', html, path)

    def test_la_spa_non_disegna_piu_la_sua(self):
        sorgente = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "main.jsx").read_text(encoding="utf-8")
        self.assertNotIn('className="masthead"', sorgente)

    def test_le_due_rotte_spa_vestono_il_chrome_condiviso(self):
        """`chrome.css` e' scoped sotto `.sitechrome`: senza quella classe sul
        body la testata esce senza nessuno stile, ed e' successo."""
        for path in ("/atlante", "/confronto"):
            with self.subTest(path=path):
                html = self.client.get(path).get_data(as_text=True)
                self.assertIn('<body class="ds sitechrome">', html)
                self.assertIn("css/ds/chrome.css", html)
                self.assertIn("js/ds-chrome.js", html)

    def test_l_atlante_dichiara_percorso_e_lista(self):
        """Era l'unica pagina indicizzabile e in sitemap senza nessun JSON-LD e
        senza percorso."""
        import json

        html = self.client.get("/atlante").get_data(as_text=True)
        tipi = []
        for blocco in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
            documento = json.loads(blocco)
            tipi.append(documento.get("@type"))
        self.assertIn("BreadcrumbList", tipi)
        self.assertIn("CollectionPage", tipi)

if __name__ == "__main__":
    unittest.main()
