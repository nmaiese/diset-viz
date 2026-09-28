"""Gate 2 del pilota: verifica deterministica di numeri e supporti.

Non e' un LLM: confronta ogni frase della bozza strutturata con il dossier.
Uso: bin/py docs/design_drafts/pilot_carceri/gate2_verify.py
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOSSIER_PATH = HERE / "dossier_v2.json"
DRAFT_PATH = HERE / "draft_v2.json"

NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def numeric_values_in_fact(fact):
    value = fact.get("value")
    found = set()
    if isinstance(value, (int, float)):
        found.add(round(float(value), 1))
        found.add(round(float(value)))
    return found


def numbers_in_text(text):
    out = []
    for match in NUMBER_RE.finditer(text):
        raw = match.group().replace(",", ".")
        try:
            out.append(round(float(raw), 1))
        except ValueError:
            continue
    return out


def main():
    dossier = load(DOSSIER_PATH)
    draft = load(DRAFT_PATH)
    facts = dossier["facts"]

    problems = []
    sentences = []
    for item in draft.get("lead", []):
        sentences.append(("lead", item))
    for section in draft.get("sections", []):
        role = section.get("role", "?")
        for item in section.get("sentences", []):
            sentences.append((role, item))

    for role, item in sentences:
        text = item.get("text", "")
        support = item.get("support", [])

        unknown_ids = [fid for fid in support if fid not in facts]
        if unknown_ids:
            problems.append(f"[{role}] id non nel dossier: {unknown_ids} — frase: {text!r}")

        allowed_numbers = set()
        for fid in support:
            fact = facts.get(fid)
            if fact is not None:
                allowed_numbers |= numeric_values_in_fact(fact)

        found_numbers = numbers_in_text(text)
        for num in found_numbers:
            if num in (100.0, 100):
                continue
            if num not in allowed_numbers and round(num) not in allowed_numbers:
                problems.append(
                    f"[{role}] cifra {num} nel testo senza un fatto corrispondente nel support {support} — frase: {text!r}"
                )

        if found_numbers and not support:
            problems.append(f"[{role}] frase con cifra senza alcun support: {text!r}")

    banned_chars = {"—": "em-dash", "–": "en-dash", ";": "punto e virgola", "…": "puntini di sospensione"}
    all_text = " ".join(item.get("text", "") for _, item in sentences)
    for ch, label in banned_chars.items():
        if ch in all_text:
            problems.append(f"assoluto di stile violato: {label} presente nel testo")

    print(f"Frasi controllate: {len(sentences)}")
    if not problems:
        print("PASS: nessun problema trovato dal gate deterministico.")
        return 0

    print(f"FAIL: {len(problems)} problemi")
    for p in problems:
        print(f"- {p}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
