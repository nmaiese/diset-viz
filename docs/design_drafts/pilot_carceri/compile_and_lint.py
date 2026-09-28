"""Compila draft_v2.json nel formato reale dello store e lancia il Gate 5.

Scrive SOLO in una cartella scratch fuori da content/indicators/: non e' una
promozione, e' il passo 4 (compilatore) del pilota.
Uso: bin/py docs/design_drafts/pilot_carceri/compile_and_lint.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from scripts import indicator_store  # noqa: E402

DOSSIER_PATH = HERE / "dossier_v2.json"
DRAFT_PATH = HERE / "draft_v2.json"
SCRATCH_STORE = HERE / "scratch_store"


def join_sentences(items):
    return " ".join(item["text"] for item in items).strip()


def main():
    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)
    with open(DRAFT_PATH, "r", encoding="utf-8") as f:
        draft = json.load(f)

    lead = join_sentences(draft["lead"])
    sezioni = []
    for section in draft["sections"]:
        sezioni.append({
            "role": section["role"],
            "h": section.get("h", ""),
            "body": join_sentences(section["sentences"]),
        })

    key = f"{dossier['family']}:{dossier['id']}"
    entry = {
        "key": key,
        "level": dossier["level"],
        "vintage": dossier["facts"]["meta.year_max"]["value"],
        "seo_title": "Affollamento delle carceri per provincia",
        "angolo_scelto": (
            "A Fermo il carcere ospita più di tre volte e mezzo i detenuti "
            "previsti, e nel 2024 la media delle province supera già la capienza."
        ),
        "fonti": [
            {"testo": dossier["source"]["label"], "url": dossier["source"]["url"]},
        ],
        "lead": lead,
        "sections": sezioni,
    }

    SCRATCH_STORE.mkdir(exist_ok=True)
    path = indicator_store.write(key, entry, root=SCRATCH_STORE)
    print(f"Scritto: {path}")
    print("--- contenuto ---")
    print(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
