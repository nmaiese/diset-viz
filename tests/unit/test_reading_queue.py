"""La coda di lettura: il quarto asse, la leggibilita'.

Il reader-editor non corregge niente, come il verificatore, quindi tutto quello
che si puo' sbagliare sta in due posti: la regola che decide **quando una lettura
copre ancora la prosa** (l'impronta, riusata dal verificatore) e i controlli che
decidono **quando una riga di lettura si puo' credere**. Piu' il freno K-round,
che e' l'unica logica nuova di questo modulo. Tutto su dati sintetici.
"""

from __future__ import annotations

import unittest

from scripts import reading_queue as rq
from scripts import verification_queue as vq


def _entry(lead="Un lead che apre sulla geografia.", **extra):
    """Un articolo pubblicato: lead piu' i quattro ruoli con un corpo, firmato."""
    base = {
        "lead": lead,
        "level": "regione",
        "vintage": 2024,
        "reviewed_at": "2026-07-27",
        "reviewed_vintage": 2024,
        "fonti": [],
        "sections": [
            {"role": "definizione", "h": None, "body": "Che cosa misura."},
            {"role": "quadro", "h": None, "body": "Come si distribuisce."},
            {"role": "dinamica", "h": None, "body": "Come e' cambiato."},
            {"role": "limiti", "h": None, "body": "Che cosa non dice."},
        ],
    }
    base.update(extra)
    return base


def _reading(entry, code="ter-611", verdict="pass", hard_failures=None, note=None, **scores):
    if note is None:
        # Un `revise` senza nota non e' una lettura credibile: `row_problems` lo
        # rifiuta, quindi la fixture onesta ne porta una.
        note = "il quadro apre sulla meccanica" if verdict == "revise" else ""
    row = {
        "code": code,
        "level": entry.get("level") or "regione",
        "at": "2026-08-01",
        "reviewed_at": entry.get("reviewed_at", ""),
        "prosa": vq.prose_fingerprint(entry),
        "verdict": verdict,
        "hard_failures": hard_failures or [],
        "note": note,
    }
    for name in rq.CRITERIA:
        row[name] = scores.get(name, 2 if verdict == "pass" else 1)
    return row


class TheQueueCarriesTheReadersAddress(unittest.TestCase):
    """La riga di coda diventa il lancio di una riscrittura, quindi e' l'unico
    canale per cui il lavoro del reader-editor arriva al produttore. Buttare la
    nota e i criteri qui rendeva cieca la riscrittura."""

    def test_a_revise_row_carries_the_note_and_the_fallen_criteria(self):
        entry = _entry()
        reading = _reading(entry, verdict="revise", structure=0, cognitive_load=1,
                           focus=2, note="la meccanica FTE apre la narrazione")
        rows = rq.build_queue({"611": entry}, [reading])
        self.assertEqual(rows[0]["note"], "la meccanica FTE apre la narrazione")
        # dal piu' basso, e i criteri al massimo non entrano
        self.assertEqual(rows[0]["low_scores"][0], ("structure", 0))
        self.assertIn(("cognitive_load", 1), rows[0]["low_scores"])
        self.assertNotIn("focus", [name for name, _ in rows[0]["low_scores"]])

    def test_an_unread_row_has_nothing_to_carry(self):
        rows = rq.build_queue({"611": _entry()}, [])
        self.assertEqual(rows[0]["note"], "")
        self.assertEqual(rows[0]["low_scores"], [])


class TheReadingCoversAText(unittest.TestCase):
    def test_a_published_article_with_no_reading_is_unread(self):
        rows = rq.build_queue({"611": _entry()}, [])
        self.assertEqual(len(rq.unread(rows)), 1)
        self.assertEqual(rows[0]["status"], "unread")

    def test_an_unsigned_article_is_not_eligible(self):
        """Leggere un non firmato misura lo scrittore, non e' la coda di lettura."""
        rows = rq.build_queue({"611": _entry(reviewed_at="")}, [])
        self.assertEqual(rows, [])

    def test_an_incomplete_article_is_not_eligible(self):
        entry = _entry()
        entry["sections"] = entry["sections"][:2]  # solo definizione + quadro
        self.assertEqual(rq.build_queue({"611": entry}, []), [])

    def test_a_pass_reading_leaves_the_queue_clean(self):
        entry = _entry()
        rows = rq.build_queue({"611": entry}, [_reading(entry, verdict="pass")])
        self.assertEqual(rows[0]["status"], "clean")
        self.assertEqual(rq.unread(rows), [])
        self.assertEqual(rq.to_revise(rows), [])

    def test_a_revise_reading_sends_to_the_producer(self):
        entry = _entry()
        rows = rq.build_queue({"611": entry}, [_reading(entry, verdict="revise")])
        self.assertEqual(rows[0]["status"], "revise")
        self.assertEqual(len(rq.to_revise(rows)), 1)

    def test_a_reading_of_stale_prose_does_not_cover_the_new_prose(self):
        """La riscrittura cambia l'impronta: la vecchia lettura non copre piu'."""
        old = _entry(lead="Vecchio lead.")
        stale = _reading(old, verdict="pass")
        new = _entry(lead="Lead riscritto per leggibilita'.")
        rows = rq.build_queue({"611": new}, [stale])
        self.assertEqual(rows[0]["status"], "unread")


