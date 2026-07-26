#!/usr/bin/env python3
"""The gate: the deterministic verdict that lets a stage publish without a human.

The chain is autonomous, which only works if "autonomous" cannot mean
"autonomously wrong at scale". Every agent stage ends here: it hands the gate
its branch, and the gate answers with a merge verdict computed from the diff and
from the test suite, never from the agent's own opinion of its work.

What it checks, in order of how much damage the failure would do:

1. **Blast radius.** Each stage may touch a fixed, short list of paths. The
   writer may write prose and nothing else; the hunter may write the queue and
   nothing else. An agent that edits `app/views.py` while claiming to be the
   writer fails here, before anyone reads a word of its reasoning. This is the
   single check that makes the rest safe to automate: a stage cannot widen its
   own scope, because the list lives in the repo, not in the prompt.
2. **The suite.** All of it, not the stage's favourite subset. The guards on
   prose, vintage drift, figures attributed to a region, the CSV schema and
   `/legacy` are the accumulated memory of everything that has gone wrong here,
   and a stage that breaks any of them has not finished its job.
3. **Stage invariants the suite cannot see**, because they are about the *diff*
   rather than the state: a triage decision with no written reason, a
   `score_eligible=true` on a verso that is not directional, a reviewed article
   that never got its `reviewed_at`.
4. **Repo hygiene**: whitespace, and the `Co-Authored-By` trailer CLAUDE.md bans.

The verdict carries a merge mode, and the modes are deliberately not uniform
(see MERGE_POLICY). Prose is reversible and reaches no other page. A curation
decision moves the quality-of-life score. A new source puts an institution's
name and licence on a public page. Those are different risks and they get
different answers.

Pure stdlib, like the rest of the chain, so it runs in a cloud agent that has no
venv yet.

    python3 scripts/pipeline_gate.py --stage writer
    python3 scripts/pipeline_gate.py --stage curator --base origin/master --json
    python3 scripts/pipeline_gate.py --stage writer --skip-tests   # triage only
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import curate, discovery  # noqa: E402  (path bootstrap above)

EXTERNAL_DATASET = "app/static/data/external/normalized_external_indicators.csv"
EXTERNAL_MANIFEST = "app/static/data/external_indicator_manifest.csv"
CURATED_DESCRIPTIONS = "app/static/data/external/curated_descriptions.csv"
INDICATOR_TEXTS = "app/static/data/indicator_texts.json"
CANDIDATES = "data/discovery/candidates.csv"
SOURCE_CANDIDATES = "data/discovery/source_candidates.csv"
CURATION = "data/discovery/curation.csv"
ISTAT_SERIES_CONFIG = "config/istat_series.yaml"
THEME_CATEGORIES = "config/theme_categories.csv"

# What each stage is allowed to change. Anything outside its list is a failure,
# not a warning: the point of the list is that a prompt cannot widen it.
STAGE_PATHS = {
    "scout": (SOURCE_CANDIDATES, ISTAT_SERIES_CONFIG),
    "hunter": (CANDIDATES,),
    "promoter": (CANDIDATES, EXTERNAL_DATASET, EXTERNAL_MANIFEST),
    # The curator gets the theme map because a promoted indicator brings a theme
    # name with it, and an unmapped theme drops it out of every macro-area total
    # silently. That fix used to live in `app/taxonomy.py`, which no agent may
    # touch, so it would have stalled the chain on a legitimate case.
    "curator": (CURATION, EXTERNAL_DATASET, EXTERNAL_MANIFEST, CURATED_DESCRIPTIONS, THEME_CATEGORIES),
    "writer": (INDICATOR_TEXTS,),
    "reviewer": (INDICATOR_TEXTS,),
}

# How far a green gate is allowed to go, per stage. Not uniform on purpose.
#
#   auto     merge now. The change is prose in one file, it reaches no other
#            page, and reverting it is one commit.
#   checks   merge when the remote checks pass (`gh pr merge --auto`). The
#            change moves live numbers (the quality-of-life score, the atlas
#            catalogue), so it goes through CI and leaves a window in which a
#            human can still step in.
#   manual   never merged by an agent. Admitting a source decides which
#            institution, licence and name a reader sees on a public page, and
#            that is the one decision the chain does not take by itself.
MERGE_POLICY = {
    "scout": "manual",
    "hunter": "checks",
    "promoter": "checks",
    "curator": "checks",
    "writer": "auto",
    "reviewer": "auto",
}

# Borrowed, not restated. A local copy drifted from `curate.SCOREABLE_DIRECTIONS`
# the moment it was written: it left out `higher_worse`, which is a perfectly
# scoreable verso, so the gate would have blocked correct curation work.
DIRECTIONAL = curate.SCOREABLE_DIRECTIONS

# The floor under an autonomous approval. Below this a series cannot support the
# comparisons the atlas makes of it: the pages, the ranking and the quality-of-life
# score all read across the twenty regions, and a series that covers twelve of
# them produces a national reading built on a hole. Deliberately the same
# threshold the adapters use to pick their "honest recent year".
MIN_APPROVAL_COVERAGE = 0.8


class Check:
    """One verdict line. `ok` decides the exit code, `detail` explains it."""

    def __init__(self, name, ok, detail=""):
        self.name = name
        self.ok = bool(ok)
        self.detail = detail

    def as_dict(self):
        return {"check": self.name, "ok": self.ok, "detail": self.detail}


def _git(*args, cwd=None):
    result = subprocess.run(
        ("git",) + args,
        cwd=str(cwd or PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def resolve_base(base=None, cwd=None):
    """The commit the branch is measured against.

    Tries the caller's value, then `origin/master`, then `master`. A cloud agent
    works on a fresh checkout where `origin/master` exists; a local worktree may
    only have `master`. Returning None means "no base": the caller falls back to
    the working tree, which is what a local dry run wants.
    """
    for candidate in (base, "origin/master", "master"):
        if not candidate:
            continue
        code, _, _ = _git("rev-parse", "--verify", "--quiet", candidate, cwd=cwd)
        if code == 0:
            return candidate
    return None


def changed_paths(base=None, cwd=None):
    """Repo-relative paths this branch touches, committed and uncommitted.

    Both halves matter. A cloud agent commits before opening its PR, so the diff
    against the base is the real answer. A local run may still have the change
    in the working tree, and a gate that only looked at commits would call that
    branch clean and green.
    """
    paths = set()
    resolved = resolve_base(base, cwd=cwd)
    if resolved:
        code, out, _ = _git("diff", "--name-only", f"{resolved}...HEAD", cwd=cwd)
        if code == 0:
            paths.update(line.strip() for line in out.splitlines() if line.strip())
    code, out, _ = _git("status", "--porcelain", cwd=cwd)
    if code == 0:
        for line in out.splitlines():
            entry = line[3:].strip()
            if not entry:
                continue
            # Renames arrive as "old -> new"; the destination is what changed.
            paths.add(entry.split(" -> ")[-1].strip())
    return sorted(p for p in paths if p)


def check_blast_radius(stage, paths):
    allowed = STAGE_PATHS[stage]
    stray = [p for p in paths if p not in allowed]
    if stray:
        return Check(
            "blast-radius",
            False,
            f"lo stadio '{stage}' puo' toccare solo {', '.join(allowed)}. Fuori perimetro: {', '.join(stray)}",
        )
    if not paths:
        return Check("blast-radius", True, "nessun file modificato")
    return Check("blast-radius", True, f"{len(paths)} file, tutti nel perimetro dello stadio")


def check_whitespace(cwd=None):
    code, out, _ = _git("diff", "--check", cwd=cwd)
    if code != 0 or out.strip():
        return Check("whitespace", False, out.strip()[:400] or "git diff --check ha segnalato errori")
    return Check("whitespace", True, "git diff --check pulito")


def check_no_coauthor_trailer(base=None, cwd=None):
    """CLAUDE.md bans the trailer, and an agent that adds it has stopped reading
    the repo rules, which is worth catching on the cheapest possible signal."""
    resolved = resolve_base(base, cwd=cwd)
    if not resolved:
        return Check("no-coauthor", True, "nessuna base di confronto, controllo saltato")
    code, out, _ = _git("log", "--format=%B", f"{resolved}..HEAD", cwd=cwd)
    if code != 0:
        return Check("no-coauthor", True, "nessun commit da controllare")
    if "Co-Authored-By" in out or "Co-authored-by" in out:
        return Check("no-coauthor", False, "un messaggio di commit porta il trailer Co-Authored-By, vietato da CLAUDE.md")
    return Check("no-coauthor", True, "nessun trailer Co-Authored-By")


def _read_csv(path):
    full = PROJECT_ROOT / path
    if not full.exists():
        return []
    return discovery.read_semicolon(full)


def check_hunter_decisions(rows=None):
    """A triage decision with no written reason is not a decision, it is a
    coin toss with a CSV column. The chain has to be able to explain, months
    later, why a candidate was let in, and the only place that survives is the
    queue itself."""
    rows = rows if rows is not None else _read_csv(CANDIDATES)
    if not rows:
        return Check("triage-motivato", True, "coda vuota")
    silent = [
        row.get("candidate_id", "?")
        for row in rows
        if (row.get("triage_status") or "new") not in ("new", "promoted")
        and not (row.get("triage_notes") or "").strip()
    ]
    if silent:
        return Check("triage-motivato", False, f"decisioni senza motivazione scritta: {', '.join(silent[:5])}")
    claimed_exact = [
        row.get("candidate_id", "?") for row in rows if row.get("definition_match") == "exact"
    ]
    if claimed_exact:
        return Check(
            "triage-motivato",
            False,
            f"definition_match=exact non e' mai automatico: {', '.join(claimed_exact[:5])}",
        )
    # Hard floor under an approval. The hunter approves on its own now, so the
    # things that make an indicator unusable have to be refusable without
    # reading its reasoning: a series that covers half the regions cannot carry
    # a national comparison, and one with no licence cannot be published at all.
    unusable = []
    for row in rows:
        if row.get("triage_status") != "approved":
            continue
        try:
            coverage = float(row.get("coverage") or 0)
        except ValueError:
            coverage = 0.0
        if coverage < MIN_APPROVAL_COVERAGE:
            unusable.append(f"{row.get('candidate_id', '?')} (copertura {coverage:.2f})")
        elif not (row.get("license") or "").strip():
            unusable.append(f"{row.get('candidate_id', '?')} (licenza assente)")
    if unusable:
        return Check(
            "triage-motivato",
            False,
            f"approvazioni che non reggono i minimi: {', '.join(unusable[:5])}",
        )
    return Check("triage-motivato", True, f"{len(rows)} candidati, ogni decisione ha una motivazione")


def check_curation_decisions(rows=None):
    """`score_eligible=true` on a verso that is not directional would put an
    indicator with no "better" into the quality-of-life score, where every value
    is oriented. apply_curation refuses it too, but the gate says so before the
    PR exists rather than after."""
    rows = rows if rows is not None else _read_csv(CURATION)
    if not rows:
        return Check("curatela-direzionale", True, "nessuna decisione di curatela")
    bad = [
        row.get("target_indicator_id", "?")
        for row in rows
        if (row.get("score_eligible") or "").strip().lower() == "true"
        and (row.get("reviewed_direction") or "").strip() not in DIRECTIONAL
    ]
    if bad:
        return Check(
            "curatela-direzionale",
            False,
            f"score_eligible=true con verso non direzionale: {', '.join(bad[:5])}",
        )
    undated = [
        row.get("target_indicator_id", "?")
        for row in rows
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", (row.get("reviewed_at") or "").strip())
    ]
    if undated:
        return Check(
            "curatela-direzionale",
            False,
            f"decisioni senza reviewed_at in formato YYYY-MM-DD: {', '.join(undated[:5])}",
        )
    return Check("curatela-direzionale", True, f"{len(rows)} decisioni, versi e date coerenti")


def check_reviewer_signature(base=None, cwd=None):
    """The reviewer's whole output is a signature, so a run that changed prose
    without signing anything has not reviewed, it has rewritten."""
    resolved = resolve_base(base, cwd=cwd)
    if not resolved:
        return Check("firma-revisore", True, "nessuna base di confronto, controllo saltato")
    code, out, _ = _git("diff", f"{resolved}...HEAD", "--", INDICATOR_TEXTS, cwd=cwd)
    if code != 0 or not out.strip():
        code, out, _ = _git("diff", "--", INDICATOR_TEXTS, cwd=cwd)
    if not out.strip():
        return Check("firma-revisore", True, "nessuna modifica ai testi")
    signed = [line for line in out.splitlines() if line.startswith("+") and '"reviewed_at"' in line]
    if not signed:
        return Check(
            "firma-revisore",
            False,
            "il revisore ha cambiato la prosa senza aggiungere nessun reviewed_at",
        )
    return Check("firma-revisore", True, f"{len(signed)} articoli firmati")


def changed_text_keys(base=None, cwd=None):
    """The article ids this branch actually touched.

    Read by comparing the two versions of the file rather than by parsing the
    diff hunks: a JSON diff shows the changed *lines*, and the id that owns them
    can be a hundred lines above. Comparing parsed objects gives the ids
    directly and costs one `git show`.
    """
    current_path = PROJECT_ROOT / INDICATOR_TEXTS
    if not current_path.exists():
        return []
    try:
        new = json.loads(current_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    resolved = resolve_base(base, cwd=cwd)
    if not resolved:
        return []
    code, out, _ = _git("show", f"{resolved}:{INDICATOR_TEXTS}", cwd=cwd)
    if code != 0:
        return sorted(new)
    try:
        old = json.loads(out)
    except json.JSONDecodeError:
        return sorted(new)
    return sorted(key for key in new if new[key] != old.get(key))


def check_writer_vintage(base=None, cwd=None):
    """The writer's contract is `vintage == year_max`, stricter than the drift
    guard in the suite, which only fails when the vintage falls *behind*. A
    vintage ahead of the data is prose written against numbers that do not exist
    yet, and nothing would ever flag it: the drift guard is looking the other
    way, and a reader has no way to tell.

    Scoped to the ids the branch touched. The suite already walks all of them
    for staleness, and rebuilding 362 view models to re-check work nobody edited
    would make the gate the slowest step in an autonomous chain.
    """
    keys = changed_text_keys(base, cwd=cwd)
    if not keys:
        return Check("vintage", True, "nessun articolo modificato")
    try:
        from app import sources  # noqa: PLC0415  (optional: needs the app venv)
        from app.indicator_view import build_indicator_view
    except Exception as exc:  # pragma: no cover - only without the venv
        return Check("vintage", True, f"controllo saltato, l'app non e' importabile ({type(exc).__name__})")
    entries = json.loads((PROJECT_ROOT / INDICATOR_TEXTS).read_text(encoding="utf-8"))
    ahead = []
    for key in keys:
        entry = entries.get(key) or {}
        vintage = entry.get("vintage")
        if not isinstance(vintage, int):
            continue
        try:
            family, raw_id = sources.split_internal_id(key)
            view = build_indicator_view(family, raw_id)
        except Exception:
            continue
        if view is None:
            continue
        wanted = entry.get("level") or "regione"
        level = next((lv for lv in view["levels"] if lv["key"] == wanted), None)
        if level and isinstance(level.get("year_max"), int) and vintage > level["year_max"]:
            ahead.append(f"{key} ({vintage} > {level['year_max']})")
    if ahead:
        return Check("vintage", False, f"vintage oltre i dati: {', '.join(ahead[:5])}")
    return Check("vintage", True, f"{len(keys)} articoli toccati, nessun vintage oltre i dati")


def _python():
    venv = PROJECT_ROOT / ".venv" / "bin" / "python"
    return str(venv) if venv.exists() else sys.executable


def check_suite(cwd=None):
    result = subprocess.run(
        [_python(), "-m", "unittest", "discover", "-s", "tests"],
        cwd=str(cwd or PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    tail = (result.stderr or result.stdout).strip().splitlines()
    summary = " / ".join(line for line in tail[-3:] if line.strip())
    if result.returncode != 0:
        return Check("suite", False, f"la suite fallisce: {summary[:500]}")
    return Check("suite", True, summary[:200] or "suite verde")


def build_verdict(stage, paths, checks):
    """Assemble the answer. Separate from `run` so the policy can be tested
    without a git tree, which is the only way to assert that a red gate really
    does refuse to name a merge mode."""
    ok = all(check.ok for check in checks)
    return {
        "stage": stage,
        "ok": ok,
        # A red gate has no merge mode at all: there is nothing to argue about
        # between "the checks failed" and "but only a little".
        "merge": MERGE_POLICY[stage] if ok else "blocked",
        "paths": list(paths),
        "checks": [check.as_dict() for check in checks],
    }


def run(stage, base=None, skip_tests=False, cwd=None):
    """Every check for one stage, in the order a failure should be read."""
    if stage not in STAGE_PATHS:
        raise SystemExit(f"stadio sconosciuto '{stage}'. Noti: {', '.join(sorted(STAGE_PATHS))}")
    paths = changed_paths(base, cwd=cwd)
    checks = [
        check_blast_radius(stage, paths),
        check_whitespace(cwd=cwd),
        check_no_coauthor_trailer(base, cwd=cwd),
    ]
    if stage in ("hunter", "promoter"):
        checks.append(check_hunter_decisions())
    if stage == "curator":
        checks.append(check_curation_decisions())
    if stage == "reviewer":
        checks.append(check_reviewer_signature(base, cwd=cwd))
    if stage in ("writer", "reviewer"):
        checks.append(check_writer_vintage(base, cwd=cwd))
    if not skip_tests:
        checks.append(check_suite(cwd=cwd))
    return build_verdict(stage, paths, checks)


def main():
    parser = argparse.ArgumentParser(
        description="Il cancello: dice se lo stadio puo' pubblicare da solo.",
        epilog="uscita 0 = verde, 1 = bloccato.",
    )
    parser.add_argument("--stage", required=True, choices=sorted(STAGE_PATHS))
    parser.add_argument("--base", help="commit di confronto (default: origin/master, poi master)")
    parser.add_argument("--skip-tests", action="store_true", help="salta la suite (solo per un triage rapido)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    verdict = run(args.stage, args.base, skip_tests=args.skip_tests)
    if args.json:
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
    else:
        print(f"stadio {verdict['stage']}: {'VERDE' if verdict['ok'] else 'BLOCCATO'}  (merge: {verdict['merge']})")
        for check in verdict["checks"]:
            print(f"  [{'ok ' if check['ok'] else 'NO '}] {check['check']}: {check['detail']}")
        if verdict["paths"]:
            print("  file toccati: " + ", ".join(verdict["paths"]))
    return 0 if verdict["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
