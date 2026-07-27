#!/usr/bin/env python3
"""Prepara una eval e stampa il compito da dare all'agente.

Le eval hanno due meta'. Questa prepara la parte non deterministica: copia le
fixture in una directory di lavoro e stampa il prompt con cui lanciare
l'agente (in una sessione Claude Code, o a mano). La meta' deterministica e'
`score_eval.py`, che misura quello che l'agente ha prodotto.

    python3 evals/run_eval.py writer
    python3 evals/run_eval.py reviewer
    python3 evals/run_eval.py verifier

Tutte le eval giudicano CONTRO IL BRIEF CONGELATO, mai contro i dati vivi:
e' cio' che rende il punteggio confrontabile tra un modello e il successivo.
Stdlib puro.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

EVALS = Path(__file__).resolve().parent
OUT = EVALS / "out"
BRIEF = "evals/writer/brief_ter-178.txt"

PROMPTS = {
    "writer": f"""\
Scrivi l'articolo per l'indicatore ter-178 (Tasso di occupazione, femmine)
usando COME UNICA FONTE DEI NUMERI il brief congelato in {BRIEF}.
Non consultare i dati vivi e non usare WebSearch: questa e' una eval, non una
run di produzione. Segui content/STYLE.md e la struttura di
.claude/agents/indicator-writer.md (lead + definizione, quadro, dinamica,
limiti, con "level": "regione" e "vintage": 2025).
Scrivi il risultato in evals/out/writer/article.json e fermati li': niente
store, niente commit, niente pull request.
Poi misura: python3 evals/score_eval.py writer evals/out/writer/article.json""",
    "reviewer": f"""\
In evals/out/reviewer/ ci sono due articoli su ter-178 con errori veri dentro.
Rileggili contro il brief congelato in {BRIEF} (unica fonte dei numeri, niente
dati vivi ne' web) applicando le classi di errore della skill
indicator-review. Correggi ogni errore SUL POSTO nei due file, come farebbe il
revisore: riscrivi, etichetta o taglia. Non firmare (niente reviewed_at):
questa e' una eval, non una run. Non toccare altro.
Poi misura: python3 evals/score_eval.py reviewer evals/out/reviewer""",
    "verifier": f"""\
In evals/out/verifier/claims.json ci sono affermazioni su ter-178, ognuna con
un campo "verdict" vuoto. Giudica ciascuna contro il brief congelato in
{BRIEF} (unica fonte, niente dati vivi ne' web) e riempi "verdict" con uno di:
confermata, smentita, non_verificabile. Sii avversariale: la domanda e' "posso
farla cadere?", non "sembra plausibile?". Non modificare nient'altro del file.
Poi misura: python3 evals/score_eval.py verifier evals/out/verifier/claims.json""",
}


def prepare(name):
    workdir = OUT / name
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)
    if name == "reviewer":
        for fixture in ("article_a.json", "article_b.json"):
            shutil.copy(EVALS / "reviewer" / fixture, workdir / fixture)
    elif name == "verifier":
        import json

        gold = json.loads((EVALS / "verifier" / "claims.json").read_text(encoding="utf-8"))
        for row in gold["claims"]:
            row.pop("label", None)
            row.pop("why", None)
            row["verdict"] = ""
        (workdir / "claims.json").write_text(
            json.dumps(gold, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return workdir


def main():
    parser = argparse.ArgumentParser(description="Prepara una eval e stampa il compito.")
    parser.add_argument("eval", choices=sorted(PROMPTS))
    args = parser.parse_args()
    workdir = prepare(args.eval)
    print(f"# fixture pronte in {workdir}")
    print(f"# compito per l'agente:\n\n{PROMPTS[args.eval]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
