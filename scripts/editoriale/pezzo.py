"""Apre in modo uniforme un nuovo lavoro editoriale."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

import frontmatter


ROOT = Path(__file__).resolve().parents[2]
ORCA_WORKTREE = Path.home() / "dev/dev-tools/scripts/orca-worktree.sh"
STOPWORD = {
    "alla", "alle", "anche", "come", "dalla", "dalle", "degli", "della", "delle",
    "dello", "dentro", "dopo", "italia", "nelle", "nella", "nello", "perche", "prima",
    "divario", "regioni", "regione", "nord", "sud", "italiano", "dati",
    "quale", "quelli", "questo", "sono", "sulla", "sulle", "sullo", "tutte", "tutto",
}


@dataclass(frozen=True)
class TemaEsistente:
    percorso: Path
    titolo: str


def _parole(testo: str) -> set[str]:
    senza_accenti = "".join(
        carattere
        for carattere in unicodedata.normalize("NFKD", testo.casefold())
        if not unicodedata.combining(carattere)
    )
    return {
        # La famiglia scolastica non condivide il prefisso letterale con scuola.
        "scuol" if parola.startswith(("scolast", "scuol")) else parola[:5]
        for parola in re.findall(r"[a-z0-9]+", senza_accenti)
        if len(parola) >= 4 and parola not in STOPWORD
    }


def _frase_normalizzata(testo: str) -> str:
    return "-".join(re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKD", testo.casefold()).encode("ascii", "ignore").decode()))


def valida_chiave(chiave: str) -> str:
    if len(chiave) > 40:
        raise ValueError("chiave non valida: massimo 40 caratteri")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", chiave):
        raise ValueError("chiave non valida: usa solo minuscole, numeri e trattini")
    return chiave


def trova_temi_esistenti(
    chiave: str,
    titolo: str,
    posts_dir: Path,
    indicators_dir: Path,
) -> list[TemaEsistente]:
    richieste = _parole(f"{chiave} {titolo}")
    chiave_norm = _frase_normalizzata(chiave)
    trovati = []
    for directory in (Path(posts_dir), Path(indicators_dir)):
        if not directory.exists():
            continue
        for percorso in sorted(directory.glob("*.md")):
            try:
                title = frontmatter.load(percorso).get("title")
            except (OSError, UnicodeError, ValueError):
                title = None
            is_indicator = directory == Path(indicators_dir)
            if is_indicator and not title:
                continue
            titolo_file = str(title or percorso.stem)
            slug_norm = _frase_normalizzata(percorso.stem)
            slug_parole = set() if is_indicator else _parole(percorso.stem)
            titolo_parole = _parole(titolo_file)
            chiave_nello_slug = not is_indicator and bool(_parole(chiave)) and bool(re.search(rf"(?:^|-)({re.escape(chiave_norm)})(?:-|$)", slug_norm))
            # Basta una radice significativa: anche "abbandono scolastico"
            # deve segnalare un pezzo sulla scuola, senza le parole generiche.
            if richieste & slug_parole or richieste & titolo_parole or chiave_nello_slug:
                trovati.append(TemaEsistente(percorso, titolo_file))
    return trovati


def corpo_issue(tipo: str, chiave: str, firma: str) -> str:
    return (
        f"Tipo: {tipo}\nChiave: `{chiave}`\n\n"
        "Consegna in una PR draft, con controlli e fonti previsti dal progetto. "
        "Seguire `docs/WORKFLOW_ORCA.md`."
        + (f"\n\n— {firma}" if firma else "")
    )


def corpo_pr(issue: int, tipo: str, chiave: str, firma: str) -> str:
    return (
        f"Apre il lavoro editoriale `{chiave}` di tipo `{tipo}`.\n\nCloses #{issue}"
        + (f"\n\n— {firma}" if firma else "")
    )


def identita_agente() -> str:
    return os.environ.get("AGENT_ID", "").strip()


def contenuto_brief(titolo: str, tipo: str, issue: int, simili: Sequence[TemaEsistente]) -> str:
    righe_simili = [f"- `{tema.percorso}`: {tema.titolo}" for tema in simili]
    if not righe_simili:
        righe_simili = ["- Nessuno."]
    return (
        f"# {titolo}\n\n"
        f"Tipo: {tipo}\n\n"
        f"Issue: #{issue}\n\n"
        "## File simili\n\n"
        + "\n".join(righe_simili)
        + "\n\n## Regole\n\n"
        "Seguire `content/STYLE.md`. Articolo di dati: 700-1100 parole. "
        "Analisi lunga: 1400-2000 parole.\n"
    )


def esegui(cmd: Sequence[str]) -> str:
    return subprocess.check_output(list(cmd), cwd=ROOT, text=True, stderr=subprocess.PIPE)


def _esiste_ramo(cmd: Sequence[str], esegui_fn: Callable[[Sequence[str]], str]) -> bool:
    try:
        output = esegui_fn(cmd)
    except subprocess.CalledProcessError as error:
        if error.returncode == 1 and cmd[1] == "show-ref":
            return False
        raise
    return cmd[1] == "show-ref" or bool(output.strip())


def _numero_issue(output: str) -> int:
    match = re.search(r"/issues/(\d+)\b", output.strip())
    if not match:
        raise ValueError("GitHub non ha restituito il numero della issue")
    return int(match.group(1))


def _ultimo_percorso(output: str) -> Path:
    for line in reversed(output.splitlines()):
        candidate = Path(line.strip())
        if line.strip() and candidate.is_dir():
            return candidate
    raise ValueError("Orca non ha restituito un percorso worktree esistente")


class ParserItaliano(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"Errore: argomenti non validi: {message}", file=sys.stderr)
        raise SystemExit(2)


def _parser() -> argparse.ArgumentParser:
    parser = ParserItaliano(description=__doc__)
    sub = parser.add_subparsers(dest="comando", required=True)
    apri = sub.add_parser("apri")
    apri.add_argument("tipo", choices=("blog", "team"))
    apri.add_argument("chiave")
    apri.add_argument("--titolo", required=True)
    apri.add_argument("--prova", action="store_true")
    apri.add_argument("--forza-tema-esistente", action="store_true")
    return parser


def _mostra_simili(simili: Sequence[TemaEsistente], root: Path) -> None:
    for tema in simili:
        try:
            percorso = tema.percorso.relative_to(root)
        except ValueError:
            percorso = tema.percorso
        print(f"- {percorso}: {tema.titolo}")


def main(
    argv: Sequence[str] | None = None,
    *,
    esegui_fn: Callable[[Sequence[str]], str] = esegui,
    root: Path = ROOT,
) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as error:
        return int(error.code)

    resources: list[str] = []
    step = "controlli preliminari"
    try:
        valida_chiave(args.chiave)
        posts = root / "content/posts"
        indicators = root / "content/indicators"
        simili = trova_temi_esistenti(args.chiave, args.titolo, posts, indicators)
        if simili:
            print("Tema già presente nei file:")
            _mostra_simili(simili, root)
            if not args.forza_tema_esistente:
                print("Apertura interrotta. Usa --forza-tema-esistente solo dopo avere verificato i file.")
                return 3

        if args.prova:
            print(f"Creerei l'issue con label run:{args.tipo}.")
            print(f"Creerei worktree divario-{args.chiave} e ramo divario/{args.chiave}.")
            print(f"Creerei lavoro/{args.chiave}/, commit, push e PR draft.")
            return 0

        ramo = f"divario/{args.chiave}"
        if _esiste_ramo(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{ramo}"], esegui_fn):
            raise RuntimeError(f"il ramo locale {ramo} esiste già")
        if _esiste_ramo(
            ["git", "ls-remote", "--heads", "origin", f"refs/heads/{ramo}"], esegui_fn
        ):
            raise RuntimeError(f"il ramo remoto {ramo} esiste già")
        lavoro_root = root / "lavoro" / args.chiave
        if lavoro_root.exists():
            raise RuntimeError(f"la cartella lavoro/{args.chiave} esiste già")

        worktree_name = f"divario-{args.chiave}"
        listed = esegui_fn(["git", "worktree", "list", "--porcelain", "-z"])
        if any(
            entry.startswith("worktree ") and Path(entry[9:]).name == worktree_name
            for entry in listed.split("\0")
        ):
            raise RuntimeError(f"il worktree {worktree_name} esiste già")
        step = "aggiornamento origin/master"
        esegui_fn(["git", "fetch", "origin", "master"])
        print("Riferimento origin/master aggiornato.", flush=True)

        label = f"run:{args.tipo}"
        firma = identita_agente()
        step = "ricerca issue"
        candidates = json.loads(esegui_fn([
            "gh", "issue", "list", "--search", args.titolo,
            "--state", "open", "--json", "number,title",
        ]))
        issue = next((item["number"] for item in candidates if item["title"] == args.titolo), None)
        if issue is None:
            step = "creazione issue"
            issue_output = esegui_fn(
                [
                    "gh", "issue", "create", "--title", args.titolo, "--label", label,
                    "--body", corpo_issue(args.tipo, args.chiave, firma),
                ]
            )
            issue = _numero_issue(issue_output)
            print(f"Issue #{issue} creata.", flush=True)
        else:
            print(f"Issue #{issue} riusata.", flush=True)
        resources.append(f"Issue #{issue} aperta: riusala oppure chiudila manualmente con gh issue close {issue}.")
        step = "creazione worktree"
        worktree_output = esegui_fn([str(ORCA_WORKTREE), worktree_name, "--base-branch", "master"])
        worktree = _ultimo_percorso(worktree_output)
        resources.append(f"Worktree {worktree}: conservalo per riprendere il lavoro.")
        print(f"Worktree {worktree} creato.", flush=True)
        step = "creazione ramo"
        esegui_fn(["git", "-C", str(worktree), "switch", "-c", ramo, "origin/master"])

        resources.append(f"Ramo {ramo}: riprendi da questo ramo nel worktree indicato.")
        print(f"Ramo {ramo} creato.", flush=True)
        step = "scrittura file"
        cartella = worktree / "lavoro" / args.chiave
        cartella.mkdir(parents=True)
        resources.append(f"Cartella {cartella}: verifica i file prima di riprendere.")
        print(f"Cartella {cartella} creata.", flush=True)
        (cartella / "brief.md").write_text(
            contenuto_brief(args.titolo, args.tipo, issue, simili), encoding="utf-8"
        )
        print(f"File {cartella / 'brief.md'} creato.", flush=True)
        (cartella / "numeri.md").write_text("# Numeri\n", encoding="utf-8")
        print(f"File {cartella / 'numeri.md'} creato.", flush=True)
        (cartella / "fonti.md").write_text("# Fonti\n", encoding="utf-8")

        print(f"File {cartella / 'fonti.md'} creato.", flush=True)
        step = "git add"
        esegui_fn(["git", "-C", str(worktree), "add", "-f", f"lavoro/{args.chiave}"])
        print(f"File di {cartella} aggiunti all'indice.", flush=True)
        step = "commit"
        esegui_fn(
            ["git", "-C", str(worktree), "commit", "-m", f"Apre il lavoro editoriale su {args.titolo}"]
        )
        resources.append(f"Commit creato sul ramo {ramo}.")
        print(f"Commit creato sul ramo {ramo}.", flush=True)
        step = "push"
        esegui_fn(["git", "-C", str(worktree), "push", "-u", "origin", ramo])
        resources.append(f"Ramo remoto origin/{ramo} pubblicato: verifica il remoto prima di ripetere il push.")
        print(f"Ramo remoto origin/{ramo} pubblicato.", flush=True)
        step = "creazione PR"
        pr_output = esegui_fn(
            [
                "gh", "pr", "create", "--draft", "--base", "master", "--head", ramo,
                "--title", args.titolo, "--body", corpo_pr(issue, args.tipo, args.chiave, firma),
                "--label", label,
            ]
        ).strip()
        print(f"Issue #{issue}")
        print(f"PR {pr_output}")
        print(f"Worktree {worktree}")
        return 0
    except (OSError, subprocess.CalledProcessError, ValueError, RuntimeError) as error:
        dettaglio = str(error)
        if isinstance(error, subprocess.CalledProcessError):
            dettaglio = (error.stderr or error.output or str(error)).strip()
        print(f"Errore al passo {step}: {dettaglio}", file=sys.stderr)
        for resource in resources:
            print(resource, file=sys.stderr)
        if resources or step == "creazione issue":
            print(
                f"Per riprendere dal passo {step}, verifica prima le risorse elencate "
                "e gli eventuali effetti parziali del comando fallito. "
                "Non rilanciare l'apertura se worktree o ramo esistono già.",
                file=sys.stderr,
            )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
