"""Il lanciatore per-indicatore: che cosa lancia, per chi, e in che ordine.

Nucleo puro: ogni test costruisce un dossier sintetico (la forma di
`practice_timeline.reconstruct`) e code finte, senza toccare il disco. Coniare i
run_id e' iniettato, cosi' l'uscita e' deterministica."""

import unittest

from scripts import pipeline_launch


def practice(code, *, state="in-lavorazione", flags=None, completed=(),
             required=("curator", "writer", "reviewer", "verificatore"),
             priority=0.0):
    return {
        "id": code,
        "state": state,
        "flags": dict(flags or {}),
        "completed_stages": list(completed),
        "required_stages": tuple(required),
        "priority": priority,
    }


def _mint(role):
    # Deterministico: nessun timestamp, cosi' il test confronta stringhe fisse.
    return f"{role}-RUNID"


class PlanLaunches(unittest.TestCase):
    def test_a_writer_ready_indicator_is_one_producer_launch(self):
        """Il ruolo resta, il bersaglio no: scrivere un articolo e' passato
        all'officina, e `.claude/agents/producer.md` non esiste piu'.

        Un piano che continuasse a nominarlo sarebbe un puntatore morto che
        qualcuno lancia una volta sola, scoprendo il guasto quando la run muore.
        """
        dossier = {"ter-5": practice("ter-5", completed=["curator"], priority=7.0)}
        plan = pipeline_launch.plan_launches(dossier, {}, mint=_mint)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["role"], "producer")
        self.assertIsNone(plan[0]["agent"])
        self.assertIn("produci-indicatori", plan[0]["workflow"])
        self.assertIn("ter-5", plan[0]["comando"])
        self.assertEqual(plan[0]["indicator"], "ter-5")
        self.assertEqual(plan[0]["scope"], "indicatore")
        self.assertEqual(plan[0]["run_id"], "producer-RUNID")

    def test_a_signed_unverified_indicator_goes_to_the_verificatore(self):
        dossier = {"ter-9": practice("ter-9",
                                     completed=["curator", "writer", "reviewer"],
                                     priority=3.0)}
        plan = pipeline_launch.plan_launches(dossier, {}, mint=_mint)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["role"], "verificatore")
        # Il ruolo **e'** l'agente: non c'e' piu' una mappa da tradurre, e
        # questa asserzione e' cio' che se ne accorgerebbe se tornasse.
        self.assertEqual(plan[0]["agent"], "verificatore")
        self.assertEqual(plan[0]["indicator"], "ter-9")

    def test_the_source_queue_lights_up_the_admissions_batch(self):
        # Le proposte di fonti non sono indicatori nel dossier: si leggono dalle code.
        plan = pipeline_launch.plan_launches({}, {"scout": 50, "hunter": 0,
                                                  "promoter": 0}, mint=_mint)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["role"], "admissions")
        self.assertEqual(plan[0]["agent"], "admissions")
        self.assertIsNone(plan[0]["indicator"])
        self.assertEqual(plan[0]["scope"], "batch")
        self.assertIn("50", plan[0]["reason"])

    def test_an_uncountable_upstream_queue_still_launches_admissions(self):
        # None conta come lavoro, come ovunque nella catena: meglio andarci a vedere.
        plan = pipeline_launch.plan_launches({}, {"scout": None, "hunter": 0,
                                                  "promoter": 0}, mint=_mint)
        self.assertEqual([item["role"] for item in plan], ["admissions"])

    def test_a_public_smentita_preempts_everything(self):
        dossier = {
            "ter-1": practice("ter-1", state="invalidata",
                              flags={"open_smentita": True},
                              completed=["curator", "writer", "reviewer", "verificatore"],
                              required=("reviewer", "verificatore"), priority=100.0),
            "ter-2": practice("ter-2", completed=["curator"], priority=5.0),
        }
        plan = pipeline_launch.plan_launches(dossier, {"scout": 50, "hunter": 0,
                                                       "promoter": 0}, mint=_mint)
        # smentita (100) prima, poi il produttore fresco (5), poi l'ammissione (0).
        self.assertEqual(plan[0]["indicator"], "ter-1")
        self.assertEqual(plan[0]["role"], "producer")   # il reviewer e' fuso nel produttore
        self.assertEqual(plan[-1]["role"], "admissions")
        self.assertEqual([item["priority"] for item in plan], [100.0, 5.0, 0.0])

    def test_two_producer_indicators_are_two_parallel_launches(self):
        dossier = {
            "ter-3": practice("ter-3", completed=["curator"], priority=4.0),
            "ter-4": practice("ter-4", completed=["curator"], priority=6.0),
        }
        plan = pipeline_launch.plan_launches(dossier, {}, mint=_mint)
        self.assertEqual(len(plan), 2)
        self.assertEqual({item["indicator"] for item in plan}, {"ter-3", "ter-4"})
        # ordinati per priorita' decrescente
        self.assertEqual([item["indicator"] for item in plan], ["ter-4", "ter-3"])

    def test_blocked_and_terminal_practices_are_not_launched(self):
        dossier = {
            "ter-6": practice("ter-6", state="in-attesa", flags={"needs_info": True}),
            "ter-7": practice("ter-7", state="chiusa", flags={"rejected": True}),
            "ter-8": practice("ter-8", state="pubblicata",
                              completed=["curator", "writer", "reviewer", "verificatore"]),
        }
        plan = pipeline_launch.plan_launches(dossier, {}, mint=_mint)
        self.assertEqual(plan, [])

    def test_a_proposta_reinforces_admissions_without_a_second_launch(self):
        dossier = {"eur-x": practice("eur-x", state="proposta",
                                     flags={"approved_candidate": True},
                                     completed=[], priority=12.0)}
        plan = pipeline_launch.plan_launches(dossier, {"scout": 0, "hunter": 0,
                                                       "promoter": 0}, mint=_mint)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["role"], "admissions")
        # la priorita' della batch e' quella della proposta piu' urgente
        self.assertEqual(plan[0]["priority"], 12.0)

    def test_nothing_ready_is_an_empty_plan(self):
        plan = pipeline_launch.plan_launches({}, {"scout": 0, "hunter": 0,
                                                  "promoter": 0}, mint=_mint)
        self.assertEqual(plan, [])


