#!/usr/bin/env python3
"""La guardia per-agente: il perimetro applicato mentre l'agente lavora.

Il cancello (`pipeline_gate.py`) giudica il branch alla fine della run, e resta
l'unico verdetto che conta. Ma tra l'inizio della run e quel verdetto un agente
con Bash pieno puo' fare molte cose che il cancello non vede mai: un comando
distruttivo non lascia un diff da giudicare, un `gh pr merge` diretto salta il
passo di merge, una scrittura fuori perimetro viene scoperta solo quando il
lavoro e' gia' tutto fatto. Questa guardia sposta il "no" al momento del gesto,
come hook PreToolUse dichiarato nel frontmatter di ogni agente della catena.

Non sostituisce niente: e' difesa in profondita'. La lista dei percorsi resta
`pipeline_gate.STAGE_PATHS`, importata e mai ricopiata, per la stessa ragione
per cui il perimetro sta nel repo e non nel prompt: una copia locale sarebbe
gia' in disaccordo con l'originale la settimana prossima.

Tre modi d'uso, tutti da hook (il JSON dell'evento arriva su stdin):

    python3 scripts/agent_guard.py --stage writer                  # PreToolUse
    python3 scripts/agent_guard.py --stage hunter --stage promoter # perimetro a due stadi
    python3 scripts/agent_guard.py --stage writer --check close    # Stop / SubagentStop

Uscita 0 = permesso, 2 = bloccato con la ragione su stderr, che e' il canale
che l'harness rilegge all'agente. Un errore interno della guardia esce 0 con
una nota: il cancello a valle resta intero, e una guardia che si rompe non deve
fermare una catena non presidiata su un guasto che non e' dell'agente.

Stdlib puro, come tutto il resto della catena.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import pipeline_gate  # noqa: E402  (bootstrap del path qui sopra)

# Gli stadi che la guardia sa sorvegliare. Sono quelli del cancello piu' il
# dispatcher, che del cancello non e' uno stadio (non apre pull request, non ha
# una voce in STAGE_PATHS) ma un agente e': il suo perimetro di scrittura e' il
# solo diario, perche' tutto il resto del suo giro passa dagli script, mai da
# Edit/Write. La voce sta qui e non in STAGE_PATHS apposta: aggiungerla la'
# insegnerebbe al cancello uno stadio che non deve mai giudicare.
GUARDED_STAGES = dict(pipeline_gate.STAGE_PATHS)
GUARDED_STAGES["dispatch"] = (pipeline_gate.RUN_JOURNAL,)

# Comandi che nessuno stadio ha motivo di dare, mai. Regex sul comando intero,
# prima di ogni altra valutazione: un pattern qui vince anche su un prefisso
# permesso ("git push --force" comincia con "git").
DENY_PATTERNS = (
    (r"\brm\s+(-[a-zA-Z]*[rf][a-zA-Z]*\s+)+", "rm ricorsivo o forzato"),
    (r"\bgit\s+push\b.*(--force|--force-with-lease|\s-f\b)", "git push --force"),
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard"),
    (r"\bgit\s+clean\b", "git clean"),
    (r"\bgit\s+filter-branch\b", "git filter-branch"),
    # Il merge della catena passa da scripts/pipeline_merge.py, che aspetta i
    # check remoti. `gh pr merge` diretto non aspetta niente (CLAUDE.md spiega
    # il perche', un probe l'ha dimostrato) e qui e' vietato in ogni forma.
    (r"\bgh\s+pr\s+merge\b", "gh pr merge (usa scripts/pipeline_merge.py)"),
    # Il web per gli agenti e' WebFetch/WebSearch, che passano dai controlli
    # dell'harness. curl e wget li scavalcherebbero, e "scaricato ed eseguito"
    # e' la forma di guasto che non vogliamo nemmeno dover ripulire.
    (r"\bcurl\b", "curl (usa WebFetch)"),
    (r"\bwget\b", "wget (usa WebFetch)"),
    (r"\bsudo\b", "sudo"),
    (r"\bapt(-get)?\s+install\b", "apt install"),
)

# Le famiglie di comandi di cui una run ha davvero bisogno. Prefissi sul primo
# token (o sui primi due per gh e git), un segmento per volta: un comando
# composto con && o | viene giudicato pezzo per pezzo.
#
# La lista e' volutamente generosa sul leggere e stretta sull'agire fuori dal
# repo: python fa girare gli script della catena e la suite, git e gh pr
# aprono la pull request, il resto e' consultazione. Quello che manca (npm,
# pip fuori dal venv, docker, ...) non serve a nessuno stadio, e uno stadio a
# cui servisse davvero e' una conversazione da avere, non un buco da lasciare.
ALLOW_SINGLE = {
    "python", "python3", ".venv/bin/python", ".venv/bin/python3",
    "ls", "cat", "head", "tail", "wc", "grep", "rg", "find", "diff",
    "sort", "uniq", "cut", "tr", "sed", "awk", "date", "pwd", "echo",
    "printf", "true", "test", "[", "cd", "which", "command", "env",
    "mkdir", "cp", "mv", "touch", "jq", "sha256sum", "xargs",
}
ALLOW_PAIRS = {
    ("git", None),          # tutto git, salvo i DENY_PATTERNS qui sopra
    ("gh", "pr"),           # create/view/checks/diff/comment; merge e' negato sopra
    ("gh", "run"),
    ("gh", "auth"),
    (".venv/bin/pip", "install"),   # solo per ricreare l'ambiente che il gate pretende
    ("pip", "install"),
}

# Fuori dal repo l'agente puo' scrivere dove vuole: uno scratch in /tmp non
# arriva in nessuna pull request. Il perimetro riguarda solo il repo.
SERVICE_PATHS = (
    # Il meta di sessione che session-start.sh scrive e pipeline_log.py legge:
    # locale, ignorato da git, ma dentro l'albero del repo.
    "data/pipeline/.session_meta.json",
    "data/pipeline/tool_failures.jsonl",
)


def _stages_paths(stages):
    allowed = []
    for stage in stages:
        for entry in GUARDED_STAGES[stage]:
            if entry not in allowed:
                allowed.append(entry)
    return tuple(allowed)


def command_verdict(command, stages):
    """(ok, ragione) per un comando Bash."""
    for pattern, label in DENY_PATTERNS:
        if re.search(pattern, command):
            return False, (
                f"comando vietato dalla guardia dello stadio: {label}. "
                "Il perimetro e la procedura stanno in docs/AGENT_CONTRACT.md."
            )
    # Un segmento per volta: "a && b | c" sono tre gesti, non uno.
    for segment in re.split(r"&&|\|\||\||;|\n", command):
        segment = segment.strip()
        if not segment:
            continue
        try:
            tokens = shlex.split(segment)
        except ValueError:
            tokens = segment.split()
        # Le assegnazioni d'ambiente davanti al comando non sono il comando.
        while tokens and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]):
            tokens = tokens[1:]
        if not tokens:
            continue
        head = tokens[0]
        second = tokens[1] if len(tokens) > 1 else None
        if head in ALLOW_SINGLE:
            continue
        if any(head == a and (b is None or second == b) for a, b in ALLOW_PAIRS):
            continue
        return False, (
            f"'{head}' non e' fra i comandi che questo stadio usa. Permessi: "
            "python/python3 (script della catena e suite), git, gh pr/run/auth, "
            "lettura file (ls, cat, grep, ...). Se il lavoro richiede altro, "
            "fermati e segnalalo nella riga di diario invece di aggirare la guardia."
        )
    return True, ""


def path_verdict(path, stages, cwd=None):
    """(ok, ragione) per una scrittura via Edit/Write."""
    base = Path(cwd) if cwd else PROJECT_ROOT
    resolved = (base / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    try:
        relative = resolved.relative_to(PROJECT_ROOT)
    except ValueError:
        # Fuori dal repo: scratch legittimo, il perimetro non c'entra.
        return True, ""
    rel = str(relative)
    if rel in SERVICE_PATHS:
        return True, ""
    allowed = _stages_paths(stages)
    if pipeline_gate.path_allowed(rel, allowed):
        return True, ""
    return False, (
        f"'{rel}' e' fuori dal perimetro dello stadio "
        f"({', '.join(stages)}): puoi toccare solo {', '.join(allowed)}. "
        "Il cancello bloccherebbe comunque questa run: meglio fermarla adesso."
    )


def close_verdict(stages, cwd=None):
    """(ok, ragione) alla chiusura: una run su automation/* deve avere il diario.

    Ripete via `pipeline_gate.check_run_is_recorded` lo stesso controllo che il
    cancello fara' comunque, ma al momento in cui l'agente sta per fermarsi,
    che e' l'unico momento in cui puo' ancora rimediare da solo.
    """
    code, out, _ = pipeline_gate._git("rev-parse", "--abbrev-ref", "HEAD", cwd=cwd)
    branch = out.strip() if code == 0 else ""
    if not branch.startswith("automation/"):
        return True, ""
    paths = pipeline_gate.changed_paths(cwd=cwd)
    if not paths:
        return True, ""
    for stage in stages:
        check = pipeline_gate.check_run_is_recorded(stage, paths, cwd=cwd)
        if check.ok:
            return True, ""
    return False, (
        f"stai chiudendo una run su '{branch}' senza la riga di diario dello "
        f"stadio. {check.detail}"
    )


def main():
    parser = argparse.ArgumentParser(description="La guardia per-agente della catena.")
    parser.add_argument("--stage", action="append", required=True,
                        choices=sorted(GUARDED_STAGES),
                        help="ripetibile: il cacciatore chiude anche da promotore")
    parser.add_argument("--check", choices=("tool", "close"), default="tool")
    args = parser.parse_args()

    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    cwd = payload.get("cwd") or None

    try:
        if args.check == "close":
            ok, reason = close_verdict(args.stage, cwd=cwd)
        else:
            tool = payload.get("tool_name") or ""
            tool_input = payload.get("tool_input") or {}
            if tool == "Bash":
                ok, reason = command_verdict(tool_input.get("command") or "", args.stage)
            elif tool in ("Edit", "Write", "NotebookEdit"):
                target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
                ok, reason = path_verdict(target, args.stage, cwd=cwd)
            else:
                ok, reason = True, ""
    except Exception as exc:  # pragma: no cover - la guardia non deve fermare la catena
        print(f"agent_guard: errore interno ({type(exc).__name__}), gesto permesso, "
              "il cancello a valle giudica comunque", file=sys.stderr)
        return 0

    if ok:
        return 0
    print(reason, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
