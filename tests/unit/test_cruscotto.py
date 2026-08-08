"""Il lettore dei trascritti: `lab/cruscotto.py`.

Le cartelle di prova si costruiscono qui invece di committare trascritti veri,
che pesano fra i 74 e i 152 KB per agente. Le forme dei record sono quelle
misurate sulla sonda `wf_90bf85dd-65e` e sulle run reali della catena, e stanno
scritte per esteso apposta: se il runtime dei workflow cambiasse formato, il
posto dove accorgersene e' questo file, non una run in produzione.
"""

import json
import os
import re
import shutil
import tempfile
import unittest

from lab import cruscotto

RADICE_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _scrivi(percorso, righe):
    os.makedirs(os.path.dirname(percorso), exist_ok=True)
    with open(percorso, "w", encoding="utf-8") as handle:
        for riga in righe:
            handle.write(json.dumps(riga, ensure_ascii=False) + "\n")


def _turno(agent_id, request_id, uso, testo="ok"):
    """Un record `assistant` come lo scrive Claude Code, con il suo `usage`."""
    return {
        "type": "assistant", "agentId": agent_id, "requestId": request_id,
        "message": {"usage": uso, "content": [{"type": "text", "text": testo}]},
    }


class CartellaFinta:
    """Una radice `~/.claude/projects/<slug>` con dentro una sessione e le run."""

    def __init__(self):
        self.radice = tempfile.mkdtemp(prefix="cruscotto-")
        self.sessione = os.path.join(self.radice, "sessione-01")

    def run(self, run_id):
        return os.path.join(self.sessione, "subagents", "workflows", run_id)

    def meta(self, run_id):
        return os.path.join(self.sessione, "workflows", run_id + ".json")

    def agente(self, run_id, agent_id, agent_type, prompt, turni=(), chiuso=None):
        cartella = self.run(run_id)
        os.makedirs(cartella, exist_ok=True)
        with open(os.path.join(cartella, f"agent-{agent_id}.meta.json"), "w") as handle:
            json.dump({"agentType": agent_type, "spawnDepth": 1}, handle)
        righe = [{"type": "user", "agentId": agent_id,
                  "message": {"content": [{"type": "text", "text": prompt}]}}]
        righe.extend(turni)
        _scrivi(os.path.join(cartella, f"agent-{agent_id}.jsonl"), righe)
        journal = os.path.join(cartella, "journal.jsonl")
        voci = []
        if os.path.exists(journal):
            with open(journal) as handle:
                voci = [json.loads(r) for r in handle if r.strip()]
        voci.append({"type": "started", "key": "v2:" + agent_id, "agentId": agent_id})
        if chiuso is not None:
            voci.append({"type": "result", "key": "v2:" + agent_id,
                         "agentId": agent_id, "result": chiuso})
        _scrivi(journal, voci)

    def chiudi(self, run_id, meta):
        os.makedirs(os.path.dirname(self.meta(run_id)), exist_ok=True)
        with open(self.meta(run_id), "w", encoding="utf-8") as handle:
            json.dump(meta, handle)

    def via(self):
        shutil.rmtree(self.radice, ignore_errors=True)


class PostinoFinto:
    def __init__(self):
        self.mandati = []
        self.stampa = False
        self.acceso = True

    def manda(self, payload):
        self.mandati.append(payload)
        return True

    def azioni(self):
        return [p["action"] for p in self.mandati]


