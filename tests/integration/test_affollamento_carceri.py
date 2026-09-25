"""L'affollamento delle carceri: gli zeri che non erano una misura, e un verso solo.

Macerata e Savona valevano 0 dal 2016 al 2024 e stavano in testa alla
classifica, prime sulla mappa e "prime su 107" nella loro pagina provincia. Uno
zero di affollamento non e' un carcere vuoto: la provincia non ha posti
regolamentari da contare. Da `bes_data.NOT_MEASURED` ogni lettore le vede n.d.

E la stessa misura si leggeva in due modi: `contextual` sulle regioni
(06POL012), `lower_better` sulle province (06POL012P). La polarita' BES e'
negativa, e adesso le due schede dicono "Meglio se basso" tutte e due.
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
                path = re.search(rf'<path [^>]*data-key="{key}"[^>]*>', self.html)
                self.assertIsNotNone(path)
                self.assertIn('data-value=""', path.group(0))
                self.assertIn("url(#nd-", path.group(0))
        self.assertIn("n.d., dato non disponibile", self.html)

    def test_nessuno_zero_per_loro_in_pagina(self):
        """Ne' nella striscia del divario, ne' nella classifica, ne' sulla
        mappa: prima c'erano come "Macerata 0" e "0%", in testa."""
        self.assertIn('<tr data-key="arezzo">', self.html)
        for key, name in zip(NOT_MEASURED_KEYS, ("Macerata", "Savona")):
            with self.subTest(provincia=name):
                self.assertNotIn(f'<tr data-key="{key}">', self.html)
                self.assertNotIn(f'data-key="{key}" cx=', self.html)
                self.assertNotIn(f"<title>{name} 0</title>", self.html)
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
        for key, value in (("macerata", "126,8"), ("savona", "63,3")):
            with self.subTest(provincia=key):
                row = self._row(key)
                self.assertIn(f">{value}</data>", row)
                self.assertIn('data-label="Anno">2015</td>', row)
                self.assertNotRegex(row, r'value="0(\.0)?"')

    def test_non_e_prima_su_107_nel_2024(self):
        """Prima del cambio l'affollamento era il primo dei punti di forza di
        Macerata: "0,0% nel 2024, 1a su 107 province"."""
        for key in NOT_MEASURED_KEYS:
            with self.subTest(provincia=key):
                facts = re.findall(r'<li><a href="' + re.escape(PROVINCIAL) + r'">.*?</li>',
                                   self.pages[key], re.DOTALL)
                for fact in facts:
                    self.assertNotIn("nel 2024", fact)


class UnVersoSolo(unittest.TestCase):
    def test_le_due_schede_hanno_lo_stesso_verso(self):
        regional = build_indicator_view("bes", "06POL012")["meta"]["direction"]
        provincial = build_indicator_view("bes", "06POL012P")["meta"]["direction"]
        self.assertEqual(regional, provincial)
        self.assertEqual(regional, "lower_better")

    def test_la_regionale_dice_meglio_se_basso(self):
        html = app.test_client().get(REGIONAL).get_data(as_text=True)
        self.assertIn("Meglio se basso", html)
        self.assertNotIn("Senza un verso", html)


if __name__ == "__main__":
    unittest.main()
