"""Il diario delle run, e il cruscotto che lo mostra.

Il buco che chiudono: una Routine che gira e non produce niente ha lo stesso
aspetto di una Routine che non è mai partita. È così che lo scrittore ha
lavorato per settimane su un file morto senza che nessuno se ne accorgesse, e
finché l'unica traccia di una run resta il commit che produce, quel modo di
fallire resta invisibile per costruzione.

Nessun test qui tocca il diario committato: ognuno scrive in una directory
temporanea.
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from scripts import pipeline_dashboard, pipeline_log, pipeline_status

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TheJournalRecordsWhatWouldOtherwiseVanish(unittest.TestCase):
    def test_a_run_that_produced_nothing_is_still_a_record(self):
        """Il caso che conta di più. Una coda vuota è una risposta, e senza
        questa riga sarebbe indistinguibile da un agente mai partito."""
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs.jsonl"
            pipeline_log.append(
                pipeline_log.build_entry("admissions", "nothing", "coda vuota, niente da curare"),
                path=path,
            )
            entries = pipeline_log.read_journal(path)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["outcome"], "nothing")
        self.assertTrue(entries[0]["at"])

    def test_the_row_says_who_produced_the_run_when_it_can(self):
        """I campi di provenienza (sessione, durata, base) sono best-effort:
        presenti quando l'ambiente li sa, mai stringhe vuote da leggere per
        niente. Senza, una regressione dopo un cambio di modello o di runtime
        non ha nessuna pista nel diario."""
        from unittest import mock

        with TemporaryDirectory() as tmp:
            meta = Path(tmp) / "meta.json"
            meta.write_text(json.dumps({
                "session_id": "sess-prova",
                "started_at": "2026-07-27T06:00:00+00:00",
            }), encoding="utf-8")
            with mock.patch.object(pipeline_log, "SESSION_META", meta):
                entry = pipeline_log.build_entry("verificatore", "nothing", "x")
        self.assertEqual(entry["session_id"], "sess-prova")
        self.assertIsInstance(entry["duration_seconds"], int)
        self.assertGreaterEqual(entry["duration_seconds"], 0)
        # La base è best-effort come tutto il resto: su un checkout con un
        # ref di master c'è ed è distinta dall'HEAD della run, su un clone
        # shallow (la CI fa così) manca, e mancare è il comportamento
        # giusto, non una stringa vuota da leggere per niente.
        import subprocess
        has_master = any(
            subprocess.run(("git", "rev-parse", "--verify", "--quiet", ref),
                           cwd=str(pipeline_log.PROJECT_ROOT),
                           capture_output=True).returncode == 0
            for ref in ("origin/master", "master")
        )
        if has_master:
            self.assertTrue(entry.get("base_commit"))
        else:
            self.assertNotIn("base_commit", entry)

    def test_a_checkout_without_a_session_writes_fewer_fields_not_empty_ones(self):
        from unittest import mock

        with TemporaryDirectory() as tmp:
            with mock.patch.object(pipeline_log, "SESSION_META", Path(tmp) / "assente.json"):
                entry = pipeline_log.build_entry("verificatore", "nothing", "x")
        self.assertNotIn("session_id", entry)
        self.assertNotIn("duration_seconds", entry)

    def test_an_unknown_stage_or_outcome_is_refused(self):
        """Il vocabolario è corto di proposito: un campo libero si riempirebbe
        di sinonimi e l'aggregato diventerebbe illeggibile."""
        with self.assertRaises(SystemExit):
            pipeline_log.build_entry("giornalista", "nothing", "x")
        with self.assertRaises(SystemExit):
            pipeline_log.build_entry("verificatore", "andata-benino", "x")

    def test_a_demolished_stage_can_be_read_but_never_written_again(self):
        """`STAGES` e `HISTORICAL_STAGES` sono due insiemi diversi apposta, e
        finora **nessuna riga della suite** guardava la differenza.

        Scrivere una run `writer` non si può più: quello stadio non ha un
        agente, non ha un perimetro nel cancello, e una riga nuova col suo nome
        sarebbe una run che nessuno ha aperto. Rileggere le run già scritte
        invece si deve: in `data/pipeline/runs/` ce ne sono quaranta `producer`,
        otto `writer` e nove `scout`, e derivare anche le scelte di **lettura**
        dai soli stadi vivi renderebbe illeggibile metà del diario, cioè
        butterebbe la storia per aver cancellato del codice.

        Il modo in cui la separazione regredisce è banale: qualcuno deriva
        `--stage choices` da `STAGES` perché sembra il più stretto dei due.
        """
        for morto in ("writer", "reviewer", "producer", "scout"):
            self.assertIn(morto, pipeline_log.HISTORICAL_STAGES, morto)
            self.assertNotIn(morto, pipeline_log.STAGES, morto)
            with self.assertRaises(SystemExit, msg=morto):
                pipeline_log.build_entry(morto, "merged", "x")

    def test_the_history_written_by_the_demolished_stages_still_reads(self):
        """La prova che la lettura regge, sulle righe vere e non su un elenco di
        nomi: due righe `producer` con lo stesso `run_id` collassano in una run
        sola, come farebbero oggi quelle di uno stadio vivo."""
        rows = [
            {"at": "2026-07-29T10:10:10+00:00", "stage": "producer", "outcome": "pr-open",
             "summary": "scritto ter-1", "run_id": "producer-20260729T101010Z-abcd",
             "pr": "77", "commit": "aaa1111", "branch": "automation/producer-2026-07-29"},
            {"at": "2026-07-29T10:40:00+00:00", "stage": "producer", "outcome": "merged",
             "summary": "PR #77 fusa", "run_id": "producer-20260729T101010Z-abcd",
             "pr": "77", "commit": "bbb2222", "branch": "master"},
        ]
        collassate = pipeline_log.collapse_runs(rows)
        self.assertEqual(len(collassate), 1)
        self.assertEqual(collassate[0]["outcome"], "merged")
        self.assertEqual(pipeline_log.summarize(collassate)["producer"]["runs"], 1)

    def test_a_corrupt_line_does_not_hide_the_rest(self):
        """È un registro, non uno schema: la riga dopo vale ancora."""
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs.jsonl"
            path.write_text(
                '{"stage":"verificatore","outcome":"merged","summary":"ok","at":"2026-07-01T00:00:00"}\n'
                "{ questa riga e rotta\n"
                '{"stage":"verificatore","outcome":"nothing","summary":"niente","at":"2026-07-02T00:00:00"}\n',
                encoding="utf-8",
            )
            entries = pipeline_log.read_journal(path)
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[2]["stage"], "verificatore")

    def test_the_summary_flags_the_runs_worth_looking_at(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs.jsonl"
            for outcome in ("merged", "nothing", "blocked", "stopped"):
                pipeline_log.append(
                    pipeline_log.build_entry("verificatore", outcome, f"run {outcome}"), path=path
                )
            state = pipeline_log.summarize(pipeline_log.read_journal(path))
        self.assertEqual(state["verificatore"]["runs"], 4)
        self.assertEqual(state["verificatore"]["attention"], 2, "blocked e stopped, non merged ne nothing")

    def test_nothing_is_not_a_problem(self):
        """Una coda vuota è la risposta giusta, non un allarme: se finisse fra i
        casi da guardare, il cruscotto urlerebbe ogni settimana per niente."""
        self.assertNotIn("nothing", pipeline_log.ATTENTION)
        self.assertNotIn("merged", pipeline_log.ATTENTION)

    def test_the_journal_is_append_only_across_runs(self):
        """Due run non si sovrascrivono: è JSON per riga proprio per questo."""
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs.jsonl"
            pipeline_log.append(pipeline_log.build_entry("admissions", "nothing", "prima"), path=path)
            pipeline_log.append(pipeline_log.build_entry("admissions", "merged", "seconda"), path=path)
            entries = pipeline_log.read_journal(path)
        self.assertEqual([e["summary"] for e in entries], ["prima", "seconda"])


class SilenceIsTheFailureNobodySees(unittest.TestCase):
    """Una run andata male lascia una riga `blocked` e si vede. Una Routine che
    smette di partire non lascia niente, e il diario di uno stadio fermo da un
    mese è identico a quello di uno stadio che ha finito il lavoro."""

    def entry(self, stage, days_ago):
        from datetime import datetime, timedelta, timezone

        when = datetime.now(timezone.utc) - timedelta(days=days_ago)
        return {"stage": stage, "outcome": "merged", "at": when.isoformat(timespec="seconds")}

    def group(self, rows, name):
        return next(r for r in rows if r["group"] == name)

    def test_a_daily_stage_quiet_for_a_week_is_flagged(self):
        rows = pipeline_log.silence([self.entry("verificatore", 7)])
        self.assertTrue(self.group(rows, "verificatore")["stale"])

    def test_a_daily_stage_that_skipped_one_day_is_not_flagged(self):
        """Con la grazia troppo stretta l'allarme suona ogni settimana per
        niente, e un allarme che suona sempre non è un allarme."""
        rows = pipeline_log.silence([self.entry("verificatore", 2)])
        self.assertFalse(self.group(rows, "verificatore")["stale"])

    def test_the_grace_is_what_separates_a_skip_from_a_stop(self):
        """La grazia misurata su una cadenza qualunque, non sui giorni dei
        gruppi di oggi.

        C'era un test che la provava su un gruppo settimanale (`curatore`,
        cadenza 7): fermo da dieci giorni, non ancora in ritardo. Quel gruppo
        non esiste più e nessuno dei quattro rimasti ha una cadenza diversa da
        1, quindi la proprietà non aveva più dove appoggiarsi. Provarla su un
        `WATCH_GROUPS` finto è l'unico modo di non perderla: `GRACE` è il
        numero che decide se un allarme suona, e nessun'altra riga della suite
        lo guarda."""
        finto = (("finto", ("verificatore",), 7),)
        with mock.patch.object(pipeline_log, "WATCH_GROUPS", finto):
            entro = pipeline_log.silence([self.entry("verificatore", 10)])
            oltre = pipeline_log.silence([self.entry("verificatore", 20)])
        self.assertFalse(self.group(entro, "finto")["stale"], "7 * 2.5 = 17,5 giorni")
        self.assertTrue(self.group(oltre, "finto")["stale"])

    def test_the_admissions_stage_is_one_group_even_if_it_was_three(self):
        """Scout, cacciatore e promotore erano tre gruppi per un agente solo, e
        chiudeva su uno dei tre a seconda di come era andata: contarli separati
        segnalava fermo l'uno ogni volta che lavorava l'altro. Adesso è un
        gruppo perché è un agente, e il caso non è più costruibile."""
        rows = pipeline_log.silence([self.entry("admissions", 1)])
        group = self.group(rows, "admissions")
        self.assertFalse(group["stale"])
        self.assertFalse(group["never"])

    def test_a_group_is_named_after_what_it_watches(self):
        """Niente più personaggi. Un avviso deve dire quale run aprire, e per
        farlo deve chiamarsi come lo stadio, che è anche il nome dell'agente
        per i tre che ne hanno uno."""
        for name, stages, _ in pipeline_log.WATCH_GROUPS:
            self.assertIn(name, pipeline_log.STAGES, name)
            self.assertIn(name, stages, name)

    def test_never_run_is_not_the_same_as_late(self):
        """Il giorno in cui nasce il diario nessuno stadio ha una storia. Dire
        che sono tutti fermi da sempre insegnerebbe a ignorare l'avviso."""
        rows = pipeline_log.silence([])
        for row in rows:
            self.assertTrue(row["never"])
            self.assertFalse(row["stale"])

    def test_every_stage_belongs_to_exactly_one_group(self):
        watched = [s for _, stages, _ in pipeline_log.WATCH_GROUPS for s in stages]
        self.assertEqual(sorted(watched), sorted(pipeline_log.STAGES))
        self.assertEqual(len(watched), len(set(watched)))


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
        """Non dai messaggi né dagli autori: un agente può scrivere qualunque
        messaggio, ma non può uscire dal proprio perimetro senza che il cancello
        lo fermi."""
        commits = pipeline_dashboard.recent_chain_commits(limit=5)
        from scripts import pipeline_gate

        owned = {p for paths in pipeline_gate.STAGE_PATHS.values() for p in paths}
        for commit in commits:
            for path in commit["files"]:
                self.assertTrue(pipeline_gate.path_allowed(path, owned), f"{commit['sha']}: {path}")
            self.assertTrue(commit["sha"] and commit["at"])


if __name__ == "__main__":
    unittest.main()


class TwoRowsAreOneRun(unittest.TestCase):
    """L'agente scrive la propria riga dentro la PR, il passo di merge scrive
    l'esito su master. Contarle come due run gonfia il totale **solo** per gli
    stadi che aprono pull request, cioè proprio quelli che lavorano."""

    ROWS = [
        {"at": "2026-07-27T06:20:00+00:00", "stage": "admissions", "outcome": "pr-open",
         "summary": "triage", "detail": ["DEPENDRATE respinto"], "gate": "checks",
         "pr": "45", "commit": "aaa1111", "branch": "automation/hunter-2026-07-27"},
        {"at": "2026-07-27T06:28:30+00:00", "stage": "admissions", "outcome": "merged",
         "summary": "PR #45 fusa", "detail": [], "gate": "checks",
         "pr": "45", "commit": "bbb2222", "branch": "master"},
        # Un altro stadio, di proposito: è il rumore accanto alle due righe che
        # devono collassare. Se anche questa fosse `admissions`, il conteggio
        # dell'ammissione varrebbe 2 e il test smetterebbe di distinguere "due
        # righe una run" da "due run".
        {"at": "2026-07-27T07:00:00+00:00", "stage": "verificatore", "outcome": "nothing",
         "summary": "niente da verificare", "detail": [], "gate": "", "pr": "",
         "commit": "ccc3333", "branch": "master"},
    ]

    def test_a_merged_run_counts_once(self):
        collapsed = pipeline_log.collapse_runs(self.ROWS)
        self.assertEqual(len(collapsed), 2)
        self.assertEqual(pipeline_log.summarize(collapsed)["admissions"]["runs"], 1)

    def test_the_outcome_is_the_one_the_merge_step_knew(self):
        row = pipeline_log.collapse_runs(self.ROWS)[0]
        self.assertEqual(row["outcome"], "merged")
        self.assertEqual(row["commit"], "bbb2222")

    def test_the_agents_reasons_survive(self):
        """La riga del passo di merge non porta le motivazioni. Tenere solo la
        più recente vorrebbe dire scambiare il perché con il come è finita."""
        row = pipeline_log.collapse_runs(self.ROWS)[0]
        self.assertIn("DEPENDRATE respinto", row["detail"])

    def test_a_run_without_a_pull_request_stays_alone(self):
        """La terza riga non ha PR e non ha nessuno con cui unirsi: resta una
        run per conto suo, accanto alla coppia collassata."""
        collapsed = pipeline_log.collapse_runs(self.ROWS)
        self.assertEqual([r["stage"] for r in collapsed], ["admissions", "verificatore"])

    def test_rows_of_different_stages_never_merge(self):
        rows = [dict(self.ROWS[0]), dict(self.ROWS[1], stage="verificatore")]
        self.assertEqual(len(pipeline_log.collapse_runs(rows)), 2)

    def test_the_closing_time_is_what_the_silence_alarm_sees(self):
        row = pipeline_log.collapse_runs(self.ROWS)[0]
        self.assertEqual(row["at"], "2026-07-27T06:28:30+00:00")


class TheRunIdIsWhatActuallyIdentifiesARun(unittest.TestCase):
    """La chiave era `(stadio, pr)`, e su trenta run reali ne apparava undici.

    Il motivo non è una dimenticanza degli agenti ed è istruttivo: la riga
    dell'agente viaggia **dentro** la pull request, quindi va committata prima
    che la pull request esista, quindi non può portarne il numero. Il diario
    finiva per dichiarare ventuno run in attesa mentre le pull request aperte
    erano zero.
    """

    def rows(self, run_id="reviewer-20260727T110207Z-a3f1"):
        return [
            {"at": "2026-07-27T11:02:07+00:00", "run_id": run_id, "stage": "verificatore",
             "outcome": "pr-open", "summary": "sei articoli", "detail": ["ter-920 corretto"],
             "gate": "auto", "pr": "", "commit": "aaa1111", "branch": "automation/x"},
            {"at": "2026-07-27T11:07:01+00:00", "run_id": run_id, "stage": "verificatore",
             "outcome": "merged", "summary": "PR #47 fusa", "detail": [],
             "gate": "auto", "pr": "47", "commit": "bbb2222", "branch": "master"},
        ]

    def test_the_two_halves_join_without_the_pull_request_number(self):
        collapsed = pipeline_log.collapse_runs(self.rows())
        self.assertEqual(len(collapsed), 1)
        self.assertEqual(collapsed[0]["outcome"], "merged")
        self.assertIn("ter-920 corretto", collapsed[0]["detail"])

    def test_the_number_arrives_from_the_half_that_could_know_it(self):
        self.assertEqual(pipeline_log.collapse_runs(self.rows())[0]["pr"], "47")

    def test_two_runs_of_the_same_stage_on_the_same_day_stay_apart(self):
        """Il ripiego `(stadio, pr)` non li distingueva quando il numero
        mancava, e due run del revisore nello stesso giorno sono la norma."""
        rows = self.rows() + self.rows(run_id="reviewer-20260727T114619Z-77b2")
        self.assertEqual(len(pipeline_log.collapse_runs(rows)), 2)

    def test_old_rows_without_an_id_still_join_on_the_pull_request(self):
        """Il ripiego resta, perché la storia già scritta non ha id."""
        rows = [dict(r) for r in TwoRowsAreOneRun.ROWS]
        self.assertEqual(len(pipeline_log.collapse_runs(rows)), 2)

    def test_an_id_is_minted_and_printed_for_whoever_writes_first(self):
        entry = pipeline_log.build_entry("verificatore", "pr-open", "x")
        self.assertTrue(entry["run_id"].startswith("verificatore-"))
        self.assertEqual(entry["trigger"], "manuale")

    def test_an_unknown_trigger_is_refused_like_an_unknown_outcome(self):
        with self.assertRaises(SystemExit):
            pipeline_log.build_entry("verificatore", "pr-open", "x", trigger="a-mano-di-notte")


class TheCliRefusesToMintARunIdSilently(unittest.TestCase):
    """Un agente che dimentica `--run-id` lasciava un file orfano che poi
    bloccava il merge come "worktree non pulito": lo script coniava un id
    nuovo invece di fermarsi, e la documentazione che dice già che
    `--run-id` non è facoltativo (AGENT_CONTRACT.md, pipeline-close-run)
    non basta da sola a impedirlo."""

    def _run(self, *extra_args):
        return subprocess.run(
            [sys.executable, "scripts/pipeline_log.py", "--write",
             "--stage", "verificatore", "--outcome", "nothing", "--summary", "x", *extra_args],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=30,
        )

    def test_write_without_a_run_id_is_refused(self):
        result = self._run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--run-id", result.stderr)

    def test_mint_run_id_is_accepted_as_the_explicit_opt_out(self):
        """La chiamata conierà comunque un id (coperto già da
        `test_an_id_is_minted_and_printed_for_whoever_writes_first`); qui
        conta solo che `--mint-run-id` faccia passare l'argparse invece di
        essere respinto insieme a `--run-id` mancante. Scrive per davvero
        nello shard reale (`RUNS_DIR` non è configurabile da CLI): lo shard
        va ripulito subito, non è materia di questo test."""
        runs_dir = REPO_ROOT / "data" / "pipeline" / "runs"
        before = set(runs_dir.iterdir())
        result = self._run("--mint-run-id")
        after = set(runs_dir.iterdir())
        created = after - before
        try:
            self.assertNotIn("--run-id mancante", result.stderr)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(created), 1)
        finally:
            for path in created:
                path.unlink()


