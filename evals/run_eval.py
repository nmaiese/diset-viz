#!/usr/bin/env python3
"""Prepara una eval e stampa il compito da dare all'agente.

Le eval hanno due metà. Questa prepara la parte non deterministica: copia le
fixture in una directory di lavoro e stampa il prompt con cui lanciare
l'agente (in una sessione Claude Code, o a mano). La metà deterministica è
`score_eval.py`, che misura quello che l'agente ha prodotto.

    python3 evals/run_eval.py writer
    python3 evals/run_eval.py reviewer
    python3 evals/run_eval.py verifier
    python3 evals/run_eval.py admissions

Tutte le eval giudicano CONTRO UNA FIXTURE CONGELATA (il brief per le editoriali,
la descrizione del caso per l'ammissione), mai contro i dati vivi o il web: è
ciò che rende il punteggio confrontabile tra un modello e il successivo.
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
Non consultare i dati vivi e non usare WebSearch: questa è una eval, non una
run di produzione. Segui content/STYLE.md. I `role` sono quattro e solo
quattro: definizione, quadro, dinamica, limiti. I tre sostanziali ci sono
sempre, definizione è la sola omettibile, l'ordine è libero e una sola
sezione per ruolo. Scrivi con "level": "regione" e "vintage": 2025.

Il candidato da misurare è il tipo `scrittore-indicatore`, che non può
scrivere file: fallo girare sul brief e riporta tu la sua risposta strutturata
in evals/out/writer/article.json, aggiungendo key, level e vintage. Il metro
non cambia, il prompt misurato sì.

Fermati lì: niente store, niente commit, niente pull request.
Poi misura: python3 evals/score_eval.py writer evals/out/writer/article.json""",
    "reviewer": f"""\
In evals/out/reviewer/ ci sono due articoli su ter-178 con errori veri dentro.
Rileggili contro il brief congelato in {BRIEF} (unica fonte dei numeri, niente
dati vivi né web) applicando le classi di errore della skill
indicator-review. Correggi ogni errore SUL POSTO nei due file, come farebbe il
revisore: riscrivi, etichetta o taglia. Non firmare (niente reviewed_at):
questa è una eval, non una run. Non toccare altro.
Poi misura: python3 evals/score_eval.py reviewer evals/out/reviewer""",
    "verifier": f"""\
In evals/out/verifier/claims.json ci sono affermazioni su ter-178, ognuna con
un campo "verdict" vuoto. Giudica ciascuna contro il brief congelato in
{BRIEF} (unica fonte, niente dati vivi né web) e riempi "verdict" con uno di:
confermata, smentita, non_verificabile. Sii avversariale: la domanda è "posso
farla cadere?", non "sembra plausibile?". Non modificare nient'altro del file.
Poi misura: python3 evals/score_eval.py verifier evals/out/verifier/claims.json""",
    "reader-editor": """\
In evals/out/reader-editor/cases.json ci sono articoli indicatore congelati,
ognuno col campo "verdict" vuoto e la prosa (lead più sezioni) dentro il caso.
Giudica la LEGGIBILITÀ di ognuno CONTRO LA PROSA CONGELATA nel caso, mai contro
la pagina viva, i dati o il web (questa è una eval, non una run): un lettore
comune, non tecnico, capisce l'articolo al primo passaggio? Applica gli otto
criteri e i fallimenti duri di .claude/agents/reader-editor.md, tenendo gli assi
separati (mai una media unica), e ricorda che NON giudichi i fatti (li verifica
un altro) né i tic (li prende prose_lint): solo se si legge. Riempi "verdict"
con uno di: pass, revise. Un `revise` ha almeno un criterio sotto il 2 o un
fallimento duro; un `pass` non porta fallimenti duri. Non modificare
nient'altro del file.
Poi misura: python3 evals/score_eval.py reader-editor evals/out/reader-editor/cases.json""",
    "admissions": """\
In evals/out/admissions/cases.json ci sono casi di triage dell'ammissione,
ognuno con un campo "verdict" vuoto. Ogni caso ha in "caso" TUTTI i fatti che
servono al giudizio (istituzione, licenza, dettaglio territoriale, cadenza,
additività, e per i candidati copertura e verso proposto): giudica CONTRO
QUELLA DESCRIZIONE CONGELATA, mai contro il catalogo vivo, i dati o il web
(questa è una eval, non una run: la licenza è quella scritta nel caso, non
una da aprire con WebFetch). Applica la rubrica giusta secondo "tipo": per una
"fonte" le quattro parti (istituzionale, licenza esplicita e compatibile,
territoriale e regolare, additivo), per un "candidato" le quattro condizioni
(additivo, copertura vera, licenza e istituzione, verso difendibile). Prima di
scrivere "approvato" fai l'auto-refutazione: costruisci il caso più forte
CONTRO l'ammissione e approva solo se cade. Se il caso contro regge anche solo
su un punto verificabile è "needs-info"; se fallisce una parte per come è
fatto il dato è "respinto". Riempi "verdict" con uno di: approvato, respinto,
needs-info. Non modificare nient'altro del file.
Poi misura: python3 evals/score_eval.py admissions evals/out/admissions/cases.json""",
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
    elif name == "admissions":
        import json

        gold = json.loads((EVALS / "admissions" / "cases.json").read_text(encoding="utf-8"))
        for row in gold["cases"]:
            row.pop("label", None)
            row.pop("classe", None)
            row.pop("why", None)
            row["verdict"] = ""
        (workdir / "cases.json").write_text(
            json.dumps(gold, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    elif name == "reader-editor":
        import json
        import sys

        # Lo stesso modulo che poi ricalcola la corrispondenza: la regola degli id
        # ciechi vive lì, in un posto solo, o preparazione e punteggio divergono
        # e la eval smette di sommare.
        sys.path.insert(0, str(EVALS))
        import score_eval

        gold = json.loads((EVALS / "reader-editor" / "cases.json").read_text(encoding="utf-8"))
        # Via il blocco `_`: è commento per chi legge il gold, e se descrive quali
        # casi siano revise (il primo `_` lo faceva) regala all'agente le risposte.
        gold.pop("_", None)
        for row in gold["cases"]:
            row.pop("label", None)
            row.pop("why", None)
            # Via anche il `code`: per i casi reali è l'id pubblico dell'articolo,
            # e uno (eur-rd_p_persreg) è nominato come esempio-revise nelle
            # istruzioni stesse del reader-editor, quindi il codice tradirebbe la
            # risposta. L'agente giudica la prosa, non il codice; lo score unisce
            # su `id`, che resta.
            row.pop("code", None)
            # E via anche l'id parlante: `p01`-`p04` sono i quattro `pass` e
            # `r01`-`rc04` i quattro `revise`, quindi il prefisso dà 8/8 a chi
            # non legge nemmeno la prosa, e una baseline che si centra così non
            # vede più nessuna regressione. `score_eval.blind_id` ricalcola la
            # corrispondenza da sé: niente file di mappa accanto alla fixture,
            # che sarebbe la stessa fuga con un passaggio in più.
            row["id"] = score_eval.blind_id(row["id"])
            row["verdict"] = ""
        # In ordine di id cieco: lasciarli nell'ordine del gold rimetterebbe in
        # fila i quattro pass e poi i quattro revise, cioè la risposta di prima
        # travestita da posizione.
        gold["cases"].sort(key=lambda row: row["id"])
        (workdir / "cases.json").write_text(
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
