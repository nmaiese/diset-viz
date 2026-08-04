#!/usr/bin/env python3
"""Il diario della catena: che cosa ha fatto ogni agente, quando, e come e' finita.

Il problema che risolve. Gli agenti girano in cloud, a freddo, e per tutta la
durata della run non lasciano nessuna traccia: l'unico segno che qualcosa e'
successo arriva alla fine, sotto forma di commit o di pull request. Se una run
non produce niente (coda vuota, cancello che blocca, agente che si ferma a
meta') non resta assolutamente nulla da leggere, e la domanda "che cosa ha fatto
stanotte il revisore" non ha risposta. Peggio: una Routine che gira e non
produce ha lo stesso aspetto di una Routine che non e' mai partita, ed e'
esattamente cosi' che lo scrittore ha lavorato per settimane su un file morto
senza che nessuno se ne accorgesse.

Il diario e' la risposta. Ogni agente, alla fine della run, registra qui che
cosa ha fatto, **anche quando non ha prodotto niente**, che e' il caso in cui
serve di piu'. E' committato, quindi la storia sopravvive alla sessione che
l'ha creata.

## Un file per run, e non piu' un registro unico

Era `runs.jsonl`, una riga per run in fondo a un file solo, e la forma era la
causa del guasto piu' frequente della catena. Sette stadi che appendono tutti
in coda allo stesso file collidono **sempre** quando girano vicini: git vede
due modifiche sull'ultima riga e chiama conflitto quella che e' solo la somma
di due righe che non si contraddicono. Il contratto degli agenti ci aveva
costruito sopra un'intera sezione che spiegava come risolvere a mano tenendo
tutte e due le parti, cioe' una pagina di prosa per rimediare a un problema che
il formato non doveva avere.

Adesso ogni run scrive il **proprio** file in `data/pipeline/runs/`, e due run
diverse non toccano mai lo stesso percorso. Il conflitto non e' improbabile,
non e' risolvibile: non esiste. Le trenta run del vecchio `runs.jsonl` sono
state travasate una per file e il registro unico e' sparito: tenerlo e leggerlo
accanto agli shard avrebbe contato due volte le stesse run, che e' proprio il
genere di numero sbagliato che questo file esiste per non produrre.

## Chi ha fatto cosa: il `run_id`

Le due righe di una run (quella dell'agente dentro la PR, quella del passo di
merge su master) si univano su `(stadio, pr)`, e non funzionava, perche' la
riga dell'agente **non puo' conoscere il numero della PR**: viaggia dentro la
pull request, quindi va committata prima che la pull request esista. Sulle
prime trenta run reali, diciannove non avevano il campo, il diario dichiarava
ventuno run `pr-open` contro sei fuse, e nessuna delle due cifre era vera.

Il `run_id` toglie il problema alla radice: lo conia chi scrive la prima riga,
lo stampa, e l'agente lo passa al passo di merge. Non dipende da niente che
succeda dopo.

    python3 scripts/pipeline_log.py                    # la timeline
    python3 scripts/pipeline_log.py --stage writer     # un agente solo
    python3 scripts/pipeline_log.py --json

    # quello che scrive un agente alla fine della sua run
    python3 scripts/pipeline_log.py --write \\
        --stage reviewer --outcome pr-open \\
        --summary "5 articoli riletti, 2 correzioni causali" \\
        --detail "eur-rd_e_gerdreg: tolta la domanda retorica" \\
        --gate auto --queue-before 41 --queue-after 36
    # stampa: run_id: reviewer-20260727T110207Z-a3f1

Stdlib puro come il resto della catena.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import pipeline_gate  # noqa: E402  (path bootstrap above)

# Dove scrive chi registra una run: un file per run, mai contendibile.
RUNS_DIR = PROJECT_ROOT / "data" / "pipeline" / "runs"
# Gli stadi che il cancello conosce (`pipeline_gate.STAGE_PATHS`), piu' `launch`,
# il battito del lanciatore. `launch` non e' uno stadio del cancello: non ha
# perimetro, non apre pull request e non passa dal cancello. Registra pero' un
# tick per volta, ed e' quella riga a rendere misurabile il silenzio della
# catena senza dover ricopiare qui il cron delle Routine. Si deriva da
# STAGE_PATHS invece di riscriverla a mano: cosi' `build_entry` accetta ogni
# stadio che il cancello sa fondere (produttore, ammissione, publisher inclusi),
# e un ruolo nuovo non torna a crashare il passo di merge dopo che ha gia' fuso.
STAGES = tuple(sorted(pipeline_gate.STAGE_PATHS)) + ("launch",)

# Come e' finita una run. Il vocabolario e' corto di proposito: un campo libero
# si riempirebbe di sinonimi e diventerebbe illeggibile in aggregato.
OUTCOMES = {
    "merged": "fatto e pubblicato",
    "pr-open": "PR aperta, aspetta",
    "blocked": "cancello bloccato",
    "nothing": "niente da fare",
    "stopped": "fermato a meta'",
    "error": "errore",
}

# Quali esiti meritano di essere notati leggendo in fretta. `nothing` non e' un
# problema, e' la risposta giusta quando la coda e' vuota.
ATTENTION = {"blocked", "stopped", "error"}

# Ogni quanto ci si aspetta che qualcuno registri una run, per gruppo di stadi.
#
# Serve perche' il diario da solo non vede il modo di fallire piu' pericoloso di
# tutti: una Routine che smette di partire. Una run andata male lascia una riga
# `blocked` e si vede subito. Una run che non parte, o che muore prima di
# scrivere, non lascia niente, e il diario di uno stadio fermo da un mese e'
# identico a quello di uno stadio che ha finito il lavoro. E' la stessa forma del
# bug che e' costato settimane: il silenzio letto come normalita'.
#
# **Il gruppo che conta davvero e' il primo.** Da quando il lavoro lo assegna il
# lanciatore, un ruolo non ha piu' una cadenza propria: gira quando la sua coda
# non e' vuota, quindi il suo silenzio e' una risposta legittima e non un
# guasto. Chi ha una cadenza e' il lanciatore, ed e' l'unico la cui assenza
# significa senza ambiguita' che la catena si e' fermata: percio' il suo battito
# (`launch`) e i ruoli che lancia (`admissions`, `producer`, `publisher`) stanno
# tutti nel primo gruppo, l'unico esente dal conto delle code. Tenerli qui, e
# non in gruppi per-ruolo, e' voluto: i gruppi a coda piena portano solo i nomi
# dei vecchi stadi, che sono le uniche chiavi che `queue_sizes()` produce, cosi'
# nessun ruolo finisce in un gruppo dove una coda non contata diventerebbe un
# falso ritardo.
#
# Le attese per stadio restano, ma valgono **solo a coda piena**: `silence` le
# applica se gli si passano le code, e uno stadio zitto con la coda a zero
# risulta `idle`, non in ritardo. Segnalare fermo il curatore perche' non c'e'
# niente da curare e' il modo piu' sicuro di insegnare a ignorare gli avvisi.
#
# Cacciatore e promotore condividono un agente solo: chiude su `hunter` se non
# ha promosso niente e su `promoter` se ha promosso, quindi ci si aspetta una
# riga dall'uno **o** dall'altro, mai da tutti e due.
WATCH_GROUPS = (
    ("lanciatore", ("launch", "admissions", "producer", "publisher"), 1),
    ("scout", ("scout",), 7),
    ("cacciatore", ("hunter", "promoter"), 7),
    ("curatore", ("curator",), 7),
    ("scrittore", ("writer",), 7),
    ("revisore", ("reviewer",), 1),
    # Il verificatore gira dietro al revisore, quindi la sua attesa e' la
    # stessa: se il revisore firma ogni giorno, ogni giorno c'e' qualcosa da
    # provare a far cadere.
    ("verificatore", ("verificatore",), 1),
)
# Una run saltata non e' una catena rotta. Due si'.
GRACE = 2.5

# Da dove e' partita una run. Corto come il vocabolario degli esiti, e per la
# stessa ragione: serve a poter chiedere "quante ne ha lanciate il lanciatore"
# senza leggere trenta righe di prosa.
TRIGGERS = ("launch", "routine", "manuale")
# La variabile con cui il lanciatore si annuncia agli agenti che lancia, cosi'
# la provenienza non dipende dal fatto che l'agente si ricordi di dichiararla.
TRIGGER_ENV = "DI_PIPELINE_TRIGGER"

# Lo stato che l'hook di inizio sessione lascia per chi scrive il diario:
# session_id e istante di avvio. Locale e mai committato (.gitignore), perche'
# appartiene alla sessione e non alla storia. Sovrascrivibile nei test.
SESSION_META = PROJECT_ROOT / "data" / "pipeline" / ".session_meta.json"


def _now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _git(*args):
    result = subprocess.run(
        ("git",) + args, cwd=str(PROJECT_ROOT), capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr


def new_run_id(stage):
    """L'identita' di una run, coniata da chi la registra.

    Forma `<stadio>-<istante>-<quattro esadecimali>`, leggibile a occhio e
    ordinabile per tempo. I quattro esadecimali servono al caso in cui due run
    dello stesso stadio partano nello stesso secondo, che con un lanciatore che
    ne conia piu' d'uno non e' impossibile e con un ritentativo nemmeno improbabile.
    """
    import secrets
    from datetime import datetime, timezone

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stage}-{stamp}-{secrets.token_hex(2)}"


_CLAUDE_VERSION_CACHE = []


def _claude_version():
    """La versione di Claude Code che sta facendo girare la run, o ''.

    Best effort e memoizzata: una run senza CLI in PATH (la CI, un checkout
    locale) scrive semplicemente meno campi. Il campo esiste perche' hook e
    subagent sono cambiati piu' volte nel corso del 2026, e una regressione di
    comportamento senza la versione nel diario non e' diagnosticabile.
    """
    if _CLAUDE_VERSION_CACHE:
        return _CLAUDE_VERSION_CACHE[0]
    import shutil

    version = ""
    if shutil.which("claude"):
        try:
            result = subprocess.run(
                ("claude", "--version"), capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip().splitlines()[0][:80] if result.stdout.strip() else ""
        except (OSError, subprocess.TimeoutExpired):
            version = ""
    _CLAUDE_VERSION_CACHE.append(version)
    return version


def _session_meta(path=None):
    """Il meta di sessione lasciato da session-start.sh, o {}."""
    target = Path(path) if path else SESSION_META
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _session_fields():
    """I campi con cui il diario dice CHI ha prodotto la run, non solo cosa.

    Tutti facoltativi e tutti best-effort: la riga di diario resta valida anche
    scritta da un checkout senza sessione Claude. Quello che c'e' viene scritto,
    quello che manca non diventa una stringa vuota da leggere per niente.

    - `model`: dall'ambiente della sessione, se dichiarato.
    - `claude_code_version`: dal CLI, se in PATH.
    - `session_id` e `duration_seconds`: dal meta che l'hook di inizio sessione
      lascia in `SESSION_META`. La durata e' dall'avvio della sessione alla
      scrittura della riga, che per una run della catena (una sessione, una
      run) e' la durata della run.
    - `base_commit`: dove stava master quando la riga e' stata scritta. Il
      campo `commit` e' l'HEAD del branch della run; senza la base, il diff che
      il cancello ha giudicato non e' ricostruibile a distanza di mesi.
    """
    fields = {}
    model = (os.environ.get("ANTHROPIC_MODEL") or os.environ.get("CLAUDE_MODEL") or "").strip()
    if model:
        fields["model"] = model
    version = _claude_version()
    if version:
        fields["claude_code_version"] = version
    meta = _session_meta()
    session_id = str(meta.get("session_id") or "").strip()
    if session_id:
        fields["session_id"] = session_id
    started = str(meta.get("started_at") or "").strip()
    if started:
        from datetime import datetime, timezone

        try:
            began = datetime.fromisoformat(started.replace("Z", "+00:00"))
            if began.tzinfo is None:
                began = began.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - began).total_seconds()
            if elapsed >= 0:
                fields["duration_seconds"] = int(elapsed)
        except ValueError:
            pass
    for candidate in ("origin/master", "master"):
        code, out, _ = _git("rev-parse", "--short", candidate)
        if code == 0 and out.strip():
            fields["base_commit"] = out.strip()
            break
    return fields


def read_journal(path=None):
    """Tutte le run registrate.

    `path` accetta tutte e due le forme, e non e' una comodita': i test
    scrivono un `.jsonl` temporaneo, la catena scrive una directory, e una
    funzione che ne capisce una sola costringerebbe a duplicare la lettura.
    """
    target = Path(path) if path else RUNS_DIR
    if target.is_dir():
        return _read_shards(target)
    if target.exists():
        return _read_jsonl(target)
    return []


def _read_shards(root):
    """Un file per run. Un file illeggibile non nasconde gli altri.

    Illeggibile pero' non vuol dire assente, e la differenza e' tutto il punto
    di questo file. Saltare in silenzio uno shard rotto farebbe sparire una run
    dal diario, cioe' produrrebbe esattamente l'invisibilita' che il diario
    esiste per togliere, e per giunta proprio sulle run andate male, che sono
    quelle piu' probabilmente scritte a meta'. Quindi si lascia un segnaposto,
    come fa da sempre la lettura riga per riga del vecchio registro.
    """
    entries = []
    for shard in sorted(Path(root).glob("*.json")):
        try:
            data = json.loads(shard.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            entries.append({
                "stage": "?", "outcome": "error", "run_id": shard.stem,
                "summary": f"run illeggibile in {shard.name}: {type(exc).__name__}",
                "at": "", "detail": [], "gate": "", "pr": "",
            })
            continue
        if isinstance(data, dict):
            entries.append(data)
        else:
            entries.append({
                "stage": "?", "outcome": "error", "run_id": shard.stem,
                "summary": f"{shard.name} non contiene un oggetto JSON",
                "at": "", "detail": [], "gate": "", "pr": "",
            })
    return sorted(entries, key=lambda r: r.get("at") or "")


def _read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            # Una riga rotta non deve rendere illeggibile tutto il diario: e' un
            # registro, non uno schema, e la riga dopo vale ancora.
            entries.append({"stage": "?", "outcome": "error", "summary": f"riga illeggibile: {line[:80]}"})
    return entries


def shard_name(entry, suffix=""):
    """Il nome del file di una riga di diario.

    Il `run_id` e' gia' unico, quindi il nome non ha bisogno di altro. Il
    suffisso distingue le due righe della stessa run: quella dell'agente,
    dentro la pull request, e quella dell'esito, che il passo di merge scrive
    su master quando sa come e' finita. Nomi diversi, quindi nemmeno quelle due
    si contendono un percorso.
    """
    run_id = entry.get("run_id") or f"{entry.get('stage', 'ignoto')}-senza-id"
    return f"{run_id}{suffix}.json"


def append(entry, path=None, suffix=""):
    """Registra una run. Su una directory scrive uno shard, su un file appende.

    Il doppio comportamento non e' indecisione: la catena scrive shard, i test
    e chiunque abbia in mano un vecchio `.jsonl` continuano a poter appendere
    una riga, e le due strade portano allo stesso `read_journal`.
    """
    target = Path(path) if path else RUNS_DIR
    if target.suffix == ".jsonl":
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        return entry
    target.mkdir(parents=True, exist_ok=True)
    (target / shard_name(entry, suffix)).write_text(
        json.dumps(entry, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
        encoding="utf-8",
    )
    return entry


def build_entry(stage, outcome, summary, detail=None, gate=None, pr=None,
                commit=None, branch=None, queue_before=None, queue_after=None,
                run_id=None, trigger=None):
    if stage not in STAGES:
        raise SystemExit(f"stadio sconosciuto '{stage}'. Noti: {', '.join(STAGES)}")
    if outcome not in OUTCOMES:
        raise SystemExit(f"esito sconosciuto '{outcome}'. Noti: {', '.join(OUTCOMES)}")
    trigger = trigger or os.environ.get(TRIGGER_ENV) or "manuale"
    if trigger not in TRIGGERS:
        raise SystemExit(f"provenienza sconosciuta '{trigger}'. Note: {', '.join(TRIGGERS)}")
    if not branch:
        code, out, _ = _git("rev-parse", "--abbrev-ref", "HEAD")
        branch = out.strip() if code == 0 else ""
    if not commit:
        code, out, _ = _git("rev-parse", "--short", "HEAD")
        commit = out.strip() if code == 0 else ""
    entry = {
        "at": _now(),
        "run_id": run_id or new_run_id(stage),
        "trigger": trigger,
        "stage": stage,
        "outcome": outcome,
        "summary": summary,
        "detail": detail or [],
        "gate": gate or "",
        "pr": pr or "",
        "commit": commit,
        "branch": branch,
    }
    if queue_before is not None:
        entry["queue_before"] = queue_before
    if queue_after is not None:
        entry["queue_after"] = queue_after
    # Chi ha prodotto la run: modello, versione del CLI, sessione, durata,
    # base. Facoltativi tutti, perche' la riga deve restare scrivibile da
    # qualsiasi checkout, ma quando ci sono trasformano "che cosa e' successo"
    # in "che cosa e' successo, con che cosa": senza, una regressione dopo un
    # cambio di modello o di runtime non ha nessuna pista nel diario.
    entry.update(_session_fields())
    return entry


def collapse_runs(entries):
    """Una run lascia due righe, e sono un evento solo.

    L'agente scrive la propria dentro la pull request, quando l'esito non lo sa
    ancora, e scrive `pr-open`. Il passo di merge scrive la seconda su master,
    quando l'esito lo conosce. Chi legge le contava come due run, e siccome solo
    le run che aprono una PR ne producono due, il conteggio gonfiava proprio gli
    stadi che lavorano e lasciava intatti quelli fermi: il numero saliva quando
    la catena andava bene, che e' il modo piu' subdolo di essere sbagliato.

    Si uniscono per `run_id`, che e' l'unica cosa che identifica una run
    davvero. Prima la chiave era `(stadio, pr)`, e su trenta run reali ne
    apparava undici: la riga dell'agente **non puo'** portare il numero della
    pull request, perche' viaggia dentro la pull request e va committata prima
    che esista. Il diario finiva per dichiarare ventuno run in attesa quando le
    pull request aperte erano zero.

    `(stadio, pr)` resta come ripiego per le righe vecchie, scritte prima che
    esistesse il `run_id`, e per l'agente che si dimentica di passarlo al passo
    di merge. Una riga senza ne' l'uno ne' l'altro resta per conto suo, che e'
    la risposta giusta: non si sa a quale run appartenga, e inventarlo sarebbe
    peggio che dirlo.

    L'unione tiene il meglio delle due, non la piu' recente. La riga dell'agente
    porta le motivazioni, una per decisione, e sono la parte che serve rileggere
    a distanza di mesi. La riga del passo di merge porta l'esito vero e il
    verdetto del cancello. Buttarne via una delle due sarebbe tornare a scegliere
    fra sapere che cosa e' stato deciso e sapere come e' finita.
    """
    order, index = [], {}
    for entry in sorted(entries, key=lambda r: r.get("at") or ""):
        run_id = str(entry.get("run_id") or "").strip()
        pr = str(entry.get("pr") or "").strip()
        key = ("run", run_id) if run_id else (("pr", entry.get("stage"), pr) if pr else None)
        if key is None:
            order.append(entry)
            continue
        if key not in index:
            index[key] = len(order)
            order.append(dict(entry))
            continue
        first = order[index[key]]
        # `pr-open` non e' un esito, e' l'assenza di un esito: vuol dire che
        # chi ha scritto la riga non sapeva ancora come sarebbe finita. Non
        # deve mai coprire un esito vero, e prendere semplicemente la riga piu'
        # recente lo faceva ogni volta che le due cadevano nello stesso secondo,
        # perche' a parita' di istante l'ordine lo decide il nome del file.
        incoming = entry.get("outcome")
        if incoming and (incoming != "pr-open" or first.get("outcome") == "pr-open"):
            first["outcome"] = incoming
        first["gate"] = entry.get("gate") or first.get("gate")
        first["commit"] = entry.get("commit") or first.get("commit")
        # Il numero arriva quasi sempre dalla seconda riga, ed e' la ragione
        # per cui la prima non lo poteva avere.
        first["pr"] = first.get("pr") or entry.get("pr") or ""
        # `at` diventa quando la run si e' chiusa, non quando ha aperto la PR:
        # e' la data che l'allarme del silenzio deve guardare. Il massimo e non
        # l'ultima letta, per la stessa ragione dell'esito qui sopra.
        first["at"] = max(entry.get("at") or "", first.get("at") or "")
        first["detail"] = (first.get("detail") or []) + (entry.get("detail") or [])
    return order


def summarize(entries):
    """Aggregato per stadio: l'ultima run e quante ne meritano attenzione."""
    by_stage = {}
    for entry in entries:
        by_stage.setdefault(entry.get("stage", "?"), []).append(entry)
    out = {}
    for stage, runs in by_stage.items():
        ordered = sorted(runs, key=lambda r: r.get("at", ""))
        out[stage] = {
            "runs": len(ordered),
            "last": ordered[-1],
            "attention": sum(1 for r in ordered if r.get("outcome") in ATTENTION),
        }
    return out


