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

    python3 scripts/agent_guard.py --stage verificatore                # PreToolUse
    python3 scripts/agent_guard.py --stage admissions --stage launch   # perimetro a due stadi
    python3 scripts/agent_guard.py --stage verificatore --check close  # Stop / SubagentStop

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
# lanciatore (`launch`), che del cancello non e' uno stadio (non apre pull
# request, non ha una voce in STAGE_PATHS) ma un agente e': non fa il lavoro di
# nessun ruolo, legge le code e lancia, e il solo gesto che scrive nel repo e' il
# battito del tick (una riga di diario, portata su master dagli script, mai da
# Edit/Write). La voce sta qui e non in STAGE_PATHS apposta: aggiungerla la'
# insegnerebbe al cancello uno stadio che non deve mai giudicare.
GUARDED_STAGES = dict(pipeline_gate.STAGE_PATHS)
GUARDED_STAGES["launch"] = (pipeline_gate.RUN_JOURNAL,)

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
    # `bin/py` e' l'interprete del progetto (`CLAUDE.md`), e mancava: la guardia
    # conosceva solo `python3` e `.venv/bin/python`, cioe' i due che questo
    # ambiente non garantisce. Ogni comando che un agente e' **istruito** a
    # eseguire cadeva qui prima ancora di partire, compresa la suite in coda a
    # `admissions.md`. Una guardia che rifiuta il comando scritto nel contratto
    # non protegge un perimetro: ferma il lavoro e basta.
    "bin/py",
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

# Prefissi di servizio: directory usa-e-getta, fuori da ogni perimetro di stadio,
# che pero' un agente hooked deve poter scrivere. `evals/out/` e' la cartella di
# lavoro delle eval del canary: e' ignorata da git (non arriva in nessuna pull
# request) e non e' in `STAGE_PATHS`, quindi senza questa deroga l'agente vero,
# con i suoi hook, non potrebbe girare la propria eval. La deroga chiude
# quell'attrito senza allargare cio' che il cancello giudica.
SERVICE_PREFIXES = (
    "evals/out/",
)


def _stages_paths(stages):
    allowed = []
    for stage in stages:
        for entry in GUARDED_STAGES[stage]:
            if entry not in allowed:
                allowed.append(entry)
    return tuple(allowed)


def _bash_write_targets(segment, tokens):
    """I percorsi che questo segmento di comando scrive, per quanto si veda.

    Best effort dichiarato: prende le redirezioni (`>`, `>>`), le destinazioni
    di `cp`/`mv` e gli argomenti di `tee`, che sono i modi ovvi di scrivere un
    file senza passare da Edit/Write. Non prova a essere una sandbox: un
    `python3 -c` puo' scrivere dove vuole e li' restano il cancello e
    l'append-only. Questo controllo esiste per il caso comune, non per il
    caso ostile.
    """
    targets = []
    for match in re.finditer(r"(?<![0-9&])>{1,2}\s*(\S+)", segment):
        target = match.group(1).strip("'\"")
        # `2>&1`, `>&2` e simili non sono file, /dev/* nemmeno.
        if target.startswith("&") or target.startswith("/dev/"):
            continue
        targets.append(target)
    if tokens:
        head = tokens[0]
        positional = [t for t in tokens[1:] if not t.startswith("-")]
        if head in ("cp", "mv") and positional:
            targets.append(positional[-1])
        elif head == "tee":
            targets.extend(positional)
    return targets


