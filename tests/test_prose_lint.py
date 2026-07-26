"""The mechanical half of the writing rubric.

Two failure modes matter here and they pull in opposite directions. A pattern
that never fires is worse than no pattern: it reports zero, the summary reads as
progress, and nobody notices the check died. A pattern that fires on correct
Italian is worse still, because a linter that cries wolf gets ignored and then it
protects nothing. So every check is pinned from both sides, on a sentence that
must trip it and on prose that must not.
"""

import unittest

from scripts import prose_lint


def _entry(text):
    return {"lead": text, "sections": []}


class EveryCheckFires(unittest.TestCase):
    CASES = {
        "lessico": "Il dato sottolinea la distanza tra le due aree.",
        "intervallo": "Il fenomeno cresce dal Nord al Sud senza eccezioni.",
        "riassunto": "La quota sale. Nel complesso il quadro resta diseguale.",
        "doppio": "Lavora quasi la metà (48%) delle donne in età da lavoro.",
        "slogan": "Non è una classifica, è una fotografia del paese.",
        "domanda": "Il mercato assume di più o le giovani restano fuori?",
    }

    def test_each_pattern_catches_its_own_case(self):
        for name, text in self.CASES.items():
            with self.subTest(check=name):
                found = prose_lint.inspect(_entry(text))
                self.assertIn(name, found["hits"])

    def test_each_pattern_catches_only_its_own_case(self):
        """A check that also fires on the other five is not a check, it is noise."""
        for name, text in self.CASES.items():
            with self.subTest(check=name):
                found = prose_lint.inspect(_entry(text))
                self.assertEqual(sorted(found["hits"]), [name])

    def test_the_summary_lists_every_check_even_at_zero(self):
        """A check missing from the summary reads as a check that passed."""
        rows = prose_lint.build_report({"x": _entry("Una frase neutra e priva di tell.")})
        summary = prose_lint.summarize(rows)
        expected = {name for name, _, _ in prose_lint.CHECKS} | {"domanda"}
        self.assertEqual(set(summary["checks"]), expected)


class CorrectProseStaysClean(unittest.TestCase):
    CLEAN = (
        "In Campania il valore resta sotto i 40 punti, in Lombardia sopra i 60.",
        "Dal 2018 al 2025 la media è salita di quasi cinque punti, e la distanza "
        "tra la prima e l'ultima regione si è accorciata di meno di un punto.",
        "Il conteggio vede solo il turismo che passa dagli esercizi ufficiali, "
        "quindi alberghi, campeggi e agriturismi.",
        "La graduatoria non scende con gradualità: tra la prima e la seconda "
        "regione si aprono più di ventidue giornate.",
        "Una regione poco popolosa con numeri assoluti modesti può risultare "
        "intensa, mentre la Lombardia resta in fondo alla graduatoria.",
    )

    def test_no_check_fires_on_ordinary_editorial_prose(self):
        for text in self.CLEAN:
            with self.subTest(text=text[:40]):
                self.assertEqual(prose_lint.inspect(_entry(text))["hits"], {})

    def test_a_list_of_three_nouns_is_not_flagged(self):
        """The rubric keeps the rule of three, this file deliberately does not.

        Italian lists three things constantly and a regex cannot tell an
        editorial tic from a complete enumeration, so the check lives with the
        reader. Pinned here so nobody adds it back without reading why.
        """
        found = prose_lint.inspect(_entry(
            "Asilo nido, micronido e servizi integrativi entrano tutti nel conto."
        ))
        self.assertEqual(found["hits"], {})


class WhatTheReportCounts(unittest.TestCase):
    def test_internal_links_are_separated_from_external_ones(self):
        found = prose_lint.inspect(_entry(
            "Vedi il [tasso di occupazione](/indicatore/tasso/ter-1) e "
            "[Istat](https://www.istat.it/)."
        ))
        self.assertEqual(found["internal_links"], ["/indicatore/tasso/ter-1"])

    def test_an_entry_with_no_prose_is_not_a_clean_article(self):
        """An unwritten article has no tells because it has no text. Counting it
        as clean would make the catalogue look better the less of it exists."""
        self.assertIsNone(prose_lint.inspect({"sections": [], "vintage": 2024}))

    def test_the_closing_question_is_counted_per_paragraph(self):
        entry = {
            "lead": "Una domanda in coda?",
            "sections": [{"role": "quadro", "body": "Un fatto. E un'altra domanda?"}],
        }
        self.assertEqual(len(prose_lint.inspect(entry)["hits"]["domanda"]), 2)

    def test_a_question_mid_paragraph_is_not_a_closing_question(self):
        found = prose_lint.inspect(_entry(
            "Quante donne lavorano? La risposta cambia molto da regione a regione."
        ))
        self.assertNotIn("domanda", found["hits"])


class AgainstTheRealCatalogue(unittest.TestCase):
    def test_the_report_reads_the_published_articles(self):
        rows = prose_lint.build_report()
        self.assertGreater(len(rows), 300)
        summary = prose_lint.summarize(rows)
        self.assertEqual(summary["articles"], len(rows))
        self.assertLessEqual(summary["clean"], summary["articles"])


if __name__ == "__main__":
    unittest.main()
