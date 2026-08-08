"""La bozza verificata diventa un file. E poi si misura, senza mai rifiutarla.

Scrive in `content/indicators/`, cioè **sulla pagina pubblica**: da quando la
catena editoriale precedente è stata ritirata, questa è l'unica che produce
articoli. Il nome del file e la struttura sono quelli di sempre, quindi le
pagine già scritte restano come sono finché non le si rifà una per una: il
ricambio è per indicatore, non un'operazione unica.

Sovrascrivere un articolo pubblicato è irreversibile per il lettore e
invisibile in un diff se nessuno lo dice: l'uscita porta `sovrascritto` e il
vintage di ciò che c'era prima, così chi legge l'esito sa se ha aggiunto una
pagina o ne ha rifatta una.

Legge la bozza da un **percorso**, non da stdin: è quella congelata da
`lab.controlla --salva`, cioè esattamente l'oggetto che il verificatore ha
approvato. Così fra la verifica e il disco non c'è nessun modello che ribatte
il testo.

L'ordine conta: prima scrive, poi misura. `lab.lint` gira dentro un try/except
e i suoi rilievi sono informativi, anche quelli marcati `blocca`: qui non c'è
cancello, e un'eccezione della misura non deve portarsi via l'unico prodotto.

    bin/py -m lab.pubblica ter-30 --bozza data/lab/bozze/ter-30.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from lab.dossier import risolvi
from lab.validazione import RUOLI, bloccanti
from app.indicator_view import build_indicator_view
from app import sources

ARTICOLI = os.path.join("content", "indicators")

# Dove si scriveva prima, e dove si scrive ancora con `--out` quando si vuole
# una bozza su disco senza toccare il sito.
LABORATORIO = os.path.join("data", "lab", "articoli")


# Ciò che un articolo può portare. `claims` non c'è apposta: un id di claim
# inventato non deve poter entrare, e le fonti web della lite stanno in `fonti`.
CAMPI = ("lead", "sections", "fonti")
CAMPI_SEZIONE = ("role", "h", "body")

# I controlli che una bozza deve passare stanno in `lab/validazione.py`, e chi
# li fa valere e' **chi verifica**, dentro `lab.controlla`, dove il testo si puo'
# ancora correggere. Qui si contano e si stampano, non si rifiuta: rifiutare
# all'ultimo passo non ripara niente, butta la run intera.


def _entry(codice, bozza, livello_chiesto=None):
    """Dalla bozza all'oggetto che l'app sa leggere, più livello e vintage."""
    famiglia, grezzo = risolvi(codice)
    vista = build_indicator_view(famiglia, grezzo)
    if vista is None:
        return None, None
    livelli = {livello["key"]: livello for livello in vista["levels"]}
    livello = livelli.get(livello_chiesto or vista["default_level"])
    if livello is None:
        return None, None

    chiave = sources.internal_id(famiglia, grezzo)
    entry = {campo: bozza[campo] for campo in CAMPI if bozza.get(campo) is not None}
    entry["sections"] = [
        {campo: sezione.get(campo) for campo in CAMPI_SEZIONE if campo in sezione}
        for sezione in bozza.get("sections") or []
    ]
    entry["key"] = chiave
    entry["level"] = livello["key"]
    # L'angolo della lite è una scelta editoriale in parole, non uno dei tipi
    # calibrati di `packs/angles.py`: si registra sotto un altro nome, così il
    # lint non lo misura con un metro che questa pipeline non usa.
    if bozza.get("angolo"):
        entry["angolo_scelto"] = bozza["angolo"]
    # L'anno che l'articolo descrive: è quello che la guardia numerica usa per
    # decidere contro quale colonna confrontare una cifra senza anno accanto.
    entry["vintage"] = livello["year_max"]
    return chiave, entry


def _impaginazione(entry):
    """Gli H2 che la pagina renderebbe, e le sezioni che perderebbe per strada.

    Non basta chiedere la sequenza dei ruoli a `emitted_roles`: da sola non
    mostra un corpo perso, che è proprio il guasto da sorvegliare. Si rifà
    quindi il giro completo che fa `build_article`, con la stessa coda per
    ruolo, e si guarda che cosa resta nella coda alla fine.

    Una sezione rimasta nella coda non dà errore da nessuna parte: non la vede
    l'app, non la vede il lint, e chi l'ha scritta la crede pubblicata. Qui
    diventa un rifiuto, perché scrivere un file che perde un pezzo di articolo
    è peggio che non scriverlo.
    """
    from app import indicator_texts

    sequenza = indicator_texts.emitted_roles(entry)
    scritte = {}
    for sezione in entry.get("sections") or []:
        if (sezione.get("role") in indicator_texts.DEFAULT_HEADINGS
                and (sezione.get("body") or "").strip()):
            scritte.setdefault(sezione["role"], []).append(sezione)

    resa = []
    for ruolo in sequenza:
        coda = scritte.get(ruolo) or []
        scritta = coda.pop(0) if coda else None
        titolo = (scritta.get("h") or "").strip() if scritta else ""
        resa.append({"role": ruolo,
                     "h2": titolo or indicator_texts.DEFAULT_HEADINGS[ruolo],
                     "scritta": scritta is not None})
    perse = [f"{ruolo}: \"{(sezione.get('h') or '(senza titolo)')[:50]}\""
             for ruolo, coda in scritte.items() for sezione in coda]
    return resa, perse


def _rilievi(chiave, entry):
    """Il metro della prosa. Misura e basta: qui non c'è cancello."""
    from lab import lint

    try:
        return lint.rilievi(entry)
    except Exception as errore:  # la misura non porta via il prodotto
        return [{"rule": "lint-non-eseguito", "severity": "segnala",
                 "detail": f"{type(errore).__name__}: {errore}", "field": None}]


