#!/usr/bin/env python3
"""Gli articoli delle pagine indicatore, un file Markdown per articolo.

Prima stavano tutti dentro `app/static/data/indicator_texts.json`, un oggetto
solo da 365 voci e mezzo megabyte, e il formato era la causa di due guasti
distinti che sembravano scollegati.

**Il primo è la concorrenza.** Scrittore e revisore condividono il perimetro:
sono gli unici due stadi che possono scrivere la prosa, girano tutti e due
ogni giorno, e ogni loro modifica riscriveva l'intero file. Due run vicine su
due articoli diversi producevano due versioni complete dello stesso oggetto, e
il merge riusciva solo finché le due voci erano lontane abbastanza nel testo.
Quando non lo erano, il conflitto arrivava su un file che nessun agente può
risolvere leggendolo. Con un file per articolo il conflitto non è improbabile,
è **impossibile**: due stadi che lavorano su articoli diversi toccano percorsi
diversi, e git non ha niente da fondere. Restano contendibili solo le modifiche
allo stesso articolo, che è l'unico caso in cui un conflitto significa davvero
qualcosa e va letto.

**Il secondo è la leggibilità del diff**, ed è la ragione per cui questi file
sono Markdown e non più JSON. Un articolo in JSON tiene ogni sezione su una
riga sola con gli a capo scritti `\\n`: in una pull request il pezzo non si
legge, non si commenta riga per riga, e correggere una parola produce un hunk
che nessuno può giudicare. Il merge di quella PR è la pubblicazione, quindi il
momento in cui il testo va letto è proprio quello. In Markdown il diff di una
correzione è la riga corretta, e la PR mostra il pezzo come lo vedrà il
lettore. `git log content/indicators/17.md` resta la storia editoriale di
quella pagina, e adesso `git show` di quella storia si legge.

## Il formato

    content/indicators/<chiave>.md

dove `<chiave>` è la chiave interna con i due punti scritti `__`, perché i
due punti sono ostili come nome di file e nessuna chiave del catalogo contiene
già un doppio underscore (le sigle Multiscopo ne usano uno solo). La codifica
è quindi reversibile senza ambiguità e senza tabelle:

    1                        ->  content/indicators/1.md
    bes:10AMB004             ->  content/indicators/bes__10AMB004.md
    bes:09PAE009-N25         ->  content/indicators/bes__09PAE009-N25.md
    multiscopo:MULTI_BMI_OBESI -> content/indicators/multiscopo__MULTI_BMI_OBESI.md

Dentro il file:

    ---
    key: "17"
    level: "regione"
    vintage: 2025
    fonti:
      - testo: "Istat, Banca dati territoriale"
        url: "https://www.istat.it/..."
    ---

    Il lead, che è tutto il testo prima della prima sezione.

    <!-- sezione: definizione -->
    ## Chi finisce dentro questo numero

    Il corpo della sezione.

Il frontmatter porta ogni campo dell'entry **tranne** `lead` e `sections`, che
sono il testo: gli stessi campi di prima (`fonti`, `vintage`, e per gli
articoli firmati `level`, `reviewed_at`, `reviewed_vintage`), più `key`, che
ripete la chiave. Il campo `key` non fa parte del modello e `load_all` lo
toglie: serve solo perché un file aperto a mano dica di che cosa parla, e
perché un file rinominato per sbaglio sia riconoscibile invece che
silenziosamente perduto.

**Perché il ruolo sta in un commento e non nel titolo.** Il ruolo serve al
renderer, il titolo è di chi scrive, e sono due cose diverse: al travaso 643
sezioni su 893 non avevano titolo, e sette articoli avevano due sezioni con lo
stesso ruolo. Un marcatore separato regge tutti e tre i casi, non si disallinea
da un elenco tenuto in un'altra parte del file, e non si vede quando la pagina
è resa.

**Perché i valori del frontmatter sono JSON.** Sono un sottoinsieme di YAML
valido, ma si leggono con `json.loads` una riga alla volta: nessuna ambiguità
di virgolette, di due punti dentro un titolo, di `sì` letto come booleano. Il
file lo scrive `motore pubblica`, non una persona a mano, quindi la severità
sulla scrittura costa zero e toglie una classe intera di guasti silenziosi.

Quello che **non** è cambiato: una voce vale per un livello territoriale solo,
e il livello resta un campo dentro la voce (`level`, default `regione`). Il
modello resta una voce per indicatore, non una per coppia (indicatore,
livello).

Stdlib puro e senza nessun import di `app`, perché lo leggono sia l'app Flask
sia gli script della catena, che girano su un checkout senza venv. Sta in
`scripts/` e non in `app/` proprio per questo: `app/__init__.py` importa Flask,
quindi `from app import ...` è fuori portata per metà dei suoi lettori. Per la
stessa ragione il frontmatter non passa da `python-frontmatter`, che l'app ha
fra le dipendenze e chi lancia uno script no.

    python3 scripts/indicator_store.py --list
    python3 scripts/indicator_store.py --show ter-920
    python3 scripts/indicator_store.py --migrate app/static/data/indicator_texts.json
    python3 scripts/indicator_store.py --da-json content/indicators
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ROOT = PROJECT_ROOT / "content" / "indicators"

# Il vecchio file unico, non più in repo: il travaso è avvenuto e la sua
# storia vive in git. Il percorso resta perché `--migrate` funzioni su un
# checkout vecchio, e perché dica da dove vengono questi file.
#
# Stava sotto `app/static/`, quindi era anche servito in chiaro come risorsa
# statica pubblica. La prosa non è un artefatto dell'app: sta in `content/`,
# accanto ai post del blog, che è dove il resto dei testi vive già.
LEGACY_PATH = PROJECT_ROOT / "app" / "static" / "data" / "indicator_texts.json"

# La codifica della chiave nel nome del file. Una costante e non un letterale
# sparso, perché compare in tutte e due le direzioni e sbagliarne una sola
# renderebbe invisibile metà del catalogo senza nessun errore.
NAMESPACE_SEP = ":"
FILENAME_SEP = "__"
SUFFIX = ".md"

# Il campo che ripete la chiave dentro il file. Fuori dal modello: `load_all`
# lo toglie, così quello che i consumatori vedono è esattamente il dizionario
# che vedevano prima.
KEY_FIELD = "key"

# I due campi che sono testo e stanno nel corpo, non nel frontmatter.
TESTO = ("lead", "sections")

DELIMITER = "---"
# `<!-- sezione: quadro -->` apre una sezione. `<!-- claims: [...] -->` subito
# sotto porta un campo di sezione che non è né `role`, né `h`, né `body`: oggi
# ce n'è uno solo in tutto il catalogo, e un campo nuovo non deve costare un
# formato nuovo.
MARCATORE = re.compile(r"^<!--\s*sezione:\s*(?P<role>[^>]*?)\s*-->\s*$")
EXTRA = re.compile(r"^<!--\s*(?P<chiave>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?P<valore>.*?)\s*-->\s*$")
TITOLO = re.compile(r"^##\s+(?P<h>.+?)\s*$")


class StoreError(RuntimeError):
    """Un file dello store non è leggibile o non è dove dovrebbe."""


def filename_for(key: str) -> str:
    """Il nome del file che contiene l'articolo di `key`."""
    key = str(key)
    if FILENAME_SEP in key:
        raise StoreError(
            f"la chiave '{key}' contiene '{FILENAME_SEP}', che è il separatore "
            "usato nei nomi di file: non è codificabile senza ambiguità"
        )
    return key.replace(NAMESPACE_SEP, FILENAME_SEP) + SUFFIX


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
    return sorted(base.glob("*" + SUFFIX))


