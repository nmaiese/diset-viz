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


def _reading(entry, code="ter-611", verdict="pass", hard_failures=None, **scores):
    row = {
        "code": code,
        "level": entry.get("level") or "regione",
        "at": "2026-08-01",
        "reviewed_at": entry.get("reviewed_at", ""),
        "prosa": vq.prose_fingerprint(entry),
        "verdict": verdict,
        "hard_failures": hard_failures or [],
        "note": "",
    }
    for name in rq.CRITERIA:
        row[name] = scores.get(name, 2 if verdict == "pass" else 1)
    return row


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
        row = _reading(entry, verdict="revise", hard_failures=["cognitive_overload"])
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
