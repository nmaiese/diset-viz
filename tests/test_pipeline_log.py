"""Il diario delle run, e il cruscotto che lo mostra.

Il buco che chiudono: una Routine che gira e non produce niente ha lo stesso
aspetto di una Routine che non e' mai partita. E' cosi' che lo scrittore ha
lavorato per settimane su un file morto senza che nessuno se ne accorgesse, e
finche' l'unica traccia di una run resta il commit che produce, quel modo di
fallire resta invisibile per costruzione.

Nessun test qui tocca il diario committato: ognuno scrive in una directory
temporanea.
"""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import pipeline_dashboard, pipeline_log


class TheJournalRecordsWhatWouldOtherwiseVanish(unittest.TestCase):
    def test_a_run_that_produced_nothing_is_still_a_record(self):
        """Il caso che conta di piu'. Una coda vuota e' una risposta, e senza
        questa riga sarebbe indistinguibile da un agente mai partito."""
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs.jsonl"
            pipeline_log.append(
                pipeline_log.build_entry("curator", "nothing", "coda vuota, niente da curare"),
                path=path,
            )
            entries = pipeline_log.read_journal(path)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["outcome"], "nothing")
        self.assertTrue(entries[0]["at"])

    def test_an_unknown_stage_or_outcome_is_refused(self):
        """Il vocabolario e' corto di proposito: un campo libero si riempirebbe
        di sinonimi e l'aggregato diventerebbe illeggibile."""
        with self.assertRaises(SystemExit):
            pipeline_log.build_entry("giornalista", "nothing", "x")
        with self.assertRaises(SystemExit):
            pipeline_log.build_entry("writer", "andata-benino", "x")

    def test_a_corrupt_line_does_not_hide_the_rest(self):
        """E' un registro, non uno schema: la riga dopo vale ancora."""
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs.jsonl"
            path.write_text(
                '{"stage":"writer","outcome":"merged","summary":"ok","at":"2026-07-01T00:00:00"}\n'
                "{ questa riga e rotta\n"
                '{"stage":"reviewer","outcome":"nothing","summary":"niente","at":"2026-07-02T00:00:00"}\n',
                encoding="utf-8",
            )
            entries = pipeline_log.read_journal(path)
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[2]["stage"], "reviewer")

    def test_the_summary_flags_the_runs_worth_looking_at(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs.jsonl"
            for outcome in ("merged", "nothing", "blocked", "stopped"):
                pipeline_log.append(
                    pipeline_log.build_entry("writer", outcome, f"run {outcome}"), path=path
                )
            state = pipeline_log.summarize(pipeline_log.read_journal(path))
        self.assertEqual(state["writer"]["runs"], 4)
        self.assertEqual(state["writer"]["attention"], 2, "blocked e stopped, non merged ne nothing")

    def test_nothing_is_not_a_problem(self):
        """Una coda vuota e' la risposta giusta, non un allarme: se finisse fra i
        casi da guardare, il cruscotto urlerebbe ogni settimana per niente."""
        self.assertNotIn("nothing", pipeline_log.ATTENTION)
        self.assertNotIn("merged", pipeline_log.ATTENTION)

    def test_the_journal_is_append_only_across_runs(self):
        """Due run non si sovrascrivono: e' JSON per riga proprio per questo."""
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs.jsonl"
            pipeline_log.append(pipeline_log.build_entry("hunter", "nothing", "prima"), path=path)
            pipeline_log.append(pipeline_log.build_entry("hunter", "merged", "seconda"), path=path)
            entries = pipeline_log.read_journal(path)
        self.assertEqual([e["summary"] for e in entries], ["prima", "seconda"])


class TheDashboardReadsWithoutBreaking(unittest.TestCase):
    def test_it_renders_over_the_real_repo(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "cruscotto.html"
            written = pipeline_dashboard.render(out)
            page = written.read_text(encoding="utf-8")
        self.assertTrue(page.startswith("<!doctype html>"))
        for stage in pipeline_log.STAGES:
            self.assertIn(stage, page, f"lo stadio {stage} non compare nel cruscotto")

    def test_it_is_self_contained(self):
        """Si apre da file, anche offline: nessuna richiesta esterna, o smette di
        funzionare esattamente quando serve controllare qualcosa."""
        with TemporaryDirectory() as tmp:
            page = pipeline_dashboard.render(Path(tmp) / "c.html").read_text(encoding="utf-8")
        for tag in ("<script", "src=", "@import", "<link"):
            self.assertNotIn(tag, page, f"il cruscotto carica risorse esterne ({tag})")

    def test_chain_commits_are_recognised_by_the_files_they_touch(self):
        """Non dai messaggi ne' dagli autori: un agente puo' scrivere qualunque
        messaggio, ma non puo' uscire dal proprio perimetro senza che il cancello
        lo fermi."""
        commits = pipeline_dashboard.recent_chain_commits(limit=5)
        from scripts import pipeline_gate

        owned = {p for paths in pipeline_gate.STAGE_PATHS.values() for p in paths}
        for commit in commits:
            self.assertTrue(set(commit["files"]) <= owned, commit["sha"])
            self.assertTrue(commit["sha"] and commit["at"])


if __name__ == "__main__":
    unittest.main()
