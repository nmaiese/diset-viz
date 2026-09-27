"""Helper di Orchestrazione Multi-Agente Orca per Divario Italia.

Semplifica e automatizza la creazione di worktree isolati via Orca CLI (`orca-ide`),
la generazione del file `TASK.md` live e il routing dei task verso l'agente specializzato.

Uso:
    bin/py scripts/orca_dispatch.py <slug> --title "Titolo Task" --objective "Obiettivo" --role worker
    bin/py scripts/orca_dispatch.py audit-link --title "Audit link" --objective "..." --role researcher
    bin/py scripts/orca_dispatch.py <slug> --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

AGENT_ROUTING = {
    "worker": "codex",
    "researcher": "gemini",
    "architect": "claude",
}

# Modelli OpenCode operativi e testati (da ~/dev/dev-tools/docs/opencode-modelli.md)
OPENCODE_MODELS = {
    "fast": "opencode/ling-3.0-flash-fin-free",  # 80 tok/s: titoli, link, micro-audit
    "workhorse": "opencode/big-pickle",           # Default bilanciato per coding
    "coding_speed": "ollama-cloud/gpt-oss:120b",  # 189 tok/s: generazione test e script (1 connes. max)
    "reasoning": "opencode/nemotron-3-ultra-free",# 36 tok/s: audit e riflessioni
    "backup_free": "openrouter/liquid/lfm-2.5-2.6b:free", # 175 tok/s: fallback
}

LOCK_DIR = PROJECT_ROOT / ".orca" / "locks"


def check_provider_lock(role: str) -> bool:
    """Verifica e gestisce la coda di lock per provider ad una sola connessione concorrente (Ollama Cloud)."""
    if role == "worker":
        LOCK_DIR.mkdir(parents=True, exist_ok=True)
        lock_file = LOCK_DIR / "ollama_cloud.lock"
        if lock_file.exists():
            print(f"[!] Avviso Concorrenza: Provider Ollama Cloud libero da 1 sola connessione in corso. Task accodato.")
            return False
    return True

TASK_TEMPLATE = """# Task: {title}

> Status: in-progress
> Assegnato a: {agent} ({role})
> Branch: nmaiese/{slug}

## Obiettivo
{objective}

## Requisiti
- R1. Operare esclusivamente dentro questo worktree (`.orca/worktrees/divarioitalia/{slug}`).
- R2. Usare sempre `DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py` per l'ambiente virtuale Python.
- R3. Rispettare tassativamente le linee guida del progetto in `CLAUDE.md`, `STATUS.md` e `content/STYLE.md`.

## Criteri di Accettazione (Checklist)
- [ ] Test unitari passati: `bin/py -m unittest discover -s tests/unit -v`
- [ ] Suite completa passata: `bin/py -m unittest discover -s tests -v`
- [ ] Nessun file fuori worktree o file lock forzato.

## Note e Feedback Live di Nello
<!-- Scrivi qui feedback live mentre l'agente lavora. Salva con Ctrl+S -->

## Log Decisioni Agente
"""


def get_orca_cmd() -> str:
    """Restituisce il comando Orca CLI per l'ambiente corrente (WSL o Linux)."""
    env_cmd = os.environ.get("ORCA_CLI_COMMAND")
    if env_cmd:
        return env_cmd
    # Controlla alias comune su WSL
    wsl_exe = Path("/mnt/c/Users/Nilo/AppData/Local/Programs/orca/resources/bin/orca.exe")
    if wsl_exe.exists():
        return str(wsl_exe)
    return "orca-ide"


def dispatch_task(
    slug: str,
    title: str,
    objective: str,
    role: str = "worker",
    dry_run: bool = False,
) -> int:
    agent = AGENT_ROUTING.get(role.lower(), "codex")
    worktree_dir = PROJECT_ROOT / ".orca" / "worktrees" / "divarioitalia" / slug
    orca_bin = get_orca_cmd()

    print(f"=== Orca Multi-Agent Dispatcher ===")
    print(f"Task Slug : {slug}")
    print(f"Titolo    : {title}")
    print(f"Ruolo     : {role} -> Agente: {agent}")
    print(f"Path      : {worktree_dir}")

    task_content = TASK_TEMPLATE.format(
        title=title,
        agent=agent.capitalize(),
        role=role,
        slug=slug,
        objective=objective,
    )

    if dry_run:
        print("\n--- [DRY RUN] TASK.md Generato ---")
        print(task_content)
        print("--- [DRY RUN] Comando Orca CLI ---")
        print(f"{orca_bin} worktree create --name {slug} --no-parent --agent {agent} --json")
        return 0

    # 1. Creazione directory e TASK.md
    worktree_dir.mkdir(parents=True, exist_ok=True)
    task_file = worktree_dir / "TASK.md"
    task_file.write_text(task_content, encoding="utf-8")
    print(f"[+] Generato {task_file}")

    # 2. Invocazione Orca CLI
    cmd = [
        orca_bin, "worktree", "create",
        "--name", slug,
        "--no-parent",
        "--agent", agent,
        "--prompt", f"Leggi TASK.md ed esegui l'obiettivo per {slug}",
        "--json",
    ]
    print(f"[+] Esecuzione comando Orca: {' '.join(cmd)}")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if res.stdout:
            print(f"Out: {res.stdout.strip()}")
        if res.stderr:
            print(f"Err: {res.stderr.strip()}")
    except Exception as exc:
        print(f"[!] Nota su Orca CLI: {exc} (il worktree e TASK.md sono stati registrati fisicamente).")

    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Orca Task Dispatcher per Divario Italia")
    parser.add_argument("slug", help="Nome breve / slug del task (es. lead-ter-13, fix-analytics)")
    parser.add_argument("--title", default="", help="Titolo esteso del task")
    parser.add_argument("--objective", default="", help="Obiettivo dettagliato del task")
    parser.add_argument(
        "--role",
        choices=["worker", "researcher", "architect"],
        default="worker",
        help="Ruolo richiesto (worker=Codex, researcher=Gemini, architect=Claude)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Mostra l'anteprima senza eseguire modifiche")

    args = parser.parse_args(argv)
    title = args.title or args.slug.replace("-", " ").title()
    objective = args.objective or f"Esegui il lavoro richiesto per il task {args.slug}."

    return dispatch_task(
        slug=args.slug,
        title=title,
        objective=objective,
        role=args.role,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
