"""La ricerca trova regioni, province e ogni indicatore indicizzabile.

Fino al 23/9/2026 `/ricerca?q=Lecce` diceva "Nessun risultato": l'indice
conteneva solo gli indicatori dell'atlante, che e' regionale, e gli articoli.
Non si trovavano le 20 regioni, le 107 province e i 26 indicatori BES misurati
solo per provincia, che pure hanno una pagina indicizzabile.
"""
import unittest

from app import app, indicator_universe, province_profile
from app.taxonomy import DUPLICATE_BES_IDS

ESEMPI = {
    "Lecce": "/provincia/lecce",
    "provincia di lecce": "/provincia/lecce",
    "Bozen": "/provincia/bolzano",
    "reggio nell'emilia": "/provincia/reggio-emilia",
    "forli": "/provincia/forli-cesena",
    "Pesaro e Urbino": "/provincia/pesaro-e-urbino",
    "massa carrara": "/provincia/massa-carrara",
    "Monza": "/provincia/monza-e-della-brianza",
    "l'aquila": "/provincia/l-aquila",
    "Puglia": "/regione/puglia",
    "emilia romagna": "/regione/emilia-romagna",
    "città metropolitana di Milano": "/provincia/milano",
}


class LaRicercaTrovaITerritori(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def test_il_territorio_e_il_primo_risultato(self):
        for domanda, pagina in ESEMPI.items():
            with self.subTest(domanda=domanda):
                dati = self.client.get("/api/search", query_string={"q": domanda}).get_json()
                self.assertTrue(dati["territories"], domanda)
                self.assertEqual(dati["territories"][0]["path"], pagina)
                html = self.client.get("/ricerca", query_string={"q": domanda}).get_data(as_text=True)
                primo = html.index('class="search-result__title"')
                self.assertIn(f'href="{pagina}"', html[primo:primo + 200])

    def test_ogni_provincia_si_trova_col_suo_nome(self):
        with app.app_context():
            for regione in province_profile.by_region().values():
                for provincia in regione:
                    with self.subTest(provincia=provincia["name"]):
                        dati = self.client.get("/api/search", query_string={"q": provincia["name"]}).get_json()
                        self.assertEqual(dati["territories"][0]["path"], provincia["path"])

    def test_ogni_indicatore_indicizzabile_si_trova_col_suo_nome(self):
        """Anche i 26 BES solo provinciali, e anche dai suggerimenti."""
        with app.app_context():
            catalogo = indicator_universe.indexable_catalog()
        for record in catalogo:
            meta = record["meta"]
            if meta.get("raw_id") in DUPLICATE_BES_IDS:
                continue
            with self.subTest(indicatore=meta["id"]):
                dati = self.client.get("/api/search", query_string={"q": meta["name"]}).get_json()
                self.assertIn(meta["canonical_path"], [r["path"] for r in dati["results"]])

    def test_la_forma_dei_risultati_resta_quella_dei_client(self):
        """`indicator-finder.js` e i suggerimenti leggono path, name, theme e
        catalog_family_label: le voci aggiunte li portano tutti."""
        dati = self.client.get("/api/search", query_string={"q": "medici specialisti"}).get_json()
        self.assertTrue(dati["results"])
        for voce in dati["results"]:
            for campo in ("path", "name", "theme", "catalog_family_label"):
                self.assertIn(campo, voce)
        for voce in self.client.get("/api/search", query_string={"q": "lecce"}).get_json()["territories"]:
            for campo in ("path", "name", "kind", "context"):
                self.assertIn(campo, voce)

    def test_una_domanda_corta_non_trova_territori(self):
        self.assertEqual(self.client.get("/api/search", query_string={"q": "l"}).get_json()["territories"], [])


if __name__ == "__main__":
    unittest.main()
