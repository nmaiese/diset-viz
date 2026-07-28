#!/usr/bin/env python3
"""La verifica della pubblicazione sul sito (docs/EDITORIAL_PRACTICE.md, §8).

E' il solo pezzo davvero nuovo del modello a pratica: la catena oggi sa dire
"fuso su master" ma non "la pagina pubblica serve questa versione". Trattare il
merge come pubblicazione e' un falso positivo, perche' il repository puo' essere
avanti e il sito indietro. Questa e' la transizione `fusa -> pubblicata`: prende
la pagina pubblica dell'indicatore e controlla che serva la versione attesa.

Il confronto e' una **firma di contenuto**, non l'impronta grezza `prosa` (che
nell'HTML non compare): un frammento normalizzato del `lead` committato piu'
l'anno del `vintage` citato. Se entrambi sono nella pagina, la versione online
combacia con l'articolo committato.

Regola di prudenza presa dal cancello: un controllo che non ha potuto girare
**non passa**. Se il sito e' irraggiungibile l'esito e' `irraggiungibile`
(`ok=None`), non un successo e non un fallimento. Un controllo che passa perche'
non ha potuto girare e' il difetto che il cancello di questa catena esiste per
non avere.

Il nucleo (`page_signature`, `match_signature`) e' puro e testato senza rete, il
recupero HTTP e' un urllib sottile e tollerante, con il fetcher iniettabile.
Stdlib puro come il resto.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_BASE = "https://divarioitalia.it"
# Il registro delle prove di pubblicazione: un file per record, come `verifiche/`.
# Ogni prova e' un'osservazione datata che il sito ha servito una versione, con
# l'impronta `prosa` di quella versione, cosi' scade quando il testo cambia.
PUBLICATIONS_DIR = PROJECT_ROOT / "data" / "pipeline" / "pubblicazioni"
_WS = re.compile(r"\s+")
_TAGS = re.compile(r"<[^>]+>")
_SNIPPET_WORDS = 12


def _normalize(text: str) -> str:
    return _WS.sub(" ", (text or "").strip()).lower()


def page_signature(entry: dict) -> dict:
    """La firma attesa di una pagina, dall'articolo committato.

    Un frammento del `lead` (le prime parole, normalizzate) e l'anno del
    `vintage`. Il frammento e' corto apposta: deve sopravvivere a come il
    template avvolge il testo, non deve pretendere di ritrovare l'HTML parola per
    parola.
    """
    lead = _normalize(entry.get("lead") or "")
    snippet = " ".join(lead.split()[:_SNIPPET_WORDS])
    vintage = str(entry.get("vintage") or "").strip()
    return {"snippet": snippet, "vintage": vintage}


def _visible_text(html: str) -> str:
    return _normalize(_TAGS.sub(" ", html or ""))


def match_signature(html: str, signature: dict) -> dict:
    """Confronta l'HTML servito con la firma attesa. Puro: nessuna rete.

    `snippet_ok`: il frammento del lead e' nel testo visibile della pagina.
    `vintage_ok`: l'anno citato compare nella pagina. `ok` solo se entrambi.
    """
    text = _visible_text(html)
    snippet = signature.get("snippet") or ""
    vintage = signature.get("vintage") or ""
    snippet_ok = bool(snippet) and snippet in text
    vintage_ok = bool(vintage) and re.search(rf"\b{re.escape(vintage)}\b", text) is not None
    return {
        "ok": bool(snippet_ok and vintage_ok),
        "snippet_ok": snippet_ok,
        "vintage_ok": vintage_ok,
    }


def _fetch(url: str, timeout: float = 15.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "divario-publication-check"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (fixed https base)
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def verify(url: str, entry: dict, fetcher=_fetch) -> dict:
    """Verifica che `url` serva la versione dell'articolo `entry`.

    `fetcher(url) -> html` e' iniettabile, cosi' il test non tocca la rete.
    Esiti: `ok=True` combacia, `ok=False` la pagina non porta la versione attesa,
    `ok=None` irraggiungibile (rete assente, timeout, HTTP != 200), che non e' ne'
    un successo ne' un fallimento.
    """
    signature = page_signature(entry)
    try:
        html = fetcher(url)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as exc:
        return {"ok": None, "reason": "irraggiungibile", "error": str(exc),
                "url": url, "signature": signature}
    result = match_signature(html, signature)
    result.update({"url": url, "signature": signature,
                   "reason": "combacia" if result["ok"] else "versione diversa"})
    return result


def build_url(code: str, slug: str = "", base: str = DEFAULT_BASE, level: str = "") -> str:
    """L'URL canonico di una pagina indicatore, `/indicatore/<slug>/<acr>-<id>`.

    Il segmento `<acr>-<id>` (il `code`) e' la parte stabile e la sola che
    identifica l'indicatore, lo slug e' descrittivo. Senza slug si usa la forma a
    solo code, `/indicatore/<code>`, che l'app serve apposta e **301 reindirizza**
    alla forma canonica con lo slug (vedi `sources.indicator_url`): il fetcher
    segue il redirect, quindi non serve conoscere lo slug in anticipo. Chi lo ha
    lo passa e salta il salto.

    `level` aggiunge `?livello=<level>`, il parametro con cui l'app sceglie quale
    livello territoriale rendere lato server (`app/views.py`, `request.args.get
    ("livello")`). Senza, l'app serve il livello di default (regione), quindi la
    pagina di un articolo **provinciale** non porterebbe mai il suo lead e
    resterebbe `fusa` per sempre. L'app conserva la query oltre la
    canonicalizzazione 301, quindi il parametro sopravvive al salto.
    """
    root = base.rstrip("/") + "/indicatore"
    path = f"{root}/{slug}/{code}" if slug else f"{root}/{code}"
    if level:
        path += f"?livello={level}"
    return path


# --- il registro delle prove (un file per record) ---------------------------

def proof_name(code: str, level: str, prosa: str) -> str:
    return f"{code}__{level}__{prosa}.json"


def build_proof(entry: dict, result: dict, level: str = "regione", at: str = "") -> dict:
    """Una prova di pubblicazione dalla firma attesa e dall'esito del confronto.

    Porta l'impronta `prosa` della versione verificata: e' il tripwire che fa
    scadere la prova quando il testo cambia, esattamente come le schede di
    `verifiche/`. Una pubblicazione verificata non e' verificata per sempre, e'
    verificata finche' serve quella versione.
    """
    from scripts import verification_queue
    return {
        "code": result.get("code") or "",
        "level": level,
        "at": at or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "url": result.get("url", ""),
        "ok": result.get("ok"),
        "snippet_ok": result.get("snippet_ok"),
        "vintage_ok": result.get("vintage_ok"),
        "vintage": str(entry.get("vintage") or ""),
        "prosa": verification_queue.prose_fingerprint(entry),
        "reason": result.get("reason", ""),
    }


def write_proof(proof: dict, root=None) -> Path:
    base = Path(root or PUBLICATIONS_DIR)
    base.mkdir(parents=True, exist_ok=True)
    path = base / proof_name(proof["code"], proof.get("level", "regione"), proof["prosa"])
    path.write_text(json.dumps(proof, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8")
    return path


def load_proofs(root=None) -> list:
    base = Path(root or PUBLICATIONS_DIR)
    if not base.is_dir():
        return []
    out = []
    for path in sorted(base.glob("*.json")):
        try:
            out.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return out


# --- la coda del publisher: gli indicatori fusi non ancora provati (§8) ------
#
# La transizione `fusa -> pubblicata` e' l'unico stato che la catena non sapeva
# osservare. Qui c'e' la sua coda, deterministica come le altre (si calcola dai
# file committati, non da un giudizio), il suo referto nella forma di
# `pipeline_status`, e il controllo puro che il cancello usa per imporre la
# regola di prudenza invece di ricordarla. Il perimetro dello stadio
# (`data/pipeline/pubblicazioni/`) vive in `pipeline_gate.STAGE_PATHS`.
#
# **Lo stadio e' agganciato ma spento.** Non e' in `pipeline_status.STAGE_ORDER`,
# quindi il dispatcher non lo lancia: la macchina e' pronta, l'interruttore no,
# esattamente come per la preemption per priorita'. Accenderlo (aggiungere
# `publisher` all'ordine di catena, o farne un passo del dispatcher dopo il
# deploy) e' la riga operativa del cutover, dopo il confronto delle metriche.


def publication_queue(dossier=None, today: str = "", proofs_root=None) -> list:
    """Gli indicatori in stato `fusa` che aspettano la verifica del sito.

    Uno indicatore e' `fusa` quando il suo ciclo editoriale e' completo ed e' su
    master, ma nessuna prova conferma che la pagina pubblica serva quella
    versione. Puro se `dossier` e' passato, altrimenti lo ricostruisce dai file
    reali. Ogni voce porta l'`id` d'indicatore e il `code` della sua pagina.
    """
    from scripts import practice_timeline
    if dossier is None:
        dossier = practice_timeline.load_real(today=today, proofs_root=proofs_root)
    out = [{"id": d["id"], "code": practice_timeline.code_of(d["id"])}
           for d in dossier.values() if d.get("state") == "fusa"]
    return sorted(out, key=lambda r: r["id"])


def stage_report(proofs_root=None) -> dict:
    """La coda del publisher nella forma di `pipeline_status`.

    Pronta per il giorno in cui il cutover aggiunge `publisher` all'ordine di
    catena: fino ad allora nessuno la chiama nel giro del dispatcher, che legge
    solo `STAGE_ORDER`.
    """
    queue = publication_queue(proofs_root=proofs_root)
    n = len(queue)
    return {
        "stage": "publisher",
        "waiting": n,
        "detail": {"da_verificare_sul_sito": n,
                   "indicatori": [r["id"] for r in queue][:10]},
        "next": (f"verificare sul sito {n} indicatori fusi e non ancora provati"
                 if n else "ogni indicatore fuso ha una prova di pubblicazione valida"),
        "command": ("python3 scripts/verify_publication.py --all-fusa "
                    "--base https://divarioitalia.it --write"),
    }


def publication_problems(proof: dict, valid_fingerprints: dict) -> list:
    """Cosa non va in una prova di pubblicazione. Puro, cosi' il cancello lo
    prova senza un albero git.

    `valid_fingerprints` e' `{code: set(impronte accettabili)}`, l'impronta
    `prosa` di adesso piu' quella della base. E' il gemello di
    `verification_queue.row_problems`, e serve al cancello per **imporre** invece
    di ricordare la prudenza di §8: una prova con `ok` diverso da True e' un
    controllo che non ha confermato niente, e registrarla come pubblicazione e'
    proprio il falso positivo che la Fase D esiste per non avere. Un'impronta che
    non corrisponde a nessuna versione dell'articolo e' la prova di un testo che
    non e' in pagina.
    """
    code = (proof.get("code") or "").strip()
    if not code:
        return ["una prova non ha code"]
    problems = []
    if proof.get("ok") is not True:
        problems.append(
            f"{code}: prova con ok={proof.get('ok')!r}, non si registra una "
            "pubblicazione che il controllo non ha confermato")
    if code not in valid_fingerprints:
        problems.append(f"{code}: nessun articolo per questo code")
        return problems
    prosa = (proof.get("prosa") or "").strip()
    if prosa not in valid_fingerprints[code]:
        problems.append(
            f"{code}: impronta prosa che non corrisponde a nessuna versione "
            "dell'articolo, ne' quella di adesso ne' quella della base")
    return problems


def verify_one(indicator, base=DEFAULT_BASE, slug="", level=None,
               write=False, proofs_root=None, url=None, fetcher=_fetch) -> dict | None:
    """Verifica un indicatore contro il sito e, se combacia e `write`, registra
    la prova. Ritorna il `result` (con `code`, ed eventuale `proof_path`) o None
    se l'articolo non e' nel repo.

    Il livello si ricava dall'articolo (`entry["level"]`) se non e' passato, e si
    usa **sia** nell'URL (`?livello=`) **sia** nella prova: un articolo
    provinciale va verificato contro la vista provinciale, e la sua prova va
    etichettata `provincia`, altrimenti resterebbe `fusa` per sempre o porterebbe
    un livello sbagliato.
    """
    from scripts import indicator_store, practice_timeline
    entry = indicator_store.read(indicator)
    if entry is None:
        return None
    code = practice_timeline.code_of(indicator)
    lvl = level or (entry.get("level") or "regione")
    result = verify(url or build_url(code, slug, base, level=lvl), entry, fetcher=fetcher)
    result["code"] = code
    if write and result["ok"] is True:
        result["proof_path"] = str(
            write_proof(build_proof(entry, result, level=lvl), root=proofs_root))
    return result


# --- il passo del sito, meccanico e post-deploy (era nel dispatcher) ---------
#
# La verifica `fusa -> pubblicata` non e' uno stadio con un agente: e'
# deterministica, non apre pull request e non lancia una sessione. E non puo'
# vivere nella run del produttore, che gira **prima** del deploy: il sito serve
# la versione nuova solo dopo il merge. Quindi e' un passo meccanico che il
# lanciatore fa a un tick successivo, sul sito gia' dispiegato. Scrive solo dove
# il controllo ha confermato (`ok is True`), quindi le invarianti che il cancello
# imporrebbe sono garantite per costruzione, e le prove nuove arrivano su master
# con un commit costruito sopra origin/master, spinto da qualunque branch.

def _run(argv, cwd=None, env=None):
    import subprocess
    full_env = None
    if env:
        import os
        full_env = {**os.environ, **env}
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, env=full_env)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def land_on_master(rels, message, runner=_run, cwd=None, log=print, attempts=3,
                   label="prove"):
    """Mette file nuovi su master **da qualsiasi branch**, spingendo solo quei file.

    La sessione di una Routine sta sempre su un branch `claude/*`, mai su master,
    e questi sono file nuovi per record (una prova per versione, nome che nessun
    altro sceglie), fuori da qualsiasi pull request. Si costruisce un commit
    **sopra origin/master** che contiene **solo** questi file, seminando un indice
    temporaneo da origin/master e aggiungendoci i soli percorsi da pubblicare, e
    si spinge quel commit su master. L'invariante 'non spinge altro che se stesso'
    vale per costruzione, non per guardia: HEAD e gli altri file non committati non
    entrano. Chi perde la corsa del push si ricostruisce sopra il master
    aggiornato e ritenta.
    """
    rels = sorted(set(rels))
    if not rels:
        return False

    import os
    import tempfile

    fd, index = tempfile.mkstemp(prefix="publish-index-")
    os.close(fd)
    try:
        for attempt in range(1, attempts + 1):
            code, out = runner(["git", "fetch", "origin", "master"], cwd=cwd)
            if code != 0:
                log(f"  {label}: git fetch origin master fallito ({out.strip()[:120]})")
                return False
            code, out = runner(["git", "read-tree", "origin/master"], cwd=cwd,
                               env={"GIT_INDEX_FILE": index})
            if code != 0:
                log(f"  {label}: read-tree origin/master fallito ({out.strip()[:120]})")
                return False
            code, out = runner(["git", "add", "--", *rels], cwd=cwd,
                               env={"GIT_INDEX_FILE": index})
            if code != 0:
                log(f"  {label}: git add fallito ({out.strip()[:120]})")
                return False
            code, out = runner(["git", "write-tree"], cwd=cwd,
                               env={"GIT_INDEX_FILE": index})
            tree = out.split()[0] if code == 0 and out.split() else ""
            if not tree:
                log(f"  {label}: write-tree fallito ({out.strip()[:120]})")
                return False
            code, out = runner(
                ["git", "commit-tree", tree, "-p", "origin/master", "-m", message],
                cwd=cwd)
            commit = out.split()[0] if code == 0 and out.split() else ""
            if not commit:
                log(f"  {label}: commit-tree fallito ({out.strip()[:120]})")
                return False
            code, out = runner(["git", "push", "origin", f"{commit}:master"], cwd=cwd)
            if code == 0:
                log(f"  {label}: {len(rels)} su master")
                return True
            log(f"  {label}: push perso, ritento ({attempt}/{attempts})")
        log(f"  {label.upper()} NON SU MASTER: la corsa al push non si e' chiusa in "
            f"{attempts} tentativi.")
        return False
    finally:
        try:
            os.remove(index)
        except OSError:
            pass


def commit_proofs(rels, runner=_run, cwd=None, log=print, attempts=3):
    """Porta le prove di pubblicazione nuove su master. Sono file nuovi per
    record con un nome che nessun altro sceglie, quindi il commit mirato di
    `land_on_master` e' sicuro e arriva su master anche dal branch di lavoro."""
    n = len(set(rels))
    return land_on_master(
        rels, f"Prove di pubblicazione: {n} indicatori verificati sul sito",
        runner=runner, cwd=cwd, log=log, attempts=attempts, label="prove")