def _reading(key, status, code=None, hard_failures=None, level="regione",
             note="", low_scores=None):
    return {"key": key, "code": code or key, "level": level, "status": status,
            "hard_failures": list(hard_failures or []),
            "note": note, "low_scores": list(low_scores or [])}


class ReadingsFeedTheLauncher(unittest.TestCase):
    """La quarta lista: i pubblicati entrano dalla coda di lettura, non da
    `ready_stage` (terminale su `pubblicata`). Le letture restano fuori dalla
    macchina a stati, quindi si passano al piano come una lista a parte."""

    def test_an_unread_published_article_is_a_reader_editor_launch(self):
        readings = [_reading("dem:POP014", "unread")]
        plan = pipeline_launch.plan_launches({}, {}, mint=_mint, readings=readings)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["role"], "reader-editor")
        self.assertEqual(plan[0]["agent"], "reader-editor")
        self.assertEqual(plan[0]["indicator"], "dem:POP014")
        self.assertEqual(plan[0]["run_id"], "reader-editor-RUNID")

    def test_a_revise_reading_is_a_producer_rewrite(self):
        readings = [_reading("eur:rd_p_persreg", "revise", code="eur-rd_p_persreg",
                             hard_failures=["numeric_overload"])]
        plan = pipeline_launch.plan_launches({}, {}, mint=_mint, readings=readings)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["role"], "producer")
        self.assertEqual(plan[0]["indicator"], "eur:rd_p_persreg")
        self.assertIn("leggibilita", plan[0]["reason"])
        self.assertIn("fallimenti duri: numeric_overload", plan[0]["reason"])

    def test_the_rewrite_carries_where_the_reader_stumbled(self):
        """Il motivo del lancio e' l'unica cosa che il produttore riceve, quindi
        se non porta l'indirizzo della bocciatura la riscrittura parte cieca e si
        fa bocciare di nuovo finche' il freno non parcheggia il codice."""
        readings = [_reading("eur:rd_p_persreg", "revise", code="eur-rd_p_persreg",
                             note="la meccanica FTE apre la narrazione, spostala fuori dal corpo",
                             low_scores=[("structure", 0), ("cognitive_load", 1)])]
        plan = pipeline_launch.plan_launches({}, {}, mint=_mint, readings=readings)
        reason = plan[0]["reason"]
        self.assertIn("structure=0", reason)
        self.assertIn("cognitive_load=1", reason)
        self.assertIn("la meccanica FTE apre la narrazione", reason)

    def test_a_parked_reading_launches_nothing(self):
        # reading_queue non emette mai `parked` come lavoro; il piano non lo tocca.
        readings = [_reading("ter-9", "parked")]
        plan = pipeline_launch.plan_launches({}, {}, mint=_mint, readings=readings)
        self.assertEqual(plan, [])

    def test_a_clean_reading_launches_nothing(self):
        readings = [_reading("ter-9", "clean")]
        plan = pipeline_launch.plan_launches({}, {}, mint=_mint, readings=readings)
        self.assertEqual(plan, [])

    def test_a_revise_does_not_double_launch_a_producer_already_ready(self):
        # ter-5 e' gia' pronto per il produttore da ready_stage (curata, da scrivere)
        # E anche bocciato per leggibilita'. Un solo produttore, non due.
        dossier = {"ter-5": practice("ter-5", completed=["curator"], priority=7.0)}
        readings = [_reading("ter-5", "revise")]
        plan = pipeline_launch.plan_launches(dossier, {}, mint=_mint, readings=readings)
        producers = [p for p in plan if p["role"] == "producer"]
        self.assertEqual(len(producers), 1, "un solo produttore per indicatore nel tick")

    def test_an_article_about_to_be_rewritten_is_not_read(self):
        # ter-5 in produzione (ready_stage) e anche unread: non lo si legge ora,
        # l'impronta cambiera' e la lettura scadrebbe subito.
        dossier = {"ter-5": practice("ter-5", completed=["curator"], priority=7.0)}
        readings = [_reading("ter-5", "unread")]
        plan = pipeline_launch.plan_launches(dossier, {}, mint=_mint, readings=readings)
        self.assertEqual([p["role"] for p in plan], ["producer"])

    def test_a_signed_but_unread_article_is_read_before_it_is_verified(self):
        """Il doppione vero, trovato in revisione: un articolo appena firmato sta
        insieme fra i verificabili e fra i non letti, e il lanciatore metteva in
        volo tutte e due le voci. Se poi la lettura boccia, la riscrittura fa
        scadere la verifica appena fatta: una run opus buttata."""
        dossier = {"ter-9": practice("ter-9",
                                     completed=["curator", "writer", "reviewer"],
                                     priority=15.0)}
        readings = [_reading("ter-9", "unread")]
        plan = pipeline_launch.plan_launches(dossier, {}, mint=_mint, readings=readings)
        self.assertEqual([p["role"] for p in plan], ["reader-editor"])
        # e non scende nel piano per essere stato dedotto: tiene la priorita' alta
        self.assertEqual(plan[0]["priority"], 15.0)

    def test_the_deferred_role_comes_back_once_the_reading_exists(self):
        """Scartare non e' perdere: il piano si ricalcola a ogni tick."""
        dossier = {"ter-9": practice("ter-9",
                                     completed=["curator", "writer", "reviewer"],
                                     priority=15.0)}
        readings = [_reading("ter-9", "clean")]
        plan = pipeline_launch.plan_launches(dossier, {}, mint=_mint, readings=readings)
        self.assertEqual([p["role"] for p in plan], ["verificatore"])

    def test_the_reader_editor_sorts_before_the_verificatore_on_a_tie(self):
        # Stesso indicatore, stessa priorita': leggere prima, per non sprecare la
        # verifica su un testo che una bocciatura fara' riscrivere.
        dossier = {"ter-9": practice("ter-9",
                                     completed=["curator", "writer", "reviewer"],
                                     priority=0.0)}
        readings = [_reading("dem:POP014", "unread")]  # priorita' 0.0, non nel dossier
        plan = pipeline_launch.plan_launches(dossier, {}, mint=_mint, readings=readings)
        roles = [p["role"] for p in plan]
        self.assertLess(roles.index("reader-editor"), roles.index("verificatore"))


