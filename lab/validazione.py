"""I controlli che una bozza deve passare, in un posto solo, e prima del disco.

Sono deterministici, senza modello in mezzo: un accento scritto come apostrofo,
un lead che manca, un corpo vuoto, un ruolo che la pagina non rende, una fonte
senza url. Le prime quattro cose che rendono un articolo sbagliato o invisibile
senza che nulla fallisca.

Vivevano dentro `lab/pubblica.py` e li vedeva solo il pubblicatore, cioe'
**l'unico passo dopo il quale non si puo' piu' correggere niente**. Una run
intera (`wf_32afde53-c4e`, 4,10 $, 11 agenti, 42 turni) e' finita cosi': verifica
pulita a tre passaggi, tutte e cinque le classi passate, nessuna cifra inventata,
e il file mai scritto per un `adeguata'` in una sezione. Che per giunta era una
**citazione**, non un accento sbagliato: il difetto costava la run, e non c'era
nemmeno.

Adesso li esegue `lab.controlla`, cioe' chi verifica, dove il testo si corregge e
il giro riparte. `lab.pubblica` li conta e li stampa, e non rifiuta piu': un
controllo che ferma dove non si puo' riparare non protegge la pagina, butta il
lavoro.

Il metro della prosa (`lab.lint`) resta un'altra cosa: quello misura e non ferma
per scelta, questo dice che cosa va riparato prima di scrivere.
"""
from __future__ import annotations

import re

# I quattro ruoli che la pagina indicatore sa rendere. Una sezione con un ruolo
# diverso verrebbe scartata in silenzio dal template.
RUOLI = ("definizione", "quadro", "dinamica", "limiti")

# Un accento scritto con l'apostrofo: "poverta" seguito da apice, "perche"
# seguito da apice, la "e" verbo seguita da apice. In italiano nessuna parola
# finisce con vocale piu' apostrofo, tranne il troncamento `po'` e qualche
# imperativo (`va'`, `fa'`, `di'`), che qui non compare mai.
# Le elisioni non c'entrano: hanno l'apostrofo dopo una consonante (`l'anno`).
ACCENTO_APOSTROFO = re.compile(r"\b\w*[aeiouAEIOU]'(?![a-zA-Zà-ÿ])")
APOSTROFO_LEGITTIMO = {"po", "va", "fa", "da", "di", "sta"}


def _chiusure(testo):
    """Le posizioni dei `'` che **chiudono una citazione**, non un accento.

    `'non adeguata'` e' una frase citata, e il secondo apice sta dopo una vocale
    esattamente come l'errore che questa guardia cerca: la regex da sola non
    puo' distinguerli, e infatti ha fermato una run intera su una citazione
    scritta bene (`wf_32afde53-c4e`, verifica pulita a tre passaggi).

    Un apice **apre** se ha davanti uno spazio o un segno e dietro una lettera;
    da li' in poi il primo apice che ha dietro qualcosa che non e' una lettera
    **chiude**. Un accento sbagliato (`poverta'`) non apre mai, perche' ha una
    lettera davanti, quindi resta segnalato; e un'elisione (`l'anno`) non entra
    ne' da una parte ne' dall'altra, perche' ha lettere da tutte e due i lati.
    """
    chiusure, aperta = set(), None
    for posizione, carattere in enumerate(testo):
        if carattere != "'":
            continue
        prima = testo[posizione - 1] if posizione else " "
        dopo = testo[posizione + 1] if posizione + 1 < len(testo) else " "
        if aperta is None:
            if not prima.isalnum() and dopo.isalpha():
                aperta = posizione
        elif not dopo.isalpha():
            chiusure.add(posizione)
            aperta = None
    return chiusure


def accenti(bozza):
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
        chiusure = _chiusure(testo)
        parole = sorted({trovato.group(0) for trovato in ACCENTO_APOSTROFO.finditer(testo)
                         if trovato.group(0)[:-1].lower() not in APOSTROFO_LEGITTIMO
                         and trovato.end() - 1 not in chiusure})
        if parole:
            problemi.append(f"{dove}: accento scritto come apostrofo in {', '.join(parole)}")
    return problemi


def bloccanti(bozza):
    """Gli errori che rendono l'articolo invisibile o rotto. Nient'altro."""
    problemi = accenti(bozza)
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
