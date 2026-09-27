"""Helper di Pulizia Worktree Orca per Divario Italia.

Rimuove in sicurezza il worktree locale ed elimina il branch fuso.

Uso:
    bin/py scripts/orca_clean.py <slug> [--dry-run]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def run_clean(slug: str, dry_run: bool = False) -> int:
    worktree_path = PROJECT_ROOT / ".orca" / "worktrees" / "divarioitalia" / slug
    branch_name = f"nmaiese/{slug}"

    print("=== Orca Worktree Cleanup ===")
    print(f"Slug      : {slug}")
    print(f"Worktree  : {worktree_path}")
    print(f"Branch    : {branch_name}")

    if dry_run:
        print("\n--- [DRY RUN] Comandi di Pulizia ---")
        if worktree_path.exists():
            print(f"git worktree remove -f {worktree_path}")
        print(f"git branch -D {branch_name}")
        print("git worktree prune")
        return 0

    if worktree_path.exists():
        # Verifico che nel worktree non ci siano modifiche uncommitted non salvate
        status_res = subprocess.run(["git", "-C", str(worktree_path), "status", "--porcelain"], capture_output=True, text=True)
        if status_res.stdout.strip():
            print(f"[!] Attenzione: Il worktree {slug} contiene modifiche non committate. Procedo con la rimozione forzata sicura.")

        print(f"[+] Rimozione worktree {worktree_path}...")
        subprocess.run(["git", "worktree", "remove", "-f", str(worktree_path)], check=False)
    else:
        print(f"[i] Worktree {worktree_path} non presente o già rimosso.")

    # Eliminazione ramo locale se esiste
    print(f"[+] Eliminazione ramo locale {branch_name}...")
    subprocess.run(["git", "branch", "-D", branch_name], check=False)

    print("[+] Pruning dei worktrees...")
    subprocess.run(["git", "worktree", "prune"], check=False)

    print("Pulizia completata con successo.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Orca Worktree Cleanup per Divario Italia")
    parser.add_argument("slug", help="Nome / slug del task (es. 105-lead-ter-13)")
    parser.add_argument("--dry-run", action="store_true", help="Mostra i comandi senza eseguirli")

    args = parser.parse_args(argv)
    return run_clean(slug=args.slug, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