class MappaDelleFasi(unittest.TestCase):
    """La stima della fase e' una mappa sola, e deve coprire il workflow vero.

    Dal vivo la fase non esiste (sta in `<runId>.json`, che compare a run
    finita), quindi si stima dal tipo di agente. Un tipo nuovo senza fase non
    romperebbe niente in modo visibile: la run comparirebbe sul cruscotto senza
    fase, e nessuno collegherebbe le due cose. Qui invece fallisce la suite."""

    def test_ogni_agent_type_del_workflow_ha_una_fase(self):
        percorso = os.path.join(RADICE_REPO, ".claude", "workflows", "indicatore-lite.js")
        with open(percorso, encoding="utf-8") as handle:
            sorgente = handle.read()
        tipi = set(re.findall(r"agentType:\s*['\"]([^'\"]+)['\"]", sorgente))
        self.assertTrue(tipi, "nessun agentType trovato nel workflow: regex da rifare")
        mancanti = sorted(t for t in tipi if t not in cruscotto.FASE_PER_TIPO)
        self.assertEqual(mancanti, [], f"tipi senza fase in FASE_PER_TIPO: {mancanti}")

    def test_ogni_fase_stimata_esiste_nell_ordine(self):
        fuori = sorted(set(cruscotto.FASE_PER_TIPO.values()) - set(cruscotto.ORDINE_FASI))
        self.assertEqual(fuori, [])


class IlVivo(unittest.TestCase):
    """Quello che si legge mentre la run gira, senza `<runId>.json`."""

    def setUp(self):
        self.finta = CartellaFinta()
        self.addCleanup(self.finta.via)
        self.finta.agente(
            "wf_prova", "a1", "lab-dossierista",
            "Esegui bin/py -m lab.dossier ter-13 --out data/lab/dossier",
            chiuso={"dossier": [{"codice": "ter-13", "percorso": "/tmp/ter-13.json"}]})
        self.finta.agente(
            "wf_prova", "a2", "lab-verificatore",
            "Prova a smentire questo articolo dell'indicatore ter-13 di Divario Italia.")

    def test_agenti_aperti_e_chiusi(self):
        vivo = cruscotto.stato_vivo(self.finta.run("wf_prova"))
        per_id = {a["agent_id"]: a for a in vivo["agenti"]}
        self.assertEqual(per_id["a1"]["stato_vivo"], "chiuso")
        self.assertEqual(per_id["a2"]["stato_vivo"], "aperto")
        self.assertEqual(vivo["agenti_visti"], 2)

    def test_il_valore_di_ritorno_arriva_col_chiuso(self):
        vivo = cruscotto.stato_vivo(self.finta.run("wf_prova"))
        chiuso = [a for a in vivo["agenti"] if a["agent_id"] == "a1"][0]
        self.assertEqual(chiuso["risultato"]["dossier"][0]["codice"], "ter-13")

    def test_la_fase_si_stima_dal_tipo(self):
        vivo = cruscotto.stato_vivo(self.finta.run("wf_prova"))
        per_id = {a["agent_id"]: a for a in vivo["agenti"]}
        self.assertEqual(per_id["a1"]["fase_stimata"], "Dossier")
        self.assertEqual(per_id["a2"]["fase_stimata"], "Verifica")
        # La fase della run e' la piu' avanzata fra quelle viste, non l'ultima
        # in ordine di tempo: due scout paralleli non fanno tornare indietro.
        self.assertEqual(vivo["fase_stimata"], "Verifica")

    def test_l_indicatore_viene_dal_prompt(self):
        vivo = cruscotto.stato_vivo(self.finta.run("wf_prova"))
        self.assertEqual({a["indicatore"] for a in vivo["agenti"]}, {"ter-13"})

    def test_un_codice_che_non_e_un_indicatore_non_passa(self):
        self.assertEqual(cruscotto.indicatore_del_prompt("run wf_2bb7c8b6-41f del 2026-08-08"), "")
        self.assertEqual(cruscotto.indicatore_del_prompt("indicatore bes-10AMB002"), "bes-10AMB002")

    def test_senza_runid_json_non_c_e_consuntivo(self):
        self.assertIsNone(cruscotto.consuntivo(self.finta.run("wf_prova"),
                                               self.finta.meta("wf_prova")))


