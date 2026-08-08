"""The gate, tested by the failures it has to catch.

A gate that has only ever returned green is not a gate, it is a formality. Every
test here builds the bad input first and asserts the gate refuses it, then
builds the good one and asserts it passes. The asymmetry is deliberate: the
whole point of this file is that an autonomous stage cannot talk its way past a
check, so the check has to be shown saying no.

Pure stdlib and side-effect free. Nothing here reads or writes the committed
queues: every check takes its rows as an argument for exactly this reason.
"""

import itertools
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import indicator_store, pipeline_gate, verification_queue


class BlastRadius(unittest.TestCase):
    """The check that makes the rest safe to automate.

    An agent's prompt can be edited, misread or ignored. The path list lives in
    the repo, so a stage that decides to "just fix" a view module fails here,
    before its reasoning is ever read.

    Le fixture di questa classe girano sul perimetro del **verificatore**
    (`data/pipeline/verifiche/`), e non su `content/indicators/`, che era la
    scelta ovvia finché esisteva uno stadio che scriveva gli articoli. Dopo la
    demolizione non ne esiste più nessuno: l'officina scrive lì, ma non è una
    run e non passa dal cancello. Un test che usasse ancora gli articoli come
    esempio di "dentro il perimetro" proverebbe il contrario di ciò che dice.
    """

    DENTRO = "data/pipeline/verifiche/ter-30.json"

    def test_a_stage_that_edits_application_code_is_refused(self):
        check = pipeline_gate.check_blast_radius(
            "verificatore", [self.DENTRO, "app/views.py"],
        )
        self.assertFalse(check.ok)
        self.assertIn("app/views.py", check.detail)

    def test_a_stage_inside_its_perimeter_passes(self):
        check = pipeline_gate.check_blast_radius("verificatore", [self.DENTRO])
        self.assertTrue(check.ok, check.detail)

    def test_the_articles_are_nobodys_perimeter_any_more(self):
        """La demolizione, detta come proprietà invece che come cronaca.

        Il produttore non esiste più e l'officina non è una run: nessuno
        stadio può scrivere un articolo passando dal cancello. Un perimetro
        riaperto per comodità su `content/indicators/` sarebbe il diritto di
        pubblicare fuori da `officina/lint.py`, cioè fuori da ogni cancello
        editoriale."""
        for stage, paths in pipeline_gate.STAGE_PATHS.items():
            self.assertNotIn(pipeline_gate.INDICATOR_TEXTS, paths, stage)
            self.assertFalse(
                pipeline_gate.check_blast_radius(
                    stage, ["content/indicators/ter__920.json"]).ok, stage)

    def test_a_directory_perimeter_does_not_leak_past_the_slash(self):
        """Il perimetro a directory è l'unico modo di autorizzare uno store a
        un file per record senza elencarne trecento file, e la barra finale è
        ciò che gli impedisce di allargarsi da solo. Senza, il prefisso
        `data/pipeline/verifiche` autorizzerebbe anche
        `data/pipeline/verifiche-bozze`, cioè un percorso che nessuno ha mai
        concesso a nessuno stadio."""
        check = pipeline_gate.check_blast_radius(
            "verificatore", ["data/pipeline/verifiche-bozze/ter-30.json"]
        )
        self.assertFalse(check.ok)
        self.assertTrue(
            pipeline_gate.path_allowed(
                "data/pipeline/verifiche/bes__10AMB004.json",
                pipeline_gate.STAGE_PATHS["verificatore"],
            )
        )

    def test_the_perimeters_do_not_overlap_where_it_would_matter(self):
        """Nessuno stadio può toccare il lavoro di un altro.

        The run journal is the one deliberate exception, and it is shared on
        purpose: every stage records what it did, including the runs that produce
        nothing else, which are exactly the runs that would otherwise vanish.
        Stated as a test because the lists are short enough that widening one by
        hand looks harmless in a diff.

        A coppie su `STAGE_PATHS`, non su due stadi scelti a mano: la versione
        scritta a mano ne confrontava due su tre, e il perimetro del terzo
        (`data/pipeline/letture/`) non veniva controllato da nessuno. Una
        proprietà che vale "per ogni coppia" non va enumerata, o la prossima
        aggiunta la lascia indietro in silenzio.
        """
        shared = {pipeline_gate.RUN_JOURNAL}
        perimetri = {stage: set(paths) - shared
                     for stage, paths in pipeline_gate.STAGE_PATHS.items()}
        for uno, altro in itertools.combinations(sorted(perimetri), 2):
            self.assertEqual(perimetri[uno] & perimetri[altro], set(),
                             f"{uno} e {altro} condividono un percorso")

    def test_every_stage_can_write_the_run_journal(self):
        """A stage that cannot record its run is a stage nobody can observe, and
        the gate would block it for trying."""
        for stage, paths in pipeline_gate.STAGE_PATHS.items():
            self.assertIn(pipeline_gate.RUN_JOURNAL, paths, stage)

    def test_every_stage_declares_a_merge_policy(self):
        self.assertEqual(
            sorted(pipeline_gate.STAGE_PATHS), sorted(pipeline_gate.MERGE_POLICY)
        )
        for stage, policy in pipeline_gate.MERGE_POLICY.items():
            self.assertIn(policy, ("auto", "checks", "manual"), stage)

    def test_no_stage_waits_for_a_human(self):
        """La catena è non presidiata per decisione presa. Un modo `manual`
        parcheggia la PR finché qualcuno guarda, e in una catena che nessuno
        guarda vuol dire per sempre: lo scout era l'unico stadio così, ed era
        il tappo che teneva ferma tutta la scoperta di indicatori nuovi."""
        for stage, policy in pipeline_gate.MERGE_POLICY.items():
            self.assertNotEqual(policy, "manual", stage)

    def test_no_chain_stage_waits_on_the_remote_ci(self):
        """Ogni stadio della catena fonde sul cancello locale, non sulla CI
        remota. La CI remota non parte sulle PR aperte via il GitHub MCP, quindi
        la vecchia policy `checks` non comprava un verdetto indipendente: comprava
        un deadlock (la PR restava `pr-open` per sempre e il dispatcher non
        lanciava più niente). Il cancello locale gira la stessa suite del job
        CI `python` e lo stesso perimetro del job `gate`, e gira prima del merge
        invece che mai. Se un giorno la CI parte su queste PR, gli stadi che
        muovono numeri vivi sono quelli da riportare a `checks`.

        Si itera la tabella, non una lista scritta a mano. La lista c'è stata,
        con sette voci per tre stadi: nominava `admissions` quattro volte,
        `verificatore` tre e **`reader-editor` mai**, quindi rimetterlo a
        `checks` non avrebbe fatto diventare rosso niente. Cioè il deadlock
        che questo test esiste per impedire sarebbe rientrato dalla porta che
        il test stesso lasciava aperta."""
        self.assertEqual(sorted(pipeline_gate.MERGE_POLICY),
                         sorted(pipeline_gate.STAGE_PATHS))
        for stage, policy in pipeline_gate.MERGE_POLICY.items():
            self.assertEqual(policy, "auto", stage)


