"""Avvia task isolati per Divario Italia tramite Orca."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main_checkout_root() -> Path:
    """Il checkout principale: da un worktree Orca PROJECT_ROOT e' il worktree stesso."""
    result = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return PROJECT_ROOT
    return Path(result.stdout.strip()).parent


MAIN_ROOT = main_checkout_root()


def _wslpath(flag: str, value: str) -> str | None:
    if not shutil.which("wslpath"):
        return None
    result = subprocess.run(
        ["wslpath", flag, value], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() or None if result.returncode == 0 else None


def to_orca_repo_path(path: Path) -> str:
    """Orca registra i repo WSL come percorsi UNC: ``path:/home/...`` da' repo_not_found."""
    return _wslpath("-w", str(path)) or str(path)


ORCA_REPO_PATH = to_orca_repo_path(MAIN_ROOT)


def from_orca_path(value: str) -> Path:
    """Converte il percorso UNC restituito da Orca in un percorso WSL."""
    if value.startswith("\\\\"):
        converted = _wslpath("-u", value)
        if converted:
            return Path(converted)
    return Path(value)

AGENT_ROUTING = {
    "worker": "codex",
    "researcher": "antigravity",
    "architect": "codex",
}

TASK_TEMPLATE = """# Task: {title}

> Status: in-progress
> Assegnato a: {agent} ({role})
> Branch: nmaiese/{slug}

## Obiettivo
{objective}

## Requisiti
- R1. Operare esclusivamente dentro questo worktree.
- R2. Usare sempre `bin/py` con `DIVARIO_PYTHON={python}`: il worktree non ha una sua `.venv`.
- R3. Rispettare tassativamente le linee guida del progetto in `CLAUDE.md`, `STATUS.md` e `content/STYLE.md`.

## Criteri di Accettazione (Checklist)
- [ ] Test unitari passati: `bin/py -m unittest discover -s tests/unit -v`
- [ ] Suite completa passata: `bin/py -m unittest discover -s tests -v`
- [ ] Nessun file modificato fuori dal worktree.

## Note e Feedback Live di Nello
<!-- Questo e' il file per note live mentre l'agente lavora. -->

## Log Decisioni Agente
<!-- Registra qui le decisioni prese durante il task. -->
"""


class OrcaOutputError(ValueError):
    """Indica una risposta JSON Orca assente o incompleta."""


def get_orca_cmd() -> str:
    """Trova la CLI Orca senza rischiare di avviare il lettore di schermo."""
    env_cmd = os.environ.get("ORCA_CLI_COMMAND")
    if env_cmd:
        return env_cmd
    orca_cmd = shutil.which("orca-ide")
    if orca_cmd:
        return orca_cmd
    raise RuntimeError(
        "CLI Orca non trovata: imposta ORCA_CLI_COMMAND o aggiungi orca-ide al PATH."
    )


def parse_orca_json(output: str) -> dict[str, Any]:
    """Legge un oggetto JSON anche se la CLI ha anteposto righe informative."""
    candidates = [output.strip(), *reversed(output.splitlines())]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise OrcaOutputError("Orca non ha restituito un oggetto JSON valido.")


def is_runtime_unavailable(*values: object) -> bool:
    """Riconosce l'errore incerto che puo' seguire una create gia' applicata."""
    return "runtime_unavailable" in " ".join(str(value) for value in values).lower()


def _walk_objects(value: object):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_objects(child)


def extract_worktree_details(payload: dict[str, Any]) -> tuple[Path, str]:
    """Estrae percorso e ramo reali dalla risposta di ``worktree create``."""
    path_keys = ("worktreePath", "worktree_path", "path")
    branch_keys = ("branchName", "branch_name", "branch")
    for item in _walk_objects(payload):
        path_value = next(
            (item[key] for key in path_keys if isinstance(item.get(key), str)),
            None,
        )
        branch_value = next(
            (item[key] for key in branch_keys if isinstance(item.get(key), str)),
            None,
        )
        if path_value and branch_value:
            clean_path = path_value.removeprefix("path:")
            clean_branch = branch_value.removeprefix("refs/heads/")
            return from_orca_path(clean_path), clean_branch
    raise OrcaOutputError(
        "La risposta Orca non contiene il percorso e il ramo del worktree."
    )


def build_task_content(
    slug: str,
    title: str,
    objective: str,
    role: str,
    agent: str,
    branch: str | None = None,
) -> str:
    """Compone il contratto da salvare nel worktree creato da Orca."""
    content = TASK_TEMPLATE.format(
        title=title,
        agent=agent.capitalize(),
        role=role,
        slug=slug,
        objective=objective,
        python=MAIN_ROOT / ".venv" / "bin" / "python",
    )
    if branch:
        content = content.replace(f"> Branch: nmaiese/{slug}", f"> Branch: {branch}")
    return content


def build_prompt(task_content: str) -> str:
    """Trasforma l'intero contratto in un prompt su una sola riga."""
    lines = (line.strip() for line in task_content.splitlines())
    return " | ".join(line for line in lines if line)


def _print_process_output(result: subprocess.CompletedProcess[str]) -> None:
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)


