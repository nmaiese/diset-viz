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

from app import app, auth, config, editorial_state
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
        # `cache.clear()` svuota Flask-Caching e **non** tocca
        # `synchronized_cache`, che tiene il catalogo per la vita del processo:
        # senza questa riga il primo test che chiede `/api/catalogo` lo congela
        # per tutta la classe e i successivi leggono lo stato del primo.
        editorial_state.cache_clear()

    def tearDown(self):
        config.LEADERBOARD_DB = self._db
        config.PIPELINE_INGEST_TOKEN = self._token
        auth.current_user = self._current_user
        shutil.rmtree(self._tmp, ignore_errors=True)
        cache.clear()
        editorial_state.cache_clear()

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

    def scrivi(self, run_id, esito, avviata):
        """Una run finita che ha prodotto `esito`: battito piu' consuntivo."""
        self.posta({"action": "run", "run_id": run_id, "avviata_il": avviata})
        self.posta({"action": "consuntivo", "run_id": run_id,
                    "run": {"workflow": "indicatore-lite", "stato": "completed",
                            "esito": esito, "costo": 7.0, "costo_pavimento": 1},
                    "agenti": []})

    def catalogo(self):
        self.admin()
        cache.clear()
        editorial_state.cache_clear()
        risposta = self.client.get("/_pipeline/api/catalogo")
        self.assertEqual(risposta.status_code, 200)
        return risposta.get_json()


class LaPresa(CruscottoBase):
    def test_senza_segreto_non_conferma_nemmeno_di_esistere(self):
        for segreto in ("", "sbagliato"):
            self.assertEqual(self.posta({"action": "run", "run_id": "wf_11111111-aa1"}, segreto).status_code, 404)

    def test_azione_sconosciuta_e_400(self):
        self.assertEqual(self.posta({"action": "boh"}).status_code, 400)

    def test_ping_risponde_e_non_scrive_niente(self):
        """Chiedere se la presa e' viva non deve lasciare una run sul cruscotto.

        Prima si chiedeva con un `run` finto, che pero' e' un battito vero:
        lasciava una riga fantasma in cima al cruscotto, senza agenti e per
        sempre in volo, cioe' proprio dove l'occhio va per primo. Una domanda
        non deve avere effetti."""
        risposta = self.posta({"action": "ping"})
        self.assertEqual(risposta.status_code, 200)
        corpo = risposta.get_json()
        self.assertTrue(corpo["ok"])
        # Chi chiama deve poter sapere se quello che sta per mandare verra'
        # capito, invece di scoprirlo mandandolo.
        self.assertIn("consuntivo", corpo["azioni"])
        self.assertEqual(self.runs(), [])

    def test_ping_senza_segreto_e_404(self):
        self.assertEqual(self.posta({"action": "ping"}, "sbagliato").status_code, 404)

    def test_run_senza_id_e_400(self):
        self.assertEqual(self.posta({"action": "run", "run_id": ""}).status_code, 400)

    def test_il_battito_crea_la_run_e_i_suoi_agenti(self):
        self.assertEqual(self.posta({
            "action": "run", "run_id": "wf_11111111-aa1",
            "avviata_il": "2026-08-08T09:00:00+00:00", "fase_stimata": "Verifica",
            "agenti_visti": 2}).status_code, 200)
        self.posta({"action": "agente", "run_id": "wf_11111111-aa1", "agent_id": "a1",
                    "agent_type": "lab-scrittore", "fase_stimata": "Scrittura",
                    "indicatore": "ter-13", "stato_vivo": "chiuso",
                    "risultato": json.dumps({"angolo": "una tesi"})})
        run = self.runs()[0]
        self.assertEqual(run["run_id"], "wf_11111111-aa1")
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
        risposta = self.posta({"action": "agente", "run_id": "wf_11111111-aa1", "agent_id": "a1",
                               "agent_type": "lab-verificatore", "stato_vivo": "aperto",
                               "risultato": None})
        self.assertEqual(risposta.status_code, 200)
        agente = self.runs()[0]["agenti"][0]
        self.assertEqual(agente["stato_vivo"], "aperto")
        self.assertIsNone(agente["risultato"])

    def test_un_battito_parziale_non_azzera_quello_di_prima(self):
        self.posta({"action": "run", "run_id": "wf_11111111-aa1", "sessione": "s-01",
                    "fase_stimata": "Contesto", "agenti_visti": 4})
        self.posta({"action": "run", "run_id": "wf_11111111-aa1", "fase_stimata": "Scrittura"})
        run = self.runs()[0]
        self.assertEqual(run["fase_stimata"], "Scrittura")
        self.assertEqual(run["sessione"], "s-01")
        self.assertEqual(run["agenti_visti"], 4)


