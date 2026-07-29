#!/usr/bin/env python3
"""La fotografia delle PR aperte della catena, per il cruscotto /_pipeline.

Il cruscotto mostrava solo lo stato committato su master, quindi niente finche'
una PR non era fusa. Questo script chiude l'altra meta' del buco: elenca le PR
aperte su `automation/*`, con il loro `run_id`, lo stato dei check e la
mergeabilita', e le manda all'endpoint del sito (lo stesso vivo dei battiti).
Cosi' il cruscotto distingue "un ruolo sta lavorando" da "c'e' una PR aperta con
la CI rossa" da "c'e' una PR pronta che aspetta il merge".

Lo esegue il **lanciatore** a ogni tick: e' l'unico punto della catena che parla
gia' con GitHub, quindi la sola chiamata a GitHub sta qui, non sul sito (che non
ha un token e non deve averne). Riusa la superficie REST di `pipeline_merge`
(`repo_slug`, `api`, `check_states`), la stessa che regge il merge dietro il proxy.

    python3 scripts/pipeline_inflight.py --json     # stampa la fotografia
    python3 scripts/pipeline_inflight.py --post     # la manda al sito (via /_pipeline/beat)

Stdlib puro. Il `runner` e' iniettabile, cosi' un test prova la classificazione
senza rete.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import pipeline_merge, pipeline_monitor  # noqa: E402

AUTOMATION_PREFIX = "automation/"

# I bucket dei check, gia' la lingua di pipeline_merge, riassunti in una parola
# per il cruscotto: se anche uno e' rosso la PR e' rossa, se nessuno e' rosso ma
# qualcuno gira e' in corsa, se sono tutti verdi e' verde, se non ne risulta
# nessuno e' "nessuna" (una PR aperta via il MCP su cui la CI non parte).
def _ci_word(states: dict) -> str:
    if not states:
        return "nessuna"
    buckets = set(states.values())
    if buckets & {"fail"}:
        return "rossa"
    if buckets & {"pending"}:
        return "in-corsa"
    return "verde"


def _role_of_branch(branch: str) -> str:
    """Il ruolo dal nome del branch `automation/<ruolo>-<data>-<suffisso>`."""
    tail = branch[len(AUTOMATION_PREFIX):] if branch.startswith(AUTOMATION_PREFIX) else branch
    return tail.split("-", 1)[0] if tail else ""


def _run_id_of(pr: dict) -> str:
    """Il run_id di una PR: dal corpo se lo dichiara, altrimenti dal branch.

    L'agente puo' scriverlo nel corpo (`run_id: <...>`); in mancanza, il suffisso
    del branch lo identifica comunque in modo univoco."""
    import re
    body = pr.get("body") or ""
    m = re.search(r"run[_-]?id[:\s]+([A-Za-z0-9:_-]+)", body)
    if m:
        return m.group(1)
    branch = ((pr.get("head") or {}).get("ref") or "")
    return branch[len(AUTOMATION_PREFIX):] if branch.startswith(AUTOMATION_PREFIX) else ""


def _mergeable_word(pr: dict) -> str:
    m = pr.get("mergeable")
    return {True: "si", False: "no"}.get(m, "?")


def build_snapshot(pulls, checks_by_pr) -> list:
    """Le PR aperte su `automation/*`, gia' interpretate per il cruscotto. Pura.

    `pulls` sono i dict REST delle PR aperte; `checks_by_pr` mappa numero PR ->
    `check_states` gia' letto. Ignora le PR fuori da `automation/*`: non sono
    della catena."""
    snapshot = []
    for pr in pulls:
        branch = ((pr.get("head") or {}).get("ref") or "")
        if not branch.startswith(AUTOMATION_PREFIX):
            continue
        number = pr.get("number")
        snapshot.append({
            "pr": number,
            "branch": branch,
            "run_id": _run_id_of(pr),
            "role": _role_of_branch(branch),
            "title": pr.get("title", ""),
            "ci": _ci_word(checks_by_pr.get(number, {})),
            "mergeable": _mergeable_word(pr),
        })
    return snapshot


def open_runs(runner=pipeline_merge._run, cwd=None, slug=None) -> list:
    """Legge da GitHub le PR aperte e ne costruisce la fotografia (I/O + puro)."""
    slug = slug or pipeline_merge.repo_slug(runner=runner, cwd=cwd)
    ok, data = pipeline_merge.api(
        f"repos/{slug}/pulls?state=open&per_page=100", runner=runner, cwd=cwd)
    pulls = data if (ok and isinstance(data, list)) else []
    checks_by_pr = {}
    for pr in pulls:
        branch = ((pr.get("head") or {}).get("ref") or "")
        number = pr.get("number")
        if branch.startswith(AUTOMATION_PREFIX) and number is not None:
            checks_by_pr[number] = pipeline_merge.check_states(
                number, runner=runner, cwd=cwd, slug=slug)
    return build_snapshot(pulls, checks_by_pr)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="La fotografia delle PR aperte della catena, per /_pipeline.")
    parser.add_argument("--json", action="store_true", help="stampa la fotografia")
    parser.add_argument("--post", action="store_true",
                        help="manda la fotografia al sito (PIPELINE_INGEST_URL/TOKEN)")
    args = parser.parse_args(argv)

    snapshot = open_runs()
    if args.post:
        sent = pipeline_monitor.post_beat({"action": "prs", "prs": snapshot})
        if not args.json:
            print(f"{len(snapshot)} PR aperte"
                  + (" inviate al sito" if sent else " (non inviate: manca URL/segreto)"))
    if args.json or not args.post:
        import json
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
