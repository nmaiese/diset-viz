"""La ricostruzione della storia per indicatore (Fase B) e la riconciliazione
dichiarato-vs-osservato (Fase C), su artefatti sintetici.

Il nucleo `reconstruct` e' puro: gli si passano i registri gia' letti, cosi' il
test non tocca disco ne' app.
"""

import unittest

from scripts import practice_timeline as t
from scripts import verification_queue


def _article(key, vintage, reviewed_at=None, reviewed_vintage=None, complete=True):
    roles = ("definizione", "quadro", "dinamica", "limiti") if complete else ("definizione",)
    entry = {
        "key": key,
        "lead": f"Lead di {key}.",
        "vintage": vintage,
        "sections": [{"role": r, "h": None, "body": f"Corpo {r}."} for r in roles],
    }
    if reviewed_at:
        entry["reviewed_at"] = reviewed_at
        entry["reviewed_vintage"] = reviewed_vintage
    return entry


def _verifica(code, entry, esito="pulito", smentite=0, at="2026-07-27"):
    return {
        "code": code, "level": "regione", "at": at,
        "prosa": verification_queue.prose_fingerprint(entry),
        "esito": esito, "smentite": str(smentite),
        "controllate": "10", "confermate": str(10 - smentite),
        "non_verificabili": "0", "vintage": str(entry["vintage"]),
    }