class HunterDecisions(unittest.TestCase):
    def test_a_decision_without_a_written_reason_is_refused(self):
        check = pipeline_gate.check_hunter_decisions(
            [{"candidate_id": "eurostat_regional:x", "triage_status": "approved", "triage_notes": ""}]
        )
        self.assertFalse(check.ok)
        self.assertIn("eurostat_regional:x", check.detail)

    def test_a_motivated_decision_passes(self):
        check = pipeline_gate.check_hunter_decisions(
            [{
                "candidate_id": "eurostat_regional:x",
                "triage_status": "approved",
                "triage_notes": "Regionale, copertura 20 su 20, serie nuova.",
                "definition_match": "new",
                "coverage": "1.0",
                "license": "CC BY 4.0 (Eurostat)",
            }]
        )
        self.assertTrue(check.ok, check.detail)

    def test_an_untouched_candidate_needs_no_reason(self):
        """`new` is the absence of a decision, and `promoted` is written by the
        promotion script, not by a judgement. Neither owes an explanation."""
        check = pipeline_gate.check_hunter_decisions(
            [
                {"candidate_id": "a", "triage_status": "new", "triage_notes": ""},
                {"candidate_id": "b", "triage_status": "promoted", "triage_notes": ""},
            ]
        )
        self.assertTrue(check.ok, check.detail)

    def test_an_approval_below_the_coverage_floor_is_refused(self):
        """The hunter approves on its own now, so the things that make a series
        unusable have to be refusable without reading its reasoning. Twelve
        regions out of twenty cannot carry a claim about Italy."""
        check = pipeline_gate.check_hunter_decisions(
            [{
                "candidate_id": "eurostat_regional:sparse",
                "triage_status": "approved",
                "triage_notes": "sembra interessante",
                "definition_match": "new",
                "coverage": "0.6",
                "license": "CC BY 4.0",
            }]
        )
        self.assertFalse(check.ok)
        self.assertIn("copertura", check.detail)

    def test_an_approval_without_a_licence_is_refused(self):
        check = pipeline_gate.check_hunter_decisions(
            [{
                "candidate_id": "eurostat_regional:x",
                "triage_status": "approved",
                "triage_notes": "regionale, copertura piena",
                "definition_match": "new",
                "coverage": "1.0",
                "license": "",
            }]
        )
        self.assertFalse(check.ok)
        self.assertIn("licenza", check.detail)

    def test_the_floor_only_binds_approvals(self):
        """A rejected candidate is allowed to be as thin as it likes: recording
        why it was refused is exactly what the queue is for."""
        check = pipeline_gate.check_hunter_decisions(
            [{
                "candidate_id": "eurostat_regional:sparse",
                "triage_status": "rejected",
                "triage_notes": "copertura 12 regioni su 20, non regge un confronto nazionale",
                "definition_match": "new",
                "coverage": "0.6",
                "license": "",
            }]
        )
        self.assertTrue(check.ok, check.detail)

    def test_exact_is_never_claimed_automatically(self):
        check = pipeline_gate.check_hunter_decisions(
            [{
                "candidate_id": "eurostat_regional:x",
                "triage_status": "approved",
                "triage_notes": "sembra la stessa serie",
                "definition_match": "exact",
            }]
        )
        self.assertFalse(check.ok)
        self.assertIn("exact", check.detail)


class CurationDecisions(unittest.TestCase):
    def test_score_eligible_on_a_contextual_verso_is_refused(self):
        """The failure this exists for: a dependency ratio has no better, so
        orienting a z-score by it produces a ranking that means nothing."""
        check = pipeline_gate.check_curation_decisions(
            [{
                "target_indicator_id": "dem:OLDAGEDEPR",
                "reviewed_direction": "contextual",
                "score_eligible": "true",
                "reviewed_at": "2026-07-26",
            }]
        )
        self.assertFalse(check.ok)
        self.assertIn("dem:OLDAGEDEPR", check.detail)

    def test_a_contextual_indicator_out_of_the_score_passes(self):
        check = pipeline_gate.check_curation_decisions(
            [{
                "target_indicator_id": "dem:OLDAGEDEPR",
                "reviewed_direction": "contextual",
                "score_eligible": "false",
                "reviewed_at": "2026-07-26",
            }]
        )
        self.assertTrue(check.ok, check.detail)

    def test_a_directional_verso_may_enter_the_score(self):
        check = pipeline_gate.check_curation_decisions(
            [{
                "target_indicator_id": "eur:rd_e_gerdreg",
                "reviewed_direction": "higher_better",
                "score_eligible": "true",
                "reviewed_at": "2026-07-24",
            }]
        )
        self.assertTrue(check.ok, check.detail)

    def test_a_decision_with_no_date_is_refused(self):
        """`reviewed_at` is what the re-entry rule reads to decide whether a
        decision is still current, so an undated one silently freezes."""
        check = pipeline_gate.check_curation_decisions(
            [{
                "target_indicator_id": "eur:rd_e_gerdreg",
                "reviewed_direction": "higher_better",
                "score_eligible": "true",
                "reviewed_at": "",
            }]
        )
        self.assertFalse(check.ok)


class ARunThatProducedSomethingHasToSayItDid(unittest.TestCase):
    """Imposto dal cancello invece che ricordato nel prompt.

    È la stessa logica del perimetro: un promemoria si può saltare, e questo
    sta all'ultimo passo di una run lunga, cioè nel punto in cui è più
    facile saltarlo. Ed è proprio la riga di diario a rendere osservabile la
    catena, quindi vale un controllo, non un'esortazione.

    `base="HEAD"` e niente working tree, in tutti e tre i casi. La funzione
    porta davanti un **secondo** controllo, quello append-only sul diario, che
    legge il repo vero: senza una base fissata guarda `origin/master` o `master`,
    e in un checkout dove `master` è rimasto indietro di qualche commit le righe
    di diario arrivate nel frattempo risultano riscritte. Il verdetto che ne
    esce è vero ma di un'altra cosa, e questi tre casi smettono di misurare
    quello per cui esistono. Contro `HEAD` il diario è fermo per costruzione.
    """

    BASE = {"base": "HEAD", "include_worktree": False}

    def test_work_without_a_journal_line_is_refused(self):
        check = pipeline_gate.check_run_is_recorded(
            "verificatore", [pipeline_gate.VERIFICATIONS], **self.BASE
        )
        self.assertFalse(check.ok)
        self.assertIn("pipeline_log.py --write", check.detail)

    def test_a_run_that_touched_nothing_owes_no_record(self):
        """Una run a mani vuote non passa nemmeno di qui: non ha un branch da
        giudicare, e la sua riga resta affidata al contratto."""
        check = pipeline_gate.check_run_is_recorded("verificatore", [], **self.BASE)
        self.assertTrue(check.ok, check.detail)
        check = pipeline_gate.check_run_is_recorded(
            "verificatore", [pipeline_gate.RUN_JOURNAL], **self.BASE)
        self.assertTrue(check.ok, check.detail)


