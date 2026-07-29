"""La guardia per-agente resta ancorata al worktree della run.

Con i worktree ogni run lavora in un albero sorella (`diset-viz-runs/<run_id>`),
non nel checkout principale. La guardia misura il perimetro chiedendo a git a
quale working tree appartiene il file: se misurasse dal solo checkout principale,
una scrittura nel worktree (il cancello stesso incluso) fallirebbe
`relative_to(PROJECT_ROOT)` e passerebbe come 'scratch esterno', scavalcando il
perimetro. Qui si costruisce un repo con un worktree vero e si prova che non lo fa.
"""

import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import agent_guard


class GuardIsAnchoredToTheRunWorktree(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.main = Path(self._tmp.name) / "main"
        self.main.mkdir()
        self._git("init", "-q", "-b", "master")
        self._git("config", "user.email", "t@example.com")
        self._git("config", "user.name", "t")
        # Le cartelle che il perimetro conosce e una che non conosce, committate
        # cosi' il worktree le porta con se'.
        (self.main / "content" / "indicators").mkdir(parents=True)
        (self.main / "content" / "indicators" / ".gitkeep").write_text("")
        (self.main / "scripts").mkdir()
        (self.main / "scripts" / "pipeline_gate.py").write_text("# finto\n")
        self._git("add", "-A")
        self._git("commit", "-qm", "base")
        self.worktree = Path(self._tmp.name) / "diset-viz-runs" / "producer-x"
        self._git("worktree", "add", "-q", "-b", "automation/producer-x",
                  str(self.worktree), "master")
        # La guardia importa il perimetro reale ma risolve PROJECT_ROOT dalla sua
        # posizione: qui va puntata al repo finto per la durata della prova.
        self._orig_root = agent_guard.PROJECT_ROOT
        agent_guard.PROJECT_ROOT = self.main.resolve()
        self.addCleanup(lambda: setattr(agent_guard, "PROJECT_ROOT", self._orig_root))

    def _git(self, *args):
        return subprocess.run(("git",) + args, cwd=self.main,
                              capture_output=True, text=True)

    def test_a_write_outside_the_perimeter_in_the_worktree_is_blocked(self):
        # Il cancello stesso, dentro il worktree, con un percorso assoluto: prima
        # passava come scratch esterno, ora e' misurato dal worktree e bloccato.
        target = str(self.worktree / "scripts" / "pipeline_gate.py")
        ok, reason = agent_guard.path_verdict(target, ["writer"])
        self.assertFalse(ok)
        self.assertIn("perimetro", reason)

    def test_a_write_inside_the_perimeter_in_the_worktree_is_allowed(self):
        target = str(self.worktree / "content" / "indicators" / "ter-1.json")
        ok, _ = agent_guard.path_verdict(target, ["writer"])
        self.assertTrue(ok)

    def test_genuine_external_scratch_is_still_allowed(self):
        # Un percorso davvero fuori da ogni repo resta scratch legittimo.
        ok, _ = agent_guard.path_verdict(str(Path(self._tmp.name) / "appunti.md"), ["writer"])
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
