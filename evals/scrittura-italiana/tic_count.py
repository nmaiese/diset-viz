#!/usr/bin/env python3
"""Il contatore deterministico dei tic dell'italiano generato (finder, non verdetto).

Perche' esiste. `scripts/prose_lint.py` conta i tell che content/STYLE.md gia'
nomina (domanda retorica di chiusura, lessico spia, slogan, falso intervallo,
numero doppio). Sono tutti tell di *superficie editoriale*. Restano fuori i tic
*strutturali* dell'italiano AI, quelli che la skill scrittura-italiana esiste
per togliere: gli avverbi in -mente a raffica, la gerundite in coda, la
definizione bipolare nelle sue cinque varianti, le perifrasi al posto di
"e'/sono", il lessico di plastica e ad alta frequenza AI, i latinismi e i
connettori sovrabbondanti, l'incipit a cornice, e il ritmo piatto (bassa
varianza della lunghezza delle frasi).

Senza questo contatore un confronto prima/dopo sullo stadio gia' curato dal
produttore darebbe zero su prose_lint e satura sulla rubrica (vedi
docs/WRITING_QUALITY_PLAN.md, Parte seconda, buchi 1 e 3): due strumenti ciechi
proprio sul braccio che decide se la skill aggiunge valore. Questo e' lo
strumento mancante.

Cosa NON e'. Non e' un cancello e non e' un giudice. Ogni categoria e' una
*regex finder*: per costruzione prende anche falsi positivi (una gerundite
legittima, un "rappresenta" che regge). Il numero misura una densita', da
leggere insieme, mai una sola occorrenza come colpa. La lista lessicale e'
distillata da references/stile-naturale.md (§7, §8, §14, §15, §17, §18, §20,
§39, §45) e references/cliche-e-parole-alla-moda.md della skill, sotto CC BY-SA
4.0 (vedi .claude/skills/scrittura-italiana/ATTRIBUZIONE.md).

Uso:

    python3 evals/scrittura-italiana/tic_count.py <file.json|file.txt|file.md>
    python3 evals/scrittura-italiana/tic_count.py --text "..."
    python3 evals/scrittura-italiana/tic_count.py --self-test

Un file .json e' letto come articolo indicatore (lead + sezioni). Ogni altro
file e' testo (il frontmatter e i marcatori Markdown piu' rumorosi sono tolti).
Stdlib puro.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

# I caratteri che content/STYLE.md vieta in assoluto. Qui non sono un tic da
# contare tra gli altri ma un cancello: gli assoluti di progetto vincono sempre
# sulla skill, che invece in testo controllato ammette la lineetta e il punto e
# virgola. Se compaiono in un "dopo", la riscrittura e' da rifare, non da pesare.
BANNED = {"—": "em-dash", "–": "en-dash", ";": "punto e virgola", "…": "puntini"}

# -mente ad alta frequenza AI (stile-naturale.md §15). L'euristica e' la
# densita': un -mente ogni tanto e' italiano, cinque per pagina sono un tic.
MENTE = re.compile(r"\b\w+mente\b", re.IGNORECASE)

# Gerundite in coda di frase (stile-naturale.md §3, §14): il gerundio pleonastico
# che allunga una frase che dovrebbe finire. Il finder cerca un gerundio dopo la
# virgola. Prende anche gerundi legittimi: e' un candidato, non una colpa.
GERUNDITE = re.compile(
    r",\s+(?:cosi\s+)?\w+(?:ando|endo)\b", re.IGNORECASE
)

# Perifrasi al posto di "e'/sono/ha" (stile-naturale.md §8).
PERIFRASI = re.compile(
    r"\b(?:si\s+configura\s+come|si\s+pone\s+come|si\s+presenta\s+come|"
    r"si\s+erge\s+a|assurge\s+a|si\s+rivela|risulta\s+essere|"
    r"rappresenta|costituisce|si\s+tratta\s+di)\b",
    re.IGNORECASE,
)

# Le cinque varianti del bipolare (stile-naturale.md §9). Sono finder, con falsi
# positivi dichiarati (anafora triadica, citazione, tesi-manifesto): il numero e'
# una densita' da leggere, non un verdetto sulla singola frase.
BIPOLARE = [
    re.compile(r"\bnon\s+è\s+[^.;:!?]{0,60},\s+ma\b", re.IGNORECASE),      # (a) letterale
    re.compile(r"\bnon\s+è\s+[^.;:!?]{0,60}:\s+è\b", re.IGNORECASE),        # (d) due punti
    re.compile(r"\bnon\s+(?:solo|tanto)\b[^.;:!?]{0,60}\bma\s+(?:anche|quanto)\b", re.IGNORECASE),
    re.compile(r"\bnon\s+(?:sono|viene|vengono|hanno|era|erano|sarà|saranno)\s+[^.;:!?]{0,50}\bma\b", re.IGNORECASE),  # (b) plurali/tempi
    re.compile(r",\s+e\s+non\s+[^.;:!?]{3,45}[.;:]", re.IGNORECASE),        # (e) e non
]

# Latinismi pretenziosi (stile-naturale.md §17): tell quando si accumulano.
LATINISMI = re.compile(
    r"\b(?:in\s+primis|de\s+facto|ipso\s+facto|ex\s+post|ex\s+ante|"
    r"prima\s+facie|a\s+fortiori|in\s+nuce|tout\s+court|en\s+passant|ergo)\b",
    re.IGNORECASE,
)

# Connettori sovrabbondanti e formali (stile-naturale.md §20).
CONNETTORI = re.compile(
    r"\b(?:altresì|peraltro|cionondimeno|nondimeno|pertanto|"
    r"di\s+conseguenza|vale\s+a\s+dire|nello\s+specifico|"
    r"per\s+di\s+più|oltretutto|conseguentemente)\b",
    re.IGNORECASE,
)

# Incipit a cornice (stile-naturale.md §45): solo se in testa al testo o di una
# sezione. Il finder si applica alla prima frase, non al corpo.
INCIPIT_CORNICE = re.compile(
    r"^\s*(?:nel\s+mondo\s+(?:di|del|della)|nell'era\s+(?:di|del)|"
    r"nel\s+panorama|in\s+questo\s+contesto|nell'ambito\s+(?:di|del))\b",
    re.IGNORECASE,
)

# Lessico di plastica e vocabolario AI ad alta frequenza (stile-naturale.md §7,
# §39; cliche-e-parole-alla-moda.md §1). Contato come densita' per mille parole.
# NB: alcune parole (cruciale, panorama, tessuto, sottolineare, evidenziare)
# stanno gia' nel lessico-spia di prose_lint. Qui la lista e' piu' larga e la
# metrica e' la densita', non la presenza: i due strumenti si leggono insieme.
LESSICO_PLASTICA = {
    "cruciale", "cruciali", "fondamentale", "fondamentali", "imprescindibile",
    "evidenziare", "sottolineare", "valorizzare", "esaltare", "intricato",
    "articolato", "sfaccettato", "stratificato", "intreccio", "mosaico",
    "tessuto", "ordito", "panorama", "scenario", "orizzonte", "duraturo",
    "imperituro", "indelebile", "vibrante", "dinamico", "pregevole",
    "inestimabile", "abbracciare", "racchiudere", "incarnare", "sinergia",
    "criticità", "attenzionare", "concretizzare", "ottimizzare", "efficientare",
    "problematica", "tematica", "tipologia", "progettualità", "resilienza",
    "resiliente", "ecosistema", "narrazione", "iconico", "immersivo",
    "esperienziale", "plasmare", "snodo", "pilastro", "baluardo", "cardine",
}
PAROLA = re.compile(r"[A-Za-zÀ-ÿ']+")


def _strip_markdown(text: str) -> str:
    """Toglie il frontmatter YAML e i marcatori Markdown piu' rumorosi, cosi'
    il contatore misura la prosa e non la sintassi del formato."""
    text = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)
    text = re.sub(r"\{:[^}]*\}", "", text)          # attributi Kramdown ({: .x})
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)  # heading
    text = re.sub(r"[*_`]", "", text)                # enfasi
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # link -> testo
    return text


def _load_text(path: Path) -> str:
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        parts = [data.get("lead") or ""]
        for section in data.get("sections") or []:
            parts.append(section.get("h") or "")
            parts.append(section.get("body") or "")
        return "\n\n".join(parts)
    return _strip_markdown(path.read_text(encoding="utf-8"))


def _sentences(text: str):
    raw = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    return [s.strip() for s in raw if s.strip()]


def count_tics(text: str) -> dict:
    words = PAROLA.findall(text)
    n_words = len(words) or 1
    sentences = _sentences(text)
    lengths = [len(PAROLA.findall(s)) for s in sentences] or [0]

    bipolare = sum(len(rx.findall(text)) for rx in BIPOLARE)
    lessico = sum(1 for w in words if w.lower() in LESSICO_PLASTICA)
    incipit = 0
    if sentences and INCIPIT_CORNICE.search(sentences[0]):
        incipit = 1

    raw = {
        "mente": len(MENTE.findall(text)),
        "gerundite": len(GERUNDITE.findall(text)),
        "perifrasi_essere": len(PERIFRASI.findall(text)),
        "bipolare": bipolare,
        "latinismi": len(LATINISMI.findall(text)),
        "connettori": len(CONNETTORI.findall(text)),
        "incipit_cornice": incipit,
        "lessico_plastica": lessico,
    }
    banned = [label for char, label in BANNED.items() if char in text]

    mean_len = statistics.mean(lengths)
    stdev_len = statistics.pstdev(lengths) if len(lengths) > 1 else 0.0
    total = sum(raw.values())

    return {
        "parole": n_words,
        "frasi": len(sentences),
        "tic": raw,
        "tic_totali": total,
        "tic_per_1000_parole": round(total * 1000 / n_words, 1),
        "vietati": banned,                       # gate: deve essere []
        "ritmo": {
            "lunghezza_media_frase": round(mean_len, 1),
            "deviazione_standard": round(stdev_len, 1),
            # varianza del ritmo: piu' e' alta, meno piatto e' il periodare
            "burstiness": round(stdev_len / mean_len, 2) if mean_len else 0.0,
        },
    }


def _self_test() -> int:
    """Il metro provato sul metro: un testo pieno di tic deve pesare piu' di uno
    pulito, e il cancello deve vedere i caratteri vietati."""
    failures = []

    sporco = (
        "Nel mondo della statistica, il dato non è una semplice cifra, ma è un "
        "racconto. Rappresenta fondamentalmente un tassello cruciale, "
        "sottolineando significativamente le criticità del territorio, "
        "evidenziando peraltro le sfaccettature del panorama. In primis, "
        "costituisce de facto un pilastro imprescindibile."
    )
    pulito = (
        "In Campania il valore per addetto supera i 36 punti. Le Marche chiudono "
        "la classifica sotto la Calabria. Dal 1995 la distanza tra la prima e "
        "l'ultima regione si è accorciata di quattromila euro."
    )
    s = count_tics(sporco)
    p = count_tics(pulito)
    if s["tic_per_1000_parole"] <= p["tic_per_1000_parole"]:
        failures.append("il testo sporco non pesa piu' del pulito")
    for k in ("mente", "perifrasi_essere", "bipolare", "latinismi",
              "connettori", "lessico_plastica", "incipit_cornice"):
        if s["tic"][k] == 0:
            failures.append(f"categoria '{k}' non presa su un testo che la contiene")

    vietato = count_tics("Questa frase ha un punto e virgola; e un trattino —.")
    if "punto e virgola" not in vietato["vietati"] or "em-dash" not in vietato["vietati"]:
        failures.append("il cancello non vede i caratteri vietati")
    if p["vietati"]:
        failures.append("falso positivo sui caratteri vietati")

    for line in failures:
        print(f"SELF-TEST FALLITO: {line}")
    if not failures:
        print("self-test ok: il contatore separa lo sporco dal pulito e vede i vietati")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Conta i tic dell'italiano generato (finder).")
    parser.add_argument("target", nargs="?", help="file .json, .txt o .md")
    parser.add_argument("--text", help="testo da misurare direttamente")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return _self_test()
    if args.text is not None:
        result = count_tics(args.text)
    elif args.target:
        result = count_tics(_load_text(Path(args.target)))
        result["file"] = args.target
    else:
        parser.error("serve un file, --text, oppure --self-test")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
