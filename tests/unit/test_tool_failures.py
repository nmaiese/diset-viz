"""Il lettore dei guasti ripetuti: cio' che si ripete, non l'elenco.

Il file lo scriveva un hook da mesi e non lo apriva nessuno. L'errore
`.venv/bin/python: no such file` era registrato tre ore prima della prima run
del workflow: in quella run quattro scrittori l'hanno ripagato da capo, quattro
turni a testa, e un pubblicatore ha eseguito il lint con l'interprete di un
altro worktree.
"""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import tool_failures

ADESSO = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)


def _riga(errore, ore_fa=1, tool="Bash", comando="bin/py -m officina.lint"):
    return {"at": (ADESSO - timedelta(hours=ore_fa)).isoformat(timespec="seconds"),
            "tool": tool, "input": comando, "error": errore}


class TheSignatureIsTheFaultNotTheOccurrence(unittest.TestCase):
    def test_numbers_do_not_split_the_same_fault(self):
        uno = tool_failures.firma(_riga("Exit code 1\nfile not found: line 12"))
        due = tool_failures.firma(_riga("Exit code 2\nfile not found: line 480"))
        self.assertEqual(uno, due)

    def test_the_exit_code_alone_is_not_a_signature(self):
        """Quasi ogni fallimento di Bash apre con "Exit code 1": raggrupparli
        li' risponde "trentuno volte lo stesso guasto" a trentuno guasti
        diversi, che e' peggio del silenzio."""
        firma = tool_failures.firma(_riga("Exit code 1\n.venv/bin/python: not found"))
        self.assertNotIn("Exit code", firma)
        self.assertIn("not found", firma)

    def test_two_different_faults_stay_apart(self):
        self.assertNotEqual(
            tool_failures.firma(_riga("Exit code 1\nno such file: .venv/bin/python")),
            tool_failures.firma(_riga("Exit code 1\nModuleNotFoundError: flask")))


class ItReportsWhatRepeats(unittest.TestCase):
    def test_a_single_stumble_is_not_reported(self):
        righe = [_riga("Exit code 1\nun caso isolato")]
        self.assertEqual(tool_failures.ripetuti(righe), [])

    def test_the_repeated_one_comes_first_with_its_count(self):
        righe = ([_riga("Exit code 1\nno such file: .venv/bin/python")] * 4
                 + [_riga("Exit code 1\naltro")] * 2)
        gruppi = tool_failures.ripetuti(righe)
        self.assertEqual(gruppi[0][1], 4)
        self.assertIn(".venv/bin/python", gruppi[0][0])

    def test_old_faults_fall_out_of_the_window(self):
        righe = [_riga("Exit code 1\nvecchio", ore_fa=100)] * 5
        self.assertEqual(tool_failures.recenti(righe, ore=48, adesso=ADESSO), [])
        self.assertEqual(len(tool_failures.recenti(righe, ore=200, adesso=ADESSO)), 5)

    def test_a_row_without_a_readable_date_is_kept(self):
        """Un guasto senza data e' comunque un guasto: scartarlo sarebbe la
        stessa disattenzione che questo file esiste per correggere."""
        righe = [{"tool": "Bash", "error": "Exit code 1\nsenza data"}] * 2
        self.assertEqual(len(tool_failures.recenti(righe, adesso=ADESSO)), 2)


class ItNeverFailsNoisily(unittest.TestCase):
    def test_a_missing_file_reads_as_nothing_to_say(self):
        self.assertEqual(tool_failures.leggi(Path("/non/esiste.jsonl")), [])

    def test_a_broken_line_does_not_stop_the_rest(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "failures.jsonl"
            path.write_text(json.dumps(_riga("Exit code 1\nbuona")) + "\n"
                            + "{non json\n"
                            + json.dumps(_riga("Exit code 1\nbuona")) + "\n",
                            encoding="utf-8")
            self.assertEqual(len(tool_failures.leggi(path)), 2)


if __name__ == "__main__":
    unittest.main()
