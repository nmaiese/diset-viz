"""Le decisioni 1 e 2 del piano SEO sui doppioni fra schede BES e territoriali.

1. Le regioni di bes-01SAL001 sono ter-910 cella per cella: canonical verso
   ter-910, fuori dalla sitemap, ma senza `noindex` (canonical e `noindex`
   insieme sono due segnali contrari). La `/province` resta una pagina a se'.
2. `DUPLICATE_BES_IDS` diceva "identical values" di serie che non lo sono:
   10AMB008, 12SER006 e 12SER025 sono schede a se', con un H1 che le
   distingue, e per le due SDG la navigazione mostra la BES, indicizzabile e
   con le stesse cifre, al posto della territoriale `noindex`.
"""
import re
import unittest
from html import unescape

from app import (
    app,
    indicator_texts,
    indicator_universe,
    indicator_view,
    seo_titles,
    sources,
    views,
)
from app.atlas_catalog import (
    get_atlas_catalog,
    get_atlas_indicator,
    get_atlas_theme_profile,
)
from app.blog import SITE_URL
from app.taxonomy import (
    DUPLICATE_BES_IDS,
    REGIONAL_CANONICALS,
    SAME_NAME_BES_IDS,
    SUPERSEDED_TERRITORIAL_IDS,
    TERRITORIAL_NAME_TWINS,
)

BASE = "/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001"
PROVINCE = BASE + "/province"
TER_910 = "/indicatore/speranza-di-vita-alla-nascita/ter-910"


def _cells(indicator_id):
    payload = get_atlas_indicator(indicator_id)
    return {(row["year"], row["region_key"]): row["value"]
            for row in payload["series"] if row["value"] is not None}


def _head(response):
    page = response.get_data(as_text=True)

    def grab(pattern):
        found = re.search(pattern, page, re.DOTALL)
        return unescape(found.group(1).strip()) if found else None
    return {
        "title": grab(r"<title>(.*?)</title>"),
        "description": grab(r'<meta name="description" content="(.*?)"'),
        "canonical": grab(r'<link rel="canonical" href="(.*?)"'),
        "robots": grab(r'<meta name="robots" content="(.*?)"'),
        "x_robots": response.headers.get("X-Robots-Tag") or "",
        "h1": unescape(re.sub(r"<[^>]+>", "", grab(r"<h1[^>]*>(.*?)</h1>") or "")).strip(),
        "md_canonical": grab(r"URL canonica: (\S+)"),
        "content_location": response.headers.get("Content-Location"),
    }