class TheSignatureCheckReadsStateNotDiffLines(unittest.TestCase):
    """Il punto cieco che il revisore ha trovato correggendo il proprio lavoro.

    La prima versione cercava una riga aggiunta con `"reviewed_at"`. Una
    correzione in giornata su un articolo già firmato quel giorno non ne
    produce nessuna, perché la firma giusta è quella che c'è già: il
    cancello bloccava lavoro corretto e spingeva verso una data falsa. Ora
    legge lo stato degli articoli toccati, che è anche strettamente più
    forte.
    """

    def _check_over(self, entries, keys):
        import unittest.mock as mock

        original = pipeline_gate.changed_text_keys
        pipeline_gate.changed_text_keys = lambda base=None, cwd=None, include_worktree=True: keys
        try:
            with mock.patch.object(indicator_store, "load_all", lambda root=None: entries):
                return pipeline_gate.check_reviewer_signature()
        finally:
            pipeline_gate.changed_text_keys = original

    def test_a_same_day_correction_to_an_already_signed_article_passes(self):
        check = self._check_over(
            {"178": {"reviewed_at": "2026-07-26", "reviewed_vintage": 2024, "vintage": 2024}},
            ["178"],
        )
        self.assertTrue(check.ok, check.detail)

    def test_prose_changed_without_any_signature_is_refused(self):
        check = self._check_over({"178": {"vintage": 2024}}, ["178"])
        self.assertFalse(check.ok)
        self.assertIn("178", check.detail)

    def test_a_signature_that_does_not_match_the_vintage_is_refused(self):
        """Sarebbe riaperta comunque dalla regola di rientro, quindi accettarla
        qui nasconderebbe il problema per una run sola."""
        check = self._check_over(
            {"178": {"reviewed_at": "2026-07-26", "reviewed_vintage": 2023, "vintage": 2024}},
            ["178"],
        )
        self.assertFalse(check.ok)

    def test_a_run_that_touched_no_article_owes_no_signature(self):
        check = self._check_over({}, [])
        self.assertTrue(check.ok, check.detail)


class ATypoInRolesCoveredIsNotAnOmission(unittest.TestCase):
    """Rilievo Codex sulla #171: un `roles_covered` con un ruolo sconosciuto
    (refuso) rendeva esattamente le stesse sezioni di un'omissione voluta, e
    niente lo segnalava prima che l'articolo raggiungesse la pagina pubblica.
    A render time sollevare è pericoloso (farebbe cadere ogni pagina già
    pubblicata su un refuso storico), quindi il controllo vive qui, prima del
    merge, dove la stringa grezza scritta dall'editor è ancora leggibile.
    """

    def _check_over(self, entries, keys):
        import unittest.mock as mock

        original = pipeline_gate.changed_text_keys
        pipeline_gate.changed_text_keys = lambda base=None, cwd=None, include_worktree=True: keys
        try:
            with mock.patch.object(indicator_store, "load_all", lambda root=None: entries):
                return pipeline_gate.check_writer_roles()
        finally:
            pipeline_gate.changed_text_keys = original

    def test_an_unknown_role_is_refused(self):
        check = self._check_over({"178": {"roles_covered": ["quadro", "definizone"]}}, ["178"])
        self.assertFalse(check.ok)
        self.assertIn("178", check.detail)
        self.assertIn("definizone", check.detail)

    def test_the_four_known_roles_pass(self):
        check = self._check_over(
            {"178": {"roles_covered": ["definizione", "quadro", "dinamica", "limiti"]}}, ["178"]
        )
        self.assertTrue(check.ok, check.detail)

    def test_a_missing_declaration_passes(self):
        check = self._check_over({"178": {}}, ["178"])
        self.assertTrue(check.ok, check.detail)

    def test_an_empty_declaration_passes(self):
        """`roles_covered: []` è una dichiarazione valida (assorbe la
        definizione), non un refuso."""
        check = self._check_over({"178": {"roles_covered": []}}, ["178"])
        self.assertTrue(check.ok, check.detail)

    def test_a_run_that_touched_no_article_owes_no_check(self):
        check = self._check_over({}, [])
        self.assertTrue(check.ok, check.detail)


class ChecksThatCannotRunAreNotPasses(unittest.TestCase):
    """The weakest thing a gate can do is report green because it looked away.

    `check_writer_vintage` needs the app view model. On a fresh cloud checkout
    that import fails, and returning a pass there would hand `merge: auto` to a
    writer whose prose is pinned to a year the data has not reached. The drift
    guard in the suite only fires when a vintage falls *behind*, so nothing else
    would ever notice.
    """

    def test_an_unverifiable_vintage_blocks_instead_of_passing(self):
        original = pipeline_gate.changed_text_keys
        pipeline_gate.changed_text_keys = lambda base=None, cwd=None, include_worktree=True: ["eur:fake"]
        try:
            import builtins

            real_import = builtins.__import__

            def refuse_app(name, *args, **kwargs):
                if name.startswith("app"):
                    raise ModuleNotFoundError("no app here")
                return real_import(name, *args, **kwargs)

            builtins.__import__ = refuse_app
            try:
                check = pipeline_gate.check_writer_vintage()
            finally:
                builtins.__import__ = real_import
        finally:
            pipeline_gate.changed_text_keys = original
        self.assertFalse(check.ok, "un controllo che non può girare non è un controllo superato")
        self.assertIn("venv", check.detail)


class TheSuiteSummaryQuotesTheVerdict(unittest.TestCase):
    """What the gate prints about the suite has to be the suite's verdict.

    The summary was the last three lines of stderr and stdout concatenated in
    that order, and unittest writes its verdict to stderr. So one test printing
    one line to stdout pushed "Ran 476 tests / OK" out of the message entirely,
    and the gate announced `[ok ] suite: 1 segnali, 150 parole, 0 link interni`.
    The verdict underneath was correct, because the regex reads the whole
    report. The line a person reads was not, and nobody reads these pull
    requests: the gate's output is the record, so a right answer printed as a
    wrong sentence is a defect on this chain and not a cosmetic one.
    """

    class _Result:
        def __init__(self, stdout, stderr, returncode=0):
            self.stdout, self.stderr, self.returncode = stdout, stderr, returncode

    def run_with(self, stdout, stderr, returncode=0):
        original = pipeline_gate.subprocess.run
        pipeline_gate.subprocess.run = lambda *a, **k: self._Result(stdout, stderr, returncode)
        try:
            return pipeline_gate._run_suite()
        finally:
            pipeline_gate.subprocess.run = original

    def test_a_test_printing_to_stdout_does_not_become_the_message(self):
        verdict, summary, _ = self.run_with(
            stdout="1   1 segnali, 150 parole, 0 link interni\n  [domanda] una domanda\n",
            stderr="....\n" + "-" * 70 + "\nRan 476 tests in 42.4s\n\nOK\n",
        )
        self.assertEqual(verdict, "ok")
        self.assertIn("OK", summary)
        self.assertIn("476", summary)
        self.assertNotIn("segnali", summary)

    def test_a_failure_still_reports_its_own_referto(self):
        verdict, summary, _ = self.run_with(
            stdout="rumore su stdout\n",
            stderr="Ran 476 tests in 42.4s\n\nFAILED (failures=1)\n",
            returncode=1,
        )
        self.assertEqual(verdict, "failed")
        self.assertIn("FAILED", summary)

    def test_a_crash_with_nothing_on_stderr_falls_back_to_the_whole_report(self):
        """A dead interpreter may leave stdout as the only trace there is, and
        an empty message would read as "no reason", which is worse than noise."""
        verdict, summary, _ = self.run_with(
            stdout="ultima riga prima del segfault\n", stderr="", returncode=-11,
        )
        self.assertEqual(verdict, "crashed")
        self.assertIn("segfault", summary)