def _days_since(stamp, today):
    from datetime import datetime

    if not stamp:
        return None
    try:
        when = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if when.tzinfo is None:
        from datetime import timezone

        when = when.replace(tzinfo=timezone.utc)
    return max(0, (today - when).total_seconds() / 86400)


def silence(entries, today=None, queues=None):
    """Quali gruppi di stadi hanno smesso di farsi vivi.

    Ritorna una riga per gruppo, sempre, anche per i gruppi in orario: un
    cruscotto che mostra solo i problemi non permette di distinguere "tutto a
    posto" da "il controllo non ha girato".

    `queues` e' facoltativo e cambia il significato della risposta. Senza, un
    silenzio lungo e' un ritardo, che era vero quando ogni stadio aveva un
    cron. Con le code (`{stadio: quanti in attesa}`, come le calcola
    `pipeline_status`), un silenzio lungo con la coda vuota diventa `idle`
    invece che `stale`: da quando il lavoro lo assegna il lanciatore, uno
    stadio che tace perche' non ha niente da fare sta rispondendo, non si e'
    fermato. Le code arrivano da fuori invece che da un import perche' questo
    modulo resta senza dipendenze, il che e' anche cio' che permette di
    provarlo senza toccare un file.
    """
    from datetime import datetime, timezone

    today = today or datetime.now(timezone.utc)
    latest = {}
    for entry in entries:
        stage = entry.get("stage")
        stamp = entry.get("at") or ""
        if stage and stamp > latest.get(stage, ""):
            latest[stage] = stamp
    rows = []
    for name, stages, expected in WATCH_GROUPS:
        stamps = [latest[s] for s in stages if s in latest]
        last = max(stamps) if stamps else ""
        days = _days_since(last, today)
        late = days is not None and days > expected * GRACE
        # Il lanciatore non ha una coda, ha un battito: quando tace non c'e'
        # niente da interpretare, e' proprio lui a non essere partito.
        #
        # Una coda che nessuno ha potuto contare (`None`, che capita ai due
        # stadi che hanno bisogno del view model) resta `None` e **non** diventa
        # zero. Sommandola a zero, uno stadio zitto da un mese con la coda
        # incalcolabile risultava `idle`, cioe' "tace perche' non ha niente da
        # fare", che e' l'opposto di quello che si sa: non si sa niente. E'
        # la stessa scelta che fa `pipeline_status`, dove una coda non contata
        # vale come lavoro e non come lavoro finito.
        waiting = None
        if queues is not None and name != "lanciatore":
            counts = [queues.get(s) for s in stages]
            if all(c is not None for c in counts):
                waiting = sum(int(c) for c in counts)
        rows.append({
            "group": name,
            "stages": list(stages),
            "expected_days": expected,
            "last": last,
            "days_since": None if days is None else round(days, 1),
            "waiting": waiting,
            # Mai registrata una run non e' "in ritardo", e' "non ancora vista":
            # dire che il revisore e' fermo da sempre il giorno in cui nasce il
            # diario sarebbe un falso allarme che insegna a ignorare gli allarmi.
            "stale": late and (waiting is None or waiting > 0),
            # Zitto perche' non ha niente da fare. E' una risposta, non un
            # guasto, e tenerla distinta e' cio' che permette all'avviso di
            # restare credibile.
            "idle": late and waiting == 0,
            "never": not last,
        })
    return rows


