"""L'importazione di un blocco della passata schede nello store degli articoli.

Due schede reali fanno da fixture, copiate in una root temporanea: la
`multiscopo:MULTI_REDD_MEDIO` (lead, quadro, limiti, nessuna definizione) e la
`920` (le quattro sezioni, definizione compresa). Lo store committato non si
tocca mai.
"""

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import importa_passata_schede as imp
from scripts import indicator_store

REAL_KEYS = ("multiscopo:MULTI_REDD_MEDIO", "920")
PATH_REDD = "/indicatore/reddito-netto-medio-annuale-delle-famiglie/ims-MULTI_REDD_MEDIO"
PATH_ETA = "/indicatore/eta-media-della-popolazione/ter-920"

LEAD = "Nel 2024 una famiglia del Trentino Alto Adige ha avuto in media 55.295 euro, una della Calabria 34.741."
SEMPLICI = "Il numero è il reddito netto annuo di una famiglia media della regione, dopo tasse e contributi."
NON_DICE = "È una stima da campione e non tiene conto del costo della vita."


def voce(**extra):
    base = {"titolo": "Indicatore", "lead": LEAD, "parole_semplici": SEMPLICI,
            "non_dice": NON_DICE, "il_lettore_capisce": "nota", "fonte_dati": "pagina del sito",
            "parole": imp.count_words(LEAD, SEMPLICI, NON_DICE)}
    base.update(extra)
    return base


def blocco(**extra):
    return {PATH_REDD: voce(**extra), PATH_ETA: voce(**extra)}


def ruoli(entry):
    return [s["role"] for s in entry["sections"]]