def _parole(entry):
    """Lo stesso conteggio che usa il cruscotto, non uno suo.

    La console confronta le parole dell'articolo servito con quelle che la run ha
    registrato, per dire se una scrittura e' gia' in linea o aspetta un deploy.
    Con due definizioni di "parola" quel confronto misurerebbe la differenza fra
    le definizioni invece che fra gli articoli, e direbbe sempre "non in linea".
    """
    from app.editorial_state import parole

    return parole(entry)


def _impronta_prosa(entry):
    """L'identita' della prosa appena scritta, dalla stessa funzione del sito.

    Le parole dicono **quanto**, non **che cosa**: due riscritture della stessa
    lunghezza si leggevano `in linea` mentre in produzione c'era ancora l'altra.
    Il conteggio resta accanto perche' dice che cosa e' cambiato quando le due
    impronte non coincidono.
    """
    from app.editorial_state import impronta_prosa

    return impronta_prosa(entry)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("codice")
    parser.add_argument("--bozza", required=True, help="percorso della bozza congelata")
    parser.add_argument("--livello", default=None)
    parser.add_argument("--out", default=ARTICOLI, help=f"cartella (default {ARTICOLI})")
    args = parser.parse_args(argv)

    with open(args.bozza, encoding="utf-8") as handle:
        bozza = json.load(handle)

    # I controlli di `lab.validazione` **non rifiutano piu' qui**. Li esegue chi
    # verifica, dentro `lab.controlla`, dove il testo si puo' ancora correggere:
    # rifiutare all'ultimo passo non riparava niente, buttava la run intera
    # (`wf_32afde53-c4e`, 4,10 $, 11 agenti, e per giunta su un falso positivo).
    # Restano nell'uscita, perche' un difetto che nessuno vede piu' e' peggio di
    # un difetto che ferma.
    rimasti = bloccanti(bozza)

    chiave, entry = _entry(args.codice, bozza, args.livello)
    if entry is None:
        json.dump({"scritto": False, "problemi": [f"indicatore sconosciuto: {args.codice}"]},
                  sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 2

    impaginazione, perse = _impaginazione(entry)
    if perse:
        json.dump({"scritto": False, "problemi": [
            "la pagina non renderebbe queste sezioni: " + "; ".join(perse),
            "manca uno dei tre ruoli sostanziali (quadro, dinamica, limiti), "
            "quindi la sequenza scelta collassa in quella fissa e le sezioni "
            "in più non trovano posto",
        ], "impaginazione": impaginazione}, sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 2

    # Il nome del file e la chiave dentro il file devono coincidere: quando non
    # coincidono l'articolo non dà errore, sparisce.
    nome = f"{chiave.replace(':', '__')}.json"
    os.makedirs(args.out, exist_ok=True)
    percorso = os.path.join(args.out, nome)
    prima = None
    if os.path.exists(percorso):
        with open(percorso, encoding="utf-8") as handle:
            prima = json.load(handle)
    assert entry["key"] == os.path.basename(percorso)[:-5].replace("__", ":")
    with open(percorso, "w", encoding="utf-8") as handle:
        json.dump(entry, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.write("\n")

    json.dump({
        "scritto": True,
        # Non ferma piu' niente, e resta scritto: sono i controlli che il
        # verificatore aveva il compito di chiudere, e quello che ne resta dice
        # se quel passaggio ha fatto il suo lavoro.
        "bloccanti": rimasti,
        "sovrascritto": prima is not None,
        "vintage_precedente": (prima or {}).get("vintage"),
        "percorso": os.path.abspath(percorso),
        "chiave": chiave,
        "livello": entry["level"],
        "vintage": entry["vintage"],
        "parole": _parole(entry),
        "impronta_prosa": _impronta_prosa(entry),
        # Gli H2 come li vedrebbe un lettore: è l'unico modo di controllare la
        # forma di un articolo che nessuna pagina rende, perché `data/lab/`
        # non è letto da niente.
        "impaginazione": impaginazione,
        "rilievi": _rilievi(chiave, entry),
    }, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
