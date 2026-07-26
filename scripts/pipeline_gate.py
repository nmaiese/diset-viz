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
# Il diario delle run. Ogni stadio ci scrive una riga a fine run, quindi sta
# nel perimetro di tutti: senza, meta' delle run (quelle che non producono
# altro) non lascerebbe nessuna traccia, che e' esattamente il buco che il
# diario esiste per chiudere.
RUN_JOURNAL = "data/pipeline/runs.jsonl"

# What each stage is allowed to change. Anything outside its list is a failure,
# not a warning: the point of the list is that a prompt cannot widen it.
STAGE_PATHS = {
    "scout": (SOURCE_CANDIDATES, ISTAT_SERIES_CONFIG, RUN_JOURNAL),
    "hunter": (CANDIDATES, RUN_JOURNAL),
    "promoter": (CANDIDATES, EXTERNAL_DATASET, EXTERNAL_MANIFEST, RUN_JOURNAL),
    # The curator gets the theme map because a promoted indicator brings a theme
    # name with it, and an unmapped theme drops it out of every macro-area total
    # silently. That fix used to live in `app/taxonomy.py`, which no agent may
    # touch, so it would have stalled the chain on a legitimate case.
    "curator": (CURATION, EXTERNAL_DATASET, EXTERNAL_MANIFEST, CURATED_DESCRIPTIONS,
                THEME_CATEGORIES, RUN_JOURNAL),
    "writer": (INDICATOR_TEXTS, RUN_JOURNAL),
    "reviewer": (INDICATOR_TEXTS, RUN_JOURNAL),
}

