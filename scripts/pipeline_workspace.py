#!/usr/bin/env python3
"""Un worktree git privato per ogni run della catena, e la ragione per cui serve.

Il lanciatore avvia produttore, verificatore e ammissione **in parallelo**, e per
un pezzo la catena ha creduto che bastasse dare a ognuno un branch diverso nella
stessa working directory. Non basta: un checkout git ha **un** HEAD, **un**
indice e **un** branch corrente, condivisi da chiunque lavori in quella cartella.
Due ruoli in volo insieme se li contendono, e il `git checkout -b` di uno sposta
il branch sotto i piedi dell'altro, gli impila i commit sopra, gli cancella un
file non ancora committato, e nel caso peggiore riporta a master un articolo che
un altro aveva gia' committato, senza un solo errore. La premessa "indicatori
diversi toccano file diversi, quindi non contendono" e' vera per i **percorsi**
dei file, non per l'indice git ne' per HEAD.

Il rimedio e' isolare la run, non solo il suo branch: un `git worktree`, cioe' un
albero di lavoro separato con HEAD e indice propri, che condivide il solo archivio
degli oggetti (`.git`). E' lo stesso meccanismo che `pipeline_merge.record_landing`
gia' usa per scrivere il diario su master senza toccare l'albero dell'agente, qui
generalizzato all'albero **dell'agente stesso**.

    # all'avvio di una run (lo stampa il path in cui lavorare):
    python3 scripts/pipeline_workspace.py --open --role producer --run-id <run_id>
    # alla chiusura, dopo il merge:
    python3 scripts/pipeline_workspace.py --close --run-id <run_id>

`--here` non crea un worktree: apre un branch unico nel checkout corrente, per lo
sviluppo manuale di chi non vuole un albero separato. Le run lanciate in parallelo
usano sempre il worktree, perche' li' la contesa e' reale.

Stdlib puro come il resto della catena: un agente cloud lo esegue su un checkout
fresco, prima che esista un venv. Il `runner` e' iniettabile, cosi' un test prova
la sequenza dei comandi git senza un git vero.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# La radice dei worktree delle run: una cartella sorella del checkout, cosi' i
# file di lavoro di una run non compaiono mai come "non tracciati" nel checkout
# principale (che e' la meta' del bug del checkout condiviso che si vuole togliere).
RUNS_ROOT = PROJECT_ROOT.parent / "diset-viz-runs"


def _run(argv, cwd=None):
    """Ogni comando esterno passa di qui, cosi' un test ne sostituisce uno solo."""
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _utc_today():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).date().isoformat()


def branch_name(role, run_id, today=None):
    """Il branch di una run: `automation/<ruolo>-<YYYY-MM-DD>-<suffisso run_id>`.

    Il suffisso e' l'unica cosa che conta davvero: il `run_id` e' gia' unico
    (`<stadio>-<istante>-<quattro esadecimali>`), e portarne la coda nel nome del
    branch e' cio' che rende unico anche il branch di due run dello stesso ruolo
    nello stesso giorno. Era la loro collisione su un nome condiviso
    (`automation/producer-2026-07-29`) a far spostare i branch sotto i piedi.
    Resta dentro `automation/*`, quindi il cancello in CI e la guardia per-agente
    lo riconoscono come prima.
    """
    day = today or _utc_today()
    suffix = run_id.rsplit("-", 1)[-1].strip() if run_id else ""
    return f"automation/{role}-{day}-{suffix}" if suffix else f"automation/{role}-{day}"


def _runs_root(runner=_run, cwd=None):
    """La radice dei worktree delle run, ricavata dal checkout **principale**.

    Non da `PROJECT_ROOT` (la cartella dello script): quando `--close` gira dal
    worktree, `PROJECT_ROOT` e' il worktree stesso, e `PROJECT_ROOT.parent /
    'diset-viz-runs'` diventerebbe `.../diset-viz-runs/diset-viz-runs`, un percorso
    annidato inesistente, e la rimozione fallirebbe in silenzio lasciando il
    worktree registrato per sempre. `--git-common-dir` invece e' lo stesso per
    tutti i worktree (il `.git` del principale), quindi la sua cartella genitore e'
    sempre il checkout principale, sia che si parta da li' sia da un worktree."""
    code, out = runner(["git", "rev-parse", "--git-common-dir"], cwd=cwd)
    if code == 0 and out.strip():
        common = Path(out.strip().splitlines()[0])
        if not common.is_absolute():
            common = (Path(cwd) if cwd else PROJECT_ROOT) / common
        return common.resolve().parent.parent / "diset-viz-runs"
    return RUNS_ROOT


def worktree_path(run_id, root=None):
    """La cartella del worktree di una run, deterministica dal `run_id`."""
    return Path(root or RUNS_ROOT) / (run_id or "run")