class IlConsuntivo(unittest.TestCase):
    """Quello che si legge quando `<runId>.json` compare, cioe' a run finita."""

    def setUp(self):
        self.finta = CartellaFinta()
        self.addCleanup(self.finta.via)
        uso = {"input_tokens": 10, "output_tokens": 500,
               "cache_creation_input_tokens": 1000, "cache_read_input_tokens": 40000}
        self.finta.agente("wf_fine", "a1", "lab-scrittore",
                          "Scrivi l'articolo dell'indicatore ter-13 di Divario Italia.",
                          turni=[_turno("a1", "req-1", uso), _turno("a1", "req-2", uso)],
                          chiuso={"angolo": "il divario si chiude dall'alto"})
        self.finta.chiudi("wf_fine", {
            "runId": "wf_fine", "workflowName": "indicatore-lite", "args": ["ter-13"],
            "status": "completed", "durationMs": 1234567,
            "result": {"richiesti": 1, "scritti": 1, "fermati": [], "articoli": [
                {"codice": "ter-13", "scritto": True, "sovrascritto": True,
                 "vintage_precedente": 2024, "parole": 782, "giri_di_correzione": 2,
                 "angolo": "il divario si chiude dall'alto", "rilievi_aperti": ["bassa | cifra | lead"]}]},
            "logs": ["ter-13: scritto con 1 rilievi aperti, nessuno grave"],
            "workflowProgress": [
                {"type": "workflow_phase", "index": 1, "title": "Scrittura"},
                {"type": "workflow_agent", "index": 1, "label": "scrivi:ter-13",
                 "phaseTitle": "Scrittura", "agentId": "a1",
                 "agentType": "lab-scrittore", "model": "claude-opus-5", "state": "done"},
            ],
        })
        self.finito = cruscotto.consuntivo(self.finta.run("wf_fine"),
                                           self.finta.meta("wf_fine"))

    def test_la_run_porta_lo_stato_e_le_fasi(self):
        run = self.finito["run"]
        self.assertEqual(run["workflow"], "indicatore-lite")
        self.assertEqual(run["stato"], "completed")
        self.assertEqual(run["fasi"], ["Scrittura"])
        self.assertEqual(run["durata_ms"], 1234567)
        self.assertEqual(run["esito"]["articoli"][0]["vintage_precedente"], 2024)

    def test_l_agente_porta_label_fase_e_modello(self):
        agente = self.finito["agenti"][0]
        self.assertEqual(agente["label"], "scrivi:ter-13")
        self.assertEqual(agente["fase"], "Scrittura")
        self.assertEqual(agente["modello"], "claude-opus-5")
        self.assertEqual(agente["stato"], "done")

    def test_i_turni_si_contano_una_volta_per_richiesta(self):
        # Due `requestId` distinti = due turni. La regola sta in
        # `scripts/baseline_tokens.py` e non e' ricopiata qui.
        self.assertEqual(self.finito["agenti"][0]["turni"], 2)
        self.assertEqual(self.finito["run"]["turni"], 2)
        self.assertEqual(self.finito["run"]["token_out"], 1000)

    def test_il_costo_e_dichiarato_pavimento(self):
        self.assertEqual(self.finito["run"]["costo_pavimento"], 1)
        self.assertGreater(self.finito["run"]["costo"], 0)


