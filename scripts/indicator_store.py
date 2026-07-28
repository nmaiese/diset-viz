#!/usr/bin/env python3
"""Gli articoli delle pagine indicatore, un file per articolo.

Prima stavano tutti dentro `app/static/data/indicator_texts.json`, un oggetto
solo da 365 voci e mezzo megabyte, e il formato era la causa di due guasti
distinti che sembravano scollegati.

**Il primo e' la concorrenza.** Scrittore e revisore condividono il perimetro:
sono gli unici due stadi che possono scrivere la prosa, girano tutti e due
ogni giorno, e ogni loro modifica riscriveva l'intero file. Due run vicine su
due articoli diversi producevano due versioni complete dello stesso oggetto, e
il merge riusciva solo finche' le due voci erano lontane abbastanza nel testo.
Quando non lo erano, il conflitto arrivava su un file che nessun agente puo'
risolvere leggendolo, perche' e' un JSON serializzato di seicento chilobyte.
Con un file per articolo il conflitto non e' improbabile, e' **impossibile**:
due stadi che lavorano su articoli diversi toccano percorsi diversi, e git non
ha niente da fondere. Restano contendibili solo le modifiche allo stesso
articolo, che e' l'unico caso in cui un conflitto significa davvero qualcosa e
va letto.

**Il secondo e' la leggibilita' del diff.** La revisione di una frase compariva
come un hunk dentro un file enorme, senza che il diff dicesse di quale
indicatore si stesse parlando: il `git show` di una run del revisore era
illeggibile, e la history per articolo non esisteva. Adesso
`git log content/indicators/ter__920.json` e' la storia editoriale di quella
pagina, e basta.

## Il formato

    content/indicators/<chiave>.json

dove `<chiave>` e' la chiave interna con i due punti scritti `__`, perche' i
due punti sono ostili come nome di file e nessuna chiave del catalogo contiene
gia' un doppio underscore (le sigle Multiscopo ne usano uno solo). La codifica
e' quindi reversibile senza ambiguita' e senza tabelle:

    1                        ->  content/indicators/1.json
    bes:10AMB004             ->  content/indicators/bes__10AMB004.json
    bes:09PAE009-N25         ->  content/indicators/bes__09PAE009-N25.json
    multiscopo:MULTI_BMI_OBESI -> content/indicators/multiscopo__MULTI_BMI_OBESI.json

Dentro il file ci sono gli stessi campi di prima (`lead`, `sections`, `fonti`,
`vintage`, e per gli articoli firmati `level`, `reviewed_at`,
`reviewed_vintage`), piu' `key`, che ripete la chiave. Il campo `key` non fa
parte del modello e `load_all` lo toglie: serve solo perche' un file aperto a
mano dica di che cosa parla, e perche' un file rinominato per sbaglio sia
riconoscibile invece che silenziosamente perduto.

Quello che **non** e' cambiato: una voce vale per un livello territoriale solo,
e il livello resta un campo dentro la voce (`level`, default `regione`). Il
modello resta una voce per indicatore, non una per coppia (indicatore,
livello). Era cosi' prima e resta cosi' adesso, di proposito: cambiare il
modello dei dati dentro una modifica che serve a togliere i conflitti avrebbe
mescolato due cose che vanno potute rileggere separate.

Stdlib puro e senza nessun import di `app`, perche' lo leggono sia l'app Flask
sia gli script della catena, che girano su un checkout senza venv. Sta in
`scripts/` e non in `app/` proprio per questo: `app/__init__.py` importa Flask,
quindi `from app import ...` e' fuori portata per meta' dei suoi lettori.

    python3 scripts/indicator_store.py --list
    python3 scripts/indicator_store.py --show ter-920
    python3 scripts/indicator_store.py --migrate app/static/data/indicator_texts.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ROOT = PROJECT_ROOT / "content" / "indicators"

# Il vecchio file unico, non piu' in repo: il travaso e' avvenuto e la sua
# storia vive in git. Il percorso resta perche' `--migrate` funzioni su un
# checkout vecchio, e perche' dica da dove vengono questi file.
#
# Stava sotto `app/static/`, quindi era anche servito in chiaro come risorsa
# statica pubblica. La prosa non e' un artefatto dell'app: sta in `content/`,
# accanto ai post del blog, che e' dove il resto dei testi vive gia'.
LEGACY_PATH = PROJECT_ROOT / "app" / "static" / "data" / "indicator_texts.json"

# La codifica della chiave nel nome del file. Una costante e non un letterale
# sparso, perche' compare in tutte e due le direzioni e sbagliarne una sola
# renderebbe invisibile meta' del catalogo senza nessun errore.
NAMESPACE_SEP = ":"
FILENAME_SEP = "__"

# Il campo che ripete la chiave dentro il file. Fuori dal modello: `load_all`
# lo toglie, cosi' quello che i consumatori vedono e' esattamente il dizionario
# che vedevano prima.
KEY_FIELD = "key"


class StoreError(RuntimeError):
    """Un file dello store non e' leggibile o non e' dove dovrebbe."""


def filename_for(key: str) -> str:
    """Il nome del file che contiene l'articolo di `key`."""
    key = str(key)
    if FILENAME_SEP in key:
        raise StoreError(
            f"la chiave '{key}' contiene '{FILENAME_SEP}', che e' il separatore "
            "usato nei nomi di file: non e' codificabile senza ambiguita'"
        )
    return key.replace(NAMESPACE_SEP, FILENAME_SEP) + ".json"


