"""L'affollamento delle carceri: gli zeri che non erano una misura.

Macerata e Savona valevano 0 dal 2016 al 2024 e stavano in testa alla
classifica, prime sulla mappa e "prime su 107" nella loro pagina provincia. Uno
zero di affollamento non e' un carcere vuoto: la provincia non ha posti
regolamentari da contare. Da `bes_data.NOT_MEASURED` ogni lettore le vede n.d.

Il verso della regionale (06POL012, `contextual`, contro `lower_better` della
provinciale) resta com'e' finche' la redazione non riscrive la prosa di
`content/indicators/bes__06POL012.md`: quella prosa legge la classifica dal
valore piu' alto, e col verso nuovo quattro sue frasi direbbero il falso.
"""
import json
import re
import unittest

from app import app, bes_data, seo_titles
from app.indicator_view import build_indicator_view

PROVINCIAL = "/indicatore/affollamento-degli-istituti-di-pena/bes-06POL012P"
REGIONAL = "/indicatore/affollamento-degli-istituti-di-pena/bes-06POL012"
NOT_MEASURED_KEYS = ("macerata", "savona")


def _not_measured_years(territory):
    return sorted(year for (_, name, year) in bes_data.NOT_MEASURED if name == territory)


class LaSchedaProvinciale(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.html = cls.client.get(PROVINCIAL).get_data(as_text=True)
        cls.view = build_indicator_view("bes", "06POL012P")
        cls.level = cls.view["levels"][0]

    def test_la_pagina_e_la_1_0(self):
        self.assertIn('data-v1="indicatore"', self.html)

    def test_sulla_mappa_sono_tratteggiate(self):
        for key in NOT_MEASURED_KEYS:
            with self.subTest(provincia=key):
                path = re.search(rf'<(?:path|use) [^>]*data-key="{key}"[^>]*>', self.html)
                self.assertIsNotNone(path)
                self.assertIn('data-value=""', path.group(0))
                self.assertIn("url(#nd-", path.group(0))
        self.assertIn("n.d., dato non disponibile", self.html)

    def test_nessuno_zero_per_loro_in_pagina(self):
        """Ne' nella striscia del divario, ne' nella classifica, ne' sulla
        mappa: prima c'erano come "Macerata 0" e "0%", in testa."""
        # La riga porta anche l'id dell'ancora (`id="p-<key>"`): si cerca
        # l'apertura del tag, non il tag intero.
        self.assertRegex(self.html, r'<tr data-key="arezzo"[ >]')
        for key, name in zip(NOT_MEASURED_KEYS, ("Macerata", "Savona")):
            with self.subTest(provincia=name):
                self.assertNotRegex(self.html, rf'<tr data-key="{key}"[ >]')
                self.assertNotIn(f'data-key="{key}" cx=', self.html)
                self.assertNotIn(f'data-tip="{name} 0"', self.html)
                self.assertNotIn(f'<tspan class="callout__nm">{name}</tspan>', self.html)
                self.assertNotIn(f'<tspan class="strip__nm">{name}</tspan>', self.html)
                self.assertNotIn(f'href="/provincia/{key}"', self.html)

    def test_il_modello_non_le_porta_dal_2016(self):
        observed = {o["key"] for o in self.level["observations"]}
        for key, name in zip(NOT_MEASURED_KEYS, ("Macerata", "Savona")):
            with self.subTest(provincia=key):
                self.assertNotIn(key, observed)
                for year in _not_measured_years(name):
                    self.assertNotIn(key, self.level["matrix"].get(str(year), {}))

    def test_il_2015_resta_vero(self):
        self.assertEqual(self.level["matrix"]["2015"]["macerata"], 126.8)
        self.assertEqual(self.level["matrix"]["2015"]["savona"], 63.3)

    def test_il_conteggio_e_calcolato(self):
        """Le province con un dato nell'ultimo anno sono quelle del CSV meno le
        celle n.d.: il numero in pagina esce da li', non da un 107 scritto."""
        count = len(self.level["observations"])
        self.assertLess(count, self.level["territory_total"])
        self.assertIn(f"Dati Istat per {count} province", self.html)
        self.assertNotIn(f"Dati Istat per {self.level['territory_total']} province", self.html)

    def test_il_minimo_non_e_piu_zero(self):
        self.assertGreater(min(o["value"] for o in self.level["observations"]), 0)

    def test_la_copertura_e_parziale_in_pagina_e_in_markdown(self):
        """Il manifest diceva copertura 1,0 anche con due province n.d.
        nell'ultimo anno, e la frase sulla copertura parziale spariva dalla
        pagina e dal Markdown per gli agenti. N e M vengono dal livello."""
        count = len(self.level["observations"])
        total = self.level["territory_total"]
        self.assertLess(count, total)
        self.assertLess(self.level["coverage"], 1)
        markdown = self.client.get(PROVINCIAL, headers={"Accept": "text/markdown"})
        self.assertTrue(markdown.content_type.startswith("text/markdown"))
        sentence = f"copertura è parziale, {count} province su {total}"
        self.assertIn(sentence, self.html)
        self.assertIn(sentence, markdown.get_data(as_text=True))


class OgniSchedaProvinciale(unittest.TestCase):
    """La copertura di un livello provinciale BES e' quella delle province che
    la scheda mostra, non un numero del manifest che le contraddice."""

    def test_la_copertura_coincide_con_le_province_in_pagina(self):
        checked = 0
        for indicator_id in sorted(bes_data.get_bes_manifest("provincia")):
            view = build_indicator_view("bes", indicator_id)
            self.assertIsNotNone(view, indicator_id)
            for level in view["levels"]:
                if level["key"] != "provincia":
                    continue
                checked += 1
                with self.subTest(indicatore=indicator_id):
                    shown = len(level["observations"]) / level["territory_total"]
                    self.assertAlmostEqual(level["coverage"], shown, places=3)
        self.assertEqual(checked, len(bes_data.get_bes_manifest("provincia")))


class IlTitoloEDescrizione(unittest.TestCase):
    """Fermo al 358% non e' verificato: il titolo resta senza cifre anche
    adesso che il minimo e' un valore vero."""

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def _head(self, path):
        html = self.client.get(path).get_data(as_text=True)
        title = re.search(r"<title>(.*?)</title>", html, re.DOTALL).group(1)
        description = re.search(r'<meta name="description" content="([^"]*)"', html).group(1)
        return title, description

    def test_nessun_titolo_con_lo_zero(self):
        for path in (PROVINCIAL, REGIONAL):
            title, description = self._head(path)
            with self.subTest(pagina=path):
                for text in (title, description):
                    self.assertNotIn("0,00", text)
                    self.assertNotRegex(text, r"\bal 0\b")
                    self.assertNotIn("358", text)

    def test_la_provinciale_resta_senza_estremi(self):
        self.assertIn("bes-06POL012P", seo_titles.UNVERIFIED_EXTREMES)
        title, _ = self._head(PROVINCIAL)
        self.assertTrue(title.startswith("Affollamento delle carceri per provincia"))
        self.assertNotRegex(title, r"\d")

    def test_il_dataset_non_dichiara_estremi(self):
        html = self.client.get(PROVINCIAL).get_data(as_text=True)
        for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL):
            self.assertNotIn("minValue", block)
            self.assertNotIn("maxValue", block)
            json.loads(block)


