"""Lo stadio che misura lo stadio prima.

Il verificatore non corregge niente, quindi tutto quello che si puo' sbagliare sta
in due posti: la regola che decide **quando una verifica e' ancora valida**, e i
controlli che decidono **quando una riga si puo' credere**. Sono provati qui su
dati sintetici, piu' due ancore sul repo vero per le cose che il codice non puo'
sapere da solo (che lo stadio sia registrato in tutti i posti che lo pretendono).
"""

from __future__ import annotations

import unittest

from scripts import pipeline_gate, pipeline_log, pipeline_status, review_queue
from scripts import verification_queue as vq


def _entry(lead="Un lead.", quadro="Il quadro.", **extra):
    base = {
        "lead": lead,
        "level": "regione",
        "vintage": 2024,
        "reviewed_at": "2026-07-27",
        "reviewed_vintage": 2024,
        "fonti": [],
        "sections": [{"role": "quadro", "h": None, "body": quadro}],
    }
    base.update(extra)
    return base


def _row(entry, code="ter-611", **extra):
    row = {
        "code": code,
        "level": entry.get("level") or "regione",
        "at": "2026-07-27",
        "vintage": entry["vintage"],
        "reviewed_at": entry.get("reviewed_at", ""),
        "prosa": vq.prose_fingerprint(entry),
        "controllate": "40",
        "confermate": "40",
        "smentite": "0",
        "non_verificabili": "0",
        "esito": "pulito",
        "rilievi": "",
    }
    row.update({k: str(v) for k, v in extra.items()})
    return row


class TheFingerprintIsAboutTheText(unittest.TestCase):
    def test_the_same_prose_hashes_the_same(self):
        self.assertEqual(vq.prose_fingerprint(_entry()), vq.prose_fingerprint(_entry()))

    def test_whitespace_is_not_a_change(self):
        self.assertEqual(
            vq.prose_fingerprint(_entry(lead="Un   lead.\n")),
            vq.prose_fingerprint(_entry(lead="Un lead.")),
        )

    def test_reordering_the_sections_is_not_a_change(self):
        """Cambiare l'ordine non cambia niente di quello che un verificatore ha
        letto, e invalidare la verifica per quello sarebbe churn."""
        one = _entry()
        one["sections"] = [
            {"role": "quadro", "body": "A"}, {"role": "limiti", "body": "B"},
        ]
        other = _entry()
        other["sections"] = [
            {"role": "limiti", "body": "B"}, {"role": "quadro", "body": "A"},
        ]
        self.assertEqual(vq.prose_fingerprint(one), vq.prose_fingerprint(other))

    def test_one_rewritten_word_is_a_change(self):
        self.assertNotEqual(
            vq.prose_fingerprint(_entry(quadro="Il quadro.")),
            vq.prose_fingerprint(_entry(quadro="Il quadro, rivisto.")),
        )

    def test_moving_a_sentence_between_sections_is_a_change(self):
        """L'impronta e' per ruolo, non sul testo appiccicato: spostare una frase
        dal quadro ai limiti cambia che cosa dice la pagina in quel punto."""
        one = _entry()
        one["sections"] = [{"role": "quadro", "body": "A B"}, {"role": "limiti", "body": ""}]
        other = _entry()
        other["sections"] = [{"role": "quadro", "body": "A"}, {"role": "limiti", "body": "B"}]
        self.assertNotEqual(vq.prose_fingerprint(one), vq.prose_fingerprint(other))


