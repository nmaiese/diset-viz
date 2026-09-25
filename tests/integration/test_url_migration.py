"""Unified /indicatore/ URL scheme and source naming.

Every family now lives under /indicatore/<acronym>-<raw_id>/<slug> and the
pre-migration URLs 301 to it. User-facing labels are institution-first plain
names, never internal jargon on its own.
"""

import re
import unittest
from pathlib import Path

from app import app, sources
from app.atlas_catalog import get_atlas_catalog


class SourceRegistryTest(unittest.TestCase):
    def test_labels_are_plain_and_institution_first(self):
        self.assertEqual(sources.family_label("territorial"), "Istat, indicatori territoriali")
        self.assertEqual(sources.family_label("eurostat"), "Eurostat, statistiche regionali")
        # No family is labelled with a bare internal acronym.
        for family in sources.SOURCES:
            self.assertNotIn(sources.family_label(family).lower(), {"bes", "multiscopo", "multifonte"})

    def test_score_breakdown_labels_come_from_the_registry(self):
        """The visible score breakdown used to carry a second, hand-written set
        of names ("BES", "Multiscopo"), the bare internal acronyms the naming
        rules keep out of user-facing copy."""
        from app.quality_life_bes import build_bes_ranking

        breakdown = build_bes_ranking("regione", "standard")["methodology"]["source_breakdown"]
        self.assertTrue(breakdown)
        for entry in breakdown:
            expected = sources.family_short_label(entry["family"])
            self.assertEqual(entry["label"].lower(), expected.lower())
            self.assertNotIn(entry["label"].lower(), {"bes", "multiscopo"})

    def test_url_round_trip_handles_dashed_ids(self):
        # Keyword-first: the slug leads, the resolving code is the last segment.
        # BES variant ids contain dashes; they must survive the round trip.
        url = sources.indicator_url("bes", "09PAE009-N25", "verde-storico")
        self.assertEqual(url, "/indicatore/verde-storico/bes-09PAE009-N25")
        code = url.split("/")[-1]
        self.assertEqual(sources.parse_indicator_code(code), ("bes", "09PAE009-N25"))

    def test_parse_rejects_unknown_and_legacy(self):
        self.assertIsNone(sources.parse_indicator_code("105-something"))
        self.assertEqual(sources.legacy_territorial_id("105-something"), "105")
        self.assertIsNone(sources.legacy_territorial_id("bes-10AMB014"))


class UnifiedUrlRoutingTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.catalog = get_atlas_catalog()["indicators"]

    def _one(self, family):
        return next((i for i in self.catalog if i["catalog_family"] == family), None)

    def test_all_catalog_paths_are_unified(self):
        for item in self.catalog:
            self.assertTrue(item["path"].startswith("/indicatore/"), item["path"])

    def test_new_urls_resolve(self):
        for family in ("territorial", "bes", "multiscopo"):
            item = self._one(family)
            if item is None:
                continue
            self.assertEqual(self.client.get(item["path"]).status_code, 200, family)

    def test_legacy_territorial_redirects(self):
        ter = self._one("territorial")
        response = self.client.get(f"/indicatore/{ter['id']}-x")
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response.headers["Location"].endswith(ter["path"]))

    def test_legacy_bes_redirects(self):
        bes = self._one("bes")
        raw = bes["id"].split(":", 1)[1]
        response = self.client.get(f"/qualita-della-vita/indicatore/{raw}/qualcosa")
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response.headers["Location"].endswith(bes["path"]))

    def test_legacy_multiscopo_redirects(self):
        mul = self._one("multiscopo")
        if mul is None:
            self.skipTest("no multiscopo data present")
        raw = mul["id"].split(":", 1)[1]
        response = self.client.get(f"/qualita-della-vita/indicatore/multiscopo-{raw}/x")
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response.headers["Location"].endswith(mul["path"]))