class LaPaginaProvincia(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        client = app.test_client()
        cls.pages = {key: client.get(f"/provincia/{key}").get_data(as_text=True)
                     for key in NOT_MEASURED_KEYS}

    def _row(self, key):
        html = self.pages[key]
        row = re.search(r'<tr role="row">\s*<th scope="row" role="rowheader"><a href="'
                        + re.escape(PROVINCIAL) + r'">.*?</tr>', html, re.DOTALL)
        self.assertIsNotNone(row, f"{key}: manca la riga dell'affollamento")
        return row.group(0)

    def test_la_riga_dice_il_2015_non_uno_zero_del_2024(self):
        # Il valore macchina, non la cifra scritta: quella segue i decimali
        # della grandezza (126,8 si scrive "127"), e non e' questa la prova.
        for key, value in (("macerata", "126.8"), ("savona", "63.3")):
            with self.subTest(provincia=key):
                row = self._row(key)
                self.assertIn(f'value="{value}"', row)
                self.assertIn('data-label="Anno">2015</td>', row)
                self.assertNotRegex(row, r'value="0(\.0)?"')

    def _around_links(self, key):
        """Il testo attorno a ogni link alla scheda, senza tag: dal link al
        primo `</li>` o `</tr>`, cioe' il fatto o la riga che lo porta."""
        html = self.pages[key]
        pieces = []
        for match in re.finditer(r'<a href="' + re.escape(PROVINCIAL) + '">', html):
            ends = [end for end in (html.find("</li>", match.end()), html.find("</tr>", match.end()))
                    if end != -1]
            fragment = html[match.start():min(ends)]
            pieces.append(" ".join(re.sub(r"<[^>]+>", " ", fragment).split()))
        return pieces

    def test_non_e_prima_su_107_nel_2024(self):
        """Prima del cambio l'affollamento era il primo dei punti di forza di
        Macerata: "0,0% nel 2024, 1a su 107 province". Si guarda ogni punto
        della pagina che porta alla scheda, la riga e i fatti."""
        for key in NOT_MEASURED_KEYS:
            with self.subTest(provincia=key):
                pieces = self._around_links(key)
                self.assertTrue(pieces, f"{key}: nessun link alla scheda")
                for text in pieces:
                    self.assertNotIn("su 107", text)
                    self.assertNotIn("nel 2024", text)

    def test_savona_ha_il_fatto_col_suo_anno(self):
        """Savona resta fra i punti di forza col suo 2015: la prova sopra ha
        qualcosa da guardare anche fuori dalla riga, e la cifra porta l'anno."""
        facts = [text for text in self._around_links("savona") if "nel 2015" in text]
        self.assertTrue(facts)
        self.assertIn("63,3", facts[0])


if __name__ == "__main__":
    unittest.main()