def key_of(path) -> str:
    """La chiave dell'articolo contenuto in `path`, dal solo nome del file."""
    return Path(path).stem.replace(FILENAME_SEP, NAMESPACE_SEP)


def path_for(key: str, root=None) -> Path:
    return Path(root or ROOT) / filename_for(key)


def paths(root=None):
    """Tutti i file di articolo, in ordine stabile."""
    base = Path(root or ROOT)
    if not base.is_dir():
        return []
    return sorted(base.glob("*.json"))


def load_all(root=None, strict=True) -> dict:
    """Tutti gli articoli, come `{chiave: voce}`.

    E' esattamente il dizionario che `json.load` restituiva sul file unico, e
    lo e' di proposito: ogni consumatore e' passato da una riga di `json.load`
    a una chiamata qui senza toccare altro, e `tests/unit/test_indicator_store.py`
    verifica che le due letture coincidano.

    `root` accetta anche un vecchio file unico, come `read_journal` accetta un
    `.jsonl` e `load_verifications` un `.csv`. Serve alla migrazione e ai test,
    che di un catalogo intero hanno bisogno di scrivere due voci.

    `strict` decide che cosa costa un file rotto, e la risposta giusta dipende
    da chi chiede. Per il cancello, per la suite e per chi lavora sulla catena
    un file illeggibile deve fermare tutto, forte: e' un difetto e va visto.
    Per l'**app** no, e la differenza e' grossa. Con `strict` un solo file mal
    scritto solleva, il chiamante ripiega su un dizionario vuoto, e tutte e
    trecentosessantacinque le pagine perdono la prosa insieme senza che si
    veda un errore da nessuna parte. Un articolo rotto deve costare un
    articolo, non il catalogo, e a trovarlo ci pensa la suite, che gira in
    `strict`.
    """
    base = Path(root or ROOT)
    if base.is_file():
        data = json.loads(base.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise StoreError(f"{base.name} non contiene un oggetto JSON")
        return {k: {f: v for f, v in entry.items() if f != KEY_FIELD}
                for k, entry in data.items()}
    entries = {}
    for path in paths(root):
        key = key_of(path)
        try:
            if key in entries:
                raise StoreError(f"due file per la stessa chiave '{key}'")
            entries[key] = _read_file(path, key)
        except StoreError:
            if strict:
                raise
    return entries


def read(key: str, root=None):
    """La voce di un articolo, o None se nessuno l'ha ancora scritto."""
    path = path_for(key, root=root)
    if not path.exists():
        return None
    return _read_file(path, key)


def resolve_key(keys, code):
    """La chiave interna di un codice scritto in una delle due forme, o None.

    La catena scrive i codici nella forma URL (`ter-920`, `bes-10AMB004`), lo
    store li tiene in quella interna (`920`, `bes:10AMB004`). Un comando che
    accetta solo la seconda risponde "nessun articolo" proprio all'invocazione
    scritta nei prompt, e chi la incontra o la aggira o salta il passo: in
    nessuno dei due casi resta una traccia.

    Sta qui perche' questo modulo possiede le chiavi e la loro codifica, ed e'
    la terza volta che questo difetto compare in questo repo. Le prime due hanno
    prodotto due copie della stessa funzione in due file. `prose_lint` adesso
    delega qui invece di tenerne una propria.

    L'acronimo di famiglia si confronta con le chiavi che esistono davvero, mai
    con una tabella di prefissi: quella la possiede `app/sources.py`, e questo
    modulo deve restare importabile senza Flask.
    """
    keys = set(keys)
    code = str(code)
    if code in keys:
        return code
    if "-" not in code:
        return None
    _, raw = code.split("-", 1)
    matches = [key for key in keys if key.split(NAMESPACE_SEP, 1)[-1] == raw]
    return matches[0] if len(matches) == 1 else None


def write(key: str, entry: dict, root=None) -> Path:
    """Scrive (o riscrive) l'articolo di `key`. Ritorna il percorso toccato.

    Ordina le chiavi e chiude con un a capo, come faceva il dump del file
    unico: un file che cambia ordine a ogni scrittura produrrebbe diff che non
    dicono niente, ed e' meta' del motivo per cui questo store esiste.
    """
    path = path_for(key, root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {KEY_FIELD: str(key)}
    payload.update({k: v for k, v in entry.items() if k != KEY_FIELD})
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def remove(key: str, root=None) -> bool:
    path = path_for(key, root=root)
    if not path.exists():
        return False
    path.unlink()
    return True


def _read_file(path: Path, key: str) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise StoreError(f"{path.name} non e' leggibile: {type(exc).__name__}") from exc
    if not isinstance(data, dict):
        raise StoreError(f"{path.name} non contiene un oggetto JSON")
    declared = data.get(KEY_FIELD)
    if declared is not None and str(declared) != key:
        # Un file rinominato a mano, o scritto sotto il nome sbagliato. Detto
        # invece che ignorato: la voce sarebbe raggiungibile con una chiave e
        # descriverebbe un altro indicatore, che e' il modo peggiore di
        # sbagliare perche' la pagina si renderizza lo stesso.
        raise StoreError(
            f"{path.name} dichiara la chiave '{declared}' ma il nome del file dice '{key}'"
        )
    return {k: v for k, v in data.items() if k != KEY_FIELD}


def migrate(legacy_path=None, root=None) -> int:
    """Travasa il vecchio file unico nello store. Ritorna quanti articoli."""
    source = Path(legacy_path or LEGACY_PATH)
    data = json.loads(source.read_text(encoding="utf-8"))
    for key, entry in data.items():
        write(key, entry, root=root)
    return len(data)


def main():
    parser = argparse.ArgumentParser(description="Lo store degli articoli, un file per indicatore.")
    parser.add_argument("--list", action="store_true", help="le chiavi presenti")
    parser.add_argument("--show", metavar="CHIAVE", help="una voce, in JSON")
    parser.add_argument("--migrate", metavar="FILE", nargs="?", const=str(LEGACY_PATH),
                        help="travasa il vecchio file unico nello store")
    args = parser.parse_args()

    if args.migrate:
        count = migrate(args.migrate)
        print(f"{count} articoli scritti in {ROOT.relative_to(PROJECT_ROOT)}/")
        return 0
    entries = load_all()
    if args.show:
        key = resolve_key(entries, args.show)
        if key is None:
            print(f"nessun articolo per '{args.show}'", file=sys.stderr)
            return 1
        print(json.dumps(entries[key], ensure_ascii=False, indent=2))
        return 0
    if args.list:
        for key in sorted(entries):
            print(key)
        return 0
    authored = sum(1 for e in entries.values() if (e.get("lead") or "").strip())
    signed = sum(1 for e in entries.values() if (e.get("reviewed_at") or "").strip())
    print(f"{len(entries)} articoli, {authored} con lead scritto, {signed} firmati dal revisore")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        # `--list | head` chiude la pipe mentre stiamo ancora stampando. Non e'
        # un errore del programma, e lasciare uscire il traceback fa sembrare
        # rotto un comando che ha funzionato.
        sys.stderr.close()
        raise SystemExit(0)
