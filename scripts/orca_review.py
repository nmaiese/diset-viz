"""Helper di Review Orca + GitHub per Divario Italia.

Apre una Draft PR su GitHub, aggiorna la label della Issue a `status:in-review`
ed imposta lo stato della card Orca.

Uso:
    bin/py scripts/orca_review.py <slug> [--issue <ID>] [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def run_review(slug: str, issue_id: int | None = None, dry_run: bool = False) -> int:
    branch_name = f"nmaiese/{slug}"
    
    # Se issue_id non è fornito, tenta di estrarlo dallo slug (es. 105-nuova-scheda)
    if issue_id is None:
        match = re.match(r"^(\d+)-", slug)
        if match:
            issue_id = int(match.group(1))

    print("=== Orca + GitHub Review Dispatcher ===")
    print(f"Slug      : {slug}")
    print(f"Branch    : {branch_name}")
    print(f"Issue ID  : {issue_id or 'N/A'}")

    if dry_run:
        print("\n--- [DRY RUN] Comandi GitHub CLI ---")
        print(f"git push -u origin {branch_name}")
        if issue_id:
            print(f"gh pr create --draft --body 'Closes #{issue_id}' --title 'Risolve #{issue_id}: {slug}'")
            print(f"gh issue edit {issue_id} --add-label 'status:in-review' --remove-label 'status:in-progress'")
        else:
            print(f"gh pr create --draft --title '{slug}'")
        return 0

    # 1. Push su GitHub origin
    print(f"[+] Push del branch {branch_name} su origin...")
    subprocess.run(["git", "push", "-u", "origin", branch_name], check=False)

    # 2. Creazione Draft PR
    if issue_id:
        cmd_pr = [
            "gh", "pr", "create",
            "--draft",
            "--title", f"Risolve #{issue_id}: {slug}",
            "--body", f"Closes #{issue_id}",
            "--base", "master",
        ]
        cmd_issue = [
            "gh", "issue", "edit", str(issue_id),
            "--add-label", "status:in-review",
            "--remove-label", "status:in-progress",
        ]
        print(f"[+] Creazione Draft PR: {' '.join(cmd_pr)}")
        subprocess.run(cmd_pr, check=False)
        print(f"[+] Aggiornamento label Issue: {' '.join(cmd_issue)}")
        subprocess.run(cmd_issue, check=False)
    else:
        cmd_pr = ["gh", "pr", "create", "--draft", "--title", slug, "--base", "master"]
        print(f"[+] Creazione Draft PR: {' '.join(cmd_pr)}")
        subprocess.run(cmd_pr, check=False)

    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Orca Review Dispatcher per Divario Italia")
    parser.add_argument("slug", help="Nome / slug del task (es. 105-lead-ter-13)")
    parser.add_argument("--issue", type=int, default=None, help="ID della Issue GitHub collegata")
    parser.add_argument("--dry-run", action="store_true", help="Mostra le operazioni senza eseguirle")

    args = parser.parse_args(argv)
    return run_review(slug=args.slug, issue_id=args.issue, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
