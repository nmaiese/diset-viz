"""Misura mensile: quante pagine del sito Google ha indicizzato davvero.

Legge la sitemap di produzione, estrae un campione di URL per tipo e chiede a
Search Console (API URL Inspection) lo stato di indicizzazione di ognuno.

    uv run --with google-auth --with requests python scripts/misure/url_inspection.py --prova
    uv run --with google-auth --with requests python scripts/misure/url_inspection.py \\
        --per-tipo 20 --md reports/url_inspection.md

Le credenziali sono un account di servizio: percorso da `--credenziali`, poi
`GSC_SA_JSON`, poi `~/.config/gcloud/ga4-mcp-sa.json`. Il file si apre solo
per costruire le credenziali, mai per stamparlo.

Le funzioni pure (tipo, campione, aggregazione) non fanno rete. L'I/O sta in
`fetch_sitemap` e `inspect_url`.
"""
import argparse
import json
import os
import random
import re
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

SITEMAP_URL = "https://divarioitalia.it/sitemap.xml"
SITE_PROPERTY = "sc-domain:divarioitalia.it"
ENDPOINT = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
DEFAULT_CREDENTIALS = "~/.config/gcloud/ga4-mcp-sa.json"
# User agent dichiarato per i controlli del sito pubblico.
HEADERS = {"User-Agent": "DivarioCheck/1.0"}
DAILY_QUOTA = 2000
PAUSE_SECONDS = 1.0
MAX_ATTEMPTS = 3
TIMEOUT = 60

TYPES = ("home", "indicatore", "indicatore_province", "regione",
         "provincia", "tema", "blog", "altro")
INSPECTION_FIELDS = ("verdict", "coverageState", "robotsTxtState", "indexingState",
                     "lastCrawlTime", "googleCanonical", "userCanonical")


def classify(url):
    """Tipo di pagina dal percorso dell'URL."""
    path = re.sub(r"^https?://[^/]+", "", url).split("?", 1)[0].split("#", 1)[0]
    path = path.rstrip("/") or "/"
    if path == "/":
        return "home"
    if path.startswith("/indicatore/"):
        return "indicatore_province" if path.endswith("/province") else "indicatore"
    if path.startswith("/regione/"):
        return "regione"
    if path.startswith("/provincia/"):
        return "provincia"
    if path.startswith("/tema/"):
        return "tema"
    if path == "/blog" or path.startswith("/blog/"):
        return "blog"
    return "altro"


def sample_urls(urls, per_type, seed, max_total):
    """Campione deterministico: `per_type` URL per tipo, al massimo `max_total` in tutto.

    Con lo stesso seme e la stessa sitemap due lanci danno lo stesso campione.
    Se il tetto taglia, i tipi cedono a turno un URL ciascuno, cosi nessuno sparisce.
    """
    by_type = {t: [] for t in TYPES}
    for url in sorted(set(urls)):
        by_type[classify(url)].append(url)
    picked = {}
    for t in TYPES:
        pool = by_type[t]
        # un generatore per tipo: l'ordine non dipende dagli altri tipi
        rng = random.Random(f"{seed}:{t}")
        picked[t] = rng.sample(pool, min(per_type, len(pool)))
    cap = max(0, min(max_total, DAILY_QUOTA))
    result, rank = [], 0
    while len(result) < cap and any(len(v) > rank for v in picked.values()):
        for t in TYPES:
            if len(picked[t]) > rank and len(result) < cap:
                result.append((t, picked[t][rank]))
        rank += 1
    return result


def row_from_response(url, kind, response):
    """Riga di report da una risposta dell'API (o da un'eccezione già in `error`)."""
    result = (response.get("inspectionResult") or {}).get("indexStatusResult") or {}
    row = {"url": url, "tipo": kind}
    row.update({f: result.get(f) for f in INSPECTION_FIELDS})
    return row


def error_row(url, kind, message):
    return {"url": url, "tipo": kind, "errore": message}