class StoreTemporaneo(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        for key in REAL_KEYS:
            entry = indicator_store.read(key)
            self.assertIsNotNone(entry, f"la scheda reale {key} non c'è più nello store")
            indicator_store.write(key, entry, root=self.root)
        self.prima = {k: indicator_store.read(k, root=self.root) for k in REAL_KEYS}

    def leggi(self, key):
        return indicator_store.read(key, root=self.root)


class ImportaDueSchede(StoreTemporaneo):
    def test_fixture_ha_le_due_forme_attese(self):
        self.assertEqual(ruoli(self.prima["multiscopo:MULTI_REDD_MEDIO"]), ["quadro", "limiti"])
        self.assertIn("definizione", ruoli(self.prima["920"]))

    def test_prima_e_dopo(self):
        esito = imp.import_block(blocco(), root=self.root)
        self.assertEqual((len(esito.written), len(esito.errors)), (2, 0))

        redd = self.leggi("multiscopo:MULTI_REDD_MEDIO")
        self.assertEqual(redd["lead"], LEAD)
        self.assertEqual(ruoli(redd), ["definizione", "quadro", "limiti"])
        definizione, quadro, limiti = redd["sections"]
        self.assertEqual((definizione["h"], definizione["body"]),
                         ("In parole semplici", SEMPLICI))
        self.assertEqual((limiti["h"], limiti["body"]), ("Che cosa questo dato non dice", NON_DICE))
        # quadro e frontmatter restano com'erano
        self.assertEqual(quadro, self.prima["multiscopo:MULTI_REDD_MEDIO"]["sections"][0])
        for campo in ("fonti", "vintage"):
            self.assertEqual(redd[campo], self.prima["multiscopo:MULTI_REDD_MEDIO"][campo])

        eta = self.leggi("920")
        antica = self.prima["920"]
        self.assertEqual(ruoli(eta), ruoli(antica))     # la definizione c'era: si sostituisce, non si duplica
        self.assertEqual(sum(r == "definizione" for r in ruoli(eta)), 1)
        self.assertEqual(eta["sections"][0]["body"], SEMPLICI)
        for ruolo in ("quadro", "dinamica"):
            self.assertEqual(next(s for s in eta["sections"] if s["role"] == ruolo),
                             next(s for s in antica["sections"] if s["role"] == ruolo))
        self.assertEqual(eta["fonti"], antica["fonti"])

    def test_il_lettore_capisce_e_fonte_dati_non_si_importano(self):
        imp.import_block(blocco(), root=self.root)
        testo = indicator_store.path_for("920", root=self.root).read_text(encoding="utf-8")
        self.assertNotIn("nota", testo.split("---")[2])
        self.assertNotIn("pagina del sito", testo)

    def test_idempotente(self):
        imp.import_block(blocco(), root=self.root)
        dopo_uno = {p.name: p.read_text(encoding="utf-8") for p in indicator_store.paths(self.root)}
        esito = imp.import_block(blocco(), root=self.root)
        dopo_due = {p.name: p.read_text(encoding="utf-8") for p in indicator_store.paths(self.root)}
        self.assertEqual(dopo_uno, dopo_due)
        self.assertEqual((len(esito.written), len(esito.unchanged)), (0, 2))

    def test_percorso_con_province_risolve_come_senza(self):
        esito = imp.import_block({PATH_REDD + "/province": voce()}, root=self.root)
        self.assertEqual(esito.written, ["multiscopo:MULTI_REDD_MEDIO"])

    def test_percorso_sconosciuto_e_errore_e_nessuna_scrittura(self):
        dati = blocco()
        dati["/indicatore/non-esiste/ter-99999"] = voce()
        esito = imp.import_block(dati, root=self.root)
        self.assertEqual([p for p, _ in esito.errors], ["/indicatore/non-esiste/ter-99999"])
        self.assertEqual(esito.written, [])
        for key in REAL_KEYS:                       # nemmeno le schede buone
            self.assertEqual(self.leggi(key), self.prima[key])

    def test_titoli_di_default_e_titoli_dati(self):
        imp.import_block({PATH_REDD: voce()}, root=self.root)
        sezioni = {s["role"]: s["h"] for s in self.leggi("multiscopo:MULTI_REDD_MEDIO")["sections"]}
        self.assertEqual((sezioni["definizione"], sezioni["limiti"]),
                         ("In parole semplici", "Che cosa questo dato non dice"))
        imp.import_block({PATH_REDD: voce(titolo_parole_semplici="Che cosa misura",
                                          titolo_non_dice="Cosa manca")}, root=self.root)
        sezioni = {s["role"]: s["h"] for s in self.leggi("multiscopo:MULTI_REDD_MEDIO")["sections"]}
        self.assertEqual((sezioni["definizione"], sezioni["limiti"]), ("Che cosa misura", "Cosa manca"))

    def test_lead_vuoto_lascia_l_esistente_con_avviso(self):
        esito = imp.import_block({PATH_REDD: voce(lead="", parole=0)}, root=self.root)
        redd = self.leggi("multiscopo:MULTI_REDD_MEDIO")
        self.assertEqual(redd["lead"], self.prima["multiscopo:MULTI_REDD_MEDIO"]["lead"])
        self.assertEqual(esito.empty_leads, [PATH_REDD])
        self.assertTrue(any("lead vuoto" in testo for _, testo in esito.warnings))
        self.assertEqual(ruoli(redd), ["definizione", "quadro", "limiti"])

    def test_lead_lungo_avvisa_e_non_taglia(self):
        lungo = ("Una frase ragionevole. " * 20).strip()
        self.assertGreater(len(lungo), imp.LEAD_MAX)
        esito = imp.import_block({PATH_REDD: voce(lead=lungo, parole=0)}, root=self.root)
        self.assertEqual(esito.long_leads, [PATH_REDD])
        self.assertEqual(self.leggi("multiscopo:MULTI_REDD_MEDIO")["lead"], lungo)

    def test_parole_dichiarate_incoerenti_avvisano(self):
        esito = imp.import_block({PATH_REDD: voce(parole=500)}, root=self.root)
        self.assertTrue(any("parole dichiarate" in testo for _, testo in esito.warnings))
        self.assertEqual(len(esito.written), 1)

    def test_caratteri_vietati_sono_errore(self):
        for vietato in ("—", "–", ";", "…"):
            with self.subTest(vietato=vietato):
                esito = imp.import_block({PATH_REDD: voce(non_dice=f"A {vietato} B.", parole=0)},
                                         root=self.root)
                self.assertEqual(len(esito.errors), 1)
                self.assertEqual(esito.written, [])
                self.assertEqual(self.leggi("multiscopo:MULTI_REDD_MEDIO"),
                                 self.prima["multiscopo:MULTI_REDD_MEDIO"])

    def test_non_pubblicare_si_salta(self):
        esito = imp.import_block({PATH_REDD: {"titolo": "x", "non_pubblicare": "da verificare"}},
                                 root=self.root)
        self.assertEqual((len(esito.skipped), len(esito.errors), esito.written), (1, 0, []))

    def test_dry_run_non_scrive_ma_mostra_il_diff(self):
        esito = imp.import_block(blocco(), root=self.root, dry_run=True)
        self.assertEqual(len(esito.written), 2)
        self.assertEqual(set(esito.diffs), set(REAL_KEYS))
        self.assertIn("+<!-- sezione: definizione -->", esito.diffs["multiscopo:MULTI_REDD_MEDIO"])
        for key in REAL_KEYS:
            self.assertEqual(self.leggi(key), self.prima[key])


class Cli(StoreTemporaneo):
    def lancia(self, dati, *extra):
        import json
        file = self.root / "blocco.json"
        file.write_text(json.dumps(dati), encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            codice = imp.main(["--blocco", str(file), "--root", str(self.root), *extra])
        return codice, out.getvalue(), err.getvalue()

    def test_exit_e_riepilogo(self):
        codice, out, _ = self.lancia(blocco(), "--dry-run")
        self.assertEqual(codice, 0)
        self.assertIn("2 da scrivere", out)
        codice, out, err = self.lancia({"/indicatore/x/ter-99999": voce()})
        self.assertEqual(codice, 1)
        self.assertIn("1 in errore", out)
        self.assertIn("ERRORE", err)


class LaPaginaResaMostraLaProsa(StoreTemporaneo):
    def test_scheda_in_tmp_mostra_lead_e_le_due_sezioni(self):
        from app import app, indicator_texts
        imp.import_block({PATH_REDD: voce()}, root=self.root)
        with patch.object(indicator_store, "ROOT", self.root):
            indicator_texts._load.cache_clear()
            self.addCleanup(indicator_texts._load.cache_clear)
            pagina = app.test_client().get(PATH_REDD).get_data(as_text=True)
        for atteso in (LEAD, "In parole semplici", SEMPLICI,
                       "Che cosa questo dato non dice", NON_DICE):
            self.assertIn(atteso, pagina)


if __name__ == "__main__":
    unittest.main()