class TheParallelismCap(unittest.TestCase):
    """Il cap di parallelismo: un tick lancia al massimo tre ruoli, e taglia i
    meno prioritari, non i piu'. Nasce dalla richiesta di non far partire dieci
    subagent insieme."""

    def _plan(self, n):
        # gia' ordinato per priorita' decrescente, come load_plan restituisce
        return [{"role": "producer", "indicator": f"ter-{i}", "priority": 100 - i}
                for i in range(n)]

    def test_default_cap_is_three(self):
        shown = pipeline_launch.cap_for_tick(self._plan(10))
        self.assertEqual(len(shown), 3)

    def test_the_cap_keeps_the_most_urgent_and_drops_the_tail(self):
        plan = self._plan(10)
        shown = pipeline_launch.cap_for_tick(plan)
        self.assertEqual(shown, plan[:3])
        self.assertEqual(shown[0]["indicator"], "ter-0")  # priorita' piu' alta

    def test_fewer_than_the_cap_passes_all_through(self):
        self.assertEqual(len(pipeline_launch.cap_for_tick(self._plan(2))), 2)

    def test_zero_means_no_cap(self):
        plan = self._plan(7)
        self.assertEqual(pipeline_launch.cap_for_tick(plan, max_parallel=0), plan)

    def test_top_overrides_the_cap(self):
        self.assertEqual(len(pipeline_launch.cap_for_tick(self._plan(9), top=5)), 5)