def summarize(rows):
    """Riepilogo per tipo: ispezionate, indicizzate, non indicizzate, canonical diverso."""
    summary = {}
    for t in TYPES:
        mine = [r for r in rows if r["tipo"] == t]
        if not mine:
            continue
        ok = [r for r in mine if "errore" not in r]
        indexed = [r for r in ok if r.get("verdict") == "PASS"]
        not_indexed = [r for r in ok if r.get("verdict") != "PASS"]
        states = Counter(r.get("coverageState") or "sconosciuto" for r in not_indexed)
        diverse = [r for r in ok if r.get("googleCanonical") and r.get("userCanonical")
                   and r["googleCanonical"] != r["userCanonical"]]
        summary[t] = {
            "ispezionate": len(ok),
            "errori": len(mine) - len(ok),
            "indicizzate": len(indexed),
            "non_indicizzate": len(not_indexed),
            "stati_non_indicizzate": states.most_common(3),
            "canonical_diverso": len(diverse),
        }
    return summary


def to_markdown(summary, day):
    lines = [f"# URL Inspection del {day}", "",
             "| tipo | ispezionate | indicizzate | non indicizzate | stati più frequenti | canonical diverso | errori |",
             "| --- | ---: | ---: | ---: | --- | ---: | ---: |"]
    for t, s in summary.items():
        states = ", ".join(f"{c} ({n})" for c, n in s["stati_non_indicizzate"]) or "-"
        lines.append(f"| {t} | {s['ispezionate']} | {s['indicizzate']} | {s['non_indicizzate']} "
                     f"| {states} | {s['canonical_diverso']} | {s['errori']} |")
    return "\n".join(lines) + "\n"


def fetch_sitemap(requests):
    r = requests.get(SITEMAP_URL, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return re.findall(r"<loc>([^<]+)</loc>", r.text)


def inspect_url(session, url, sleep=time.sleep):
    """Chiama l'API per un URL, con backoff su 429 e 5xx. Solleva se esaurisce i tentativi."""
    body = {"inspectionUrl": url, "siteUrl": SITE_PROPERTY, "languageCode": "it"}
    for attempt in range(1, MAX_ATTEMPTS + 1):
        resp = session.post(ENDPOINT, json=body, timeout=TIMEOUT)
        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt < MAX_ATTEMPTS:
                sleep(2 ** attempt)
                continue
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code} su {url}: {resp.text[:200]}")
        return resp.json()


def make_session(credentials_path):
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    creds = service_account.Credentials.from_service_account_file(
        os.path.expanduser(credentials_path), scopes=[SCOPE])
    return AuthorizedSession(creds)


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--per-tipo", type=int, default=20)
    p.add_argument("--max", type=int, default=100, dest="max_total")
    p.add_argument("--seme", type=int, default=1)
    p.add_argument("--credenziali", default=os.environ.get("GSC_SA_JSON", DEFAULT_CREDENTIALS))
    p.add_argument("--data", default=date.today().isoformat(), help="data nel nome del report")
    p.add_argument("--out")
    p.add_argument("--md")
    p.add_argument("--prova", action="store_true", help="non chiama l'API")
    return p.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    import requests
    sample = sample_urls(fetch_sitemap(requests), args.per_tipo, args.seme, args.max_total)
    if args.prova:
        for t in TYPES:
            urls = [u for k, u in sample if k == t]
            print(f"{t}: {len(urls)}")
            for u in urls:
                print(f"  {u}")
        print(f"Chiamate previste: {len(sample)} (quota giornaliera {DAILY_QUOTA})")
        return 0
    session = make_session(args.credenziali)
    rows = []
    for i, (kind, url) in enumerate(sample):
        if i:
            time.sleep(PAUSE_SECONDS)
        try:
            rows.append(row_from_response(url, kind, inspect_url(session, url)))
        except Exception as exc:  # un URL in errore non ferma gli altri
            rows.append(error_row(url, kind, str(exc)))
    out = Path(args.out or f"reports/url_inspection_{args.data}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md = to_markdown(summarize(rows), args.data)
    print(md)
    if args.md:
        Path(args.md).write_text(md, encoding="utf-8")
    print(f"Righe per URL in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
