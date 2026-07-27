#!/usr/bin/env python3
"""The merge step: the only way a stage of the chain lands on master.

This exists because the instruction it replaces was a lie, and the lie was
invisible. The contract used to tell three stages to close with

    gh pr merge --auto --squash --delete-branch

on the belief that `--auto` parks the pull request until the remote checks go
green. It does not, on this repository: `allow_auto_merge` is false and `master`
carries no protection, so `gh` silently falls back to merging immediately. A
probe pull request merged with the `python` job still `IN_PROGRESS`. Every
"waits for the checks" stage had been merging blind since the day the policy was
written, and nothing anywhere would have said so.

So the wait lives here, in code, where it can be read and tested, instead of in
an agent's memory of a flag's semantics:

- `blocked`  refuse. Not "warn": refuse, non-zero exit, no merge.
- `auto`     merge now. Prose only, and the gate has already run the suite.
- `checks`   poll the pull request until every check concludes, merge only if
             they all passed, refuse if any failed, give up loudly on timeout.

The verdict is not taken from the caller. This script re-runs the gate itself,
because a merge step that trusts the agent's report of its own verdict protects
nothing at all: the one moment worth checking is exactly the moment an agent
that got it wrong would rather skip.

Pure stdlib, like the rest of the chain, so it runs on a fresh cloud checkout
that has no venv yet. It shells out to `gh`, which the agents already have.

    python3 scripts/pipeline_merge.py --stage writer --pr 42
    python3 scripts/pipeline_merge.py --stage curator --pr 43 --dry-run
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import pipeline_gate, pipeline_log  # noqa: E402  (path bootstrap above)

# How long to wait for the remote checks, and how often to look. Fifteen seconds
# is polite to the API and invisible next to a CI run that takes minutes.
POLL_SECONDS = 15
CHECKS_TIMEOUT = 45 * 60
# GitHub does not register the checks the instant the pull request opens. Waiting
# a little for them to appear is not the same as accepting a pull request that
# has none, and the two must not be confused: no checks at all means `checks`
# cannot be satisfied, and that is a refusal, not a pass.
CHECKS_APPEAR_TIMEOUT = 5 * 60

PASSING = {"pass", "skipping"}
PENDING = {"pending"}


def _run(argv, cwd=None):
    """Every external command goes through here, so a test can replace one thing."""
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def check_states(pr, runner=_run, cwd=None):
    """The state of every check on a pull request, as {name: bucket}.

    `gh` buckets a check into pass / fail / pending / skipping / cancel, which is
    exactly the vocabulary needed and saves interpreting the raw conclusions.
    """
    code, out = runner(["gh", "pr", "checks", str(pr), "--json", "name,bucket"], cwd=cwd)
    text = out.strip()
    if not text or text.lstrip()[:1] not in "[{":
        # `gh` says "no checks reported" on stderr and exits non-zero. That is a
        # legitimate transient state right after the push, so it is not an error
        # here: the caller decides how long to keep asking.
        return {}
    try:
        rows = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return {row.get("name", "?"): (row.get("bucket") or "pending") for row in rows}


def wait_for_checks(pr, runner=_run, cwd=None, sleep=time.sleep,
                    timeout=CHECKS_TIMEOUT, appear_timeout=CHECKS_APPEAR_TIMEOUT,
                    log=print):
    """Poll until every check has concluded. Returns (ok, detail).

    Three ways out, and each one has to be distinguishable by the caller, because
    "the checks failed" and "the checks never showed up" want opposite fixes.
    """
    waited = 0
    while True:
        states = check_states(pr, runner=runner, cwd=cwd)
        if not states:
            if waited >= appear_timeout:
                return False, (
                    f"nessun check risulta sulla PR #{pr} dopo {waited // 60} minuti. "
                    "Con la politica 'checks' questo e' un rifiuto: non c'e' niente da aspettare."
                )
        else:
            failed = sorted(n for n, b in states.items() if b not in PASSING and b not in PENDING)
            if failed:
                return False, f"check falliti: {', '.join(failed)}"
            pending = sorted(n for n, b in states.items() if b in PENDING)
            if not pending:
                return True, f"tutti i check verdi: {', '.join(sorted(states))}"
            log(f"  in attesa di {', '.join(pending)} ({waited // 60}m{waited % 60:02d}s)")
        if waited >= timeout:
            return False, f"i check non hanno concluso entro {timeout // 60} minuti"
        sleep(POLL_SECONDS)
        waited += POLL_SECONDS


def merge(pr, runner=_run, cwd=None):
    code, out = runner(
        ["gh", "pr", "merge", str(pr), "--squash", "--delete-branch"], cwd=cwd
    )
    return code == 0, out.strip()


def record_landing(stage, pr, result, runner=_run, cwd=None, log=print, attempts=3):
    """Scrive su master la riga di diario con l'esito vero, e la spinge.

    Esiste perche' il diario non poteva quasi mai dire come e' finita, e il modo
    in cui non poteva e' istruttivo. La riga sta nel perimetro dello stadio,
    quindi viaggia dentro la pull request e va committata **prima** che la pull
    request si fonda: quando l'agente la scrive non sa ancora l'esito, e scrive
    `pr-open`. Il cacciatore ha scritto `pr-open` e si e' fuso trenta secondi
    dopo, e per mezza giornata il diario ha raccontato che nessuno stadio
    `checks` si fosse mai chiuso da solo, mentre la #45 diceva il contrario.

    L'altra meta' del buco e' peggiore. Quando il cancello o i check rifiutano, la
    riga dell'agente resta su un branch che non si fonde mai, quindi **da master
    non si vede affatto**: la run del 26 luglio dello scout esiste, dice
    `blocked`, e vive su `automation/scout-2026-07-26` dove nessuno strumento la
    legge. Una run rifiutata e una run mai avvenuta producono lo stesso master,
    che e' esattamente la confusione che il diario esiste per togliere.

    Quindi la riga la scrive chi l'esito lo conosce, cioe' questo passo, per ogni
    uscita terminale e non solo per il merge. Il docstring di `decide` prometteva
    gia' un dizionario "che il chiamante trasforma in una riga di diario": il
    chiamante era l'agente, cioe' la parte che in un caso su due non l'ha fatto.

    Il lavoro avviene in un worktree usa e getta su `origin/master`, mai
    nell'albero dell'agente, che a questo punto e' su un branch appena cancellato
    dal remoto e non va toccato. Se il push perde una corsa contro un altro
    stadio si ricomincia da capo: si rilegge `origin/master`, che nel frattempo
    porta la riga dell'altro, e la nostra le va dietro. Su un registro in coda un
    ritentativo e' automaticamente corretto, ed e' la stessa ragione per cui il
    passo 3-bis del contratto dice di tenere entrambe le righe.
    """
    import shutil
    import tempfile

    outcome = result["outcome"]
    summary = {
        "merged": f"PR #{pr} fusa in master dal passo di merge",
        "blocked": f"PR #{pr} non fusa: il cancello e' rosso",
        "stopped": f"PR #{pr} non fusa: i check non l'hanno permesso",
        "error": f"PR #{pr} non fusa: il merge e' fallito",
    }.get(outcome, f"PR #{pr}: {outcome}")

    for attempt in range(1, attempts + 1):
        runner(["git", "worktree", "prune"], cwd=cwd)
        code, out = runner(["git", "fetch", "origin", "master"], cwd=cwd)
        if code != 0:
            log(f"  diario: fetch fallito ({out.strip()[:120]})")
            continue
        code, head = runner(["git", "rev-parse", "--short", "origin/master"], cwd=cwd)
        tip = head.strip() if code == 0 else ""
        tmp = tempfile.mkdtemp(prefix="diario-")
        try:
            code, out = runner(
                ["git", "worktree", "add", "--detach", tmp, "origin/master"], cwd=cwd
            )
            if code != 0:
                log(f"  diario: worktree fallito ({out.strip()[:120]})")
                continue
            entry = pipeline_log.build_entry(
                stage, outcome, summary,
                detail=[result["detail"]] if result.get("detail") else [],
                gate=result.get("gate"), pr=pr, commit=tip, branch="master",
            )
            pipeline_log.append(entry, path=Path(tmp) / "data" / "pipeline" / "runs.jsonl")
            runner(["git", "add", "data/pipeline/runs.jsonl"], cwd=tmp)
            code, out = runner(
                ["git", "commit", "-m", f"Diario: {summary}"], cwd=tmp
            )
            if code != 0:
                log(f"  diario: commit fallito ({out.strip()[:120]})")
                continue
            code, out = runner(["git", "push", "origin", "HEAD:master"], cwd=tmp)
            if code == 0:
                log(f"  diario: riga '{outcome}' scritta su master")
                return True
            log(f"  diario: push perso, ritento ({attempt}/{attempts})")
        finally:
            # Due passaggi e non uno: `worktree remove` cancella la directory
            # quando il worktree e' stato creato davvero, ma se `add` e' fallito
            # resta la cartella vuota di mkdtemp, e una run al giorno che perde
            # una cartella e' una perdita lenta che nessuno collega alla causa.
            runner(["git", "worktree", "remove", "--force", tmp], cwd=cwd)
            shutil.rmtree(tmp, ignore_errors=True)

    # Non e' un fallimento del merge, che e' gia' avvenuto o gia' stato rifiutato.
    # Va detto forte comunque: da qui in poi master non sa come e' finita.
    log(f"  DIARIO NON SCRITTO dopo {attempts} tentativi. "
        f"Registrala a mano: pipeline_log.py --write --stage {stage} "
        f"--outcome {outcome} --pr {pr}")
    return False


def decide(stage, pr, verdict=None, runner=_run, cwd=None, sleep=time.sleep,
           dry_run=False, log=print, skip_tests=False, journal=True):
    """Run the gate, obey it, and merge only if the gate and the checks agree.

    Returns the dict the caller should turn into a journal row, so that a run
    that refused to merge still leaves the same kind of trace as one that did.
    """
    if verdict is None:
        verdict = pipeline_gate.run(stage, skip_tests=skip_tests, cwd=cwd)
    mode = verdict["merge"]
    log(f"stadio {stage}, PR #{pr}, cancello: {mode}")

    def finish(result):
        """Ogni uscita terminale passa di qui, e nessuna sfugge al diario.

        `pr-open` no: li' non e' finito niente, la pull request resta aperta e la
        riga che l'agente ha gia' committato dentro la PR la descrive bene.
        """
        if journal and not dry_run and result["outcome"] != "pr-open":
            record_landing(stage, pr, result, runner=runner, cwd=cwd, log=log)
        return result

    if mode == "blocked":
        failed = [c["check"] for c in verdict["checks"] if not c["ok"]]
        detail = "il cancello e' rosso: " + ", ".join(failed)
        log(f"  RIFIUTO. {detail}")
        return finish({"merged": False, "outcome": "blocked", "gate": mode, "detail": detail})

    if mode == "checks":
        ok, detail = wait_for_checks(pr, runner=runner, cwd=cwd, sleep=sleep, log=log)
        if not ok:
            log(f"  RIFIUTO. {detail}")
            return finish({"merged": False, "outcome": "stopped", "gate": mode, "detail": detail})
        log(f"  {detail}")

    if dry_run:
        log("  --dry-run: mi fermo qui, la PR resta aperta.")
        return {"merged": False, "outcome": "pr-open", "gate": mode, "detail": "dry run"}

    ok, out = merge(pr, runner=runner, cwd=cwd)
    if not ok:
        log(f"  il merge e' fallito: {out}")
        return finish({"merged": False, "outcome": "error", "gate": mode, "detail": out})
    log(f"  PR #{pr} fusa in master.")
    return finish({"merged": True, "outcome": "merged", "gate": mode, "detail": out})


def main():
    parser = argparse.ArgumentParser(
        description="Fonde la PR di uno stadio, ma solo se il cancello e i check lo permettono.",
        epilog="uscita 0 = fusa, 1 = non fusa (e il motivo e' stampato).",
    )
    parser.add_argument("--stage", required=True, choices=sorted(pipeline_gate.STAGE_PATHS))
    parser.add_argument("--pr", required=True, help="numero della pull request")
    parser.add_argument("--dry-run", action="store_true",
                        help="arriva fino al merge e non lo fa")
    parser.add_argument("--skip-tests", action="store_true",
                        help="non rilanciare la suite dentro il cancello (solo per un giro a vuoto)")
    parser.add_argument("--no-journal", action="store_true",
                        help="non scrivere la riga di esito su master (solo per prove)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = decide(args.stage, args.pr, dry_run=args.dry_run, skip_tests=args.skip_tests,
                    journal=not args.no_journal)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["merged"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