class TheReaderEditorGetsAReservedSlotButDoesNotPreempt(unittest.TestCase):
    """Le letture ereditano la priorita' alta di un articolo pubblicato: senza
    riserva monopolizzerebbero il tick e fermerebbero il lavoro fattuale. La
    riserva le tiene a una voce a tick, e gli altri due slot al resto."""

    def _mixed(self, readers, others):
        plan = ([{"role": "reader-editor", "indicator": f"r{i}", "priority": 100 - i}
                 for i in range(readers)]
                + [{"role": "producer", "indicator": f"p{i}", "priority": 50 - i}
                   for i in range(others)])
        plan.sort(key=lambda x: (-x["priority"],
                                 pipeline_launch.ROLE_ORDER.index(x["role"]),
                                 x["indicator"]))
        return plan

    def test_one_reader_slot_even_when_readers_have_the_top_priority(self):
        # Cinque letture ad alta priorita', cinque produttori: il tick porta una
        # sola lettura e due produttori, non tre letture.
        tick = pipeline_launch.cap_for_tick(self._mixed(5, 5))
        self.assertEqual(sum(1 for x in tick if x["role"] == "reader-editor"), 1)
        self.assertEqual(sum(1 for x in tick if x["role"] == "producer"), 2)

    def test_readers_fill_the_tick_when_there_is_no_other_work(self):
        tick = pipeline_launch.cap_for_tick(self._mixed(5, 0))
        self.assertEqual(len(tick), 3)
        self.assertTrue(all(x["role"] == "reader-editor" for x in tick))

    def test_no_readers_means_the_reservation_costs_nothing(self):
        tick = pipeline_launch.cap_for_tick(self._mixed(0, 5))
        self.assertEqual(len(tick), 3)
        self.assertTrue(all(x["role"] == "producer" for x in tick))

    def test_a_single_reader_still_drains_against_a_full_producer_queue(self):
        # Il caso vero: un arretrato di letture dietro centinaia di produttori.
        tick = pipeline_launch.cap_for_tick(self._mixed(1, 200))
        self.assertEqual(sum(1 for x in tick if x["role"] == "reader-editor"), 1,
                         "l'arretrato di lettura deve drenare, non morire di fame")


class TheLaunchTick(unittest.TestCase):
    """Il battito del lanciatore: uno shard `launch` per tick, portato su master
    con un runner iniettato, mai un git vero. Senza questo battito una Routine a
    vuoto e' indistinguibile da una che non e' mai partita, che e' il guasto che
    il diario esiste per non avere."""

    def _tick(self, tmp, **kwargs):
        from pathlib import Path

        from scripts import pipeline_log

        original = pipeline_log.RUNS_DIR
        pipeline_log.RUNS_DIR = Path(tmp)
        try:
            entry = pipeline_launch.log_tick(
                [{"role": "producer"}], log=lambda *_: None, **kwargs)
            shards = list(Path(tmp).glob("launch-*.json"))
        finally:
            pipeline_log.RUNS_DIR = original
        return entry, shards

    def test_the_tick_builds_a_launch_shard_and_lands_it(self):
        import tempfile

        calls = []

        def fake_runner(cmd, cwd=None, env=None):
            calls.append(cmd)
            return 0, "deadbeef\n"

        with tempfile.TemporaryDirectory() as tmp:
            entry, shards = self._tick(tmp, runner=fake_runner)

        self.assertEqual(entry["stage"], "launch")
        self.assertEqual(entry["outcome"], "nothing")
        self.assertEqual(entry["trigger"], "routine")
        self.assertEqual(len(shards), 1)  # uno shard, mai un registro unico
        # ha provato a portarlo su master, e solo attraverso il runner iniettato
        self.assertTrue(any(c[:2] == ["git", "push"] for c in calls))
        self.assertTrue(any("commit-tree" in c for c in calls))

    def test_without_commit_it_writes_the_shard_but_touches_no_git(self):
        import tempfile

        calls = []

        def fake_runner(*a, **k):
            calls.append(a)
            return 0, ""

        with tempfile.TemporaryDirectory() as tmp:
            _, shards = self._tick(tmp, runner=fake_runner, do_commit=False)

        self.assertEqual(len(shards), 1)
        self.assertEqual(calls, [])  # do_commit=False: nessuna chiamata a git


if __name__ == "__main__":
    unittest.main()
