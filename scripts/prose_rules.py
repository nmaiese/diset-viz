"""Il metro della prosa, per la catena minima. Misura, non ferma.

Sta in `scripts/` e non nella redazione perche' lo legge anche l'app servita, e quella
non entra nell'immagine Docker: il cruscotto deve contare **gli stessi rilievi**
che la catena stampa in `esito.articoli[].rilievi`, e un secondo metro darebbe
due numeri per la stessa pagina. Come `scripts/indicator_store.py`, e' stdlib
puro: non importa `app`, cosi' resta leggibile da un checkout senza venv.
`python3 scripts/prose_lint.py` resta il modo di chiamarlo a mano.

Sostituisce la chiamata a `officina/lint.py`, che non era portabile: 870 righe
che tirano dentro `packs.build`, `scripts.definition_check` e
`scripts.verification_queue`, cioè mezza catena vecchia sotto un altro nome.

Qui restano solo le regole che servono a questa catena e che `motore verifica`
non copre già. Le cifre e le fonti le controlla lui, una per una, contro il
dossier e contro la pagina rifetchata: ripeterle qui con un metro più grossolano
produceva rilievi falsi. Sui due articoli della lite il lint di officina ha dato
tre `cifra-falsa` bloccanti, e **tutte e tre erano volatilità**, dette
correttamente dal testo e accostate al valore della regione nominata accanto.

Nessun rilievo ferma un articolo: chi pubblica li stampa e basta. Cio' che
ferma sta in `motore pubblica`, ed è solo ciò che rende la pagina rotta.

    python3 scripts/prose_lint.py --show ter-13
"""
from __future__ import annotations

import argparse
import json
import re
import sys

# Gli assoluti tipografici di `content/STYLE.md`. Non sono gusto: il trattino
# lungo e il punto e virgola sono i due tell più forti di un testo generato, e
# il progetto li ha proibiti prima che esistesse questa catena.
VIETATI = {"—": "trattino lungo", "–": "trattino medio", ";": "punto e virgola",
           "…": "puntini in un carattere solo"}

# Un link a una pagina indicatore scritto nella forma vecchia, che non è
# canonica e che i motori indicizzano come duplicato.
LINK_VECCHIO = re.compile(r"/\?indicator=")

# Una frase che spiega un movimento. Se una sezione `dinamica` le usa e
# l'articolo non porta nessuna fonte, sta spiegando con niente in mano.
SPIEGA = re.compile(r"\b(perch[ée]|a causa|dovut[oaie]|per effetto|grazie a|"
                    r"spiega|riflette|deriva|conseguenza)\b", re.IGNORECASE)

CIFRA = re.compile(r"\d")

# Sotto questa quota di paragrafi senza nemmeno una cifra la prosa è calda.
# La misura viene dal confronto fra i pubblicati e gli esempi: la densità
# numerica non separa i due corpora, la quota di paragrafi scoperti sì.
SCOPERTI_MASSIMI = 0.5
PAROLE_MINIME = 350
LEAD_MASSIMO = 200


def _paragrafi(entry):
    for sezione in entry.get("sections") or []:
        for paragrafo in (sezione.get("body") or "").split("\n\n"):
            if paragrafo.strip():
                yield sezione, paragrafo.strip()


def _testo(entry):
    pezzi = [entry.get("lead") or ""]
    for sezione in entry.get("sections") or []:
        pezzi.append(sezione.get("h") or "")
        pezzi.append(sezione.get("body") or "")
    return "\n".join(pezzi)


def rilievi(entry):
    """[{rule, severity, detail, field}], la lista che chi pubblica stampa."""
    fuori = []

    def segna(regola, severita, dettaglio, campo=None):
        fuori.append({"rule": regola, "severity": severita,
                      "detail": dettaglio, "field": campo})

    testo = _testo(entry)
    for carattere, nome in VIETATI.items():
        if carattere in testo:
            quante = testo.count(carattere)
            segna("caratteri-vietati", "blocca",
                  f"{nome} ({carattere}) {quante} volte: non si usa in questo progetto")

    lead = (entry.get("lead") or "").strip()
    if len(lead) > LEAD_MASSIMO:
        segna("lead-lungo", "segnala",
              f"{len(lead)} caratteri: il lead diventa la meta description, "
              f"sopra {LEAD_MASSIMO} viene tagliato", "lead")

    if LINK_VECCHIO.search(testo):
        segna("link-non-canonico", "blocca",
              "un link nella forma `/?indicator=`: la forma canonica è "
              "`/indicatore/<slug>/<codice>`")

    parole = len(testo.split())
    if parole < PAROLE_MINIME:
        segna("troppo-corto", "segnala",
              f"{parole} parole: sotto {PAROLE_MINIME} la pagina dice meno del suo cruscotto")

    if not (entry.get("fonti") or []):
        for sezione, paragrafo in _paragrafi(entry):
            if sezione.get("role") == "dinamica" and SPIEGA.search(paragrafo):
                segna("dinamica-senza-fonte", "segnala",
                      "una sezione dinamica spiega un movimento e l'articolo non "
                      "porta nessuna fonte: dire che non si spiega è meglio che "
                      "spiegare lo stesso", "sections")
                break

    paragrafi = [paragrafo for _, paragrafo in _paragrafi(entry)]
    scoperti = [paragrafo for paragrafo in paragrafi if not CIFRA.search(paragrafo)]
    if paragrafi and len(scoperti) / len(paragrafi) > SCOPERTI_MASSIMI:
        segna("paragrafi-scoperti", "segnala",
              f"{len(scoperti)} paragrafi su {len(paragrafi)} senza una cifra: "
              f"è la misura che separa la prosa fredda da quella che dice qualcosa")

    return fuori


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("articolo", help="file JSON di un articolo o di una bozza")
    args = parser.parse_args(argv)
    entry = json.loads(open(args.articolo, encoding="utf-8").read())
    print(json.dumps({"rilievi": rilievi(entry)}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
