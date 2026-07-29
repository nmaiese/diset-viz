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

from scripts import (  # noqa: E402  (path bootstrap above)
    curate,
    discovery,
    indicator_store,
    verification_queue,
)

EXTERNAL_DATASET = "app/static/data/external/normalized_external_indicators.csv"
EXTERNAL_MANIFEST = "app/static/data/external_indicator_manifest.csv"
CURATED_DESCRIPTIONS = "app/static/data/external/curated_descriptions.csv"
CANDIDATES = "data/discovery/candidates.csv"
SOURCE_CANDIDATES = "data/discovery/source_candidates.csv"
CURATION = "data/discovery/curation.csv"
ISTAT_SERIES_CONFIG = "config/istat_series.yaml"
THEME_CATEGORIES = "config/theme_categories.csv"

# I tre perimetri a directory. La barra finale non e' cosmetica: e' cio' che
# `path_allowed` usa per distinguere una directory da un file, e senza di essa
# `content/indicators` autorizzerebbe anche `content/indicators-vecchi.json`.
#
# Sono directory perche' i tre registri che contengono erano file unici a cui
# tutti gli stadi appendevano in coda, cioe' la causa meccanica di ogni
# conflitto fra due run vicine. Un file per record toglie il conflitto invece
# di insegnare a risolverlo.
INDICATOR_TEXTS = "content/indicators/"
# Il diario delle run. Ogni stadio ci scrive a fine run, quindi sta nel
# perimetro di tutti: senza, meta' delle run (quelle che non producono altro)
# non lascerebbe nessuna traccia, che e' esattamente il buco che il diario
# esiste per chiudere.
RUN_JOURNAL = "data/pipeline/runs/"
# Il registro delle verifiche. Sta nel perimetro del solo verificatore, ed e'
# tutto quello che quello stadio produce.
VERIFICATIONS = "data/pipeline/verifiche/"
# Il registro delle prove di pubblicazione (§8 di EDITORIAL_PRACTICE.md). Sta nel
# perimetro del solo `publisher`, lo stadio che verifica il sito e osserva la
# transizione `fusa -> pubblicata`. Come gli altri store e' a un file per record.
PUBLICATIONS = "data/pipeline/pubblicazioni/"

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
    # Il verificatore NON ha `INDICATOR_TEXTS`, e l'assenza e' la definizione
    # dello stadio piu' che il suo prompt. Uno stadio che trova e ripara i propri
    # rilievi corregge i propri compiti, che e' esattamente il difetto che questo
    # stadio esiste per prendere un livello sopra: la firma del revisore era la
    # parola del revisore sul lavoro del revisore. Le smentite tornano al revisore
    # come il segnale `smentita` di `review_queue`, che le legge da qui.
    "verificatore": (VERIFICATIONS, RUN_JOURNAL),
    # Il publisher verifica il sito dopo il merge e il deploy e scrive una prova
    # in `pubblicazioni/`. Non tocca ne' l'articolo ne' la verifica: osserva, non
    # ripara, come il verificatore. Lo stadio esiste nel cancello (perimetro e
    # merge) ma **non** in `pipeline_status.STAGE_ORDER`: non e' uno stadio
    # dell'ordine di catena, e' il passo del sito del lanciatore
    # (`pipeline_launch.py --publish`), che committa la prova da se'.
    "publisher": (PUBLICATIONS, RUN_JOURNAL),
    # I due ruoli della ri-architettura per-indicatore. Nascono qui accanto ai
    # vecchi stadi: il perimetro e' l'unione di quelli che fondono, perche' un
    # ruolo porta un indicatore da grezzo a pubblicato in una sola run. Restano
    # fuori da `pipeline_status.STAGE_ORDER`, che tiene i vecchi stadi granulari,
    # ma li lancia il lanciatore per-indicatore, e il cancello e la guardia li
    # riconoscono, cosi' l'agente produttore ha dove committare.
    #
    # `producer` = curator + writer + reviewer: cura, scrive, si auto-critica,
    # firma. Il perimetro largo e' sicuro perche' gli invarianti del cancello si
    # smistano per tipo-di-file (vedi `run`), non per nome, quindi allargarlo non
    # allarga cio' che sfugge al controllo.
    "producer": (CURATION, EXTERNAL_DATASET, EXTERNAL_MANIFEST, CURATED_DESCRIPTIONS,
                 THEME_CATEGORIES, INDICATOR_TEXTS, RUN_JOURNAL),
    # `admissions` = scout + hunter + promoter: propone la fonte, triaga il
    # candidato, promuove nel layer esterno, in una run.
    "admissions": (SOURCE_CANDIDATES, ISTAT_SERIES_CONFIG, CANDIDATES,
                   EXTERNAL_DATASET, EXTERNAL_MANIFEST, RUN_JOURNAL),
}

