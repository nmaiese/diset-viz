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
- `auto`     merge now, on the local gate the caller has already run (suite,
             perimeter, invariants). Every chain stage uses this today.
- `checks`   poll the pull request until every check concludes, merge only if
             they all passed, refuse if any failed, give up loudly on timeout.
             Kept and tested, but no chain stage is `checks` now: the remote CI
             does not fire on a pull request opened through the MCP, so the wait
             could never be satisfied and the pull request froze the chain. See
             `pipeline_gate.MERGE_POLICY` for the full reasoning.

The verdict is not taken from the caller. This script re-runs the gate itself,
because a merge step that trusts the agent's report of its own verdict protects
nothing at all: the one moment worth checking is exactly the moment an agent
that got it wrong would rather skip.

Pure stdlib, like the rest of the chain, so it runs on a fresh cloud checkout
that has no venv yet. It shells out to `gh`, which the agents already have.

It shells out to `gh api`, the REST surface, and never to the porcelain
`gh pr checks` / `gh pr merge`. That is not a stylistic preference. Those two
subcommands are GraphQL, and GraphQL is not always reachable: a session behind
an egress proxy answered every REST call about this repository and refused the
GraphQL endpoint with

    HTTP 403: This GraphQL query is not enabled for this session

which is a wall the merge step used to hit as `gh: command failed` with no hint
of the cause. REST is the smaller and older surface, so a step whose whole job
is to be reliable is better off on it. The cost is that REST has no `bucket`, so
`_bucket` reproduces the classification `gh` was doing for us: the vocabulary is
unchanged and everything downstream reads the same words.

    python3 scripts/pipeline_merge.py --stage writer --pr 42
    python3 scripts/pipeline_merge.py --stage curator --pr 43 --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
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

# La classificazione che `gh pr checks` faceva per noi, rifatta sulle conclusioni
# grezze della REST. `neutral` sta con i verdi perche' li' stava, e `cancelled`
# resta fuori da PASSING: un check annullato non e' un check passato.
_CONCLUSION_BUCKET = {
    "success": "pass",
    "neutral": "pass",
    "skipped": "skipping",
    "cancelled": "cancel",
    "failure": "fail",
    "timed_out": "fail",
    "action_required": "fail",
    "startup_failure": "fail",
    "stale": "fail",
}
# Le commit status della vecchia API, che alcuni servizi usano ancora al posto
# delle check run. Ignorarle vorrebbe dire fondere senza aver guardato.
_STATE_BUCKET = {
    "success": "pass",
    "pending": "pending",
    "failure": "fail",
    "error": "fail",
}


def _run(argv, cwd=None):
    """Every external command goes through here, so a test can replace one thing."""
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _bucket(run):
    """Una check run REST -> il bucket che `gh` avrebbe stampato."""
    if (run.get("status") or "") != "completed":
        return "pending"
    return _CONCLUSION_BUCKET.get(run.get("conclusion") or "", "fail")