class TheQueueDrainsAndRefills(unittest.TestCase):
    def test_a_signed_article_with_no_verification_is_waiting(self):
        rows = vq.build_queue({"611": _entry()}, [])
        self.assertEqual(len(vq.waiting(rows)), 1)
        self.assertFalse(rows[0]["verified"])

    def test_an_unsigned_article_is_not_waiting(self):
        """Verificare un articolo non firmato misura lo scrittore, che e' un
        esperimento utile una volta e una coda inutile sempre: il revisore sta per
        riscrivere quelle frasi comunque."""
        rows = vq.build_queue({"611": _entry(reviewed_at="", reviewed_vintage=None)}, [])
        self.assertEqual(vq.waiting(rows), [])
        self.assertFalse(rows[0]["verifiable"])

    def test_an_article_from_the_officina_enters_without_a_signature(self):
        """La macchina nuova non ha un revisore, e senza questa porta i suoi
        articoli restavano invisibili all'unico passo di falsificazione
        indipendente della catena: 377 in catalogo, 50 firmati, e i tre
        dell'officina fuori."""
        entry = _entry(reviewed_at="", reviewed_vintage=None, origine=vq.OFFICINA)
        rows = vq.build_queue({"611": entry}, [])
        self.assertTrue(rows[0]["verifiable"])
        self.assertEqual(len(vq.waiting(rows)), 1)

    def test_a_signature_that_does_not_match_the_vintage_is_not_verifiable(self):
        entry = _entry(reviewed_vintage=2023)
        rows = vq.build_queue({"611": entry}, [])
        self.assertFalse(rows[0]["verifiable"])

    def test_a_verified_article_leaves_the_queue(self):
        entry = _entry()
        rows = vq.build_queue({"611": entry}, [_row(entry)])
        self.assertEqual(vq.waiting(rows), [])
        self.assertTrue(rows[0]["verified"])

    def test_rewriting_the_prose_puts_it_back(self):
        """Il cuore dello stadio. La verifica riguarda un testo, quindi scade
        quando quel testo cambia, e nient'altro la fa scadere."""
        verified = _row(_entry())
        rewritten = _entry(quadro="Il quadro, riscritto dal revisore.")
        rows = vq.build_queue({"611": rewritten}, [verified])
        self.assertEqual(len(vq.waiting(rows)), 1)
        self.assertTrue(rows[0]["stale"], "va distinto da un articolo mai verificato")

    def test_the_rewritten_ones_come_first(self):
        one, two = _entry(), _entry(lead="Un altro lead.")
        rows = vq.build_queue(
            {"611": _entry(quadro="riscritto"), "72": two},
            [_row(one, code="ter-611")],
        )
        self.assertEqual([r["code"] for r in vq.waiting(rows)][0], "ter-611")

    def test_a_verification_of_a_text_nobody_published_covers_nothing(self):
        """Una riga con un'impronta che non corrisponde a niente non deve poter
        far uscire un articolo dalla coda: sarebbe il modo piu' semplice di
        dichiarare verificato tutto il catalogo."""
        rows = vq.build_queue({"611": _entry()}, [_row(_entry(), prosa="0000000000000000")])
        self.assertEqual(len(vq.waiting(rows)), 1)


class ARefutationGoesBackToTheReviewer(unittest.TestCase):
    REFUTED = {"smentite": 1, "confermate": 39, "esito": "smentito",
               "rilievi": "quadro/classifica: una frase"}

    def test_it_is_open_while_the_refuted_prose_is_still_there(self):
        entry = _entry()
        found = review_queue.open_refutations({"611": entry}, [_row(entry, **self.REFUTED)])
        self.assertIn(("ter-611", "regione"), found)

    def test_rewriting_it_closes_the_refutation(self):
        """Chiuso vuol dire "qualcuno l'ha riscritta", e l'articolo torna in coda
        al verificatore. Le due code si passano il lavoro senza che nessuna delle
        due cancelli una riga dell'altra."""
        verified = _row(_entry(), **self.REFUTED)
        rewritten = _entry(quadro="Il quadro, corretto.")
        self.assertEqual(review_queue.open_refutations({"611": rewritten}, [verified]), {})
        rows = vq.build_queue({"611": rewritten}, [verified])
        self.assertEqual(len(vq.waiting(rows)), 1)

    def test_an_open_refutation_invalidates_the_signature(self):
        """Il difetto trovato provando il segnale invece di fidarsi: il peso era
        60 e due righe dopo lo azzeravamo, perche' l'articolo e' firmato. Il
        segnale c'era, l'articolo restava fuori dalla coda di lettura."""
        entry = _entry()
        refutations = review_queue.open_refutations({"611": entry}, [_row(entry, **self.REFUTED)])
        row = review_queue.assess("611", entry, _view(), definitions={}, refutations=refutations)
        self.assertIn("smentita", row["flags"])
        self.assertGreater(row["score"], 0, "una smentita aperta deve riaprire l'articolo")
        self.assertEqual(row["reviewed_at"], "", "la firma non vale piu'")

    def test_without_a_refutation_a_signed_article_stays_out(self):
        row = review_queue.assess("611", _entry(), _view(), definitions={}, refutations={})
        self.assertEqual(row["score"], 0)


def _view():
    return {
        "meta": {"family": "territorial", "raw_id": "611", "name": "Un indicatore",
                 "indexable": True, "quality_life_scored": False},
        "levels": [{"key": "regione",
                    "stats": {"year_avg": 40.73, "gap_abs": 15.60},
                    "best": {"value": 48.30}, "worst": {"value": 32.70},
                    "annual_change": {"average_delta": 0.74}}],
    }


