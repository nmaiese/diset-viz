#!/usr/bin/env python3
"""Il cruscotto della catena: una pagina sola, tutto quello che gli agenti fanno.

Nasce da una richiesta precisa: poter guardare la catena senza aprire file e
senza ricordarsi sei comandi. Mette insieme le tre cose che oggi stanno in tre
posti diversi:

- **dove si e' fermata**, cioe' la coda di ogni stadio (`pipeline_status`),
- **che cosa hanno fatto gli agenti**, cioe' il diario delle run
  (`pipeline_log`), incluse le run che non hanno prodotto niente,
- **che cosa e' finito in pagina**, cioe' i commit e le pull request che la
  catena ha generato (git, e `gh` se c'e').

Una pagina HTML autonoma, senza rete e senza dipendenze: si apre da file, anche
offline, e si rigenera in un secondo.

    python3 scripts/pipeline_dashboard.py            # scrive e stampa il file://
    python3 scripts/pipeline_dashboard.py --open     # e lo apre nel browser
    python3 scripts/pipeline_dashboard.py --out /tmp/catena.html

Stdlib puro come il resto della catena, cosi' gira anche in un agente cloud
prima che esista il venv. Le due code che hanno bisogno del view model degradano
da sole, come in `pipeline_status`.
"""

from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import pipeline_log, pipeline_status  # noqa: E402

DEFAULT_OUT = PROJECT_ROOT / "data" / "pipeline" / "cruscotto.html"
REPO = "nmaiese/diset-viz"

# L'identita' cartografica del progetto (CLAUDE.md): navy, carta, un solo accento.
# Un cruscotto che sembra un altro prodotto si legge come un altro prodotto.
#
# I font veri del sito (Archivo, Inter, Space Mono) arrivano da Google Fonts, che
# qui non si puo' caricare: la pagina deve restare autonoma e apribile offline.
# Quindi uno stack di sistema scelto, non un fallback silenzioso.
#
# I colori stanno tutti in token su :root e vengono ridefiniti tre volte: dal
# sistema, e poi da data-theme nelle due direzioni, perche' l'interruttore di chi
# guarda deve poter vincere anche contro la preferenza del sistema.
CSS = """
:root {
  --paper:#fbfaf7; --ink:#15233b; --accent:#e4572e;
  --muted:#5a6779; --line:rgba(21,35,59,.16); --sunk:rgba(21,35,59,.035);
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
}
@media (prefers-color-scheme: dark) {
  :root { --paper:#0e1522; --ink:#e9edf4; --accent:#ff7a52;
          --muted:#94a1b5; --line:rgba(233,237,244,.18); --sunk:rgba(233,237,244,.04); }
}
:root[data-theme="dark"] { --paper:#0e1522; --ink:#e9edf4; --accent:#ff7a52;
  --muted:#94a1b5; --line:rgba(233,237,244,.18); --sunk:rgba(233,237,244,.04); }
:root[data-theme="light"] { --paper:#fbfaf7; --ink:#15233b; --accent:#e4572e;
  --muted:#5a6779; --line:rgba(21,35,59,.16); --sunk:rgba(21,35,59,.035); }

* { box-sizing:border-box; }
body { margin:0; padding:2.5rem 1.25rem 4rem; background:var(--paper); color:var(--ink);
  font-family:var(--sans); line-height:1.55; -webkit-font-smoothing:antialiased; }
.wrap { max-width:62rem; margin:0 auto; display:flex; flex-direction:column; gap:2.5rem; }
header { display:flex; flex-direction:column; gap:.6rem; }
h1 { font-size:1.75rem; font-weight:700; letter-spacing:-.02em; margin:0; text-wrap:balance; }
h2 { font-size:.78rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase;
  color:var(--muted); margin:0 0 .75rem; }
section { display:flex; flex-direction:column; }
.lede { margin:0; font-size:1rem; color:var(--ink); max-width:52ch; }
.lede strong { color:var(--accent); }
.stamp { margin:0; font-family:var(--mono); font-size:.75rem; color:var(--muted); }

.strip { display:grid; grid-template-columns:repeat(auto-fit,minmax(9rem,1fr)); gap:1px;
  background:var(--line); border:1px solid var(--line); }
.cell { background:var(--paper); padding:.9rem 1rem; display:flex; flex-direction:column; gap:.2rem; }
.cell .k { font-size:.68rem; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
.cell .v { font-family:var(--mono); font-size:1.5rem; font-variant-numeric:tabular-nums;
  line-height:1.1; }
.cell.alert .v { color:var(--accent); }

table { width:100%; border-collapse:collapse; font-size:.92rem; }
th { text-align:left; font-weight:600; font-size:.68rem; letter-spacing:.08em; text-transform:uppercase;
  color:var(--muted); padding:.45rem .7rem; border-bottom:1px solid var(--line); white-space:nowrap; }
td { padding:.6rem .7rem; border-bottom:1px solid var(--line); vertical-align:top; }
tbody tr:last-child td { border-bottom:0; }
tbody tr.idle td { color:var(--muted); }
tbody tr.flag td:first-child { box-shadow:inset 3px 0 0 var(--accent); }
.n { font-family:var(--mono); text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
.mono { font-family:var(--mono); font-size:.85em; }
.tag { display:inline-block; padding:.12rem .5rem; border:1px solid var(--line); background:var(--sunk);
  font-family:var(--mono); font-size:.7rem; letter-spacing:.03em; white-space:nowrap; }
.tag.bad { border-color:var(--accent); color:var(--accent); background:transparent; }
.detail { color:var(--muted); font-size:.85rem; margin:.3rem 0 0; padding-left:.8rem;
  border-left:2px solid var(--line); }
a { color:var(--accent); text-underline-offset:.15em; }
a:focus-visible, summary:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
.empty { color:var(--muted); font-size:.9rem; margin:0; padding:.9rem 0; }
.scroll { overflow-x:auto; }
footer { border-top:1px solid var(--line); padding-top:1rem; color:var(--muted); font-size:.8rem;
  display:flex; flex-direction:column; gap:.4rem; }
"""


