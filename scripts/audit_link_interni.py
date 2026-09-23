#!/usr/bin/env python3
"""I link interni rispondono, e le province sono raggiungibili.

Le 103 pagine provincia sono uscite con 513 link in 404 e 929 in 301, e nessuna
prova se ne e' accorta: quella che doveva farlo cercava i link con una regex che
non vedeva i due punti di `ter-bes:<id>`, e accettava i 301. Da qui due regole,
che valgono per ogni pagina e per ognuna delle sue forme (HTML, Markdown,
JSON-LD, JSON):

- un link interno risponde **200 senza redirect**: un 301 interno e' un link
  scritto male, anche quando alla fine si arriva;
- un link con un'ancora trova l'`id` nella pagina di arrivo.

Il modulo serve due usi con le stesse funzioni. Il test
`tests/integration/test_link_interni.py` le fa girare su un campione, una
pagina per tipo piu' tutte le province. Questo script le fa girare su tutta la
sitemap e aggiunge la misura che il lavoro sulle province deve spostare: per
ogni provincia, quante pagine la linkano, contando tutte e solo quelle
indicizzabili (le URL della sitemap).

    PYTHONPATH=. bin/py scripts/audit_link_interni.py          # riassunto
    PYTHONPATH=. bin/py scripts/audit_link_interni.py --json   # tutto
"""
from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from urllib.parse import urlsplit

SITE_URL = "https://divarioitalia.it"
MARKDOWN = {"Accept": "text/markdown"}

_HREF = re.compile(r'\bhref="([^"]*)"')
_MARKDOWN_LINK = re.compile(r"\]\(([^)\s]+)\)")
_BARE_URL = re.compile(re.escape(SITE_URL) + r"(/[^\s)<>\"'`]*)")
_JSON_LD = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL)
# I campi che in un JSON-LD o in un payload JSON sono un indirizzo del sito.
_URL_KEYS = {"item", "url", "@id", "path", "href", "loc"}


def _internal_path(value):
    """Il path interno di un link, o None se il link porta fuori dal sito."""
    value = html_lib.unescape(value.strip())
    if value.startswith(SITE_URL):
        value = value[len(SITE_URL):] or "/"
    if not value.startswith("/") or value.startswith("//"):
        return None
    return value


def _collect_from_json(node, out):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in _URL_KEYS and isinstance(value, str):
                # Un `@id` e' il nome di un nodo (`/chi-siamo#organizzazione`),
                # non un'ancora da trovare in pagina: si controlla solo che il
                # documento risponda.
                out.append(value.split("#")[0] if key == "@id" else value)
            else:
                _collect_from_json(value, out)
    elif isinstance(node, list):
        for value in node:
            _collect_from_json(value, out)


def extract_links(body, content_type):
    """Tutti i link interni di un documento, nella forma in cui sono scritti.

    HTML: gli `href` (con query, maiuscole e due punti, che erano proprio cio'
    che la prova vecchia non vedeva) e gli indirizzi dei JSON-LD. Markdown e
    testo: i link `[..](..)` e gli URL assoluti nudi, come "URL canonica:".
    JSON: i campi che portano un indirizzo.

    Un JSON-LD o un JSON che non si legge e' un `ValueError`, non un blocco
    saltato: saltarlo voleva dire non controllare i suoi link e dare verde, la
    stessa cecita' da cui questa prova e' nata. E un JSON-LD rotto e' gia' un
    difetto della pagina.
    """
    raw = []
    if "html" in content_type:
        raw += _HREF.findall(body)
        for block in _JSON_LD.findall(body):
            try:
                _collect_from_json(json.loads(block), raw)
            except json.JSONDecodeError as error:
                raise ValueError(f"JSON-LD non valido: {error}") from error
    elif "json" in content_type:
        try:
            _collect_from_json(json.loads(body), raw)
        except json.JSONDecodeError as error:
            raise ValueError(f"JSON non valido: {error}") from error
    else:
        raw += _MARKDOWN_LINK.findall(body)
        raw += _BARE_URL.findall(body)
    links = set()
    for value in raw:
        path = _internal_path(value)
        if path:
            links.add(path.rstrip(".,;:"))
    return links