def repo_slug(runner=_run, cwd=None):
    """`owner/repo`, e non lo si chiede a `gh` perche' `gh` qui non lo sa.

    Il proxy di uscita riscrive `origin` in qualcosa come
    `http://local_proxy@127.0.0.1:41729/git/nmaiese/diset-viz`, e davanti a quel
    remote `gh` dice "none of the git remotes point to a known GitHub host" e si
    ferma. Gli ultimi due segmenti del percorso pero' sono ancora owner e repo, e
    lo sono anche in `git@github.com:owner/repo.git` e in un URL https normale,
    quindi si prendono da li'. `GH_REPO` vince su tutto, com'e' l'abitudine di
    `gh`, cosi' un caso che non avessi previsto resta sbloccabile senza toccare
    il codice.
    """
    env = (os.environ.get("GH_REPO") or "").strip()
    if env:
        return env
    code, out = runner(["git", "remote", "get-url", "origin"], cwd=cwd)
    if code != 0:
        raise RuntimeError("non riesco a leggere l'URL di origin")
    url = out.strip().split()[0] if out.strip() else ""
    path = url.rsplit(":", 1)[-1] if url.startswith("git@") else url
    parts = [p for p in path.replace("\\", "/").split("/") if p]
    if len(parts) < 2:
        raise RuntimeError(f"non riesco a ricavare owner/repo da '{url}'")
    owner, repo = parts[-2], parts[-1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return f"{owner}/{repo}"


def api(path, runner=_run, cwd=None, method=None, fields=()):
    """Una chiamata REST via `gh api`. Ritorna (ok, dato-decodificato-o-testo)."""
    argv = ["gh", "api"]
    if method:
        argv += ["--method", method]
    argv.append(path)
    for key, value in fields:
        argv += ["-f", f"{key}={value}"]
    code, out = runner(argv, cwd=cwd)
    text = (out or "").strip()
    if code != 0:
        return False, text
    if not text or text.lstrip()[:1] not in "[{":
        return True, text
    try:
        return True, json.loads(text)
    except json.JSONDecodeError:
        return False, text


def head_sha(pr, runner=_run, cwd=None, slug=None):
    """Il commit in cima alla PR, che e' quello su cui girano i check."""
    slug = slug or repo_slug(runner=runner, cwd=cwd)
    ok, data = api(f"repos/{slug}/pulls/{pr}", runner=runner, cwd=cwd)
    if not ok or not isinstance(data, dict):
        return ""
    return ((data.get("head") or {}).get("sha") or "")


def check_states(pr, runner=_run, cwd=None, slug=None):
    """The state of every check on a pull request, as {name: bucket}.

    Due endpoint e non uno: le check run moderne e le commit status storiche
    vivono separate, e un repo puo' avere le une, le altre o entrambe. Le prime
    vincono su un nome in comune, che e' il caso raro in cui lo stesso servizio
    scrive in tutti e due i posti.

    Un dizionario vuoto vuol dire "non risulta niente", e resta uno stato
    transitorio legittimo subito dopo il push: quanto insistere lo decide chi
    chiama. Vale anche quando la chiamata fallisce, come valeva prima quando
    `gh pr checks` usciva non-zero.
    """
    slug = slug or repo_slug(runner=runner, cwd=cwd)
    sha = head_sha(pr, runner=runner, cwd=cwd, slug=slug)
    if not sha:
        return {}
    states = {}
    ok, data = api(f"repos/{slug}/commits/{sha}/status?per_page=100",
                   runner=runner, cwd=cwd)
    if ok and isinstance(data, dict):
        for row in data.get("statuses") or []:
            name = row.get("context") or "?"
            states[name] = _STATE_BUCKET.get(row.get("state") or "", "pending")
    ok, data = api(f"repos/{slug}/commits/{sha}/check-runs?per_page=100",
                   runner=runner, cwd=cwd)
    if ok and isinstance(data, dict):
        for row in data.get("check_runs") or []:
            states[row.get("name") or "?"] = _bucket(row)
    return states


def wait_for_checks(pr, runner=_run, cwd=None, sleep=time.sleep,
                    timeout=CHECKS_TIMEOUT, appear_timeout=CHECKS_APPEAR_TIMEOUT,
                    log=print, slug=None):
    """Poll until every check has concluded. Returns (ok, detail).

    Three ways out, and each one has to be distinguishable by the caller, because
    "the checks failed" and "the checks never showed up" want opposite fixes.
    """
    waited = 0
    while True:
        states = check_states(pr, runner=runner, cwd=cwd, slug=slug)
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


def merge(pr, runner=_run, cwd=None, slug=None, log=print):
    """Squash merge via REST, poi cancella il branch. Ritorna (ok, dettaglio).

    L'ordine conta e la separazione anche: fondere e cancellare erano un flag
    solo (`--delete-branch`), qui sono due chiamate, e la seconda non puo'
    disfare la prima. Se la cancellazione fallisce il merge resta fatto, quindi
    si dice e si va avanti: restituire un fallimento manderebbe a master una riga
    di diario che dice `error` su una PR che si e' fusa davvero, che e' il tipo
    di bugia che questo script esiste per non raccontare.
    """
    slug = slug or repo_slug(runner=runner, cwd=cwd)
    branch = ""
    ok, data = api(f"repos/{slug}/pulls/{pr}", runner=runner, cwd=cwd)
    if ok and isinstance(data, dict):
        branch = ((data.get("head") or {}).get("ref") or "")

    ok, data = api(f"repos/{slug}/pulls/{pr}/merge", runner=runner, cwd=cwd,
                   method="PUT", fields=[("merge_method", "squash")])
    if not ok:
        return False, str(data)[:400]
    if isinstance(data, dict) and not data.get("merged", True):
        return False, str(data.get("message") or data)[:400]
    detail = (data.get("message") if isinstance(data, dict) else None) or "merged"

    if branch:
        gone, out = api(f"repos/{slug}/git/refs/heads/{branch}", runner=runner,
                        cwd=cwd, method="DELETE")
        if not gone:
            log(f"  branch '{branch}' non cancellato: {str(out)[:120]}")
    return True, detail


def record_landing(stage, pr, result, runner=_run, cwd=None, log=print, attempts=3,
                   run_id=None):
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
    porta la riga dell'altro, e la nostra le va dietro.

    Il ritentativo adesso e' anche piu' raro. Con un file per run le due righe
    non finiscono nello stesso file, quindi due passi di merge concorrenti non
    si contendono niente e il push perde la corsa solo per il normale
    non-fast-forward, non per un conflitto di contenuto.

    Il `run_id` arriva da chi ha aperto la pull request, ed e' l'unica cosa che
    lega questa riga alla riga dell'agente: quando l'agente ha scritto la sua,
    il numero della pull request non esisteva ancora, quindi appaiarle su
    quello non funzionava e per meta' delle run non funzionava affatto.
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
                run_id=run_id, trigger=result.get("trigger"),
            )
            # `.esito` e non un nome nuovo: le due meta' della run condividono
            # il `run_id`, e il suffisso e' cio' che permette loro di stare in
            # due file senza contendersi un percorso.
            pipeline_log.append(
                entry, path=Path(tmp) / "data" / "pipeline" / "runs", suffix=".esito"
            )
            runner(["git", "add", "data/pipeline/runs"], cwd=tmp)
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
        f"--outcome {outcome} --pr {pr}"
        + (f" --run-id {run_id}" if run_id else ""))
    return False


