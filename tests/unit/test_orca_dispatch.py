"""Test unitario per scripts/orca_dispatch.py (Orchestratore Multi-Agente Orca)."""
import tempfile
import unittest
from pathlib import Path

from scripts import orca_dispatch


class OrcaDispatchTest(unittest.TestCase):
    def test_routing_maps_roles_to_expected_agents(self):
        self.assertEqual(orca_dispatch.AGENT_ROUTING["worker"], "codex")
        self.assertEqual(orca_dispatch.AGENT_ROUTING["researcher"], "antigravity")
        self.assertEqual(orca_dispatch.AGENT_ROUTING["architect"], "codex")

    def test_dry_run_executes_without_error(self):
        code = orca_dispatch.dispatch_task(
            slug="unit-test-task",
            title="Unit Test Title",
            objective="Test dry run execution",
            role="worker",
            dry_run=True,
        )
        self.assertEqual(code, 0)

    def test_task_template_formatting(self):
        content = orca_dispatch.TASK_TEMPLATE.format(
            title="Titolo Prova",
            agent="Codex",
            role="worker",
            slug="prova-slug",
            objective="Obiettivo di prova",
        )
        self.assertIn("# Task: Titolo Prova", content)
        self.assertIn("> Assegnato a: Codex (worker)", content)
        self.assertIn("DIVARIO_PYTHON=", content)
        self.assertIn("CLAUDE.md", content)


if __name__ == "__main__":
    unittest.main()
