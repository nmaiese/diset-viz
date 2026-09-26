"""Titolo, descrizione e figura d'apertura delle 20 pagine regione: il titolo
non porta posizioni, e ogni posizione scritta porta il nome della sua misura.

Fino al 26 settembre 2026 il `<title>` diceva "Lombardia: 7ª su 20 regioni,
tema per tema" mentre la figura d'apertura della stessa pagina la metteva 2ª
per qualita' della vita: il titolo portava la posizione media sugli indicatori
(`profiles.region_profile`, "avg_rank") senza dirlo, e un crawler (e un
lettore della SERP) lo leggeva come la classifica. Le prove girano sul
generatore comune, su tutte le regioni, non su una pagina scelta.
"""

import html as html_lib
import re
import unittest

from app import app, profiles
from app.data import REGION_ORDER
from app.design.pages import regione as region_design
from app.seo_titles import DESCRIPTION_MAX, TITLE_MAX
from app.views import _region_description, _region_title


def _first(pattern, text):
    m = re.search(pattern, text, re.S)
    return html_lib.unescape(m.group(1)).strip() if m else None


def _plain(fragment):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", fragment or "")).strip()


class TestTitoliRegioni(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        client = app.test_client()
        cls.pages = {}
        index = client.get("/regioni").get_data(as_text=True)
        keys = sorted(set(re.findall(r'href="/regione/([a-z-]+)"', index)))
        cls.keys = keys
        for key in keys:
            response = client.get(f"/regione/{key}")
            cls.pages[key] = (response.status_code, response.get_data(as_text=True))

    def test_ci_sono_tutte_le_regioni(self):
        self.assertEqual(len(self.keys), len(REGION_ORDER))

    def test_il_titolo_non_porta_posizioni_e_nomina_la_regione(self):
        titles = set()
        for key, (status, page) in self.pages.items():
            with self.subTest(regione=key):
                self.assertEqual(status, 200)
                profile = profiles.region_profile(key)
                title = _first(r"<title>(.*?)</title>", page)
                self.assertEqual(title, _region_title(profile))
                self.assertLessEqual(len(title), TITLE_MAX)
                self.assertTrue(title.startswith(f"{profile['region']} in numeri: "), title)
                self.assertNotRegex(title, r"\d+ª")
                titles.add(title)
        self.assertEqual(len(titles), len(self.pages))

    def test_og_title_e_il_titolo(self):
        for key, (_, page) in self.pages.items():
            with self.subTest(regione=key):
                self.assertEqual(_first(r'property="og:title" content="(.*?)"', page),
                                 _first(r"<title>(.*?)</title>", page))

    def test_la_descrizione_nomina_la_qualita_della_vita_con_la_posizione_della_figura(self):
        for key, (_, page) in self.pages.items():
            with self.subTest(regione=key):
                description = _first(r'name="description" content="(.*?)"', page)
                self.assertLessEqual(len(description), DESCRIPTION_MAX)
                quality = region_design._quality(key, profiles.region_profile(key)["region"])
                ranks = re.findall(r"(\d+)ª su (\d+) regioni", description)
                for rank, total in ranks:
                    # Una posizione in descrizione e' sempre quella della
                    # qualita' della vita, ed e' scritta accanto al suo nome.
                    self.assertIn(f"Qualità della vita: {rank}ª su {total} regioni", description)
                    self.assertEqual((int(rank), int(total)), (quality["rank"], quality["total"]))
                    # La stessa posizione sta nella figura d'apertura.
                    self.assertIn(quality["claim"], _plain(html_lib.unescape(page)))

    def test_la_lombardia_e_il_trentino_non_si_contraddicono_piu(self):
        """I casi dell'audit: un titolo che diceva 7ª e 6ª accanto a una
        figura che dice 2ª e 1ª. Ora il titolo non porta posizioni, e quella
        della qualita' della vita sta in descrizione con il suo nome."""
        for key in ("lombardia", "trentino-alto-adige", "calabria"):
            with self.subTest(regione=key):
                quality = region_design._quality(key, profiles.region_profile(key)["region"])
                if quality is None:
                    self.skipTest("classifica della qualita' della vita non disponibile")
                page = self.pages[key][1]
                self.assertNotRegex(_first(r"<title>(.*?)</title>", page), r"\d+ª")
                description = _first(r'name="description" content="(.*?)"', page)
                if f"{quality['rank']}ª" in description:
                    self.assertIn(f"Qualità della vita: {quality['rank']}ª", description)


class TestGeneratoreTitoloRegione(unittest.TestCase):
    """Il generatore su profili sintetici: i sacrifici e il ripiego."""

    def _profile(self, name, rank=7, count=142):
        return {"region": name, "avg_rank": rank, "comparable_count": count,
                "region_total": 20, "all_indicators": list(range(312))}

    def test_la_forma_piena(self):
        self.assertEqual(_region_title(self._profile("Lombardia")),
                         "Lombardia in numeri: 312 indicatori su lavoro e redditi")

    def test_un_nome_lungo_perde_i_temi(self):
        title = _region_title(self._profile("Friuli-Venezia Giulia", 8))
        self.assertEqual(title, "Friuli-Venezia Giulia in numeri: 312 indicatori Istat")
        self.assertLessEqual(len(title), TITLE_MAX)

    def test_senza_posizione_media_il_titolo_non_cambia(self):
        self.assertEqual(_region_title(self._profile("Molise", rank=None)),
                         "Molise in numeri: 312 indicatori su lavoro e redditi")

    def test_la_descrizione_non_aggiunge_niente_a_una_frase_troncata(self):
        profile = self._profile("Abruzzo")
        ritratto = {"descrizione": "x" * 140 + "..."}
        self.assertEqual(_region_description(profile, ritratto, {"rank": 3, "total": 20}),
                         ritratto["descrizione"])

    def test_senza_classifica_resta_la_tesi(self):
        profile = self._profile("Liguria")
        ritratto = {"descrizione": "La Liguria ha la popolazione più anziana d'Italia."}
        self.assertEqual(_region_description(profile, ritratto, None), ritratto["descrizione"])
        self.assertEqual(_region_description(profile, ritratto, {"rank": 8, "total": 20}),
                         "La Liguria ha la popolazione più anziana d'Italia. "
                         "Qualità della vita: 8ª su 20 regioni.")


if __name__ == "__main__":
    unittest.main()