class ACrashIsNotAFailure(unittest.TestCase):
    """Sono due cose diverse e vogliono reazioni opposte.

    Un `FAILED` è un bug con un referto, e ritentarlo sarebbe nasconderlo. Una
    morte senza referto non è una bocciatura, è un'assenza di risposta: qui
    capita circa una run su venticinque, dentro `build_indicator_view`, e
    trattarla come rossa fermerebbe uno stadio su un guasto che non esiste in una
    catena dove nessuno rilancia.
    """

    def run_with(self, *outcomes):
        calls = []
        queue = list(outcomes)

        def fake(cwd=None, modules=None):
            calls.append(1)
            return queue.pop(0)

        original = pipeline_gate._run_suite
        pipeline_gate._run_suite = fake
        try:
            return pipeline_gate.check_suite(), len(calls)
        finally:
            pipeline_gate._run_suite = original

    def test_a_real_failure_is_never_retried(self):
        check, calls = self.run_with(("failed", "FAILED (failures=1)", 1))
        self.assertFalse(check.ok)
        self.assertEqual(calls, 1, "ha ritentato un fallimento vero, cioè l'ha nascosto")

    def test_a_crash_without_a_verdict_gets_one_retry(self):
        check, calls = self.run_with(("crashed", "", -11), ("ok", "OK", 0))
        self.assertTrue(check.ok)
        self.assertEqual(calls, 2)
        self.assertIn("senza referto", check.detail)

    def test_two_crashes_in_a_row_are_red(self):
        """Il secondo tentativo è definitivo, o il ritentativo diventa un modo
        per ignorare un crash riproducibile."""
        check, calls = self.run_with(("crashed", "", -11), ("crashed", "", -11))
        self.assertFalse(check.ok)
        self.assertEqual(calls, 2)

    def test_a_failure_after_a_crash_is_still_a_failure(self):
        check, _ = self.run_with(("crashed", "", -11), ("failed", "FAILED (errors=2)", 1))
        self.assertFalse(check.ok)

    def test_green_with_a_dying_interpreter_stays_green_and_says_so(self):
        check, calls = self.run_with(("ok", "OK", -11))
        self.assertTrue(check.ok)
        self.assertEqual(calls, 1, "aveva un referto, non c'era niente da ritentare")
        self.assertIn("segnale 11", check.detail)

    def test_nothing_to_verify_is_still_a_pass(self):
        """Precision matters: a stage that touched no article owes no vintage."""
        original = pipeline_gate.changed_text_keys
        pipeline_gate.changed_text_keys = lambda base=None, cwd=None, include_worktree=True: []
        try:
            check = pipeline_gate.check_writer_vintage()
        finally:
            pipeline_gate.changed_text_keys = original
        self.assertTrue(check.ok, check.detail)


class Verdict(unittest.TestCase):
    def test_a_red_check_leaves_no_merge_mode(self):
        """There is nothing to negotiate between "the checks failed" and "but
        only a little", so a blocked verdict does not carry the stage's policy."""
        verdict = pipeline_gate.build_verdict(
            "verificatore", ["app/views.py"], [pipeline_gate.Check("finto", False, "rosso")]
        )
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["merge"], "blocked")

    def test_a_green_stage_may_merge_on_its_own(self):
        verdict = pipeline_gate.build_verdict(
            "verificatore", [pipeline_gate.VERIFICATIONS], [pipeline_gate.Check("finto", True)]
        )
        self.assertTrue(verdict["ok"])
        self.assertEqual(verdict["merge"], "auto")

    def test_the_admissions_stage_merges_on_the_local_gate_too(self):
        """Ogni stadio verde fonde `auto`: il cancello locale ha già girato la
        suite, e la CI remota (che `checks` aspetterebbe) non parte sulle PR via
        MCP. Detto sull'ammissione perché è quella che muove numeri vivi, cioè
        la prima candidata a tornare `checks` se un giorno la CI partisse."""
        verdict = pipeline_gate.build_verdict(
            "admissions", [pipeline_gate.CURATION], [pipeline_gate.Check("finto", True)]
        )
        self.assertEqual(verdict["merge"], "auto")


class InvariantDispatch(unittest.TestCase):
    """Gli invarianti di contenuto si smistano per **tipo-di-file toccato**, la
    firma per ruolo. La distinzione regge la demolizione: i tre ruoli rimasti
    compongono da soli i controlli dei tipi che toccano, senza che nessuno abbia
    dovuto elencarli per stadio. `invariant_labels` è pura, si prova senza git."""

    def _paths(self, *constants):
        # per un file la costante è già il percorso; per una directory (barra
        # finale) serve un .json sotto, che è la forma che il perimetro accetta.
        return [c + "x.json" if c.endswith("/") else c for c in constants]

    def test_each_living_stage_gets_the_invariants_of_what_it_touches(self):
        """Un invariante per tipo di file, non per nome di stadio: è ciò che ha
        reso la demolizione dei sette perimetri morti un taglio e non una
        riscrittura."""
        G = pipeline_gate
        self.assertEqual(G.invariant_labels("admissions", self._paths(G.CANDIDATES)), ["triage"])
        self.assertEqual(G.invariant_labels("admissions", self._paths(G.CURATION)), ["curation"])
        self.assertEqual(G.invariant_labels("admissions", self._paths(G.SOURCE_CANDIDATES)), [])
        self.assertEqual(G.invariant_labels("verificatore", self._paths(G.VERIFICATIONS)),
                         ["verifications"])
        self.assertEqual(G.invariant_labels("reader-editor", self._paths(G.READINGS)),
                         ["readings"])

    def test_the_articles_keep_their_invariants_without_an_owner(self):
        """Lo smistamento è per **tipo di file**, e questa è la prova che la
        distinzione non era accademica.

        Nessuno stadio ha più `content/indicators/` nel perimetro, quindi
        nessuno arriva qui portando un articolo. Ma `vintage` e `roles` restano
        agganciati al tipo di file e non a un nome di ruolo: il giorno in cui un
        percorso ci riporta un articolo (una run che ne tocca uno per sbaglio, o
        un ruolo futuro), i due controlli scattano da soli invece di essere
        rimessi a mano. `roles` è il controllo che master ha aggiunto mentre
        questo ramo demoliva i perimetri: un refuso in `roles_covered` e
        un'omissione voluta rendono la stessa pagina, e qui è l'ultimo punto in
        cui sono ancora distinguibili."""
        etichette = pipeline_gate.invariant_labels(
            "verificatore", self._paths(pipeline_gate.INDICATOR_TEXTS))
        self.assertEqual(etichette, ["vintage", "roles"])

    def test_the_reader_editor_does_not_sign(self):
        """Legge, non firma: come il verificatore, il suo verdetto è un file, non
        una responsabilità sul testo altrui."""
        G = pipeline_gate
        self.assertNotIn("signature", G.invariant_labels("reader-editor", self._paths(G.READINGS)))
        self.assertNotIn("reader-editor", G.ROLES_THAT_SIGN)

    def test_nobody_signs_any_more(self):
        """La firma era del revisore, poi del produttore che lo aveva assorbito.
        Nessuno dei due esiste: l'articolo lo scrive l'officina, che non è una
        run e al posto della firma ha `origine: officina` più il verdetto di
        `officina/lint.py`. I tre ruoli rimasti non toccano `content/indicators/`,
        quindi non hanno niente da firmare."""
        G = pipeline_gate
        self.assertEqual(G.ROLES_THAT_SIGN, ())
        for stadio in G.STAGE_PATHS:
            self.assertNotIn("signature",
                             G.invariant_labels(stadio, self._paths(G.INDICATOR_TEXTS)), stadio)

    def test_a_role_still_composes_the_invariants_of_everything_it_touches(self):
        """La composizione resta, ed è ciò che ha reso la demolizione un taglio
        e non una riscrittura: un ruolo che tocca due tipi di file prende gli
        invarianti di tutti e due, senza che nessuno li elenchi per lui. Lo
        diceva il produttore (curation + vintage + roles + signature); lo dice
        adesso l'ammissione, che è il solo ruolo rimasto a toccare più di un
        tipo."""
        G = pipeline_gate
        labels = G.invariant_labels(
            "admissions", self._paths(G.CURATION, G.CANDIDATES))
        self.assertEqual(set(labels), {"curation", "triage"})

    def test_admissions_composes_the_triage(self):
        G = pipeline_gate
        labels = G.invariant_labels("admissions", self._paths(G.CANDIDATES, G.SOURCE_CANDIDATES))
        self.assertEqual(labels, ["triage"])