def _ensure_master(runner, cwd, attempts=5, sleep=time.sleep, backoff=0.5):
    """Aggiorna `origin/master`, tollerando la corsa fra run concorrenti.

    Piu' run partono insieme e fanno `git fetch` sullo **stesso** repo condiviso:
    i worktree isolano HEAD e indice, ma i ref remoti no, quindi due fetch corrono
    a scrivere `refs/remotes/origin/master` e git respinge il perdente con
    "cannot lock ref". E' transitorio: il lock e' tenuto dal fetch di un sibling e
    si libera appena quello finisce, quindi si **ritenta con backoff** finche' il
    nostro fetch riesce.

    E si fallisce se non riesce mai. La sola prova che `origin/master` e' il tip
    remoto vero e' un fetch nostro andato a buon fine: un `origin/master` che
    "risolve" dice solo che una copia in cache esiste, non che e' fresca. Partire
    da quella copia (fetch fallito per rete o auth, non per lock) farebbe girare il
    cancello su codice vecchio e poi fondere in un master piu' nuovo senza aver mai
    provato l'albero combinato. Meglio fallire l'apertura che partire da un tip non
    verificato."""
    last = ""
    for i in range(max(1, attempts)):
        code, out = runner(["git", "fetch", "origin", "master"], cwd=cwd)
        if code == 0:
            return
        last = out
        if i + 1 < attempts:
            sleep(backoff * (i + 1))
    raise RuntimeError(
        f"git fetch origin master fallito dopo {attempts} tentativi (il ref non e' "
        f"verificato fresco, non si parte da un tip stantio): {last.strip()[:200]}")


def _link_venv(path):
    """Rende il venv del checkout principale visibile nel worktree.

    Il worktree non contiene `.venv` (gitignored, quindi non tracciato), ma il
    passo di merge ci gira dentro e ne ha bisogno: rilancia il cancello, che per
    il vintage importa l'app, e la suite gira su quel venv. Un symlink al venv
    principale fa risolvere `.venv/bin/python` dal worktree senza ricrearlo (deps
    dal venv principale, codice dell'app dal worktree). Best effort: se il
    principale non ha un venv (checkout cloud fresco), non fa niente, e il merge
    lo creera' come gia' prevede il contratto."""
    import os
    main_venv = PROJECT_ROOT / ".venv"
    link = Path(path) / ".venv"
    if main_venv.is_dir() and Path(path).is_dir() and not link.exists():
        try:
            os.symlink(main_venv, link)
        except OSError:
            pass


def open_workspace(role, run_id, base="origin/master", runner=_run, cwd=None,
                   today=None, root=None, here=False, sleep=time.sleep):
    """Apre l'albero di lavoro privato della run e ne ritorna il path (stringa).

    Parte sempre da `origin/master` aggiornato, non da qualunque cosa HEAD porti
    adesso: una run non deve ereditare l'incompiuto di un'altra, ne' finire su un
    master locale stantio (dove, per esempio, `scripts/pipeline_gate.py` potrebbe
    non esistere ancora). Prima il fetch, poi il worktree sul branch della run.

    `here=True` non crea un worktree: apre il branch nel checkout corrente, per lo
    sviluppo manuale. Le run in parallelo non lo usano, li' la contesa e' reale.
    """
    branch = branch_name(role, run_id, today=today)
    _ensure_master(runner, cwd, sleep=sleep)

    if here:
        code, out = runner(["git", "checkout", "-b", branch, base], cwd=cwd)
        if code != 0:
            raise RuntimeError(f"git checkout -b {branch} fallito: {out.strip()[:200]}")
        return str(cwd or PROJECT_ROOT)

    path = worktree_path(run_id, root=root or _runs_root(runner, cwd))
    runner(["git", "worktree", "prune"], cwd=cwd)
    code, out = runner(
        ["git", "worktree", "add", "-b", branch, str(path), base], cwd=cwd)
    if code != 0:
        raise RuntimeError(
            f"git worktree add -b {branch} {path} {base} fallito: {out.strip()[:200]}")
    _link_venv(path)
    return str(path)


def close_workspace(run_id, runner=_run, cwd=None, root=None):
    """Rimuove il worktree della run e pota i riferimenti pendenti.

    Due passaggi come in `record_landing`: `worktree remove --force` cancella la
    cartella, `worktree prune` toglie il riferimento se la cartella e' gia' sparita
    per altra via. Best effort: una run gia' chiusa non deve fallire qui."""
    path = worktree_path(run_id, root=root or _runs_root(runner, cwd))
    runner(["git", "worktree", "remove", "--force", str(path)], cwd=cwd)
    runner(["git", "worktree", "prune"], cwd=cwd)
    return str(path)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Apre o chiude il worktree privato di una run della catena.")
    parser.add_argument("--open", action="store_true", help="apre il worktree e stampa il path")
    parser.add_argument("--close", action="store_true", help="rimuove il worktree della run")
    parser.add_argument("--role", help="il ruolo della run (con --open)")
    parser.add_argument("--run-id", required=True, help="l'id della run, coniato da pipeline_log")
    parser.add_argument("--base", default="origin/master", help="la base da cui partire (con --open)")
    parser.add_argument("--today", default="", help="data YYYY-MM-DD (per i test)")
    parser.add_argument("--here", action="store_true",
                        help="apre il branch nel checkout corrente invece di un worktree")
    args = parser.parse_args(argv)

    if args.open == args.close:
        parser.error("scegli esattamente uno fra --open e --close")

    if args.open:
        if not args.role:
            parser.error("--open vuole --role")
        path = open_workspace(args.role, args.run_id, base=args.base,
                              today=args.today or None, here=args.here)
        print(path)
        return 0

    close_workspace(args.run_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
