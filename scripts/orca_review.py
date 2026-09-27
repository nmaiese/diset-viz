"""Pubblica un ramo Orca e apre la relativa pull request in bozza."""

from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class WorktreeResolutionError(RuntimeError):
    """Indica che uno slug non identifica un solo worktree."""


def find_worktree_path(porcelain: str, slug: str) -> Path:
    """Trova ``slug`` o ``slug-N`` nell'output porcelain di Git."""
    paths = [
        Path(line.removeprefix("worktree "))
        for line in porcelain.splitlines()
        if line.startswith("worktree ")
    ]
    suffix_pattern = re.compile(rf"^{re.escape(slug)}-\d+$")
    matches = [
        path for path in paths if path.name == slug or suffix_pattern.fullmatch(path.name)
    ]
    if not matches:
        raise WorktreeResolutionError(f"Nessun worktree trovato per lo slug {slug!r}.")
    if len(matches) > 1:
        rendered = ", ".join(str(path) for path in matches)
        raise WorktreeResolutionError(
            f"Slug ambiguo {slug!r}; corrisponde a: {rendered}."
        )
    return matches[0]


def _run_capture(
    command: list[str], cwd: Path = PROJECT_ROOT
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(command, 124, "", f"Timeout: {exc}")
    except OSError as exc:
        return subprocess.CompletedProcess(command, 1, "", str(exc))


def resolve_worktree(slug: str) -> tuple[Path, str]:
    """Risolve percorso e ramo interrogando Git, senza ricostruirli dallo slug."""
    list_cmd = ["git", "worktree", "list", "--porcelain"]
    result = _run_capture(list_cmd)
    if result.returncode != 0:
        raise WorktreeResolutionError(
            f"Comando fallito: {shlex.join(list_cmd)}\n{result.stderr.strip()}"
        )
    path = find_worktree_path(result.stdout, slug)

    branch_cmd = ["git", "branch", "--show-current"]
    branch_result = _run_capture(branch_cmd, cwd=path)
    branch = branch_result.stdout.strip()
    if branch_result.returncode != 0 or not branch:
        raise WorktreeResolutionError(
            f"Comando fallito: git -C {shlex.quote(str(path))} branch --show-current\n"
            f"{branch_result.stderr.strip()}"
        )
    return path, branch


def _print_failure(command: list[str], result: subprocess.CompletedProcess[str]) -> None:
    print(f"[!] Comando fallito: {shlex.join(command)}", file=sys.stderr)
    if result.stdout.strip():
        print(result.stdout.strip(), file=sys.stderr)
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)


def _task_body(worktree_path: Path, issue_id: int | None) -> str:
    task_file = worktree_path / "TASK.md"
    parts = []
    if task_file.is_file():
        parts.append(task_file.read_text(encoding="utf-8").rstrip())
    if issue_id is not None:
        parts.append(f"Closes #{issue_id}")
    return "\n\n".join(parts) or "Review del lavoro Orca completato."


def _dry_run_identity(slug: str) -> tuple[Path, str]:
    """Usa dati reali quando esistono, altrimenti placeholder non inventati."""
    try:
        return resolve_worktree(slug)
    except WorktreeResolutionError:
        return Path(f"<worktree:{slug}>"), "<ramo-del-worktree>"


def run_review(slug: str, issue_id: int | None = None, dry_run: bool = False) -> int:
    """Verifica il worktree, pubblica il ramo e crea una draft PR."""
    if issue_id is None:
        match = re.match(r"^(\d+)-", slug)
        if match:
            issue_id = int(match.group(1))

    if dry_run:
        worktree_path, branch = _dry_run_identity(slug)
    else:
        try:
            worktree_path, branch = resolve_worktree(slug)
        except WorktreeResolutionError as exc:
            print(f"[!] {exc}", file=sys.stderr)
            return 1

    title = f"Risolve #{issue_id}: {slug}" if issue_id else slug
    body = _task_body(worktree_path, issue_id)
    push_cmd = ["git", "push", "-u", "origin", branch]
    pr_cmd = [
        "gh",
        "pr",
        "create",
        "--draft",
        "--base",
        "master",
        "--head",
        branch,
        "--title",
        title,
        "--body",
        body,
    ]

    print("=== Orca + GitHub Review ===")
    print(f"Worktree  : {worktree_path}")
    print(f"Branch    : {branch}")
    if dry_run:
        print(shlex.join(push_cmd))
        print(shlex.join(pr_cmd))
        return 0

    status_cmd = ["git", "status", "--porcelain"]
    status_result = _run_capture(status_cmd, cwd=worktree_path)
    if status_result.returncode != 0:
        _print_failure(status_cmd, status_result)
        return 1
    if status_result.stdout.strip():
        print("[!] Il worktree contiene modifiche non committate.", file=sys.stderr)
        return 1

    count_cmd = ["git", "rev-list", "--count", "origin/master..HEAD"]
    count_result = _run_capture(count_cmd, cwd=worktree_path)
    if count_result.returncode != 0:
        _print_failure(count_cmd, count_result)
        return 1
    try:
        commit_count = int(count_result.stdout.strip())
    except ValueError:
        _print_failure(count_cmd, count_result)
        return 1
    if commit_count < 1:
        print("[!] Nessun commit sopra origin/master: review rifiutata.", file=sys.stderr)
        return 1

    push_result = _run_capture(push_cmd, cwd=worktree_path)
    if push_result.returncode != 0:
        _print_failure(push_cmd, push_result)
        return push_result.returncode or 1
    pr_result = _run_capture(pr_cmd, cwd=worktree_path)
    if pr_result.returncode != 0:
        _print_failure(pr_cmd, pr_result)
        return pr_result.returncode or 1
    print("[+] Ramo pubblicato e draft PR creata.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Orca Review Dispatcher per Divario Italia")
    parser.add_argument("slug", help="Nome / slug del task")
    parser.add_argument("--issue", type=int, default=None, help="ID della Issue collegata")
    parser.add_argument("--dry-run", action="store_true", help="Mostra i comandi")
    args = parser.parse_args(argv)
    return run_review(slug=args.slug, issue_id=args.issue, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