# --- il frontmatter ---------------------------------------------------------
#
# Un sottoinsieme di YAML: chiavi in ordine, valori JSON, e liste di scalari o
# di oggetti piatti. Copre tutto ciò che un'entry contiene (`fonti`, `corpus`,
# `roles_covered`, e gli scalari) e rifiuta il resto invece di inventarsi una
# resa, perché una resa inventata la si scopre rileggendo, cioè troppo tardi.


def _scalare(valore) -> str:
    if isinstance(valore, (str, int, float, bool)) or valore is None:
        return json.dumps(valore, ensure_ascii=False)
    raise StoreError(f"valore non rappresentabile nel frontmatter: {valore!r}")


def rendi_frontmatter(campi: dict) -> str:
    righe = []
    for chiave in sorted(campi):
        valore = campi[chiave]
        if isinstance(valore, list):
            if not valore:
                righe.append(f"{chiave}: []")
                continue
            righe.append(f"{chiave}:")
            for voce in valore:
                if isinstance(voce, dict):
                    sotto = sorted(voce)
                    if not sotto:
                        raise StoreError(f"{chiave}: una voce vuota non è rappresentabile")
                    righe.append(f"  - {sotto[0]}: {_scalare(voce[sotto[0]])}")
                    righe.extend(f"    {k}: {_scalare(voce[k])}" for k in sotto[1:])
                else:
                    righe.append(f"  - {_scalare(voce)}")
        elif isinstance(valore, dict):
            raise StoreError(f"{chiave}: un oggetto annidato non è rappresentabile nel frontmatter")
        else:
            righe.append(f"{chiave}: {_scalare(valore)}")
    return "\n".join(righe)


