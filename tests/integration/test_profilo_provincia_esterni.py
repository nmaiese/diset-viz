"""Il profilo di una provincia porta anche gli indicatori delle altre fonti.

Le famiglie esterne con un livello provinciale (Istat indicatori provinciali, ACI, AGCOM) sono
descrittive: niente punteggio, niente forti e deboli, niente classifiche. Queste
prove tengono ferme tre cose che si rompono in silenzio:

1. **ogni riga dice la sua fonte**, e la dice il registro (`app/sources.py`):
   un indicatore ACI non esce sotto il nome di Istat;
2. **il punteggio non si muove**: i nuovi indicatori non entrano negli elenchi
   su cui si contano movimenti, forti, deboli e posizione media;
3. **un indicatore senza verso non da' un giudizio**: sulla regione non ha
   posizione, sulla provincia la posizione dice "per valore".
"""
import html as htmllib
import json
import re
import unittest

from app import app, province_profile, provincial_families, sources


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


class ProvinciaConGliIndicatoriEsterni(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.html = cls.client.get("/provincia/milano").get_data(as_text=True)
        cls.esterni = province_profile.external_indicators("milano")

    def test_la_pagina_risponde_e_porta_tutti_gli_indicatori_provinciali(self):
        resp = self.client.get("/provincia/milano")
        self.assertEqual(resp.status_code, 200)
        self.assertIn('data-v1="provincia"', self.html)
        attesi = provincial_families.indicators_for_province("milano")
        self.assertGreaterEqual(len(attesi), 11, "la fixture di produzione ha undici serie provinciali")
        self.assertEqual({r["id"] for r in self.esterni}, {r["id"] for r in attesi})
        testo = _corpo(self.html)
        for riga in attesi:
            self.assertIn(riga["name"], testo, f"{riga['id']} non e' nella pagina")
            self.assertIn(f'href="{riga["path"].split("#")[0]}', self.html)

    def test_valore_anno_e_link_sono_quelli_del_loader(self):
        """Il profilo non ricalcola: valore, anno e scheda sono quelli di `indicators_for_province`."""
        loader = {r["id"]: r for r in provincial_families.indicators_for_province("milano")}
        for riga in self.esterni:
            atteso = loader[riga["id"]]
            self.assertEqual(riga["value"], atteso["value"])
            self.assertEqual(riga["year"], atteso["year"])
            self.assertEqual(riga["province_count"], atteso["province_count"])
            self.assertEqual(riga["path"].split("#")[0], atteso["path"])
            self.assertTrue(riga["path"].endswith("#p-milano") or "#" not in riga["path"])

    def test_ogni_riga_ha_la_fonte_del_registro(self):
        attese = {
            "aci": "Automobile Club d'Italia",
            "agcom": "Autorità per le garanzie nelle comunicazioni",
            "ipr": "Istat",
        }
        visti = set()
        for riga in self.esterni:
            prefisso = riga["id"].split(":")[0]
            self.assertEqual(riga["source"], attese[prefisso], riga["id"])
            self.assertEqual(riga["source"], sources.family_institution(riga["family"]))
            self.assertEqual(riga["source_label"], sources.family_label(riga["family"]))
            visti.add(prefisso)
        self.assertEqual(visti, set(attese))
        # E nella pagina: la riga ACI dice ACI e non Istat.
        riga_aci = next(r for r in self.esterni if r["id"].startswith("aci:"))
        pezzo = re.search(
            rf'<a href="{re.escape(riga_aci["path"])}">[^<]*</a>'
            r'<span class="provincia-src">(.*?)</span></th>', self.html, re.DOTALL)
        self.assertIsNotNone(pezzo)
        assert pezzo is not None
        fonte = htmllib.unescape(re.sub(r"<[^>]+>", "", pezzo.group(1)))
        self.assertEqual(fonte, "Fonte: Automobile Club d'Italia")

    def test_la_riga_senza_verso_non_da_un_giudizio(self):
        contestuali = [r for r in self.esterni if r["direction"] == "contextual"]
        self.assertTrue(contestuali)
        for riga in contestuali:
            self.assertTrue(riga["contextual"])
            self.assertIsNone(riga["movement"], "la posizione di un indicatore senza verso non e' un movimento")
        self.assertIn("per valore", _corpo(self.html))
        direzionali = [r for r in self.esterni if r["direction"] != "contextual"]
        self.assertTrue(all(not r["contextual"] for r in direzionali))

    def test_il_punteggio_e_gli_elenchi_di_giudizio_non_cambiano(self):
        bes = province_profile.indicatori("milano")
        self.assertFalse({r["id"] for r in bes} & {r["id"] for r in self.esterni})
        self.assertTrue(all(r["id"].startswith("bes-") or ":" not in r["id"] or r["id"].startswith("bes:")
                            for r in bes))
        su, giu = province_profile.movimenti(bes)
        for riga in su + giu:
            self.assertNotIn(riga["id"], {r["id"] for r in self.esterni})
        ids_profilo = {x["id"] for x in province_profile.profilo("milano")["top_positive"]}
        self.assertFalse(ids_profilo & {r["id"] for r in self.esterni})
        # La descrizione cita ancora solo il BES, con il suo conteggio.
        descrizione = re.search(r'<meta name="description" content="([^"]*)"', self.html).group(1)
        self.assertIn("Istat BES", descrizione)
        self.assertNotIn("ACI", descrizione)

    def test_la_fonte_sotto_la_tabella_e_i_dati_strutturati_vengono_dal_registro(self):
        atteso = sources.institutions_label(["bes", "istat_provinciale", "aci", "agcom"])
        self.assertIn(f"Fonte: {atteso}. Elaborazione Divario Italia.", _corpo(self.html))
        dataset = _dataset(self.html)
        self.assertEqual(dataset["isBasedOn"]["creator"]["name"], "Istat")
        parti = {p["creator"]["name"]: p for p in dataset["hasPart"]}
        self.assertEqual(set(parti), {"Istat", "Automobile Club d'Italia",
                                      "Autorità per le garanzie nelle comunicazioni"})
        for parte in parti.values():
            self.assertTrue(parte["license"].startswith("https://"))
            self.assertTrue(parte["description"], "Search Console vuole una description su ogni Dataset")
        nomi = {v["name"] for v in dataset["variableMeasured"]}
        for riga in self.esterni:
            self.assertIn(riga["name"], nomi)

    def test_ogni_provincia_risponde(self):
        for chiave in ("lecce", "sud-sardegna", "bolzano", "roma"):
            with self.subTest(chiave=chiave):
                resp = self.client.get(f"/provincia/{chiave}")
                if resp.status_code == 404:
                    continue
                self.assertEqual(resp.status_code, 200)
                self.assertIn('data-v1="provincia"', resp.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
