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


def build_url(code: str, slug: str = "", base: str = DEFAULT_BASE) -> str:
    """L'URL canonico di una pagina indicatore, `/indicatore/<slug>/<acr>-<id>`.

    Il segmento `<acr>-<id>` (il `code`) e' la parte stabile e la sola che
    identifica l'indicatore, lo slug e' descrittivo. Senza slug si usa la forma a
    solo code, `/indicatore/<code>`, che l'app serve apposta e **301 reindirizza**
    alla forma canonica con lo slug (vedi `sources.indicator_url`): il fetcher
    segue il redirect, quindi non serve conoscere lo slug in anticipo. Chi lo ha
    lo passa e salta il salto.
    """
    root = base.rstrip("/") + "/indicatore"
    return f"{root}/{slug}/{code}" if slug else f"{root}/{code}"


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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--indicator", help="chiave d'articolo, es. dem:NMIGRATEIN")
    parser.add_argument("--url", help="URL completo della pagina (altrimenti si costruisce dal code)")
    parser.add_argument("--slug", default="", help="slug della pagina, se noto (altrimenti la forma a solo code, che 301 reindirizza)")
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--level", default="regione")
    parser.add_argument("--write", action="store_true",
                        help="se combacia, registra la prova in data/pipeline/pubblicazioni/")
    parser.add_argument("--proofs-root", default=None, help="cartella del registro prove (per i test)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not args.indicator:
        parser.error("serve --indicator")

    from scripts import indicator_store, practice_timeline
    entry = indicator_store.read(args.indicator)
    if entry is None:
        print(f"nessun articolo per {args.indicator}", file=sys.stderr)
        return 2

    code = practice_timeline.code_of(args.indicator)
    url = args.url or build_url(code, args.slug, args.base)
    result = verify(url, entry)
    result["code"] = code

    proof_path = None
    if args.write and result["ok"] is True:
        proof_path = write_proof(build_proof(entry, result, level=args.level), root=args.proofs_root)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        state = {True: "pubblicata", False: "NON combacia", None: "irraggiungibile"}[result["ok"]]
        print(f"{args.indicator}  {state}  <{url}>")
        if result.get("signature"):
            print(f"  atteso: lead '{result['signature']['snippet']}...' + anno {result['signature']['vintage']}")
        if proof_path:
            print(f"  prova registrata: {proof_path}")
    # irraggiungibile (None) non e' un fallimento del comando: esce 0. Solo un
    # mancato combaciamento (False) esce !=0.
    return 1 if result["ok"] is False else 0


if __name__ == "__main__":
    raise SystemExit(main())