def _valore(testo: str, dove: str):
    try:
        return json.loads(testo)
    except ValueError as exc:
        raise StoreError(f"{dove}: valore non leggibile ({testo!r})") from exc


def leggi_frontmatter(righe: list[str], dove: str) -> dict:
    campi: dict = {}
    corrente = None   # la chiave della lista aperta, se ce n'è una
    for riga in righe:
        if not riga.strip():
            continue
        if riga.startswith("  - ") or riga.startswith("    "):
            if corrente is None:
                raise StoreError(f"{dove}: voce di lista senza una lista aperta ({riga!r})")
            corpo = riga.strip()
            nuova = corpo.startswith("- ")
            if nuova:
                corpo = corpo[2:]
            if ": " in corpo:
                chiave, _, resto = corpo.partition(":")
                voce = {chiave.strip(): _valore(resto.strip(), dove)}
                if nuova:
                    campi[corrente].append(voce)
                else:
                    if not campi[corrente] or not isinstance(campi[corrente][-1], dict):
                        raise StoreError(f"{dove}: campo di oggetto fuori da un oggetto ({riga!r})")
                    campi[corrente][-1].update(voce)
            elif nuova:
                campi[corrente].append(_valore(corpo, dove))
            else:
                raise StoreError(f"{dove}: riga di lista non riconosciuta ({riga!r})")
            continue
        if ":" not in riga:
            raise StoreError(f"{dove}: riga di frontmatter senza due punti ({riga!r})")
        chiave, _, resto = riga.partition(":")
        chiave, resto = chiave.strip(), resto.strip()
        if resto == "":
            campi[chiave] = []
            corrente = chiave
        elif resto == "[]":
            campi[chiave] = []
            corrente = None
        else:
            campi[chiave] = _valore(resto, dove)
            corrente = None
    return campi


# --- il corpo ---------------------------------------------------------------


def _controlla_testo(testo: str, dove: str) -> str:
    """Un testo che contiene un marcatore tornerebbe indietro spaccato in due."""
    for riga in testo.split("\n"):
        if MARCATORE.match(riga) or EXTRA.match(riga):
            raise StoreError(f"{dove}: il testo contiene una riga che è un marcatore ({riga!r})")
    return testo


