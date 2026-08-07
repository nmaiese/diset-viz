"""The mechanical half of the writing rubric.

Two failure modes matter here and they pull in opposite directions. A pattern
that never fires is worse than no pattern: it reports zero, the summary reads as
progress, and nobody notices the check died. A pattern that fires on correct
Italian is worse still, because a linter that cries wolf gets ignored and then it
protects nothing. So every check is pinned from both sides, on a sentence that
must trip it and on prose that must not.

Sintetico soltanto: i due test che leggono il catalogo pubblicato stanno in
`tests/integration/test_prose_lint_live.py`.
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
        self.assertEqual(set(summary["checks"]), set(prose_lint.ALL_SIGNALS))
        for name in prose_lint.ALL_SIGNALS:
            self.assertTrue(summary["checks"][name]["label"], name)


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


class TheSameQuantityTwice(unittest.TestCase):
    """The residual defect of the articles that pass everything else.

    Two blind judges, scoring the rewritten batch independently, both named the
    same thing: an image in one section and the figure it stands for in another.
    STYLE.md already bans the version where they touch ("quasi la metà (48%)");
    this is the same fault spread across the page, where an editor stops seeing it.

    The check is deliberately precise rather than complete. It uses the direction
    the approximation implies, because tolerance alone matched three different
    quantities in one article that happened to round the same way, and a linter
    that cries wolf gets ignored.
    """

    def _hits(self, quadro, dinamica):
        entry = {"sections": [
            {"role": "quadro", "body": quadro},
            {"role": "dinamica", "body": dinamica},
        ]}
        return prose_lint.inspect(entry)["hits"].get("ripetuto", [])

    def test_an_image_and_its_figure_in_two_sections_are_caught(self):
        self.assertTrue(self._hits(
            "Tra le due si apre un vuoto di quasi tre punti.",
            "Il salto vale 2,79 punti in un colpo solo.",
        ))

    def test_a_different_quantity_of_the_same_size_is_not_caught(self):
        """"quasi tre punti" is 2,79 and the article also discusses 3,31 and
        3,48 in points. Those are three quantities, not one said three times."""
        self.assertEqual(self._hits(
            "Tra le due si apre un vuoto di quasi tre punti.",
            "La media sta 3,31 punti sopra la mediana, e altrove sono 3,48 punti.",
        ), [])

    def test_the_approximation_has_to_point_the_right_way(self):
        """"quasi nove" is below nine. A 9,3 is not what it was approximating."""
        self.assertEqual(self._hits(
            "La Sardegna ha aggiunto quasi nove anni.",
            "Il divario vale 9,3 anni.",
        ), [])
        self.assertTrue(self._hits(
            "La Sardegna ha aggiunto oltre nove anni.",
            "Il divario vale 9,3 anni.",
        ))

    def test_the_unit_has_to_match(self):
        """Nine years and nine points are not the same fact twice."""
        self.assertEqual(self._hits(
            "La Sardegna ha aggiunto quasi nove anni.",
            "Il divario vale 8,9 punti.",
        ), [])

    def test_inside_one_section_it_is_elaboration_not_repetition(self):
        entry = {"sections": [{"role": "quadro",
                               "body": "Un vuoto di quasi tre punti. Vale 2,79 punti."}]}
        self.assertNotIn("ripetuto", prose_lint.inspect(entry)["hits"])


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


class ShowAcceptsTheCodeAsItIsWritten(unittest.TestCase):
    """The same guard `review_queue` already carries, on the newer tool.

    `--show` indexed the texts dict directly, so it took the internal id and
    refused the URL form, which is the form the reviewer's prompt puts in its
    example (`prose_lint.py --show ter-63`). The documented command answered
    "nessun articolo" for every indicator, and an agent that hits that either
    works around it or drops the step. `review_queue` had exactly this defect,
    it was found and fixed, and it was written again here a few commits later:
    hence a test in both places rather than a memory of the first one.
    """

    TEXTS = {"920": {"lead": "x"}, "bes:10AMB004": {"lead": "y"}}

    def test_the_url_form_resolves(self):
        self.assertEqual(prose_lint.resolve_key(self.TEXTS, "ter-920"), "920")
        self.assertEqual(
            prose_lint.resolve_key(self.TEXTS, "bes-10AMB004"), "bes:10AMB004"
        )

    def test_the_internal_id_still_resolves(self):
        self.assertEqual(prose_lint.resolve_key(self.TEXTS, "920"), "920")
        self.assertEqual(
            prose_lint.resolve_key(self.TEXTS, "bes:10AMB004"), "bes:10AMB004"
        )

    def test_a_code_with_no_article_does_not_resolve_to_a_neighbour(self):
        self.assertIsNone(prose_lint.resolve_key(self.TEXTS, "ter-99999"))
        self.assertIsNone(prose_lint.resolve_key(self.TEXTS, "pippo"))

    def test_an_ambiguous_raw_id_refuses_rather_than_guessing(self):
        """Matching on the part after the prefix is what keeps this script free
        of a copy of the family table. The cost is that two families sharing a
        raw id are indistinguishable, and the right answer there is to say so
        instead of picking whichever came first in the file."""
        texts = {"bes:X1": {"lead": "a"}, "ims:X1": {"lead": "b"}}
        self.assertIsNone(prose_lint.resolve_key(texts, "bes-X1"))


if __name__ == "__main__":
    unittest.main()
