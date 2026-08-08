"""Il cruscotto lato server: la presa dati e le due viste.

Il perno di questo file e' un invariante che non si vede guardando una risposta
sola: **il battito e il consuntivo scrivono colonne disgiunte**. Vengono da due
sorgenti diverse (i file che il runtime scrive mentre la run gira, e
`<runId>.json` che compare a run finita), arrivano in ordine non garantito, e il
secondo puo' ripetersi. Se una sorgente riscrivesse quello che ha detto l'altra,
il cruscotto direbbe una bugia proprio sulla run che qualcuno sta guardando. Qui
si prova nei due ordini.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from app import app, auth, config
from app.cache import cache

SEGRETO = "ingest-di-prova"

ESITO_CON_SOVRASCRITTURA = {
    "richiesti": 1, "scritti": 1, "fermati": [],
    "articoli": [{
        "codice": "ter-13", "scritto": True, "sovrascritto": True,
        "vintage_precedente": 2024, "percorso": "content/indicators/13.json",
        "parole": 782, "angolo": "il divario si chiude dall'alto perche' cade la testa",
        "giri_di_correzione": 2, "cifre_verificate": 41,
        "rilievi_aperti": ["bassa | cifra | lead: il 16,85 e' la media semplice"],
        "rilievi": [{"rule": "dinamica-senza-fonte", "severity": "segnala", "detail": ""}],
        "impaginazione": [{"role": "quadro", "h2": "Dove sta l'Italia", "scritta": True}],
    }],
}

ESITO_FERMATO = {
    "richiesti": 1, "scritti": 0, "articoli": [],
    "fermati": [{"codice": "ter-30", "pubblicabile": False,
                 "motivo": "smentito 3 volte", "giri": 2,
                 "verdetto": {"verificate": 12, "smentite": [
                     {"tipo": "cifra", "dove": "lead", "gravita": "alta",
                      "cosa_dice_il_testo": "media nazionale",
                      "cosa_dicono_i_dati": "media semplice delle venti regioni"}]}}],
}


class CruscottoBase(unittest.TestCase):
    """Un database per classe, e la mail admin finta sul JWT verificato.

    `auth.current_user` legge il JWT: qui si sostituisce, perche' il confine che
    interessa a questo file e' 404-per-chi-non-e-admin, non la firma del token,
    che ha i suoi test in `tests/integration/test_auth.py`."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._db = config.LEADERBOARD_DB
        config.LEADERBOARD_DB = str(Path(self._tmp) / "cruscotto.sqlite3")
        self._token = config.PIPELINE_INGEST_TOKEN
        config.PIPELINE_INGEST_TOKEN = SEGRETO
        self._current_user = auth.current_user
        self.client = app.test_client()
        cache.clear()

    def tearDown(self):
        config.LEADERBOARD_DB = self._db
        config.PIPELINE_INGEST_TOKEN = self._token
        auth.current_user = self._current_user
        shutil.rmtree(self._tmp, ignore_errors=True)
        cache.clear()

    def admin(self):
        auth.current_user = lambda headers: {"email": config.MONITOR_ADMIN_EMAIL.lower()}

    def anonimo(self):
        auth.current_user = lambda headers: None

    def posta(self, payload, segreto=SEGRETO):
        return self.client.post("/_pipeline/beat", json=payload,
                                headers={"X-Pipeline-Key": segreto})

    def runs(self):
        self.admin()
        cache.clear()
        risposta = self.client.get("/_pipeline/api/runs")
        self.assertEqual(risposta.status_code, 200)
        return risposta.get_json()["runs"]

    def indicatori(self):
        self.admin()
        cache.clear()
        risposta = self.client.get("/_pipeline/api/indicatori")
        self.assertEqual(risposta.status_code, 200)
        return risposta.get_json()["indicatori"]