class Reconstruct(unittest.TestCase):
    def _run(self, **kw):
        base = dict(candidates=[], manifest=[], curation=[], external=[],
                    articles={}, verifiche=[], runs=[], today="2026-07-28")
        base.update(kw)
        return t.reconstruct(**base)

    def test_new_external_full_cycle_is_published(self):
        art = _article("dem:NMIGRATEIN", 2024, "2026-07-26", 2024)
        d = self._run(
            manifest=[{"target_indicator_id": "dem:NMIGRATEIN", "status": "integrated",
                       "new_year": "2024"}],
            curation=[{"target_indicator_id": "dem:NMIGRATEIN", "reviewed_at": "2026-07-25",
                       "reviewed_direction": "higher_better", "direction_verdict": "corretto",
                       "reviewed_category": "lavoro_opportunita", "score_eligible": "true",
                       "data_year": "2024"}],
            external=[{"target_indicator_id": "dem:NMIGRATEIN", "year": "2024"}],
            articles={"dem:NMIGRATEIN": art},
            verifiche=[_verifica("dem-NMIGRATEIN", art)],
        )["dem:NMIGRATEIN"]
        self.assertEqual(d["state"], "pubblicata")  # merge = pubblicazione
        self.assertTrue(d["score_eligible"])
        self.assertTrue(d["verification_valid"])
        self.assertTrue(d["published"])  # fuso su master

    def test_open_refutation_is_invalidata_and_ranks_top(self):
        art = _article("eur:rd_e_gerdreg", 2023, "2026-07-26", 2023)
        d = self._run(
            manifest=[{"target_indicator_id": "eur:rd_e_gerdreg", "status": "integrated"}],
            curation=[{"target_indicator_id": "eur:rd_e_gerdreg", "reviewed_at": "2026-07-24",
                       "reviewed_direction": "higher_better", "direction_verdict": "confermato",
                       "reviewed_category": "ricerca", "score_eligible": "true", "data_year": "2023"}],
            external=[{"target_indicator_id": "eur:rd_e_gerdreg", "year": "2023"}],
            articles={"eur:rd_e_gerdreg": art},
            verifiche=[_verifica("eur-rd_e_gerdreg", art, esito="smentito", smentite=1)],
        )["eur:rd_e_gerdreg"]
        self.assertEqual(d["state"], "invalidata")
        self.assertEqual(d["error_class"], "editoriale")
        self.assertTrue(d["flags"]["open_smentita"])
        self.assertGreater(d["priority"], 100)

    def test_rejected_candidate_is_closed_terminal(self):
        d = self._run(candidates=[{
            "candidate_id": "istat_demografia:DEPENDRATE", "source": "istat_demografia",
            "source_indicator_id": "DEPENDRATE", "definition_match": "compatible",
            "duplicate_of": "dem:OLDAGEDEPR", "triage_status": "rejected",
            "triage_notes": "Duplica OLDAGEDEPR.", "discovered_at": "2026-07-01"}])
        # punta a dem:OLDAGEDEPR via duplicate_of
        d = d["dem:OLDAGEDEPR"]
        self.assertEqual(d["state"], "chiusa")
        self.assertEqual(d["error_class"], "terminale")

    def test_needs_info_candidate_is_blocked_external_change(self):
        d = self._run(candidates=[{
            "candidate_id": "eurostat_regional:foo", "source": "eurostat_regional",
            "source_indicator_id": "foo", "definition_match": "new", "duplicate_of": "",
            "triage_status": "needs-info", "triage_notes": "DSD non verificabile.",
            "discovered_at": "2026-07-01"}])["eur:foo"]
        self.assertEqual(d["state"], "in-attesa")
        self.assertEqual(d["motivo"], "dipendenza-esterna")
        self.assertEqual(d["error_class"], "ripetibile-dopo-cambio-esterno")

    def test_stale_vintage_is_invalidata(self):
        art = _article("dem:OLDAGEDEPR", 2024, "2026-07-01", 2023)  # firmata sul 2023, ora 2024
        d = self._run(
            manifest=[{"target_indicator_id": "dem:OLDAGEDEPR", "status": "integrated"}],
            curation=[{"target_indicator_id": "dem:OLDAGEDEPR", "reviewed_at": "2026-07-01",
                       "reviewed_direction": "contextual", "direction_verdict": "confermato",
                       "reviewed_category": "salute", "score_eligible": "false", "data_year": "2024"}],
            external=[{"target_indicator_id": "dem:OLDAGEDEPR", "year": "2024"}],
            articles={"dem:OLDAGEDEPR": art},
        )["dem:OLDAGEDEPR"]
        self.assertEqual(d["state"], "invalidata")
        self.assertEqual(d["error_class"], "cambiamento-in-corsa")
        self.assertTrue(d["flags"]["stale_vintage"])

    def test_territorial_backbone_needs_no_curator(self):
        art = _article("651", 2023, "2026-07-27", 2023)
        d = self._run(
            articles={"651": art},
            verifiche=[_verifica("ter-651", art)],
        )["651"]
        self.assertNotIn("curator", d["required_stages"])
        self.assertEqual(d["state"], "pubblicata")  # writer+reviewer+verificatore, ciclo pieno = fuso su master

    def test_run_is_associated_to_the_indicator_it_names(self):
        d = self._run(runs=[{
            "run_id": "curator-20260726", "stage": "curator", "at": "2026-07-26",
            "summary": "dem:NMIGRATEIN curato: verso higher_better", "detail": [], "pr": "43",
            "outcome": "merged"}])
        self.assertIn("curator-20260726", d["dem:NMIGRATEIN"]["runs"])

    def test_hyphenated_bes_id_in_run_text_is_not_truncated(self):
        # bes-03LAV006-N25 non deve diventare il fantasma bes:03LAV006 (review #1)
        d = self._run(runs=[{
            "run_id": "writer-1", "stage": "writer", "at": "2026-07-27",
            "summary": "Scritto bes-03LAV006-N25", "detail": [], "pr": "", "outcome": "merged"}])
        self.assertIn("bes:03LAV006-N25", d)
        self.assertNotIn("bes:03LAV006", d)
        self.assertIn("writer-1", d["bes:03LAV006-N25"]["runs"])

    def test_stale_verification_reopens_the_verifier_stage(self):
        # la prosa e' cambiata dopo la verifica: l'impronta non combacia piu'
        art = _article("dem:Y", 2024, "2026-07-26", 2024)
        stale = {"code": "dem-Y", "level": "regione", "at": "2026-07-01",
                 "prosa": "impronta_vecchia", "esito": "pulito", "smentite": "0",
                 "vintage": "2024"}
        d = self._run(
            manifest=[{"target_indicator_id": "dem:Y", "status": "integrated"}],
            curation=[{"target_indicator_id": "dem:Y", "reviewed_at": "2026-07-25",
                       "reviewed_direction": "higher_better", "direction_verdict": "corretto",
                       "reviewed_category": "x", "score_eligible": "true", "data_year": "2024"}],
            external=[{"target_indicator_id": "dem:Y", "year": "2024"}],
            articles={"dem:Y": art}, verifiche=[stale],
        )["dem:Y"]
        self.assertFalse(d["verification_valid"])
        self.assertNotIn("verificatore", d["completed_stages"])  # scaduta, non completa
        self.assertNotEqual(d["state"], "fusa")
        self.assertEqual(t.ready_stage(d), "verificatore")       # torna al verificatore

    def test_stale_refutation_is_not_open(self):
        # una vecchia smentita la cui prosa e' stata riscritta non e' piu' aperta (review #4)
        art = _article("dem:Z", 2024, "2026-07-26", 2024)
        stale_smentita = {"code": "dem-Z", "level": "regione", "at": "2026-07-01",
                          "prosa": "impronta_vecchia", "esito": "smentito", "smentite": "1",
                          "vintage": "2024"}
        d = self._run(articles={"dem:Z": art}, verifiche=[stale_smentita])["dem:Z"]
        self.assertFalse(d["flags"].get("open_smentita"))

    def test_a_complete_cycle_on_master_is_published(self):
        # Merge = pubblicazione: un articolo completo e committato (= su master)
        # con il ciclo obbligatorio chiuso e' `pubblicata`, senza verifica-sito.
        art = _article("651", 2023, "2026-07-27", 2023)
        d = self._run(
            articles={"651": art},
            verifiche=[_verifica("ter-651", art)],
        )["651"]
        self.assertEqual(d["state"], "pubblicata")
        self.assertTrue(d["published"])