class ARowYouCannotBelieve(unittest.TestCase):
    def test_zero_checked_claims_is_refused(self):
        """Senza `controllate`, "zero smentite" e "non ho guardato" sono lo stesso
        zero, ed e' l'unico modo in cui questo stadio puo' mentire."""
        problems = vq.row_problems(_row(_entry(), controllate=0, confermate=0))
        self.assertTrue(any("non ha guardato" in p for p in problems), problems)

    def test_the_parts_must_sum_to_the_total(self):
        problems = vq.row_problems(_row(_entry(), controllate=40, confermate=10))
        self.assertTrue(any("i conti non tornano" in p for p in problems), problems)

    def test_the_outcome_must_agree_with_the_count(self):
        problems = vq.row_problems(_row(_entry(), smentite=2, confermate=38, esito="pulito"))
        self.assertTrue(any("pulito" in p for p in problems), problems)

    def test_a_row_without_a_fingerprint_is_refused(self):
        problems = vq.row_problems(_row(_entry(), prosa=""))
        self.assertTrue(any("impronta" in p for p in problems), problems)

    def test_a_good_row_has_no_problems(self):
        self.assertEqual(vq.row_problems(_row(_entry())), [])


class TheStageIsRegisteredEverywhere(unittest.TestCase):
    """Uno stadio nuovo e' inchiodato in tre posti che non si parlano, e il
    cancello lo *rifiuta* invece di degradarlo se manca da uno."""

    def test_the_gate_knows_it_and_gives_it_a_merge_mode(self):
        self.assertIn("verificatore", pipeline_gate.STAGE_PATHS)
        self.assertIn("verificatore", pipeline_gate.MERGE_POLICY)

    def test_it_may_not_touch_the_prose(self):
        """L'assenza di content/indicators/ dal perimetro *e'* la definizione
        dello stadio: uno stadio che ripara i propri rilievi corregge i propri
        compiti, che e' il difetto che esiste per prendere."""
        self.assertNotIn(pipeline_gate.INDICATOR_TEXTS,
                         pipeline_gate.STAGE_PATHS["verificatore"])

    def test_the_log_and_the_status_know_it_too(self):
        self.assertIn("verificatore", pipeline_log.STAGES)
        self.assertIn("verificatore", pipeline_status.STAGE_ORDER)
        self.assertIn("verificatore", pipeline_status.AGENT_OF)
        self.assertIn("verificatore", pipeline_status.BUILDERS)

    def test_it_is_the_last_stage(self):
        self.assertEqual(pipeline_status.STAGE_ORDER[-1], "verificatore")

    def test_its_agent_file_is_named_after_the_stage(self):
        """Il file si chiamava `indicator-verifier.md` mentre lo stadio si
        chiamava `verificatore`, e la differenza esisteva solo per essere
        tradotta da un dizionario. Adesso combaciano, e questo test e' il
        controllo per il solo stadio che aveva il problema (l'invariante su
        tutti e tre sta in `test_docs_match_the_code.py`)."""
        agent = pipeline_gate.PROJECT_ROOT / ".claude" / "agents" / "verificatore.md"
        self.assertTrue(agent.exists(), "lo stadio non ha un agente")
        self.assertIn("name: verificatore", agent.read_text(encoding="utf-8"))

    def test_the_committed_register_is_readable_and_credible(self):
        rows = vq.load_verifications()
        self.assertTrue(rows, "il registro delle verifiche e' vuoto")
        for row in rows:
            with self.subTest(code=row.get("code")):
                self.assertEqual(vq.row_problems(row), [])


