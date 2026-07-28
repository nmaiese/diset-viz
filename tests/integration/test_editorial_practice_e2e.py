"""Il modello a pratica editoriale, provato end-to-end contro l'app servita.

Questo test prende le primitive che il modello unifica (`practice_timeline`,
`verify_publication`, `practice_store`, `practice_metrics`, la preemption di
`pipeline_dispatch`) e le fa girare **insieme**, sul percorso reale di un
indicatore, contro un sito **davvero servito**: un gunicorn su `run:app`, non il
test client. E' la differenza che conta, perche' la transizione `fusa ->
pubblicata` (docs/EDITORIAL_PRACTICE.md, §8) esiste apposta per distinguere "fuso
su master" da "la pagina pubblica serve questa versione", e la si puo' provare
solo contro una pagina viva.

Copre, senza ricostruzioni a mano:
  1. osservabilita' (Fase B): la storia intera di un indicatore dai soli artefatti.
  2. riconciliatore (Fase C): scritto vs ricostruito, zero divergenze, poi una sola
     divergenza dopo una perturbazione dichiarata.
  3. verifica del sito (Fase D): la prova promuove a `pubblicata`, un cambio di
     prosa la fa scadere (tripwire), un sito irraggiungibile da' `ok=None`.
  4. cicli di manutenzione (Fase E): due cicli distinti ma collegati.
  5. priorita' del dispatcher (Fase F): una smentita reale scavalca l'ordine di catena.
  6. associazione run->indicatore: un id BES col trattino non si tronca.
  7. metriche (Fase F): la fotografia prima/dopo, con i suoi None dichiarati.

Gli artefatti derivati (record di pratica, prove di pubblicazione) restano in
cartelle temporanee: non si committano, si ricostruiscono a comando.

Un solo indicatore committato regge tutto il percorso, e se un giorno sparisce il
test lo dice invece di fingere di aver provato.
"""

import copy
import http.client
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
                     pipeline_dispatch, pipeline_log, practice_metrics,
                     practice_store, practice_timeline)
