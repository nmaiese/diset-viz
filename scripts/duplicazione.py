"""Quanto testo di una scheda indicatore si legge identico su altre schede.

Il numero che serviva e non c'era. Un revisore esterno, umano o automatico, non
giudica la pagina migliore: guarda un campione e si chiede se sta leggendo
trecento volte la stessa pagina con dei numeri diversi. Finche' non si misura,
"le schede si somigliano" resta un'impressione, e l'unico modo di rispondere e'
aprirne due accanto.

**Due numeri, non uno, e il secondo e' li' per onesta'.** Il metodo di una
scheda (come si legge il valore, su che perimetro vale il confronto, in che
verso va la graduatoria) e' giusto che sia la stessa frase ovunque, e vive nel
riquadro "Come leggere il dato". Se lo si misurasse insieme al racconto,
spostare una frase dall'uno all'altro farebbe scendere il numero senza che
niente sia cambiato per chi legge: una misura che premia lo spostamento e'
peggio di nessuna misura.

Quindi:

- **racconto**: solo il blocco articolo, cioe' la prosa che racconta questi
  numeri. E' il numero che deve scendere;
- **racconto e metodo**: articolo piu' riquadro. Scende solo se la ripetizione
  sparisce davvero, non se cambia stanza.

Fuori da tutti e due: testata, cruscotto, tabelle, apparato e navigazione, che
sono uguali per costruzione ed e' giusto che lo siano.

Il testo si spezza in sequenze di otto parole, e una sequenza e' ripetuta
quando compare su piu' di `SOGLIA_PAGINE` pagine. Otto parole perche' sotto le
cinque pescano incisi comuni della lingua ("in tutti i territori e per"), sopra
le dieci lasciano passare la stessa frase con un nome di regione dentro.

`quota_ripetuta` e' la percentuale di parole che vivono dentro una sequenza
condivisa. Non deve arrivare a zero e non ci arrivera'. Deve scendere quando
l'apparato esce dal racconto, e non deve risalire dopo.

    bin/py scripts/duplicazione.py --summary
    bin/py scripts/duplicazione.py --frasi 20

Pure stdlib piu' l'app, come il resto della catena.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FINESTRA = 8
SOGLIA_PAGINE = 5

_ARTICOLO = re.compile(r'<div class="indicator-article prose">.*?</div>', re.S)
_COME_LEGGERE = re.compile(r'<section class="come-leggere".*?</section>', re.S)
_TAG = re.compile(r"<[^>]+>")
_SPAZI = re.compile(r"\s+")


def _parole(frammenti):
    if not frammenti:
        return []
    testo = html.unescape(_TAG.sub(" ", " ".join(frammenti)))
    return _SPAZI.sub(" ", testo).strip().split()


def _prosa(pagina):
    """(racconto, racconto piu' metodo) di una scheda."""
    articolo = _ARTICOLO.search(pagina)
    metodo = _COME_LEGGERE.search(pagina)
    racconto = _parole([articolo.group(0)] if articolo else [])
    con_metodo = _parole(
        [t.group(0) for t in (articolo, metodo) if t])
    return racconto, con_metodo


def _sequenze(parole):
    return [tuple(parole[i:i + FINESTRA]) for i in range(len(parole) - FINESTRA + 1)]


def _quota(corpora):
    """Quanta parte delle parole vive dentro una sequenza condivisa."""
    su_quante = Counter()
    for parole in corpora:
        su_quante.update(set(_sequenze(parole)))
    ripetute = {seq for seq, quante in su_quante.items() if quante > SOGLIA_PAGINE}

    totali = ripetute_conto = 0
    for parole in corpora:
        totali += len(parole)
        coperte = set()
        for indice, sequenza in enumerate(_sequenze(parole)):
            if sequenza in ripetute:
                coperte.update(range(indice, indice + FINESTRA))
        ripetute_conto += len(coperte)

    return {
        "parole_medie": round(totali / len(corpora)) if corpora else 0,
        "sequenze": len(ripetute),
        "quota": round(100 * ripetute_conto / totali, 1) if totali else 0.0,
        "peggiori": su_quante.most_common(),
    }


def misura(limite=None, base_only=False):
    """Le due quote sulle pagine di livello indicizzabili.

    Una voce per pagina (`indicator_universe.level_pages`): le `/province`
    delle schede a due livelli sono URL a se', e si misurano come le altre.
    `base_only` tiene le sole basi delle schede, il perimetro su cui sono
    tarati i tetti della prova (`tests/integration/test_duplicazione_schede.py`).
    """
    from app import app, indicator_universe

    client = app.test_client()
    racconti, con_metodo = [], []
    letti = 0
    for vista in indicator_universe.level_pages():
        if base_only and not vista["base"]:
            continue
        percorso = vista["path"]
        risposta = client.get(percorso, follow_redirects=True)
        if risposta.status_code != 200:
            continue
        racconto, intero = _prosa(risposta.get_data(as_text=True))
        if not racconto:
            continue
        racconti.append(racconto)
        con_metodo.append(intero)
        letti += 1
        if limite and letti >= limite:
            break

    return {"pagine": letti,
            "racconto": _quota(racconti),
            "con_metodo": _quota(con_metodo)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--summary", action="store_true",
                        help="solo il numero da confrontare con l'ultima volta")
    parser.add_argument("--frasi", type=int, default=0,
                        help="le N sequenze presenti sul maggior numero di pagine")
    parser.add_argument("--limite", type=int, default=0,
                        help="quante pagine leggere, per una prova veloce")
    args = parser.parse_args(argv)

    esito = misura(limite=args.limite or None)
    print(f"pagine lette              {esito['pagine']}")
    for etichetta, chiave in (("racconto", "racconto"), ("racconto e metodo", "con_metodo")):
        blocco = esito[chiave]
        print(f"{etichetta:25s} {blocco['parole_medie']:4d} parole in media, "
              f"{blocco['quota']:5.1f}% ripetuto, {blocco['sequenze']} sequenze condivise")
    if args.summary:
        return 0
    for sequenza, quante in esito["racconto"]["peggiori"][:args.frasi]:
        print(f"  [{quante:4d}] {' '.join(sequenza)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
