"""L'indicatore in evidenza della home, su ogni coppia che puo' uscire.

La home pesca a ogni visita una coppia (indicatore, livello) dal catalogo
indicizzabile (`app/home_pick.py`). In produzione, se la regia della 1.0 cede,
`app/design` serve il template di prima e scrive l'errore nel log: con una
scelta a caso quel ripiego diventerebbe una home su N, senza che nessuno se ne
accorga. Qui la modalita' stretta (`DIVARIO_V1_STRICT`, da tests/conftest.py)
fa uscire l'eccezione, e ogni coppia del pool deve:

- rispondere 200 dal template della 1.0, col marcatore "Indicatore in evidenza";
- mostrare l'indicatore e il livello chiesti, non un altro;
- non lasciare in pagina un `None`, un `nan` o il segnaposto dei prototipi;
- avere la mappa per tutti e due i livelli, e per le province le prime e le
  ultime dieci;
- aprire sul livello chiesto, e disegnare l'altro (nascosto) quando
  l'indicatore sta nel pool anche li'.
"""

import random
import re
import unittest

from app import app, home_pick, sources
from app.design.common import PLACEHOLDER
from tests.integration.test_v1_pages import FUGHE, visible_text


class OgniCoppiaDelPool(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        with app.app_context():
            cls.pool = home_pick.pool()

    def test_il_pool_ha_entrambi_i_livelli(self):
        self.assertGreater(len(self.pool["regione"]), 100)
        self.assertGreater(len(self.pool["provincia"]), 20)

    def test_ogni_territorio_ha_la_sua_ripartizione(self):
        """Le frasi della home sul Mezzogiorno ("nessuna regione del
        Mezzogiorno arriva...") valgono sull'insieme: se un territorio non ha
        ripartizione la frase si toglie. Qui si controlla che oggi non succeda,
        cosi' la guardia resta una guardia e non una frase che sparisce."""
        from app.design import charts
        with app.app_context():
            areas = charts.area_map()
            fuori = set()
            for level, pairs in self.pool.items():
                for family, raw_id in pairs:
                    scelta = home_pick.pick(sources.indicator_code(family, raw_id), level)
                    fuori |= {o["key"] for o in scelta["level"]["observations"] if areas.get(o["key"]) is None}
        self.assertEqual(fuori, set())

    def test_ogni_coppia_rende_la_home_della_v1(self):
        guasti = []
        for level, pairs in self.pool.items():
            for family, raw_id in pairs:
                code = sources.indicator_code(family, raw_id)
                path = f"/?indicatore={code}&livello={level}"
                risposta = self.client.get(path)
                html = risposta.get_data(as_text=True)
                testo = visible_text(html)
                if risposta.status_code != 200:
                    guasti.append((path, risposta.status_code))
                elif 'data-v1="home"' not in html:
                    guasti.append((path, "non e' il template della 1.0"))
                elif "Indicatore in evidenza" not in testo:
                    guasti.append((path, "manca il marcatore"))
                elif PLACEHOLDER in html:
                    guasti.append((path, "segnaposto in pagina"))
                elif FUGHE.search(testo):
                    guasti.append((path, FUGHE.search(testo).group(0)))
                elif f"/{code}\"" not in html and f"/{code}?livello=" not in html:
                    guasti.append((path, "l'indicatore in evidenza non e' quello chiesto"))
                elif not re.search(rf'<div class="feat__level" id="lv-{level}"[^>]*data-page-root(?![^>]*hidden)', html):
                    guasti.append((path, "il livello in evidenza non e' quello chiesto"))
                elif html.find(f'id="lv-{level}"') > html.find('class="feat__level"') + 40:
                    guasti.append((path, "il livello chiesto non e' il primo pannello"))
                elif level == "regione" and 'class="map" data-map' not in html:
                    guasti.append((path, "regioni senza mappa"))
                elif level == "provincia" and ('class="map map--province"' not in html or "Le prime dieci" not in html):
                    guasti.append((path, "province senza mappa o senza le prime e le ultime dieci"))
        self.assertEqual(guasti, [], guasti[:10])


class PanelLinkComesFromTheCaller(unittest.TestCase):
    """`home.level_panel` non scrive l'indirizzo della home: lo riceve, cosi'
    lo puo' usare un'altra pagina. Il link del selettore della home resta
    quello di prima, `/?indicatore=<codice>&livello=<livello>#dato`."""

    def test_another_page_gets_its_own_link(self):
        from app.design.pages import home
        with app.app_context():
            scelta = home_pick.pick("bes-01SAL001", "provincia")
            panel = home.level_panel(scelta["meta"], scelta["level"], "/atlante?indicatore=bes-01SAL001#mappa")
            self.assertEqual(panel["href"], "/atlante?indicatore=bes-01SAL001&livello=provincia#mappa")
            levels = home.feature(scelta)["levels"]
        self.assertEqual(len(levels), 2)
        for panel in levels:
            self.assertEqual(panel["href"], f"/?indicatore=bes-01SAL001&livello={panel['key']}#dato")

    def test_the_level_goes_before_the_anchor(self):
        from app.design.pages.home import level_href
        self.assertEqual(level_href("/atlante", "regione"), "/atlante?livello=regione")
        self.assertEqual(level_href("/atlante#mappa", "regione"), "/atlante?livello=regione#mappa")
        self.assertEqual(level_href("/?indicatore=ter-901", "regione"), "/?indicatore=ter-901&livello=regione")


class LaSchedaSulSuoLivello(unittest.TestCase):
    """Ogni pannello porta alla scheda aperta sul suo livello. La scheda di un
    indicatore con tutti e due i livelli si apre sulle regioni, e il pannello
    delle province mandava li': chi cercava la sua provincia non la trovava."""

    def test_ogni_pannello_del_pool(self):
        from app.design.pages import home
        with app.app_context():
            for level, pairs in home_pick.pool().items():
                for family, raw_id in pairs:
                    code = sources.indicator_code(family, raw_id)
                    scelta = home_pick.pick(code, level)
                    primo = scelta["available"][0]
                    for panel in home.feature(scelta)["levels"]:
                        with self.subTest(indicatore=code, livello=panel["key"]):
                            base = scelta["meta"]["canonical_path"]
                            atteso = base if panel["key"] == primo else f"{base}?livello={panel['key']}"
                            self.assertEqual(panel["scheda"], atteso)

    def test_titolo_e_bottone_del_pannello_province(self):
        html = app.test_client().get("/?indicatore=bes-01SAL001&livello=provincia").get_data(as_text=True)
        self.assertRegex(html, r'<h3 class="feat__name" id="feat-name"><a href="[^"]*/bes-01SAL001\?livello=provincia"')
        self.assertIn("/bes-01SAL001?livello=provincia\">Tutta la scheda", html)


class LeFrasi(unittest.TestCase):
    """I titoli dei grafici della fascia, su ogni coppia del pool.

    Con il PIL fisso i titoli erano quattro e si potevano leggere a mano. Con
    l'estrazione a caso sono centinaia, e la revisione ne ha trovati di
    sgrammaticati ("una regioni del Mezzogiorno"), di falsi ("tutte le sette
    regioni del Mezzogiorno" col Molise senza dato, "228 centomila anziani"
    per un tasso) e di troppo lunghi."""

    @classmethod
    def setUpClass(cls):
        from app.design.pages import home
        cls.frasi = []
        with app.app_context():
            for level, pairs in home_pick.pool().items():
                for family, raw_id in pairs:
                    code = sources.indicator_code(family, raw_id)
                    # Tutti e due i pannelli: quello estratto e l'altro livello,
                    # che il selettore mostra senza ricaricare.
                    for panel in home.feature(home_pick.pick(code, level))["levels"]:
                        for claim in (panel["lead_claim"], panel["table_claim"]):
                            if claim:
                                cls.frasi.append((code, panel["key"], claim, panel))

    def test_ci_sono_frasi(self):
        self.assertGreater(len(self.frasi), 300)

    def test_nessun_titolo_oltre_i_novanta_caratteri(self):
        lunghi = [(c, l, len(t)) for c, l, t, _ in self.frasi if len(t) > 90]
        self.assertEqual(lunghi, [], lunghi[:5])

    def test_accordo_col_singolare(self):
        rotte = [(c, t) for c, _, t, _ in self.frasi if re.search(r"\buna (regioni|province)\b", t)]
        self.assertEqual(rotte, [], rotte[:5])

    def test_nessuna_etichetta_generica_come_unita(self):
        """Ne' un'etichetta che non e' un'unita', ne' una percentuale scritta per
        esteso ("79,9 valori percentuali"): accanto alla cifra va "%". Lo spazio
        fra cifra e unita' e' insecabile (`common.with_unit`), e `\\s` lo
        prende: con lo spazio semplice la prova non vedeva nessuna frase."""
        rotte = [(c, t) for c, _, t, _ in self.frasi
                 if re.search(r"\d\s(numero|valore medio|Valore medio|indice|rapporto|classi|centomila"
                              r"|percentuale|[Vv]alori percentuali)\b", t)]
        self.assertEqual(rotte, [], rotte[:5])

    def test_il_mezzogiorno_nominato_c_e_tutto(self):
        """Una frase che conta il Mezzogiorno ("le otto regioni", "su 38") lo
        conta intero: con un territorio senza dato la frase non si scrive."""
        from app.design import charts
        from app.design.pages.home import expected_areas
        areas = charts.area_map()
        rotte = []
        for code, level, claim, f in self.frasi:
            if "Mezzogiorno" not in claim:
                continue
            attesi = expected_areas(level)["sud"]
            presenti = {k for k in f["names"] if areas.get(k) == "sud"}
            if attesi - presenti:
                rotte.append((code, level, claim))
        self.assertEqual(rotte, [], rotte[:5])


class LaScelta(unittest.TestCase):
    def test_prima_il_livello_poi_l_indicatore(self):
        """Le coppie regionali sono molte piu' di quelle provinciali: pescando
        fra tutte le province uscirebbero una volta su otto. Scegliendo prima il
        livello, su duecento estrazioni escono entrambi in quote vicine."""
        rng = random.Random(20260924)
        with app.app_context():
            levels = [home_pick.pick(rng=rng)["level"]["key"] for _ in range(200)]
        province = levels.count("provincia")
        self.assertGreater(province, 70)
        self.assertLess(province, 130)

    def test_la_home_cambia_da_una_visita_all_altra(self):
        client = app.test_client()
        titoli = set()
        for _ in range(12):
            html = client.get("/").get_data(as_text=True)
            m = re.search(r'<h3 class="feat__name" id="feat-name"><a href="([^"]+)"', html)
            self.assertIsNotNone(m)
            titoli.add(m.group(1))
        self.assertGreater(len(titoli), 1, "dodici visite, sempre lo stesso indicatore")

    def test_il_parametro_del_selettore_di_prima_vale_ancora(self):
        """`?indicator=901` era il selettore della home fino al 24 settembre
        2026: i link gia' in giro devono aprire lo stesso indicatore."""
        html = app.test_client().get("/?indicator=901").get_data(as_text=True)
        self.assertIn("/ter-901\"", html)

    def test_un_codice_che_non_esiste_ripiega_sul_caso(self):
        risposta = app.test_client().get("/?indicatore=ter-99999999")
        self.assertEqual(risposta.status_code, 200)
        self.assertIn("Indicatore in evidenza", risposta.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