def _check_uncertain_create(orca_cmd: str, slug: str) -> None:
    """Controlla senza riprovare se Orca ha creato il worktree."""
    list_cmd = [
        orca_cmd,
        "worktree",
        "list",
        "--repo",
        f"path:{ORCA_REPO_PATH}",
        "--json",
    ]
    try:
        result = subprocess.run(
            list_cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"[!] Impossibile verificare la lista dei worktree: {exc}", file=sys.stderr)
        print("[!] Non riprovare automaticamente la create.", file=sys.stderr)
        return

    combined = f"{result.stdout}\n{result.stderr}"
    if f'"{slug}"' in combined or f"/{slug}" in combined:
        print(
            "[!] Orca elenca un worktree col nome richiesto: non ripetere la create; "
            "verifica il worktree e completa TASK.md manualmente.",
            file=sys.stderr,
        )
    else:
        print(
            "[!] Orca non conferma il worktree richiesto: controlla con "
            f"`{shlex.join(list_cmd)}` prima di qualsiasi nuovo tentativo.",
            file=sys.stderr,
        )


def dispatch_task(
    slug: str,
    title: str,
    objective: str,
    role: str = "worker",
    dry_run: bool = False,
) -> int:
    """Crea il worktree con Orca e solo dopo vi scrive ``TASK.md``."""
    normalized_role = role.lower()
    if normalized_role not in AGENT_ROUTING:
        print(f"[!] Ruolo Orca non valido: {role}", file=sys.stderr)
        return 1
    agent = AGENT_ROUTING[normalized_role]

    try:
        orca_cmd = get_orca_cmd()
    except RuntimeError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 1

    initial_task = build_task_content(
        slug=slug,
        title=title,
        objective=objective,
        role=normalized_role,
        agent=agent,
    )
    prompt = build_prompt(initial_task)
    cmd = [
        orca_cmd,
        "worktree",
        "create",
        "--repo",
        f"path:{ORCA_REPO_PATH}",
        "--name",
        slug,
        "--no-parent",
        "--base-branch",
        "origin/master",
        "--setup",
        "skip",
        "--agent",
        agent,
        "--prompt",
        prompt,
        "--json",
    ]

    if dry_run:
        print(shlex.join(cmd))
        return 0

    print(f"[+] Esecuzione: {shlex.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print("[!] Timeout Orca dopo 180 secondi.", file=sys.stderr)
        _check_uncertain_create(orca_cmd, slug)
        return 2
    except OSError as exc:
        print(f"[!] Impossibile eseguire Orca: {exc}", file=sys.stderr)
        return 1

    if is_runtime_unavailable(result.stdout, result.stderr):
        _print_process_output(result)
        _check_uncertain_create(orca_cmd, slug)
        return 2

    try:
        payload = parse_orca_json(result.stdout)
    except OrcaOutputError as exc:
        _print_process_output(result)
        print(f"[!] {exc}", file=sys.stderr)
        return 1

    if result.returncode != 0 or payload.get("ok") is False:
        _print_process_output(result)
        print(
            f"[!] Creazione Orca fallita (exit {result.returncode}, ok={payload.get('ok')}).",
            file=sys.stderr,
        )
        return 1

    try:
        worktree_path, branch = extract_worktree_details(payload)
    except OrcaOutputError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 1
    if not worktree_path.is_dir():
        print(
            f"[!] Il path restituito da Orca non e' una directory: {worktree_path}",
            file=sys.stderr,
        )
        return 1

    task_content = build_task_content(
        slug=slug,
        title=title,
        objective=objective,
        role=normalized_role,
        agent=agent,
        branch=branch,
    )
    task_file = worktree_path / "TASK.md"
    task_file.write_text(task_content, encoding="utf-8")
    print(f"[+] Creato {worktree_path} sul ramo {branch}")
    print(f"[+] Scritto {task_file}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Orca Task Dispatcher per Divario Italia")
    parser.add_argument("slug", help="Nome breve / slug del task")
    parser.add_argument("--title", default="", help="Titolo esteso del task")
    parser.add_argument("--objective", default="", help="Obiettivo dettagliato del task")
    routing_help = ", ".join(
        f"{role}={agent}" for role, agent in AGENT_ROUTING.items()
    )
    parser.add_argument(
        "--role",
        choices=list(AGENT_ROUTING),
        default="worker",
        help=f"Ruolo richiesto ({routing_help})",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Mostra il comando senza eseguirlo"
    )

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