class UnaRunRipresa(unittest.TestCase):
    """Lo stesso `runId` sotto due sessioni: misurarne una sola e' meta' run.

    Succede con `resumeFromRunId`: gli agenti replicati da cache restano nella
    cartella vecchia, quelli rigirati stanno nella nuova. E' lo stesso difetto
    che `scripts/baseline_tokens.find_workflow` esiste per chiudere, un piano
    piu' in basso, e qui va chiuso di nuovo perche' la scoperta delle run passa
    da `run_viste` e non da la'."""

    def setUp(self):
        self.finta = CartellaFinta()
        self.addCleanup(self.finta.via)
        uso = {"input_tokens": 5, "output_tokens": 100,
               "cache_creation_input_tokens": 0, "cache_read_input_tokens": 1000}
        self.finta.agente("wf_ripresa", "a1", "lab-dossierista", "dossier di ter-13",
                          turni=[_turno("a1", "req-1", uso)], chiuso={"dossier": []})
        # La seconda sessione, con un agente in piu' e il suo `<runId>.json`.
        self.finta.sessione = os.path.join(self.finta.radice, "sessione-02")
        self.finta.agente("wf_ripresa", "a2", "lab-scrittore", "Scrivi ter-13",
                          turni=[_turno("a2", "req-2", uso)], chiuso={"angolo": "una tesi"})
        self.finta.chiudi("wf_ripresa", {
            "workflowName": "indicatore-lite", "status": "completed",
            "workflowProgress": [
                {"type": "workflow_agent", "label": "scrivi:ter-13",
                 "phaseTitle": "Scrittura", "agentId": "a2", "model": "opus", "state": "done"}],
        })
        self.dove = cruscotto.run_viste(self.finta.radice)["wf_ripresa"]

    def test_le_due_cartelle_stanno_sotto_lo_stesso_run_id(self):
        self.assertEqual(len(self.dove["trascritti"]), 2)

    def test_il_vivo_vede_gli_agenti_di_tutte_e_due(self):
        vivo = cruscotto.stato_vivo(self.dove["trascritti"])
        self.assertEqual({a["agent_id"] for a in vivo["agenti"]}, {"a1", "a2"})
        self.assertEqual(vivo["fase_stimata"], "Scrittura")

    def test_il_consuntivo_somma_tutte_e_due(self):
        finito = cruscotto.consuntivo(self.dove["trascritti"], self.dove["meta"])
        self.assertEqual(finito["run"]["agenti"], 2)
        self.assertEqual(finito["run"]["turni"], 2)

    def test_l_agente_senza_passo_non_esce_con_la_riga_vuota(self):
        # `a1` sta nei file ma non in `workflowProgress`: la riga deve dire chi
        # e', non presentarsi vuota come se il cruscotto fosse rotto. La fase
        # resta nulla, cosi' la vista cade sulla stima e la dichiara tale.
        finito = cruscotto.consuntivo(self.dove["trascritti"], self.dove["meta"])
        per_id = {a["agent_id"]: a for a in finito["agenti"]}
        self.assertIn("lab-dossierista", per_id["a1"]["label"])
        self.assertIsNone(per_id["a1"]["fase"])
        self.assertEqual(per_id["a2"]["fase"], "Scrittura")


class LaRadice(unittest.TestCase):
    """Due condizioni diverse, e confonderle ammazzerebbe la run che conta."""

    def test_la_radice_che_non_si_risolve_e_fatale(self):
        vuota = tempfile.mkdtemp(prefix="senza-progetti-")
        self.addCleanup(shutil.rmtree, vuota, ignore_errors=True)
        salvata = cruscotto.PROJECTS
        cruscotto.PROJECTS = os.path.join(vuota, "non-esiste-*")
        try:
            with self.assertRaises(cruscotto.RadiceMancante):
                cruscotto.radice_progetto(cwd=os.path.join(vuota, "checkout"))
        finally:
            cruscotto.PROJECTS = salvata

    def test_zero_run_dentro_una_radice_risolta_non_e_fatale(self):
        # E' lo stato normale dei primi secondi: il lettore parte prima del
        # workflow. Deve restituire una mappa vuota, non sollevare.
        vuota = tempfile.mkdtemp(prefix="cruscotto-vuota-")
        self.addCleanup(shutil.rmtree, vuota, ignore_errors=True)
        self.assertEqual(cruscotto.run_viste(vuota), {})