def rendi_corpo(lead: str, sezioni: list) -> str:
    pezzi = [_controlla_testo((lead or "").strip(), "lead")]
    for i, sezione in enumerate(sezioni or []):
        if not isinstance(sezione, dict):
            raise StoreError(f"sezione {i}: non è un oggetto")
        ruolo = (sezione.get("role") or "").strip()
        if not ruolo:
            raise StoreError(f"sezione {i}: senza ruolo, e il ruolo è ciò che il renderer legge")
        blocco = [f"<!-- sezione: {ruolo} -->"]
        for chiave in sorted(set(sezione) - {"role", "h", "body"}):
            blocco.append(f"<!-- {chiave}: {json.dumps(sezione[chiave], ensure_ascii=False)} -->")
        titolo = (sezione.get("h") or "").strip()
        if titolo:
            if "\n" in titolo:
                raise StoreError(f"sezione {i}: il titolo va su una riga sola")
            blocco.append(f"## {titolo}")
        corpo = _controlla_testo((sezione.get("body") or "").strip(), f"sezione {i}")
        if not titolo and TITOLO.match(corpo.split("\n", 1)[0]):
            raise StoreError(
                f"sezione {i}: senza titolo, ma il corpo comincia con un H2: "
                "rileggendo il file quell'H2 diventerebbe il titolo")
        pezzi.append("\n".join(blocco) + ("\n\n" + corpo if corpo else ""))
    return "\n\n".join(p for p in pezzi if p)


def leggi_corpo(testo: str, dove: str) -> tuple[str, list]:
    lead: list[str] = []
    sezioni: list = []
    corrente: dict | None = None
    corpo: list[str] = []

    def chiudi():
        if corrente is not None:
            corrente["body"] = "\n".join(corpo).strip()
            sezioni.append(corrente)

    for riga in testo.split("\n"):
        marcatore = MARCATORE.match(riga)
        if marcatore:
            chiudi()
            corrente = {"role": marcatore.group("role"), "h": None}
            corpo = []
            continue
        if corrente is None:
            lead.append(riga)
            continue
        if not corpo:
            # La testa di una sezione: gli extra e il titolo. Si leggono solo
            # finché il corpo non è cominciato, così un commento HTML dentro il
            # testo resta testo invece di diventare un campo.
            extra = EXTRA.match(riga)
            if extra:
                corrente[extra.group("chiave")] = _valore(extra.group("valore"), dove)
                continue
            titolo = TITOLO.match(riga)
            if titolo and corrente["h"] is None:
                corrente["h"] = titolo.group("h")
                continue
            if not riga.strip():
                continue
        corpo.append(riga)
    chiudi()
    return "\n".join(lead).strip(), sezioni


def rendi(key: str, entry: dict) -> str:
    """Il file intero di un articolo, come stringa."""
    campi = {k: v for k, v in entry.items() if k not in TESTO and k != KEY_FIELD}
    campi[KEY_FIELD] = str(key)
    corpo = rendi_corpo(entry.get("lead") or "", entry.get("sections") or [])
    return f"{DELIMITER}\n{rendi_frontmatter(campi)}\n{DELIMITER}\n\n{corpo}\n"


def analizza(testo: str, dove: str) -> dict:
    """L'entry contenuta in un file, `key` compresa."""
    righe = testo.split("\n")
    if not righe or righe[0].strip() != DELIMITER:
        raise StoreError(f"{dove}: manca il frontmatter (la prima riga deve essere '{DELIMITER}')")
    try:
        fine = next(i for i in range(1, len(righe)) if righe[i].strip() == DELIMITER)
    except StopIteration:
        raise StoreError(f"{dove}: il frontmatter non è chiuso da '{DELIMITER}'") from None
    entry = leggi_frontmatter(righe[1:fine], dove)
    lead, sezioni = leggi_corpo("\n".join(righe[fine + 1:]), dove)
    entry["lead"] = lead
    entry["sections"] = sezioni
    return entry


# --- lo store ---------------------------------------------------------------