class TheVerificationRegisterIsAppendOnly(unittest.TestCase):
    """Rilievi P2 di Codex sulla #49, su un repo git costruito qui.

    Questi due controlli leggono l'albero git, quindi non si possono provare
    passando righe a una funzione: serve una base con il registro dentro. Il
    repo è finto e minuscolo, e il punto è sempre lo stesso di questo file,
    far dire no al cancello prima di fargli dire sì.
    """

    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self._run("git", "init", "-q", "-b", "main")
        self._run("git", "config", "user.email", "t@example.com")
        self._run("git", "config", "user.name", "t")
        (self.repo / "data" / "pipeline" / "verifiche").mkdir(parents=True)
        (self.repo / "content" / "indicators").mkdir(parents=True)
        self.entry = {
            "lead": "Un lead.", "level": "regione", "vintage": 2024,
            "reviewed_at": "2026-07-27", "reviewed_vintage": 2024, "fonti": [],
            "sections": [{"role": "quadro", "h": None, "body": "Il quadro."}],
        }
        self._write_texts({"611": self.entry})
        self.fingerprint = verification_queue.prose_fingerprint(self.entry)
        self._write_register([self._row()])
        self._run("git", "add", "-A")
        self._run("git", "commit", "-qm", "base")

    def _run(self, *args):
        return subprocess.run(args, cwd=self.repo, capture_output=True, text=True)

    def _write_texts(self, texts):
        root = self.repo / "content" / "indicators"
        for stale in root.glob("*.json"):
            stale.unlink()
        for key, entry in texts.items():
            indicator_store.write(key, entry, root=root)

    def _write_register(self, rows):
        root = self.repo / "data" / "pipeline" / "verifiche"
        for stale in root.glob("*.json"):
            stale.unlink()
        for row in rows:
            verification_queue.write_verification(row, root=root)

    def _row(self, code="ter-611", level="regione", prosa=None, controllate="40",
             confermate="40", smentite="0", esito="pulito"):
        return {
            "code": code, "level": level, "at": "2026-07-27", "vintage": "2024",
            "reviewed_at": "2026-07-27", "prosa": prosa or self.fingerprint,
            "controllate": controllate, "confermate": confermate,
            "smentite": smentite, "non_verificabili": "0", "esito": esito,
            "rilievi": "",
        }

    def _check(self):
        # Il cancello legge lo store del repo vero per calcolare le impronte,
        # quindi va puntato a quello finto per la durata della prova.
        original = indicator_store.ROOT
        gate_root = pipeline_gate.PROJECT_ROOT
        indicator_store.ROOT = self.repo / "content" / "indicators"
        pipeline_gate.PROJECT_ROOT = self.repo
        try:
            return pipeline_gate.check_verifications(base="HEAD", cwd=self.repo)
        finally:
            indicator_store.ROOT = original
            pipeline_gate.PROJECT_ROOT = gate_root

    def test_an_unchanged_register_passes(self):
        self.assertTrue(self._check().ok, self._check().detail)

    def test_appending_an_honest_row_passes(self):
        self._write_texts({"611": self.entry, "72": self.entry})
        self._write_register([self._row(), self._row(code="ter-72")])
        check = self._check()
        self.assertTrue(check.ok, check.detail)

    def test_deleting_a_row_is_refused(self):
        """Il caso che passava: senza righe nuove il cancello diceva "nessuna
        verifica nuova da controllare" e il segnale spariva dalla coda del
        revisore con il verde."""
        self._write_register([])
        check = self._check()
        self.assertFalse(check.ok)
        self.assertIn("append-only", check.detail)

    def test_dropping_one_row_while_adding_another_is_refused(self):
        self._write_texts({"611": self.entry, "72": self.entry})
        self._write_register([self._row(code="ter-72")])
        check = self._check()
        self.assertFalse(check.ok)
        self.assertIn("append-only", check.detail)

    def test_rewriting_a_row_in_place_is_refused(self):
        """Riscrivere è cancellare con un passaggio in più: cambia che cosa dice
        una verifica passata senza lasciare traccia."""
        self._write_register([self._row(controllate="99", confermate="99")])
        check = self._check()
        self.assertFalse(check.ok)
        self.assertIn("append-only", check.detail)

    def test_a_row_whose_level_does_not_match_the_article_is_refused(self):
        """`build_queue` unisce su (codice, livello), quindi una riga col livello
        sbagliato passava il cancello e poi non copriva niente: la smentita
        restava scritta e invisibile."""
        self._write_register([self._row(), self._row(level="provincia")])
        check = self._check()
        self.assertFalse(check.ok)
        self.assertIn("livello", check.detail)

    def test_a_fingerprint_matching_nothing_is_refused(self):
        self._write_register([self._row(), self._row(prosa="deadbeefdeadbeef")])
        check = self._check()
        self.assertFalse(check.ok)
        self.assertIn("impronta", check.detail)

    def test_a_truncated_shard_is_refused_instead_of_skipped(self):
        """Lo stesso buco che la revisione ha trovato sulle letture, sul registro
        gemello: il caricatore delle letture è nato copiando questo, e ne aveva
        copiato il silenzio sui file illeggibili. Correggerne uno solo avrebbe
        lasciato al verificatore, che gira da settimane, il difetto che il
        reader-editor non ha più."""
        (self.repo / "data" / "pipeline" / "verifiche" / "ter-72-regione.json").write_text(
            '{"code": "ter-72", "contro', encoding="utf-8")
        check = self._check()
        self.assertFalse(check.ok)
        self.assertIn("illeggibili", check.detail)

    def test_a_run_that_adds_no_verification_stays_green(self):
        check = self._check()
        self.assertTrue(check.ok, check.detail)
        self.assertIn("nessuna verifica nuova", check.detail)