class TheBrakeBoundsTheLoop(unittest.TestCase):
    def _revised_versions(self, code, n):
        """n letture `revise`, ognuna su una versione diversa della prosa."""
        readings = []
        for i in range(n):
            version = _entry(lead=f"Lead versione {i}.")
            readings.append(_reading(version, code=code, verdict="revise"))
        return readings

    def test_below_the_cap_a_revise_still_goes_to_the_producer(self):
        # La corrente bocciata e' la (READABILITY_ROUNDS - 1)-esima versione
        # bocciata in totale: ancora sotto il tetto, si lancia il produttore.
        current = _entry(lead="Lead corrente ancora sotto il tetto.")
        readings = self._revised_versions("ter-611", rq.READABILITY_ROUNDS - 2)
        readings.append(_reading(current, code="ter-611", verdict="revise"))
        rows = rq.build_queue({"611": current}, readings)
        self.assertEqual(rows[0]["revised_rounds"], rq.READABILITY_ROUNDS - 1)
        self.assertEqual(rows[0]["status"], "revise")

    def test_at_the_cap_the_code_is_parked_not_relaunched(self):
        # La corrente bocciata e' la READABILITY_ROUNDS-esima versione bocciata:
        # il freno morde, non si lancia una riscrittura in piu'.
        current = _entry(lead="Lead corrente al tetto.")
        readings = self._revised_versions("ter-611", rq.READABILITY_ROUNDS - 1)
        readings.append(_reading(current, code="ter-611", verdict="revise"))
        rows = rq.build_queue({"611": current}, readings)
        self.assertEqual(rows[0]["revised_rounds"], rq.READABILITY_ROUNDS)
        self.assertEqual(rows[0]["status"], "parked")
        self.assertEqual(rq.to_revise(rows), [])

    def test_a_pass_does_not_count_toward_the_cap(self):
        """Solo le bocciature contano: un pass in mezzo non consuma un round."""
        readings = self._revised_versions("ter-611", rq.READABILITY_ROUNDS)
        current = _entry(lead="Lead finalmente leggibile.")
        readings.append(_reading(current, code="ter-611", verdict="pass"))
        rows = rq.build_queue({"611": current}, readings)
        self.assertEqual(rows[0]["status"], "clean")