class IlGiro(unittest.TestCase):
    """La memoria del poller: si posta quello che cambia, non la storia."""

    def setUp(self):
        self.finta = CartellaFinta()
        self.addCleanup(self.finta.via)
        self.postino = PostinoFinto()
        self.giro = cruscotto.Giro(self.postino, self.finta.radice)

    def test_lo_stesso_stato_non_si_riposta(self):
        self.finta.agente("wf_giro", "a1", "lab-dossierista", "dossier di ter-13")
        self.assertGreater(self.giro.passa(), 0)
        prima = len(self.postino.mandati)
        self.assertEqual(self.giro.passa(), 0)
        self.assertEqual(len(self.postino.mandati), prima)

    def test_un_agente_nuovo_fa_ripartire_il_battito(self):
        self.finta.agente("wf_giro", "a1", "lab-dossierista", "dossier di ter-13")
        self.giro.passa()
        self.finta.agente("wf_giro", "a2", "lab-scout", "Indicatore ter-13, la tua lente")
        self.assertGreater(self.giro.passa(), 0)
        self.assertIn("agente", self.postino.azioni())

    def test_il_consuntivo_parte_da_solo_e_una_volta_sola(self):
        self.finta.agente("wf_giro", "a1", "lab-dossierista", "dossier di ter-13",
                          chiuso={"dossier": []})
        self.giro.passa()
        self.assertNotIn("consuntivo", self.postino.azioni())
        self.finta.chiudi("wf_giro", {"workflowName": "indicatore-lite",
                                      "status": "completed", "workflowProgress": []})
        self.giro.passa()
        self.assertEqual(self.postino.azioni().count("consuntivo"), 1)
        self.giro.passa()
        self.assertEqual(self.postino.azioni().count("consuntivo"), 1)

    def test_il_risultato_lungo_si_tronca(self):
        self.finta.agente("wf_giro", "a1", "lab-scrittore", "Scrivi ter-13",
                          chiuso={"body": "x" * (cruscotto.TETTO_RISULTATO * 2)})
        self.giro.passa()
        agenti = [p for p in self.postino.mandati if p["action"] == "agente"]
        self.assertLessEqual(len(agenti[0]["risultato"]), cruscotto.TETTO_RISULTATO)


class IlRinfrescoDelBattito(unittest.TestCase):
    """Il silenzio del poller non e' il silenzio della run.

    Mentre un agente lavora non cambia niente di leggibile da fuori, quindi
    l'impronta resta identica e la soppressione ferma ogni POST. Ma
    `ultimo_battito` lo stampa il server a ogni POST: senza rinfresco, un turno
    lungo (la norma per chi scrive) faceva leggere la run come `battito fermo`
    mentre il lettore stava benissimo."""

    def setUp(self):
        self.finta = CartellaFinta()
        self.addCleanup(self.finta.via)
        self.postino = PostinoFinto()
        self.adesso = 0.0
        self.giro = cruscotto.Giro(self.postino, self.finta.radice,
                                   orologio=lambda: self.adesso)
        self.finta.agente("wf_rinfresco", "a1", "lab-scrittore", "Scrivi ter-13")

    def test_lo_stato_invariato_si_riposta_a_scadenza(self):
        self.giro.passa()
        self.adesso = cruscotto.RINFRESCO_BATTITO - 1
        self.assertEqual(self.giro.passa(), 0)
        self.adesso = cruscotto.RINFRESCO_BATTITO
        self.assertEqual(self.giro.passa(), 1)
        self.assertEqual(self.postino.azioni().count("run"), 2)

    def test_il_rinfresco_non_riposta_gli_agenti(self):
        """Il costo del monitoraggio deve crescere con quello che succede, non
        con la durata della run: e' la ragione per cui `Giro` ha una memoria."""
        self.giro.passa()
        agenti_prima = self.postino.azioni().count("agente")
        self.adesso = cruscotto.RINFRESCO_BATTITO
        self.giro.passa()
        self.assertEqual(self.postino.azioni().count("agente"), agenti_prima)

    def test_la_scadenza_si_conta_dall_ultimo_invio(self):
        """Anche da un invio partito per un cambio di stato. Contarla dal primo
        battito farebbe scattare il rinfresco quando non serve, e quindi tacere
        piu' a lungo quando serve."""
        self.giro.passa()
        self.adesso = 100.0
        self.finta.agente("wf_rinfresco", "a2", "lab-scout", "Indicatore ter-13, la tua lente")
        self.assertGreater(self.giro.passa(), 0)
        self.adesso = 100.0 + cruscotto.RINFRESCO_BATTITO - 1
        self.assertEqual(self.giro.passa(), 0)
        self.adesso = 100.0 + cruscotto.RINFRESCO_BATTITO
        self.assertEqual(self.giro.passa(), 1)


if __name__ == "__main__":
    unittest.main()