from scripts import verify_publication as vp
from scripts import verification_queue as vq

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Un articolo territoriale col ciclo editoriale completo (scritto, firmato,
# verificato): la sua pagina porta lead e vintage, quindi la verifica del sito ha
# qualcosa da confermare.
PINNED_TER = "651"
# L'indicatore esterno con due cicli: la storia intera promosso -> curato ->
# firmato -> verificato-smentito, e la smentita poi chiusa correggendo la glossa
# della fonte, cosi' il secondo ciclo e' tornato in-lavorazione (verifica scaduta).
PINNED_EUR = "eur:rd_e_gerdreg"

# Popolati da setUpModule: la base del sito servito, o None se non si e' potuto
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
            return False  # gunicorn e' morto in avvio, inutile insistere
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
    grezzi, cosi' un test puo' perturbarne uno (per il tripwire) prima di
    ricostruire. Tenere qui la stessa lista di load_real e' voluto: e' il modo di
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


def _reconstruct(inputs, proofs=None):
    return practice_timeline.reconstruct(
        inputs["candidates"], inputs["manifest"], inputs["curation"],
        inputs["external"], inputs["articles"], inputs["verifiche"],
        inputs["runs"], verifications_site=proofs)


# --- 1. Osservabilita' (Fase B) ---------------------------------------------

class Observability(unittest.TestCase):
    """La storia intera di un indicatore, dai soli artefatti committati."""

    @classmethod
    def setUpClass(cls):
        cls.dossier = practice_timeline.load_real()

    def test_eur_history_then_refutation_closed(self):
        d = self.dossier.get(PINNED_EUR)
        if d is None:
            self.skipTest(f"{PINNED_EUR} non e' piu' nel repo")
        # promosso -> curato -> scritto -> firmato -> verificato-smentito: la
        # storia resta nel diario anche dopo che la smentita e' stata chiusa.
        kinds = [ev.get("kind") for ev in d["timeline"]]
        for expected in ("promossa", "curata", "firmata", "verificata"):
            self.assertIn(expected, kinds, kinds)
        verificate = [ev for ev in d["timeline"] if ev.get("kind") == "verificata"]
        self.assertTrue(any(ev.get("esito") == "smentito" for ev in verificate))
        # la glossa smentita ("quattro regioni del Nord ... 60%") e' stata
        # corretta (le quattro sono Lombardia, Lazio, Emilia-Romagna e Piemonte,
        # e il Lazio non e' al Nord) e spostata nel corpo: l'impronta della prosa
        # cambia, la smentita si spegne e la verifica scade, cosi' l'articolo
        # torna in coda al verificatore invece di restare in pagina con l'errore.
        self.assertFalse(d["flags"].get("open_smentita"))
        self.assertEqual(d["state"], "in-lavorazione")
        self.assertFalse(d["verification_valid"])
        for stage in ("curator", "writer", "reviewer"):
            self.assertIn(stage, d["completed_stages"])
        self.assertNotIn("verificatore", d["completed_stages"])

    def test_table_row_per_indicator(self):
        # una riga per indicatore, con stato/stadi/priorita'/entrato
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

        # perturba lo stato del ciclo attivo di un record dichiarato
        eur = dossier.get(PINNED_EUR)
        if eur is None:
            self.skipTest(f"{PINNED_EUR} non e' piu' nel repo")
        active = practice_timeline.cycles_for(eur)[-1]
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
        self.assertEqual(row["id"], PINNED_EUR)
        self.assertEqual(row["kind"], "divergente")
        self.assertEqual(row["declared"], "pubblicata")
        self.assertEqual(row["reconstructed"], "in-lavorazione")


# --- 3. Verifica del sito, fusa -> pubblicata (Fase D) -----------------------

class SiteVerificationLive(unittest.TestCase):
    """Contro il gunicorn servito: la forma a solo code 301-reindirizza allo
    slug canonico, la firma lead+vintage combacia, la prova promuove a
    `pubblicata`, un cambio di prosa la fa scadere, un sito giu' da' `ok=None`."""

    def setUp(self):
        if not _SITE_BASE:
            self.skipTest("gunicorn non e' stato avviato in questo ambiente")
        self.entry = indicator_store.read(PINNED_TER)
        if self.entry is None:
            self.skipTest(f"l'articolo {PINNED_TER} non e' piu' nel repo")
        self.code = practice_timeline.code_of(PINNED_TER)
        self.url = vp.build_url(self.code, base=_SITE_BASE)

    def test_code_only_url_301s_to_canonical_slug(self):
        host = _SITE_BASE.split("://", 1)[1]
        conn = http.client.HTTPConnection(host, timeout=10)
        try:
            conn.request("GET", f"/indicatore/{self.code}")
            resp = conn.getresponse()
            location = resp.getheader("Location") or ""
            resp.read()
        finally:
            conn.close()
        self.assertIn(resp.status, (301, 308))
        self.assertIn("/indicatore/", location)
        self.assertIn(self.code, location)

    def test_publication_proof_promotes_to_pubblicata(self):
        # la verifica gira contro la pagina vera, seguendo il 301
        result = vp.verify(self.url, self.entry)
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["snippet_ok"])
        self.assertTrue(result["vintage_ok"])
        result["code"] = self.code

        # la prova, scritta in un registro temporaneo, porta la ricostruzione a
        # `pubblicata`: la transizione e' guidata dall'artefatto, non da una
        # modifica di stato a mano
        root = tempfile.mkdtemp()
        vp.write_proof(vp.build_proof(self.entry, result), root=root)
        d = practice_timeline.load_real(proofs_root=root).get(PINNED_TER)
        self.assertIsNotNone(d)
        self.assertTrue(d["published"])
        self.assertEqual(d["state"], "pubblicata")

    def test_tripwire_prose_change_expires_the_proof(self):
        # scrivo una prova vera (impronta della versione attuale) contro il sito
        result = vp.verify(self.url, self.entry)
        self.assertTrue(result["ok"], result)
        result["code"] = self.code
        root = tempfile.mkdtemp()
        vp.write_proof(vp.build_proof(self.entry, result), root=root)
        proofs = vp.load_proofs(root=root)

        inputs = _read_inputs()
        # baseline: la prova combacia con la prosa committata -> pubblicata
        base = _reconstruct(inputs, proofs=proofs)[PINNED_TER]
        self.assertTrue(base["published"])
        self.assertEqual(base["state"], "pubblicata")

        # il revisore riscrive il lead: l'articolo e la sua verifica prendono una
        # nuova impronta, la prova sul sito resta ancorata alla vecchia. La prova
        # scade: published torna False, lo stato torna `fusa` (non regredisce a
        # in-lavorazione perche' la verifica del contenuto e' stata rifatta).
        tam = copy.deepcopy(inputs)
        tam["articles"][PINNED_TER]["lead"] = \
            "Riscrittura del revisore. " + (tam["articles"][PINNED_TER].get("lead") or "")
        new_fp = vq.prose_fingerprint(tam["articles"][PINNED_TER])
        for row in tam["verifiche"]:
            if row.get("code") == self.code:
                row["prosa"] = new_fp
        after = _reconstruct(tam, proofs=proofs)[PINNED_TER]
        self.assertFalse(after["published"])
        self.assertEqual(after["state"], "fusa")

    def test_unreachable_site_is_none_not_a_pass(self):
        def dead_fetcher(url):
            raise OSError("connessione rifiutata")

        result = vp.verify(self.url, self.entry, fetcher=dead_fetcher)
        # ne' successo ne' fallimento: un controllo che non ha potuto girare non passa
        self.assertIsNone(result["ok"])
        self.assertEqual(result["reason"], "irraggiungibile")
        # e non promuove niente: senza prova la ricostruzione resta non-pubblicata
        self.assertNotEqual(practice_timeline._published_from([], None), True)