def _dossier(timeline, **kw):
    base = dict(id="dem:X", type="nuovo", state="in-lavorazione", entered_at="2026-01-01",
                completed_stages=[], required_stages=["writer", "reviewer", "verificatore"],
                flags={}, error_class=None, score_eligible=False, published=None,
                verification_valid=None, runs=[], priority=0.0, timeline=timeline)
    base.update(kw)
    return base


def _ev(at, kind, **extra):
    e = {"at": at, "stage": "", "kind": kind, "detail": ""}
    e.update(extra)
    return e


class Cycles(unittest.TestCase):
    def test_one_cycle_when_no_trigger(self):
        d = _dossier([_ev("2026-01-01", "scritta", vintage=2023),
                      _ev("2026-01-02", "firmata")], state="fusa")
        cy = t.cycles_for(d)
        self.assertEqual(len(cy), 1)
        self.assertEqual((cy[0]["type"], cy[0]["seq"], cy[0]["active"]), ("nuovo", 1, True))
        self.assertEqual(cy[0]["state"], "fusa")

    def test_refutation_opens_a_second_linked_cycle(self):
        d = _dossier([
            _ev("2026-01-01", "scritta", vintage=2023),
            _ev("2026-01-02", "firmata"),
            _ev("2026-01-03", "verificata", esito="smentito"),
        ], state="invalidata", flags={"open_smentita": True})
        cy = t.cycles_for(d)
        self.assertEqual([(c["type"], c["seq"]) for c in cy], [("nuovo", 1), ("smentita", 2)])
        self.assertEqual(cy[0]["state"], "chiusa")
        self.assertEqual(cy[0]["outcome"], "sostituita")
        self.assertTrue(cy[1]["active"])
        self.assertEqual(cy[1]["state"], "invalidata")
        # collegati: stesso indicatore, sequenza che cresce
        self.assertEqual({c["indicator_id"] for c in cy}, {"dem:X"})

    def test_a_second_curation_opens_an_update_cycle(self):
        d = _dossier([
            _ev("2026-01-01", "curata"),
            _ev("2026-01-02", "firmata"),
            _ev("2027-01-01", "curata"),
        ], state="in-lavorazione")
        cy = t.cycles_for(d)
        self.assertEqual([c["type"] for c in cy], ["nuovo", "aggiornamento"])

    def test_a_newer_vintage_rewrite_opens_an_update_cycle(self):
        d = _dossier([
            _ev("2026-01-01", "scritta", vintage=2023),
            _ev("2026-01-02", "firmata"),
            _ev("2027-01-01", "scritta", vintage=2024),
        ])
        cy = t.cycles_for(d)
        self.assertEqual([c["type"] for c in cy], ["nuovo", "aggiornamento"])

    def test_active_record_persists_the_wait_motivo(self):
        # Il record serializzato deve portare il motivo, o `in-attesa` perde
        # l'urgenza (una sosta normale vs un blocco esterno diventano uguali).
        d = _dossier([], state="in-attesa", motivo="dipendenza-esterna",
                     error_class="ripetibile-dopo-cambio-esterno")
        rec = t.cycles_for(d)[-1]
        self.assertTrue(rec["active"])
        self.assertEqual(rec["motivo"], "dipendenza-esterna")

    def test_empty_timeline_is_one_active_cycle(self):
        cy = t.cycles_for(_dossier([]))
        self.assertEqual(len(cy), 1)
        self.assertTrue(cy[0]["active"])


