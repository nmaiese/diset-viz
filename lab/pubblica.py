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
import re
import sys

from lab.dossier import risolvi
from app.indicator_view import build_indicator_view
from app import sources

ARTICOLI = os.path.join("content", "indicators")

# Dove si scriveva prima, e dove si scrive ancora con `--out` quando si vuole
# una bozza su disco senza toccare il sito.
LABORATORIO = os.path.join("data", "lab", "articoli")

# I quattro ruoli che la pagina indicatore sa rendere. Una sezione con un ruolo
# diverso verrebbe scartata in silenzio dal template.
#
# **Quattro ruoli non vuol dire quattro sezioni.** La pagina tiene una lista per
# ruolo (`app/indicator_texts.py:267-282`) e la sequenza degli H2 la deriva
# dalle sezioni scritte conservando ordine e ripetizioni: due `quadro` con due
# titoli diversi rendono due H2. È così che i sette temi di un articolo stanno
# dentro quattro ruoli, col titolo a portare il tema.
#
# La derivazione però scatta **solo** se le sezioni scritte coprono tutti e tre
# i ruoli sostanziali. Se ne manca uno, la forma scelta collassa nei quattro
# fissi e le sezioni in eccesso spariscono senza errore: è il guasto che
# `_impaginazione` esiste per intercettare.
RUOLI = ("definizione", "quadro", "dinamica", "limiti")

# Ciò che un articolo può portare. `claims` non c'è apposta: un id di claim
# inventato non deve poter entrare, e le fonti web della lite stanno in `fonti`.
CAMPI = ("lead", "sections", "fonti")
CAMPI_SEZIONE = ("role", "h", "body")

# Un accento scritto con l'apostrofo: "poverta" seguito da apice, "perche"
# seguito da apice, la "e" verbo seguita da apice. In italiano nessuna parola
# finisce con vocale più apostrofo, tranne il troncamento `po'` e qualche
# imperativo (`va'`, `fa'`, `di'`), che qui non compare mai.
# Le elisioni non c'entrano: hanno l'apostrofo dopo una consonante (`l'anno`).
ACCENTO_APOSTROFO = re.compile(r"\b\w*[aeiouAEIOU]'(?![a-zA-Zà-ÿ])")
APOSTROFO_LEGITTIMO = {"po", "va", "fa", "da", "di", "sta"}


def _accenti(bozza):
    """Le parole in cui un accento è stato scritto come apostrofo.

    Non è una preferenza di stile: "poverta" con l'apice al posto dell'accento
    è italiano sbagliato su una pagina pubblica, e la forma giusta è
    "povertà". Serve una guardia e non basta la regola scritta, perché
    il difetto non nasce da una svista ma dall'imitazione: le istruzioni che
    il modello legge sono scritte così, e un modello forte ne copia il
    registro. La prima bozza scritta con opus aveva diciannove apostrofi e
    zero accenti, quella scritta con sonnet sullo stesso impianto ne aveva
    trentasei veri e nessun apostrofo.
    """
    pezzi = [("lead", bozza.get("lead") or "")]
    for indice, sezione in enumerate(bozza.get("sections") or []):
        pezzi.append((f"sezione {indice} (titolo)", sezione.get("h") or ""))
        pezzi.append((f"sezione {indice}", sezione.get("body") or ""))
    problemi = []
    for dove, testo in pezzi:
        parole = sorted({t for t in ACCENTO_APOSTROFO.findall(testo)
                         if t[:-1].lower() not in APOSTROFO_LEGITTIMO})
        if parole:
            problemi.append(f"{dove}: accento scritto come apostrofo in {', '.join(parole)}")
    return problemi


def _valida(bozza):
    """Gli errori che rendono l'articolo invisibile o rotto. Nient'altro."""
    problemi = _accenti(bozza)
    if not (bozza.get("lead") or "").strip():
        problemi.append("manca il lead")
    sezioni = bozza.get("sections") or []
    if not sezioni:
        problemi.append("nessuna sezione")
    for indice, sezione in enumerate(sezioni):
        if sezione.get("role") not in RUOLI:
            problemi.append(f"sezione {indice}: ruolo '{sezione.get('role')}' "
                            f"non fra {', '.join(RUOLI)}")
        if not (sezione.get("body") or "").strip():
            problemi.append(f"sezione {indice}: corpo vuoto")
    for indice, fonte in enumerate(bozza.get("fonti") or []):
        if not (fonte.get("url") or "").strip() or not (fonte.get("testo") or "").strip():
            problemi.append(f"fonte {indice}: servono testo e url")
    return problemi


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
    testo = " ".join([entry.get("lead") or ""] +
                     [s.get("body") or "" for s in entry.get("sections") or []])
    return len(testo.split())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("codice")
    parser.add_argument("--bozza", required=True, help="percorso della bozza congelata")
    parser.add_argument("--livello", default=None)
    parser.add_argument("--out", default=ARTICOLI, help=f"cartella (default {ARTICOLI})")
    args = parser.parse_args(argv)

    with open(args.bozza, encoding="utf-8") as handle:
        bozza = json.load(handle)

    problemi = _valida(bozza)
    if problemi:
        json.dump({"scritto": False, "problemi": problemi}, sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 2

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
        "sovrascritto": prima is not None,
        "vintage_precedente": (prima or {}).get("vintage"),
        "percorso": os.path.abspath(percorso),
        "chiave": chiave,
        "livello": entry["level"],
        "vintage": entry["vintage"],
        "parole": _parole(entry),
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