class LaPresa(CruscottoBase):
    def test_senza_segreto_non_conferma_nemmeno_di_esistere(self):
        for segreto in ("", "sbagliato"):
            self.assertEqual(self.posta({"action": "run", "run_id": "wf_1"}, segreto).status_code, 404)

    def test_azione_sconosciuta_e_400(self):
        self.assertEqual(self.posta({"action": "boh"}).status_code, 400)

    def test_run_senza_id_e_400(self):
        self.assertEqual(self.posta({"action": "run", "run_id": ""}).status_code, 400)

    def test_il_battito_crea_la_run_e_i_suoi_agenti(self):
        self.assertEqual(self.posta({
            "action": "run", "run_id": "wf_1",
            "avviata_il": "2026-08-08T09:00:00+00:00", "fase_stimata": "Verifica",
            "agenti_visti": 2}).status_code, 200)
        self.posta({"action": "agente", "run_id": "wf_1", "agent_id": "a1",
                    "agent_type": "lab-scrittore", "fase_stimata": "Scrittura",
                    "indicatore": "ter-13", "stato_vivo": "chiuso",
                    "risultato": json.dumps({"angolo": "una tesi"})})
        run = self.runs()[0]
        self.assertEqual(run["run_id"], "wf_1")
        self.assertTrue(run["in_volo"])
        self.assertEqual(run["fase_stimata"], "Verifica")
        # Dal vivo il nome del workflow non esiste: sta solo in `<runId>.json`,
        # che compare a run finita. La riga lo dice restando nulla, invece di
        # inventarselo.
        self.assertIsNone(run["workflow"])
        agente = run["agenti"][0]
        self.assertEqual(agente["indicatore"], "ter-13")
        self.assertEqual(agente["risultato"]["angolo"], "una tesi")
        # Dal vivo la fase e' una stima, e la riga deve dirlo: mostrarla con la
        # stessa faccia della verita' sarebbe la bugia piu' facile da fare.
        self.assertTrue(agente["fase_stimata"])

    def test_un_agente_aperto_non_ha_ancora_un_risultato(self):
        # Il lettore manda `risultato: null` per ogni agente che non ha ancora
        # restituito, cioe' per ogni agente in volo. La colonna non e' nullable,
        # e scriverla faceva 500 sul POST: il cruscotto perdeva esattamente gli
        # agenti aperti, che sono l'unica cosa che l'orizzonte in tempo reale
        # deve mostrare. Trovato girando il lettore contro un server vero.
        risposta = self.posta({"action": "agente", "run_id": "wf_1", "agent_id": "a1",
                               "agent_type": "lab-verificatore", "stato_vivo": "aperto",
                               "risultato": None})
        self.assertEqual(risposta.status_code, 200)
        agente = self.runs()[0]["agenti"][0]
        self.assertEqual(agente["stato_vivo"], "aperto")
        self.assertIsNone(agente["risultato"])

    def test_un_battito_parziale_non_azzera_quello_di_prima(self):
        self.posta({"action": "run", "run_id": "wf_1", "sessione": "s-01",
                    "fase_stimata": "Contesto", "agenti_visti": 4})
        self.posta({"action": "run", "run_id": "wf_1", "fase_stimata": "Scrittura"})
        run = self.runs()[0]
        self.assertEqual(run["fase_stimata"], "Scrittura")
        self.assertEqual(run["sessione"], "s-01")
        self.assertEqual(run["agenti_visti"], 4)


class LeDueSorgentiNonSiPestano(CruscottoBase):
    """L'invariante del modello dati, nei due ordini possibili."""

    def battito(self):
        self.posta({"action": "run", "run_id": "wf_1",
                    "avviata_il": "2026-08-08T09:00:00+00:00",
                    "fase_stimata": "Verifica", "agenti_visti": 1})
        self.posta({"action": "agente", "run_id": "wf_1", "agent_id": "a1",
                    "agent_type": "lab-scrittore", "fase_stimata": "Scrittura",
                    "indicatore": "ter-13", "stato_vivo": "chiuso",
                    "risultato": json.dumps({"angolo": "una tesi"})})

    def consuntivo(self):
        self.posta({"action": "consuntivo", "run_id": "wf_1", "run": {
            "workflow": "indicatore-lite",
            "stato": "completed", "durata_ms": 1234567, "fasi": ["Scrittura"],
            "esito": ESITO_CON_SOVRASCRITTURA, "logs": ["una riga"],
            "agenti": 1, "turni": 9, "tool": 14, "token_out": 5000,
            "costo": 7.1, "costo_pavimento": 1,
        }, "agenti": [{"agent_id": "a1", "label": "scrivi:ter-13", "fase": "Scrittura",
                       "modello": "claude-opus-5", "stato": "done", "turni": 9,
                       "tool": 14, "costo": 3.2}]})

    def controlla(self):
        run = self.runs()[0]
        # dal consuntivo
        self.assertEqual(run["workflow"], "indicatore-lite")
        self.assertEqual(run["stato"], "completed")
        self.assertEqual(run["costo"], 7.1)
        self.assertTrue(run["costo_pavimento"])
        self.assertFalse(run["in_volo"])
        # dal battito, ancora intatto
        self.assertEqual(run["fase_stimata"], "Verifica")
        self.assertEqual(run["avviata_il"], "2026-08-08T09:00:00+00:00")
        agente = run["agenti"][0]
        self.assertEqual(agente["label"], "scrivi:ter-13")
        self.assertEqual(agente["modello"], "claude-opus-5")
        self.assertEqual(agente["indicatore"], "ter-13")
        self.assertEqual(agente["stato_vivo"], "chiuso")
        self.assertEqual(agente["risultato"]["angolo"], "una tesi")
        # La fase adesso e' quella vera, e la riga smette di dichiararla stimata.
        self.assertEqual(agente["fase"], "Scrittura")
        self.assertFalse(agente["fase_stimata"])

    def test_prima_il_battito_poi_il_consuntivo(self):
        self.battito()
        self.consuntivo()
        self.controlla()

    def test_prima_il_consuntivo_poi_il_battito(self):
        # Succede davvero: il lettore parte a run gia' finita, oppure il POST
        # del battito arriva in ritardo dopo un guasto di rete.
        self.consuntivo()
        self.battito()
        self.controlla()

    def test_il_consuntivo_ripetuto_non_cancella_il_vivo(self):
        self.battito()
        self.consuntivo()
        self.consuntivo()
        self.controlla()