# --- 4. Cicli di manutenzione (Fase E) --------------------------------------

class MaintenanceCycles(unittest.TestCase):
    """Un indicatore con una smentita ha due cicli distinti ma collegati; uno a
    ciclo singolo ne resta uno."""

    @classmethod
    def setUpClass(cls):
        cls.dossier = practice_timeline.load_real()

    def test_eur_has_two_linked_cycles(self):
        d = self.dossier.get(PINNED_EUR)
        if d is None:
            self.skipTest(f"{PINNED_EUR} non e' piu' nel repo")
        cycles = practice_timeline.cycles_for(d)
        self.assertEqual(len(cycles), 2, [c["practice_id"] for c in cycles])
        first, second = cycles
        self.assertEqual(first["practice_id"], f"{PINNED_EUR}#nuovo-1")
        self.assertFalse(first["active"])
        self.assertEqual(first["state"], "chiusa")
        self.assertEqual(first["outcome"], "sostituita")
        self.assertEqual(second["practice_id"], f"{PINNED_EUR}#smentita-2")
        self.assertTrue(second["active"])
        # la smentita di questo ciclo e' stata chiusa correggendo la glossa: il
        # ciclo resta attivo ma torna in-lavorazione (verifica scaduta), non piu'
        # invalidata con l'errore in pagina.
        self.assertEqual(second["state"], "in-lavorazione")

    def test_single_cycle_indicator_stays_one(self):
        d = self.dossier.get(PINNED_TER)
        if d is None:
            self.skipTest(f"{PINNED_TER} non e' piu' nel repo")
        cycles = practice_timeline.cycles_for(d)
        self.assertEqual(len(cycles), 1, [c["practice_id"] for c in cycles])
        self.assertTrue(cycles[0]["active"])


# --- 5. Priorita' del dispatcher (Fase F) -----------------------------------

