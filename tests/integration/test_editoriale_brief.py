"""Il dossier di una scheda sui due casi veri: ter-12 e bes-06POL012P.

ter-12 (disoccupazione) ha i fratelli di genere 175 e 176 e tutte le venti
regioni nelle tre ripartizioni. bes-06POL012P (affollamento delle carceri) e'
solo provinciale, ha un solo estremo non verificato, Fermo, e due province
dove la fonte non misura: tolte quelle, il minimo rimasto e' un valore vero.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.editoriale import brief

ROOT = Path(__file__).resolve().parent.parent.parent


class Resolve(unittest.TestCase):
    def test_le_quattro_forme(self):
        self.assertEqual(brief.resolve("ter-12"), ("territorial", "12"))
        self.assertEqual(brief.resolve("12"), ("territorial", "12"))
        self.assertEqual(brief.resolve("bes-06POL012P"), ("bes", "06POL012P"))
        self.assertEqual(brief.resolve("bes:06POL012P"), ("bes", "06POL012P"))

    def test_codice_sconosciuto_o_di_un_altra_famiglia(self):
        with self.assertRaises(LookupError):
            brief.resolve("ter-99999999")
        with self.assertRaises(LookupError):
            brief.resolve("ims-12")


class Ter12(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dossier = brief.build("ter-12")
        cls.level = cls.dossier["livelli"][0]

    def test_identita_senza_giudizi(self):
        identity = self.dossier["identita"]
        self.assertEqual(identity["codice"], "ter-12")
        self.assertEqual(identity["unita"]["variazione"], "punti percentuali")
        self.assertEqual(identity["verso"]["classifica_del_sito"], "dal valore piu' basso")
        text = json.dumps(self.dossier, ensure_ascii=False).lower()
        for word in ("migliore", "peggiore", "lower_better", "higher_better"):
            self.assertFalse(word in text, f"giudizio di polarita' nel dossier: {word}")

    def test_fratelli_di_genere(self):
        dimensions = self.dossier["dimensioni"]
        self.assertEqual(dimensions["dimensione_di_questa_scheda"], "totale")
        self.assertEqual(
            [(s["codice"], s["dimensione"]) for s in dimensions["fratelli"]],
            [("ter-175", "maschi"), ("ter-176", "femmine")],
        )
        gap = dimensions["confronto_per_territorio"]
        self.assertEqual(gap["distanza"], "femmine meno maschi")
        self.assertEqual(gap["territori"]["valore"], 20)
        first = gap["valori"][0]
        self.assertAlmostEqual(
            first["distanza"]["valore"], first["femmine"]["valore"] - first["maschi"]["valore"], places=5
        )

    def test_tre_ripartizioni_che_coprono_le_venti_regioni(self):
        snapshot = self.level["fotografia"]
        areas = snapshot["ripartizioni"]["valori"]
        self.assertEqual([a["ripartizione"] for a in areas], ["Nord", "Centro", "Mezzogiorno"])
        self.assertEqual(sum(a["territori"]["valore"] for a in areas), 20)
        self.assertEqual(len(snapshot["valori"]), 20)

    def test_media_semplice_mai_nazionale_e_niente_valore_italia_inventato(self):
        snapshot = self.level["fotografia"]
        self.assertIn("non la media nazionale", snapshot["media_semplice_territori"]["etichetta"])
        self.assertIsNone(snapshot["valore_italia"]["valore"])

    def test_percentuale_in_punti_e_niente_variazione_relativa(self):
        long_run = self.level["serie"]["variazione_lungo_periodo"]
        self.assertIsNone(long_run["relativa"])
        self.assertIn("punti percentuali", long_run["assoluta"]["testo"])

    def test_variazione_di_ogni_regione(self):
        changes = self.level["serie"]["variazione_per_territorio"]
        self.assertEqual(changes["territori"]["valore"], 20)
        self.assertEqual(len(changes["valori"]), 20)
        self.assertEqual(changes["da"], 2018)
        self.assertEqual(changes["a"], 2025)
        # Un territorio che non sta fra i tre cali, con le tre cifre gia' scritte.
        cali = {m["territorio"] for m in self.level["serie"]["territori_piu_mossi"]["cali"]}
        molise = next(r for r in changes["valori"] if r["territorio"] == "Molise")
        self.assertNotIn("Molise", cali)
        self.assertIn("punti percentuali", molise["variazione"]["testo"])
        self.assertAlmostEqual(
            molise["variazione"]["valore"], molise["dopo"]["valore"] - molise["prima"]["valore"], places=5
        )

    def test_contesto_economico(self):
        context = self.dossier["contesto_economico"]
        self.assertEqual([i["codice"] for i in context["indicatori"]], list(brief.CONTEXT_CODES))
        self.assertEqual(len(context["territori"]), 6)
        self.assertEqual(set(context["territori"][0]["contesto"]), set(brief.CONTEXT_CODES))
        for correlation in context["correlazioni_di_rango"]:
            self.assertEqual(correlation["territori"]["valore"], 20)
            self.assertLessEqual(abs(correlation["rho_spearman"]["valore"]), 1)

    def test_ogni_numero_ha_valore_e_testo(self):
        def walk(node):
            if isinstance(node, dict):
                if "testo" in node and "valore" in node:
                    self.assertIsInstance(node["testo"], str)
                    return
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)
            elif isinstance(node, float):
                self.fail(f"cifra nuda nel dossier: {node}")

        walk(self.dossier)


class Carceri(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dossier = brief.build("bes-06POL012P")
        cls.level = cls.dossier["livelli"][0]

    def test_livello_provinciale_e_gemello_regionale(self):
        self.assertEqual(self.level["livello"], "provincia")
        twin = self.dossier["dimensioni"]["gemello_di_livello"]
        self.assertEqual(twin["livello"], "regione")
        self.assertEqual(twin["codice"], "bes-06POL012")

    def test_fermo_estremo_non_verificato(self):
        extremes = self.dossier["avvisi"]["estremi_non_verificati"]
        self.assertEqual(len(extremes), 1)
        self.assertEqual(extremes[0]["livello"], "provincia")
        self.assertEqual(extremes[0]["territorio"], "Fermo")
        self.assertEqual(extremes[0]["anno"], 2024)
        self.assertEqual(extremes[0]["valore"]["valore"], 358.1)
        snapshot = self.level["fotografia"]
        top = snapshot["piu_alti"][0]
        self.assertEqual(top["territorio"], "Fermo")
        self.assertTrue(top[brief.EXTREME_FLAG])
        # Le cifre derivate dagli estremi portano il segno anche loro: l'intervallo
        # poggia sul capo non verificato, qualunque sia l'altro capo.
        self.assertTrue(snapshot["rapporto_fra_estremi"][brief.EXTREME_FLAG])
        self.assertTrue(snapshot["distanza_fra_estremi"][brief.EXTREME_FLAG])
        self.assertTrue(self.dossier["contesto_economico"]["territori"][0][brief.EXTREME_FLAG])
        last_year = self.level["serie"]["media_semplice_per_anno"][-1]
        self.assertTrue(last_year["distanza_fra_estremi"][brief.EXTREME_FLAG])

    def test_il_minimo_e_arezzo_e_un_valore_vero(self):
        # Gli zeri di Macerata e Savona erano buchi di fonte, non misure: tolti
        # quelli, il minimo rimasto e' Arezzo e non porta nessun segno.
        snapshot = self.level["fotografia"]
        bottom = snapshot["valori"][-1]
        self.assertEqual(bottom["territorio"], "Arezzo")
        self.assertNotIn(brief.EXTREME_FLAG, bottom)
        self.assertEqual([r["territorio"] for r in snapshot["valori"] if brief.EXTREME_FLAG in r], ["Fermo"])
        for row in snapshot["piu_bassi"]:
            self.assertNotIn(brief.EXTREME_FLAG, row)
        for area in snapshot["ripartizioni"]["valori"]:
            self.assertNotIn(brief.EXTREME_FLAG, area["piu_basso"])
        extremes = self.dossier["avvisi"]["estremi_non_verificati"]
        self.assertNotIn("Arezzo", json.dumps(extremes, ensure_ascii=False))
        contesto = {t["territorio"]: brief.EXTREME_FLAG in t for t in self.dossier["contesto_economico"]["territori"]}
        self.assertEqual(contesto, {"Fermo": True, "Brescia": False, "Como": False,
                                    "Sud Sardegna": False, "Nuoro": False, "Arezzo": False})

    def test_variazione_di_ogni_provincia(self):
        changes = self.level["serie"]["variazione_per_territorio"]
        self.assertEqual(changes["territori"]["valore"], 104)
        self.assertEqual(len(changes["valori"]), 104)
        self.assertEqual(changes["da"], 2015)
        self.assertEqual(changes["a"], 2024)
        # Una provincia che non sta fra i tre aumenti e i tre cali.
        mossi = self.level["serie"]["territori_piu_mossi"]
        in_top = {m["territorio"] for m in mossi["aumenti"] + mossi["cali"]}
        provincia = next(r for r in changes["valori"] if r["territorio"] not in in_top)
        self.assertIn("punti percentuali", provincia["variazione"]["testo"])
        self.assertAlmostEqual(
            provincia["variazione"]["valore"], provincia["dopo"]["valore"] - provincia["prima"]["valore"], places=5
        )

    def test_ter12_non_porta_il_segno(self):
        ter12 = brief.dumps(brief.build("ter-12"))
        self.assertNotIn(brief.EXTREME_FLAG, ter12)

    def test_territori_non_misurati_e_anni_parziali(self):
        warnings = self.dossier["avvisi"]
        not_measured = {w["territorio"] for w in warnings["territori_non_misurati"]
                        if "NOT_MEASURED" in w["motivo"]}
        self.assertEqual(not_measured, {"Macerata", "Savona"})
        self.assertIn(2017, [w["anno"] for w in warnings["anni_copertura_parziale"]])

    def test_soglia_e_ripartizioni_dalle_regioni(self):
        snapshot = self.level["fotografia"]
        threshold = snapshot["soglia"]
        self.assertEqual(threshold["soglia"]["valore"], 100)
        self.assertEqual(
            threshold["sopra"]["valore"] + threshold["pari"]["valore"] + threshold["sotto"]["valore"],
            snapshot["territori_con_dato"]["valore"],
        )
        areas = snapshot["ripartizioni"]["valori"]
        self.assertEqual(sum(a["territori"]["valore"] for a in areas), snapshot["territori_con_dato"]["valore"])

    def test_contesto_regionale_senza_correlazioni(self):
        context = self.dossier["contesto_economico"]
        self.assertIsNone(context["correlazioni_di_rango"])
        self.assertTrue(context["motivo_senza_correlazioni"])
        self.assertEqual(context["territori"][0]["regione"], "Marche")


class Cli(unittest.TestCase):
    def test_scrive_il_json_ed_e_deterministico(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "ter-12.json"
            result = subprocess.run(
                [sys.executable, "-m", "scripts.editoriale.brief", "ter-12", "--out", str(out)],
                cwd=ROOT, capture_output=True, timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(out.read_text(encoding="utf-8"), brief.dumps(brief.build("12")))

    def test_codice_sconosciuto_esce_con_errore(self):
        result = subprocess.run(
            [sys.executable, "-m", "scripts.editoriale.brief", "ter-99999999"],
            cwd=ROOT, capture_output=True, timeout=120,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"nessuna scheda", result.stderr)


if __name__ == "__main__":
    unittest.main()