class ReadyStage(unittest.TestCase):
    def test_refutation_waits_on_reviewer(self):
        self.assertEqual(t.ready_stage(_dossier([], state="invalidata",
                         flags={"open_smentita": True})), "reviewer")

    def test_stale_curation_waits_on_curator(self):
        self.assertEqual(t.ready_stage(_dossier([], state="invalidata",
                         flags={"stale_curation": True})), "curator")

    def test_proposal_waits_on_promoter(self):
        self.assertEqual(t.ready_stage(_dossier([], state="proposta")), "promoter")

    def test_in_progress_waits_on_next_required(self):
        d = _dossier([], completed_stages=["writer"])
        self.assertEqual(t.ready_stage(d), "reviewer")

    def test_blocked_and_published_are_not_dispatchable(self):
        self.assertIsNone(t.ready_stage(_dossier([], state="in-attesa", flags={"needs_info": True})))
        self.assertIsNone(t.ready_stage(_dossier([], state="pubblicata")))

    def test_stage_priorities_takes_the_max_per_stage(self):
        a = _dossier([], state="invalidata", flags={"open_smentita": True}, priority=120.0, id="a")
        b = _dossier([], completed_stages=["writer"], priority=10.0, id="b")
        c = _dossier([], completed_stages=["writer"], priority=45.0, id="c")
        pri = t.stage_priorities({"a": a, "b": b, "c": c})
        self.assertEqual(pri["reviewer"], 120.0)   # la pratica 'a', smentita, domina
        # b e c aspettano entrambe il reviewer: il massimo e' comunque 'a'
        self.assertNotIn("writer", pri)


class Recovery(unittest.TestCase):
    """Fase F: la ripresa dopo un'interruzione. La ricostruzione e' una funzione
    pura degli artefatti committati, quindi rieseguirla dopo una sessione
    interrotta da' lo stesso risultato: nessuno stato vive solo nella sessione."""

    def _inputs(self):
        art = _article("dem:X", 2024, "2026-07-26", 2024)
        return dict(candidates=[], manifest=[
            {"target_indicator_id": "dem:X", "status": "integrated", "new_year": "2024"}],
            curation=[{"target_indicator_id": "dem:X", "reviewed_at": "2026-07-25",
                       "reviewed_direction": "higher_better", "direction_verdict": "corretto",
                       "reviewed_category": "x", "score_eligible": "true", "data_year": "2024"}],
            external=[{"target_indicator_id": "dem:X", "year": "2024"}],
            articles={"dem:X": art}, verifiche=[_verifica("dem-X", art)], runs=[],
            today="2026-07-28")

    def test_reconstruction_is_deterministic(self):
        a = t.reconstruct(**self._inputs())["dem:X"]
        b = t.reconstruct(**self._inputs())["dem:X"]
        self.assertEqual((a["state"], a["published"], a["priority"]),
                         (b["state"], b["published"], b["priority"]))

    def test_rewriting_the_records_twice_is_idempotent(self):
        d = t.reconstruct(**self._inputs())["dem:X"]
        first = [r["practice_id"] for r in t.cycles_for(d)]
        second = [r["practice_id"] for r in t.cycles_for(d)]
        self.assertEqual(first, second)


class Reconcile(unittest.TestCase):
    def _reconstructed(self):
        art = _article("651", 2023, "2026-07-27", 2023)
        return t.reconstruct(candidates=[], manifest=[], curation=[], external=[],
                             articles={"651": art}, verifiche=[_verifica("ter-651", art)],
                             runs=[], today="2026-07-28")

    def test_matching_declaration_has_no_divergence(self):
        rec = self._reconstructed()
        declared = {t._dossier_to_record(rec["651"])["practice_id"]: t._dossier_to_record(rec["651"])}
        self.assertEqual(t.reconcile(declared, rec), [])

    def test_declared_drift_is_reported(self):
        rec = self._reconstructed()
        record = t._dossier_to_record(rec["651"])
        record["state"] = "in-lavorazione"  # dichiara in corso cio' che gli artefatti dicono pubblicato
        div = t.reconcile({record["practice_id"]: record}, rec)
        self.assertEqual(len(div), 1)
        self.assertEqual(div[0]["kind"], "divergente")
        self.assertEqual(div[0]["reconstructed"], "pubblicata")

    def test_missing_declaration_is_reported(self):
        rec = self._reconstructed()
        div = t.reconcile({}, rec)
        self.assertEqual(div[0]["kind"], "mancante")


if __name__ == "__main__":
    unittest.main()
