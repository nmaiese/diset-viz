"""Lo stadio `publisher`: la verifica del sito agganciata al cancello, spenta.

La transizione `fusa -> pubblicata` (docs/EDITORIAL_PRACTICE.md, §8) e' l'unico
stato che la catena non sapeva osservare. Qui si prova che ha ora una coda
deterministica, un perimetro nel cancello e un controllo che impone la prudenza
(una prova non confermata non e' una pubblicazione), **senza** che il dispatcher
lo lanci: `publisher` non e' in `STAGE_ORDER`, quindi la catena di default non
cambia comportamento. Macchina pronta, interruttore spento.
"""

import unittest

from scripts import agent_guard, pipeline_gate, pipeline_status
from scripts import verify_publication as vp


def _dossier(**states):
    """Un dossier sintetico: `{id: {'id', 'state'}}` dai kwargs id=stato."""
    return {ind: {"id": ind, "state": state} for ind, state in states.items()}


class PublicationQueue(unittest.TestCase):
    def test_only_fusa_indicators_are_in_the_queue(self):
        dossier = _dossier(**{
            "651": "fusa",
            "eur:rd_e_gerdreg": "invalidata",
            "dem:NMIGRATEIN": "pubblicata",
            "902": "in-lavorazione",
            "903": "fusa",
        })
        queue = vp.publication_queue(dossier=dossier)
        ids = [row["id"] for row in queue]
        self.assertEqual(ids, ["651", "903"])  # ordinati, solo i fusi
        self.assertEqual(queue[0]["code"], "ter-651")
        self.assertEqual(vp.publication_queue(dossier={}), [])

    def test_stage_report_has_the_pipeline_status_shape(self):
        report = vp.stage_report()
        self.assertEqual(report["stage"], "publisher")
        self.assertIsInstance(report["waiting"], int)
        self.assertIn("da_verificare_sul_sito", report["detail"])
        self.assertIn("--all-fusa", report["command"])


class PublicationProblems(unittest.TestCase):
    VALID = {"ter-651": {"abc123"}}

    def test_a_confirmed_anchored_proof_has_no_problems(self):
        proof = {"code": "ter-651", "ok": True, "prosa": "abc123"}
        self.assertEqual(vp.publication_problems(proof, self.VALID), [])

    def test_a_proof_the_check_did_not_confirm_is_refused(self):
        for bad in (False, None):
            proof = {"code": "ter-651", "ok": bad, "prosa": "abc123"}
            problems = vp.publication_problems(proof, self.VALID)
            self.assertTrue(any("ok=" in p for p in problems), (bad, problems))

    def test_a_proof_without_a_code_is_refused(self):
        self.assertEqual(vp.publication_problems({"ok": True}, self.VALID),
                         ["una prova non ha code"])

    def test_a_proof_for_an_unknown_article_is_refused(self):
        proof = {"code": "ter-999", "ok": True, "prosa": "abc123"}
        problems = vp.publication_problems(proof, self.VALID)
        self.assertTrue(any("nessun articolo" in p for p in problems), problems)

    def test_a_stale_fingerprint_is_refused(self):
        # il testo e' cambiato dopo la prova: l'impronta non e' piu' di nessuna
        # versione dell'articolo, e la prova e' di un testo che non e' in pagina
        proof = {"code": "ter-651", "ok": True, "prosa": "vecchia"}
        problems = vp.publication_problems(proof, self.VALID)
        self.assertTrue(any("impronta prosa" in p for p in problems), problems)


class GateWiring(unittest.TestCase):
    def test_publisher_has_a_perimeter_and_a_merge_policy(self):
        self.assertIn("publisher", pipeline_gate.STAGE_PATHS)
        self.assertIn("publisher", pipeline_gate.MERGE_POLICY)
        self.assertEqual(pipeline_gate.STAGE_PATHS["publisher"],
                         (pipeline_gate.PUBLICATIONS, pipeline_gate.RUN_JOURNAL))
        # come il verificatore: cambia numeri/segnali, non prosa, quindi passa dalla CI
        self.assertEqual(pipeline_gate.MERGE_POLICY["publisher"], "checks")
        # e puo' registrare la propria run, come ogni stadio
        self.assertIn(pipeline_gate.RUN_JOURNAL, pipeline_gate.STAGE_PATHS["publisher"])

    def test_the_switch_is_off_the_dispatcher_does_not_see_publisher(self):
        # l'aggancio e' nel cancello, non nell'ordine di catena: il dispatcher
        # legge STAGE_ORDER, quindi di default non lancia mai il publisher
        self.assertNotIn("publisher", pipeline_status.STAGE_ORDER)

    def test_the_guard_enforces_the_publisher_perimeter_too(self):
        # GUARDED_STAGES deriva da STAGE_PATHS, quindi il publisher e' sorvegliato
        self.assertIn("publisher", agent_guard.GUARDED_STAGES)
        ok, _ = agent_guard.path_verdict(
            "data/pipeline/pubblicazioni/ter-651__regione__abc.json", ["publisher"])
        self.assertTrue(ok)
        stray, _ = agent_guard.path_verdict(
            "content/indicators/ter-651.json", ["publisher"])
        self.assertFalse(stray)

    def test_blast_radius_accepts_a_proof_and_rejects_a_stray(self):
        good = pipeline_gate.check_blast_radius(
            "publisher", ["data/pipeline/pubblicazioni/ter-651__regione__abc.json"])
        self.assertTrue(good.ok, good.detail)
        bad = pipeline_gate.check_blast_radius(
            "publisher", ["content/indicators/ter-651.json"])
        self.assertFalse(bad.ok)


if __name__ == "__main__":
    unittest.main()
