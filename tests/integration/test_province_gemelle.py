"""Le province si raggiungono da ogni scheda che le ha, anche da una gemella.

Il controllo del 24/9 sui link alle province ha trovato tre buchi. Dalla scheda
regionale della speranza di vita (ter-910) non si arrivava mai a quella con le
107 province (bes-01SAL001). Le 25 schede solo provinciali non stavano in
nessuna pagina tema, e la loro briciola rimandava proprio li'. E la scheda al
livello provinciale non aveva la mappa, che quella regionale ha.
"""
import re
import unittest

from app import app, bes_data, indicator_view, sources
from app.taxonomy import PROVINCE_TWINS, REGIONAL_TWINS


def _view(code):
    family, raw_id = sources.parse_indicator_code(code)
    return indicator_view.build_indicator_view(family, raw_id)


class LeGemelle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def test_ogni_coppia_esiste_e_ha_il_livello_che_manca(self):
        with app.app_context():
            for regional, provincial in PROVINCE_TWINS.items():
                with self.subTest(coppia=(regional, provincial)):
                    regionale, provinciale = _view(regional), _view(provincial)
                    self.assertEqual([lv["key"] for lv in regionale["levels"]], ["regione"])
                    self.assertIn("provincia", [lv["key"] for lv in provinciale["levels"]])
                    self.assertEqual(regionale["twin"]["code"], provincial)
                    self.assertTrue(regionale["twin"]["path"].split("?")[0].endswith("/" + provincial))
                    # Il tema puo' differire (ter-590 sta in Salute, bes-12SER025
                    # in Mobilita' e servizi): lo decidono due tassonomie delle
                    # fonti, non la coppia. Il nome invece e' lo stesso.
                    self.assertEqual(regionale["meta"]["name"].split(" (")[0].lower().replace(" 20-64 anni", ""),
                                     provinciale["meta"]["name"].split(" (")[0].lower())

    def test_la_solo_provinciale_torna_alla_sua_regionale(self):
        with app.app_context():
            for provincial, regional in REGIONAL_TWINS.items():
                with self.subTest(scheda=provincial):
                    vista = _view(provincial)
                    if [lv["key"] for lv in vista["levels"]] == ["provincia"]:
                        self.assertEqual(vista["twin"]["code"], regional)
                    else:
                        self.assertIsNone(vista["twin"])

    def test_il_selettore_porta_alla_gemella(self):
        html = self.client.get("/indicatore/speranza-di-vita-alla-nascita/ter-910").get_data(as_text=True)
        seg = re.search(r'<div class="seg" role="group" aria-label="Livello territoriale">(.*?)</div>', html, re.S)
        self.assertIsNotNone(seg)
        self.assertIn('href="/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001?livello=provincia">Province</a>',
                      seg.group(1))
        # La voce su cui si e' non e' un link.
        self.assertIn('<span aria-current="page">Regioni</span>', seg.group(1))
        # Il link alla gemella dice di che cosa parla, col numero dal dato:
        # "La stessa misura per province" era la stessa ancora su ogni gemella.
        self.assertIn('href="/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001?livello=provincia">'
                      "Speranza di vita nelle 107 province</a>", html)
        self.assertNotIn(">La stessa misura per province</a>", html)
        html = self.client.get("/indicatore/affollamento-degli-istituti-di-pena/bes-06POL012P").get_data(as_text=True)
        seg = re.search(r'<div class="seg" role="group" aria-label="Livello territoriale">(.*?)</div>', html, re.S)
        self.assertIn('href="/indicatore/affollamento-degli-istituti-di-pena/bes-06POL012">Regioni</a>', seg.group(1))
        self.assertIn('<span aria-current="page">Province</span>', seg.group(1))
        self.assertLess(seg.group(1).index("Regioni"), seg.group(1).index("Province"))
        self.assertIn('href="/indicatore/affollamento-degli-istituti-di-pena/bes-06POL012">'
                      "Affollamento delle carceri nelle 20 regioni</a>", html)

    def test_il_markdown_dice_la_gemella(self):
        markdown = self.client.get("/indicatore/speranza-di-vita-alla-nascita/ter-910",
                                   headers={"Accept": "text/markdown"}).get_data(as_text=True)
        self.assertIn("- La stessa misura per province, in un'altra scheda: ", markdown)
        self.assertIn("/bes-01SAL001?livello=provincia", markdown)


class LeSchedeProvincialiNeiTemi(unittest.TestCase):
    def test_ogni_scheda_provinciale_sta_nel_tema_della_sua_briciola(self):
        client = app.test_client()
        pagine = {}
        with app.app_context():
            for item in bes_data.all_bes_indicators():
                if "provincia" not in item["levels"]:
                    continue
                vista = indicator_view.build_indicator_view("bes", item["id"])
                if not vista["meta"]["indexable"]:
                    continue
                tema = vista["meta"]["theme_path"]
                if tema not in pagine:
                    pagine[tema] = client.get(tema).get_data(as_text=True)
                html = pagine[tema]
                with self.subTest(scheda=item["id"], tema=tema):
                    sezione = html[html.index('id="province"'):]
                    self.assertIn(f'href="{vista["meta"]["canonical_path"]}', sezione)

    def test_il_markdown_del_tema_porta_le_province(self):
        markdown = app.test_client().get("/tema/istituzioni-e-partecipazione",
                                         headers={"Accept": "text/markdown"}).get_data(as_text=True)
        self.assertIn("## Per provincia", markdown)
        self.assertIn("/bes-06POL012P)", markdown)


class LaMappaDelleProvince(unittest.TestCase):
    def test_la_scheda_sulle_province_ha_la_mappa(self):
        client = app.test_client()
        for path in ("/indicatore/affollamento-degli-istituti-di-pena/bes-06POL012P",
                     "/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001?livello=provincia"):
            with self.subTest(pagina=path):
                html = client.get(path).get_data(as_text=True)
                self.assertIn('data-v1="indicatore"', html)
                self.assertIn('class="map map--province"', html)
                self.assertIn("Mappa cliccabile delle province italiane", html)
                self.assertIn("openpolis", html)
        html = client.get("/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001").get_data(as_text=True)
        self.assertIn("Mappa cliccabile delle regioni italiane", html)
        self.assertNotIn("map--province", html)


if __name__ == "__main__":
    unittest.main()