def publish_step(base=DEFAULT_BASE, fetcher=None, runner=_run, cwd=None,
                 log=print, proofs_root=None, do_commit=True):
    """Il passo del sito come step meccanico del lanciatore, non come stadio.

    Per ogni indicatore in stato `fusa` prende la pagina pubblica e, se serve la
    versione committata, scrive la prova e la porta su master. Opt-in nel
    lanciatore: un sito irraggiungibile o una versione non ancora dispiegata non
    scrivono niente (ok None/False), l'indicatore resta `fusa` e si riprova al
    tick dopo, senza un falso positivo.
    """
    queue = publication_queue(proofs_root=proofs_root)
    checked, written = [], []
    for row in queue:
        try:
            kwargs = {} if fetcher is None else {"fetcher": fetcher}
            result = verify_one(
                row["id"], base=base, write=True, proofs_root=proofs_root, **kwargs)
        except Exception as exc:  # una pagina non deve fermare le altre
            log(f"  prove: {row['code']} saltato ({type(exc).__name__})")
            continue
        if result is None:
            continue
        checked.append({"code": row["code"], "ok": result.get("ok")})
        if result.get("proof_path"):
            written.append(result["proof_path"])

    summary = {"base": base, "fusa": len(queue), "verificati": len(checked),
               "prove_scritte": len(written), "checked": checked}
    if written and do_commit:
        rels = []
        for path in written:
            p = Path(path)
            rels.append(str(p.relative_to(PROJECT_ROOT)) if p.is_absolute() and
                        str(p).startswith(str(PROJECT_ROOT)) else path)
        summary["committed"] = commit_proofs(rels, runner=runner, cwd=cwd, log=log)
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--indicator", help="chiave d'articolo, es. dem:NMIGRATEIN")
    parser.add_argument("--all-fusa", action="store_true",
                        help="verifica ogni indicatore in stato 'fusa' (la coda del publisher)")
    parser.add_argument("--queue", action="store_true",
                        help="stampa la coda del publisher e basta (nessuna rete)")
    parser.add_argument("--url", help="URL completo della pagina (altrimenti si costruisce dal code)")
    parser.add_argument("--slug", default="", help="slug della pagina, se noto (altrimenti la forma a solo code, che 301 reindirizza)")
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--level", default="",
                        help="livello territoriale; vuoto = ricavato dall'articolo (regione/provincia)")
    parser.add_argument("--write", action="store_true",
                        help="se combacia, registra la prova in data/pipeline/pubblicazioni/")
    parser.add_argument("--proofs-root", default=None, help="cartella del registro prove (per i test)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.queue:
        queue = publication_queue(proofs_root=args.proofs_root)
        if args.json:
            print(json.dumps(queue, ensure_ascii=False, indent=1))
        else:
            print(f"coda publisher: {len(queue)} indicatori fusi da verificare sul sito")
            for row in queue:
                print(f"  {row['id']:32.32} {row['code']}")
        return 0

    if args.all_fusa:
        queue = publication_queue(proofs_root=args.proofs_root)
        results = []
        for row in queue:
            result = verify_one(row["id"], base=args.base, level=args.level,
                                write=args.write, proofs_root=args.proofs_root)
            if result is not None:
                results.append(result)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=1))
        else:
            for result in results:
                state = {True: "pubblicata", False: "NON combacia",
                         None: "irraggiungibile"}[result["ok"]]
                print(f"  {result['code']:24.24} {state}")
                if result.get("proof_path"):
                    print(f"    prova: {result['proof_path']}")
            proved = sum(1 for r in results if r.get("proof_path"))
            print(f"{len(results)} verificati, {proved} prove registrate.")
        # Un mancato combaciamento (False) e' un fallimento; irraggiungibile
        # (None) no, per la stessa prudenza del caso singolo.
        return 1 if any(r["ok"] is False for r in results) else 0

    if not args.indicator:
        parser.error("serve --indicator, --all-fusa o --queue")

    result = verify_one(args.indicator, base=args.base, slug=args.slug,
                        level=args.level, write=args.write,
                        proofs_root=args.proofs_root, url=args.url)
    if result is None:
        print(f"nessun articolo per {args.indicator}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        state = {True: "pubblicata", False: "NON combacia", None: "irraggiungibile"}[result["ok"]]
        print(f"{args.indicator}  {state}  <{result.get('url', '')}>")
        if result.get("signature"):
            print(f"  atteso: lead '{result['signature']['snippet']}...' + anno {result['signature']['vintage']}")
        if result.get("proof_path"):
            print(f"  prova registrata: {result['proof_path']}")
    # irraggiungibile (None) non e' un fallimento del comando: esce 0. Solo un
    # mancato combaciamento (False) esce !=0.
    return 1 if result["ok"] is False else 0


if __name__ == "__main__":
    raise SystemExit(main())