class TheReadingRegisterIsAppendOnly(unittest.TestCase):
    """Il registro delle letture, protetto come quello delle verifiche.

    Stesso repo git finto, stesse prove: append-only prima di tutto, righe
    credibili, impronta che combacia con un testo reale. Il reader-editor è un
    critico indipendente esattamente come il verificatore, quindi il suo registro
    non può essere più debole.
    """

    def setUp(self):
        from scripts import reading_queue
        self.reading_queue = reading_queue
        self._tmp = TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self._run("git", "init", "-q", "-b", "main")
        self._run("git", "config", "user.email", "t@example.com")
        self._run("git", "config", "user.name", "t")
        (self.repo / "data" / "pipeline" / "letture").mkdir(parents=True)
        (self.repo / "content" / "indicators").mkdir(parents=True)
        self.entry = {
            "lead": "Un lead.", "level": "regione", "vintage": 2024,
            "reviewed_at": "2026-07-27", "reviewed_vintage": 2024, "fonti": [],
            "sections": [{"role": "quadro", "h": None, "body": "Il quadro."}],
        }
        self._write_texts({"611": self.entry})
        self.fingerprint = self.reading_queue.reading_fingerprint(self.entry)
        self._write_register([self._row()])
        self._run("git", "add", "-A")
        self._run("git", "commit", "-qm", "base")

    def _run(self, *args):
        return subprocess.run(args, cwd=self.repo, capture_output=True, text=True)

    def _write_texts(self, texts):
        root = self.repo / "content" / "indicators"
        for stale in root.glob("*.json"):
            stale.unlink()
        for key, entry in texts.items():
            indicator_store.write(key, entry, root=root)

    def _write_register(self, rows):
        root = self.repo / "data" / "pipeline" / "letture"
        for stale in root.glob("*.json"):
            stale.unlink()
        for row in rows:
            self.reading_queue.write_reading(row, root=root)

    def _row(self, code="ter-611", level="regione", prosa=None, verdict="revise",
             comprehension=1):
        row = {
            "code": code, "level": level, "at": "2026-08-01",
            "reviewed_at": "2026-07-27", "prosa": prosa or self.fingerprint,
            "verdict": verdict, "hard_failures": [],
            # Una bocciatura senza nota non passa il cancello: è il punto
            # d'inciampo, cioè l'unica cosa che il produttore riceve per sapere
            # dove riscrivere.
            "note": "il quadro apre sulla meccanica" if verdict == "revise" else "",
        }
        for name in self.reading_queue.CRITERIA:
            row[name] = comprehension if name == "comprehension" else 2
        return row

    def _check(self):
        original = indicator_store.ROOT
        gate_root = pipeline_gate.PROJECT_ROOT
        indicator_store.ROOT = self.repo / "content" / "indicators"
        pipeline_gate.PROJECT_ROOT = self.repo
        try:
            return pipeline_gate.check_readings(base="HEAD", cwd=self.repo)
        finally:
            indicator_store.ROOT = original
            pipeline_gate.PROJECT_ROOT = gate_root

    def test_an_unchanged_register_passes(self):
        self.assertTrue(self._check().ok, self._check().detail)

    def test_appending_an_honest_row_passes(self):
        self._write_texts({"611": self.entry, "72": self.entry})
        self._write_register([self._row(), self._row(code="ter-72")])
        check = self._check()
        self.assertTrue(check.ok, check.detail)

    def test_deleting_a_row_is_refused(self):
        self._write_register([])
        check = self._check()
        self.assertFalse(check.ok)
        self.assertIn("append-only", check.detail)

    def test_rewriting_a_row_in_place_is_refused(self):
        self._write_register([self._row(comprehension=0)])
        check = self._check()
        self.assertFalse(check.ok)
        self.assertIn("append-only", check.detail)

    def test_an_incredible_row_is_refused(self):
        """Un verdetto ignoto non passa il cancello, come un contatore malformato
        non passa per le verifiche."""
        bad = self._row()
        bad["verdict"] = "forse"
        self._write_texts({"611": self.entry, "72": self.entry})
        self._write_register([self._row(), dict(bad, code="ter-72")])
        check = self._check()
        self.assertFalse(check.ok)

    def test_a_fingerprint_matching_nothing_is_refused(self):
        self._write_texts({"611": self.entry, "72": self.entry})
        self._write_register([self._row(), self._row(code="ter-72", prosa="deadbeefdeadbeef")])
        check = self._check()
        self.assertFalse(check.ok)
        self.assertIn("impronta", check.detail)

    def test_a_truncated_shard_is_refused_instead_of_skipped(self):
        """Il caso peggiore, perché è quello che passava verde.

        Una run che aggiunge una sola scheggia troncata non lascia nessuna riga
        da controllare: saltandola in silenzio il cancello diceva "nessuna
        lettura nuova" e il file veniva fuso lo stesso, illeggibile per la coda,
        che continua a considerare quell'articolo da leggere e a rilanciarlo.
        """
        (self.repo / "data" / "pipeline" / "letture" / "ter-72-regione.json").write_text(
            '{"code": "ter-72", "verd', encoding="utf-8")
        check = self._check()
        self.assertFalse(check.ok)
        self.assertIn("illeggibili", check.detail)

    def test_a_shard_that_is_not_an_object_is_refused(self):
        (self.repo / "data" / "pipeline" / "letture" / "ter-72-regione.json").write_text(
            '["ter-72"]', encoding="utf-8")
        check = self._check()
        self.assertFalse(check.ok)
        self.assertIn("illeggibili", check.detail)

    def test_a_run_that_adds_no_reading_stays_green(self):
        """La controprova: il rifiuto è delle schegge illeggibili aggiunte, non
        di una run che non tocca il registro (il produttore, l'ammissione)."""
        check = self._check()
        self.assertTrue(check.ok, check.detail)
        self.assertIn("nessuna lettura nuova", check.detail)


if __name__ == "__main__":
    unittest.main()


