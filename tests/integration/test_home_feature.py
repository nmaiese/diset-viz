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
- avere la mappa solo per le regioni, e per le province le prime e le ultime
  dieci al suo posto.
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
                elif f"/{code}\"" not in html:
                    guasti.append((path, "l'indicatore in evidenza non e' quello chiesto"))
                elif ("per regione." if level == "regione" else "per provincia.") not in testo:
                    guasti.append((path, "il livello in evidenza non e' quello chiesto"))
                elif level == "regione" and 'class="map"' not in html:
                    guasti.append((path, "regioni senza mappa"))
                elif level == "provincia" and ("module__body--pair" not in html or 'class="map"' in html):
                    guasti.append((path, "province senza le prime e le ultime dieci"))
        self.assertEqual(guasti, [], guasti[:10])


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
            m = re.search(r'<p class="h-title"><a href="([^"]+)"', html)
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