def queue_sizes():
    """Le code degli stadi, o None se non si riescono a contare.

    Importato qui dentro e non in testa: `pipeline_status` legge il catalogo e
    per due stadi ha bisogno del view model, quindi puo' fallire su un checkout
    appena clonato. Il diario deve restare leggibile anche li', e senza le code
    `silence` torna semplicemente al comportamento di prima.
    """
    try:
        from scripts import pipeline_status

        return pipeline_status.queue_sizes()
    except Exception:
        return None


def _print_silence(entries, queues=None):
    rows = silence(entries, queues=queues)
    late = [r for r in rows if r["stale"]]
    print()
    if late:
        print("Stadi fermi:")
        for row in late:
            waiting = "" if row["waiting"] is None else f", {row['waiting']} in coda"
            print(f"  ! {row['group']:11s} ultima run {row['days_since']:.0f} giorni fa, "
                  f"ne era attesa una ogni {row['expected_days']}{waiting}")
    else:
        seen = [r for r in rows if not r["never"]]
        if seen:
            print("Nessuno stadio e fermo oltre l'attesa.")
    idle = [r for r in rows if r.get("idle")]
    if idle:
        print("Zitti perche non hanno niente da fare: " + ", ".join(r["group"] for r in idle))
    never = [r for r in rows if r["never"]]
    if never:
        print("Mai registrata una run: " + ", ".join(r["group"] for r in never))