class ARowIsBelievedOrItIsNot(unittest.TestCase):
    def _valid(self, **over):
        row = _reading(_entry(), verdict="revise", comprehension=1)
        row.update(over)
        return row

    def test_a_clean_revise_row_has_no_problems(self):
        self.assertEqual(rq.row_problems(self._valid()), [])

    def test_a_clean_pass_row_has_no_problems(self):
        self.assertEqual(rq.row_problems(_reading(_entry(), verdict="pass")), [])

    def test_a_nested_hard_failure_is_refused_before_it_can_crash_the_launcher(self):
        """Il gemello della nota storta, sull'altro campo: `[["numeric_overload"]]`
        e' una lista non vuota, quindi passava il controllo di coerenza, e poi
        l'elemento interno finiva in `", ".join(...)` nel motivo del lancio e in
        `review_queue`, con un TypeError che ferma il catalogo intero."""
        problems = rq.row_problems(self._valid(hard_failures=[["numeric_overload"]]))
        self.assertTrue(any("ignoti" in p for p in problems), problems)

    def test_a_hard_failure_outside_the_vocabulary_is_refused(self):
        """Le sette classi sono un vocabolario chiuso: una inventata da una run
        non vorrebbe dire niente per il produttore che la legge."""
        problems = rq.row_problems(self._valid(hard_failures=["troppo_lungo"]))
        self.assertTrue(any("ignoti" in p for p in problems), problems)

    def test_the_queue_drops_a_nested_failure_that_slipped_through(self):
        entry = _entry()
        reading = _reading(entry, verdict="revise",
                           hard_failures=[["numeric_overload"], "filler_section"])
        rows = rq.build_queue({"611": entry}, [reading])
        self.assertEqual(rows[0]["hard_failures"], ["filler_section"])

    def test_the_vocabulary_mirrors_the_prompt(self):
        """Le sette classi vivono in `.claude/agents/reader-editor.md`: se una
        cade o cambia nome li', questo test lo dice invece di lasciare il
        cancello a rifiutare una classe legittima."""
        from pathlib import Path
        prompt = (Path(__file__).resolve().parents[2]
                  / ".claude" / "agents" / "reader-editor.md").read_text(encoding="utf-8")
        for name in rq.HARD_FAILURES:
            self.assertIn(f"`{name}`", prompt)

    def test_a_mute_revise_is_not_believed(self):
        """Una bocciatura senza il punto d'inciampo e' un'opinione, e rimette la
        riscrittura a indovinare: e' esattamente la riscrittura cieca che questa
        catena cerca di evitare."""
        problems = rq.row_problems(self._valid(note="   "))
        self.assertTrue(any("senza nota" in p for p in problems), problems)

    def test_a_note_that_is_not_a_string_is_refused_before_it_can_crash_the_queue(self):
        """`build_queue` fa `.strip()` su questo campo: una nota scritta come
        lista (l'errore piu' facile in un JSON a mano) fermerebbe la coda, il
        lanciatore e la coda del revisore per il catalogo intero."""
        problems = rq.row_problems(self._valid(note=["la meccanica apre"]))
        self.assertTrue(any("non e' una stringa" in p for p in problems), problems)

    def test_the_queue_survives_a_shard_that_slipped_through(self):
        """Difesa in profondita': il cancello rifiuta la nota storta, ma la coda
        gira anche su cio' che e' gia' fuso e non deve morirci sopra."""
        entry = _entry()
        reading = _reading(entry, verdict="revise", note=["storta"])
        rows = rq.build_queue({"611": entry}, [reading])
        self.assertEqual(rows[0]["note"], "")

    def test_a_score_out_of_range_is_a_problem(self):
        self.assertTrue(rq.row_problems(self._valid(comprehension=3)))

    def test_an_unknown_verdict_is_a_problem(self):
        self.assertTrue(rq.row_problems(self._valid(verdict="maybe")))

    def test_a_missing_fingerprint_is_a_problem(self):
        self.assertTrue(rq.row_problems(self._valid(prosa="")))

    def test_a_pass_with_a_hard_failure_is_contradictory(self):
        row = _reading(_entry(), verdict="pass")
        row["hard_failures"] = ["lead_requires_methodology"]
        self.assertTrue(rq.row_problems(row))

    def test_a_revise_with_all_max_and_no_failure_is_contradictory(self):
        row = _reading(_entry(), verdict="revise")
        for name in rq.CRITERIA:
            row[name] = 2
        row["hard_failures"] = []
        self.assertTrue(rq.row_problems(row))

    def test_a_revise_justified_by_a_hard_failure_alone_is_fine(self):
        row = _reading(_entry(), verdict="revise")
        for name in rq.CRITERIA:
            row[name] = 2
        row["hard_failures"] = ["thesis_unidentifiable"]
        self.assertEqual(rq.row_problems(row), [])


class TheStoreRoundTrips(unittest.TestCase):
    def test_write_then_load_is_identity(self):
        import tempfile
        from pathlib import Path
        entry = _entry()
        row = _reading(entry, verdict="revise", hard_failures=["numeric_overload"])
        with tempfile.TemporaryDirectory() as tmp:
            path = rq.write_reading(row, root=tmp)
            self.assertTrue(path.exists())
            loaded = rq.load_readings(tmp)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["verdict"], "revise")
            self.assertEqual(loaded[0]["prosa"], vq.prose_fingerprint(entry))

    def test_the_file_name_is_the_three_key_fields(self):
        entry = _entry()
        row = _reading(entry)
        name = rq.reading_name(row)
        self.assertEqual(name, f"ter-611__regione__{vq.prose_fingerprint(entry)}.json")


if __name__ == "__main__":
    unittest.main()