def _git(*args):
    result = subprocess.run(("git",) + args, cwd=str(PROJECT_ROOT),
                            capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def recent_chain_commits(limit=12):
    """I commit che la catena ha prodotto, riconosciuti dai file che toccano.

    Non dai messaggi ne' dagli autori: un agente puo' scrivere qualunque
    messaggio, ma non puo' uscire dal proprio perimetro senza che il cancello lo
    fermi. I file sono quindi la firma piu' affidabile che abbiamo.
    """
    from scripts import pipeline_gate

    owned = tuple({path for paths in pipeline_gate.STAGE_PATHS.values() for path in paths})
    code, out, _ = _git("log", f"-{limit * 6}", "--format=%h%x1f%cI%x1f%s", "--name-only")
    if code != 0:
        return []
    # Parsed by "a line with the separator starts a commit, anything else is one
    # of its files". The obvious block-splitting version is wrong: `--name-only`
    # puts a blank line *between* the header and the files as well as between
    # commits, so a blank-line delimiter cuts every commit in two and the second
    # half has a filename where the header should be.
    commits = []
    current = None
    for line in out.splitlines():
        if "\x1f" in line:
            sha, when, subject = line.split("\x1f", 2)
            current = {"sha": sha, "at": when[:16].replace("T", " "),
                       "subject": subject, "files": []}
            commits.append(current)
        elif line.strip() and current is not None:
            current["files"].append(line.strip())

    out_rows = []
    for commit in commits:
        touched = set(commit["files"])
        # `path_allowed` e non l'appartenenza a un insieme: da quando i registri
        # sono store a un file per record, un perimetro puo' essere una
        # directory, e confrontare i percorsi uno a uno non riconoscerebbe piu'
        # nessun commit della catena.
        if not touched or not all(pipeline_gate.path_allowed(p, owned) for p in touched):
            continue
        commit["stages"] = sorted({
            stage for stage, paths in pipeline_gate.STAGE_PATHS.items()
            if all(pipeline_gate.path_allowed(p, paths) for p in touched)
        })
        out_rows.append(commit)
        if len(out_rows) >= limit:
            break
    return out_rows


def open_pull_requests():
    """Le PR della catena, se `gh` c'e'. Senza, la sezione lo dice e basta.

    `gh` puo' mancare del tutto: la web app usa il GitHub MCP e non installa la
    CLI, e allora `subprocess.run` solleva FileNotFoundError prima ancora di
    arrivare al controllo del returncode. Va trattato come "gh non c'e'", non
    come un crash: il cruscotto deve leggere senza rompersi anche quando l'unica
    cosa assente e' l'elenco delle PR (lo pretende TheDashboardReadsWithoutBreaking)."""
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "-R", REPO, "--state", "all", "--limit", "10",
             "--json", "number,title,state,headRefName,createdAt"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True,
        )
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    try:
        rows = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    return [r for r in rows if r.get("headRefName", "").startswith("automation/")]


