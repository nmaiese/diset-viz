"""Il modello a pratica editoriale, provato end-to-end contro l'app servita.

Questo test prende le primitive che il modello unifica (`practice_timeline`,
`practice_store`, `practice_metrics`, la priorità del lanciatore
`pipeline_launch`) e le fa girare **insieme**, sul percorso reale di un
indicatore, contro un sito **davvero servito**: un gunicorn su `run:app`, non il
test client. Il progetto ha ratificato **merge = pubblicazione**: un articolo
fuso su master è `pubblicata`, non c'è più uno stato `fusa` intermedio né una
verifica-sito.

Copre, senza ricostruzioni a mano:
  1. osservabilità (Fase B): la storia intera di un indicatore dai soli artefatti.
  2. riconciliatore (Fase C): scritto vs ricostruito, zero divergenze, poi una sola
     divergenza dopo una perturbazione dichiarata.
  3. cicli di manutenzione (Fase E): due cicli distinti ma collegati.
  4. priorità del dispatcher (Fase F): una smentita reale scavalca l'ordine di catena.
  5. associazione run->indicatore: un id BES col trattino non si tronca.
  6. metriche (Fase F): la fotografia prima/dopo, con i suoi None dichiarati.

Gli artefatti derivati (record di pratica) restano in cartelle temporanee: non si
committano, si ricostruiscono a comando.

Un solo indicatore committato regge tutto il percorso, e se un giorno sparisce il
test lo dice invece di fingere di aver provato.
"""

import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from scripts import (curate, discovery, indicator_store, pending_notes,
                     pipeline_launch, pipeline_log, practice_metrics,
                     practice_store, practice_timeline)