class LeRegioniDellaSperanzaDiVitaHannoIlCanonicalSuTer910(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def test_la_base_porta_il_canonical_su_ter_910_senza_noindex(self):
        response = self.client.get(BASE)
        self.assertEqual(response.status_code, 200)
        head = _head(response)
        self.assertEqual(head["canonical"], f"{SITE_URL}{TER_910}")
        self.assertNotIn("noindex", head["robots"])
        self.assertNotIn("noindex", head["x_robots"])

    def test_la_base_in_markdown_dice_la_stessa_url_canonica(self):
        response = self.client.get(BASE, headers={"Accept": "text/markdown"})
        self.assertEqual(response.status_code, 200)
        head = _head(response)
        self.assertEqual(head["md_canonical"], f"{SITE_URL}{TER_910}")
        # `Content-Location` descrive la rappresentazione servita: resta l'URL
        # della pagina, non quello del canonical.
        self.assertEqual(head["content_location"], f"{SITE_URL}{BASE}")
        self.assertNotIn("noindex", head["x_robots"])

    def test_la_province_resta_canonica_di_se_stessa_e_indicizzata(self):
        for accept in ({}, {"Accept": "text/markdown"}):
            with self.subTest(accept=accept):
                response = self.client.get(PROVINCE, headers=accept)
                self.assertEqual(response.status_code, 200)
                head = _head(response)
                self.assertEqual(head["canonical"] or head["md_canonical"], f"{SITE_URL}{PROVINCE}")
                self.assertNotIn("noindex", head["robots"] or "")
                self.assertNotIn("noindex", head["x_robots"])

    def test_ter_910_resta_senza_province(self):
        self.assertEqual(self.client.get(TER_910).status_code, 200)
        self.assertEqual(self.client.get(TER_910 + "/province").status_code, 404)

    def test_la_sitemap_ha_la_province_e_ter_910_e_non_la_base(self):
        sitemap = self.client.get("/sitemap.xml").get_data(as_text=True)
        locs = set(re.findall(r"<loc>(.*?)</loc>", sitemap))
        self.assertIn(f"{SITE_URL}{PROVINCE}", locs)
        self.assertIn(f"{SITE_URL}{TER_910}", locs)
        self.assertNotIn(f"{SITE_URL}{BASE}", locs)

    def test_llms_full_elenca_la_province_e_non_la_base(self):
        corpus = self.client.get("/llms-full.txt").get_data(as_text=True)
        self.assertIn(f"({SITE_URL}{PROVINCE})", corpus)
        self.assertNotIn(f"({SITE_URL}{BASE})", corpus)
        self.assertNotIn(f"{SITE_URL}{BASE}\n", corpus)

    def test_la_voce_della_province_non_porta_i_download_delle_regioni(self):
        """Il CSV e il JSON di bes-01SAL001 hanno solo le regioni: la voce che
        e' la `/province`, in llms-full e nel catalogo dati, non li offre. La
        scheda regionale li tiene."""
        corpus = self.client.get("/llms-full.txt").get_data(as_text=True)
        self.assertNotIn("bes:01SAL001.csv", corpus)
        self.assertNotIn("bes:01SAL001.json", corpus)
        with app.test_request_context():
            entry = next(e for e in views._listed_indicator_entries() if e["path"] == PROVINCE)
            ter = next(e for e in views._listed_indicator_entries() if e["path"] == TER_910)
        self.assertIsNone(entry["downloads"])
        self.assertTrue(entry["meta"]["downloads"])  # la meta della scheda non si tocca
        self.assertTrue(ter["downloads"])
        for accept in ({}, {"Accept": "text/markdown"}):
            with self.subTest(accept=accept):
                page = self.client.get("/catalogo-dati", headers=accept).get_data(as_text=True)
                self.assertNotIn("bes:01SAL001.csv", page)

    def test_il_catalogo_dati_elenca_la_province_e_non_la_base(self):
        for accept in ({}, {"Accept": "text/markdown"}):
            with self.subTest(accept=accept):
                page = self.client.get("/catalogo-dati", headers=accept).get_data(as_text=True)
                self.assertIn(PROVINCE, page)
                self.assertIn(TER_910, page)
                self.assertEqual(re.findall(re.escape(BASE) + r'(?=["\)\s])', page), [])

    def test_il_canonical_sta_solo_fra_cifre_uguali(self):
        """Il piano vieta il canonical fra pagine con cifre diverse (3.7.3): se
        un'uscita futura separa le due serie, questa diventa rossa."""
        with app.app_context():
            for code, target in REGIONAL_CANONICALS.items():
                with self.subTest(coppia=(code, target)):
                    here = _cells(sources.internal_id(*sources.parse_indicator_code(code)))
                    there = _cells(sources.internal_id(*sources.parse_indicator_code(target)))
                    common = set(here) & set(there)
                    self.assertGreater(len(common), 400)
                    self.assertEqual(set(here) - set(there), set())
                    self.assertEqual([k for k in common if abs(here[k] - there[k]) > 1e-9], [])


class NessunaTestaRipetutaFraLePagineDellIndice(unittest.TestCase):
    """Le pagine che sitemap e llms-full elencano (`level_pages`), piu' le basi
    col canonical altrove (`REGIONAL_CANONICALS`), che non hanno `noindex`,
    hanno ciascuna il suo `<title>` e il suo H1, senza eccezioni: costruiti
    come la pagina, con `seo_titles.page_title` e `views._page_h1`."""

    def test_title_e_h1_unici(self):
        with app.app_context():
            pages = [(page["meta"]["family"], page["meta"]["raw_id"], page["level"]["key"], page["path"])
                     for page in indicator_universe.level_pages()]
            pages += [(*sources.parse_indicator_code(code), "regione", code) for code in REGIONAL_CANONICALS]
            titles, h1s = {}, {}
            for family, raw_id, level_key, path in pages:
                view = indicator_view.build_indicator_view(family, raw_id)
                level = next(lv for lv in view["levels"] if lv["key"] == level_key)
                article = indicator_texts.build_article(view["meta"]["id"], level["key"])
                title = seo_titles.page_title(article, view["meta"], level, site_name="Divario Italia",
                                              source_qualifier=views._source_qualifier(family, raw_id))
                titles.setdefault(title, []).append(path)
                h1s.setdefault(views._page_h1(article, view["meta"], level), []).append(path)
        self.assertGreater(len(titles), 350)
        self.assertEqual({t: p for t, p in titles.items() if len(p) > 1}, {})
        self.assertEqual({h: p for h, p in h1s.items() if len(p) > 1}, {})


class LeListeDeiDoppioniDiconoIlVero(unittest.TestCase):
    def test_gli_insiemi_sono_coerenti(self):
        self.assertLessEqual(DUPLICATE_BES_IDS | SAME_NAME_BES_IDS, set(TERRITORIAL_NAME_TWINS))
        self.assertEqual(DUPLICATE_BES_IDS & SAME_NAME_BES_IDS, set())
        self.assertLessEqual(SUPERSEDED_TERRITORIAL_IDS, set(TERRITORIAL_NAME_TWINS.values()))
        for code in REGIONAL_CANONICALS:
            family, raw_id = sources.parse_indicator_code(code)
            self.assertEqual(family, "bes")
            self.assertIn(raw_id, DUPLICATE_BES_IDS)

    def test_le_serie_col_nome_uguale_hanno_cifre_diverse(self):
        """Una BES in `SAME_NAME_BES_IDS` non e' un doppione: se le cifre
        coincidessero, starebbe in `DUPLICATE_BES_IDS`."""
        with app.app_context():
            for raw_id in sorted(SAME_NAME_BES_IDS):
                with self.subTest(bes=raw_id):
                    bes = _cells(f"bes:{raw_id}")
                    ter = _cells(TERRITORIAL_NAME_TWINS[raw_id])
                    differ = [k for k in set(bes) & set(ter) if abs(bes[k] - ter[k]) > 1e-9]
                    self.assertTrue(differ or set(bes) != set(ter))

    def test_l_h1_delle_bes_col_nome_uguale_si_distingue(self):
        with app.app_context():
            for raw_id in sorted(SAME_NAME_BES_IDS):
                with self.subTest(bes=raw_id):
                    bes = indicator_view.build_indicator_view("bes", raw_id)
                    ter = indicator_view.build_indicator_view("territorial", TERRITORIAL_NAME_TWINS[raw_id])
                    self.assertEqual(bes["meta"]["name"], ter["meta"]["name"])
                    client = app.test_client()
                    h1_bes = _head(client.get(bes["levels"][0]["canonical_path"]))["h1"]
                    h1_ter = _head(client.get(ter["levels"][0]["canonical_path"]))["h1"]
                    self.assertNotEqual(h1_bes, h1_ter)
                    self.assertIn(sources.family_short_label("bes"), h1_bes)
                    for forbidden in ("—", "–", ";", "…"):
                        self.assertNotIn(forbidden, h1_bes)

    def test_il_titolo_delle_bes_col_nome_uguale_si_distingue_anche_senza_cifre(self):
        """Due titoli che differiscono solo nelle cifre non dicono quale serie
        e' quale, e alla prossima uscita possono arrotondare uguali. Il nome
        breve della BES (`indicator_notes.SHORT_NAMES`) li separa nelle parole.
        Vale anche dove la territoriale e' `noindex` (ter-6)."""
        def words(text):
            return re.sub(r"[\d.,%]+", "", text or "").strip()

        client = app.test_client()
        with app.app_context():
            pairs = [(indicator_view.build_indicator_view("bes", raw_id),
                      indicator_view.build_indicator_view("territorial", TERRITORIAL_NAME_TWINS[raw_id]))
                     for raw_id in sorted(SAME_NAME_BES_IDS)]
        for bes, ter in pairs:
            with self.subTest(bes=bes["meta"]["raw_id"]):
                head_bes = _head(client.get(bes["levels"][0]["canonical_path"]))
                head_ter = _head(client.get(ter["levels"][0]["canonical_path"]))
                self.assertNotEqual(words(head_bes["title"]), words(head_ter["title"]))
                self.assertNotEqual(head_bes["description"], head_ter["description"])
                # Il `<title>` dice la famiglia come l'H1 (`seo_titles._same_name_qualifier`),
                # quello della territoriale no.
                famiglia = sources.family_short_label("bes")
                self.assertIn(f"({famiglia})", head_bes["title"])
                self.assertNotIn(famiglia, head_ter["title"])
                self.assertLessEqual(len(head_bes["title"]), seo_titles.TITLE_MAX)
                for forbidden in ("—", "–", ";", "…"):
                    self.assertNotIn(forbidden, head_bes["title"])
                # Il nome breve "Verde urbano per abitante" piu' la coda del
                # livello dava "per abitante per regione".
                self.assertLessEqual(len(re.findall(r"\bper\b", head_bes["title"])), 1, head_bes["title"])


class LaHomeNonLinkaLaBase(unittest.TestCase):
    """La home pesca dal catalogo indicizzabile: le regioni di bes-01SAL001,
    col canonical su ter-910, non le pesca, e dalle sue province il link alle
    regioni va a ter-910, non alla base."""

    def test_il_pool_regionale_non_ha_la_base(self):
        from app import home_pick

        with app.app_context():
            pool = home_pick.pool()
        self.assertNotIn(("bes", "01SAL001"), pool["regione"])
        self.assertIn(("bes", "01SAL001"), pool["provincia"])
        self.assertIn(("territorial", "910"), pool["regione"])

    def test_la_home_chiesta_sulla_speranza_di_vita_bes(self):
        """Chiesta sulle regioni, la home ne pesca un'altra: nessun caso porta
        alla base."""
        for query, drawn in (({"indicatore": "bes-01SAL001"}, True),
                             ({"indicatore": "bes-01SAL001", "livello": "provincia"}, True),
                             ({"indicatore": "bes-01SAL001", "livello": "regione"}, False)):
            with self.subTest(query=query):
                page = app.test_client().get("/", query_string=query).get_data(as_text=True)
                self.assertIsNone(re.search(re.escape(BASE) + r"(?!/province)", page))
                if drawn:
                    self.assertIn(PROVINCE, page)
                    self.assertIn(f'href="{TER_910}"', page)


class LaNavigazioneMostraLaSchedaGiusta(unittest.TestCase):
    """Atlante, temi e ricerca leggono lo stesso catalogo: una serie che non c'e'
    in uno non c'e' negli altri, e ogni conteggio e' quello che si vede."""

    SHOWN = frozenset({"bes:10AMB008", "bes:12SER006", "bes:12SER025", "bes:SDG-310", "bes:SDG-311", "590", "592", "6", "910"})
    HIDDEN = frozenset({"617", "618", "bes:01SAL001", "bes:10AMB007"})

    @classmethod
    def setUpClass(cls):
        with app.app_context():
            cls.catalog = get_atlas_catalog()
        cls.by_id = {str(item["id"]): item for item in cls.catalog["indicators"]}
        cls.client = app.test_client()

    def test_l_atlante(self):
        self.assertLessEqual(self.SHOWN, set(self.by_id))
        self.assertEqual(self.HIDDEN & set(self.by_id), set())

    def test_i_conteggi_dei_temi_sono_le_schede_che_mostrano(self):
        self.assertEqual(sum(theme["indicator_count"] for theme in self.catalog["themes"]),
                         len(self.catalog["indicators"]))
        self.assertEqual(sum(area["indicator_count"] for area in self.catalog["macro_areas"]),
                         len(self.catalog["indicators"]))
        self.assertEqual(sum(family["indicator_count"] for family in self.catalog["source_families"]),
                         len(self.catalog["indicators"]))
        for theme in self.catalog["themes"]:
            with self.subTest(tema=theme["name"]):
                slug = theme["path"].rstrip("/").rsplit("/", 1)[-1]
                with app.app_context():
                    profile = get_atlas_theme_profile(slug)
                self.assertEqual(profile["indicator_count"], len(profile["indicators"]))
                self.assertEqual(profile["indicator_count"], theme["indicator_count"])

    def test_le_pagine_dei_temi(self):
        for indicator_id in sorted(self.SHOWN | self.HIDDEN):
            with app.app_context():
                meta = get_atlas_indicator(indicator_id)["metadata"]
                theme_path = next(t["path"] for t in self.catalog["themes"] if t["name"] == meta["theme"])
                profile = get_atlas_theme_profile(theme_path.rstrip("/").rsplit("/", 1)[-1])
            with self.subTest(indicatore=indicator_id, tema=theme_path):
                listed = {str(item["id"]) for item in profile["indicators"]}
                if indicator_id in self.SHOWN:
                    self.assertIn(indicator_id, listed)
                    page = self.client.get(theme_path).get_data(as_text=True)
                    self.assertIn(f'href="{meta["path"]}"', page)
                else:
                    self.assertNotIn(indicator_id, listed)

    def test_la_ricerca(self):
        for indicator_id in sorted(self.SHOWN | self.HIDDEN):
            with app.app_context():
                meta = get_atlas_indicator(indicator_id)["metadata"]
            with self.subTest(indicatore=indicator_id):
                found = self.client.get("/api/search", query_string={"q": meta["name"]}).get_json()
                paths = [result["path"] for result in found["results"]]
                if indicator_id in self.SHOWN:
                    self.assertIn(meta["path"], paths)
                else:
                    self.assertNotIn(meta["path"], paths)

    def test_la_ricerca_trova_ancora_la_province_della_speranza_di_vita(self):
        found = self.client.get("/api/search", query_string={"q": "speranza di vita alla nascita"}).get_json()
        self.assertIn(PROVINCE, [result["path"] for result in found["results"]])

    def test_la_metodologia_elenca_ogni_serie_del_punteggio(self):
        """bes-01SAL001 sta nel punteggio anche se la navigazione mostra
        ter-910: la lista della metodologia non la perde, e la porta a ter-910.
        ter-590 e' nel punteggio e nell'atlante, con la sua scheda."""
        with app.test_request_context():
            items = views._quality_life_indicators()
        paths = {item["path"] for item in items}
        self.assertIn("/indicatore/emigrazione-ospedaliera-in-altra-regione/ter-590", paths)
        self.assertIn(TER_910, paths)
        self.assertNotIn(BASE, paths)

    def test_nel_punteggio_dice_le_schede_che_il_tema_elenca(self):
        """"Nel punteggio" di un tema conta le schede del tema che il punteggio
        usa, e ogni serie del punteggio ha la sua scheda in un tema, salvo le
        regioni di bes-01SAL001, che sono ter-910 cella per cella. Quando
        ter-590 stava fuori dall'atlante, il tema della salute contava una serie
        del punteggio in meno di quelle che il punteggio usa."""
        from app.quality_life_selection import regional_quality_life_selection

        listed = set(self.by_id)
        with app.app_context():
            selection = regional_quality_life_selection()
        self.assertEqual(set(selection) - listed, {"bes:01SAL001"})
        for theme in self.catalog["themes"]:
            slug = theme["path"].rstrip("/").rsplit("/", 1)[-1]
            with self.subTest(tema=theme["name"]), app.app_context():
                profile = get_atlas_theme_profile(slug)
                ids = {str(item["id"]) for item in profile["indicators"]}
                scored = ids & set(selection)
                self.assertEqual(profile["quality_life_count"], len(scored))
                self.assertEqual(profile["quality_life_count"],
                                 sum(item["quality_life_scored"] for item in profile["indicators"]))
                page = self.client.get(theme["path"]).get_data(as_text=True)
                shown = re.search(r"<small>Nel punteggio</small><strong>(\d+)</strong>", page)
                self.assertIsNotNone(shown)
                self.assertEqual(int(shown.group(1)), len(scored))

    def test_ter_590_sta_nel_quiz(self):
        """Il quiz la prendeva su master e la riprende: bes-12SER025, con altre
        cifre, non ci entra perche' si ferma al 2024."""
        from app import quiz

        with app.app_context():
            territorial = {str(item["id"]) for item in quiz._quiz_indicators()}
            bes = {str(item["id"]) for item in quiz._bes_quiz_indicators()}
        self.assertIn("590", territorial)
        self.assertEqual(territorial & SUPERSEDED_TERRITORIAL_IDS, set())
        self.assertLessEqual({"bes:SDG-310", "bes:SDG-311"}, bes)

    def test_ter_590_resta_canonica_di_se_stessa(self):
        """ter-590 e bes-12SER025 hanno cifre diverse: tutte e due nell'indice,
        nessun canonical dall'una all'altra."""
        with app.app_context():
            paths = {page["path"] for page in indicator_universe.level_pages()}
        for path in ("/indicatore/emigrazione-ospedaliera-in-altra-regione/ter-590",
                     "/indicatore/emigrazione-ospedaliera-in-altra-regione/bes-12SER025"):
            with self.subTest(path=path):
                self.assertIn(path, paths)
                head = _head(self.client.get(path))
                self.assertEqual(head["canonical"], f"{SITE_URL}{path}")


if __name__ == "__main__":
    unittest.main()
