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
- avere un solo `<h1>`;
- disegnare ogni sparkline (`svg.spark`) nascosta agli screen reader, senza
  stirarla, e con la sua cifra scritta in testo nella stessa cella (un
  `<data>` di `numfmt`, non solo un anno).

La modalita' stretta (`DIVARIO_V1_STRICT`, da tests/conftest.py) fa uscire
l'eccezione invece del ripiego, quindi un guasto qui ha il suo traceback.
"""

import html as html_lib
import json
import re
import statistics
import unittest
from pathlib import Path

from app import app, indicator_view, profiles, province_profile, sources
from app.atlas_catalog import get_atlas_indicator
from app.blog import get_posts
from app.data import REGION_GEO_AREA
from app.design import charts
from app.design.common import PLACEHOLDER
from app.quality_life_config import QUALITY_LIFE_PROFILES
from tests.support import family_and_raw

GOLDEN = Path(__file__).resolve().parent.parent / "fixtures" / "indicator_stats_golden.json"
FUGHE = re.compile(r"\bNone\b|\bnan\b|\bundefined\b")
# "Il profilo di Calabria", "Profilo di Puglia", "a Sud Sardegna": le regioni e
# le due province che non sono una citta' prendono l'articolo. Si guarda tutto
# l'HTML, perche' la description e le caption non sono testo visibile.
SENZA_ARTICOLO = re.compile(
    r"[Pp]rofilo di (?:%s)\b|\b(?:a|di|in|dopo) (?:Sud Sardegna|Verbano-Cusio-Ossola)\b"
    % "|".join(sorted({k.split("-")[0].capitalize() for k in REGION_GEO_AREA})))


SPARK = re.compile(r'<svg\b[^>]*\bclass="spark\b[^"]*"[^>]*>.*?</svg>', re.DOTALL)
# La cella di una sparkline: il contenitore piu' vicino fra questi, aperto
# prima del disegno e chiuso dopo. Oggi e' la minicard (`<a class="minicard">`),
# domani una cella di tabella.
CELLA = re.compile(r"<(a|td|th|li)\b[^>]*>")


def spark_faults(page):
    """Quante sparkline ha la pagina, e che cosa non va in ciascuna."""
    faults = []
    found = 0
    for match in SPARK.finditer(page):
        found += 1
        svg = match.group(0)
        if 'aria-hidden="true"' not in svg:
            faults.append("sparkline senza aria-hidden")
        if "preserveAspectRatio" in svg or re.search(r"#[0-9a-fA-F]{3,8}\b", svg):
            faults.append("sparkline stirata o con un colore cotto")
        before = page[max(0, match.start() - 3000):match.start()]
        opened = list(CELLA.finditer(before))
        if not opened:
            faults.append("sparkline fuori da una cella")
            continue
        tag = opened[-1].group(1)
        close = page.find(f"</{tag}>", match.end())
        cell = before[opened[-1].start():] + page[match.end():close]
        if "<data " not in cell:
            faults.append("sparkline senza una cifra in testo accanto")
    return found, faults


def regional_iqr(indicator_id, year):
    """Lo scarto interquartile delle regioni in un anno, con i quartili per
    interpolazione lineare. Si ricalcola qui con `statistics`, non con
    `charts.spark_floor`: la prova deve accorgersene anche quando e' quella
    funzione a cedere."""
    values = [row["value"] for row in get_atlas_indicator(indicator_id)["series"]
              if row["year"] == year and row["value"] is not None]
    q1, _, q3 = statistics.quantiles(values, n=4, method="inclusive")
    return q3 - q1


def last_year(points):
    """L'anno dell'ultimo punto con un valore: quello che la card scrive."""
    return max(p["year"] for p in points if p.get("value") is not None)


def minicard(page, path):
    """La minicard che porta a `path`, dall'apertura dell'`<a>` alla chiusura."""
    start = page.index(f'<a href="{path}" class="minicard">')
    return page[start:page.index("</a>", start)]


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
        # Le sparkline viste in questo giro: una prova che ne controlla zero
        # non controlla niente.
        self.sparks_seen = 0
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
            elif SENZA_ARTICOLO.search(html_lib.unescape(html)):
                guasti.append((percorso, SENZA_ARTICOLO.search(html_lib.unescape(html)).group(0)))
            else:
                found, faults = spark_faults(html)
                self.sparks_seen += found
                if faults:
                    guasti.append((percorso, faults[0]))
        return guasti

    def test_ogni_scheda_indicatore(self):
        percorsi = []
        for indicator_id in json.loads(GOLDEN.read_text(encoding="utf-8")):
            family, raw_id = family_and_raw(indicator_id)
            percorsi.append(sources.indicator_url(family, raw_id, "x"))
        self.assertEqual(len(percorsi), 634)
        guasti = self._guasti("indicatore", percorsi)
        self.assertEqual(guasti, [], guasti[:10])
        self.assertGreater(self.sparks_seen, 0, "nessuna sparkline nelle schede: la prova non guarda niente")

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
        self.assertGreater(self.sparks_seen, 0, "nessuna sparkline negli articoli: la prova non guarda niente")

    def test_la_qualita_della_vita_con_ogni_profilo(self):
        self.assertEqual(self._guasti("qualita-della-vita", ["/qualita-della-vita"]), [])
        percorsi = [f"/qualita-della-vita/classifica/{livello}"
                    for livello in ("regioni", "province")]
        percorsi += [f"/qualita-della-vita/classifica/{livello}?profilo={profilo}"
                     for livello in ("regioni", "province") for profilo in QUALITY_LIFE_PROFILES]
        guasti = self._guasti("classifica", percorsi)
        self.assertEqual(guasti, [], guasti[:10])


class LaSparklineHaIlPavimentoEDiceDiCheMediaE(unittest.TestCase):
    """Accanto alla sparkline la cifra dice di che media e', e la sparkline
    arriva in pagina col suo pavimento.

    `spark_faults` guarda la forma di ogni sparkline, non il pavimento ne' la
    frase: con il pavimento a None, o con la frase sparita, restava tutto
    verde. Qui il disegno atteso si ricalcola da capo, dalla serie e dallo
    scarto interquartile delle regioni nell'anno dell'ultimo punto, e deve
    stare nella minicard. Il pavimento non cambia il disegno quando la serie
    si muove piu' di lui: almeno una delle sparkline guardate deve essere di
    quelle che cambia, altrimenti la prova non distingue niente."""

    PAGE = "/indicatore/pil-pro-capite/ter-901"
    PHRASE = "media semplice delle regioni con il dato"

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def _check_card(self, html, indicator_id, path, points):
        """La minicard che porta a `path` disegna `points` col pavimento e
        scrive la frase; True se qui il pavimento cambia il disegno."""
        year = last_year(points)
        drawing = charts.spark(points, "s", regional_iqr(indicator_id, year))
        cell = minicard(html, path)
        self.assertIn(drawing, cell)
        self.assertIn(f"nel {year}, {self.PHRASE}", cell)
        return drawing != charts.spark(points, "s", None)

    def test_le_correlate_della_scheda(self):
        view = indicator_view.build_indicator_view("territorial", "901")
        # Il view model non porta il pavimento: lo calcola la rotta per le
        # sole correlate che la pagina mostra. Nel view model lo pagava anche
        # la passata dei 634 di `indicator_universe`, che le correlate non le
        # legge.
        self.assertFalse([v["id"] for v in view["related"] if "spark_floor" in v])
        html = self.client.get(self.PAGE).get_data(as_text=True)
        cards = view["related"][:indicator_view.RELATED_SHOWN]
        self.assertEqual(len(cards), indicator_view.RELATED_SHOWN)
        sensitive = 0
        for card in cards:
            with self.subTest(card=card["id"]):
                sensitive += self._check_card(html, card["id"], card["path"], card["spark"])
        self.assertGreater(sensitive, 0, "nessuna correlata dove il pavimento cambia il disegno")

    def test_la_scheda_negli_articoli(self):
        seen = sensitive = 0
        for post in get_posts():
            payload = get_atlas_indicator(post["indicator"]) if post.get("indicator") else None
            if payload is None:
                continue
            meta = payload["metadata"]
            points = [p for p in meta.get("spark") or [] if p.get("value") is not None]
            if len(points) < 2:
                continue
            html = self.client.get(f"/blog/{post['slug']}").get_data(as_text=True)
            with self.subTest(post=post["slug"]):
                sensitive += self._check_card(html, post["indicator"], meta["path"], points)
            seen += 1
        self.assertGreater(seen, 0, "nessun articolo con la scheda dell'indicatore")
        self.assertGreater(sensitive, 0, "nessun articolo dove il pavimento cambia il disegno")


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
                        if percorso.startswith("/indicatore/"):
                            # Il filtro `sparkline` e' un involucro di
                            # `charts.spark`: il ripiego lo usa ancora.
                            self.assertIn('class="related-card__spark"><svg class="spark spark--m"', html)
                            # E col pavimento, nella taglia m.
                            for card in indicator_view.build_indicator_view(
                                    "territorial", "901")["related"][:indicator_view.RELATED_SHOWN]:
                                year = last_year(card["spark"])
                                self.assertIn(charts.spark(card["spark"], "m",
                                                           regional_iqr(card["id"], year)), html)
        finally:
            app.logger.setLevel(livello)
            cache.clear()


if __name__ == "__main__":
    unittest.main()
