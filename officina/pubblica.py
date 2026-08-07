"""Scrive in `content/indicators/` una bozza gia' decisa. Un comando, niente giudizio.

Perche' esiste. Il pubblicatore riceveva la bozza come oggetto e doveva
comporre da solo l'entry dello store: chiave interna, livello, vintage, forma
del file. Nessuna di quelle quattro cose e' una decisione editoriale, e per
scoprirle apriva `scripts/indicator_store.py`, i template e le viste. Otto turni
nella prova, ventuno e ventiquattro nella prima run, per far uscire zero a un
linter. Un turno che scopre una cosa che il codice gia' sa si paga due volte,
perche' tutti i turni successivi lo rileggono.

Qui la mappa bozza -> entry e' codice, quindi e' la stessa a ogni articolo:

    bin/py -m officina.pubblica ter-30 <<'BOZZA'
    {"lead": "...", "sections": [...], "corpus": [], "angolo": "..."}
    BOZZA

Rifiuta invece di scrivere male. Un ruolo fuori dai quattro, una sezione senza
corpo, un codice che non e' nel catalogo: esce 2 e dice quale, perche' una
guardia che accetta cio' che non capisce non e' una guardia (e' successo con
`officina.lint ter-176`, che selezionava zero articoli e stampava zero rilievi).

Non decide niente di editoriale: non tocca il testo, non riordina le sezioni,
non aggiunge fonti. `roles_covered` non lo scrive **apposta**: lo deriva
`app.indicator_texts.emitted_roles` dalle sezioni scritte, e dichiararlo qui
sarebbe la seconda copia della stessa lista, cioe' il modo per farle divergere.
"""
from __future__ import annotations

import argparse
import json
import sys

from app import sources
from app.indicator_texts import DEFAULT_LEVEL
from app.indicator_view import build_indicator_view
from scripts import indicator_store, verification_queue

RUOLI = ("definizione", "quadro", "dinamica", "limiti")
# Cio' che passa dalla bozza all'entry, e nient'altro. Un campo in piu' nella
# risposta di un agente non deve poter finire in un file pubblicato.
CAMPI = ("lead", "sections", "corpus", "angolo")
CAMPI_SEZIONE = ("role", "h", "body", "claims")


class Rifiutata(Exception):
    """La bozza non si scrive, e il messaggio dice quale riga la ferma."""


def chiave(code: str) -> str:
    """La chiave interna dello store per un codice in forma URL (`ter-30`)."""
    parsed = sources.parse_indicator_code(code)
    if not parsed:
        raise Rifiutata(f"'{code}' non e' un codice indicatore (atteso es. ter-30, bes-10AMB004)")
    family, raw_id = parsed
    return sources.internal_id(family, raw_id)


def livello(code: str, level: str | None):
    """(chiave del livello, ultimo anno). Solleva se l'indicatore o il livello non esiste."""
    parsed = sources.parse_indicator_code(code)
    view = build_indicator_view(*parsed) if parsed else None
    if view is None:
        raise Rifiutata(f"'{code}' non e' nel catalogo")
    wanted = level or DEFAULT_LEVEL
    trovato = next((lv for lv in view["levels"] if lv["key"] == wanted), None)
    if trovato is None:
        disponibili = ", ".join(lv["key"] for lv in view["levels"])
        raise Rifiutata(f"'{code}' non ha il livello '{wanted}' (ha: {disponibili})")
    return wanted, trovato["year_max"]


