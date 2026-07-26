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

# L'identita' del progetto, la stessa di frontend/src/styles.css. Un cruscotto
# che sembra un altro prodotto si legge come un altro prodotto.
CSS = """
:root { --ink:#15233b; --paper:#fbfaf7; --accent:#e4572e; --line:rgba(21,35,59,.16); --muted:#5a6779; }
* { box-sizing:border-box; }
body { margin:0; padding:2rem 1.25rem 4rem; background:var(--paper); color:var(--ink);
  font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; line-height:1.55; }
.wrap { max-width:60rem; margin:0 auto; }
h1 { font-family:Archivo,Inter,sans-serif; font-size:1.9rem; letter-spacing:-.02em; margin:0 0 .25rem; }
h2 { font-family:Archivo,Inter,sans-serif; font-size:1.15rem; margin:2.5rem 0 .75rem;
  padding-bottom:.4rem; border-bottom:1px solid var(--line); }
.sub { color:var(--muted); font-size:.9rem; margin:0 0 1.5rem; }
.mono { font-family:"Space Mono",ui-monospace,SFMono-Regular,Menlo,monospace; }
table { width:100%; border-collapse:collapse; font-size:.92rem; }
th { text-align:left; font-weight:600; font-size:.75rem; letter-spacing:.06em; text-transform:uppercase;
  color:var(--muted); padding:.5rem .6rem; border-bottom:1px solid var(--line); }
td { padding:.55rem .6rem; border-bottom:1px solid var(--line); vertical-align:top; }
tr:last-child td { border-bottom:0; }
.n { font-family:"Space Mono",ui-monospace,monospace; text-align:right; white-space:nowrap; }
.dot { display:inline-block; width:.55rem; height:.55rem; border-radius:0; margin-right:.5rem;
  background:var(--line); vertical-align:middle; }
.dot.work { background:var(--accent); }
.tag { display:inline-block; padding:.1rem .45rem; border:1px solid var(--line);
  font-size:.72rem; letter-spacing:.04em; text-transform:uppercase; white-space:nowrap; }
.tag.bad { border-color:var(--accent); color:var(--accent); }
.detail { color:var(--muted); font-size:.86rem; margin:.35rem 0 0; padding-left:1rem;
  border-left:2px solid var(--line); }
a { color:var(--accent); }
.empty { color:var(--muted); font-style:italic; padding:.8rem 0; }
.scroll { overflow-x:auto; }
footer { margin-top:3rem; padding-top:1rem; border-top:1px solid var(--line);
  color:var(--muted); font-size:.82rem; }
@media (prefers-color-scheme: dark) {
  :root { --ink:#eceff4; --paper:#101725; --line:rgba(236,239,244,.16); --muted:#9aa6b8; }
}
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

    owned = {path for paths in pipeline_gate.STAGE_PATHS.values() for path in paths}
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
        if not touched or not touched <= owned:
            continue
        commit["stages"] = sorted({
            stage for stage, paths in pipeline_gate.STAGE_PATHS.items()
            if touched <= set(paths)
        })
        out_rows.append(commit)
        if len(out_rows) >= limit:
            break
    return out_rows


def open_pull_requests():
    """Le PR della catena, se `gh` c'e'. Senza, la sezione lo dice e basta."""
    result = subprocess.run(
        ["gh", "pr", "list", "-R", REPO, "--state", "all", "--limit", "10",
         "--json", "number,title,state,headRefName,createdAt"],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True,
    )
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
    rows = []
    for entry in status["stages"]:
        dot = "dot work" if entry["waiting"] else "dot"
        rows.append(
            f"<tr><td><span class='{dot}'></span><strong>{_esc(entry['stage'])}</strong></td>"
            f"<td class='mono'>{_esc(entry['agent'])}</td>"
            f"<td class='n'>{entry['waiting']}</td>"
            f"<td>{_esc(entry['next'])}</td></tr>"
        )
    return "\n".join(rows)


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
    entries = pipeline_log.read_journal()
    commits = recent_chain_commits()
    prs = open_pull_requests()

    if status["next_stage"]:
        first = next(e for e in status["stages"] if e["stage"] == status["next_stage"])
        headline = f"Prossimo passo: <strong>{_esc(first['agent'])}</strong>, {_esc(first['next'])}."
    else:
        headline = ("Niente in coda: la catena e ferma perche ha finito, "
                    "non perche e bloccata.")

    generated = pipeline_log._now().replace("T", " ")[:16]
    page = f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Catena Divario Italia</title>
<style>{CSS}</style></head><body><div class="wrap">
<h1>Catena Divario Italia</h1>
<p class="sub">{headline} Generato il {_esc(generated)} UTC.</p>

<h2>Dove sta la catena adesso</h2>
<div class="scroll"><table>
<tr><th>stadio</th><th>agente</th><th class="n">in attesa</th><th>prossima cosa da fare</th></tr>
{_stage_rows(status)}
</table></div>

<h2>Che cosa hanno fatto gli agenti</h2>
{_journal_rows(entries)}

<h2>Che cosa e finito in pagina</h2>
{_commit_rows(commits)}

<h2>Pull request della catena</h2>
{_pr_rows(prs)}

<footer>
Rigenera con <span class="mono">python3 scripts/pipeline_dashboard.py --open</span>.
Questa pagina e una fotografia: mostra lo stato del checkout locale al momento in
cui e stata scritta. Per lo stato vivo di una Routine in corso serve
<a href="https://claude.ai/code/routines">claude.ai/code/routines</a>.
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
