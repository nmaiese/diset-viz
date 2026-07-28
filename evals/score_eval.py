#!/usr/bin/env python3
"""Il punteggio deterministico delle eval degli agenti.

La meta' non deterministica (far girare un agente su una fixture) la prepara
`run_eval.py`. Questa meta' e' solo aritmetica su file, quindi e' ripetibile e
si puo' provare da sola (`--self-test`): un metro che nessuno ha tarato non
misura niente.

    python3 evals/score_eval.py writer   <articolo.json>
    python3 evals/score_eval.py reviewer <dir-con-articoli-corretti>
    python3 evals/score_eval.py verifier <verdetti.json>
    python3 evals/score_eval.py --self-test

Uscita 0 quando il punteggio e' stato calcolato (il numero e' il risultato,
non un verdetto), 1 su input illeggibile o self-test fallito. Stdlib puro.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

EVALS = Path(__file__).resolve().parent
BRIEF = EVALS / "writer" / "brief_ter-178.txt"
REVIEWER_EXPECTED = EVALS / "reviewer" / "expected.json"
VERIFIER_GOLD = EVALS / "verifier" / "claims.json"
ADMISSIONS_GOLD = EVALS / "admissions" / "cases.json"

# I caratteri che content/STYLE.md vieta in assoluto.
BANNED = {"—": "em-dash", "–": "en-dash", ";": "punto e virgola",
          "…": "puntini"}


def _article_text(data):
    parts = [data.get("lead") or ""]
    for section in data.get("sections") or []:
        parts.append(section.get("h") or "")
        parts.append(section.get("body") or "")
    return "\n".join(parts)


def score_writer(article_path, brief_path=None):
    """Ogni cifra dell'articolo deve stare nel brief congelato.

    Il controllo e' volutamente grezzo: una cifra e' lecita se compare testuale
    nel brief, se e' un anno, o se e' un intero da 0 a 20 (ranghi e conteggi su
    venti regioni). Non giudica la prosa: quella resta al lettore. Quello che
    prende e' la classe di guasto che conta di piu' in una eval, il numero che
    non viene da nessuna parte.
    """
    data = json.loads(Path(article_path).read_text(encoding="utf-8"))
    brief = Path(brief_path or BRIEF).read_text(encoding="utf-8")
    text = _article_text(data)

    problems = []
    for char, label in BANNED.items():
        if char in text:
            problems.append(f"carattere vietato: {label}")

    strays = []
    for token in re.findall(r"\d+(?:,\d+)?", text):
        if token in brief:
            continue
        if "," not in token:
            value = int(token)
            if 1900 <= value <= 2100 or 0 <= value <= 20:
                continue
        strays.append(token)
    return {
        "eval": "writer",
        "file": str(article_path),
        "cifre_fuori_brief": sorted(set(strays)),
        "problemi": problems,
        "ok": not strays and not problems,
    }


def score_reviewer(corrected_dir, expected_path=None):
    """Quanti errori piantati sono spariti dal testo corretto.

    Un errore conta come trovato quando la sua frase non c'e' piu': riscritta,
    etichettata o tagliata. Il metro non giudica la riscrittura, conta le
    sopravvivenze, perche' un errore piantato che sopravvive a una revisione
    e' esattamente cio' che questa eval esiste per misurare.
    """
    expected = json.loads(Path(expected_path or REVIEWER_EXPECTED).read_text(encoding="utf-8"))
    root = Path(corrected_dir)
    found, missed, unreadable = [], [], []
    for error in expected["errors"]:
        target = root / error["file"]
        try:
            text = _article_text(json.loads(target.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            unreadable.append(error["file"])
            continue
        (missed if error["pattern"] in text else found).append(error["id"])
    return {
        "eval": "reviewer",
        "dir": str(corrected_dir),
        "trovati": found,
        "mancati": missed,
        "illeggibili": sorted(set(unreadable)),
        "score": f"{len(found)}/{len(expected['errors'])}",
    }


def score_verifier(verdicts_path, gold_path=None):
    """Verdetti dell'agente contro il gold set, con precision e recall sulle
    smentite: una smentita falsa rimanda in lavorazione un articolo giusto,
    quindi e' l'errore che va misurato per primo."""
    gold = json.loads(Path(gold_path or VERIFIER_GOLD).read_text(encoding="utf-8"))
    produced = json.loads(Path(verdicts_path).read_text(encoding="utf-8"))
    if isinstance(produced, dict) and "claims" in produced:
        produced = {row["id"]: row.get("verdict") for row in produced["claims"]}
    labels = {row["id"]: row["label"] for row in gold["claims"]}

    right, wrong, missing = [], [], []
    tp = fp = fn = 0
    for claim_id, label in labels.items():
        verdict = produced.get(claim_id)
        if verdict is None:
            missing.append(claim_id)
            continue
        (right if verdict == label else wrong).append(claim_id)
        if label == "smentita" and verdict == "smentita":
            tp += 1
        elif label != "smentita" and verdict == "smentita":
            fp += 1
        elif label == "smentita":
            fn += 1
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    return {
        "eval": "verifier",
        "giusti": right,
        "sbagliati": wrong,
        "senza_verdetto": missing,
        "accuratezza": f"{len(right)}/{len(labels)}",
        "precision_smentite": precision,
        "recall_smentite": recall,
    }


def score_admissions(verdicts_path, gold_path=None):
    """Verdetti di triage dell'ammissione contro il gold set, con precision e
    recall sugli APPROVATI: una falsa approvazione fa entrare in una pagina
    pubblica, sotto il nome del progetto, una fonte o un indicatore che non
    doveva passare, e nessuno la rilegge. E' l'errore irreversibile della
    catena, quindi e' quello che va misurato per primo (l'analogo della falsa
    smentita nel verificatore). Un rinvio 'needs-info' costa poco: e' un esito
    legittimo, non un errore."""
    gold = json.loads(Path(gold_path or ADMISSIONS_GOLD).read_text(encoding="utf-8"))
    produced = json.loads(Path(verdicts_path).read_text(encoding="utf-8"))
    if isinstance(produced, dict) and "cases" in produced:
        produced = {row["id"]: row.get("verdict") for row in produced["cases"]}
    labels = {row["id"]: row["label"] for row in gold["cases"]}

    right, wrong, missing, false_approvals = [], [], [], []
    tp = fp = fn = 0
    for case_id, label in labels.items():
        verdict = produced.get(case_id)
        if verdict in (None, ""):
            missing.append(case_id)
            continue
        (right if verdict == label else wrong).append(case_id)
        if label == "approvato" and verdict == "approvato":
            tp += 1
        elif label != "approvato" and verdict == "approvato":
            fp += 1
            false_approvals.append(case_id)
        elif label == "approvato":
            fn += 1
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    return {
        "eval": "admissions",
        "giusti": right,
        "sbagliati": wrong,
        "false_approvazioni": false_approvals,
        "senza_verdetto": missing,
        "accuratezza": f"{len(right)}/{len(labels)}",
        "precision_approvati": precision,
        "recall_approvati": recall,
    }


def self_test():
    """Il metro provato sul metro: fixture non corrette e gold contro se stesso."""
    failures = []

    writer = score_writer(EVALS / "reviewer" / "article_a.json")
    if "54,9" not in writer["cifre_fuori_brief"]:
        failures.append("writer: la cifra inventata 54,9 non e' stata presa")

    reviewer = score_reviewer(EVALS / "reviewer")
    if reviewer["trovati"] or len(reviewer["mancati"]) != 7:
        failures.append(f"reviewer: sulle fixture non corrette atteso 0/7, avuto {reviewer['score']}")

    gold_as_verdicts = {
        row["id"]: row["label"]
        for row in json.loads(VERIFIER_GOLD.read_text(encoding="utf-8"))["claims"]
    }
    tmp = EVALS / ".self_test_verdicts.json"
    tmp.write_text(json.dumps(gold_as_verdicts), encoding="utf-8")
    try:
        verifier = score_verifier(tmp)
    finally:
        tmp.unlink()
    if verifier["sbagliati"] or verifier["senza_verdetto"]:
        failures.append("verifier: il gold contro se stesso non fa punteggio pieno")

    admissions_gold = {
        row["id"]: row["label"]
        for row in json.loads(ADMISSIONS_GOLD.read_text(encoding="utf-8"))["cases"]
    }
    tmp = EVALS / ".self_test_admissions.json"
    tmp.write_text(json.dumps(admissions_gold), encoding="utf-8")
    try:
        admissions = score_admissions(tmp)
        # Un'ammissione ingenua che approva tutto: la precision sugli approvati
        # deve crollare, o il metro non vede la falsa approvazione (l'errore che
        # esiste per prendere).
        naive = {cid: "approvato" for cid in admissions_gold}
        tmp.write_text(json.dumps(naive), encoding="utf-8")
        naive_score = score_admissions(tmp)
    finally:
        tmp.unlink()
    if admissions["sbagliati"] or admissions["senza_verdetto"]:
        failures.append("admissions: il gold contro se stesso non fa punteggio pieno")
    if admissions["precision_approvati"] != 1.0 or admissions["recall_approvati"] != 1.0:
        failures.append("admissions: il gold contro se stesso non da' precision/recall pieni")
    if not naive_score["false_approvazioni"] or (naive_score["precision_approvati"] or 1) >= 1.0:
        failures.append("admissions: 'approva tutto' non fa crollare la precision, il metro e' cieco")

    for line in failures:
        print(f"SELF-TEST FALLITO: {line}")
    if not failures:
        print("self-test ok: writer, reviewer, verifier e admissions misurano quel che devono")
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description="Punteggio deterministico delle eval.")
    parser.add_argument("eval", nargs="?",
                        choices=("writer", "reviewer", "verifier", "admissions"))
    parser.add_argument("target", nargs="?", help="il file o la directory da misurare")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if not (args.eval and args.target):
        parser.error("servono eval e target, oppure --self-test")
    scorer = {"writer": score_writer, "reviewer": score_reviewer,
              "verifier": score_verifier, "admissions": score_admissions}[args.eval]
    print(json.dumps(scorer(args.target), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
