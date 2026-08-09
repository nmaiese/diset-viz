import importlib.util
import unittest
from pathlib import Path


RADICE = Path(__file__).resolve().parents[2]
PERCORSO = RADICE / ".claude" / "hooks" / "team_monitor.py"
SPEC = importlib.util.spec_from_file_location("team_monitor", PERCORSO)
team_monitor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(team_monitor)


def evento(nome, subject, **altro):
    return {
        "hook_event_name": nome,
        "session_id": "a1b2c3d4-resto",
        "team_name": "session-a1b2c3d4",
        "task_id": "task-7",
        "task_subject": subject,
        "cwd": "/repo/diset-viz",
        **altro,
    }


class TeamMonitorTest(unittest.TestCase):
    def test_settings_e_frontend_conoscono_il_team(self):
        import json
        settings = json.loads((RADICE / ".claude" / "settings.json").read_text())
        self.assertEqual(settings["env"]["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"], "1")
        self.assertEqual(settings["teammateMode"], "in-process")
        self.assertIn("TaskCreated", settings["hooks"])
        self.assertIn("TaskCompleted", settings["hooks"])
        frontend = (RADICE / "frontend" / "src" / "monitor" / "main.js").read_text()
        for fase in team_monitor.FASI.values():
            if fase != "Chiusura":
                self.assertIn(f'"{fase}"', frontend)

    def test_ignora_i_task_non_editoriali(self):
        self.assertEqual(team_monitor.payload(evento("TaskCreated", "Refactor auth")), [])

    def test_apre_un_task_nella_dashboard_esistente(self):
        righe = team_monitor.payload(evento(
            "TaskCreated",
            "[redazione:data-editor:ricerca] ter-6 - leggere il dossier",
        ), now="2026-08-09T08:00:00+00:00")
        self.assertEqual(len(righe), 2)
        self.assertEqual(righe[0]["run_id"], "wf_team-session-a1b2c3d4")
        self.assertEqual(righe[0]["fase_stimata"], "Ricerca")
        self.assertEqual(righe[1]["agent_type"], "data-editor")
        self.assertEqual(righe[1]["stato_vivo"], "aperto")
        self.assertEqual(righe[1]["indicatore"], "ter-6")

    def test_completamento_chiude_solo_il_task(self):
        righe = team_monitor.payload(evento(
            "TaskCompleted",
            "[redazione:skeptical-editor:verifica] bes-SDG-310 - stress test",
        ), now="2026-08-09T08:05:00+00:00")
        self.assertEqual(len(righe), 2)
        self.assertEqual(righe[1]["stato_vivo"], "chiuso")
        self.assertEqual(righe[1]["chiuso_il"], "2026-08-09T08:05:00+00:00")

    def test_la_sentinella_chiude_il_run(self):
        righe = team_monitor.payload(evento(
            "TaskCompleted",
            "[redazione:lead:chiusura] ter-13 - chiusura del run",
        ))
        self.assertEqual(len(righe), 3)
        self.assertNotIn("fase_stimata", righe[0])
        self.assertEqual(righe[2]["action"], "consuntivo")
        self.assertEqual(righe[2]["run"]["workflow"], "editorial-agent-team")
        self.assertEqual(righe[2]["run"]["stato"], "completed")

    def test_ruolo_o_fase_non_previsti_non_sporcano_il_cruscotto(self):
        for subject in (
            "[redazione:hacker:ricerca] ter-6 - no",
            "[redazione:data-editor:deploy] ter-6 - no",
        ):
            self.assertEqual(team_monitor.payload(evento("TaskCreated", subject)), [])


if __name__ == "__main__":
    unittest.main()