def load_all(root=None, strict=True) -> dict:
    """Tutti gli articoli, come `{chiave: voce}`.

    È esattamente il dizionario che `json.load` restituiva sul file unico, e
    lo è di proposito: ogni consumatore è passato da una riga di `json.load`
    a una chiamata qui senza toccare altro, prima quando gli articoli sono
    diventati un file ciascuno e di nuovo quando quei file sono diventati
    Markdown. `tests/unit/test_indicator_store.py` verifica che le letture
    coincidano.

    `root` accetta anche un vecchio file unico, come `read_journal` accetta un
    `.jsonl` e `load_verifications` un `.csv`. Serve alla migrazione e ai test,
    che di un catalogo intero hanno bisogno di scrivere due voci.

    `strict` decide che cosa costa un file rotto, e la risposta giusta dipende
    da chi chiede. Per il cancello, per la suite e per chi lavora sulla catena
    un file illeggibile deve fermare tutto, forte: è un difetto e va visto.
    Per l'**app** no, e la differenza è grossa. Con `strict` un solo file mal
    scritto solleva, il chiamante ripiega su un dizionario vuoto, e tutte e
    trecentottantadue le pagine perdono la prosa insieme senza che si veda un
    errore da nessuna parte. Un articolo rotto deve costare un articolo, non il
    catalogo, e a trovarlo ci pensa la suite, che gira in `strict`.
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

    Sta qui perché questo modulo possiede le chiavi e la loro codifica, ed è
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

    Il frontmatter esce con le chiavi in ordine, come faceva il dump del file
    unico: un file che cambia ordine a ogni scrittura produrrebbe diff che non
    dicono niente, ed è metà del motivo per cui questo store esiste.
    """
    path = path_for(key, root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendi(key, entry), encoding="utf-8")
    return path


def remove(key: str, root=None) -> bool:
    path = path_for(key, root=root)
    if not path.exists():
        return False
    path.unlink()
    return True


def _read_file(path: Path, key: str) -> dict:
    try:
        testo = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise StoreError(f"{path.name} non è leggibile: {type(exc).__name__}") from exc
    data = analizza(testo, path.name)
    declared = data.get(KEY_FIELD)
    if declared is not None and str(declared) != key:
        # Un file rinominato a mano, o scritto sotto il nome sbagliato. Detto
        # invece che ignorato: la voce sarebbe raggiungibile con una chiave e
        # descriverebbe un altro indicatore, che è il modo peggiore di
        # sbagliare perché la pagina si renderizza lo stesso.
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


def da_json(root=None) -> tuple[int, list[str]]:
    """Riscrive in Markdown i `.json` di una directory di articoli.

    Il travaso da JSON a Markdown, una volta sola, con la sua prova: rilegge
    ogni file appena scritto e lo confronta con la voce di partenza. Il JSON
    non si cancella e la lista dei disallineati torna al chiamante, che decide:
    un travaso che perde qualcosa deve poterlo dire prima che l'originale
    sparisca.
    """
    base = Path(root or ROOT)
    diversi = []
    scritti = 0
    for path in sorted(base.glob("*.json")):
        key = key_of(path)
        prima = json.loads(path.read_text(encoding="utf-8"))
        prima = {k: v for k, v in prima.items() if k != KEY_FIELD}
        write(key, prima, root=base)
        if read(key, root=base) != prima:
            diversi.append(key)
        scritti += 1
    return scritti, diversi


def main():
    parser = argparse.ArgumentParser(description="Lo store degli articoli, un file per indicatore.")
    parser.add_argument("--list", action="store_true", help="le chiavi presenti")
    parser.add_argument("--show", metavar="CHIAVE", help="una voce, in JSON")
    parser.add_argument("--migrate", metavar="FILE", nargs="?", const=str(LEGACY_PATH),
                        help="travasa il vecchio file unico nello store")
    parser.add_argument("--da-json", metavar="DIR", nargs="?", const=str(ROOT),
                        help="riscrive in Markdown i .json di una directory di articoli")
    args = parser.parse_args()

    if args.migrate:
        count = migrate(args.migrate)
        print(f"{count} articoli scritti in {ROOT.relative_to(PROJECT_ROOT)}/")
        return 0
    if args.da_json:
        scritti, diversi = da_json(args.da_json)
        print(f"{scritti} articoli riscritti in Markdown")
        if diversi:
            print("non tornano indietro identici: " + ", ".join(diversi), file=sys.stderr)
            return 1
        print("tutti rileggono identici alla voce di partenza")
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
        # `--list | head` chiude la pipe mentre stiamo ancora stampando. Non è
        # un errore del programma, e lasciare uscire il traceback fa sembrare
        # rotto un comando che ha funzionato.
        sys.stderr.close()
        raise SystemExit(0)