class LaVistaProvincialeHaIlSuoUrl(unittest.TestCase):
    """`/indicatore/<slug>/<codice>/province`, e i 301 in un salto solo.

    La vista provinciale di una scheda a due livelli era `?livello=provincia`,
    uno stato `noindex` della base. Adesso e' una pagina, e ogni indirizzo
    vecchio o storto arriva li' (o alla base) con un solo 301 che tiene
    `anno` e `regione` e toglie `livello`.
    """

    BASE = "/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001"
    PROVINCE = BASE + "/province"
    SOLO_PROVINCIALE = "/indicatore/medici-specialisti/bes-12SER002P"
    REGIONALE = "/indicatore/pil-pro-capite/ter-901"

    def setUp(self):
        self.client = app.test_client()

    def _un_salto(self, url, atteso):
        risposta = self.client.get(url)
        self.assertEqual(risposta.status_code, 301, url)
        self.assertEqual(risposta.headers["Location"], atteso, url)
        # Un salto solo: la destinazione risponde 200, senza un altro 301.
        self.assertEqual(self.client.get(atteso).status_code, 200, atteso)

    def test_la_vista_provinciale_risponde_da_se(self):
        risposta = self.client.get(self.PROVINCE)
        self.assertEqual(risposta.status_code, 200)
        html = risposta.get_data(as_text=True)
        self.assertIn(f'<link rel="canonical" href="https://divarioitalia.it{self.PROVINCE}">', html)
        # Il link al confronto fra province porta il livello del confronto,
        # non quello della scheda: si toglie solo quello giusto, e ogni altro
        # `/confronto?` con un livello resta davanti alla guardia.
        from app.design.pages import confronto
        own = 'href="' + confronto.compare_path({"id": "bes:01SAL001"}, "provincia").replace("&", "&amp;") + '"'
        self.assertEqual(html.count(own), 1)
        self.assertNotIn("livello=", html.replace(own, ""))
        markdown = self.client.get(self.PROVINCE, headers={"Accept": "text/markdown"})
        self.assertEqual(markdown.headers["Content-Location"], f"https://divarioitalia.it{self.PROVINCE}")

    def test_livello_provincia_va_alla_vista_tenendo_anno_e_regione(self):
        self._un_salto(self.BASE + "?livello=provincia", self.PROVINCE)
        self._un_salto(self.BASE + "?anno=2020&livello=provincia&regione=lombardia",
                       self.PROVINCE + "?anno=2020&regione=lombardia")

    def test_livello_regione_o_un_livello_che_non_c_e_vanno_alla_base(self):
        self._un_salto(self.BASE + "?livello=regione", self.BASE)
        self._un_salto(self.BASE + "?livello=regione&anno=2019", self.BASE + "?anno=2019")
        self._un_salto(self.REGIONALE + "?livello=provincia", self.REGIONALE)
        self._un_salto(self.REGIONALE + "?livello=", self.REGIONALE)
        self._un_salto(self.SOLO_PROVINCIALE + "?livello=provincia&regione=lecce",
                       self.SOLO_PROVINCIALE + "?regione=lecce")

    def test_livello_sulla_vista_provinciale_si_toglie(self):
        self._un_salto(self.PROVINCE + "?livello=regione&anno=2020", self.PROVINCE + "?anno=2020")

    def test_slug_sbagliato_e_codice_primo_vanno_al_province_canonico(self):
        self._un_salto("/indicatore/slug-sbagliato/bes-01SAL001/province?anno=2020",
                       self.PROVINCE + "?anno=2020")
        self._un_salto("/indicatore/bes-01SAL001/province", self.PROVINCE)
        self._un_salto("/indicatore/bes-01SAL001/province?livello=provincia&regione=lecce",
                       self.PROVINCE + "?regione=lecce")

    def test_province_su_una_solo_provinciale_va_alla_base(self):
        self._un_salto(self.SOLO_PROVINCIALE + "/province", self.SOLO_PROVINCIALE)
        self._un_salto(self.SOLO_PROVINCIALE + "/province?anno=2021", self.SOLO_PROVINCIALE + "?anno=2021")

    def test_province_su_una_regionale_senza_province_e_404(self):
        for url in (self.REGIONALE + "/province",
                    "/indicatore/speranza-di-vita/ter-910/province",
                    "/indicatore/ter-910/province"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_il_terzo_segmento_accetta_solo_province(self):
        for url in (self.BASE + "/regioni", self.BASE + "/provincia", self.BASE + "/x"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_una_vista_fuori_indice_ha_comunque_il_suo_canonical(self):
        path = "/indicatore/posti-km-offerti-dal-tpl/bes-12SER008/province"
        risposta = self.client.get(path)
        self.assertEqual(risposta.status_code, 200)
        self.assertEqual(risposta.headers.get("X-Robots-Tag"), "noindex, follow")
        self.assertIn(f'<link rel="canonical" href="https://divarioitalia.it{path}">',
                      risposta.get_data(as_text=True))

    def test_bes_level_path_porta_alla_vista(self):
        from app.bes_data import bes_level_path

        self.assertEqual(bes_level_path("01SAL001", "provincia"), self.PROVINCE)
        self.assertEqual(bes_level_path("01SAL001", "regione"), self.BASE)
        self.assertEqual(bes_level_path("12SER002P", "provincia"), self.SOLO_PROVINCIALE)


class LaSitemapElencaLeVisteIndicizzabili(unittest.TestCase):
    """17 `/province` in piu' nella sitemap, nessuna URL con una query, e
    l'interruttore che le spegne senza togliere link e 301."""

    LOC = re.compile(r"<loc>([^<]+)</loc>")

    def setUp(self):
        from app import indicator_universe

        self.client = app.test_client()
        self.universe = indicator_universe

    def _locs(self):
        return self.LOC.findall(self.client.get("/sitemap.xml").get_data(as_text=True))

    def _bases_elsewhere(self):
        """Le basi col canonical su un'altra scheda (le regioni di
        bes-01SAL001, verso ter-910), che la sitemap non elenca mai."""
        from app import indicator_view

        return [record for record in self.universe.indexable_catalog()
                if indicator_view.canonical_elsewhere(record["meta"], record["levels"][0]["key"])]

    def test_diciassette_province_e_nessuna_query(self):
        locs = self._locs()
        province = [loc for loc in locs if loc.endswith("/province") and "/indicatore/" in loc]
        self.assertEqual(len(province), 17)
        self.assertFalse([loc for loc in locs if "/indicatore/" in loc and "?" in loc])
        schede = [loc for loc in locs if "/indicatore/" in loc]
        self.assertEqual(len(self._bases_elsewhere()), 1)
        self.assertEqual(len(schede), len(self.universe.indexable_catalog()) - 1 + 17)
        self.assertEqual(len(schede), len(set(schede)))

    def test_l_interruttore_spento(self):
        from unittest import mock

        from app import seo_policy

        base = "/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001"
        with mock.patch.object(seo_policy, "LEVEL_PAGES_INDEXABLE", False):
            locs = self._locs()
            self.assertEqual([loc for loc in locs if "/indicatore/" in loc and loc.endswith("/province")], [])
            elsewhere = self._bases_elsewhere()
            self.assertEqual(len(elsewhere), 1)
            self.assertEqual(len([loc for loc in locs if "/indicatore/" in loc]),
                             len(self.universe.indexable_catalog()) - len(elsewhere))
            risposta = self.client.get(base + "/province")
            self.assertEqual(risposta.status_code, 200)
            self.assertEqual(risposta.headers.get("X-Robots-Tag"), "noindex, follow")
            # La base resta indicizzata e continua a portare alla vista.
            pagina = self.client.get(base)
            self.assertNotEqual(pagina.headers.get("X-Robots-Tag"), "noindex, follow")
            self.assertIn(f'href="{base}/province"', pagina.get_data(as_text=True))
            # I 301 restano, e la ricerca la trova ancora.
            vecchio = self.client.get(base + "?livello=provincia")
            self.assertEqual(vecchio.status_code, 301)
            self.assertEqual(vecchio.headers["Location"], base + "/province")
            self.assertIn(f'href="{base}/province"',
                          self.client.get("/ricerca?q=speranza").get_data(as_text=True))
        self.assertEqual(len([loc for loc in self._locs() if "/indicatore/" in loc and loc.endswith("/province")]), 17)


class EditorialLinksAreCanonicalTest(unittest.TestCase):
    """Articles must link to the canonical indicator page.

    `/?indicator=...` now opens the home page, and `/atlante?indicator=...`
    lands on the atlas and only reaches the indicator through JavaScript. Both
    are broken destinations for a reader without JS and for a crawler."""

    LEGACY = re.compile(r"\((/(?:atlante)?\?indicator=[^)]*)\)")

    def test_no_post_links_to_a_query_string_indicator(self):
        posts = Path(__file__).resolve().parent.parent.parent / "content" / "posts"
        offenders = [
            (md.name, match)
            for md in sorted(posts.glob("*.md"))
            for match in self.LEGACY.findall(md.read_text(encoding="utf-8"))
        ]
        self.assertEqual(offenders, [], f"legacy atlas links in posts: {offenders[:10]}")

    def test_every_indicator_link_in_posts_resolves(self):
        posts = Path(__file__).resolve().parent.parent.parent / "content" / "posts"
        client = app.test_client()
        link_re = re.compile(r"\((/indicatore/[^)\s]+)\)")
        seen = set()
        for md in sorted(posts.glob("*.md")):
            for href in link_re.findall(md.read_text(encoding="utf-8")):
                if href in seen:
                    continue
                seen.add(href)
                self.assertEqual(
                    client.get(href).status_code, 200, f"{md.name} -> {href}"
                )
        self.assertTrue(seen, "no canonical indicator links found in the posts")


if __name__ == "__main__":
    unittest.main()