def _esc(value):
    return html.escape(str(value if value is not None else ""))


def _stage_rows(status):
    """Lo stato incide nella forma, non solo nel numero: una riga con lavoro in
    coda porta una barretta d'accento, una a zero si spegne nel colore attenuato.
    Un cruscotto si scorre, non si legge."""
    rows = []
    for entry in status["stages"]:
        # `None` non e' zero: una coda che nessuno ha contato si accende come
        # quelle piene, perche' "non lo so" e' un motivo per guardare, non per
        # spegnere la riga.
        waiting = entry["waiting"]
        css = "idle" if waiting == 0 else "flag"
        shown = "?" if waiting is None else str(waiting)
        rows.append(
            f"<tr class='{css}'><td><strong>{_esc(entry['stage'])}</strong></td>"
            f"<td class='mono'>{_esc(entry['agent'])}</td>"
            f"<td class='n'>{_esc(shown)}</td>"
            f"<td>{_esc(entry['next'])}</td></tr>"
        )
    return "\n".join(rows)


def _summary_cells(status, entries, queues=None):
    """Il riassunto prima del dettaglio. Quattro numeri che dicono, in un colpo
    d'occhio, se c'e' qualcosa da guardare o no."""
    attention = sum(1 for e in entries if e.get("outcome") in pipeline_log.ATTENTION)
    last = max((e.get("at", "") for e in entries), default="")
    late = [r for r in pipeline_log.silence(entries, queues=queues) if r["stale"]]
    # Il totale non puo' portare l'etichetta "tutti gli stadi" quando uno stadio
    # non e' stato contato: sarebbe lo zero silenzioso della riga di stadio
    # spostato nel numero piu' grande della pagina, cioe' l'unico che si legge
    # davvero in un colpo d'occhio. Quando manca un termine, la somma lo dice e
    # si accende, perche' un totale parziale spacciato per completo e' peggio di
    # nessun totale.
    unknown = status.get("unknown_stages") or []
    if unknown:
        coda_label = f"in coda, senza {', '.join(unknown)}"
        coda_value = f"{status['total_waiting']}+?"
    else:
        coda_label, coda_value = "in coda, tutti gli stadi", str(status["total_waiting"])
    cells = [
        (coda_label, coda_value, bool(unknown)),
        ("run registrate", str(len(entries)), False),
        ("run da guardare", str(attention), attention > 0),
        # Il silenzio non entra fra le "run da guardare" perche' non e' una run:
        # e' l'assenza di una run, ed e' il modo di fallire che non lascia tracce.
        ("stadi fermi", str(len(late)), bool(late)),
        ("ultima run", (last[:10] or "mai"), False),
    ]
    return "\n".join(
        f"<div class='cell{' alert' if alert else ''}'>"
        f"<span class='k'>{_esc(k)}</span><span class='v'>{_esc(v)}</span></div>"
        for k, v, alert in cells
    )


def _journal_rows(entries, limit=25):
    if not entries:
        return ("<p class='empty'>Nessuna run registrata. Il diario si riempie da solo: "
                "ogni agente ci scrive una riga a fine run, anche quando non ha "
                "prodotto niente.</p>")
    shown = sorted(entries, key=lambda r: r.get("at", ""), reverse=True)[:limit]
    rows = []
    for entry in shown:
        outcome = entry.get("outcome", "?")
        css = "tag bad" if outcome in pipeline_log.ATTENTION else "tag"
        label = pipeline_log.OUTCOMES.get(outcome, outcome)
        detail = "".join(
            f"<p class='detail'>{_esc(line)}</p>" for line in (entry.get("detail") or [])
        )
        refs = []
        if entry.get("pr"):
            refs.append(f"<a href='https://github.com/{REPO}/pull/{_esc(entry['pr'])}'>PR #{_esc(entry['pr'])}</a>")
        if entry.get("gate"):
            refs.append(f"cancello: {_esc(entry['gate'])}")
        if entry.get("commit"):
            refs.append(f"<span class='mono'>{_esc(entry['commit'])}</span>")
        rows.append(
            f"<tr><td class='mono'>{_esc((entry.get('at') or '')[:16].replace('T', ' '))}</td>"
            f"<td><strong>{_esc(entry.get('stage'))}</strong></td>"
            f"<td><span class='{css}'>{_esc(label)}</span></td>"
            f"<td>{_esc(entry.get('summary'))}{detail}"
            f"<p class='detail'>{' | '.join(refs)}</p></td></tr>"
        )
    return ("<div class='scroll'><table><tr><th>quando</th><th>stadio</th><th>esito</th>"
            "<th>che cosa ha fatto</th></tr>" + "\n".join(rows) + "</table></div>")