class LinkChecker:
    """Apre le pagine con il client di prova e ricorda le risposte.

    Una destinazione si apre una volta sola anche se cento pagine la linkano:
    e' cio' che rende possibile controllare tutta la sitemap in un test.
    """

    def __init__(self, client):
        self.client = client
        self._responses = {}

    def response(self, path, markdown=False):
        key = (path, markdown)
        if key not in self._responses:
            r = self.client.get(path, headers=MARKDOWN if markdown else None,
                                follow_redirects=False)
            content_type = r.headers.get("Content-Type", "")
            # Immagini, font e PDF rispondono, ma non hanno link da leggere.
            is_text = any(t in content_type for t in ("text/", "json", "xml", "javascript"))
            body = r.get_data(as_text=True) if is_text else ""
            r.close()
            self._responses[key] = (r.status_code, content_type, r.headers.get("Location", ""), body)
        return self._responses[key]

    def broken(self, path, markdown=False):
        """I link di una pagina che non rispondono 200 o non trovano l'ancora.

        Ogni guasto e' (link, motivo). La pagina stessa deve rispondere 200:
        se non lo fa, il guasto e' lei.
        """
        status, content_type, location, body = self.response(path, markdown)
        if status != 200:
            return [(path, f"la pagina risponde {status} {location}".strip())]
        try:
            page_links = extract_links(body, content_type)
        except ValueError as error:
            return [(path, str(error))]
        out = []
        for link in sorted(page_links):
            target, _, anchor = link.partition("#")
            if not target:
                continue
            target_status, target_type, target_location, target_body = self.response(target)
            if target_status != 200:
                out.append((link, f"{target_status} {target_location}".strip()))
            elif anchor and "html" in target_type and not re.search(
                    rf'\b(?:id|name)="{re.escape(anchor)}"', target_body):
                out.append((link, f"ancora #{anchor} assente"))
        return out

    def links(self, path, markdown=False):
        status, content_type, _, body = self.response(path, markdown)
        return extract_links(body, content_type) if status == 200 else set()


def sitemap_pages(client):
    body = client.get("/sitemap.xml").get_data(as_text=True)
    return [_internal_path(loc) for loc in re.findall(r"<loc>([^<]+)</loc>", body)]


def audit(client, pages, has_markdown):
    """Guasti e link entranti delle province su un elenco di pagine.

    `has_markdown(path)` dice se quella pagina ha anche la forma Markdown.
    """
    checker = LinkChecker(client)
    broken, inbound = {}, defaultdict(set)
    for path in pages:
        for md in (False, True) if has_markdown(path) else (False,):
            found = checker.broken(path, markdown=md)
            if found:
                broken[f"{path}{' [md]' if md else ''}"] = found
        try:
            page_links = checker.links(path)
        except ValueError:
            # Il JSON-LD illeggibile e' gia' fra i guasti di questa pagina,
            # riportato da `broken()` qui sopra.
            continue
        for link in page_links:
            target = urlsplit(link).path
            if target.startswith("/provincia/") and target != path:
                inbound[target.split("/")[2]].add(path)
    return broken, inbound


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--json", action="store_true", help="stampa tutto il risultato in JSON")
    args = parser.parse_args(argv)

    from app import app, province_profile
    from app.agent_discovery import markdown_available

    start = time.monotonic()
    client = app.test_client()
    pages = sitemap_pages(client)
    broken, inbound = audit(client, pages, markdown_available)
    with app.app_context():
        keys = province_profile.chiavi()
    counts = {key: len(inbound.get(key, ())) for key in keys}
    reasons = Counter(reason.split(" ")[0] for entries in broken.values() for _, reason in entries)
    result = {
        "pagine": len(pages),
        "secondi": round(time.monotonic() - start, 1),
        "link_guasti": sum(len(v) for v in broken.values()),
        "per_motivo": dict(reasons),
        "pagine_con_guasti": len(broken),
        "province": len(keys),
        "province_mai_linkate": sorted(k for k, n in counts.items() if n == 0),
        "mediana_pagine_indicizzabili_per_provincia": statistics.median(counts.values()) if counts else 0,
        "pagine_indicizzabili_per_provincia": counts,
        "guasti": broken,
    }
    if args.json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=1)
        print()
    else:
        for key in ("pagine", "secondi", "link_guasti", "per_motivo", "pagine_con_guasti",
                    "province", "mediana_pagine_indicizzabili_per_provincia"):
            print(f"{key}: {result[key]}")
        print(f"province mai linkate da una pagina indicizzabile: {len(result['province_mai_linkate'])}")
        for page, entries in list(broken.items())[:15]:
            print(f"  {page}: {entries[:3]}{' ...' if len(entries) > 3 else ''}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