def entry(bozza: dict, code: str, level: str | None = None) -> dict:
    """L'entry dello store per una bozza. Solleva `Rifiutata` invece di indovinare."""
    if not isinstance(bozza, dict):
        raise Rifiutata("la bozza non e' un oggetto JSON")
    if not (bozza.get("lead") or "").strip():
        raise Rifiutata("la bozza non ha un lead")
    sezioni = bozza.get("sections")
    if not isinstance(sezioni, list) or not sezioni:
        raise Rifiutata("la bozza non ha sezioni")

    pulite = []
    for indice, sezione in enumerate(sezioni):
        if not isinstance(sezione, dict):
            raise Rifiutata(f"la sezione {indice} non e' un oggetto")
        ruolo = sezione.get("role")
        if ruolo not in RUOLI:
            raise Rifiutata(f"ruolo '{ruolo}' nella sezione {indice}: i ruoli sono {', '.join(RUOLI)}")
        if not (sezione.get("body") or "").strip():
            raise Rifiutata(f"la sezione '{ruolo}' non ha corpo")
        # Una sezione per ruolo. Al primo giro della macchina nuova sono uscite
        # due `dinamica` con due titoli diversi: la pagina ne rendeva una due
        # volte e perdeva l'altra, perche' il renderer indicizzava per ruolo.
        # Il renderer ora regge il caso, ma il contratto resta uno: due sezioni
        # sullo stesso ruolo vanno unite in una, ed e' chi scrive a doverlo
        # fare, non chi rende.
        if any(fatta["role"] == ruolo for fatta in pulite):
            raise Rifiutata(f"due sezioni con ruolo '{ruolo}': uniscile in una")
        pulite.append({campo: sezione[campo] for campo in CAMPI_SEZIONE if sezione.get(campo)})

    chiave_livello, anno = livello(code, level)
    fatta = {campo: bozza[campo] for campo in CAMPI if bozza.get(campo)}
    fatta["sections"] = pulite
    fatta["level"] = chiave_livello
    fatta["vintage"] = anno
    # **`origine` non si mette qui.** Vedi `bloccanti`: il campo apre due code a
    # valle, e metterlo mentre si monta il dizionario vuol dire metterlo prima
    # che il cancello abbia parlato.
    return fatta


def bloccanti(key: str, fatta: dict) -> list:
    """I rilievi `blocca` del cancello editoriale su questa bozza.

    Serve a decidere se scriverle `origine`, e non e' un dettaglio di
    contabilita': `origine: officina` e' l'**unica** condizione che rende un
    articolo idoneo per la coda di verifica (`verification_queue.py:391`) e per
    quella di lettura (`reading_queue.py:358`), perche' l'officina non ha un
    revisore che firmi. Il campo si scriveva mentre si montava il dizionario,
    cioe' prima che il lint girasse, e un articolo bocciato lo portava lo
    stesso: finiva in tutte e due le code, veniva reso dall'app, e i due critici
    indipendenti sprecavano un giro su una prosa gia' respinta.

    Il cancello resta uno solo. Qui non c'e' una seconda regola: gira lo stesso
    `lint_entry` che gira `officina.lint`, sullo stesso store con la bozza
    gia' sostituita al proprio posto, cosi' i due verdetti non possono divergere.

    **Su una prima pubblicazione l'articolo bocciato si scrive comunque**, e
    senza il campo: li' non c'e' niente da proteggere, e rifiutare perderebbe
    l'unica copia della bozza. Su una **riscrittura** no, vedi `main`.
    """
    return [rilievo for rilievo in tutti_i_rilievi(key, fatta)
            if rilievo["severity"] == "blocca"]


def tutti_i_rilievi(key: str, fatta: dict) -> list:
    """Il verdetto intero del cancello editoriale su questa bozza, `segnala`
    compresi.

    Esiste perche' e' l'unico verdetto che parla della **bozza**. Il passo di
    lint del pubblicatore rilegge l'articolo da disco, quindi quando la
    scrittura viene rifiutata (`main`) descrive il testo precedente: i rilievi
    da rimandare a chi riscrive devono venire da qui, non da li'.
    """
    from officina import lint

    try:
        texts = dict(indicator_store.load_all())
        texts[key] = fatta
        alternation = lint.territory_alternation(texts)
        compiled = lint.patterns(alternation)
        compiled["alternation"] = alternation
        return lint.lint_entry(key, fatta, texts=texts, compiled=compiled)
    except Exception as errore:  # noqa: BLE001
        # Un cancello che non riesce a girare non e' un cancello verde. Il
        # verso di questa guardia e' scelto: **non** si scrive `origine`, cosi'
        # un guasto qui non promuove niente. La scrittura invece prosegue,
        # perche' prima di questa funzione avveniva sempre, e far sparire
        # l'articolo per un errore del lint sarebbe una regressione peggiore
        # del difetto che stiamo chiudendo.
        return [_finding_di_guasto(errore)]


def _finding_di_guasto(errore: BaseException) -> dict:
    return {"rule": "cancello-non-eseguibile", "severity": "blocca",
            "detail": f"{type(errore).__name__}: {errore}"[:300], "field": None}