def _stage_metric_rows(entries):
    """L'aggregato per stadio: quante run, quante da guardare, quanto durano,
    con quale modello. I campi di provenienza sono best-effort nel diario,
    quindi qui una colonna vuota significa "le run vecchie non li avevano",
    non un errore: la tabella diventa piu' piena a ogni run nuova.
    """
    if not entries:
        return "<p class='empty'>Nessuna run registrata, quindi niente da aggregare.</p>"
    by_stage = {}
    for entry in entries:
        by_stage.setdefault(entry.get("stage") or "?", []).append(entry)
    rows = []
    for stage in [s for s in pipeline_log.STAGES if s in by_stage]:
        runs = by_stage[stage]
        attention = sum(1 for r in runs if r.get("outcome") in pipeline_log.ATTENTION)
        durations = [r["duration_seconds"] for r in runs
                     if isinstance(r.get("duration_seconds"), (int, float))]
        avg = f"{sum(durations) / len(durations) / 60:.0f} min" if durations else ""
        models = sorted({r["model"] for r in runs if r.get("model")})
        last = max(runs, key=lambda r: r.get("at") or "")
        rows.append(
            f"<tr><td><strong>{_esc(stage)}</strong></td>"
            f"<td class='n'>{len(runs)}</td>"
            f"<td class='n'>{attention or ''}</td>"
            f"<td class='n'>{_esc(avg)}</td>"
            f"<td>{_esc(', '.join(models))}</td>"
            f"<td class='mono'>{_esc((last.get('at') or '')[:10])}</td></tr>"
        )
    return ("<div class='scroll'><table><tr><th>stadio</th><th class='n'>run</th>"
            "<th class='n'>da guardare</th><th class='n'>durata media</th>"
            "<th>modello</th><th>ultima</th></tr>" + "\n".join(rows) + "</table></div>")


def _commit_rows(commits):
    if not commits:
        return "<p class='empty'>Nessun commit della catena nella storia recente.</p>"
    rows = []
    for c in commits:
        stages = ", ".join(c["stages"]) or "?"
        rows.append(
            f"<tr><td class='mono'>{_esc(c['at'])}</td>"
            f"<td class='mono'><a href='https://github.com/{REPO}/commit/{_esc(c['sha'])}'>{_esc(c['sha'])}</a></td>"
            f"<td>{_esc(stages)}</td>"
            f"<td>{_esc(c['subject'])}<p class='detail'>{_esc(', '.join(c['files']))}</p></td></tr>"
        )
    return ("<div class='scroll'><table><tr><th>quando</th><th>commit</th><th>stadio</th>"
            "<th>che cosa e' cambiato</th></tr>" + "\n".join(rows) + "</table></div>")


def _pr_rows(prs):
    if prs is None:
        return "<p class='empty'>`gh` non e' disponibile qui, quindi le pull request non sono elencate.</p>"
    if not prs:
        return "<p class='empty'>Nessuna pull request aperta dalla catena.</p>"
    rows = []
    for pr in prs:
        rows.append(
            f"<tr><td class='mono'>{_esc(pr.get('createdAt', '')[:16].replace('T', ' '))}</td>"
            f"<td><a href='https://github.com/{REPO}/pull/{pr['number']}'>#{pr['number']}</a></td>"
            f"<td><span class='tag'>{_esc(pr.get('state'))}</span></td>"
            f"<td>{_esc(pr.get('title'))}<p class='detail mono'>{_esc(pr.get('headRefName'))}</p></td></tr>"
        )
    return ("<div class='scroll'><table><tr><th>quando</th><th>PR</th><th>stato</th>"
            "<th>titolo</th></tr>" + "\n".join(rows) + "</table></div>")