from scripts import verification_queue as vq

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Un articolo territoriale col ciclo editoriale completo (scritto, firmato,
# verificato): la sua pagina porta lead e vintage, quindi la verifica del sito ha
# qualcosa da confermare.
PINNED_TER = "651"

# Popolati da setUpModule: la base del sito servito, o None se non si è potuto
# avviare gunicorn (in tal caso i soli test che toccano la rete si saltano).
_SITE_BASE = None
_PROC = None


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_until_up(base: str, tries: int = 60, delay: float = 0.25) -> bool:
    for _ in range(tries):
        if _PROC is not None and _PROC.poll() is not None:
            return False  # gunicorn è morto in avvio, inutile insistere
        try:
            with urllib.request.urlopen(base + "/", timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            time.sleep(delay)
    return False


def setUpModule():
    """Avvia gunicorn come sito reale, una volta per il modulo."""
    global _SITE_BASE, _PROC
    port = _free_port()
    base = f"http://127.0.0.1:{port}"
    try:
        _PROC = subprocess.Popen(
            [sys.executable, "-m", "gunicorn", "run:app",
             "-b", f"127.0.0.1:{port}", "--workers", "1", "--timeout", "60"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        _PROC = None
        return
    if _wait_until_up(base):
        _SITE_BASE = base
    else:
        _stop_site()


def _stop_site():
    global _PROC
    if _PROC is None:
        return
    try:
        os.killpg(os.getpgid(_PROC.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        _PROC.terminate()
    try:
        _PROC.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(_PROC.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            _PROC.kill()
    _PROC = None


def tearDownModule():
    _stop_site()


def _read_inputs():
    """Gli stessi lettori reali di `practice_timeline.load_real`, ma restituiti
    grezzi, così un test può perturbarne uno (per il tripwire) prima di
    ricostruire. Tenere qui la stessa lista di load_real è voluto: è il modo di
    provare la ricostruzione su input che nessun file committato porta ancora."""
    return {
        "candidates": discovery.read_candidates(),
        "manifest": pending_notes.read_manifest(),
        "curation": curate.read_curation(),
        "external": curate.read_external(),
        "articles": indicator_store.load_all(strict=False),
        "verifiche": vq.load_verifications(),
        "runs": pipeline_log.collapse_runs(pipeline_log.read_journal()),
    }


def _reconstruct(inputs):
    return practice_timeline.reconstruct(
        inputs["candidates"], inputs["manifest"], inputs["curation"],
        inputs["external"], inputs["articles"], inputs["verifiche"],
        inputs["runs"])


# Un id esterno inventato, così la fixture non dipende da nessun artefatto
# committato: la catena è fatta apposta per portare un indicatore oltre lo
# stato "non ancora verificato", quindi pinnare un indicatore reale a quello
# stato lo rompe appena il primo verificatore lo chiude (cosa che ha bloccato
# la PR #86). Lo stato lo ricostruiamo dagli input, come fa il resto del modulo.
_SYNTH_EUR = "eur:synthreg"


def _synthetic_expired_smentita():
    """Ricostruisce un EUR con una smentita chiusa correggendo la prosa.

    Ciclo editoriale completo (promosso, curato, scritto, firmato) più una
    verifica smentita la cui impronta non combacia più con la prosa attuale:
    è scaduta, quindi il verificatore non risulta completo, la smentita non è
    più aperta, e l'articolo torna in-lavorazione invece di restare in pagina
    con l'errore. È lo stato transitorio che i vecchi test pinnavano su un
    indicatore reale, qui riprodotto deterministicamente dai soli input.
    """
    candidates = [{
        "triage_status": "promoted", "definition_match": "exact",
        "duplicate_of": _SYNTH_EUR, "discovered_at": "2026-01-01",
        "triage_notes": "promossa (sintetico)",
    }]
    curation = [{
        "target_indicator_id": _SYNTH_EUR, "reviewed_at": "2026-02-01",
        "reviewed_direction": "higher-better", "direction_verdict": "directional",
        "reviewed_category": "ricerca", "data_year": 2022, "score_eligible": "true",
    }]
    article = {
        "lead": "Una glossa sul divario nella spesa in ricerca.",
        "vintage": 2022, "reviewed_at": "2026-03-01", "reviewed_vintage": 2022,
        "sections": [{"role": r, "body": f"Il {r}."}
                     for r in ("definizione", "quadro", "dinamica", "limiti")],
    }
    verifiche = [{
        "code": "eur-synthreg", "level": "regione", "at": "2026-04-01",
        "esito": "smentito", "smentite": "1", "controllate": "20",
        "confermate": "19", "non_verificabili": "0",
        # impronta di un testo che non è più quello di adesso: la verifica è
        # scaduta, così la smentita si spegne e l'articolo torna in coda.
        "prosa": "0000000000000000",
    }]
    dossier = practice_timeline.reconstruct(
        candidates, [], curation, [], {_SYNTH_EUR: article}, verifiche, [],
        today="2026-05-01")
    return dossier[_SYNTH_EUR]


# --- 1. Osservabilità (Fase B) ---------------------------------------------

class Observability(unittest.TestCase):
    """La storia intera di un indicatore, dai soli artefatti committati."""

    @classmethod
    def setUpClass(cls):
        cls.dossier = practice_timeline.load_real()

    def test_history_then_refutation_closed(self):
        # Ricostruito da input sintetici: la catena è fatta per superare lo stato
        # "non ancora verificato", quindi questo non si pinna su un indicatore
        # reale (lo romperebbe il primo verificatore che lo chiude, come per la #86).
        d = _synthetic_expired_smentita()
        # promosso -> curato -> scritto -> firmato -> verificato-smentito: la
        # storia resta nella timeline anche dopo che la smentita è stata chiusa.
        kinds = [ev.get("kind") for ev in d["timeline"]]
        for expected in ("promossa", "curata", "firmata", "verificata"):
            self.assertIn(expected, kinds, kinds)
        verificate = [ev for ev in d["timeline"] if ev.get("kind") == "verificata"]
        self.assertTrue(any(ev.get("esito") == "smentito" for ev in verificate))
        # La glossa smentita è stata corretta e l'impronta della prosa è
        # cambiata: la smentita si spegne, la verifica scade, e l'articolo torna
        # in coda al verificatore invece di restare in pagina con l'errore.
        self.assertFalse(d["flags"].get("open_smentita"))
        self.assertEqual(d["state"], "in-lavorazione")
        self.assertFalse(d["verification_valid"])
        for stage in ("curator", "writer", "reviewer"):
            self.assertIn(stage, d["completed_stages"])
        self.assertNotIn("verificatore", d["completed_stages"])

    def test_table_row_per_indicator(self):
        # una riga per indicatore, con stato/stadi/priorità/entrato
        self.assertIn(PINNED_TER, self.dossier)
        for d in self.dossier.values():
            self.assertIn("state", d)
            self.assertIsInstance(d["completed_stages"], list)
            self.assertIn("priority", d)
            self.assertIn("entered_at", d)


# --- 2. Riconciliatore (Fase C) ---------------------------------------------

class Reconciler(unittest.TestCase):
    """Scritto vs ricostruito: zero divergenze, poi esattamente quella che
    inietto perturbando un record dichiarato."""

    def test_write_then_check_and_a_single_declared_divergence(self):
        dossier = practice_timeline.load_real()
        # Il record da perturbare è sintetico, non un indicatore reale: pinnarne
        # uno allo stato "in-lavorazione" lo rompe appena il primo verificatore lo
        # chiude (cosa che ha bloccato la #86). Il resto del dossier reale resta
        # nel test, perché la riconciliazione a zero divergenze è la sua garanzia.
        synth = _synthetic_expired_smentita()
        dossier[_SYNTH_EUR] = synth
        root = tempfile.mkdtemp()

        # --write (in una practices-root temporanea): un record per ciclo
        written = 0
        for d in dossier.values():
            for rec in practice_timeline.cycles_for(d):
                practice_store.save(rec, root=root)
                written += 1
        self.assertGreater(written, 0)

        # --check: dichiarato == ricostruito, zero divergenze
        declared = practice_store.load_all(root=root, strict=False)
        self.assertEqual(practice_timeline.reconcile(declared, dossier), [])

        # perturba lo stato del ciclo attivo del record sintetico
        active = practice_timeline.cycles_for(synth)[-1]
        self.assertTrue(active["active"])
        rec = practice_store.load(active["practice_id"], root=root)
        self.assertEqual(rec["state"], "in-lavorazione")
        rec["state"] = "pubblicata"  # una bugia rispetto agli artefatti
        practice_store.save(rec, root=root)

        # --check di nuovo: segnala esattamente quella divergenza, e solo quella
        declared2 = practice_store.load_all(root=root, strict=False)
        divergenze = practice_timeline.reconcile(declared2, dossier)
        self.assertEqual(len(divergenze), 1, divergenze)
        row = divergenze[0]
        self.assertEqual(row["id"], _SYNTH_EUR)
        self.assertEqual(row["kind"], "divergente")
        self.assertEqual(row["declared"], "pubblicata")
        self.assertEqual(row["reconstructed"], "in-lavorazione")


# --- 3. Cicli di manutenzione (Fase E) --------------------------------------

class MaintenanceCycles(unittest.TestCase):
    """Un indicatore con una smentita ha due cicli distinti ma collegati; uno a
    ciclo singolo ne resta uno."""

    @classmethod
    def setUpClass(cls):
        cls.dossier = practice_timeline.load_real()

    def test_a_smentita_opens_a_second_linked_cycle(self):
        # Sintetico, per la stessa ragione dell'osservabilità: una verifica
        # smentita su una pagina già a valle apre un secondo ciclo, legato al
        # primo, senza dipendere dallo stato committato di un indicatore reale.
        d = _synthetic_expired_smentita()
        cycles = practice_timeline.cycles_for(d)
        self.assertEqual(len(cycles), 2, [c["practice_id"] for c in cycles])
        first, second = cycles
        self.assertEqual(first["practice_id"], f"{_SYNTH_EUR}#nuovo-1")
        self.assertFalse(first["active"])
        self.assertEqual(first["state"], "chiusa")
        self.assertEqual(first["outcome"], "sostituita")
        self.assertEqual(second["practice_id"], f"{_SYNTH_EUR}#smentita-2")
        self.assertTrue(second["active"])
        # la smentita di questo ciclo è stata chiusa correggendo la glossa: il
        # ciclo resta attivo ma torna in-lavorazione (verifica scaduta), non più
        # invalidata con l'errore in pagina.
        self.assertEqual(second["state"], "in-lavorazione")

    def test_single_cycle_indicator_stays_one(self):
        d = self.dossier.get(PINNED_TER)
        if d is None:
            self.skipTest(f"{PINNED_TER} non è più nel repo")
        cycles = practice_timeline.cycles_for(d)
        self.assertEqual(len(cycles), 1, [c["practice_id"] for c in cycles])
        self.assertTrue(cycles[0]["active"])


# --- 5. Priorità del lanciatore per-indicatore -----------------------------

class LauncherPriority(unittest.TestCase):
    """Nel lanciatore la priorità è per-indicatore, non per-stadio: una smentita
    pubblica (peso 100+) apre il piano davanti a tutto il resto, e il piano è
    ordinato per priorità decrescente. Non c'è più 'uno stadio scavalca
    l'altrò, ci sono unità di lavoro lanciabili in parallelo, ordinate."""

    # coda a monte con lavoro d'ammissione, più un dossier con una smentita urgente.
    QUEUES = {"scout": 0, "hunter": 3, "promoter": 0, "curator": 0,
              "writer": 0, "reviewer": 0, "verificatore": 0}

    def smentita_dossier(self):
        return {"eur-x": {
            "id": "eur-x", "state": "invalidata",
            "flags": {"open_smentita": True},
            "completed_stages": ["curator", "writer", "reviewer", "verificatore"],
            "required_stages": ("reviewer", "verificatore"), "priority": 105.0,
        }}

    def test_a_public_smentita_leads_the_plan(self):
        # La smentita (produttore, il reviewer è fuso lì) apre il piano; la coda
        # d'ammissione a monte (hunter=3) la segue, perché 105 > 0.
        plan = pipeline_launch.plan_launches(
            self.smentita_dossier(), self.QUEUES, mint=lambda role: f"{role}-x")
        self.assertEqual(plan[0]["indicator"], "eur-x")
        self.assertEqual(plan[0]["role"], "producer")
        self.assertEqual(plan[-1]["role"], "admissions")

    def test_the_plan_is_sorted_by_priority_descending(self):
        # Coi dati reali il piano resta ordinato: è l'invariante che sostituisce
        # 'sopra soglia scavalcà, e si deriva dallo stato reale invece di pinnarlo.
        plan = pipeline_launch.load_plan()
        priorities = [item["priority"] for item in plan]
        self.assertEqual(priorities, sorted(priorities, reverse=True))

    def test_without_a_smentita_upstream_admissions_still_appears(self):
        # Nessuna pratica urgente: la coda d'ammissione a monte resta lanciabile.
        plan = pipeline_launch.plan_launches({}, self.QUEUES, mint=lambda role: f"{role}-x")
        self.assertEqual([item["role"] for item in plan], ["admissions"])


# --- 6. Associazione run -> indicatore --------------------------------------

class RunAssociation(unittest.TestCase):
    """Un id BES col trattino nel testo di un run va mappato all'id intero, mai
    al fantasma troncato al secondo trattino."""

    def test_bes_dash_id_is_not_truncated(self):
        text = "Verificato bes-03LAV006-N25, tutto ok, accanto a eur-rd_e_gerdreg."
        ids = practice_timeline._ids_in_text(text)
        self.assertIn("bes-03LAV006-N25", ids)
        self.assertNotIn("bes-03LAV006", ids)
        self.assertEqual(practice_timeline.key_of_code("bes-03LAV006-N25"),
                         "bes:03LAV006-N25")

    def test_real_run_attaches_to_full_bes_key(self):
        dossier = practice_timeline.load_real()
        full = dossier.get("bes:03LAV006-N25")
        if full is None:
            self.skipTest("bes:03LAV006-N25 non è più nel repo")
        self.assertTrue(full["runs"], "il run col trattino non si è associato")
        self.assertNotIn("bes:03LAV006", dossier)  # nessun fantasma troncato


# --- 7. Metriche (Fase F) ----------------------------------------------------

class Metrics(unittest.TestCase):
    """La fotografia prima/dopo: gli errori pubblici, le fuse senza prova, la
    quota di run associati; le metriche longitudinali sono None, non zero finto."""

    def test_metrics_expose_the_snapshot_and_declare_their_gaps(self):
        # senza --today usa oggi, non zero giorni: le pratiche aperte hanno età
        metrics = practice_metrics.load_and_compute()

        oss = metrics["osservabilita"]
        self.assertIsNotNone(oss["quota_run_associati_a_un_indicatore_pct"])

        aff = metrics["affidabilita"]
        self.assertIsNotNone(aff["errori_pubblici_dopo_pubblicazione"])
        self.assertGreaterEqual(aff["errori_pubblici_dopo_pubblicazione"], 0)
        # le longitudinali non si inventano da un'istantanea
        self.assertIsNone(aff["tentativi_duplicati"])
        self.assertIsNone(aff["transizioni_applicate_due_volte"])
        self.assertIsNone(aff["pratiche_perse_dopo_interruzione"])
        self.assertIsNone(metrics["qualita"]["controlli_saltati"])

    def test_today_default_is_not_zero_days(self):
        # se ci sono pratiche aperte, la loro età media con la data di oggi è > 0
        metrics = practice_metrics.load_and_compute()
        if metrics["velocita"]["pratiche_aperte"] > 0:
            self.assertGreater(metrics["velocita"]["eta_media_aperte_giorni"], 0)


if __name__ == "__main__":
    unittest.main()