class TwoRunsNeverWriteTheSameFile(unittest.TestCase):
    """Il conflitto che ha reso necessaria una sezione intera del contratto.

    Sette stadi che appendono in coda allo stesso `.jsonl` collidono sempre.
    Con un file per run non c'è niente da fondere, e questo test lo dice sul
    filesystem invece che in un commento.
    """

    def test_two_stages_recording_at_once_touch_two_files(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline_log.append(pipeline_log.build_entry("verificatore", "pr-open", "a"), path=root)
            pipeline_log.append(pipeline_log.build_entry("verificatore", "pr-open", "b"), path=root)
            names = sorted(p.name for p in root.glob("*.json"))
            self.assertEqual(len(names), 2)
            self.assertEqual(len(pipeline_log.read_journal(root)), 2)

    def test_the_outcome_row_sits_beside_the_agents_row_not_on_top_of_it(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = pipeline_log.build_entry("verificatore", "pr-open", "a")
            pipeline_log.append(entry, path=root)
            pipeline_log.append(
                pipeline_log.build_entry("verificatore", "merged", "fusa", run_id=entry["run_id"]),
                path=root, suffix=".esito",
            )
            self.assertEqual(len(list(root.glob("*.json"))), 2)
            collapsed = pipeline_log.collapse_runs(pipeline_log.read_journal(root))
        self.assertEqual(len(collapsed), 1)
        self.assertEqual(collapsed[0]["outcome"], "merged")


class SilenceMeansSomethingElseNowThatTheLauncherAssignsTheWork(unittest.TestCase):
    """Uno stadio che tace perché non ha niente da fare sta rispondendo.

    Con sei cron, il silenzio del curatore era un ritardo. Con il lanciatore è
    la risposta giusta a una coda vuota, e segnalarlo come guasto è il modo
    più sicuro di insegnare a ignorare gli avvisi.
    """

    def entry(self, stage, days_ago):
        from datetime import datetime, timedelta, timezone

        when = datetime.now(timezone.utc) - timedelta(days=days_ago)
        return {"stage": stage, "outcome": "nothing", "summary": "x",
                "at": when.isoformat(timespec="seconds")}

    def group(self, rows, name):
        return next(r for r in rows if r["group"] == name)

    def test_a_quiet_stage_with_an_empty_queue_is_idle_not_late(self):
        rows = pipeline_log.silence([self.entry("verificatore", 40)],
                                    queues={"verificatore": 0})
        self.assertFalse(self.group(rows, "verificatore")["stale"])
        self.assertTrue(self.group(rows, "verificatore")["idle"])

    def test_a_quiet_stage_with_work_waiting_is_still_late(self):
        rows = pipeline_log.silence([self.entry("verificatore", 40)],
                                    queues={"verificatore": 3})
        self.assertTrue(self.group(rows, "verificatore")["stale"])
        self.assertFalse(self.group(rows, "verificatore")["idle"])

    def test_without_the_queues_it_behaves_as_it_always_did(self):
        rows = pipeline_log.silence([self.entry("verificatore", 40)])
        self.assertTrue(self.group(rows, "verificatore")["stale"])

    def test_only_the_verifier_actually_has_a_countable_queue(self):
        """Perché i tre test qui sopra girano tutti sul verificatore, e non su
        un altro gruppo qualunque.

        `queue_sizes()` ha per chiavi `pipeline_status.STAGE_ORDER`, che è il
        vocabolario **storico** delle code. Di tutto `WATCH_GROUPS` solo
        `verificatore` compare anche lì: per gli altri `queues.get()` torna
        `None`, `waiting` resta `None`, e la distinzione `idle` / `stale` non si
        può esercitare. Provarla su `admissions` darebbe un test verde che non
        misura niente."""
        contate = set(pipeline_status.STAGE_ORDER)
        con_coda = [n for n, stages, _ in pipeline_log.WATCH_GROUPS
                    if set(stages) <= contate]
        self.assertEqual(con_coda, ["verificatore"])

    def test_the_launch_heartbeat_is_judged_on_itself_and_nothing_else(self):
        """Non ha una coda: quando tace, è il lanciatore a non essere partito,
        e non c'è niente da interpretare. Il suo battito è il tick `launch`,
        e l'esenzione vive in `pipeline_log.SENZA_CODA`.

        Le code arrivano qui da fuori, quindi un chiamante **può** passare un
        conteggio per `launch` anche se `queue_sizes()` non lo produce mai: se
        l'esenzione sparisse, un battito muto da nove giorni con quel conteggio
        a zero risulterebbe `idle`, cioè "tutto a posto, non c'era niente da
        lanciare". È il falso silenzio più costoso della catena."""
        rows = pipeline_log.silence([self.entry("launch", 9)],
                                    queues={s: 0 for s in pipeline_log.STAGES})
        self.assertTrue(self.group(rows, "launch")["stale"])
        self.assertIsNone(self.group(rows, "launch")["waiting"])


class ABrokenShardLeavesAMarkInsteadOfVanishing(unittest.TestCase):
    """Saltare in silenzio uno shard rotto farebbe sparire una run dal diario,
    cioè produrrebbe esattamente l'invisibilità che il diario esiste per
    togliere, e per giunta sulle run andate male, che sono quelle più
    probabilmente scritte a metà."""

    def test_the_run_still_shows_up_as_unreadable(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline_log.append(
                pipeline_log.build_entry("verificatore", "merged", "buona"), path=root)
            (root / "rotta.json").write_text("{ meta riga", encoding="utf-8")
            entries = pipeline_log.read_journal(root)
        self.assertEqual(len(entries), 2)
        broken = [e for e in entries if e["outcome"] == "error"]
        self.assertEqual(len(broken), 1)
        self.assertIn("rotta.json", broken[0]["summary"])

    def test_a_json_that_is_not_an_object_counts_too(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "lista.json").write_text("[1, 2, 3]", encoding="utf-8")
            entries = pipeline_log.read_journal(root)
        self.assertEqual([e["outcome"] for e in entries], ["error"])
