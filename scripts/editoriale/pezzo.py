"""Apre in modo uniforme un nuovo lavoro editoriale."""
from __future__ import annotations

import argparse
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
        parola
        for parola in re.findall(r"[a-z0-9]+", senza_accenti)
        if len(parola) >= 4 and parola not in STOPWORD
    }


def _frase_normalizzata(testo: str) -> str:
    return "-".join(re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKD", testo.casefold()).encode("ascii", "ignore").decode()))


def valida_chiave(chiave: str) -> str:
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
                titolo_file = str(frontmatter.load(percorso).get("title") or percorso.stem)
            except (OSError, UnicodeError, ValueError):
                titolo_file = percorso.stem
            slug_norm = _frase_normalizzata(percorso.stem)
            slug_parole = _parole(percorso.stem)
            titolo_parole = _parole(titolo_file)
            chiave_nello_slug = bool(re.search(rf"(?:^|-)({re.escape(chiave_norm)})(?:-|$)", slug_norm))
            if len(richieste & slug_parole) >= 2 or len(richieste & titolo_parole) >= 2 or chiave_nello_slug:
                trovati.append(TemaEsistente(percorso, titolo_file))
    return trovati


def corpo_issue(tipo: str, chiave: str, firma: str) -> str:
    return (
        f"Tipo: {tipo}\nChiave: `{chiave}`\n\n"
        "Consegna in una PR draft, con controlli e fonti previsti dal progetto. "
        f"Seguire `docs/WORKFLOW_ORCA.md`.\n\n— {firma}"
    )


def corpo_pr(issue: int, tipo: str, chiave: str, firma: str) -> str:
    return f"Apre il lavoro editoriale `{chiave}` di tipo `{tipo}`.\n\nCloses #{issue}\n\n— {firma}"


def identita_agente() -> str:
    return os.environ.get("AGENT_ID", "").strip() or "codex-gpt-5.6-sol"


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
    return subprocess.check_output(list(cmd), cwd=ROOT, text=True, stderr=subprocess.STDOUT)


def _esiste_ramo(cmd: Sequence[str], esegui_fn: Callable[[Sequence[str]], str]) -> bool:
    try:
        output = esegui_fn(cmd)
    except subprocess.CalledProcessError as error:
        if error.returncode in (1, 2):
            return False
        raise
    return bool(output.strip())


def _numero_issue(output: str) -> int:
    match = re.search(r"/issues/(\d+)(?:\s*)$", output.strip())
    if not match:
        raise ValueError("GitHub non ha restituito il numero della issue")
    return int(match.group(1))


def _ultimo_percorso(output: str) -> Path:
    righe = [riga.strip() for riga in output.splitlines() if riga.strip()]
    if not righe:
        raise ValueError("Orca non ha restituito il percorso del worktree")
    return Path(righe[-1])


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
        if _esiste_ramo(["git", "show-ref", "--verify", f"refs/heads/{ramo}"], esegui_fn):
            raise RuntimeError(f"il ramo locale {ramo} esiste già")
        if _esiste_ramo(
            ["git", "ls-remote", "--exit-code", "--heads", "origin", f"refs/heads/{ramo}"], esegui_fn
        ):
            raise RuntimeError(f"il ramo remoto {ramo} esiste già")
        lavoro_root = root / "lavoro" / args.chiave
        if lavoro_root.exists():
            raise RuntimeError(f"la cartella lavoro/{args.chiave} esiste già")

        label = f"run:{args.tipo}"
        firma = identita_agente()
        issue_output = esegui_fn(
            [
                "gh", "issue", "create", "--title", args.titolo, "--label", label,
                "--body", corpo_issue(args.tipo, args.chiave, firma),
            ]
        )
        issue = _numero_issue(issue_output)
        worktree_output = esegui_fn([str(ORCA_WORKTREE), f"divario-{args.chiave}"])
        worktree = _ultimo_percorso(worktree_output)
        esegui_fn(["git", "-C", str(worktree), "switch", "-c", ramo, "origin/master"])

        cartella = worktree / "lavoro" / args.chiave
        cartella.mkdir(parents=True)
        (cartella / "brief.md").write_text(
            contenuto_brief(args.titolo, args.tipo, issue, simili), encoding="utf-8"
        )
        (cartella / "numeri.md").write_text("# Numeri\n", encoding="utf-8")
        (cartella / "fonti.md").write_text("# Fonti\n", encoding="utf-8")

        esegui_fn(["git", "-C", str(worktree), "add", "-f", f"lavoro/{args.chiave}"])
        esegui_fn(
            ["git", "-C", str(worktree), "commit", "-m", f"Apre il lavoro editoriale su {args.titolo}"]
        )
        esegui_fn(["git", "-C", str(worktree), "push", "-u", "origin", ramo])
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
        dettaglio = error.output.strip() if isinstance(error, subprocess.CalledProcessError) and error.output else str(error)
        print(f"Errore: {dettaglio}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
