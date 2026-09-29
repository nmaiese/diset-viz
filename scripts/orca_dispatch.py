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
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:  # immagini senza git, come quella dei test di Cloud Build
        return PROJECT_ROOT
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

DEV_TOOLS = Path(os.environ.get("DEV_TOOLS", Path.home() / "dev" / "dev-tools"))

# Alias di ruolo -> attivita' di ~/dev/dev-tools/agents/ruoli.tsv, che e' la fonte unica:
# quale agente esegua l'attivita' lo decide orca-lancia.sh, in base alla quota.
ROLE_TO_ATTIVITA = {
    "worker": "implementazione",
    "architect": "architettura",
    "researcher": "ricerca",
}

TASK_TEMPLATE = """# Task: {title}

> Status: in-progress
> Assegnato a: {attivita}
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


def build_task_content(
    slug: str,
    title: str,
    objective: str,
    attivita: str,
    branch: str | None = None,
) -> str:
    """Compone il contratto da salvare nel worktree creato da Orca."""
    content = TASK_TEMPLATE.format(
        title=title,
        attivita=attivita,
        slug=slug,
        objective=objective,
        python=MAIN_ROOT / ".venv" / "bin" / "python",
    )
    if branch:
        content = content.replace(f"> Branch: nmaiese/{slug}", f"> Branch: {branch}")
    return content


def orca_worktree_script() -> Path:
    return Path(os.environ.get("ORCA_WORKTREE", DEV_TOOLS / "scripts" / "orca-worktree.sh"))


def orca_lancia_script() -> str:
    return os.environ.get("ORCA_LANCIA", str(DEV_TOOLS / "scripts" / "orca-lancia.sh"))


def resolve_attivita(role: str = "worker", attivita: str | None = None) -> str | None:
    """L'attivita' esplicita vince sul ruolo; un ruolo sconosciuto da' None."""
    return attivita or ROLE_TO_ATTIVITA.get(role.lower())


def dispatch_task(
    slug: str,
    title: str,
    objective: str,
    role: str = "worker",
    dry_run: bool = False,
    attivita: str | None = None,
    sola_lettura: bool = False,
) -> int:
    """Crea il worktree (orca-worktree.sh), vi scrive ``TASK.md`` e delega a orca-lancia.sh.

    Il lancio, la scelta dell'agente per quota e il controllo della spec sono di
    orca-lancia.sh: qui non si sceglie nessun agente e non si lancia in headless.
    """
    resolved = resolve_attivita(role, attivita)
    if not resolved:
        print(f"[!] Ruolo Orca non valido: {role}", file=sys.stderr)
        return 1

    lancia = [orca_lancia_script(), "--attivita", resolved, "--worktree", slug]

    if dry_run:
        # Solo stampa: niente Orca, niente disco (deve andare in CI e in Cloud Build).
        spec = f"<worktree {slug}>/TASK.md"
        cmd = [*lancia, "--spec-file", spec]
        if sola_lettura:
            cmd.append("--sola-lettura")
        print(shlex.join(cmd))
        return 0

    wt_cmd = [
        str(orca_worktree_script()),
        slug,
        "--repo",
        ORCA_REPO_PATH,
        "--base-branch",
        "origin/master",
    ]
    print(f"[+] Esecuzione: {shlex.join(wt_cmd)}")
    try:
        created = subprocess.run(
            wt_cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL, check=False
        )
    except OSError as exc:
        print(f"[!] Impossibile eseguire orca-worktree.sh: {exc}", file=sys.stderr)
        return 1
    if created.returncode != 0 or not created.stdout.strip():
        if created.stderr.strip():
            print(created.stderr.strip(), file=sys.stderr)
        print(f"[!] Worktree non creato (exit {created.returncode}).", file=sys.stderr)
        return created.returncode or 1
    worktree_path = Path(created.stdout.strip().splitlines()[-1])
    if not worktree_path.is_dir():
        print(f"[!] Il worktree non e' una directory: {worktree_path}", file=sys.stderr)
        return 1

    task_file = worktree_path / "TASK.md"
    task_file.write_text(
        build_task_content(slug, title, objective, resolved), encoding="utf-8"
    )
    print(f"[+] Scritto {task_file}")

    cmd = [*lancia, "--spec-file", str(task_file)]
    if sola_lettura:
        cmd.append("--sola-lettura")
    print(f"[+] Esecuzione: {shlex.join(cmd)}")
    try:
        # Niente capture_output: l'esito e i controlli di orca-lancia.sh vanno in chiaro a chi lancia.
        return subprocess.run(cmd, cwd=MAIN_ROOT, check=False).returncode
    except OSError as exc:
        print(f"[!] Impossibile eseguire orca-lancia.sh: {exc}", file=sys.stderr)
        return 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Orca Task Dispatcher per Divario Italia")
    parser.add_argument("slug", help="Nome breve / slug del task")
    parser.add_argument("--title", default="", help="Titolo esteso del task")
    parser.add_argument("--objective", default="", help="Obiettivo dettagliato del task")
    mapping_help = ", ".join(f"{r}={a}" for r, a in ROLE_TO_ATTIVITA.items())
    parser.add_argument(
        "--role",
        choices=list(ROLE_TO_ATTIVITA),
        default="worker",
        help=f"Ruolo, alias di un'attivita' di ruoli.tsv ({mapping_help})",
    )
    parser.add_argument(
        "--attivita",
        help="Attivita' di ruoli.tsv: vince su --role",
    )
    parser.add_argument(
        "--sola-lettura",
        action="store_true",
        help="Lancia l'agente in sola lettura (review, ricerca)",
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
        attivita=args.attivita,
        sola_lettura=args.sola_lettura,
    )


if __name__ == "__main__":
    sys.exit(main())
