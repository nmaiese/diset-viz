"""L'importazione della passata v2 (quattro sezioni) nello store degli articoli.

Due schede reali fanno da fixture, copiate in una root temporanea e riportate
alla forma di prima della passata: la `multiscopo:MULTI_REDD_MEDIO` senza
definizione né dinamica (quadro, limiti) e la `920` con le quattro sezioni.
Lo store committato non si tocca mai.
"""

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import importa_passata_schede as imp
from scripts import indicator_store

REAL_KEYS = ("multiscopo:MULTI_REDD_MEDIO", "920")
KEY_REDD, KEY_ETA = REAL_KEYS
PATH_REDD = "/indicatore/reddito-netto-medio-annuale-delle-famiglie/ims-MULTI_REDD_MEDIO"
PATH_ETA = "/indicatore/eta-media-della-popolazione/ter-920"

LEAD = ("Nel 2024 una famiglia del Trentino Alto Adige ha avuto in media 55.295 euro, una della "
        "Calabria 34.741 (Istat). In un anno il reddito è aumentato in tutte le regioni, da nord a sud.")
MISURA = "Il numero è il reddito netto annuo di una famiglia media della regione, dopo tasse e contributi."
QUADRO = "La mediana delle regioni è 45.631 euro e la fascia centrale va da 39.237 a 48.835."
CAMBIAMENTO = "La media delle regioni è passata da 35.330 euro nel 2018 a 44.463 nel 2024."
LETTURA = "Un reddito alto non vuol dire una vita più comoda: il costo della vita cambia da regione a regione."


def voce(suffisso="", **extra):
    base = {"lead": LEAD,
            "misura_titolo": f"Che cosa include il reddito{suffisso}", "misura": MISURA,
            "quadro_titolo": f"Oltre ventimila euro di distanza{suffisso}", "quadro": QUADRO,
            "cambiamento_titolo": f"Una crescita con una flessione{suffisso}", "cambiamento": CAMBIAMENTO,
            "lettura_titolo": f"Il reddito non è il benessere{suffisso}", "lettura": LETTURA,
            "il_lettore_capisce": "nota", "fonte_dati": "pagina del sito",
            "parole": imp.count_words(LEAD, MISURA, QUADRO, CAMBIAMENTO, LETTURA)}
    base.update(extra)
    return base


def blocco(**extra):
    """Due schede, con titoli diversi (due uguali fra schede sono un errore)."""
    return {PATH_REDD: voce(**extra), PATH_ETA: voce(" (età)", **extra)}


def ruoli(entry):
    return [s["role"] for s in entry["sections"]]


def sezione(entry, ruolo):
    return next(s for s in entry["sections"] if s["role"] == ruolo)