def _print_timeline(entries, limit, queues=None):
    if not entries:
        print("Il diario e vuoto: nessun agente ha ancora registrato una run.")
        print("Le run precedenti al diario si leggono in git (`git log --oneline`) e nelle PR.")
        return
    shown = sorted(entries, key=lambda r: r.get("at", ""), reverse=True)[:limit]
    print(f"Diario della catena, ultime {len(shown)} run su {len(entries)}\n")
    for entry in shown:
        mark = "!" if entry.get("outcome") in ATTENTION else " "
        when = (entry.get("at") or "")[:16].replace("T", " ")
        outcome = OUTCOMES.get(entry.get("outcome"), entry.get("outcome", "?"))
        print(f"{mark} {when}  {entry.get('stage', '?'):9s} {outcome:22s} {entry.get('summary', '')}")
        for line in entry.get("detail") or []:
            print(f"      - {line}")
        refs = []
        if entry.get("pr"):
            refs.append(f"PR #{entry['pr']}")
        if entry.get("gate"):
            refs.append(f"cancello: {entry['gate']}")
        if entry.get("commit"):
            refs.append(entry["commit"])
        if refs:
            print(f"      {' | '.join(refs)}")
    print()
    for stage in STAGES:
        state = summarize(entries).get(stage)
        if not state:
            print(f"  {stage:9s} mai registrata una run")
            continue
        last = state["last"]
        warn = f"  ({state['attention']} da guardare)" if state["attention"] else ""
        print(f"  {stage:9s} {state['runs']:3d} run, ultima {(last.get('at') or '')[:10]}"
              f" -> {OUTCOMES.get(last.get('outcome'), '?')}{warn}")
    _print_silence(entries, queues=queues)