class LeDueSorgentiNonSiPestano(CruscottoBase):
    """L'invariante del modello dati, nei due ordini possibili."""

    def battito(self):
        self.posta({"action": "run", "run_id": "wf_11111111-aa1",
                    "avviata_il": "2026-08-08T09:00:00+00:00",
                    "fase_stimata": "Verifica", "agenti_visti": 1})
        self.posta({"action": "agente", "run_id": "wf_11111111-aa1", "agent_id": "a1",
                    "agent_type": "lab-scrittore", "fase_stimata": "Scrittura",
                    "indicatore": "ter-13", "stato_vivo": "chiuso",
                    "risultato": json.dumps({"angolo": "una tesi"})})

    def consuntivo(self):
        self.posta({"action": "consuntivo", "run_id": "wf_11111111-aa1", "run": {
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

    def test_un_articolo_scritto_porta_sovrascritto_e_vintage(self):
        self.scrivi("wf_11111111-aa1", ESITO_CON_SOVRASCRITTURA, "2026-08-08T09:00:00+00:00")
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
        self.scrivi("wf_22222222-bb2", ESITO_FERMATO, "2026-08-08T10:00:00+00:00")
        riga = self.indicatori()[0]
        self.assertEqual(riga["indicatore"], "ter-30")
        self.assertEqual(riga["esito"], "fermato")
        self.assertFalse(riga["scritto"])
        self.assertEqual(riga["motivo"], "smentito 3 volte")
        self.assertIsNone(riga["sovrascritto"])

    def test_le_scritture_stanno_in_ordine_di_tempo(self):
        self.scrivi("wf_11111111-aa1", ESITO_CON_SOVRASCRITTURA, "2026-08-08T09:00:00+00:00")
        self.scrivi("wf_22222222-bb2", ESITO_FERMATO, "2026-08-08T10:00:00+00:00")
        self.assertEqual([r["indicatore"] for r in self.indicatori()], ["ter-30", "ter-13"])

    def test_una_run_in_volo_non_produce_righe(self):
        self.posta({"action": "run", "run_id": "wf_33333333-cc3",
                    "avviata_il": "2026-08-08T11:00:00+00:00"})
        self.assertEqual(self.indicatori(), [])


CHIAVI_RIGA_RUN = {
    "run_id", "workflow", "args", "avviata_il", "ultimo_battito", "fase_stimata",
    "agenti_visti", "sessione", "progetto", "stato", "in_volo", "battito_fermo",
    "durata_ms", "fasi", "esito", "logs", "agenti", "agenti_totali", "turni",
    "tool", "token", "advisor", "costo", "costo_pavimento", "consuntivo_il",
}

CHIAVI_RIGA_CATALOGO = {
    "id", "codice", "nome", "famiglia", "famiglia_label", "tema", "livello",
    "livelli", "predefinito", "anno_dato", "vintage", "arretrato", "lead",
    "mancanti", "scritte", "sezioni", "ruoli", "indicizzabile", "motivo",
    "percorso", "punteggio", "rilievi", "parole", "impronta_prosa", "stato",
    "certezza", "url", "ultima_run", "ultima_run_il",
}

CHIAVI_RIGA_INDICATORE = {
    "run_id", "workflow", "at", "durata_ms", "costo", "costo_pavimento",
    "indicatore", "esito", "scritto", "sovrascritto", "vintage_precedente",
    "percorso", "parole", "impronta_prosa", "angolo", "giri_di_correzione",
    "cifre_verificate", "sezioni", "impaginazione", "rilievi", "rilievi_aperti",
    "motivo", "published_url",
}


class LaFormaDelPayload(CruscottoBase):
    """I tipi dei campi, non solo i loro valori.

    E' il buco da cui e' passato `[object Object]`: `agenti` era **una chiave per
    due cose**, il conteggio intero che scriveva il consuntivo e la lista che
    rileggeva l'API, e il frontend era scritto per leggere il conteggio. Nessun
    test guardava la forma delle risposte, quindi la collisione e' arrivata in
    produzione e si e' vista solo a schermo.

    `assertEqual(set(riga), ATTESI)` e non `assertIn`: un campo in piu' senza
    tipo dichiarato e' esattamente il modo in cui entra il prossimo."""

    def test_agenti_e_una_lista_e_agenti_totali_un_intero(self):
        self.posta({"action": "run", "run_id": "wf_11111111-aa1",
                    "avviata_il": "2026-08-08T09:00:00+00:00"})
        self.posta({"action": "agente", "run_id": "wf_11111111-aa1", "agent_id": "a1",
                    "agent_type": "lab-scrittore", "stato_vivo": "aperto"})
        run = self.runs()[0]
        self.assertIsInstance(run["agenti"], list)
        self.assertIsInstance(run["agenti_totali"], int)
        self.assertEqual(run["agenti_totali"], 1)

    def test_ogni_campo_di_una_riga_run_ha_il_suo_tipo(self):
        self.posta({"action": "run", "run_id": "wf_11111111-aa1",
                    "avviata_il": "2026-08-08T09:00:00+00:00"})
        run = self.runs()[0]
        self.assertEqual(set(run), CHIAVI_RIGA_RUN)
        for campo in ("token", "advisor"):
            self.assertIsInstance(run[campo], dict)
        for campo in ("fasi", "logs", "args", "agenti"):
            self.assertIsInstance(run[campo], list)
        for campo in ("in_volo", "battito_fermo"):
            self.assertIsInstance(run[campo], bool)
        self.assertIsInstance(run["agenti_totali"], int)

    def test_ogni_campo_di_una_riga_di_catalogo_ha_il_suo_tipo(self):
        riga = self.catalogo()["righe"][0]
        self.assertEqual(set(riga), CHIAVI_RIGA_CATALOGO)
        for campo in ("codice", "nome", "famiglia", "livello", "stato", "certezza"):
            self.assertIsInstance(riga[campo], str)
        for campo in ("lead", "arretrato", "predefinito", "indicizzabile"):
            self.assertIsInstance(riga[campo], bool)
        for campo in ("mancanti", "ruoli"):
            self.assertIsInstance(riga[campo], list)
        for campo in ("scritte", "sezioni", "punteggio", "rilievi", "parole", "livelli"):
            self.assertIsInstance(riga[campo], int)

    def test_i_totali_contano_gli_indicatori_e_le_pagine(self):
        """634 indicatori, 668 righe: l'unita' e' la coppia (indicatore,
        livello), come nella coda editoriale. Due unita' diverse per la stessa
        cosa divergono, e il numero che si stampa in cima e' quello che l'utente
        crede di poter confrontare col `--coda`."""
        payload = self.catalogo()
        totali = payload["totali"]
        predefinite = [r for r in payload["righe"] if r["predefinito"]]
        self.assertEqual(totali["indicatori"], len(predefinite))
        self.assertEqual(totali["pagine"], len(payload["righe"]))
        self.assertGreater(totali["pagine"], totali["indicatori"])

    def test_un_indicatore_scritto_da_una_run_e_non_in_linea(self):
        """L'immagine servita porta `content/indicators/` al commit del deploy,
        quindi una run puo' aver scritto un articolo che la pagina non ha
        ancora. E' la sola differenza vera fra "scritto" e "pubblicato" qui."""
        esito = {"richiesti": 1, "scritti": 1, "fermati": [], "articoli": [
            {"codice": "bes-06POL012P", "scritto": True, "parole": 900}]}
        self.scrivi("wf_11111111-aa1", esito, "2026-08-08T09:00:00+00:00")
        righe = {r["codice"]: r for r in self.catalogo()["righe"]}
        riga = righe["bes-06POL012P"]
        self.assertEqual(riga["stato"], "scritto, non in linea")
        self.assertEqual(riga["certezza"], "esatta")

    def test_un_indicatore_che_nessuna_run_ha_toccato_non_finge_certezza(self):
        righe = self.catalogo()["righe"]
        senza = [r for r in righe if r["ultima_run"] is None and r["scritte"]]
        self.assertTrue(senza, "serve almeno un articolo su disco senza run")
        self.assertEqual(senza[0]["stato"], "in linea")
        self.assertEqual(senza[0]["certezza"], "assente")

    def test_ogni_campo_di_una_riga_per_indicatore_ha_il_suo_tipo(self):
        """Anche il ramo `fermati`, che compone la riga a mano da un'altra parte
        del codice: due rami della stessa riga con due forme diverse sono
        `[object Object]` che aspetta il suo turno."""
        self.scrivi("wf_11111111-aa1", ESITO_CON_SOVRASCRITTURA, "2026-08-08T09:00:00+00:00")
        self.scrivi("wf_22222222-bb2", ESITO_FERMATO, "2026-08-08T10:00:00+00:00")
        for riga in self.indicatori():
            self.assertEqual(set(riga), CHIAVI_RIGA_INDICATORE)
            for campo in ("sezioni", "impaginazione", "rilievi", "rilievi_aperti"):
                self.assertIsInstance(riga[campo], list)
            self.assertIsInstance(riga["scritto"], bool)

    def _riga_con_articolo(self):
        righe = [r for r in self.catalogo()["righe"] if r["scritte"] and r["impronta_prosa"]]
        self.assertTrue(righe, "serve almeno un articolo su disco")
        return righe[0]

    def _con_run(self, riga, **voce):
        esito = {"richiesti": 1, "scritti": 1, "fermati": [],
                 "articoli": [{"codice": riga["codice"], "scritto": True, **voce}]}
        self.scrivi("wf_11111111-aa1", esito, "2026-08-08T09:00:00+00:00")
        return {r["codice"]: r for r in self.catalogo()["righe"]}[riga["codice"]]

    def test_l_impronta_decide_e_non_lascia_dubbi(self):
        """Lead piu' `sections[].{role,h,body}`, la stessa funzione dalle due
        parti: `lab.pubblica` la stampa dopo aver scritto, il sito la ricalcola
        dal file servito."""
        riga = self._riga_con_articolo()
        dopo = self._con_run(riga, parole=riga["parole"], impronta_prosa=riga["impronta_prosa"])
        self.assertEqual((dopo["stato"], dopo["certezza"]), ("in linea", "esatta"))

    def test_un_impronta_diversa_e_una_pubblicazione_che_aspetta(self):
        riga = self._riga_con_articolo()
        dopo = self._con_run(riga, parole=riga["parole"], impronta_prosa="0" * 16)
        self.assertEqual((dopo["stato"], dopo["certezza"]),
                         ("scritto, non in linea", "esatta"))

    def test_le_sole_parole_non_sono_una_certezza_alta(self):
        """Le parole dicono **quanto**, non **che cosa**: una riscrittura della
        stessa lunghezza si leggeva `in linea` con certezza `alta` mentre in
        produzione c'era ancora l'altra. Nessuna run registrata prima
        dell'impronta la porta, quindi questo ramo resta, ma dichiara quanto sa.
        """
        riga = self._riga_con_articolo()
        dopo = self._con_run(riga, parole=riga["parole"])
        self.assertEqual((dopo["stato"], dopo["certezza"]), ("in linea", "debole"))

    def test_un_conteggio_diverso_invece_e_una_prova(self):
        riga = self._riga_con_articolo()
        dopo = self._con_run(riga, parole=riga["parole"] + 1)
        self.assertEqual((dopo["stato"], dopo["certezza"]),
                         ("scritto, non in linea", "alta"))


class IlCruscottoNonContaPagineCheNonEsistono(CruscottoBase):
    """La console contro la sitemap servita, che e' l'incrocio che vale.

    Non la proiezione contro se stessa: con un proprietario solo quella prova e'
    tautologica e passerebbe anche col difetto dentro. Qui si confronta **quello
    che la console dice** con **quello che il sito pubblica**, cosi' il giorno in
    cui qualcuno ricalcola l'indicizzabilita' da un'altra parte per comodita' del
    cruscotto, il conto non torna. E' successo: una copia in `app/views.py`
    contava indicizzabili `dem:LIFEEXP65F` e `dem:LIFEEXP65M`, due varianti di
    genere che la sitemap non elenca."""

    def test_ogni_riga_in_indice_ha_la_sua_riga_in_sitemap(self):
        xml = self.client.get("/sitemap.xml").get_data(as_text=True)
        pubblicate = {pezzo.split("</loc>")[0].split("/indicatore/")[1]
                      for pezzo in xml.split("<loc>")[1:] if "/indicatore/" in pezzo}
        self.assertTrue(pubblicate)
        for riga in self.catalogo()["righe"]:
            if not riga["indicizzabile"] or not riga["predefinito"]:
                continue
            coda = riga["percorso"].split("/indicatore/")[1]
            self.assertIn(coda, pubblicate,
                          f"{riga['codice']} conta come in indice ma non e' in sitemap")

    def test_il_totale_in_indice_non_supera_le_pagine_pubblicate(self):
        xml = self.client.get("/sitemap.xml").get_data(as_text=True)
        pubblicate = sum(1 for pezzo in xml.split("<loc>")[1:] if "/indicatore/" in pezzo)
        self.assertLessEqual(self.catalogo()["totali"]["indicizzabili"], pubblicate)


class LaFormaDelRunId(CruscottoBase):
    """La forma e' quella del contratto, e non una dedotta dai campioni.

    L'ingest accettava qualunque stringa, quindi una riga vuota o
    `[object Object]` diventavano una run. La forma la dichiara lo strumento
    Workflow per `resumeFromRunId`, `^wf_[a-z0-9-]{6,}$`, e si prende
    **verbatim**: pretendere in piu' il trattino che ogni runId visto finora ha
    rifiuterebbe `wf_abcdef`, che il contratto ammette, e la rifiuterebbe in
    silenzio, perche' il `Postino` inghiotte il 400. Perdere il monitoraggio di
    una run vera e' peggio che accettare una riga finta.

    Quindi la forma **non separa** `wf_precheck` da un runId legale: quella
    difesa e' il `ping`, che risponde senza scrivere, piu' `battito_fermo`, che
    toglie dal posto d'onore una riga che nessuno rinfresca."""

    def test_una_stringa_che_non_e_un_run_id_e_rifiutata(self):
        for finto in ("", "precheck", "wf_", "wf_abc", "wf_abc def",
                      "[object Object]", "WF_239AD8CE-AF7", "wf_239ad8ce-af7/../x"):
            self.assertEqual(self.posta({"action": "run", "run_id": finto}).status_code, 400,
                             f"accettato come run_id: {finto!r}")
        self.assertEqual(self.runs(), [])

    def test_un_run_id_vero_passa(self):
        """Tutto quello che il contratto ammette: **lettere oltre la f** (non e'
        esadecimale), e nessun trattino obbligatorio."""
        for vero in ("wf_239ad8ce-af7", "wf_2bb7c8b6-41f", "wf_zzzzzzzz-ppp", "wf_abcdef"):
            self.assertEqual(self.posta({"action": "run", "run_id": vero}).status_code, 200,
                             f"rifiutato un run_id legale: {vero!r}")
        self.assertEqual(len(self.runs()), 4)

    def test_anche_agente_e_consuntivo_rifiutano(self):
        self.assertEqual(self.posta(
            {"action": "agente", "run_id": "wf_", "agent_id": "a1"}).status_code, 400)
        self.assertEqual(self.posta(
            {"action": "consuntivo", "run_id": "wf_", "run": {}, "agenti": []}).status_code, 400)
        self.assertEqual(self.runs(), [])


class IlBattitoCheSiFerma(CruscottoBase):
    def test_una_run_che_non_batte_da_un_pezzo_non_e_piu_in_volo(self):
        """Quello che si osserva e' che **il lettore ha smesso di battere**, non
        che la run sia finita: il lettore muore anche mentre la run e' viva,
        basta che la run superi il `--per` del poller. Il campo si chiama cosi',
        e la console lo scrive per esteso, perche' dire "interrotta" sarebbe la
        stessa bugia gia' riparata una volta."""
        self.posta({"action": "run", "run_id": "wf_11111111-aa1",
                    "avviata_il": "2026-08-08T09:00:00+00:00"})
        run = self.runs()[0]
        self.assertTrue(run["in_volo"])
        self.assertFalse(run["battito_fermo"])

        from datetime import datetime, timedelta, timezone
        from app import pipeline_store
        vecchio = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(timespec="seconds")
        pipeline_store.registra_run("wf_11111111-aa1", {}, now=vecchio)
        run = self.runs()[0]
        self.assertTrue(run["in_volo"])
        self.assertTrue(run["battito_fermo"])

    def test_il_ping_dice_quante_run_sono_aperte(self):
        """Un controllo che risponde solo `ok` conferma il segreto e nient'altro,
        quindi chi lo chiama non ha nessun motivo di preferirlo a una `run`
        finta."""
        self.posta({"action": "run", "run_id": "wf_11111111-aa1",
                    "avviata_il": "2026-08-08T09:00:00+00:00"})
        stato = self.posta({"action": "ping"}).get_json()["stato"]
        self.assertEqual(stato["db"], "su")
        self.assertEqual(stato["aperte"], 1)
        self.assertEqual(stato["ultima"]["run_id"], "wf_11111111-aa1")

    def test_col_database_giu_il_ping_lo_dice_invece_di_dire_zero(self):
        """Zero run e database irraggiungibile non devono uscire uguali.

        `run()` inghiotte l'errore e torna `[]`, che per una pagina e' giusto
        (il cruscotto resta vuoto invece di cadere) e per un controllo pre-run
        e' una bugia: chi sta per spendere sette dollari leggerebbe "presa sana,
        nessuna run" da una presa che non scrive niente."""
        from app import pipeline_store
        vero = pipeline_store.db_vivo
        pipeline_store.db_vivo = lambda: False
        try:
            stato = self.posta({"action": "ping"}).get_json()["stato"]
        finally:
            pipeline_store.db_vivo = vero
        self.assertEqual(stato["db"], "giu")
        self.assertIsNone(stato["run"])


class IlConfine(CruscottoBase):
    def test_le_tre_api_sono_404_per_chi_non_e_admin(self):
        self.anonimo()
        for rotta in ("/_pipeline/api/runs", "/_pipeline/api/indicatori",
                      "/_pipeline/api/catalogo"):
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
