import importlib.util
import json
import tempfile
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
        settings = json.loads((RADICE / ".claude" / "settings.json").read_text())
        self.assertEqual(settings["env"]["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"], "1")
        self.assertEqual(settings["teammateMode"], "in-process")
        self.assertIn("TaskCreated", settings["hooks"])
        self.assertIn("TaskCompleted", settings["hooks"])
        creati = settings["hooks"]["TaskCreated"][0]["hooks"]
        self.assertTrue(any(h.get("async") and "--follow" in h.get("command", "")
                            for h in creati))
        frontend = (RADICE / "frontend" / "src" / "monitor" / "main.js").read_text()
        bundle = (RADICE / "app" / "static" / "dist" / "assets" / "monitor.js").read_text()
        for fase in team_monitor.FASI.values():
            if fase != "Chiusura":
                self.assertIn(f'"{fase}"', frontend)
                self.assertIn(f'`{fase}`', bundle)

    def test_ignora_i_task_non_editoriali(self):
        self.assertEqual(team_monitor.payload(evento("TaskCreated", "Refactor auth")), [])

    def test_apre_un_task_nella_dashboard_esistente(self):
        righe = team_monitor.payload(evento(
            "TaskCreated",
            "[redazione:data-editor:ricerca] ter-6 - leggere il dossier",
        ), now="2026-08-09T08:00:00+00:00")
        self.assertEqual(len(righe), 2)
        self.assertEqual(
            righe[0]["run_id"],
            "wf_team-session-a1b2c3d4-a1b2c3d4-resto",
        )
        self.assertEqual(righe[0]["fase_stimata"], "Ricerca")
        self.assertEqual(righe[1]["agent_type"], "data-editor")
        self.assertEqual(righe[1]["stato_vivo"], "aperto")
        self.assertEqual(righe[1]["indicatore"], "ter-6")

    def test_due_sessioni_con_lo_stesso_team_non_collidono(self):
        subject = "[redazione:data-editor:ricerca] ter-6 - leggere il dossier"
        prima = evento(
            "TaskCreated", subject,
            team_name="redazione-indicatore",
            session_id="sessione-uno",
        )
        seconda = evento(
            "TaskCreated", subject,
            team_name="redazione-indicatore",
            session_id="sessione-due",
        )
        run_prima = team_monitor.payload(prima)[0]["run_id"]
        run_seconda = team_monitor.payload(seconda)[0]["run_id"]
        self.assertNotEqual(run_prima, run_seconda)
        self.assertEqual(
            run_prima,
            "wf_team-redazione-indicatore-sessione-uno",
        )
        self.assertEqual(
            run_seconda,
            "wf_team-redazione-indicatore-sessione-due",
        )

    def test_senza_sessione_non_crea_una_run_ambigua(self):
        self.assertEqual(team_monitor.payload(evento(
            "TaskCreated",
            "[redazione:data-editor:ricerca] ter-6 - leggere il dossier",
            session_id="",
            team_name="redazione-indicatore",
        )), [])

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
            task_description=json.dumps({
                "articoli": [{"codice": "ter-13", "scritto": True, "parole": 700}],
                "fermati": [],
                "memoria": {
                    "consultata": ["source-researcher", "skeptical-editor"],
                    "candidati": 3,
                    "promossi": 1,
                    "scartati": 2,
                    "aggiornata": ["source-researcher"],
                },
            }),
        ))
        self.assertEqual(len(righe), 3)
        self.assertNotIn("fase_stimata", righe[0])
        self.assertEqual(righe[2]["action"], "consuntivo")
        self.assertEqual(righe[2]["run"]["workflow"], "editorial-agent-team")
        self.assertEqual(righe[2]["run"]["stato"], "completed")
        self.assertEqual(righe[2]["run"]["esito"]["articoli"][0]["codice"], "ter-13")
        self.assertEqual(righe[2]["run"]["esito"]["fermati"], [])
        memoria = righe[2]["run"]["esito"]["memoria"]
        self.assertEqual(memoria["consultata"],
                         ["source-researcher", "skeptical-editor"])
        self.assertEqual(memoria["candidati"], 3)
        self.assertEqual(memoria["promossi"], 1)
        self.assertEqual(memoria["scartati"], 2)
        self.assertEqual(memoria["aggiornata"], ["source-researcher"])

    def test_sentinella_senza_esito_non_finge_una_pubblicazione(self):
        righe = team_monitor.payload(evento(
            "TaskCompleted",
            "[redazione:lead:chiusura] ter-13 - chiusura del run",
        ))
        fermato = righe[2]["run"]["esito"]["fermati"][0]
        self.assertEqual(fermato["codice"], "ter-13")
        self.assertIn("senza esito", fermato["motivo"])
        self.assertEqual(righe[2]["run"]["esito"]["memoria"], {
            "consultata": [],
            "candidati": 0,
            "promossi": 0,
            "scartati": 0,
            "aggiornata": [],
        })

    def test_memoria_malformata_non_sporca_il_consuntivo(self):
        righe = team_monitor.payload(evento(
            "TaskCompleted",
            "[redazione:lead:chiusura] ter-13 - chiusura del run",
            task_description=json.dumps({
                "articoli": [],
                "fermati": [{"codice": "ter-13", "motivo": "fonte insufficiente"}],
                "memoria": {
                    "consultata": "source-researcher",
                    "candidati": "non-un-numero",
                    "promossi": -4,
                    "aggiornata": [None, "skeptical-editor"],
                },
            }),
        ))
        self.assertEqual(righe[2]["run"]["esito"]["memoria"], {
            "consultata": [],
            "candidati": 0,
            "promossi": 0,
            "scartati": 0,
            "aggiornata": ["skeptical-editor"],
        })

    def test_il_follow_rinfresca_finche_la_sentinella_e_aperta(self):
        class PostinoFinto:
            def __init__(self):
                self.righe = []

            def manda(self, payload):
                self.righe.append(payload)

        with tempfile.TemporaryDirectory() as cartella:
            stop = Path(cartella) / "stop"
            originale = team_monitor._stop_path
            team_monitor._stop_path = lambda run_id: stop
            try:
                postino = PostinoFinto()
                inviati = team_monitor.segui_battito(evento(
                    "TaskCreated",
                    "[redazione:lead:chiusura] ter-6 - chiusura del run",
                ), postino, intervallo=1, per=10,
                    pausa=lambda _: stop.touch(), orologio=lambda: 0)
            finally:
                team_monitor._stop_path = originale
        self.assertEqual(inviati, 1)
        self.assertEqual(postino.righe[0]["action"], "run")

    def test_ruolo_o_fase_non_previsti_non_sporcano_il_cruscotto(self):
        for subject in (
            "[redazione:hacker:ricerca] ter-6 - no",
            "[redazione:data-editor:deploy] ter-6 - no",
        ):
            self.assertEqual(team_monitor.payload(evento("TaskCreated", subject)), [])


if __name__ == "__main__":
    unittest.main()