def main():
    parser = argparse.ArgumentParser(description="Il diario della catena: chi ha girato, quando, con che esito.")
    parser.add_argument("--stage", choices=STAGES, help="un solo stadio")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    write = parser.add_argument_group("scrittura (la usa l'agente a fine run)")
    write.add_argument("--write", action="store_true", help="aggiunge una riga al diario")
    write.add_argument("--outcome", choices=sorted(OUTCOMES))
    write.add_argument("--summary", help="una riga: che cosa hai fatto")
    write.add_argument("--detail", action="append", default=[], help="ripetibile: una riga per decisione")
    write.add_argument("--gate", help="il campo merge del verdetto del cancello")
    write.add_argument("--pr", help="numero della pull request, se l'hai aperta")
    write.add_argument("--run-id", help="l'identita' della run, se ne hai gia' una")
    write.add_argument("--mint-run-id", action="store_true",
                       help="conia un run_id nuovo invece di richiederne uno esistente "
                            "(solo per chi non apre mai una pull request, es. il lanciatore)")
    write.add_argument("--trigger", choices=TRIGGERS,
                       help=f"da dove parte la run (default: ${TRIGGER_ENV}, poi 'manuale')")
    write.add_argument("--queue-before", type=int, help="quanto c'era in coda quando hai aperto")
    write.add_argument("--queue-after", type=int, help="quanto ne resta adesso")
    args = parser.parse_args()

    if args.write:
        if not (args.stage and args.outcome and args.summary):
            raise SystemExit("per scrivere servono --stage, --outcome e --summary")
        if not args.run_id and not args.mint_run_id:
            raise SystemExit(
                "--run-id mancante: e' l'unica cosa che lega questa riga alla pull "
                "request che la porta (docs/AGENT_CONTRACT.md #4). Se davvero non "
                "ne hai gia' uno (nessuna pull request in arrivo), passa "
                "--mint-run-id."
            )
        entry = append(build_entry(
            args.stage, args.outcome, args.summary,
            detail=args.detail, gate=args.gate, pr=args.pr,
            run_id=args.run_id, trigger=args.trigger,
            queue_before=args.queue_before, queue_after=args.queue_after,
        ))
        print(f"registrato: {entry['stage']} -> {entry['outcome']}")
        # Stampato e non solo scritto: e' il valore che va passato al passo di
        # merge, ed e' l'unica cosa che lega questa riga a come finira'.
        print(f"run_id: {entry['run_id']}")
        return 0

    entries = collapse_runs(read_journal())
    if args.stage:
        entries = [e for e in entries if e.get("stage") == args.stage]
    if args.json:
        print(json.dumps({"entries": entries, "by_stage": summarize(entries),
                          "silence": silence(entries, queues=queue_sizes())},
                         ensure_ascii=False, indent=2))
        return 0
    _print_timeline(entries, args.limit, queues=queue_sizes())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
