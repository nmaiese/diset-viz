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
- scrivere ogni percentuale accanto alla cifra come "%", mai "percentuale" o
  "valori percentuali", anche nel JSON che legge il JavaScript delle mappe;
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

from app import app, bes_data, indicator_view, profiles, province_profile, sources
from app.atlas_catalog import get_atlas_indicator
from app.blog import get_posts
from app.data import REGION_GEO_AREA, get_rows
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
# Una percentuale accanto alla cifra si scrive "%" (`numfmt.phrase_unit`): nel
# `<data>` di numfmt e nell'unita' che il JavaScript delle mappe legge dal JSON.
# Le card correlate dicevano "79,9 valori percentuali" e "60,3 percentuale".
PERCENT_IN_WORDS = re.compile(
    r'class="n__u">[\s\u2009\u00a0]*(?:valori percentuali|percentuale)\b'
    r'|"unit": "(?:[Vv]alori percentuali|percentuale)"')
EXPLORE = re.compile(r'<script type="application/json" data-explore-data>(.*?)</script>', re.DOTALL)
# La cella di una sparkline: il contenitore piu' vicino fra questi, aperto
# prima del disegno e chiuso dopo: la minicard (`<a class="minicard">`) della
# scheda e dell'articolo, o la cella `<td class="trendcell">` delle tabelle di
# regione e provincia.
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
            elif PERCENT_IN_WORDS.search(html):
                guasti.append((percorso, PERCENT_IN_WORDS.search(html).group(0)))
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
        self.assertGreater(self.sparks_seen, 0, "nessuna sparkline nelle regioni: la prova non guarda niente")

    def test_ogni_provincia(self):
        with app.app_context():
            chiavi = province_profile.chiavi()
        self.assertEqual(len(chiavi), 107)
        guasti = self._guasti("provincia", [f"/provincia/{k}" for k in chiavi])
        self.assertEqual(guasti, [], guasti[:10])
        self.assertGreater(self.sparks_seen, 0, "nessuna sparkline nelle province: la prova non guarda niente")

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


