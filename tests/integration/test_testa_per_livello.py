"""La testa della scheda segue il livello che la pagina rende.

Prima della PR che ha scritto queste prove la vista province di una scheda a
due livelli aveva l'H1, il nome del Dataset e le parole chiave della vista
regioni, le linguette portavano a `?livello=regione` (una seconda URL, noindex,
della pagina che il canonico gia' serve) e i link fra i livelli dicevano
"Province" e "La stessa misura per province" su cento schede. Qui si guarda la
catena vera: `views._page_h1`, `seo_titles.page_title`, i template resi.

Le viste province delle schede a due livelli stanno a `<canonico>/province`.
"""
import json
import logging
import os
import re
import unittest
from html import unescape
from unittest import mock

from app import (
    app,
    cache,
    indicator_texts,
    indicator_view,
    seo_titles,
    sources,
    views,
)
from app.bes_data import MIN_PUBLIC_COVERAGE, get_bes_manifest
from app.indicator_notes import strip_markdown
from app.indicator_universe import all_indicator_refs
from app.taxonomy import PROVINCE_TWINS

# Le due coppie regionali che la decisione 2 del piano SEO lascia aperte:
# ter-592 e bes-10AMB008 sono due misure diverse col nome uguale (unita'
# diverse, 200 celle su 200 diverse), ter-590 e bes-12SER025 la stessa misura
# in due uscite. Hanno lo stesso H1 perche' hanno lo stesso nome, e si
# risolvono con `DUPLICATE_BES_IDS`, non con l'H1. L'elenco si svuota con la
# PR di quella decisione.
H1_EXCEPTIONS = (
    frozenset({("ter-592", "regione"), ("bes-10AMB008", "regione")}),
    frozenset({("ter-590", "regione"), ("bes-12SER025", "regione")}),
)


def _pages():
    """(codice, vista, livello, indicizzabile) per ogni livello di ogni scheda.

    Un livello BES e' indicizzabile con la regola di `all_bes_indicators`
    applicata a quel livello (copertura e anno), gli altri se la scheda lo e'.
    """
    manifests = {key: get_bes_manifest(key) for key in ("regione", "provincia")}
    pages = []
    for family, raw_id in all_indicator_refs():
        view = indicator_view.build_indicator_view(family, raw_id)
        if view is None:
            continue
        code = sources.indicator_code(family, raw_id)
        for level in view["levels"]:
            if family == "bes":
                info = manifests[level["key"]].get(raw_id)
                indexable = (bool(info) and info["coverage_latest"] >= MIN_PUBLIC_COVERAGE
                             and info["year_max"] >= 2023)
            else:
                indexable = view["meta"]["indexable"]
            pages.append((code, view, level, indexable))
    return pages


def _path(view, level):
    path = view["meta"]["canonical_path"]
    return path if level["key"] == view["levels"][0]["key"] else f"{path}/province"


def _jsonld(page, kind):
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.DOTALL):
        data = json.loads(block)
        if data.get("@type") == kind:
            return data
    return None


def _head(page):
    """Cio' che un motore legge della testa, per confrontare due rese."""
    def grab(pattern):
        found = re.search(pattern, page, re.DOTALL)
        return unescape(found.group(1).strip()) if found else None
    return {
        "title": grab(r"<title>(.*?)</title>"),
        "robots": grab(r'<meta name="robots" content="(.*?)"'),
        "canonical": grab(r'<link rel="canonical" href="(.*?)"'),
        "h1": unescape(re.sub(r"<[^>]+>", "", grab(r"<h1[^>]*>(.*?)</h1>") or "")).strip(),
        "dataset": _jsonld(page, "Dataset"),
        "breadcrumb": _jsonld(page, "BreadcrumbList"),
    }