class StoreTemporaneo(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        for key in REAL_KEYS:
            entry = indicator_store.read(key)
            self.assertIsNotNone(entry, f"la scheda reale {key} non c'è più nello store")
            indicator_store.write(key, self.forma_di_prima(key, entry), root=self.root)
        self.prima = {k: indicator_store.read(k, root=self.root) for k in REAL_KEYS}

    @staticmethod
    def forma_di_prima(key, entry):
        if key == KEY_REDD:
            sezioni = [dict(s) for s in entry["sections"] if s["role"] in ("quadro", "limiti")]
            return {**entry, "sections": sezioni}
        return entry

    def leggi(self, key):
        return indicator_store.read(key, root=self.root)


class ImportaDueSchede(StoreTemporaneo):
    def test_fixture_ha_le_due_forme_attese(self):
        self.assertEqual(ruoli(self.prima[KEY_REDD]), ["quadro", "limiti"])
        self.assertEqual(ruoli(self.prima[KEY_ETA]), ["definizione", "quadro", "dinamica", "limiti"])

    def test_v2_completa_prima_e_dopo(self):
        esito = imp.import_block(blocco(), root=self.root)
        self.assertEqual((len(esito.written), len(esito.errors)), (2, 0))

        redd = self.leggi(KEY_REDD)
        self.assertEqual(redd["lead"], LEAD)
        self.assertEqual(ruoli(redd), ["definizione", "quadro", "dinamica", "limiti"])
        for ruolo, titolo, corpo in (
                ("definizione", "Che cosa include il reddito", MISURA),
                ("quadro", "Oltre ventimila euro di distanza", QUADRO),
                ("dinamica", "Una crescita con una flessione", CAMBIAMENTO),
                ("limiti", "Il reddito non è il benessere", LETTURA)):
            s = sezione(redd, ruolo)
            self.assertEqual((s["h"], s["body"]), (titolo, corpo))
        for campo in ("fonti", "vintage"):
            self.assertEqual(redd[campo], self.prima[KEY_REDD][campo])

        eta = self.leggi(KEY_ETA)       # le quattro c'erano: si sostituiscono, non si duplicano
        self.assertEqual(ruoli(eta), ["definizione", "quadro", "dinamica", "limiti"])
        self.assertEqual(sezione(eta, "quadro")["body"], QUADRO)
        self.assertNotEqual(sezione(eta, "quadro"), sezione(self.prima[KEY_ETA], "quadro"))

    def test_cambiamento_assente_lascia_la_dinamica(self):
        dati = blocco()
        for v in dati.values():
            del v["cambiamento"], v["cambiamento_titolo"]
        esito = imp.import_block(dati, root=self.root)
        self.assertEqual(esito.errors, [])
        # la scheda con dinamica la tiene com'era
        self.assertEqual(sezione(self.leggi(KEY_ETA), "dinamica"),
                         sezione(self.prima[KEY_ETA], "dinamica"))
        # quella senza non se ne inventa una
        self.assertEqual(ruoli(self.leggi(KEY_REDD)), ["definizione", "quadro", "limiti"])

    def test_cambiamento_con_solo_il_titolo_e_errore(self):
        dati = {PATH_REDD: voce(cambiamento="")}
        esito = imp.import_block(dati, root=self.root)
        self.assertEqual([m for _, m in esito.errors], ["campo cambiamento vuoto o mancante"])

    def test_quadro_e_limiti_si_sostituiscono(self):
        imp.import_block({PATH_REDD: voce()}, root=self.root)
        redd = self.leggi(KEY_REDD)
        vecchia = self.prima[KEY_REDD]
        self.assertNotEqual(sezione(redd, "quadro")["body"], sezione(vecchia, "quadro")["body"])
        self.assertNotEqual(sezione(redd, "limiti")["body"], sezione(vecchia, "limiti")["body"])
        self.assertEqual(sum(r == "quadro" for r in ruoli(redd)), 1)
        self.assertEqual(sum(r == "limiti" for r in ruoli(redd)), 1)

    def test_sezione_libera_e_errore_e_nessuna_scrittura(self):
        entry = self.leggi(KEY_ETA)
        entry["sections"].append({"role": "libera", "h": "Altro", "body": "Testo da non perdere."})
        indicator_store.write(KEY_ETA, entry, root=self.root)
        esito = imp.import_block(blocco(), root=self.root)
        self.assertEqual([p for p, _ in esito.errors], [PATH_ETA])
        self.assertIn("libera", esito.errors[0][1])
        self.assertEqual(esito.written, [KEY_REDD])     # tutto o niente per scheda
        self.assertIn("Testo da non perdere.", indicator_store.path_for(KEY_ETA, root=self.root).read_text("utf-8"))

    def test_il_lettore_capisce_e_fonte_dati_non_si_importano(self):
        imp.import_block(blocco(), root=self.root)
        testo = indicator_store.path_for(KEY_ETA, root=self.root).read_text(encoding="utf-8")
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
        self.assertEqual(esito.written, [KEY_REDD])

    def test_percorso_sconosciuto_e_errore_solo_per_lui(self):
        dati = blocco()
        dati["/indicatore/non-esiste/ter-99999"] = voce(" (x)")
        esito = imp.import_block(dati, root=self.root)
        self.assertEqual([p for p, _ in esito.errors], ["/indicatore/non-esiste/ter-99999"])
        self.assertEqual(len(esito.written), 2)

    def test_titolo_mancante_o_vuoto_e_errore(self):
        for campo in ("misura_titolo", "quadro_titolo", "lettura_titolo"):
            for valore in ("", None):
                with self.subTest(campo=campo, valore=valore):
                    esito = imp.import_block({PATH_REDD: voce(**{campo: valore})}, root=self.root)
                    self.assertEqual([m for _, m in esito.errors], [f"campo {campo} vuoto o mancante"])
                    self.assertEqual(esito.written, [])

    def test_lead_mancante_e_errore(self):
        dati = voce()
        del dati["lead"]
        esito = imp.import_block({PATH_REDD: dati}, root=self.root)
        self.assertEqual([m for _, m in esito.errors], ["campo lead vuoto o mancante"])

    def test_titoli_duplicati_fra_due_schede(self):
        dati = {PATH_REDD: voce(), PATH_ETA: voce()}
        esito = imp.import_block(dati, root=self.root)
        self.assertEqual({p for p, _ in esito.errors}, {PATH_ETA})
        self.assertEqual(len(esito.errors), 1)          # la prima ripetizione basta a escluderla
        self.assertEqual(esito.written, [KEY_REDD])     # la prima si scrive, la seconda no
        self.assertEqual(self.leggi(KEY_ETA), self.prima[KEY_ETA])

    def test_caratteri_vietati_in_ogni_campo_sono_errore(self):
        campi = ("lead", "misura", "quadro", "cambiamento", "lettura",
                 "misura_titolo", "quadro_titolo", "cambiamento_titolo", "lettura_titolo")
        for campo in campi:
            for vietato in ("—", "–", ";", "…"):
                with self.subTest(campo=campo, vietato=vietato):
                    esito = imp.import_block(
                        {PATH_REDD: voce(**{campo: f"A {vietato} B.", "parole": 0})}, root=self.root)
                    self.assertEqual(len(esito.errors), 1)
                    self.assertIn(campo, esito.errors[0][1])
                    self.assertEqual(esito.written, [])
                    self.assertEqual(self.leggi(KEY_REDD), self.prima[KEY_REDD])

    def test_lead_fuori_misura_avvisa_e_scrive(self):
        for lead in ("Troppo corto.", "parola " * 60):
            with self.subTest(lead=lead[:12]):
                esito = imp.import_block({PATH_REDD: voce(lead=lead.strip(), parole=0)}, root=self.root)
                self.assertTrue(any("parole (atteso 30-45)" in t for _, t in esito.warnings))
                self.assertEqual(len(esito.written), 1)

    def test_lead_in_misura_non_avvisa(self):
        esito = imp.import_block({PATH_REDD: voce()}, root=self.root)
        self.assertEqual(esito.warnings, [])

    def test_parole_dichiarate_incoerenti_avvisano(self):
        esito = imp.import_block({PATH_REDD: voce(parole=900)}, root=self.root)
        self.assertTrue(any("parole dichiarate" in testo for _, testo in esito.warnings))
        self.assertEqual(len(esito.written), 1)

    def test_non_pubblicare_si_salta(self):
        esito = imp.import_block({PATH_REDD: {"titolo": "x", "non_pubblicare": "da verificare"}},
                                 root=self.root)
        self.assertEqual((len(esito.skipped), len(esito.errors), esito.written), (1, 0, []))

    def test_dry_run_non_scrive_ma_mostra_il_diff(self):
        esito = imp.import_block(blocco(), root=self.root, dry_run=True)
        self.assertEqual(set(esito.diffs), set(REAL_KEYS))
        self.assertIn("+<!-- sezione: definizione -->", esito.diffs[KEY_REDD])
        for key in REAL_KEYS:
            self.assertEqual(self.leggi(key), self.prima[key])

    def test_solo_e_max(self):
        esito = imp.import_block(blocco(), root=self.root, max_n=1, dry_run=True)
        self.assertEqual((esito.written, esito.total), ([KEY_REDD], 1))
        esito = imp.import_block(blocco(), root=self.root, only={"ims-MULTI_REDD_MEDIO"})
        self.assertEqual((esito.written, esito.total), ([KEY_REDD], 1))
        self.assertEqual(self.leggi(KEY_ETA), self.prima[KEY_ETA])


class Cli(StoreTemporaneo):
    def lancia(self, dati, *extra):
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
        self.assertIn("1 schede in errore", out)
        self.assertIn("ERRORE", err)

    def test_solo_file_di_percorsi(self):
        elenco = self.root / "elenco.txt"
        elenco.write_text(f"{PATH_ETA}/province\n\n", encoding="utf-8")
        codice, out, _ = self.lancia(blocco(), "--solo", str(elenco), "--dry-run")
        self.assertEqual(codice, 0)
        self.assertIn("1 voci nel lancio: 1 da scrivere", out)

    def test_solo_csv_con_proposta(self):
        csv_file = self.root / "schede.csv"
        csv_file.write_text(f"percorso,proposta\n{PATH_REDD},ARRICCHIRE\n{PATH_ETA},ALTRO\n", encoding="utf-8")
        _, out, _ = self.lancia(blocco(), "--solo", str(csv_file), "--proposta", "ARRICCHIRE", "--dry-run")
        self.assertIn("1 voci nel lancio: 1 da scrivere", out)
        _, out, _ = self.lancia(blocco(), "--solo", str(csv_file), "--dry-run")
        self.assertIn("2 voci nel lancio: 2 da scrivere", out)

    def test_max(self):
        _, out, _ = self.lancia(blocco(), "--max", "1", "--dry-run")
        self.assertIn("1 voci nel lancio: 1 da scrivere", out)


class LaPaginaResaMostraLaProsa(StoreTemporaneo):
    def test_scheda_in_tmp_mostra_lead_e_le_quattro_sezioni(self):
        from app import app, indicator_texts
        imp.import_block({PATH_REDD: voce()}, root=self.root)
        with patch.object(indicator_store, "ROOT", self.root):
            indicator_texts._load.cache_clear()
            self.addCleanup(indicator_texts._load.cache_clear)
            pagina = app.test_client().get(PATH_REDD).get_data(as_text=True)
        for atteso in (LEAD, "Che cosa include il reddito", MISURA, "Oltre ventimila euro di distanza",
                       QUADRO, "Una crescita con una flessione", CAMBIAMENTO,
                       "Il reddito non è il benessere", LETTURA):
            self.assertIn(atteso, pagina)


if __name__ == "__main__":
    unittest.main()
