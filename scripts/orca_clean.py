"""Rimuove in sicurezza un worktree Orca e il suo ramo gia' fuso."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.orca_dispatch import (
    OrcaOutputError,
    get_orca_cmd,
    is_runtime_unavailable,
    parse_orca_json,
)
from scripts.orca_review import WorktreeResolutionError, resolve_worktree


def _run(command: list[str], cwd: Path = PROJECT_ROOT):
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )


def _print_failure(command: list[str], result: subprocess.CompletedProcess[str]) -> None:
    print(f"[!] Comando fallito: {shlex.join(command)}", file=sys.stderr)
    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    if output:
        print(output, file=sys.stderr)


def _remove_with_git(worktree_path: Path) -> bool:
    command = ["git", "worktree", "remove", str(worktree_path)]
    try:
        result = _run(command)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"[!] Comando non eseguibile: {shlex.join(command)}: {exc}", file=sys.stderr)
        return False
    if result.returncode != 0:
        _print_failure(command, result)
        return False
    return True


def _remove_worktree(worktree_path: Path) -> bool:
    """Preferisce Orca e usa Git solo quando il runtime non e' raggiungibile."""
    try:
        orca_cmd = get_orca_cmd()
    except RuntimeError as exc:
        print(f"[i] {exc} Uso il fallback Git.")
        return _remove_with_git(worktree_path)

    command = [
        orca_cmd,
        "worktree",
        "rm",
        "--worktree",
        f"path:{worktree_path}",
        "--json",
    ]
    try:
        result = _run(command)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"[i] Orca non raggiungibile ({exc}). Uso il fallback Git.")
        return _remove_with_git(worktree_path)

    if is_runtime_unavailable(result.stdout, result.stderr):
        print("[i] Runtime Orca non disponibile. Uso il fallback Git.")
        return _remove_with_git(worktree_path)
    try:
        payload = parse_orca_json(result.stdout)
    except OrcaOutputError:
        _print_failure(command, result)
        return False
    if result.returncode != 0 or payload.get("ok") is False:
        _print_failure(command, result)
        return False
    return True


def _is_unmerged_error(result: subprocess.CompletedProcess[str]) -> bool:
    output = f"{result.stdout}\n{result.stderr}".lower()
    return "not fully merged" in output or "non completamente" in output


def _delete_branch(branch: str) -> bool:
    safe_command = ["git", "branch", "-d", branch]
    try:
        result = _run(safe_command)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"[!] Comando non eseguibile: {shlex.join(safe_command)}: {exc}", file=sys.stderr)
        return False
    if result.returncode == 0:
        return True
    if not _is_unmerged_error(result):
        _print_failure(safe_command, result)
        return False

    view_command = ["gh", "pr", "view", branch, "--json", "state"]
    try:
        view_result = _run(view_command)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"[!] Comando non eseguibile: {shlex.join(view_command)}: {exc}", file=sys.stderr)
        return False
    if view_result.returncode != 0:
        _print_failure(view_command, view_result)
        print(f"[i] Il ramo {branch} e' stato lasciato intatto.")
        return False
    try:
        state = json.loads(view_result.stdout).get("state")
    except (json.JSONDecodeError, AttributeError):
        _print_failure(view_command, view_result)
        print(f"[i] Il ramo {branch} e' stato lasciato intatto.")
        return False
    if state != "MERGED":
        print(f"[i] La PR e' {state or 'senza stato'}: il ramo {branch} resta locale.")
        return True

    force_command = ["git", "branch", "-D", branch]
    try:
        force_result = _run(force_command)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(
            f"[!] Comando non eseguibile: {shlex.join(force_command)}: {exc}",
            file=sys.stderr,
        )
        return False
    if force_result.returncode != 0:
        _print_failure(force_command, force_result)
        return False
    return True


def _dry_run_identity(slug: str) -> tuple[Path, str]:
    try:
        return resolve_worktree(slug)
    except WorktreeResolutionError:
        return Path(f"<worktree:{slug}>"), "<ramo-del-worktree>"


def run_clean(slug: str, dry_run: bool = False) -> int:
    """Rifiuta dati sporchi, rimuove il worktree e poi tratta il ramo."""
    if dry_run:
        worktree_path, branch = _dry_run_identity(slug)
    else:
        try:
            worktree_path, branch = resolve_worktree(slug)
        except WorktreeResolutionError as exc:
            print(f"[!] {exc}", file=sys.stderr)
            return 1

    print("=== Orca Worktree Cleanup ===")
    print(f"Worktree  : {worktree_path}")
    print(f"Branch    : {branch}")
    if dry_run:
        try:
            orca_cmd = get_orca_cmd()
        except RuntimeError:
            orca_cmd = "orca-ide"
        print(
            shlex.join(
                [
                    orca_cmd,
                    "worktree",
                    "rm",
                    "--worktree",
                    f"path:{worktree_path}",
                    "--json",
                ]
            )
        )
        print(shlex.join(["git", "branch", "-d", branch]))
        return 0

    status_command = ["git", "status", "--porcelain"]
    try:
        status_result = _run(status_command, cwd=worktree_path)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(
            f"[!] Comando non eseguibile: {shlex.join(status_command)}: {exc}",
            file=sys.stderr,
        )
        return 1
    if status_result.returncode != 0:
        _print_failure(status_command, status_result)
        return 1
    if status_result.stdout.strip():
        print(
            "[!] Pulizia rifiutata: il worktree contiene modifiche non committate.",
            file=sys.stderr,
        )
        return 1

    if not _remove_worktree(worktree_path):
        return 1
    if not _delete_branch(branch):
        return 1
    print("Pulizia completata con successo.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Orca Worktree Cleanup per Divario Italia")
    parser.add_argument("slug", help="Nome / slug del task")
    parser.add_argument("--dry-run", action="store_true", help="Mostra i comandi")
    args = parser.parse_args(argv)
    return run_clean(slug=args.slug, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
