"""Il join run+token della cronologia (`pipeline_monitor.runs_timeline`).

La cronologia e' la vista che manca al cruscotto: una riga per run, ordinata nel
tempo, col consumo token. Qui si prova, su un diario sintetico e una telemetria
iniettata, che il join e' sul solo `run_id` (conserva ogni run, anche senza
token), che l'indicatore non viene mai inventato dove il testo ne cita due o
zero, e che i totali sommano solo cio' che si puo' sommare senza spartire un
costo fra indicatori di confronto."""

import unittest

from scripts import pipeline_log, pipeline_monitor


def _run(run_id, stage, outcome, at, summary="", detail=None, **extra):
    entry = {"run_id": run_id, "stage": stage, "outcome": outcome, "at": at,
             "summary": summary, "detail": detail or []}
    entry.update(extra)
    return entry


class RunsTimelineTest(unittest.TestCase):
    def setUp(self):
        # Un diario sintetico, iniettato dov'e' letto: niente file, niente git.
        self._runs = [
            _run("r1", "curator", "merged", "2026-01-02T10:00:00+00:00",
                 summary="curatela di dem:NMIGRATEIN", commit="aaa1", pr="10",
                 duration_seconds=120),
            _run("r2", "reviewer", "merged", "2026-01-01T09:00:00+00:00",
                 summary="rilettura di dem:OLDAGEDEPR contro eur:rd_p_persreg"),
            _run("r3", "hunter", "pr-open", "2026-01-03T08:00:00+00:00",
                 summary="triage della coda"),  # nessun id: lista vuota
        ]
        self._orig = pipeline_log.collapse_runs
        pipeline_log.collapse_runs = lambda entries: entries
        self._orig_read = pipeline_log.read_journal
        pipeline_log.read_journal = lambda: self._runs

    def tearDown(self):
        pipeline_log.collapse_runs = self._orig
        pipeline_log.read_journal = self._orig_read

    def test_ordina_per_at_decrescente_e_conserva_ogni_run(self):
        out = pipeline_monitor.runs_timeline({})
        self.assertEqual([r["run_id"] for r in out["runs"]], ["r3", "r1", "r2"])
        self.assertEqual(out["totals"]["runs"], 3)

    def test_token_join_sul_run_id_e_null_quando_manca(self):
        tokens = {"r1": {"tokens": 5000, "indicator": "dem:NMIGRATEIN"}}
        out = pipeline_monitor.runs_timeline(tokens)
        by_id = {r["run_id"]: r for r in out["runs"]}
        self.assertEqual(by_id["r1"]["tokens"], 5000)
        self.assertIsNone(by_id["r2"]["tokens"])  # nessun token: conservata, null
        self.assertIsNone(by_id["r3"]["tokens"])

    def test_indicatore_dal_token_e_preferito_al_testo(self):
        # La telemetria porta il bersaglio vero; il testo r2 ne cita due.
        tokens = {"r1": {"tokens": 5000, "indicator": "dem:NMIGRATEIN"}}
        out = pipeline_monitor.runs_timeline(tokens)
        by_id = {r["run_id"]: r for r in out["runs"]}
        self.assertEqual(by_id["r1"]["indicators"], ["dem:NMIGRATEIN"])

    def test_indicatore_dal_testo_resta_una_lista_mai_una_scelta(self):
        out = pipeline_monitor.runs_timeline({})
        by_id = {r["run_id"]: r for r in out["runs"]}
        self.assertEqual(by_id["r2"]["indicators"],
                         ["dem:OLDAGEDEPR", "eur:rd_p_persreg"])
        self.assertEqual(by_id["r3"]["indicators"], [])  # zero, non inventato

    def test_totali_token_per_indicatore_solo_se_non_ambiguo(self):
        tokens = {
            "r1": {"tokens": 5000, "indicator": "dem:NMIGRATEIN"},
            # r2 ha due indicatori nel testo e nessun bersaglio: i suoi token
            # non si spartiscono fra i due.
            "r2": {"tokens": 8000, "indicator": ""},
        }
        out = pipeline_monitor.runs_timeline(tokens)
        totals = out["totals"]
        self.assertEqual(totals["tokens_by_indicator"], {"dem:NMIGRATEIN": 5000})
        self.assertEqual(totals["tokens_by_stage"], {"curator": 5000, "reviewer": 8000, "hunter": 0})
        self.assertEqual(totals["runs_by_outcome"], {"merged": 2, "pr-open": 1})
        self.assertEqual(totals["tokens_by_day"]["2026-01-02"], 5000)
        self.assertEqual(totals["tokens"], 13000)

    def test_costo_mai_attribuito_da_un_id_di_prosa(self):
        # Il caso del batch di ammissione: telemetria senza bersaglio, ma il
        # diario cita per caso un solo id. Il costo NON e' di quell'indicatore.
        runs = [_run("b1", "promoter", "merged", "2026-02-01T10:00:00+00:00",
                     summary="ammessa la candidatura dem:BIRTHRATE dalla coda")]
        self._orig_read2 = pipeline_log.read_journal
        pipeline_log.read_journal = lambda: runs
        try:
            out = pipeline_monitor.runs_timeline({"b1": {"tokens": 90000, "indicator": ""}})
        finally:
            pipeline_log.read_journal = self._orig_read2
        row = out["runs"][0]
        self.assertEqual(row["indicators"], ["dem:BIRTHRATE"])  # mostrato
        self.assertEqual(row["tokens"], 90000)
        self.assertEqual(out["totals"]["tokens_by_indicator"], {})  # ma non attribuito


if __name__ == "__main__":
    unittest.main()