class LaVistaPerIndicatore(CruscottoBase):
    """Derivata dall'esito della run, non copiata in una tabella sua."""

    def scrivi(self, run_id, esito, avviata):
        self.posta({"action": "run", "run_id": run_id, "avviata_il": avviata})
        self.posta({"action": "consuntivo", "run_id": run_id,
                    "run": {"workflow": "indicatore-lite", "stato": "completed",
                            "esito": esito, "costo": 7.0, "costo_pavimento": 1},
                    "agenti": []})

    def test_un_articolo_scritto_porta_sovrascritto_e_vintage(self):
        self.scrivi("wf_1", ESITO_CON_SOVRASCRITTURA, "2026-08-08T09:00:00+00:00")
        riga = self.indicatori()[0]
        self.assertEqual(riga["indicatore"], "ter-13")
        self.assertEqual(riga["esito"], "scritto con rilievi")
        self.assertTrue(riga["sovrascritto"])
        self.assertEqual(riga["vintage_precedente"], 2024)
        self.assertEqual(riga["parole"], 782)
        self.assertEqual(riga["giri_di_correzione"], 2)
        self.assertEqual(len(riga["rilievi_aperti"]), 1)
        # L'indicatore linka la pagina pubblica: `ter-13` e' l'id `13`.
        self.assertTrue((riga["published_url"] or "").endswith("/ter-13"))

    def test_ogni_famiglia_risolve_la_sua_pagina_pubblica(self):
        """Il link alla pagina, per un codice vero di ogni famiglia.

        Non e' pignoleria: i codici della catena usano l'**acronimo**
        (`ims-...`) e gli id del catalogo la **famiglia** (`multiscopo:...`),
        e le due cose non coincidono. Scritta a mano, la traduzione sbagliava
        su `ims` e sbagliava in silenzio, perche' `_pipeline_published_url`
        inghiotte l'eccezione: la riga usciva senza link invece che con un
        errore, ed e' il tipo di guasto che nessuno vede finche' non gli serve
        proprio quel link."""
        from app import bes_data, data, external_atlas, multiscopo_data
        from app.views import _id_da_codice, _pipeline_published_url
        campioni = {
            "ter": "ter-" + str(data.get_catalog()["indicators"][0]["id"]),
            "bes": "bes-" + str(next(iter(bes_data.all_bes_indicators()))["id"]),
            "ims": "ims-" + str(next(iter(multiscopo_data.all_multiscopo_indicators()))["id"]),
        }
        for item in external_atlas.all_external_indicators():
            famiglia, _, resto = str(item["id"]).partition(":")
            campioni.setdefault(famiglia, f"{famiglia}-{resto}")
        senza_link = [c for c in campioni.values()
                      if not _pipeline_published_url(_id_da_codice(c))]
        self.assertEqual(senza_link, [], f"codici che non risolvono: {senza_link}")

    def test_una_run_fermata_non_e_un_guasto(self):
        self.scrivi("wf_2", ESITO_FERMATO, "2026-08-08T10:00:00+00:00")
        riga = self.indicatori()[0]
        self.assertEqual(riga["indicatore"], "ter-30")
        self.assertEqual(riga["esito"], "fermato")
        self.assertFalse(riga["scritto"])
        self.assertEqual(riga["motivo"], "smentito 3 volte")
        self.assertIsNone(riga["sovrascritto"])

    def test_le_scritture_stanno_in_ordine_di_tempo(self):
        self.scrivi("wf_1", ESITO_CON_SOVRASCRITTURA, "2026-08-08T09:00:00+00:00")
        self.scrivi("wf_2", ESITO_FERMATO, "2026-08-08T10:00:00+00:00")
        self.assertEqual([r["indicatore"] for r in self.indicatori()], ["ter-30", "ter-13"])

    def test_una_run_in_volo_non_produce_righe(self):
        self.posta({"action": "run", "run_id": "wf_3",
                    "avviata_il": "2026-08-08T11:00:00+00:00"})
        self.assertEqual(self.indicatori(), [])


class IlConfine(CruscottoBase):
    def test_le_due_api_sono_404_per_chi_non_e_admin(self):
        self.anonimo()
        for rotta in ("/_pipeline/api/runs", "/_pipeline/api/indicatori"):
            self.assertEqual(self.client.get(rotta).status_code, 404)

    def test_il_prefisso_pipeline_resta_noindex(self):
        self.admin()
        for rotta in ("/_pipeline/api/runs", "/_pipeline/console"):
            risposta = self.client.get(rotta)
            self.assertIn("noindex", risposta.headers.get("X-Robots-Tag", ""))

    def test_la_porta_manda_alla_console(self):
        risposta = self.client.get("/_pipeline")
        self.assertEqual(risposta.status_code, 302)
        self.assertTrue(risposta.headers["Location"].endswith("/_pipeline/console"))


if __name__ == "__main__":
    unittest.main()
