#!/usr/bin/env python3
"""Quanto costa un articolo, misurato invece che stimato.

La telemetria in Supabase (`pipeline_monitor.py --post-tokens`) copre solo le
run passate dal lanciatore, che le riporta dal risultato di `Agent`. Questo
script legge la fonte completa: i transcript locali di Claude Code sotto
`~/.claude/projects/`, dove ogni messaggio porta il proprio `usage`.

Due modi, un solo contratto di misura:

    python3 scripts/baseline_tokens.py                    # per sessione (catena vecchia)
    python3 scripts/baseline_tokens.py --since 2026-07-31 --articles 19
    python3 scripts/baseline_tokens.py --workflow wf_15ac7ba3-209 --articles 2

## Il contratto di misura, e perche' serve scritto

Tre trappole, tutte trovate misurando la prima run del workflow nuovo. Finche'
la catena vecchia e quella nuova non passano dallo stesso codice, nessun
bersaglio di costo e' aggiudicabile: si confrontano denominatori diversi.

**Uno: il trascritto scrive due record per richiesta.** Un parziale e un
finale, con lo stesso `requestId` e un `usage` sovrapposto. Sommandoli si conta
due volte: sulla prima run faceva 406 turni invece di 224 e 26,1 milioni di
lettura cache invece di 14,9. Fattore 1,75. Qui si tiene **un record per
`requestId`**, il piu' completo.

**Due: `usage` non conta i subagent.** La documentazione lo dice: *"the `usage`
field undercounts as soon as nesting occurs"*. Per questo l'attribuzione e' per
file di agente, non per aggregato di sessione.

**Tre: le chiamate all'advisor non compaiono da nessuna parte.** Stanno in
`usage.iterations` con `type: "advisor_message"`, e l'aggregato di primo
livello **le esclude**: un turno con aggregato `input_tokens: 4` portava
un'iterazione advisor da 71.870 token di input non in cache. Sulla prima run
erano 9 chiamate, 740 mila token di input e 75 mila di output, cioe' **il 35%
del costo del workflow**, invisibile in ogni contatore.

Il consumo si riporta spaccato, perche' i pezzi non costano uguale: input non
in cache, scrittura di cache, lettura di cache (un decimo), output. La voce che
domina non e' quella che si crede.

Stdlib pura, sola lettura, non tocca il repo.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

PROJECTS = "~/.claude/projects/*diset-viz*"

# Il `run_id` che ogni ruolo scrive nel diario: <ruolo>-<YYYYMMDDTHHMMSSZ>-<4 hex>.
RUN_ID = re.compile(
    r"\b(producer|verificatore|admissions|writer|reviewer|curator|scout|"
    r"hunter|promoter|launch|reader-editor)-\d{8}T\d{6}Z-[0-9a-f]{4}\b"
)

# I ruoli che non producono prosa: si escludono dal costo per articolo.
NOT_WRITING = ("admissions", "scout", "hunter", "promoter")

# Dollari per milione di token, listino Opus. Indicativo: serve a dare una
# scala, non a fare fatturazione.
PRICE = {"in": 5.0, "cache_w": 6.25, "cache_r": 0.5, "out": 25.0}

FIELDS = ("in", "cache_w", "cache_r", "out")
USAGE_KEYS = {
    "in": "input_tokens",
    "out": "output_tokens",
    "cache_w": "cache_creation_input_tokens",
    "cache_r": "cache_read_input_tokens",
}

# Il tipo di iterazione che nessun campo aggregato porta.
ADVISOR = "advisor_message"


def zero() -> dict:
    return {field: 0 for field in FIELDS}


def add(into: dict, other: dict) -> dict:
    for field in FIELDS:
        into[field] += other[field]
    return into


def _from_usage(usage: dict) -> dict:
    return {field: usage.get(key) or 0 for field, key in USAGE_KEYS.items()}


def split_usage(usage: dict) -> tuple[dict, dict]:
    """(modello, advisor) da un `usage`, senza doppioni e senza buchi.

    Quando `iterations` c'e', l'aggregato di primo livello somma **solo** le
    iterazioni di tipo `message`: le `advisor_message` restano fuori da input e
    output, e vanno raccolte a parte o si perdono. Quando non c'e', l'aggregato
    e' tutto cio' che esiste.
    """
    iterations = usage.get("iterations")
    if not iterations:
        return _from_usage(usage), zero()
    model, advisor = zero(), zero()
    for step in iterations:
        add(advisor if step.get("type") == ADVISOR else model, _from_usage(step))
    return model, advisor


def turns(path: str) -> list[dict]:
    """Un record per `requestId`, il piu' completo, in ordine di comparsa.

    Il parziale e il finale della stessa richiesta portano lo stesso `usage`
    ma solo il finale porta `iterations`: si tiene quello che pesa di piu',
    che e' anche quello che vede l'advisor.
    """
    best: dict[str, dict] = {}
    with open(path, errors="replace") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if record.get("type") != "assistant":
                continue
            usage = (record.get("message") or {}).get("usage") or {}
            if not usage:
                continue
            key = record.get("requestId") or record.get("uuid") or str(len(best))
            model, advisor = split_usage(usage)
            weight = sum(model.values()) + sum(advisor.values())
            if key not in best or weight > best[key]["weight"]:
                best[key] = {"weight": weight, "model": model, "advisor": advisor,
                             "record": record}
    return list(best.values())


def cost(use: dict) -> float:
    return sum(use[field] / 1e6 * PRICE[field] for field in FIELDS)


def tool_calls(record: dict) -> list[str]:
    content = (record.get("message") or {}).get("content")
    if not isinstance(content, list):
        return []
    return [block.get("name") or "?" for block in content
            if isinstance(block, dict) and block.get("type") == "tool_use"]


# ---------------------------------------------------------------- workflow

def find_workflow(name: str) -> list[str]:
    """**Tutte** le cartelle dei trascritti di una run, dal suo id o da un percorso.

    Plurale, e non e' pedanteria. Una run **ripresa** (`resumeFromRunId`) tiene
    lo stesso `run_id` ma scrive nella cartella della sessione nuova, quindi lo
    stesso identificatore esiste sotto due sessioni: gli agenti replicati da
    cache stanno di qua, quelli rigirati di la'. Questa funzione restituiva il
    **primo** che trovava, cioe' misurava meta' run e lo diceva con la stessa
    faccia con cui dice un totale: su una ripresa vera ha stampato 3 agenti,
    4 turni e $0,24 al posto di 7 agenti e ~$2.

    E' lo stesso difetto che questo file esiste per chiudere, un piano piu' in
    basso: un numero che sembra un totale e non lo e'. Il contratto di misura
    e' uno solo, quindi qui si sommano tutte le cartelle e non se ne sceglie
    una.
    """
    if os.path.isdir(name):
        return [name]
    trovate = []
    for root in glob.glob(os.path.expanduser(PROJECTS)):
        for hit in glob.glob(os.path.join(root, "*", "subagents", "workflows", name)):
            if os.path.isdir(hit):
                trovate.append(hit)
    return sorted(trovate)


def labels(directory: str) -> dict:
    """agentId -> etichetta, dai metadati della run.

    Non dal `journal.jsonl`, che porta solo `agentId` e la chiave di cache: le
    etichette e le fasi stanno in `<sessione>/workflows/<runId>.json`, sotto
    `workflowProgress`, accanto ai trascritti ma non dentro la loro cartella.
    """
    out: dict[str, str] = {}
    session = os.path.dirname(os.path.dirname(os.path.abspath(directory)))
    path = os.path.join(os.path.dirname(session), "workflows",
                        os.path.basename(directory.rstrip("/")) + ".json")
    if not os.path.exists(path):
        return out
    try:
        with open(path, encoding="utf-8") as handle:
            meta = json.load(handle)
    except (OSError, ValueError):
        return out
    for step in meta.get("workflowProgress") or []:
        if isinstance(step, dict) and step.get("agentId") and step.get("label"):
            out[step["agentId"]] = step["label"]
    return out


def read_agents(directory: str) -> list[dict]:
    named = labels(directory)
    agents = []
    for path in sorted(glob.glob(os.path.join(directory, "agent-*.jsonl"))):
        rows = turns(path)
        if not rows:
            continue
        model, advisor = zero(), zero()
        tools: dict[str, int] = {}
        for row in rows:
            add(model, row["model"])
            add(advisor, row["advisor"])
            for name in tool_calls(row["record"]):
                tools[name] = tools.get(name, 0) + 1
        agent_id = rows[0]["record"].get("agentId") or ""
        label = named.get(agent_id) or os.path.basename(path)[6:14]
        agents.append({"id": agent_id or os.path.basename(path),
                       "label": label, "turns": len(rows), "model": model,
                       "advisor": advisor, "tools": tools,
                       "advisor_calls": sum(1 for r in rows if any(r["advisor"].values()))})
    agents.sort(key=lambda a: -cost(a["model"]) - cost(a["advisor"]))
    return agents


def report_workflow(directories, articles: int) -> None:
    if isinstance(directories, str):
        directories = [directories]
    # Una run ripresa vive in due cartelle e un agente puo' comparire in
    # entrambe (replicato da cache di la', rigirato di qua): si tiene una volta
    # sola, per nome di file, altrimenti il totale conta due volte proprio i
    # turni che la ripresa non ha pagato.
    agents, visti = [], set()
    for directory in directories:
        for agent in read_agents(directory):
            if agent["id"] in visti:
                continue
            visti.add(agent["id"])
            agents.append(agent)
    nome = os.path.basename(str(directories[0]).rstrip("/"))
    dove = f" (ripresa: {len(directories)} sessioni)" if len(directories) > 1 else ""
    print(f"RUN {nome}{dove}: {len(agents)} agenti\n")
    print(f"{'agente':28} {'turni':>6} {'tool':>5} {'cache lett':>12} "
          f"{'output':>8} {'advisor':>8} {'$':>7}")
    total, total_advisor = zero(), zero()
    for agent in agents:
        add(total, agent["model"])
        add(total_advisor, agent["advisor"])
        both = cost(agent["model"]) + cost(agent["advisor"])
        print(f"{agent['label'][:28]:28} {agent['turns']:6} "
              f"{sum(agent['tools'].values()):5} {agent['model']['cache_r']:12,} "
              f"{agent['model']['out']:8,} {agent['advisor_calls']:8} {both:7.2f}")

    print("\nTOTALE, contratto di misura del docstring")
    for field, label in (("in", "input non in cache"), ("cache_w", "scrittura di cache"),
                         ("cache_r", "lettura di cache"), ("out", "output")):
        extra = f"  (+{total_advisor[field]:,} advisor)" if total_advisor[field] else ""
        print(f"  {label:22} {total[field]:>15,}{extra}")
    calls = sum(a["advisor_calls"] for a in agents)
    print(f"  {'turni':22} {sum(a['turns'] for a in agents):>15,}")
    print(f"  {'costo modello':22} {cost(total):>14.2f} $")
    if calls:
        share = cost(total_advisor) / (cost(total) + cost(total_advisor))
        print(f"  {'costo advisor':22} {cost(total_advisor):>14.2f} $"
              f"   {calls} chiamate, {share:.0%} del totale")
    print(f"  {'costo totale':22} {cost(total) + cost(total_advisor):>14.2f} $")
    if articles:
        unit = (cost(total) + cost(total_advisor)) / articles
        print(f"\n  per articolo ({articles})       {unit:>14.2f} $")


# ---------------------------------------------------------------- sessioni

def message_text(message: dict) -> str:
    """Il testo di un messaggio, inclusi gli argomenti delle chiamate a tool.

    Il `run_id` compare quasi sempre dentro un comando bash, non nella prosa:
    per questo i blocchi `tool_use` contano quanto il testo.
    """
    content = message.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            parts.append(block.get("text") or "")
        elif block.get("type") == "tool_use":
            parts.append(json.dumps(block.get("input") or {})[:2000])
    return "\n".join(parts)


def read_session(path: str) -> dict | None:
    """Somma l'uso e raccoglie i run_id di una sessione. None se non consuma.

    Stesso contratto del modo workflow: un record per `requestId`, e l'advisor
    contato a parte invece che perso.
    """
    model, advisor = zero(), zero()
    runs: set[str] = set()
    first = ""
    rows = turns(path)
    for row in rows:
        add(model, row["model"])
        add(advisor, row["advisor"])
        record = row["record"]
        stamp = record.get("timestamp") or ""
        if stamp and (not first or stamp < first):
            first = stamp
        runs.update(hit.group(0)
                    for hit in RUN_ID.finditer(message_text(record.get("message") or {})))
    # I run_id compaiono anche nei messaggi utente, che non hanno `usage`.
    with open(path, errors="replace") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if record.get("type") == "user":
                runs.update(hit.group(0) for hit in
                            RUN_ID.finditer(message_text(record.get("message") or {})))
    if not any(model.values()) and not any(advisor.values()):
        return None
    return {"day": first[:10], "runs": sorted(runs), "use": model,
            "advisor": advisor, "turns": len(rows),
            "sid": os.path.basename(path)[:8]}


def writing_only(runs) -> list:
    return [r for r in runs if not r.split("-2026")[0] in NOT_WRITING]


def collect(since: str) -> list:
    sessions = []
    for root in glob.glob(os.path.expanduser(PROJECTS)):
        for path in glob.glob(os.path.join(root, "*.jsonl")):
            session = read_session(path)
            if session and session["day"] >= since:
                sessions.append(session)
    sessions.sort(key=lambda s: s["day"])
    return sessions


def report(sessions, articles: int) -> None:
    chain = [s for s in sessions if s["runs"]]
    writing = [s for s in chain if writing_only(s["runs"])]

    print("SESSIONI CON ALMENO UNA RUN DELLA CATENA\n")
    print(f"{'giorno':11} {'sid':9} {'run':40} {'turni':>6} {'cache lett':>13} "
          f"{'output':>9} {'$':>7}")
    for session in chain:
        use = session["use"]
        label = ", ".join(r.split("-2026")[0] for r in session["runs"])[:40]
        print(f"{session['day']:11} {session['sid']:9} {label:40} "
              f"{session['turns']:6} {use['cache_r']:13,} {use['out']:9,} "
              f"{cost(use) + cost(session['advisor']):7.2f}")

    total, advisor = zero(), zero()
    for session in writing:
        add(total, session["use"])
        add(advisor, session["advisor"])
    n_runs = sum(len(writing_only(s["runs"])) for s in writing)
    print(f"\nSESSIONI CHE PRODUCONO PROSA: {len(writing)}, {n_runs} run")
    for field, label in (("in", "input non in cache"), ("cache_w", "scrittura di cache"),
                         ("cache_r", "lettura di cache"), ("out", "output")):
        extra = f"  (+{advisor[field]:,} advisor)" if advisor[field] else ""
        print(f"  {label:22} {total[field]:>15,}{extra}")
    print(f"  {'turni':22} {sum(s['turns'] for s in writing):>15,}")
    full = cost(total) + cost(advisor)
    print(f"  {'costo indicativo':22} {full:>14.2f} $")

    if not total["out"]:
        return
    print(f"\n  lettura di cache / output   {total['cache_r'] / total['out']:>8.0f} a 1")
    if n_runs:
        print(f"  per run                     {full / n_runs:>8.2f} $")
    if articles:
        prose = articles * 1500  # ~750 parole, ~2 token per parola
        print(f"  per articolo ({articles} firmati)  {full / articles:>8.2f} $")
        print(f"  output per articolo         {total['out'] // articles:>8,} token")
        print(f"  output / prosa pubblicata   {total['out'] / prose:>8.0f} a 1")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--since", default="2026-01-01",
                        help="considera solo le sessioni da questa data (YYYY-MM-DD)")
    parser.add_argument("--articles", type=int, default=0,
                        help="articoli firmati nella finestra, per il costo unitario")
    parser.add_argument("--workflow", default=None,
                        help="misura una run del workflow: id wf_* o percorso")
    args = parser.parse_args(argv)

    if args.workflow:
        directories = find_workflow(args.workflow)
        if not directories:
            print(f"nessuna run {args.workflow} sotto {PROJECTS}", file=sys.stderr)
            return 1
        report_workflow(directories, args.articles)
        return 0

    sessions = collect(args.since)
    if not sessions:
        print(f"nessuna sessione in {PROJECTS} dal {args.since}", file=sys.stderr)
        return 1
    report(sessions, args.articles)
    return 0


if __name__ == "__main__":
    sys.exit(main())