def decide(stage, pr, verdict=None, runner=_run, cwd=None, sleep=time.sleep,
           dry_run=False, log=print, skip_tests=False, journal=True, run_id=None):
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
            record_landing(stage, pr, result, runner=runner, cwd=cwd, log=log,
                           run_id=run_id)
        return result

    if mode == "blocked":
        failed = [c["check"] for c in verdict["checks"] if not c["ok"]]
        detail = "il cancello e' rosso: " + ", ".join(failed)
        log(f"  RIFIUTO. {detail}")
        return finish({"merged": False, "outcome": "blocked", "gate": mode, "detail": detail})

    # Dopo il ramo `blocked`, non prima: un cancello rosso non parla con GitHub,
    # e non deve fallire perche' non si capisce da dove viene il remote.
    slug = repo_slug(runner=runner, cwd=cwd)

    if mode == "checks":
        ok, detail = wait_for_checks(pr, runner=runner, cwd=cwd, sleep=sleep,
                                     log=log, slug=slug)
        if not ok:
            log(f"  RIFIUTO. {detail}")
            return finish({"merged": False, "outcome": "stopped", "gate": mode, "detail": detail})
        log(f"  {detail}")

    if dry_run:
        log("  --dry-run: mi fermo qui, la PR resta aperta.")
        return {"merged": False, "outcome": "pr-open", "gate": mode, "detail": "dry run"}

    ok, out = merge(pr, runner=runner, cwd=cwd, slug=slug, log=log)
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
    parser.add_argument("--run-id",
                        help="l'identita' della run, quella che pipeline_log ha stampato. "
                             "Senza, la riga di esito resta orfana e il diario non sa "
                             "a quale run appartiene")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = decide(args.stage, args.pr, dry_run=args.dry_run, skip_tests=args.skip_tests,
                    journal=not args.no_journal, run_id=args.run_id)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["merged"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