def _split_top_level(command):
    """Spacca su `&&`, `||`, `;`, `|`, newline, ma mai dentro le virgolette.

    `re.split` sul comando grezzo spaccava anche dentro una stringa fra
    virgolette: un `-m "riga\\n\\nparagrafo"` o un `--body "a; b"` si
    spezzavano a meta', `shlex.split` falliva sul frammento con virgolette
    sbilanciate, e il ripiego produceva un token a caso che `ALLOW_SINGLE`
    respingeva. Qui si scorre il carattere per volta tenendo lo stato delle
    virgolette (comprese le sequenze `\\x` dentro le doppie, come fa la shell),
    e si spacca solo quando non si e' dentro una di esse. Le virgolette
    restano sempre bilanciate in ogni segmento prodotto, perche' non si puo'
    incontrare un operatore non quotato mentre se ne sta chiudendo una aperta.
    """
    segments = []
    buf = []
    quote = None
    i, n = 0, len(command)
    while i < n:
        ch = command[i]
        if quote:
            buf.append(ch)
            if quote == '"' and ch == "\\" and i + 1 < n:
                buf.append(command[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            buf.append(ch)
            buf.append(command[i + 1])
            i += 2
            continue
        if ch in ("\n", ";"):
            segments.append("".join(buf))
            buf = []
            i += 1
            continue
        if ch in ("|", "&") and i + 1 < n and command[i + 1] == ch:
            segments.append("".join(buf))
            buf = []
            i += 2
            continue
        if ch == "|":
            segments.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    segments.append("".join(buf))
    return segments


# `NOME=$(comando interno)`: l'idioma sanzionato per aprire una PR
# (AGENT_CONTRACT.md, pipeline-close-run/SKILL.md) cattura il numero della PR
# cosi'. Va riconosciuto prima di tokenizzare, perche' shlex non sa cosa sia
# `$(...)` e lo spogliatore di assegnazioni sotto avrebbe altrimenti fatto
# match su `NOME=$(python3` come assegnazione semplice, scartando anche il
# comando vero insieme al nome.
_CAPTURED_ASSIGNMENT = re.compile(r"\A([A-Za-z_][A-Za-z0-9_]*)=\$\((.*)\)\s*\Z", re.DOTALL)


def _segment_verdict(segment, stages):
    """(ok, ragione) per un singolo gesto, gia' isolato da `_split_top_level`."""
    captured = _CAPTURED_ASSIGNMENT.fullmatch(segment)
    if captured:
        return _segment_verdict(captured.group(2), stages)
    try:
        tokens = shlex.split(segment)
    except ValueError:
        tokens = segment.split()
    # Le assegnazioni d'ambiente davanti al comando non sono il comando.
    while tokens and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]):
        tokens = tokens[1:]
    if not tokens:
        return True, ""
    head = tokens[0]
    second = tokens[1] if len(tokens) > 1 else None
    allowed = head in ALLOW_SINGLE or any(
        head == a and (b is None or second == b) for a, b in ALLOW_PAIRS
    )
    if not allowed:
        return False, (
            f"'{head}' non e' fra i comandi che questo stadio usa. Permessi: "
            "python/python3 (script della catena e suite), git, gh pr/run/auth, "
            "lettura file (ls, cat, grep, ...). Se il lavoro richiede altro, "
            "fermati e segnalalo nella riga di diario invece di aggirare la guardia."
        )
    # Un comando permesso puo' ancora scrivere un file: un redirect o una
    # copia sono una Write con un altro vestito, e passano dallo stesso
    # perimetro.
    for target in _bash_write_targets(segment, tokens):
        ok, reason = path_verdict(target, stages)
        if not ok:
            return False, reason
    return True, ""


def command_verdict(command, stages):
    """(ok, ragione) per un comando Bash."""
    for pattern, label in DENY_PATTERNS:
        if re.search(pattern, command):
            return False, (
                f"comando vietato dalla guardia dello stadio: {label}. "
                "Il perimetro e la procedura stanno in docs/AGENT_CONTRACT.md."
            )
    # Un segmento per volta: "a && b | c" sono tre gesti, non uno.
    for segment in _split_top_level(command):
        segment = segment.strip()
        if not segment:
            continue
        ok, reason = _segment_verdict(segment, stages)
        if not ok:
            return False, reason
    return True, ""


def _enclosing_repo_root(resolved, cwd):
    """La radice del working tree che contiene questo percorso.

    Il perimetro si misura da qui, non dal solo `PROJECT_ROOT` dello script della
    guardia. Con i worktree l'agente lavora in un albero sorella
    (`diset-viz-runs/<run_id>`), e misurare sempre dal checkout principale
    accettava come 'scratch esterno' qualunque scrittura nel worktree, cancello
    compreso: la `relative_to(PROJECT_ROOT)` falliva e il gesto passava. Si chiede
    a git a quale working tree appartiene il file (dalla sua cartella, poi dal
    cwd), cosi' il perimetro vale nel worktree della run come nel principale. Se
    il percorso non e' in nessun repo, si torna al principale, e li' la
    `relative_to` fallira' come prima: scratch legittimo."""
    for probe in (resolved.parent, Path(cwd) if cwd else None):
        # Solo cartelle che esistono: un file nuovo puo' avere una cartella
        # genitore non ancora creata, e git con un `cwd` inesistente solleva.
        if probe is None or not probe.is_dir():
            continue
        try:
            code, out, _ = pipeline_gate._git("rev-parse", "--show-toplevel", cwd=str(probe))
        except OSError:
            continue
        if code == 0 and out.strip():
            return Path(out.strip()).resolve()
    return PROJECT_ROOT


def path_verdict(path, stages, cwd=None):
    """(ok, ragione) per una scrittura via Edit/Write."""
    base = Path(cwd) if cwd else PROJECT_ROOT
    resolved = (base / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    root = _enclosing_repo_root(resolved, cwd)
    try:
        relative = resolved.relative_to(root)
    except ValueError:
        # Fuori da ogni repo: scratch legittimo, il perimetro non c'entra.
        return True, ""
    rel = str(relative)
    if rel in SERVICE_PATHS or any(rel.startswith(p) for p in SERVICE_PREFIXES):
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
                        help="ripetibile: un ruolo che copre due perimetri li somma")
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