class LaTestaSegueIlLivello(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with app.app_context():
            cls.pages = _pages()
            cls.h1 = {}
            cls.articles = {}
            for code, view, level, _ in cls.pages:
                article = indicator_texts.build_article(view["meta"]["id"], level["key"])
                cls.articles[(code, level["key"])] = article
                cls.h1[(code, level["key"])] = views._page_h1(article, view["meta"], level)
        cls.client = app.test_client()

    def test_le_due_viste_della_stessa_misura_hanno_h1_diversi(self):
        two_levels = {code for code, view, _, _ in self.pages if len(view["levels"]) > 1}
        self.assertGreater(len(two_levels), 20)
        for code in sorted(two_levels):
            with self.subTest(scheda=code):
                self.assertNotEqual(self.h1[(code, "regione")], self.h1[(code, "provincia")])

    def test_le_gemelle_hanno_h1_diversi(self):
        for regional, provincial in PROVINCE_TWINS.items():
            with self.subTest(coppia=(regional, provincial)):
                self.assertNotEqual(self.h1[(regional, "regione")], self.h1[(provincial, "provincia")])

    def test_nessun_h1_ripetuto_fra_le_pagine_indicizzabili(self):
        per_h1 = {}
        for code, _, level, indexable in self.pages:
            if indexable:
                per_h1.setdefault(self.h1[(code, level["key"])], set()).add((code, level["key"]))
        self.assertGreater(len(per_h1), 350)
        collisions = [frozenset(who) for who in per_h1.values() if len(who) > 1]
        self.assertEqual(sorted(map(sorted, collisions)), sorted(map(sorted, H1_EXCEPTIONS)))

    def test_l_h1_composto_non_entra_nell_articolo(self):
        """`page_title` usa `article["h1"]` come `<title>` se ci sta intero:
        l'H1 composto delle province li' avrebbe preso il posto delle cifre."""
        for code, view, level, _ in self.pages:
            article = self.articles[(code, level["key"])]
            if level["key"] == "provincia" and not article["h1"]:
                with self.subTest(scheda=code):
                    self.assertEqual(self.h1[(code, "provincia")],
                                     f"{view['meta']['name']} nelle province italiane")
                    self.assertIsNone(article["h1"])

    def test_ogni_titolo_provinciale_dice_per_provincia(self):
        for code, view, level, _ in self.pages:
            if level["key"] != "provincia":
                continue
            article = self.articles[(code, level["key"])]
            if article["seo_title"]:
                continue
            family, raw_id = sources.parse_indicator_code(code)
            titolo = seo_titles.page_title(article, view["meta"], level, site_name="Divario Italia",
                                           source_qualifier=views._source_qualifier(family, raw_id))
            with self.subTest(scheda=code, titolo=titolo):
                self.assertIn(" per provincia", titolo)
                self.assertLessEqual(len(titolo), seo_titles.TITLE_MAX)

    def test_la_frase_risposta_e_la_description_dicono_la_stessa_cosa(self):
        """Sulle province senza pezzo la frase che apre la pagina e' la
        description con i territori linkati, e il Dataset la ripete senza
        Markdown."""
        checked = 0
        for code, view, level, _ in self.pages:
            article = self.articles[(code, level["key"])]
            if level["key"] != "provincia" or article["lead"]:
                continue
            meta = view["meta"]
            lead = indicator_texts.composed_lead(meta, level)
            description = seo_titles.page_description(article, meta, level, composed=lead)
            if seo_titles.extremes(meta, level)[0] is None:
                continue
            checked += 1
            with self.subTest(scheda=code):
                self.assertIn("](/provincia/", lead)
                self.assertEqual(strip_markdown(lead), description)
                self.assertEqual(views._dataset_description(lead, meta), description)
                self.assertLessEqual(len(description), seo_titles.DESCRIPTION_MAX)
                for forbidden in ("—", "–", ";", "…", "media nazionale"):
                    self.assertNotIn(forbidden, description)
        self.assertGreater(checked, 40)

    def test_nessuna_pagina_porta_a_un_livello_in_query(self):
        paths = set()
        for code, view, level, _ in self.pages:
            if len(view["levels"]) > 1 or level["key"] == "provincia" or code in PROVINCE_TWINS:
                paths.add(_path(view, level))
        self.assertGreater(len(paths), 100)
        for path in sorted(paths):
            with self.subTest(pagina=path):
                page = self.client.get(path).get_data(as_text=True)
                self.assertIn('data-v1="indicatore"', page)
                self.assertNotIn("livello=", page)
                self.assertNotIn("livello=",
                                 self.client.get(path, headers={"Accept": "text/markdown"}).get_data(as_text=True))

    def test_la_linguetta_corrente_non_e_un_link(self):
        page = self.client.get("/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001/province")
        seg = re.search(r'<div class="seg" role="group" aria-label="Livello territoriale">(.*?)</div>',
                        page.get_data(as_text=True), re.DOTALL).group(1)
        self.assertIn('<span aria-current="page">Province</span>', seg)
        self.assertIn('<a href="/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001">Regioni</a>', seg)
        self.assertNotIn("aria-current", re.sub(r"<span aria-current[^>]*>[^<]*</span>", "", seg))


class LaVistaProvinciale(unittest.TestCase):
    BASE = "/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001"

    @classmethod
    def setUpClass(cls):
        client = app.test_client()
        cls.province = client.get(cls.BASE + "/province").get_data(as_text=True)
        cls.regioni = client.get(cls.BASE).get_data(as_text=True)

    def test_il_dataset_dice_il_livello(self):
        dataset = _jsonld(self.province, "Dataset")
        self.assertEqual(dataset["name"], "Speranza di vita alla nascita per provincia")
        self.assertIn("province italiane", dataset["keywords"])
        self.assertNotIn("regioni italiane", dataset["keywords"])
        self.assertNotIn("](", dataset["description"])
        self.assertTrue(dataset["temporalCoverage"].endswith("/2024"), dataset["temporalCoverage"])
        regioni = _jsonld(self.regioni, "Dataset")
        self.assertEqual(regioni["name"], "Speranza di vita alla nascita")
        self.assertIn("regioni italiane", regioni["keywords"])

    def test_la_briciola_finisce_in_province_ed_e_uguale_al_breadcrumblist(self):
        crumbs = re.search(r'<nav class="crumbs".*?</nav>', self.province, re.DOTALL).group(0)
        visible = [unescape(re.sub(r"<[^>]+>", "", item)).strip()
                   for item in re.findall(r"<li>(.*?)</li>", crumbs, re.DOTALL)]
        listed = [item["name"] for item in _jsonld(self.province, "BreadcrumbList")["itemListElement"]]
        self.assertEqual(visible, listed)
        self.assertEqual(visible[-2:], ["Speranza di vita alla nascita", "Province"])
        self.assertIn(f'<a href="{self.BASE}">Speranza di vita alla nascita</a>', crumbs)
        regioni = [item["name"] for item in _jsonld(self.regioni, "BreadcrumbList")["itemListElement"]]
        self.assertEqual(regioni[-1], "Speranza di vita alla nascita")

    def test_la_frase_risposta_e_linkata_e_la_definizione_resta(self):
        lead = re.search(r'<p class="page-lead">(.*?)</p>', self.province, re.DOTALL).group(1)
        self.assertIn('<a href="/provincia/lecco">Lecco</a>', lead)
        self.assertIn("anni", lead)
        # La definizione in piano non sta piu' nella frase che apre la pagina,
        # e la pagina la dice lo stesso.
        body = re.sub(r"<script\b.*?</script>", "", self.province, flags=re.DOTALL)
        self.assertIn("Esprime in anni la speranza di vita alla nascita", body)

    def test_i_link_fra_i_livelli_dicono_di_che_cosa(self):
        self.assertIn(f'<a href="{self.BASE}">Speranza di vita alla nascita nelle 20 regioni</a>', self.province)
        self.assertIn(f'<a href="{self.BASE}/province">Speranza di vita nelle 107 province</a>',
                      self.regioni)
        self.assertNotIn("Gli stessi dati per", self.province + self.regioni)


class IlRipiegoHaLaStessaTesta(unittest.TestCase):
    """Se la regia della 1.0 cede, `indicator_page.html` deve dire ai motori le
    stesse cose: title, robots, canonical, H1, Dataset e briciole."""

    PATHS = (
        "/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001",
        "/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001/province",
        "/indicatore/raccolta-differenziata-dei-rifiuti-urbani/bes-10AMB017",
        "/indicatore/affollamento-degli-istituti-di-pena/bes-06POL012P",
        "/indicatore/speranza-di-vita-alla-nascita/ter-910",
    )

    def test_title_robots_canonical_dataset_e_briciole_uguali(self):
        def cede(*_args, **_kwargs):
            raise RuntimeError("la regia della 1.0 cede")

        client = app.test_client()
        v1 = {path: client.get(path).get_data(as_text=True) for path in self.PATHS}
        livello = app.logger.level
        app.logger.setLevel(logging.CRITICAL)
        cache.clear()
        try:
            with mock.patch.dict(os.environ, {"DIVARIO_V1_STRICT": ""}), \
                    mock.patch("app.design.derive", side_effect=cede):
                ripiego = {path: client.get(path).get_data(as_text=True) for path in self.PATHS}
        finally:
            app.logger.setLevel(livello)
            cache.clear()
        for path in self.PATHS:
            with self.subTest(pagina=path):
                self.assertIn('data-v1="indicatore"', v1[path])
                self.assertNotIn('data-v1="', ripiego[path])
                self.assertEqual(_head(ripiego[path]), _head(v1[path]))
                self.assertNotIn("livello=regione", ripiego[path])


class LaDefinizioneInPiano(unittest.TestCase):
    def test_si_mostra_dove_nessun_altro_la_dice(self):
        meta = {"explain": {"plain": "Misura qualcosa."}}
        level = {"explain": {"plain": "Misura qualcosa."}}
        assorbita = {"come_leggere": True}
        # La frase-risposta non la contiene: senza questo la definizione spariva.
        self.assertTrue(views._show_plain_definition(assorbita, meta, level, "Da 3 (A) a 1 (B)."))
        # Il lead composto la contiene gia'.
        self.assertFalse(views._show_plain_definition(assorbita, meta, level, "Misura qualcosa. Dati Istat."))
        # Una sezione "definizione" dell'articolo la dice gia'.
        self.assertFalse(views._show_plain_definition({"come_leggere": False}, meta, level, "Da 3 a 1."))


if __name__ == "__main__":
    unittest.main()
