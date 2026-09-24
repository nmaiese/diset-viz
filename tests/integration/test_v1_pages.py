"""Le pagine della 1.0 su ogni loro istanza, non sul campione dei prototipi.

I prototipi giravano su un esempio per pagina: la scheda del PIL, la Puglia,
Lecce, due articoli, una classifica. Il sito serve 634 schede, 20 regioni, 107
province, ogni post e due classifiche per sei profili, e una pagina che regge
l'esempio puo' cedere sulla serie a un anno solo, sulla provincia con copertura
parziale, sull'articolo di giugno.

Qui ogni istanza deve:
- rispondere 200 dal template della 1.0 (`data-v1="<pagina>"`), non dal
  ripiego che `app/design` usa in produzione quando la regia nuova cede;
- non mostrare mai il segnaposto dei prototipi, ne' un `None` o un `nan`
  finiti nel testo;
- avere un solo `<h1>`.

La modalita' stretta (`DIVARIO_V1_STRICT`, da tests/conftest.py) fa uscire
l'eccezione invece del ripiego, quindi un guasto qui ha il suo traceback.
"""

import html as html_lib
import json
import re
import unittest
from pathlib import Path

from app import app, profiles, province_profile, sources
from app.blog import get_posts
from app.design.common import PLACEHOLDER
from app.quality_life_config import QUALITY_LIFE_PROFILES
from tests.support import family_and_raw

GOLDEN = Path(__file__).resolve().parent.parent / "fixtures" / "indicator_stats_golden.json"
FUGHE = re.compile(r"\bNone\b|\bnan\b|\bundefined\b")


def visible_text(page):
    page = re.sub(r"<(script|style)\b.*?</\1>", " ", page, flags=re.DOTALL)
    page = re.sub(r"<[^>]+>", " ", page)
    return " ".join(html_lib.unescape(page).split())


class LePagineDellaV1SuOgniIstanza(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def _guasti(self, pagina, percorsi):
        guasti = []
        for percorso in percorsi:
            risposta = self.client.get(percorso, follow_redirects=True)
            html = risposta.get_data(as_text=True)
            testo = visible_text(html)
            if risposta.status_code != 200:
                guasti.append((percorso, risposta.status_code))
            elif f'data-v1="{pagina}"' not in html:
                guasti.append((percorso, "non e' il template della 1.0"))
            elif PLACEHOLDER in html:
                guasti.append((percorso, "segnaposto in pagina"))
            elif FUGHE.search(testo):
                guasti.append((percorso, FUGHE.search(testo).group(0)))
            elif len(re.findall(r"<h1\b", html)) != 1:
                guasti.append((percorso, "h1 non unico"))
        return guasti

    def test_ogni_scheda_indicatore(self):
        percorsi = []
        for indicator_id in json.loads(GOLDEN.read_text(encoding="utf-8")):
            family, raw_id = family_and_raw(indicator_id)
            percorsi.append(sources.indicator_url(family, raw_id, "x"))
        self.assertEqual(len(percorsi), 634)
        guasti = self._guasti("indicatore", percorsi)
        self.assertEqual(guasti, [], guasti[:10])

    def test_ogni_scheda_al_livello_provinciale(self):
        percorsi = []
        for indicator_id in json.loads(GOLDEN.read_text(encoding="utf-8")):
            family, raw_id = family_and_raw(indicator_id)
            if family != "bes":
                continue
            base = self.client.get(sources.indicator_url(family, raw_id, "x"), follow_redirects=True)
            if "?livello=provincia" in base.get_data(as_text=True):
                percorsi.append(sources.indicator_url(family, raw_id, "x") + "?livello=provincia")
        self.assertTrue(percorsi, "nessuna scheda ha il livello provinciale: la prova non guarda niente")
        guasti = self._guasti("indicatore", percorsi)
        self.assertEqual(guasti, [], guasti[:10])

    def test_la_home(self):
        self.assertEqual(self._guasti("home", ["/"]), [])

    def test_ogni_regione(self):
        with app.app_context():
            chiavi = sorted(profiles.regions_overview())
        self.assertEqual(len(chiavi), 20)
        guasti = self._guasti("regione", [f"/regione/{k}" for k in chiavi])
        self.assertEqual(guasti, [], guasti[:10])

    def test_ogni_provincia(self):
        with app.app_context():
            chiavi = province_profile.chiavi()
        self.assertEqual(len(chiavi), 107)
        guasti = self._guasti("provincia", [f"/provincia/{k}" for k in chiavi])
        self.assertEqual(guasti, [], guasti[:10])

    def test_ogni_articolo(self):
        post = get_posts()
        self.assertTrue(post)
        guasti = self._guasti("articolo", [f"/blog/{p['slug']}" for p in post])
        self.assertEqual(guasti, [], guasti[:10])

    def test_la_qualita_della_vita_con_ogni_profilo(self):
        self.assertEqual(self._guasti("qualita-della-vita", ["/qualita-della-vita"]), [])
        percorsi = [f"/qualita-della-vita/classifica/{livello}"
                    for livello in ("regioni", "province")]
        percorsi += [f"/qualita-della-vita/classifica/{livello}?profilo={profilo}"
                     for livello in ("regioni", "province") for profilo in QUALITY_LIFE_PROFILES]
        guasti = self._guasti("classifica", percorsi)
        self.assertEqual(guasti, [], guasti[:10])


class IlRipiegoTiene(unittest.TestCase):
    """Se la regia della 1.0 cede, la pagina si serve col template di prima.

    E' la rete sotto le pagine che portano quasi tutti i clic, e nessun'altra
    prova la attraversa: la modalita' stretta dei test fa uscire l'eccezione
    prima. Qui la si toglie, si fa cedere `derive`, e ogni rotta deve
    rispondere 200 dal template di prima, sotto la testata e il piede nuovi."""

    ROTTE = ("/", "/indicatore/pil-pro-capite/ter-901", "/regione/puglia", "/provincia/lecce",
             "/blog/infortuni-lavoro-province", "/qualita-della-vita",
             "/qualita-della-vita/classifica/regioni", "/qualita-della-vita/classifica/province")

    def test_ogni_pagina_regge_senza_la_sua_regia(self):
        import logging
        import os
        from unittest import mock

        from app import cache

        def cede(*_args, **_kwargs):
            raise RuntimeError("la regia della 1.0 cede")

        client = app.test_client()
        livello = app.logger.level
        app.logger.setLevel(logging.CRITICAL)
        cache.clear()
        try:
            with mock.patch.dict(os.environ, {"DIVARIO_V1_STRICT": ""}), \
                    mock.patch("app.design.derive", side_effect=cede):
                for percorso in self.ROTTE:
                    with self.subTest(percorso=percorso):
                        risposta = client.get(percorso)
                        html = risposta.get_data(as_text=True)
                        self.assertEqual(risposta.status_code, 200)
                        self.assertNotIn('data-v1="', html)
                        self.assertIn('<header class="hdr">', html)
                        self.assertIn("css/site.css", html)
        finally:
            app.logger.setLevel(livello)
            cache.clear()


if __name__ == "__main__":
    unittest.main()