# How far a green gate is allowed to go, per stage. Not uniform on purpose.
#
#   auto     merge now. The change is prose in one file, it reaches no other
#            page, and reverting it is one commit.
#   checks   merge only once the remote checks have concluded green. The change
#            moves live numbers (the quality-of-life score, the atlas catalogue,
#            which institution a page names), so CI is what stands between the
#            agent's judgment and the site.
#   manual   never merged by an agent. No stage uses this today: the chain is
#            unattended by decision, and a mode that parks a pull request until
#            somebody looks is a mode that parks it forever. Kept as a word the
#            gate can still say, because a future stage may earn it.
#
# The wait for `checks` lives in `scripts/pipeline_merge.py`, not in a `gh` flag.
# `gh pr merge --auto` does NOT wait on this repository: with `allow_auto_merge`
# false and `master` unprotected it falls back to merging immediately, and a
# probe pull request proved it by merging with the test job still running.
MERGE_POLICY = {
    "scout": "checks",
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


def check_base_is_usable(base=None, cwd=None):
    """The base has to be an ancestor of HEAD, or every verdict below is fiction.

    `resolve_base` falls through `base` -> `origin/master` -> `master`, and a
    fresh checkout can have a `master` that trails `origin/master`. When that
    happens the diff contains every commit the branch did *not* make, the
    perimeter check lists thirty untouched files as violations, and the stage
    reads `blocked`. Its contract then tells it "the error is in your work, never
    in the gate", which leaves an autonomous agent with no way out of a wrong
    diagnosis: it will keep rewriting correct work.

    So a base that cannot explain the diff is a failure of the gate, reported as
    one, rather than a silent mismeasurement of the branch.
    """
    resolved = resolve_base(base, cwd=cwd)
    if not resolved:
        return Check("base", True, "nessuna base di confronto, giudizio sul solo working tree")
    code, _, _ = _git("merge-base", "--is-ancestor", resolved, "HEAD", cwd=cwd)
    if code != 0:
        return Check(
            "base",
            False,
            f"la base '{resolved}' non e' un antenato di HEAD: il diff misurato non e' il lavoro "
            f"di questo branch. Aggiorna la base (git fetch) o passala con --base, e NON correggere "
            f"il lavoro sulla scorta di questo verdetto.",
        )
    return Check("base", True, f"confronto contro {resolved}")


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
    without signing has not reviewed, it has rewritten.

    Checks the **state** of the articles it touched, not the lines of the diff.
    The first version looked for an added line containing `"reviewed_at"`, which
    is a proxy that fails on a real and correct case: a same-day correction to an
    article already signed today rewrites nothing, because the right signature is
    the one already there. The reviewer agent hit exactly that, refused to fake a
    date to get past the gate, refused to edit the gate, and escalated it with
    the fix. A gate that pushes a correct agent toward a false date is worse than
    no gate.

    Reading the state is also strictly stronger: a diff line proves a string was
    added, this proves every article the run touched carries a valid signature
    that matches the data it describes.
    """
    keys = changed_text_keys(base, cwd=cwd)
    if not keys:
        return Check("firma-revisore", True, "nessuna modifica ai testi")
    current = PROJECT_ROOT / INDICATOR_TEXTS
    try:
        entries = json.loads(current.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return Check("firma-revisore", False, f"testi illeggibili: {type(exc).__name__}")
    unsigned, mismatched = [], []
    for key in keys:
        entry = entries.get(key) or {}
        signed = (entry.get("reviewed_at") or "").strip()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", signed):
            unsigned.append(key)
        elif entry.get("reviewed_vintage") != entry.get("vintage"):
            # A signature that does not match the article's own vintage is one
            # the re-entry rule will reopen anyway, so accepting it here would
            # only hide the problem for one run.
            mismatched.append(f"{key} (firmato sul {entry.get('reviewed_vintage')}, ora {entry.get('vintage')})")
    if unsigned:
        return Check(
            "firma-revisore",
            False,
            f"articoli cambiati senza una firma valida: {', '.join(unsigned[:5])}",
        )
    if mismatched:
        return Check(
            "firma-revisore",
            False,
            f"firme che non corrispondono al vintage: {', '.join(mismatched[:5])}",
        )
    return Check("firma-revisore", True, f"{len(keys)} articoli toccati, tutti firmati e coerenti")


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


def check_run_is_recorded(stage, paths, base=None, cwd=None):
    """Una run che ha prodotto qualcosa deve dire di averlo fatto.

    Imposto qui invece che ricordato nel prompt, per la stessa ragione per cui
    il perimetro sta nel repo: un promemoria si puo' saltare, soprattutto
    all'ultimo passo di una run lunga, ed e' proprio la riga di diario che
    trasforma la catena in una cosa osservabile. Senza, l'unica traccia di un
    agente resta il commit, e le run che non ne producono restano invisibili.

    Vincola solo le run che hanno toccato altro. Una run a mani vuote non passa
    di qui, perche' non ha un branch da giudicare: la sua riga di diario resta
    affidata al contratto.
    """
    worked = [p for p in paths if p != RUN_JOURNAL]
    if not worked:
        return Check("diario", True, "nessun lavoro da registrare")
    if RUN_JOURNAL not in paths:
        return Check(
            "diario",
            False,
            f"la run ha toccato {len(worked)} file ma non ha registrato niente in {RUN_JOURNAL}. "
            f"Aggiungi la riga con: python3 scripts/pipeline_log.py --write --stage {stage} "
            f"--outcome <esito> --summary \"...\"",
        )
    added = _journal_lines_added(base, cwd=cwd)
    mine = [entry for entry in added if entry.get("stage") == stage]
    if not mine:
        return Check(
            "diario",
            False,
            f"il diario e' cambiato ma nessuna riga nuova e' dello stadio '{stage}'",
        )
    return Check("diario", True, f"{len(mine)} run registrate come '{stage}'")


def _journal_lines_added(base=None, cwd=None):
    """Le righe di diario che questo branch aggiunge, gia' interpretate."""
    resolved = resolve_base(base, cwd=cwd)
    old = set()
    if resolved:
        code, out, _ = _git("show", f"{resolved}:{RUN_JOURNAL}", cwd=cwd)
        if code == 0:
            old = {line for line in out.splitlines() if line.strip()}
    current = PROJECT_ROOT / RUN_JOURNAL
    if not current.exists():
        return []
    added = []
    for line in current.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line in old:
            continue
        try:
            added.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return added


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
        # Deliberately a failure, not a skip. This is the only thing standing
        # between an autonomous writer and prose pinned to numbers that do not
        # exist yet, and it runs on the two stages whose merge mode is `auto`.
        # A check that passes because it could not run is worse than no check:
        # it reads green. The venv is one command away and both stages need it
        # for the suite anyway, so "cannot verify" means "not ready to publish".
        return Check(
            "vintage",
            False,
            f"impossibile verificare il vintage di {len(keys)} articoli: l'app non e' importabile "
            f"({type(exc).__name__}). Crea il venv "
            f"(python3 -m venv .venv && .venv/bin/pip install -r requirements.txt) e rilancia.",
        )
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


def _run_suite(cwd=None):
    """Una passata di suite. Ritorna (verdetto, riassunto, codice di uscita),
    dove il verdetto e' 'ok', 'failed' o 'crashed'."""
    result = subprocess.run(
        [_python(), "-X", "faulthandler", "-m", "unittest", "discover", "-s", "tests"],
        cwd=str(cwd or PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    report = (result.stderr or "") + (result.stdout or "")
    tail = [line for line in report.strip().splitlines()[-3:] if line.strip()]
    summary = " / ".join(tail)
    if re.search(r"^FAILED", report, re.M):
        return "failed", summary, result.returncode
    if re.search(r"^OK(\s|$)", report, re.M):
        return "ok", summary, result.returncode
    return "crashed", summary, result.returncode


def check_suite(cwd=None):
    """Il verdetto lo da' il referto di unittest, non il codice di uscita.

    Sembra un cavillo ed e' invece la differenza fra una catena che gira e una
    ferma. Questa suite muore di SIGSEGV circa una run su venticinque, e il
    crash non e' dove sembrava: `-X faulthandler` lo ha inchiodato dentro
    `app.indicator_view.build_indicator_view`, sulla passata in cui il cruscotto
    costruisce la vista di ogni indicatore del catalogo. La causa vera non e'
    ancora nota.

    Ne discendono due comportamenti diversi, e confonderli costa in entrambe le
    direzioni:

    - **`OK` e poi morto.** I test sono passati e lo si dice a voce alta invece
      di ingoiarlo, perche' un crash resta una cosa da sistemare anche quando non
      e' una bocciatura.
    - **Morto senza referto.** Non e' un fallimento, e' un'assenza di risposta.
      Trattarlo come rosso bloccherebbe uno stadio su un guasto che non c'e', e
      la catena e' non presidiata: nessuno rilancerebbe. Quindi si rilancia qui,
      **una volta sola**, e la seconda risposta e' definitiva.

    Ritentare un `FAILED` sarebbe tutt'altra cosa e non si fa: quello e' un bug
    con un referto, e nasconderlo e' esattamente cio' che questo cancello esiste
    per impedire.
    """
    verdict, summary, code = _run_suite(cwd=cwd)

    if verdict == "crashed":
        retry_verdict, retry_summary, retry_code = _run_suite(cwd=cwd)
        if retry_verdict == "crashed":
            return Check("suite", False, (
                f"la suite e' morta senza referto due volte (uscita {code} e {retry_code}). "
                f"Non e' una bocciatura, e' un crash: {retry_summary[:300] or 'nessun referto'}"
            ))
        verdict, summary, code = retry_verdict, retry_summary, retry_code
        summary = f"{summary} (al primo tentativo l'interprete era morto senza referto)"

    if verdict == "failed":
        return Check("suite", False, f"la suite fallisce: {summary[:500] or 'nessun referto leggibile'}")
    if code != 0:
        signal = -code if code < 0 else code
        return Check("suite", True, (
            f"{summary[:160]} (l'interprete e' morto in uscita, segnale {signal}: "
            "i test passano, il crash e' a valle)"
        ))
    return Check("suite", True, summary[:200] or "suite verde")


def build_verdict(stage, paths, checks, base=None):
    """Assemble the answer. Separate from `run` so the policy can be tested
    without a git tree, which is the only way to assert that a red gate really
    does refuse to name a merge mode."""
    ok = all(check.ok for check in checks)
    return {
        "stage": stage,
        "ok": ok,
        # Reported, not implied: a verdict nobody can reproduce is not evidence,
        # and the base is the single input that decides what "the diff" even means.
        "base": base,
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
        # First, because every check under it is measured against this base.
        check_base_is_usable(base, cwd=cwd),
        check_blast_radius(stage, paths),
        check_whitespace(cwd=cwd),
        check_no_coauthor_trailer(base, cwd=cwd),
        check_run_is_recorded(stage, paths, base, cwd=cwd),
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
    return build_verdict(stage, paths, checks, base=resolve_base(base, cwd=cwd))


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
        print(f"  base: {resolve_base(args.base) or 'nessuna (solo working tree)'}")
        for check in verdict["checks"]:
            print(f"  [{'ok ' if check['ok'] else 'NO '}] {check['check']}: {check['detail']}")
        if verdict["paths"]:
            print("  file toccati: " + ", ".join(verdict["paths"]))
    return 0 if verdict["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
