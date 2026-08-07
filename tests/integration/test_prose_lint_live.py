"""Il lint della prosa contro il **catalogo vero**, cioe' tutti i pubblicati.

Sta in `integration/` per la regola di `CLAUDE.md`: legge tutti gli articoli
committati, quindi ha bisogno di un giro reale. I due test qui erano in
`tests/unit/test_prose_lint.py`, dove la suite veloce li girava senza dirlo.

La meta' sintetica del lint (ogni controllo pinnato da tutti e due i lati, la
frase che deve farlo scattare e la prosa che non deve) resta in
`tests/unit/test_prose_lint.py` e non tocca il disco.
"""

import contextlib
import io
import unittest

from scripts import prose_lint


class AgainstTheRealCatalogue(unittest.TestCase):
    def test_the_command_in_the_reviewer_prompt_runs(self):
        """The prompt's example, executed. It returned 1 and printed
        "nessun articolo" for a year of runs that nobody could see fail.

        Stdout is captured, and not only for tidiness: the gate reads the suite
        as stderr followed by stdout and quotes the last three lines, so a test
        that prints pushes the unittest verdict out of the only message anybody
        sees on an unattended pull request.
        """
        texts = prose_lint.load_texts()
        code = f"ter-{next(key for key in texts if key.isdigit())}"
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = prose_lint.main(["--show", code])
        self.assertEqual(exit_code, 0)

    def test_the_report_reads_the_published_articles(self):
        rows = prose_lint.build_report()
        self.assertGreater(len(rows), 300)
        summary = prose_lint.summarize(rows)
        self.assertEqual(summary["articles"], len(rows))
        self.assertLessEqual(summary["clean"], summary["articles"])


if __name__ == "__main__":
    unittest.main()