class LeUnitaPercentuali(unittest.TestCase):
    """Le due vie di un'unita' percentuale: il valore in "%", la variazione e
    la differenza fra due tassi in punti percentuali.

    `PERCENT_IN_WORDS` in `_guasti` guarda che "percentuale" non esca piu'
    accanto a una cifra, ma non si accorgerebbe dell'errore opposto: con
    "punti percentuali" trattato come una percentuale qualunque (contiene
    "percentual"), le variazioni e la differenza fra due tassi uscirebbero in
    "%" senza che niente diventi rosso. Qui si guardano le due schede che le
    portano tutte e due."""

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def _page(self, path):
        response = self.client.get(path, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def test_la_differenza_fra_due_tassi_resta_in_punti(self):
        # "Differenza tra tasso di attivita' maschile e femminile": per la fonte
        # e' in "percentuale", ma il valore e' una distanza in punti.
        html = self._page("/indicatore/x/ter-61")
        explore = json.loads(EXPLORE.search(html).group(1))
        self.assertEqual(explore["unit"], "punti percentuali")
        # La scheda fino alle correlate: tessere, mappa, richiami, classifica,
        # serie. Le correlate sono altri indicatori, e i tassi li' sono in "%".
        own = html[:html.index('class="lanes"')]
        self.assertNotIn("n__u--pct", own)
        self.assertNotRegex(own, r'data-value="[^"]*%"')
        self.assertIn('<span class="n__u">\u2009punti percentuali</span>', own)
        self.assertRegex(own, r'data-value="\d+,\d\spunti percentuali"')
        # La card correlata della sua gemella, "Differenza tra tasso di
        # occupazione", dice lo stesso: prima scriveva "16,3 percentuale".
        twin = next(item for item in indicator_view.build_indicator_view("territorial", "61")["related"]
                    if str(item["id"]) == "57")
        card = minicard(html, twin["path"])
        self.assertIn("\u2009punti percentuali</span>", card)
        self.assertNotIn("%", card)

    def test_il_valore_in_segno_e_la_variazione_in_punti(self):
        html = self._page("/indicatore/aree-terrestri-protette/ter-264")
        explore = json.loads(EXPLORE.search(html).group(1))
        self.assertEqual(explore["unit"], "%")
        # Le card correlate: "55,9%", non "55,9 percentuale".
        cards = re.findall(r'class="minicard">.*?</a>', html, re.DOTALL)
        self.assertTrue(cards)
        self.assertTrue(any('<span class="n__u n__u--pct">%</span>' in c for c in cards), cards)
        # La variazione dall'anno prima e la serie parlano in punti percentuali.
        self.assertRegex(html, r'class="n n--delta"[^>]*>[+-]\d+,\d+<span class="n__u">\u2009punti percentuali</span>')
        self.assertIn("\u00a0punti percentuali", html_lib.unescape(html))

    def test_il_titolo_di_com_e_cambiato_parla_in_punti(self):
        # Il titolo della serie diceva "la media semplice e' scesa dell'8,2%"
        # mentre la prosa della stessa scheda diceva "1,48 punti percentuali in
        # meno": una variazione relativa accanto a un livello in "%". Su ter-61
        # la misura stessa e' in punti, su ter-264 e' una quota. Su ter-163 il
        # livello e' intorno a 0,01 e lo spostamento arrotondato a due decimali
        # fa zero, ma la media e' scesa dell'11,6%: non e' "rimasta la stessa".
        for path in ("/indicatore/x/ter-61", "/indicatore/aree-terrestri-protette/ter-264", "/indicatore/x/ter-163"):
            with self.subTest(path=path):
                html = self._page(path)
                claim = re.search(r'<h3 class="h-sub">(Dal \d{4} al \d{4} la media semplice [^<]*)</h3>', html)
                self.assertIsNotNone(claim, "manca il titolo della serie")
                mean = html_lib.unescape(claim.group(1)).split(", e la distanza")[0]
                self.assertNotIn("%", mean)
                self.assertNotRegex(mean, r"raddoppiat|triplicat")
                self.assertRegex(mean, r"(?:cresciuta|scesa) di \d+,\d+\u00a0punti percentuali$")

    def test_la_riga_della_regione_dice_punti_per_la_differenza_fra_tassi(self):
        # Le righe della pagina regione scrivevano "27,9%" per la differenza fra
        # due tassi: `regione._unit` faceva "%" di ogni percentuale.
        html = self._page("/regione/puglia")
        rows = [row for row in re.findall(r"<tr\b.*?</tr>", html, re.DOTALL)
                if re.search(r'href="[^"]*/ter-(?:57|61)"', row)]
        self.assertTrue(rows, "nessuna riga di ter-57 o ter-61 su /regione/puglia")
        for row in rows:
            self.assertNotIn("n__u--pct", row)
            self.assertIn("punti percentuali<", row)

    def test_la_card_dell_articolo_dice_punti_per_la_differenza_fra_tassi(self):
        # La card della scheda dentro l'articolo leggeva l'unita' della fonte,
        # "percentuale": oggi sarebbe "16,3%", una quota che non e'.
        post = next(p for p in get_posts() if str(p.get("indicator")) in {"57", "61"} and not p.get("draft"))
        html = self._page(f"/blog/{post['slug']}")
        cards = re.findall(r'<a href="[^"]*/ter-(?:57|61)" class="minicard">.*?</a>', html, re.DOTALL)
        self.assertTrue(cards, "nessuna card della scheda nell'articolo")
        for card in cards:
            self.assertIn("\u2009punti percentuali</span>", card)
            self.assertNotIn("%", card)


def iqr_or_none(values):
    """Lo scarto interquartile con `statistics`, None sotto i due valori:
    la stessa regola di `charts.spark_floor`, ricalcolata a parte."""
    values = [v for v in values if v is not None]
    if len(values) < 2:
        return None
    q1, _, q3 = statistics.quantiles(values, n=4, method="inclusive")
    return q3 - q1


def table_row(page, path):
    """La riga della tabella "Tutti gli indicatori" che porta a `path`, dal
    `<th scope="row">` alla chiusura del `<tr>`. Lo stesso indicatore compare
    anche nei riquadri di apertura (dove eccelle, dove si e' mosso): un
    `assertIn` sulla pagina intera non direbbe in quale riga sta il disegno."""
    head = f'<th scope="row" role="rowheader"><a href="{html_lib.escape(path)}">'
    assert page.count(head) == 1, (path, page.count(head))
    start = page.index(head)
    return page[start:page.index("</tr>", start)]


class TablesDrawTheTerritorySeries(unittest.TestCase):
    """Nella tabella "Tutti gli indicatori" di una regione e di una provincia
    la sparkline e' la serie di quel territorio, anno per anno, mai una media,
    col pavimento sullo scarto interquartile dei territori dello stesso
    livello nell'ultimo anno della riga.

    Il disegno atteso si ricalcola da capo dalle righe grezze del dataset
    (`get_rows()` per le regioni, `bes_data.get_bes_rows` per le province),
    non da `_region_series` ne' da `province_profile.indicatori`: se una di
    quelle sbaglia serie, anno o pavimento, qui si vede. Il punto finale e' la
    cifra della colonna Valore, e almeno una riga deve essere di quelle dove il
    pavimento cambia il disegno, altrimenti la prova non distingue niente."""

    REGIONS = ("puglia", "lombardia")
    PROVINCE = "lecce"

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.region_points = {}   # (regione, id) -> {anno: valore}
        cls.region_year = {}     # (id, anno) -> [valori delle regioni]
        for row in get_rows():
            if row["value"] is None:
                continue
            cls.region_year.setdefault((row["id"], row["year"]), []).append(row["value"])
            if row["region_key"] in cls.REGIONS:
                cls.region_points.setdefault((row["region_key"], row["id"]), {})[row["year"]] = row["value"]
        cls.province_points = {}  # id -> {anno: valore} di Lecce
        cls.province_year = {}    # (id, anno) -> [valori delle province]
        for row in bes_data.get_bes_rows("provincia"):
            if row["value"] is None:
                continue
            cls.province_year.setdefault((row["id"], row["year"]), []).append(row["value"])
            if row["territory_key"] == cls.PROVINCE:
                cls.province_points.setdefault(row["id"], {})[row["year"]] = row["value"]

    def _check_row(self, row, points, floor):
        """La riga disegna `points` col pavimento `floor`; True se qui il
        pavimento cambia il disegno. Sotto i due punti, nessun disegno."""
        if len(points) < 2:
            self.assertNotIn('class="spark ', row)
            return False
        drawing = charts.spark(points, "s", floor)
        self.assertIn(drawing, row)
        self.assertEqual(row.count('class="spark '), 1)
        return drawing != charts.spark(points, "s", None)

    def test_regions(self):
        for key in self.REGIONS:
            with app.app_context():
                indicators = profiles.region_profile(key)["all_indicators"]
            html = self.client.get(f"/regione/{key}").get_data(as_text=True)
            self.assertIn("<th scope=\"col\" role=\"columnheader\">Andamento</th>", html)
            seen = sensitive = 0
            for ind in indicators:
                if not (ind.get("name") and ind.get("path")):
                    continue
                with self.subTest(regione=key, indicatore=ind["id"]):
                    years = self.region_points[(key, ind["id"])]
                    points = [{"year": y, "value": years[y]} for y in sorted(years) if y <= ind["year"]]
                    # Il punto finale e' la cifra della colonna Valore.
                    self.assertEqual((points[-1]["year"], points[-1]["value"]), (ind["year"], ind["value"]))
                    row = table_row(html, ind["path"])
                    sensitive += self._check_row(row, points, iqr_or_none(self.region_year[(ind["id"], ind["year"])]))
                    if len(points) > 1:
                        first = points[0]
                        self.assertIn(f'<span class="trend__from">dal {first["year"]} era</span> '
                                      f'<data class="n n--cell" value="{float(first["value"]):.6g}">', row)
                    seen += 1
            self.assertEqual(seen, len([i for i in indicators if i.get("name") and i.get("path")]))
            self.assertGreater(sensitive, 0, f"{key}: nessuna riga dove il pavimento cambia il disegno")

    def test_province(self):
        with app.app_context():
            rows = province_profile.indicatori(self.PROVINCE)
        html = self.client.get(f"/provincia/{self.PROVINCE}").get_data(as_text=True)
        self.assertTrue(rows)
        sensitive = 0
        for ind in rows:
            with self.subTest(indicatore=ind["id"]):
                years = self.province_points[ind["id"]]
                points = [{"year": y, "value": years[y]} for y in sorted(years)]
                self.assertEqual((points[-1]["year"], points[-1]["value"]), (ind["year"], ind["value"]))
                row = table_row(html, ind["path"])
                sensitive += self._check_row(row, points, iqr_or_none(self.province_year[(ind["id"], ind["year"])]))
                if len(points) > 1:
                    self.assertIn(f'<span class="trend__from">dal {points[0]["year"]}</span>', row)
        self.assertGreater(sensitive, 0, "nessuna riga dove il pavimento cambia il disegno")


class RegionSeriesCacheDoesNotGrowWithPages(unittest.TestCase):
    """Le serie delle regioni sono una voce sola per processo, per tutte le
    pagine: una cache che crescesse con le regioni visitate terrebbe venti
    copie dello stesso lavoro. Le province non aggiungono cache: la loro serie
    viene da `province_profile._serie()`, che c'era gia'."""

    def test_one_entry_for_every_region(self):
        from app.design.pages import regione

        client = app.test_client()
        regione._region_series.cache_clear()
        keys = ("puglia", "lombardia", "sicilia", "veneto", "molise")
        for key in keys:
            self.assertEqual(client.get(f"/regione/{key}").status_code, 200)
        info = regione._region_series.cache_info()
        self.assertEqual((info.currsize, info.misses), (1, 1))
        # Una lettura per pagina, non una per riga.
        self.assertEqual(info.hits, len(keys) - 1)


class LaCifraDelTerritorioELaStessaDellaScheda(unittest.TestCase):
    """Una regola dei decimali sola, `numfmt.magnitude_decimals`, anche sulle
    pagine territorio.

    La pagina provincia scriveva i valori coi decimali della fonte: il reddito
    di Milano usciva "34.885,3" e la retribuzione "26.348,5", mentre la scheda
    dell'indicatore, a un clic, scriveva "34.885". Qui ogni cifra della
    pagina territorio (valore, variazione, media delle altre, "dal ... era")
    deve avere i decimali della sua grandezza, e per tre indicatori a testa
    (euro, percentuale, cifra sotto l'uno) la cifra deve essere quella che la
    scheda scrive nella sua tabella e sulla sua mappa.

    La tabella della scheda prende i decimali dalla mediana della colonna
    (`numfmt.column_decimals`): li' dove la grandezza di una riga sta dall'altra
    parte di 1 o di 100 rispetto alla mediana, la tabella della scheda e la
    pagina territorio scrivono la stessa cifra in due modi (Milano, 136 e
    "136,0" sulla brevettazione). I tre indicatori qui non sono di quelli: la
    prova e' che la regola sia la stessa, non che la colonna non esista."""

    DATA = re.compile(r'<data class="n n--(figure|cell|delta)" value="([^"]+)">([^<]*)'
                      r'(?:<span class="n__u[^"]*">([^<]*)</span>)?</data>')
    # (pagina, chiave del territorio), (euro, percentuale, cifra sotto l'uno)
    CASI = (
        (("/provincia/milano", "milano"), ("bes-04BEC001P", "bes-10AMB018P", "bes-04BEC009P")),
        (("/regione/lombardia", "lombardia"), ("ter-902", "ter-643", "ter-242")),
    )

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.pages = {path: cls.client.get(path).get_data(as_text=True) for (path, _), _codes in cls.CASI}

    def test_ogni_cifra_ha_i_decimali_della_sua_grandezza(self):
        from app.design import numfmt

        for path, page in self.pages.items():
            # Le differenze delle dimensioni dalla media 50 sono punteggi, con
            # un decimale fisso: non sono cifre della fonte.
            page = re.sub(r'<td class="val provincia-dims__diff">.*?</td>', "", page, flags=re.DOTALL)
            found = self.DATA.findall(page)
            self.assertGreater(len(found), 100, path)
            for role, value, text, unit in found:
                if text == numfmt.UNCHANGED or (role == "delta" and "posizion" in unit):
                    continue
                shown = len(text.split(",", 1)[1]) if "," in text else 0
                with self.subTest(pagina=path, valore=value, scritto=text):
                    self.assertEqual(shown, numfmt.magnitude_decimals(float(value)))
                    if unit.strip() == "euro":
                        self.assertNotIn(",", text)

    def test_tre_indicatori_scritti_come_sulla_scheda(self):
        for (path, key), codes in self.CASI:
            page = self.pages[path]
            for code in codes:
                href = re.search(rf'<th scope="row" role="rowheader"><a href="([^"]*/{code}(?:\?[^"]*)?)">', page)
                self.assertIsNotNone(href, (path, code))
                href = html_lib.unescape(href.group(1))
                cell = re.search(r'data-label="Valore"[^>]*><data class="n n--cell" value="[^"]+">([^<]*)</data>',
                                 table_row(page, href)).group(1)
                scheda = self.client.get(href, follow_redirects=True).get_data(as_text=True)
                in_table = re.search(rf'<tr data-key="{key}">.*?<td class="val"><data class="n n--cell" '
                                     r'value="[^"]+">([^<]*)</data>', scheda).group(1)
                on_map = html_lib.unescape(re.search(
                    rf'data-key="{key}" data-name="[^"]*" data-value="([^"]*)"', scheda).group(1))
                with self.subTest(pagina=path, indicatore=code):
                    self.assertEqual(cell, in_table)
                    self.assertEqual(re.match(r"-?[\d.,]*\d", on_map).group(0), cell)
            euro = re.search(r'data-label="Valore"[^>]*><data class="n n--cell" value="[^"]+">([^<]*)',
                             table_row(page, html_lib.unescape(re.search(
                                 rf'<a href="([^"]*/{codes[0]}[^"]*)">', page).group(1)))).group(1)
            self.assertNotIn(",", euro, f"{path}: una cifra in euro con i decimali")


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
                        if percorso.startswith("/provincia/"):
                            # Il ripiego scrive le cifre con la regola della
                            # pagina: con i decimali della riga, tolti, avrebbe
                            # stampato il valore col punto decimale di Python.
                            from app.design import numfmt

                            with app.app_context():
                                voci = province_profile.indicatori(percorso.rsplit("/", 1)[1])
                            for voce in voci[:12]:
                                self.assertIn(f'<td class="num">{numfmt.text(voce["value"])} <small>', html)
                                if voce["variazione"] is not None:
                                    self.assertIn(f"dal {voce['year_from']} {numfmt.change_text(voce['variazione'])}"
                                                  "</small>", html)
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
