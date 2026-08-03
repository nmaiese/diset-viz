"""``--help`` must never touch the golden fixture.

The script had no argument parsing at all: any invocation, including
``--help``, ran straight through and overwrote
``tests/fixtures/indicator_stats_golden.json``. An agent that runs
``--help`` to learn the script's usage would silently corrupt a fixture
nobody meant to touch.
"""

import subprocess
import sys
import unittest
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "indicator_stats_golden.json"


class HelpNeverWrites(unittest.TestCase):
    def test_help_exits_clean_without_touching_the_fixture(self):
        before = FIXTURE.read_bytes()
        result = subprocess.run(
            [sys.executable, "-m", "scripts.dump_indicator_stats", "--help"],
            cwd=Path(__file__).resolve().parent.parent.parent,
            capture_output=True,
            timeout=30,
        )
        after = FIXTURE.read_bytes()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(before, after)
        self.assertIn(b"usage", result.stdout.lower())
