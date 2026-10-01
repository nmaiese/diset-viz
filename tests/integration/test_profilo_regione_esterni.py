"""Il profilo di una regione porta anche gli indicatori delle altre fonti.

Le famiglie esterne con un livello regionale (Eurostat, ACI, AGCOM) sono
descrittive: niente punteggio, niente forti e deboli, niente classifiche. Queste
prove tengono ferme tre cose che si rompono in silenzio:

1. **ogni riga dice la sua fonte**, e la dice il registro (`app/sources.py`):
   un indicatore ACI non esce sotto il nome di Istat;
2. **il punteggio non si muove**: i nuovi indicatori non entrano negli elenchi
   su cui si contano movimenti, forti, deboli e posizione media;
3. **un indicatore senza verso non da' un giudizio**: non ha posizione, e la
   tabella scrive che non si classifica.
"""
import html as htmllib
import json
import re
import unittest

from app import app, profiles, sources
from app.external_data import get_external_rows


def _corpo(html):
    corpo = re.search(r"<main\b[^>]*>.*</main>", html, re.DOTALL).group(0)
    testo = re.sub(r"<(script|style)\b.*?</\1>", "", corpo, flags=re.DOTALL)
    testo = htmllib.unescape(re.sub(r"<[^>]+>", " ", testo))
    return re.sub(r"\s+", " ", testo).strip()


def _jsonld(html):
    return [json.loads(m) for m in re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)]


def _dataset(html):
    return next(b for b in _jsonld(html) if b.get("@type") == "Dataset")


class RegioneConGliIndicatoriEsterni(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.html = cls.client.get("/regione/lombardia").get_data(as_text=True)
        cls.esterni = profiles.region_external_indicators("lombardia")

    def test_la_pagina_risponde_con_la_sezione_delle_altre_fonti(self):
        resp = self.client.get("/regione/lombardia")
        self.assertEqual(resp.status_code, 200)
        self.assertIn('data-v1="regione"', self.html)
        self.assertIn('id="altre-fonti"', self.html)
        eleggibili = {r["target_indicator_id"] for r in get_external_rows()
                      if r["profile_eligible"] == "true" and r["atlas_eligible"] == "true"
                      and r["territory_level"] == "regione"
                      and r["target_indicator_id"].split(":")[0] in ("eur", "aci", "agcom")}
        self.assertEqual({r["id"] for r in self.esterni}, eleggibili)
        testo = _corpo(self.html)
        for riga in self.esterni:
            self.assertIn(riga["name"], testo)
            self.assertIn(f'href="{riga["path"]}"', self.html)

    def test_solo_le_righe_ammesse_ai_profili(self):
        """`profile_eligible=false` (le serie demografiche, quelle del punteggio) restano fuori."""
        ids = {r["id"] for r in self.esterni}
        self.assertFalse([i for i in ids if i.startswith("dem:")])
        self.assertNotIn("eur:rd_e_gerdreg", ids)

    def test_ogni_riga_ha_la_fonte_del_registro(self):
        attese = {"eur": "Eurostat", "aci": "Automobile Club d'Italia",
                  "agcom": "Autorità per le garanzie nelle comunicazioni"}
        for riga in self.esterni:
            famiglia, _ = sources.split_internal_id(riga["id"])
            self.assertEqual(riga["source"], attese[riga["id"].split(":")[0]])
            self.assertEqual(riga["source"], sources.family_institution(famiglia))
            self.assertEqual(riga["source_label"], sources.family_label(famiglia))
        corpo = _corpo(self.html)
        for etichetta in {r["source_label"] for r in self.esterni}:
            self.assertIn(f"Fonte: {etichetta}", corpo)

    def test_senza_verso_non_si_classifica(self):
        contestuali = [r for r in self.esterni if r["direction"] == "contextual"]
        self.assertTrue(contestuali)
        for riga in contestuali:
            self.assertIsNone(riga["rank"])
            self.assertIsNone(riga["movement"])
        self.assertIn("Senza verso, non si classifica", _corpo(self.html))
        con_verso = [r for r in self.esterni if r["direction"] != "contextual"]
        self.assertTrue(con_verso)
        for riga in con_verso:
            self.assertTrue(1 <= riga["rank"] <= riga["region_count"])

    def test_punteggi_e_conteggi_non_cambiano(self):
        profilo = profiles.region_profile("lombardia")
        ids = {i["id"] for i in profilo["all_indicators"]}
        self.assertFalse(ids & {r["id"] for r in self.esterni})
        for campo in ("top_excels", "top_lags"):
            self.assertFalse({e["id"] for e in profilo[campo]} & {r["id"] for r in self.esterni})
        # H1, titolo e conteggio parlano del profilo di prima.
        n = len(profilo["all_indicators"])
        self.assertIn(f"{n} indicatori Istat", _corpo(self.html))
        titolo = re.search(r"<title>(.*?)</title>", self.html, re.DOTALL).group(1)
        self.assertIn(str(n), titolo)

    def test_dati_strutturati_con_le_fonti_del_registro(self):
        dataset = _dataset(self.html)
        self.assertEqual(dataset["isBasedOn"]["creator"]["name"], "Istat")
        creatori = {p["creator"]["name"] for p in dataset["hasPart"]}
        self.assertEqual(creatori, {"Eurostat", "Automobile Club d'Italia",
                                    "Autorità per le garanzie nelle comunicazioni"})
        for parte in dataset["hasPart"]:
            self.assertTrue(parte["description"], "Search Console vuole una description su ogni Dataset")
            self.assertTrue(parte["license"].startswith("https://"))

    def test_ogni_regione_risponde(self):
        for chiave in ("lombardia", "valle-d-aosta", "sardegna", "molise"):
            with self.subTest(chiave=chiave):
                resp = self.client.get(f"/regione/{chiave}")
                if resp.status_code == 404:
                    continue
                self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