# I ruoli che firmano cio' che scrivono. La firma (`reviewed_at`/`reviewed_vintage`)
# non e' un fatto del file ma una responsabilita' del ruolo: il writer tocca
# `INDICATOR_TEXTS` e NON deve firmare (la firma e' del revisore), il reviewer e
# il producer toccano lo stesso file e DEVONO firmare. Per questo `run` smista la
# firma per ruolo e tutto il resto per tipo-di-file toccato.
ROLES_THAT_SIGN = ("reviewer", "producer")

# How far a green gate is allowed to go, per stage. Not uniform on purpose.
#
#   auto     merge now, on the local gate's verdict. The gate this step re-runs
#            has already run the whole suite, the perimeter check and the diff
#            invariants, so a green `auto` is a change the chain has already
#            measured everything it knows how to measure against.
#   checks   merge only once the REMOTE checks have concluded green. Kept as a
#            word the gate can still say, and the wait still lives in
#            `pipeline_merge.py`, but no stage uses it today (see below).
#   manual   never merged by an agent. No stage uses this: the chain is
#            unattended by decision, and a mode that parks a pull request until
#            somebody looks is a mode that parks it forever.
#
# Why every chain stage is `auto` now, not just the prose ones. `checks` waited
# on the remote CI, and on this repository the remote CI does NOT start on a
# pull request opened through the GitHub MCP: GitHub does not run workflows for
# an app-token event, so the checks never appear. `pipeline_merge` then refuses
# a `checks` stage whose checks never showed up (correctly: it cannot merge on a
# wait it cannot satisfy), the pull request sits `pr-open` forever, and the
# dispatcher refuses to launch anything while a chain pull request is open. One
# stuck pull request froze the whole chain. So `checks` bought no independent
# remote verdict, only a deadlock. The local gate keeps the real guarantee (it
# runs the same suite the CI `python` job runs, plus the perimeter the CI `gate`
# job runs), and it runs before the merge instead of never. If the remote CI is
# ever made to fire on these pull requests, the number-moving stages
# (scout, hunter, promoter, curator, verificatore) are the ones to move back.
#
# The wait for `checks` lives in `scripts/pipeline_merge.py`, not in a `gh` flag.
# `gh pr merge --auto` does NOT wait on this repository: with `allow_auto_merge`
# false and `master` unprotected it falls back to merging immediately, and a
# probe pull request proved it by merging with the test job still running.
MERGE_POLICY = {
    "scout": "auto",
    "hunter": "auto",
    "promoter": "auto",
    "curator": "auto",
    "writer": "auto",
    "reviewer": "auto",
    "verificatore": "auto",
    # `publisher` non e' in STAGE_ORDER e non e' uno stadio dell'ordine di catena:
    # la prova di pubblicazione si committa nel passo `--publish` del tick del
    # lanciatore, non via una PR e questo passo di merge. La sua policy resta
    # inerte, la lasciamo `checks`.
    "publisher": "checks",
    # I ruoli per-indicatore fondono `auto` come tutti gli altri: il cancello
    # locale gira la suite e gli invarianti prima del merge.
    "producer": "auto",
    "admissions": "auto",
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


def _root_for(cwd=None):
    """La radice del working tree a cui `cwd` appartiene, da cui leggere i file.

    Non il `PROJECT_ROOT` del modulo. La guardia importa `pipeline_gate` dal
    checkout principale (l'hook gira come `$CLAUDE_PROJECT_DIR/scripts/agent_guard.py`)
    ma passa `cwd=worktree`: git opera sul cwd, ma leggere i file sotto il
    principale farebbe sparire quelli appena aggiunti nel worktree. Un diario
    committato nel worktree risulterebbe cancellato, e lo Stop hook rifiuterebbe
    una run bloccata/in errore che aveva committato correttamente la sua riga.
    Senza cwd (o se non e' un working tree) resta il principale."""
    if cwd:
        code, out, _ = _git("rev-parse", "--show-toplevel", cwd=cwd)
        if code == 0 and out.strip():
            return Path(out.strip())
    return PROJECT_ROOT


def _indicators_root(cwd=None):
    """La cartella degli articoli nel working tree di `cwd` (o nel principale).

    Serve a `indicator_store.load_all`/`verification_queue.load_texts`, i cui root
    sono fissati all'import del modulo: se il cancello e' importato dal checkout
    principale ma gira con `cwd=worktree`, senza questo leggerebbero gli articoli
    del principale invece di quelli cambiati nel worktree, e un verdetto potrebbe
    validare la versione sbagliata."""
    return _root_for(cwd) / "content" / "indicators"


def check_base_is_usable(base=None, cwd=None):
    """La base deve poter spiegare il diff, non deve essere in cima a master.

    Prima qui bastava che la base **non fosse un antenato** di HEAD per
    bocciare lo stadio, e quella severita' e' stata il difetto piu' costoso
    della catena. Master si muove di continuo, anche solo perche' un altro
    stadio ha registrato l'esito di una run, quindi ogni pull request aperta da
    piu' di qualche minuto diventava rossa senza che il suo lavoro fosse
    cambiato di una virgola. Il passo di merge che rifiutava una pull request
    scriveva una riga su master, quella riga faceva diventare rosse le pull
    request degli altri stadi, e un rifiuto solo bastava a fermare la catena
    intera: un anello di retroazione fatto di controlli tutti corretti presi
    uno per uno.

    La severita' non serviva nemmeno. Il diff lo misura `changed_paths` con i
    **tre punti** (`base...HEAD`), che confronta contro la base comune, quindi
    resta esatto anche quando master e' andato avanti. `check_no_coauthor`
    usa i due punti, che elencano i soli commit del branch, ed e' esatto per la
    stessa ragione. Quello che serve davvero e' che una base comune **esista**:
    senza, non c'e' nessun diff da misurare, e li' il verdetto e' fiction sul
    serio.

    Che master sia andato avanti resta scritto nel dettaglio, perche' spiega
    perche' la CI potrebbe vedere qualcosa che il cancello locale non vede: i
    check remoti girano sul merge commit, quindi su branch piu' master.
    """
    resolved = resolve_base(base, cwd=cwd)
    if not resolved:
        return Check("base", True, "nessuna base di confronto, giudizio sul solo working tree")
    code, _, _ = _git("merge-base", resolved, "HEAD", cwd=cwd)
    if code != 0:
        return Check(
            "base",
            False,
            f"la base '{resolved}' e HEAD non hanno nessun antenato in comune: non c'e' un diff "
            f"da misurare. Recupera la storia (git fetch --unshallow) o passa la base con --base.",
        )
    behind, _, _ = _git("merge-base", "--is-ancestor", resolved, "HEAD", cwd=cwd)
    if behind != 0:
        return Check(
            "base",
            True,
            f"{resolved} e' andata avanti senza questo branch: il diff resta esatto (tre punti), "
            f"ma i check remoti girano sul merge e possono vedere di piu'.",
        )
    return Check("base", True, f"confronto contro {resolved}")


def changed_paths(base=None, cwd=None, include_worktree=True):
    """Repo-relative paths this branch touches, committed and uncommitted.

    Both halves matter. A cloud agent commits before opening its PR, so the diff
    against the base is the real answer. A local run may still have the change
    in the working tree, and a gate that only looked at commits would call that
    branch clean and green.

    `--untracked-files=all` e non il default. Senza, git riassume una directory
    nuova in una voce sola (`content/indicators/`), e da quando gli store sono
    a un file per record quella e' la forma normale del lavoro di uno stadio:
    il perimetro avrebbe giudicato un percorso che non e' un file, e
    `changed_text_keys` ne avrebbe ricavato la chiave inventata `indicators`.

    `include_worktree=False` guarda i soli commit e ignora `git status`. Serve al
    passo di merge, dove il lavoro dello stadio e' gia' committato sul branch: li'
    il working tree o e' vuoto, o (in un checkout condiviso, prima che i worktree
    isolino le run) porta l'incompiuto di un altro ruolo, che attribuire a questa
    run era la seconda faccia del bug del checkout condiviso. Il cancello locale
    interattivo tiene True: una prova locale ha il lavoro ancora da committare.
    """
    paths = set()
    resolved = resolve_base(base, cwd=cwd)
    if resolved:
        code, out, _ = _git("diff", "--name-only", f"{resolved}...HEAD", cwd=cwd)
        if code == 0:
            paths.update(line.strip() for line in out.splitlines() if line.strip())
    if include_worktree:
        code, out, _ = _git("status", "--porcelain", "--untracked-files=all", cwd=cwd)
        if code == 0:
            for line in out.splitlines():
                entry = line[3:].strip()
                if not entry:
                    continue
                # Renames arrive as "old -> new"; the destination is what changed.
                paths.add(entry.split(" -> ")[-1].strip())
    return sorted(p for p in paths if p)


def path_allowed(path, allowed):
    """Un percorso rientra nel perimetro `allowed`.

    Due forme, e la differenza sta tutta nella barra finale. Senza, la voce e'
    un file e vale l'uguaglianza esatta, come e' sempre stato. Con, e' una
    directory e vale il prefisso, che e' l'unico modo di autorizzare uno store
    a un file per record senza elencarne i trecento file.

    Il prefisso e' ancorato alla barra di proposito. `content/indicators` come
    prefisso nudo autorizzerebbe `content/indicators-bozze.json`, cioe' un
    percorso fuori dallo store, e un perimetro che si allarga da solo su un
    errore di battitura non e' un perimetro.

    Dentro una directory di store passa **solo `.json`**, e nemmeno questo e'
    zelo. I tre store contengono un tipo di file solo, e tutto il resto della
    catena lo da' per scontato: `_touched_under` cerca `.json` per sapere che
    cosa e' cambiato, quindi un file di altro tipo sarebbe dentro il perimetro
    e insieme invisibile a ogni controllo che legge il contenuto. Un articolo
    scritto in `content/indicators/note.txt` non renderizzerebbe da nessuna
    parte e non farebbe fallire niente, che e' la forma di guasto che questo
    progetto ha gia' pagato con `analyst_notes.json`.
    """
    for entry in allowed:
        if entry.endswith("/"):
            if path.startswith(entry) and path.endswith(".json"):
                return True
        elif path == entry:
            return True
    return False


def check_blast_radius(stage, paths):
    allowed = STAGE_PATHS[stage]
    stray = [p for p in paths if not path_allowed(p, allowed)]
    if stray:
        return Check(
            "blast-radius",
            False,
            f"lo stadio '{stage}' puo' toccare solo {', '.join(allowed)}. Fuori perimetro: {', '.join(stray)}",
        )
    if not paths:
        return Check("blast-radius", True, "nessun file modificato")
    return Check("blast-radius", True, f"{len(paths)} file, tutti nel perimetro dello stadio")


def _touched_under(prefix, base=None, cwd=None, include_worktree=True):
    """Quali file di uno store questo branch aggiunge, cambia o toglie.

    Sostituisce il confronto riga per riga che serviva quando ogni registro era
    un file solo. Con un file per record la domanda "che cosa e' cambiato" la
    risponde l'elenco dei percorsi, senza rileggere e ridiffare il contenuto, e
    la risposta e' esatta invece che dedotta: prima un articolo modificato si
    riconosceva confrontando due JSON interi, adesso e' il nome del file.

    Unisce i commit e il working tree, come `changed_paths`, perche' una prova
    locale ha il lavoro ancora non committato e un cancello che la chiama
    pulita non serve a niente.
    """
    resolved = resolve_base(base, cwd=cwd)
    touched = [
        p for p in changed_paths(base, cwd=cwd, include_worktree=include_worktree)
        if p.startswith(prefix) and p.endswith(".json")
    ]
    added, changed, gone = [], [], []
    for path in touched:
        at_base = False
        if resolved:
            code, _, _ = _git("cat-file", "-e", f"{resolved}:{path}", cwd=cwd)
            at_base = code == 0
        if not (_root_for(cwd) / path).exists():
            gone.append(path)
        elif at_base:
            changed.append(path)
        else:
            added.append(path)
    return {"added": added, "changed": changed, "gone": gone,
            "touched": sorted(added + changed + gone)}


def _read_json_at(ref, path, cwd=None):
    """Il contenuto JSON di un file a un dato commit, o None."""
    code, out, _ = _git("show", f"{ref}:{path}", cwd=cwd)
    if code != 0:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


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


def _read_csv(path, cwd=None):
    full = _root_for(cwd) / path
    if not full.exists():
        return []
    return discovery.read_semicolon(full)


def check_hunter_decisions(rows=None, cwd=None):
    """A triage decision with no written reason is not a decision, it is a
    coin toss with a CSV column. The chain has to be able to explain, months
    later, why a candidate was let in, and the only place that survives is the
    queue itself."""
    rows = rows if rows is not None else _read_csv(CANDIDATES, cwd=cwd)
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


def check_curation_decisions(rows=None, cwd=None):
    """`score_eligible=true` on a verso that is not directional would put an
    indicator with no "better" into the quality-of-life score, where every value
    is oriented. apply_curation refuses it too, but the gate says so before the
    PR exists rather than after."""
    rows = rows if rows is not None else _read_csv(CURATION, cwd=cwd)
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


def _prose_fingerprints(rows, resolved, cwd=None):
    """Le impronte valide: quelle di adesso, piu' quelle della base.

    Le due versioni e non solo la prima, per la ragione spiegata in
    `check_verifications`. Della base pero' si leggono **solo** gli articoli che
    le righe nuove citano: prima il testo stava tutto in un file e bastava un
    `git show`, adesso sono trecentosessantacinque file e leggerli tutti a ogni
    verdetto renderebbe il cancello il passo piu' lento della catena per
    rispondere a una domanda su tre articoli.
    """
    fingerprints = set()
    try:
        texts = verification_queue.load_texts(root=_indicators_root(cwd))
    except (OSError, ValueError, indicator_store.StoreError):
        texts = {}
    for key, entry in texts.items():
        fingerprints.add((
            verification_queue.code_of(key),
            (entry.get("level") or "regione"),
            verification_queue.prose_fingerprint(entry),
        ))
    if not resolved:
        return fingerprints
    wanted = {(row.get("code") or "").strip() for row in rows}
    for key in texts:
        if verification_queue.code_of(key) not in wanted:
            continue
        path = INDICATOR_TEXTS + indicator_store.filename_for(key)
        old = _read_json_at(resolved, path, cwd=cwd)
        if not isinstance(old, dict):
            continue
        fingerprints.add((
            verification_queue.code_of(key),
            (old.get("level") or "regione"),
            verification_queue.prose_fingerprint(old),
        ))
    return fingerprints


def check_verifications(base=None, cwd=None, include_worktree=True):
    """Il verificatore consegna dei numeri, quindi i numeri devono reggere.

    Ogni verifica nuova deve dire quante affermazioni ha
    controllato, e i tre parziali devono sommare a quel totale. Non e' pignoleria
    contabile: senza `controllate` la frase "zero smentite" e la frase "non ho
    guardato" producono lo stesso file, e uno stadio che non sa distinguerle
    costa una pull request per articolo e non garantisce niente. La 3.3 del piano
    lo chiama il campo che non si negozia, e qui e' meccanico invece che ricordato
    in un prompt, per la stessa ragione per cui il perimetro sta nel repo.

    Controlla anche che la riga parli di un articolo che esiste e che l'impronta
    della prosa sia quella del testo di adesso. Una verifica registrata su
    un'impronta che non corrisponde a niente e' una verifica di un testo che non
    e' in pagina, e sarebbe invisibile: la coda la scarterebbe in silenzio come
    "da riverificare" e il conto delle smentite non tornerebbe mai.
    """
    resolved = resolve_base(base, cwd=cwd)
    # Il registro e' **append-only**, e questo controllo viene prima di guardare le
    # righe nuove. Contare solo le righe aggiunte non vede le sottrazioni, quindi
    # una run che cancella una smentita e non aggiunge niente passava come "nessuna
    # verifica nuova da controllare": il segnale sparisce dalla coda del revisore
    # con il cancello verde, che e' il modo peggiore di perdere un rilievo.
    #
    # Append-only e non solo "niente cancellazioni", perche' riscrivere una riga
    # in posto e' la stessa cosa con un passaggio in piu': cambia che cosa dice una
    # verifica passata senza lasciare traccia. Una verifica si supera riscrivendo
    # l'articolo, cosa che cambia l'impronta e ne chiede una nuova, mai
    # modificando la riga vecchia.
    removed = _verification_rows_removed(base, cwd=cwd, include_worktree=include_worktree)
    if removed:
        return Check(
            "verifiche", False,
            f"il registro e' append-only e questa run ne toglie o riscrive "
            f"{len(removed)} righe: "
            f"{', '.join(sorted(r.get('code') or '?' for r in removed)[:5])}. "
            "Per superare una verifica si riscrive l'articolo, non la sua riga.",
        )
    rows = _verification_rows_added(base, cwd=cwd, include_worktree=include_worktree)
    if not rows:
        return Check("verifiche", True, "nessuna verifica nuova da controllare")

    problems = []
    for row in rows:
        for problem in verification_queue.row_problems(row):
            problems.append(f"{row.get('code') or '?'}: {problem}")
    if problems:
        return Check("verifiche", False, "; ".join(problems[:5]))

    # L'impronta deve corrispondere a un testo che questo repo ha davvero avuto:
    # quello di adesso, oppure quello della base. Le due versioni, e non solo la
    # prima, perche' la prima e' stata scritta e subito smentita da un caso reale.
    #
    # Un verificatore legge l'articolo, calcola l'impronta e apre la pull request.
    # Nel frattempo la Routine del revisore puo' aver fuso una correzione sullo
    # stesso articolo: l'impronta della run resta quella del testo che ha
    # effettivamente letto, cioe' quella della base, ed e' onesta. Pretendere
    # l'impronta di adesso bloccava una run corretta ogni volta che due stadi si
    # incrociavano, che in una catena con due Routine al giorno non e' un caso
    # limite. Quello che va preso e' l'impronta che non corrisponde a **niente**,
    # cioe' scritta a mano o calcolata su un checkout che non e' questo.
    # La tupla porta anche il livello, e non e' pignoleria: `build_queue` unisce
    # le righe agli articoli su `(code, level)`, quindi una riga con il livello
    # sbagliato passerebbe di qui e poi non coprirebbe niente. Una smentita
    # registrata cosi' sarebbe scritta e invisibile allo stesso tempo, che e' il
    # modo di fallire peggiore fra quelli disponibili.
    fingerprints = _prose_fingerprints(rows, resolved, cwd=cwd)
    if not fingerprints:
        return Check("verifiche", False, "testi illeggibili, impossibile verificare le impronte")

    known_codes = {code for code, _level, _hash in fingerprints}
    known_pairs = {(code, level) for code, level, _hash in fingerprints}
    orphans, wrong_level, drifted = [], [], []
    for row in rows:
        code = (row.get("code") or "").strip()
        level = (row.get("level") or "").strip()
        if code not in known_codes:
            orphans.append(code)
        elif (code, level) not in known_pairs:
            wrong_level.append(f"{code} (livello {level!r})")
        elif (code, level, (row.get("prosa") or "").strip()) not in fingerprints:
            drifted.append(code)
    if orphans:
        return Check("verifiche", False,
                     f"verifiche su articoli che non esistono: {', '.join(orphans[:5])}")
    if wrong_level:
        return Check(
            "verifiche", False,
            f"livello che non corrisponde all'articolo: {', '.join(wrong_level[:5])}. "
            "La coda unisce su (codice, livello), quindi questa riga non coprirebbe "
            "niente e una sua smentita non arriverebbe al revisore.",
        )
    if drifted:
        return Check(
            "verifiche", False,
            f"impronta della prosa che non corrisponde a nessuna versione di "
            f"{', '.join(drifted[:5])}, ne' quella di adesso ne' quella della base. "
            "Ricalcolala con verification_queue.prose_fingerprint invece di scriverla.",
        )

    controllate = sum(verification_queue._int(r.get("controllate")) for r in rows)
    smentite = sum(verification_queue._int(r.get("smentite")) for r in rows)
    return Check("verifiche", True,
                 f"{len(rows)} verifiche, {controllate} affermazioni controllate, "
                 f"{smentite} smentite")


def _verification_rows_removed(base=None, cwd=None, include_worktree=True):
    """Le verifiche della base che questo branch ha tolto o riscritto.

    Cancellare un file e riscriverlo in posto sono la stessa cosa per il
    registro, cioe' cambiare che cosa dice una verifica gia' data, ed e'
    esattamente cio' che l'append-only vieta. Con un file per verifica la
    distinzione fra "aggiunta" e "riscrittura" e' il nome del file invece che
    un confronto di righe, quindi non c'e' piu' niente da dedurre.
    """
    resolved = resolve_base(base, cwd=cwd)
    if not resolved:
        return []
    touched = _touched_under(VERIFICATIONS, base, cwd=cwd, include_worktree=include_worktree)
    rows = []
    for path in touched["gone"] + touched["changed"]:
        old = _read_json_at(resolved, path, cwd=cwd)
        if isinstance(old, dict):
            rows.append(old)
    return rows


def _verification_rows_added(base=None, cwd=None, include_worktree=True):
    """Le verifiche che questo branch aggiunge, gia' interpretate."""
    rows = []
    for path in _touched_under(VERIFICATIONS, base, cwd=cwd, include_worktree=include_worktree)["added"]:
        try:
            data = json.loads((_root_for(cwd) / path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            rows.append(data)
    return rows


def _publication_rows_added(base=None, cwd=None, include_worktree=True):
    """Le prove di pubblicazione che questo branch aggiunge o riscrive.

    Una prova puo' essere riscritta senza colpa: rifare la stessa verifica scrive
    lo stesso nome di file (l'impronta `prosa` e' nel nome), ed e' idempotente.
    Quindi qui bastano aggiunte e modifiche, senza la regola append-only del
    diario o delle verifiche.
    """
    rows = []
    touched = _touched_under(PUBLICATIONS, base, cwd=cwd, include_worktree=include_worktree)
    for path in touched["added"] + touched["changed"]:
        try:
            data = json.loads((_root_for(cwd) / path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            rows.append(data)
    return rows


def check_publications(base=None, cwd=None, include_worktree=True):
    """Il publisher consegna delle prove, quindi le prove devono reggere.

    Impone la prudenza di §8 invece di ricordarla: una prova con `ok` diverso da
    True e' un controllo che non ha confermato niente, e registrarla come
    pubblicazione e' il falso positivo che tutta la Fase D esiste per non avere.
    L'impronta `prosa` deve corrispondere a un testo che questo repo ha davvero
    avuto, quello di adesso o quello della base, per la stessa ragione delle
    verifiche: una prova ancorata a un'impronta che non e' di nessuna versione e'
    la prova di un testo che non e' in pagina. Il grosso del giudizio e' in
    `verify_publication.publication_problems`, puro e provato senza un albero git.
    """
    from scripts import practice_timeline, verify_publication, verification_queue

    # Cancellare una prova non e' mai legittimo: una prova scade quando il testo
    # cambia (l'impronta non combacia piu' e la ricostruzione la ignora), non
    # togliendola. Cancellarla farebbe regredire un indicatore da `pubblicata` a
    # `fusa` senza lasciare traccia, che e' esattamente la sparizione di una prova
    # che il cancello deve impedire. La riscrittura in posto invece si controlla
    # come una riga nuova, sotto.
    gone = _touched_under(PUBLICATIONS, base, cwd=cwd, include_worktree=include_worktree)["gone"]
    if gone:
        return Check(
            "pubblicazioni", False,
            f"il registro delle prove non si cancella: questa run toglie {len(gone)} "
            f"prove ({', '.join(sorted(gone)[:5])}). Una prova scade cambiando il testo, "
            "non cancellandola, e toglierla fa regredire un indicatore da pubblicata a fusa.")

    rows = _publication_rows_added(base, cwd=cwd, include_worktree=include_worktree)
    if not rows:
        return Check("pubblicazioni", True, "nessuna prova nuova da controllare")

    resolved = resolve_base(base, cwd=cwd)
    try:
        entries = indicator_store.load_all(root=_indicators_root(cwd))
    except (OSError, ValueError, indicator_store.StoreError):
        entries = {}

    valid = {}
    for row in rows:
        code = (row.get("code") or "").strip()
        if not code or code in valid:
            continue
        key = practice_timeline.key_of_code(code)
        fingerprints = set()
        entry = entries.get(key)
        if entry is not None:
            fingerprints.add(verification_queue.prose_fingerprint(entry))
        if resolved:
            old = _read_json_at(resolved, INDICATOR_TEXTS + indicator_store.filename_for(key), cwd=cwd)
            if isinstance(old, dict):
                fingerprints.add(verification_queue.prose_fingerprint(old))
        if fingerprints:
            valid[code] = fingerprints

    problems = []
    for row in rows:
        problems.extend(verify_publication.publication_problems(row, valid))
    if problems:
        return Check("pubblicazioni", False, "; ".join(problems[:5]))
    return Check("pubblicazioni", True,
                 f"{len(rows)} prove, tutte confermate e ancorate al testo di adesso o della base")


def check_reviewer_signature(base=None, cwd=None, include_worktree=True):
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
    keys = changed_text_keys(base, cwd=cwd, include_worktree=include_worktree)
    if not keys:
        return Check("firma-revisore", True, "nessuna modifica ai testi")
    try:
        entries = indicator_store.load_all(root=_indicators_root(cwd))
    except (OSError, ValueError, indicator_store.StoreError) as exc:
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


def changed_text_keys(base=None, cwd=None, include_worktree=True):
    """Gli articoli che questo branch ha davvero toccato.

    Adesso e' l'elenco dei file, e prima non poteva esserlo. Con un JSON unico
    il diff mostrava le **righe** cambiate, e la chiave che le possiede poteva
    stare cento righe piu' su, quindi bisognava rileggere e confrontare due
    oggetti interi da mezzo megabyte per sapere di quale indicatore si stesse
    parlando. Con un file per articolo la domanda e' gia' risposta dal nome.
    """
    touched = _touched_under(INDICATOR_TEXTS, base, cwd=cwd, include_worktree=include_worktree)
    return sorted(indicator_store.key_of(p) for p in touched["touched"])


def check_run_is_recorded(stage, paths, base=None, cwd=None, include_worktree=True):
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
    # Il diario e' append-only come il registro delle verifiche, e il controllo
    # viene per primo perche' e' l'unico che riguarda le run **passate**. Una
    # run puo' solo aggiungere il proprio file: riscrivere quello di una run
    # vecchia, o cancellarlo, vuol dire cambiare che cosa ha detto qualcun
    # altro, ed e' l'unico modo di far sparire un `blocked` dalla storia. La
    # riga dell'esito che il passo di merge scrive e' un file nuovo anche lei,
    # quindi nessun flusso legittimo passa di qui.
    touched = _touched_under(RUN_JOURNAL, base, cwd=cwd, include_worktree=include_worktree)
    rewritten = touched["changed"] + touched["gone"]
    if rewritten:
        return Check(
            "diario", False,
            f"il diario e' append-only e questa run ne riscrive o cancella "
            f"{len(rewritten)} righe: {', '.join(sorted(rewritten)[:5])}. "
            "Una run registra la propria e non tocca quelle di prima.",
        )

    worked = [p for p in paths if not p.startswith(RUN_JOURNAL)]
    if not worked:
        return Check("diario", True, "nessun lavoro da registrare")
    journal = [p for p in paths if p.startswith(RUN_JOURNAL)]
    if not journal:
        return Check(
            "diario",
            False,
            f"la run ha toccato {len(worked)} file ma non ha registrato niente in {RUN_JOURNAL}. "
            f"Aggiungi la riga con: python3 scripts/pipeline_log.py --write --stage {stage} "
            f"--outcome <esito> --summary \"...\"",
        )
    added = _journal_lines_added(base, cwd=cwd, include_worktree=include_worktree)
    mine = [entry for entry in added if entry.get("stage") == stage]
    if not mine:
        return Check(
            "diario",
            False,
            f"il diario e' cambiato ma nessuna riga nuova e' dello stadio '{stage}'",
        )
    return Check("diario", True, f"{len(mine)} run registrate come '{stage}'")


def _journal_lines_added(base=None, cwd=None, include_worktree=True):
    """Le run che questo branch registra, gia' interpretate.

    Un file per run, quindi "aggiunta" e' letteralmente un file nuovo. La
    versione che confrontava le righe di un `.jsonl` doveva indovinare quali
    fossero nuove leggendo il testo, e sbagliava ogni volta che due stadi
    scrivevano nello stesso punto.
    """
    touched = _touched_under(RUN_JOURNAL, base, cwd=cwd, include_worktree=include_worktree)
    entries = []
    for path in touched["added"] + touched["changed"]:
        full = _root_for(cwd) / path
        try:
            data = json.loads(full.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            entries.append(data)
    return entries


def check_writer_vintage(base=None, cwd=None, include_worktree=True):
    """The writer's contract is `vintage == year_max`, stricter than the drift
    guard in the suite, which only fails when the vintage falls *behind*. A
    vintage ahead of the data is prose written against numbers that do not exist
    yet, and nothing would ever flag it: the drift guard is looking the other
    way, and a reader has no way to tell.

    Scoped to the ids the branch touched. The suite already walks all of them
    for staleness, and rebuilding 362 view models to re-check work nobody edited
    would make the gate the slowest step in an autonomous chain.
    """
    keys = changed_text_keys(base, cwd=cwd, include_worktree=include_worktree)
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
    entries = indicator_store.load_all(root=_indicators_root(cwd))
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
    # The summary comes from stderr alone, where unittest writes its verdict and
    # where faulthandler writes a crash. Taking the tail of the concatenation
    # instead means that any test printing anything to stdout lands at the end
    # and becomes the whole message: the gate reported "suite: 1 segnali, 150
    # parole" in place of "Ran 476 tests / OK". The verdict was right, the line
    # a human reads was not, and on this chain that line is the only record.
    verdict_source = (result.stderr or "").strip() or report
    tail = [line for line in verdict_source.strip().splitlines()[-3:] if line.strip()]
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


def invariant_labels(stage, paths):
    """Which content invariants a diff triggers, and whether the role must sign.

    Pure (no git, no disk): the whole point is that the dispatch can be tested
    without a tree. Smistato per **tipo-di-file toccato**, non per nome-stadio,
    cosi' un ruolo fuso (`producer`, `admissions`) compone da solo i controlli
    dei tipi che tocca. Ogni vecchio stadio tocca esattamente i tipi che
    innescavano i suoi controlli, quindi per loro il risultato e' identico a
    prima. L'unica eccezione e' la **firma**: e' del ruolo, non del file, perche'
    il writer tocca `INDICATOR_TEXTS` e non deve firmare, mentre il reviewer e il
    producer toccano lo stesso file e devono.
    """
    def touched(*targets):
        return any(path_allowed(p, targets) for p in paths)

    labels = []
    if touched(CANDIDATES):
        labels.append("triage")
    if touched(CURATION):
        labels.append("curation")
    if touched(INDICATOR_TEXTS):
        labels.append("vintage")
        if stage in ROLES_THAT_SIGN:
            labels.append("signature")
    if touched(VERIFICATIONS):
        labels.append("verifications")
    if touched(PUBLICATIONS):
        labels.append("publications")
    return labels


def run(stage, base=None, skip_tests=False, cwd=None, committed_only=False):
    """Every check for one stage, in the order a failure should be read.

    `committed_only=True` misura il solo diff committato e non il working tree
    (`include_worktree=False` ovunque). Lo usa il passo di merge: li' il lavoro
    dello stadio e' gia' committato sul branch, quindi un file non committato o
    non c'e', o e' l'incompiuto di un altro ruolo in un checkout condiviso, e
    attribuirlo a questa run era la seconda faccia del bug del checkout condiviso.
    Il cancello locale interattivo tiene False: una prova locale ha il lavoro
    ancora da committare, e un cancello cieco al working tree la chiamerebbe pulita.
    """
    if stage not in STAGE_PATHS:
        raise SystemExit(f"stadio sconosciuto '{stage}'. Noti: {', '.join(sorted(STAGE_PATHS))}")
    iw = not committed_only
    paths = changed_paths(base, cwd=cwd, include_worktree=iw)
    checks = [
        # First, because every check under it is measured against this base.
        check_base_is_usable(base, cwd=cwd),
        check_blast_radius(stage, paths),
        check_whitespace(cwd=cwd),
        check_no_coauthor_trailer(base, cwd=cwd),
        check_run_is_recorded(stage, paths, base, cwd=cwd, include_worktree=iw),
    ]
    # Gli invarianti di contenuto si smistano per **tipo-di-file toccato dal
    # diff** (piu' la firma, che e' del ruolo): `invariant_labels` decide quali,
    # ed e' pura, cosi' la composizione si prova senza git ne' disco.
    builders = {
        "triage": lambda: check_hunter_decisions(cwd=cwd),
        "curation": lambda: check_curation_decisions(cwd=cwd),
        "vintage": lambda: check_writer_vintage(base, cwd=cwd, include_worktree=iw),
        "signature": lambda: check_reviewer_signature(base, cwd=cwd, include_worktree=iw),
        "verifications": lambda: check_verifications(base, cwd=cwd, include_worktree=iw),
        "publications": lambda: check_publications(base, cwd=cwd, include_worktree=iw),
    }
    for label in invariant_labels(stage, paths):
        checks.append(builders[label]())
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
    parser.add_argument("--committed-only", action="store_true",
                        help="misura il solo diff committato, ignora il working tree "
                             "(il passo di merge lo usa: al merge il lavoro e' gia' committato)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    verdict = run(args.stage, args.base, skip_tests=args.skip_tests,
                  committed_only=args.committed_only)
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