def _guasto_del_cancello(fermi: list) -> bool:
    """Il cancello non ha girato, invece di aver bocciato."""
    return any(rilievo["rule"] == "cancello-non-eseguibile" for rilievo in fermi)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("code", help="il codice in forma URL, es. ter-30")
    parser.add_argument("--level", default=None, help=f"default {DEFAULT_LEVEL}")
    parser.add_argument("--bozza", default=None,
                        help="un file JSON invece di stdin")
    args = parser.parse_args(argv)

    testo = open(args.bozza, encoding="utf-8").read() if args.bozza else sys.stdin.read()
    try:
        bozza = json.loads(testo)
    except json.JSONDecodeError as errore:
        print(f"bozza non leggibile come JSON: {errore}", file=sys.stderr)
        return 2

    try:
        fatta = entry(bozza, args.code, args.level)
        key = chiave(args.code)
        esiste_gia = key in indicator_store.load_all()
        rilievi = tutti_i_rilievi(key, fatta)
        fermi = [r for r in rilievi if r["severity"] == "blocca"]
        if fermi and esiste_gia:
            # **Una riscrittura bocciata non sostituisce l'articolo che c'era.**
            #
            # Vale a ogni tentativo, e non solo all'ultimo, perche' e' il
            # **primo** a fare il danno: dopo di lui l'articolo buono non c'e'
            # piu', e qualunque prudenza successiva starebbe proteggendo una
            # bozza gia' bocciata. Una versione precedente rifiutava solo la
            # seconda scrittura, e non serviva a niente.
            #
            # Perche' si puo' rifiutare senza rompere il giro di riparazione:
            # i rilievi si stampano qui sotto. Erano il motivo per cui la
            # scrittura doveva avvenire comunque, visto che il passo successivo
            # del pubblicatore li rileggeva da disco con `officina.lint`, e su
            # un articolo non sovrascritto avrebbe descritto il testo vecchio
            # attribuendone i rilievi alla bozza nuova. Stampati qui parlano
            # della bozza, che e' l'unica cosa che chi riscrive puo' correggere.
            #
            # **Anche un guasto del cancello**, e prima non era cosi'. La regola
            # "un guasto non deve costare una scrittura" nasce sulla prima
            # pubblicazione, dove rifiutare perderebbe l'unica copia della
            # bozza; su una riscrittura si rovescia, perche' li' scrivere costa
            # l'articolo **precedente**, sostituito da un testo che nessuno ha
            # potuto controllare. La bozza non e' persa in nessuno dei due casi:
            # il workflow la riporta e la run puo' ripartire. L'articolo buono
            # si', e solo da git.
            #
            # La regola diventa quindi una sola, che vale per ogni rilievo
            # bloccante: **un articolo che esiste non viene mai sostituito da
            # qualcosa che il cancello non ha passato.**
            # **Tutte e due le righe sullo stesso flusso, e non e' pignoleria.**
            # Con l'uscita catturata (un agente non e' un terminale) stdout e'
            # a blocchi e stderr no, quindi una riga su stdout e una su stderr
            # arrivano a chi legge in ordine invertito. Il contratto del
            # pubblicatore riconosce i rilievi da una riga `RILIEVI`, e con
            # l'ordine rovesciato avrebbe riportato una lista vuota, mandando la
            # riscrittura al giro sbagliato: `ilRifiuto` invece di `ilBlocco`,
            # cioe' "correggi la forma" al posto dei rilievi editoriali veri.
            print("non scritta: il cancello blocca su "
                  + ", ".join(sorted({rilievo["rule"] for rilievo in fermi}))
                  + f", e l'articolo precedente e' rimasto al suo posto ({key}). "
                  + "Nessuna versione buona e' stata sovrascritta, e i rilievi "
                  + "qui sotto sono della bozza, non di cio' che c'e' su disco.",
                  file=sys.stderr)
            print("RILIEVI " + json.dumps(rilievi, ensure_ascii=False),
                  file=sys.stderr)
            return 2
        if not fermi:
            fatta["origine"] = verification_queue.OFFICINA
        path = indicator_store.write(key, fatta)
    except Rifiutata as errore:
        print(f"non scritta: {errore}", file=sys.stderr)
        return 2

    print(path)
    if fermi:
        # Scritta, e senza `origine`: non entra in nessuna coda finche' il
        # cancello non passa. Il verdetto per esteso lo stampa `officina.lint`,
        # che il workflow esegue subito dopo: qui basta dire che e' successo.
        print("scritta SENZA `origine`: il cancello blocca su "
              + ", ".join(sorted({rilievo["rule"] for rilievo in fermi}))
              + ". Non entra nella coda di verifica ne' in quella di lettura.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