class TheGateRefusesARowItCannotBelieve(unittest.TestCase):
    """I casi provati a mano contro il repo vero, inchiodati qui.

    `check_verifications` legge il git tree, quindi qui si prova la parte pura,
    `row_problems`, piu' la regola sulle impronte, che e' l'unica del cancello che
    non e' un inoltro.
    """

    def test_every_bad_row_shape_is_named(self):
        entry = _entry()
        cases = {
            "controllate a zero": dict(controllate=0, confermate=0),
            "parziali che non sommano": dict(controllate=40, confermate=3),
            "esito che non combacia": dict(controllate=40, confermate=38, smentite=2,
                                           esito="pulito"),
            "senza impronta": dict(prosa=""),
            "data non valida": dict(at="ieri"),
            "esito inventato": dict(esito="quasi"),
        }
        for label, mutation in cases.items():
            with self.subTest(label):
                self.assertTrue(vq.row_problems(_row(entry, **mutation)),
                                f"{label} passa e non dovrebbe")

    def test_a_fingerprint_from_the_previous_version_is_legitimate(self):
        """Il caso che ha corretto il cancello. Il verificatore legge un articolo,
        calcola l'impronta e apre la PR; nel frattempo la Routine del revisore
        fonde una correzione sullo stesso articolo. L'impronta della run resta
        quella del testo che ha letto, ed e' onesta: pretendere quella di adesso
        bloccava una run corretta ogni volta che due stadi si incrociavano."""
        read = _entry()
        meanwhile = _entry(quadro="Il quadro, corretto dal revisore.")
        row = _row(read)
        # La riga non corrisponde al testo di adesso...
        self.assertNotEqual(row["prosa"], vq.prose_fingerprint(meanwhile))
        # ...ma corrisponde a una versione che il repo ha avuto, e non e' un errore
        # di forma: `row_problems` non ha niente da dire.
        self.assertEqual(vq.row_problems(row), [])


class TheHeadingIsProseToo(unittest.TestCase):
    """Rilievo P2 di Codex sulla #49, vero e provato con un caso del repo.

    118 sezioni portano un h2 scritto a mano, sono visibili in pagina e fanno
    affermazioni. `ter-651` intitola la sua dinamica "Cinque anni di guadagni, un
    anno che ne toglie piu' della meta'", e il verificatore di quell'articolo l'ha
    contata e confermata (+1,413 contro -0,855, il 61%). Con l'impronta sul solo
    body, una verifica pulita continuava a coprire un titolo sostituito, e
    correggere un titolo smentito non riapriva l'articolo.
    """

    def _with_heading(self, heading):
        entry = _entry()
        entry["sections"] = [{"role": "quadro", "h": heading, "body": "Il quadro."}]
        return entry

    def test_changing_only_the_heading_changes_the_fingerprint(self):
        self.assertNotEqual(
            vq.prose_fingerprint(self._with_heading("Un titolo")),
            vq.prose_fingerprint(self._with_heading("Un altro titolo")),
        )

    def test_it_requeues_the_article(self):
        read = self._with_heading("Un titolo")
        rewritten = self._with_heading("Un titolo corretto")
        rows = vq.build_queue({"611": rewritten}, [_row(read)])
        self.assertEqual(len(vq.waiting(rows)), 1)

    def test_repairing_a_refuted_heading_closes_the_refutation(self):
        read = self._with_heading("Un titolo falso")
        verified = _row(read, smentite=1, confermate=39, esito="smentito", rilievi="quadro/h")
        self.assertIn(("ter-611", "regione"),
                      review_queue.open_refutations({"611": read}, [verified]))
        repaired = self._with_heading("Un titolo vero")
        self.assertEqual(review_queue.open_refutations({"611": repaired}, [verified]), {})

    def test_a_missing_heading_is_not_a_change(self):
        """`h: null` e `h: ""` sono la stessa cosa: il template compone il titolo."""
        one, other = _entry(), _entry()
        one["sections"] = [{"role": "quadro", "h": None, "body": "A"}]
        other["sections"] = [{"role": "quadro", "h": "", "body": "A"}]
        self.assertEqual(vq.prose_fingerprint(one), vq.prose_fingerprint(other))


class CountersMustBeNonNegativeIntegers(unittest.TestCase):
    """Rilievo P2 di Codex sulla #49, con il suo esempio esatto."""

    def test_the_negative_refutation_is_refused(self):
        """`controllate=40, confermate=41, smentite=-1` sommava a 40 e passava
        ogni controllo, mentre `smentite > 0` restava falso: la smentita era
        registrata e invisibile allo stesso tempo."""
        problems = vq.row_problems(_row(_entry(), controllate=40, confermate=41,
                                        smentite=-1, esito="smentito"))
        self.assertTrue(any("interi non negativi" in p for p in problems), problems)

    def test_a_non_numeric_counter_is_not_a_zero(self):
        problems = vq.row_problems(_row(_entry(), controllate="quaranta"))
        self.assertTrue(any("interi non negativi" in p for p in problems), problems)

    def test_the_bad_counter_is_named(self):
        problems = vq.row_problems(_row(_entry(), smentite="uno"))
        self.assertIn("smentite", problems[0])


if __name__ == "__main__":
    unittest.main()