def render(out_path=None):
    status = pipeline_status.build_status()
    # Collassate: una run che apre una pull request lascia due righe, la propria
    # e quella del passo di merge, e contarle come due gonfia "run registrate"
    # solo per gli stadi che lavorano.
    entries = pipeline_log.collapse_runs(pipeline_log.read_journal())
    commits = recent_chain_commits()
    prs = open_pull_requests()

    if status["next_stage"]:
        first = next(e for e in status["stages"] if e["stage"] == status["next_stage"])
        headline = f"Tocca a <strong>{_esc(first['agent'])}</strong>: {_esc(first['next'])}."
    else:
        headline = ("Niente in coda: la catena e ferma perche ha finito, "
                    "non perche e bloccata.")

    # Il battito del dispatcher, prima di tutto il resto. E' l'unico segnale che
    # distingue "nessuno stadio aveva lavoro" da "non e' partito niente": da
    # quando il lavoro lo assegna lui, il silenzio di un singolo stadio e' una
    # risposta legittima, il suo no.
    ticks = [e for e in entries if e.get("stage") == "dispatch"]
    if ticks:
        last_tick = max(ticks, key=lambda e: e.get("at") or "")
        headline += (f" Ultimo giro del dispatch: "
                     f"{_esc((last_tick.get('at') or '')[:16].replace('T', ' '))}.")
    else:
        headline += (" Il <strong>dispatch</strong> non ha mai registrato un giro: "
                     "finche' non lo fa, nessuno assegna il lavoro.")

    # Un avviso sopra tutto il resto, perche' uno stadio fermo non si vede in
    # nessuna delle tabelle sotto: quelle mostrano cio' che e' successo, e qui il
    # problema e' che non e' successo niente.
    # Le code arrivano dallo `status` gia' calcolato, non da una seconda
    # `queue_sizes()`. Quella ricostruirebbe la vista di ogni indicatore del
    # catalogo una seconda volta, che e' lavoro inutile e per giunta il punto
    # esatto in cui la suite va in segfault una run su venticinque (vedi
    # `pipeline_gate.check_suite`): raddoppiare quel passaggio raddoppierebbe
    # la probabilita' di far morire il cruscotto a meta'.
    queues = {entry["stage"]: entry["waiting"] for entry in status["stages"]}
    late = [r for r in pipeline_log.silence(entries, queues=queues) if r["stale"]]
    if late:
        detail = ", ".join(
            f"{r['group']} ({r['days_since']:.0f} giorni, atteso ogni {r['expected_days']})"
            for r in late
        )
        headline += (f" <strong>Fermi: {_esc(detail)}.</strong> "
                     "Una Routine che smette di partire non lascia nessuna traccia.")

    generated = pipeline_log._now().replace("T", " ")[:16]
    page = f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Catena Divario Italia</title>
<style>{CSS}</style></head><body><div class="wrap">

<header>
<h1>Catena Divario Italia</h1>
<p class="lede">{headline}</p>
<p class="stamp">fotografia del {_esc(generated)} UTC</p>
</header>

<section>
<div class="strip">{_summary_cells(status, entries, queues)}</div>
</section>

<section>
<h2>Dove sta la catena</h2>
<div class="scroll"><table>
<thead><tr><th>stadio</th><th>agente</th><th class="n">in coda</th><th>prossima cosa da fare</th></tr></thead>
<tbody>
{_stage_rows(status)}
</tbody></table></div>
</section>

<section>
<h2>Che cosa hanno fatto gli agenti</h2>
{_journal_rows(entries)}
</section>

<section>
<h2>Gli stadi, in aggregato</h2>
{_stage_metric_rows(entries)}
</section>

<section>
<h2>Che cosa e finito in pagina</h2>
{_commit_rows(commits)}
</section>

<section>
<h2>Pull request della catena</h2>
{_pr_rows(prs)}
</section>

<footer>
<span>Rigenera con <span class="mono">python3 scripts/pipeline_dashboard.py --open</span>.</span>
<span>Questa pagina e una fotografia del checkout locale. Per lo stato vivo di una
Routine in corso serve <a href="https://claude.ai/code/routines">claude.ai/code/routines</a>:
l'API delle Routine espone solo l'ora dell'ultimo firing.</span>
</footer>
</div></body></html>
"""
    path = Path(out_path) if out_path else DEFAULT_OUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser(description="Il cruscotto della catena, in una pagina.")
    parser.add_argument("--out", help=f"dove scriverlo (default: {DEFAULT_OUT})")
    parser.add_argument("--open", action="store_true", help="aprilo nel browser")
    args = parser.parse_args()

    path = render(args.out)
    print(f"file://{path}")
    if args.open:
        import webbrowser

        webbrowser.open(f"file://{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