class TheBaseCheckStoppedPunishingAMovingMaster(unittest.TestCase):
    """Il difetto più costoso che questa catena abbia avuto.

    Bastava che `origin/master` non fosse un antenato di HEAD perché lo stadio
    leggesse `blocked`. Master però si muove di continuo, anche solo perché un
    altro stadio ha registrato l'esito di una run, quindi ogni pull request
    aperta da più di qualche minuto diventava rossa senza che il suo lavoro
    fosse cambiato. Peggio: il passo di merge che rifiutava una pull request
    scriveva su master, e quella scrittura faceva diventare rosse le pull
    request di tutti gli altri. Un rifiuto solo fermava la catena intera.

    La severità non serviva nemmeno: il diff si misura con i tre punti, che
    confrontano contro la base comune e restano esatti quando master va avanti.
    """

    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self._git("init", "-q", "-b", "master")
        self._git("config", "user.email", "t@example.com")
        self._git("config", "user.name", "t")
        (self.repo / "content" / "indicators").mkdir(parents=True)
        self._write("content/indicators/1.json", '{"key": "1", "lead": "base"}')
        self._git("add", "-A")
        self._git("commit", "-qm", "base")

    def _git(self, *args):
        return subprocess.run(("git",) + args, cwd=self.repo,
                              capture_output=True, text=True)

    def _write(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")

    def _diverge(self, lavoro=None):
        """Un branch che lavora, e master che intanto va avanti da solo.

        `lavoro` è il file che il branch cambia. Il default è un articolo
        perché quasi tutti i test qui misurano `changed_text_keys`, che legge
        `content/indicators/`; chi invece deve far passare il **perimetro** di
        uno stadio deve passare un percorso che uno stadio vivo possa toccare,
        perché dopo la demolizione gli articoli non sono di nessuno.
        """
        base = self._git("rev-parse", "HEAD").stdout.strip()
        self._git("checkout", "-qb", "lavoro")
        if lavoro:
            self._write(lavoro, '{"code": "ter-1", "esito": "pulito"}')
            self._git("add", "-A")
            self._git("commit", "-qm", "il mio lavoro")
        else:
            self._write("content/indicators/1.json", '{"key": "1", "lead": "riscritto"}')
            self._git("commit", "-qam", "il mio lavoro")
        self._git("checkout", "-q", base)
        self._git("branch", "-qf", "master", base)
        self._git("checkout", "-q", "master")
        self._write("content/indicators/2.json", '{"key": "2", "lead": "un altro stadio"}')
        self._git("add", "-A")
        self._git("commit", "-qm", "un altro stadio ha fuso")
        self._git("checkout", "-q", "lavoro")

    def test_a_master_that_moved_ahead_is_not_a_red_verdict(self):
        self._diverge()
        check = pipeline_gate.check_base_is_usable(base="master", cwd=self.repo)
        self.assertTrue(check.ok, check.detail)
        self.assertIn("andata avanti", check.detail)

    def test_and_the_diff_it_measures_is_still_only_this_branch(self):
        """La ragione per cui ammorbidire non costa niente: i tre punti
        confrontano contro la base comune, quindi il file che ha aggiunto
        l'altro stadio non compare fra i miei."""
        self._diverge()
        root = pipeline_gate.PROJECT_ROOT
        pipeline_gate.PROJECT_ROOT = self.repo
        try:
            paths = pipeline_gate.changed_paths(base="master", cwd=self.repo)
            keys = pipeline_gate.changed_text_keys(base="master", cwd=self.repo)
        finally:
            pipeline_gate.PROJECT_ROOT = root
        self.assertEqual(paths, ["content/indicators/1.json"])
        self.assertEqual(keys, ["1"])

    def test_no_common_ancestor_at_all_is_still_refused(self):
        """Lì non c'è davvero niente da misurare, e il verdetto sotto sarebbe
        finzione: è il caso che il controllo esiste per prendere."""
        self._git("checkout", "-q", "--orphan", "altrove")
        self._git("rm", "-rqf", ".")
        self._write("altro.txt", "niente in comune")
        self._git("add", "-A")
        self._git("commit", "-qm", "orfano")
        check = pipeline_gate.check_base_is_usable(base="master", cwd=self.repo)
        self.assertFalse(check.ok)
        self.assertIn("antenato in comune", check.detail)

    def _sibling_leaves_an_uncommitted_stray(self):
        """Un altro ruolo, nello stesso checkout condiviso, lascia un file non
        committato fuori dal perimetro di questo stadio. È la forma esatta del
        bug del checkout condiviso: il working tree porta l'incompiuto altrui."""
        self._write("app/intruso.py", "print('lavoro di un altrò)")

    def test_committed_only_ignores_a_siblings_uncommitted_file(self):
        self._diverge()
        self._sibling_leaves_an_uncommitted_stray()
        root = pipeline_gate.PROJECT_ROOT
        pipeline_gate.PROJECT_ROOT = self.repo
        try:
            with_wt = pipeline_gate.changed_paths(
                base="master", cwd=self.repo, include_worktree=True)
            committed = pipeline_gate.changed_paths(
                base="master", cwd=self.repo, include_worktree=False)
        finally:
            pipeline_gate.PROJECT_ROOT = root
        self.assertIn("app/intruso.py", with_wt)
        self.assertNotIn("app/intruso.py", committed)
        self.assertEqual(committed, ["content/indicators/1.json"])

    def test_a_siblings_stray_file_does_not_trip_blast_radius_when_committed_only(self):
        """committed_only è ciò che il passo di merge usa: al merge il lavoro
        dello stadio è già committato, e l'incompiuto di un altro ruolo nello
        stesso albero non è di questa run, quindi non deve bocciarla.

        Qui il branch committa dentro `data/pipeline/verifiche/` e non un
        articolo, perché il soggetto è il perimetro e nessuno stadio vivo ha
        gli articoli nel proprio. Il `setUp` continua a fondare su un articolo:
        è ciò che serve ai test vicini, che misurano `changed_text_keys`."""
        self._diverge(lavoro="data/pipeline/verifiche/ter-1.json")
        self._sibling_leaves_an_uncommitted_stray()
        root = pipeline_gate.PROJECT_ROOT
        pipeline_gate.PROJECT_ROOT = self.repo
        try:
            shared = pipeline_gate.changed_paths(
                base="master", cwd=self.repo, include_worktree=True)
            isolated = pipeline_gate.changed_paths(
                base="master", cwd=self.repo, include_worktree=False)
        finally:
            pipeline_gate.PROJECT_ROOT = root
        # Col working tree il perimetro del verificatore boccia il file altrui...
        self.assertIn("app/intruso.py", shared)
        self.assertFalse(pipeline_gate.check_blast_radius("verificatore", shared).ok)
        # ...senza, resta verde: il diff committato è tutto nel perimetro.
        self.assertEqual(isolated, ["data/pipeline/verifiche/ter-1.json"])
        self.assertTrue(pipeline_gate.check_blast_radius("verificatore", isolated).ok)


class TheJournalIsAppendOnlyToo(unittest.TestCase):
    """Il registro delle verifiche era già sorvegliato, il diario no.

    Un file per run toglie il conflitto ma non impedisce da solo di riscrivere
    la riga di qualcun altro, ed è l'unico modo di far sparire un `blocked`
    dalla storia. Nessun flusso legittimo passa di qui: l'agente aggiunge il
    proprio file e il passo di merge ne aggiunge un secondo, tutti e due nuovi.
    """

    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self._git("init", "-q", "-b", "master")
        self._git("config", "user.email", "t@example.com")
        self._git("config", "user.name", "t")
        self.runs = self.repo / "data" / "pipeline" / "runs"
        self.runs.mkdir(parents=True)
        self._write("vecchia.json", '{"run_id": "vecchia", "stage": "verificatore", "outcome": "blocked"}')
        self._git("add", "-A")
        self._git("commit", "-qm", "base")

    def _git(self, *args):
        return subprocess.run(("git",) + args, cwd=self.repo,
                              capture_output=True, text=True)

    def _write(self, name, text):
        (self.runs / name).write_text(text + "\n", encoding="utf-8")

    def _check(self, paths):
        root = pipeline_gate.PROJECT_ROOT
        pipeline_gate.PROJECT_ROOT = self.repo
        try:
            return pipeline_gate.check_run_is_recorded(
                "verificatore", paths, base="HEAD", cwd=self.repo)
        finally:
            pipeline_gate.PROJECT_ROOT = root

    def test_rewriting_an_older_run_is_refused(self):
        self._write("vecchia.json", '{"run_id": "vecchia", "stage": "verificatore", "outcome": "merged"}')
        check = self._check(["data/pipeline/runs/vecchia.json"])
        self.assertFalse(check.ok)
        self.assertIn("append-only", check.detail)

    def test_deleting_an_older_run_is_refused(self):
        (self.runs / "vecchia.json").unlink()
        check = self._check(["data/pipeline/runs/vecchia.json"])
        self.assertFalse(check.ok)
        self.assertIn("append-only", check.detail)

    def test_adding_your_own_row_passes(self):
        self._write("mia.json", '{"run_id": "mia", "stage": "verificatore", "outcome": "pr-open"}')
        check = self._check([
            "content/indicators/ter__920.json", "data/pipeline/runs/mia.json"])
        self.assertTrue(check.ok, check.detail)


class ADirectoryPerimeterTakesOnlyItsOwnFileType(unittest.TestCase):
    """I tre store contengono un tipo di file solo, e il resto della catena lo
    dà per scontato: `_touched_under` cerca `.json` per sapere che cosa è
    cambiato. Un file di altro tipo sarebbe dentro il perimetro e insieme
    invisibile a ogni controllo che ne legge il contenuto, cioè esattamente la
    forma di guasto già pagata con `analyst_notes.json`."""

    def test_a_json_inside_the_store_is_allowed(self):
        self.assertTrue(pipeline_gate.path_allowed(
            "data/pipeline/verifiche/bes__10AMB004.json",
            pipeline_gate.STAGE_PATHS["verificatore"]))

    def test_anything_else_inside_the_store_is_not(self):
        for stray in ("data/pipeline/verifiche/note.txt",
                      "data/pipeline/letture/bozza.md",
                      "data/pipeline/runs/appunti.yaml"):
            with self.subTest(path=stray):
                self.assertFalse(pipeline_gate.path_allowed(
                    stray, pipeline_gate.STAGE_PATHS["verificatore"]))

    def test_a_file_perimeter_is_untouched_by_the_rule(self):
        """Le voci senza barra restano uguaglianze esatte, estensione o no."""
        self.assertTrue(pipeline_gate.path_allowed(
            pipeline_gate.ISTAT_SERIES_CONFIG,
            pipeline_gate.STAGE_PATHS["admissions"]))


class TheGateReadsFilesFromTheSuppliedWorktree(unittest.TestCase):
    """La guardia importa il cancello dal checkout principale ma passa
    cwd=worktree (l'hook gira come $CLAUDE_PROJECT_DIR/scripts/agent_guard.py).
    Se il cancello leggesse i file dal principale invece che dal worktree, un
    diario appena committato nel worktree risulterebbe cancellato, e lo Stop
    hook rifiuterebbe una run bloccata che aveva committato la sua riga."""

    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.main = Path(self._tmp.name) / "main"
        self.main.mkdir()
        self._git("init", "-q", "-b", "master")
        self._git("config", "user.email", "t@example.com")
        self._git("config", "user.name", "t")
        (self.main / "data" / "pipeline" / "runs").mkdir(parents=True)
        (self.main / "data" / "pipeline" / "runs" / ".gitkeep").write_text("")
        self._git("add", "-A")
        self._git("commit", "-qm", "base")
        self.wt = Path(self._tmp.name) / "runs" / "r1"
        self._git("worktree", "add", "-q", "-b", "automation/writer-x", str(self.wt), "master")
        journal = self.wt / "data" / "pipeline" / "runs" / "writer-x.json"
        journal.write_text('{"stage": "verificatore", "outcome": "blocked"}')
        subprocess.run(("git", "add", "-A"), cwd=self.wt, capture_output=True)
        subprocess.run(("git", "commit", "-qm", "diario"), cwd=self.wt, capture_output=True)
        self._orig = pipeline_gate.PROJECT_ROOT
        pipeline_gate.PROJECT_ROOT = self.main.resolve()
        self.addCleanup(lambda: setattr(pipeline_gate, "PROJECT_ROOT", self._orig))

    def _git(self, *args):
        return subprocess.run(("git",) + args, cwd=self.main, capture_output=True, text=True)

    def test_a_journal_committed_in_the_worktree_is_added_not_gone(self):
        touched = pipeline_gate._touched_under(
            pipeline_gate.RUN_JOURNAL, base="master", cwd=str(self.wt))
        self.assertIn("data/pipeline/runs/writer-x.json", touched["added"])
        self.assertEqual(touched["gone"], [])

    def test_the_invariant_loaders_follow_the_worktree(self):
        # _read_csv e indicator_store/verification_queue leggono dal worktree, non
        # dal PROJECT_ROOT del modulo: un verdetto non valida la versione del
        # principale al posto di quella cambiata nel worktree.
        self.assertEqual(pipeline_gate._indicators_root(cwd=str(self.wt)),
                         self.wt.resolve() / "content" / "indicators")
        self.assertEqual(pipeline_gate._indicators_root(cwd=None),
                         self.main.resolve() / "content" / "indicators")


class TheContentShortcut(unittest.TestCase):
    """Una run che tocca solo articoli non esegue la suite intera.

    Vale il 92% del tempo del cancello (3,7 secondi contro 45), ed è il pezzo
    più grosso della cerimonia che faceva costare trentotto dollari un
    articolo. È anche il tipo di scorciatoia che si allarga da sola finché non
    protegge più niente, quindi qui si prova soprattutto quando **non** deve
    scattare.
    """

    def test_it_applies_to_a_diff_made_only_of_articles(self):
        self.assertTrue(pipeline_gate.content_only(
            ["content/indicators/1.json", "content/indicators/bes__X.json"]))

    def test_one_file_outside_the_articles_cancels_it(self):
        self.assertFalse(pipeline_gate.content_only(
            ["content/indicators/1.json", "app/data.py"]))

    def test_an_empty_diff_does_not_qualify(self):
        """Niente da controllare non è un motivo per controllare meno."""
        self.assertFalse(pipeline_gate.content_only([]))

    def test_a_non_json_under_the_articles_cancels_it(self):
        self.assertFalse(pipeline_gate.content_only(["content/indicators/README.md"]))

    def test_a_test_file_never_qualifies(self):
        self.assertFalse(pipeline_gate.content_only(
            ["tests/integration/test_indicator_texts.py"]))

    def test_the_shortcut_runs_the_content_modules_and_says_so(self):
        seen = {}

        def fake(cwd=None, modules=None):
            seen["modules"] = modules
            return "ok", "Ran 87 tests / OK", 0

        original = pipeline_gate._run_suite
        pipeline_gate._run_suite = fake
        try:
            check = pipeline_gate.check_suite(paths=["content/indicators/1.json"])
            self.assertEqual(seen["modules"], pipeline_gate.CONTENT_TESTS)
            self.assertIn("solo i moduli di contenuto", check.detail)

            pipeline_gate.check_suite(paths=["app/data.py"])
            self.assertIsNone(seen["modules"])
        finally:
            pipeline_gate._run_suite = original

    def test_the_content_modules_include_the_prose_guards(self):
        """Se qualcuno toglie di qui il modulo delle cifre, la scorciatoia
        smette di controllare proprio ciò che una run di contenuto rischia."""
        self.assertIn("tests.integration.test_indicator_texts",
                      pipeline_gate.CONTENT_TESTS)
        self.assertIn("tests.unit.test_officina_lint", pipeline_gate.CONTENT_TESTS)


if __name__ == "__main__":
    unittest.main()