class DispatcherPriority(unittest.TestCase):
    """La priorita' reale (una smentita pesa 100+) scavalca l'ordine di catena,
    ma solo con `priorities` e solo sopra soglia."""

    # hunter (a monte) ha lavoro, reviewer (a valle) ospita la pratica urgente
    QUEUES = {"scout": 0, "hunter": 3, "promoter": 0, "curator": 0,
              "writer": 0, "reviewer": 1, "verificatore": 0}

    def test_above_threshold_preempts_chain_order(self):
        # Una pratica del reviewer sopra la soglia (100, il peso di una smentita
        # pubblica) scavalca il hunter, che a monte avrebbe la precedenza. Il test
        # usa una priorita' sintetica invece della smentita reale su eur: quella e'
        # stata chiusa (glossa corretta), e la logica di preemption va provata con
        # un input controllato, non con lo stato transitorio del repo.
        priorities = {"reviewer": pipeline_dispatch.PREEMPT_THRESHOLD, "hunter": 5.0}
        plan = pipeline_dispatch.decide(queues=self.QUEUES, priorities=priorities)
        self.assertEqual(plan["stage"], "reviewer")
        self.assertIn("urgente", plan["reason"])

    def test_real_priorities_are_consistent_with_the_dispatch(self):
        # Coi dati reali le priorita' restano calcolabili, e l'esito del dispatch
        # si **deriva** dallo stato reale invece di pinnarlo: quando un
        # verificatore registrera' una smentita vera il reviewer salira' sopra
        # soglia, e un test che pinnasse "sotto soglia -> hunter" bloccherebbe
        # proprio il PR del verificatore che introduce quel comportamento.
        priorities = practice_timeline.stage_priorities(practice_timeline.load_real())
        plan = pipeline_dispatch.decide(queues=self.QUEUES, priorities=priorities)
        if priorities.get("reviewer", 0) >= pipeline_dispatch.PREEMPT_THRESHOLD:
            self.assertEqual(plan["stage"], "reviewer")
        else:
            self.assertEqual(plan["stage"], "hunter")

    def test_without_priorities_it_is_pure_chain_order(self):
        plan = pipeline_dispatch.decide(queues=self.QUEUES)
        self.assertEqual(plan["stage"], "hunter")

    def test_below_threshold_keeps_chain_order(self):
        plan = pipeline_dispatch.decide(queues=self.QUEUES,
                                        priorities={"reviewer": 40.0, "hunter": 5.0})
        self.assertEqual(plan["stage"], "hunter")


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
            self.skipTest("bes:03LAV006-N25 non e' piu' nel repo")
        self.assertTrue(full["runs"], "il run col trattino non si e' associato")
        self.assertNotIn("bes:03LAV006", dossier)  # nessun fantasma troncato


# --- 7. Metriche (Fase F) ----------------------------------------------------

class Metrics(unittest.TestCase):
    """La fotografia prima/dopo: gli errori pubblici, le fuse senza prova, la
    quota di run associati; le metriche longitudinali sono None, non zero finto."""

    def test_metrics_expose_the_snapshot_and_declare_their_gaps(self):
        # senza --today usa oggi, non zero giorni: le pratiche aperte hanno eta'
        metrics = practice_metrics.load_and_compute()

        oss = metrics["osservabilita"]
        # Questi due conteggi possono legittimamente essere 0: il passo del sito
        # pubblica l'indicatore fuso e chiude il gap `fusa_senza_prova` (651), e
        # una smentita corretta chiude `errori_pubblici` (eur:rd_e_gerdreg). Il
        # test verifica che le metriche siano esposte e valide, non che il gap
        # esista: pinnarle a >= 1 le accoppiava a uno stato transitorio che la
        # normale operativita' della catena azzera.
        self.assertIsNotNone(oss["fusa_senza_prova_sul_sito"])
        self.assertGreaterEqual(oss["fusa_senza_prova_sul_sito"], 0)
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
        # se ci sono pratiche aperte, la loro eta' media con la data di oggi e' > 0
        metrics = practice_metrics.load_and_compute()
        if metrics["velocita"]["pratiche_aperte"] > 0:
            self.assertGreater(metrics["velocita"]["eta_media_aperte_giorni"], 0)


if __name__ == "__main__":
    unittest.main()
