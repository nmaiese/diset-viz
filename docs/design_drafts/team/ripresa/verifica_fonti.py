"""Verifica le righe di una tabella fonti.md: apre ogni URL e cerca la citazione letterale.

Uso: uv run --with pypdf --with requests python verifica_fonti.py fonti.md
"""
import html
import io
import re
import sys
import unicodedata

import logging
import os

import requests
from pypdf import PdfReader

logging.getLogger("pypdf").setLevel(logging.ERROR)
DUMP = os.environ.get("DUMP")

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}


def norm(s):
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("­", "").replace("-\n", "")
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def testo(url):
    r = requests.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    if url.lower().endswith(".pdf") or r.headers.get("content-type", "").startswith("application/pdf"):
        pdf = PdfReader(io.BytesIO(r.content))
        return " ".join((p.extract_text() or "") for p in pdf.pages), f"pdf {len(pdf.pages)} pagine"
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", r.text)
    t = re.sub(r"<[^>]+>", " ", t)
    return html.unescape(t), f"html {r.status_code}"


def main(path):
    righe = [l for l in open(path, encoding="utf-8") if l.startswith("|") and "http" in l]
    cache = {}
    for l in righe:
        celle = [c.strip() for c in l.strip().strip("|").split("|")]
        url = next((c for c in celle if c.startswith("http")), None)
        i_url = celle.index(url)
        cit = celle[i_url + 1] if len(celle) > i_url + 1 else ""
        cit = cit.strip().strip('"“”')
        if url not in cache:
            try:
                cache[url] = testo(url)
            except Exception as e:  # noqa: BLE001
                cache[url] = (None, f"errore: {e}"[:120])
        t, info = cache[url]
        if DUMP and t:
            nome = re.sub(r"[^A-Za-z0-9]+", "_", url)[-60:] + ".txt"
            open(os.path.join(DUMP, nome), "w").write(t)
        if t is None:
            print(f"NON APERTO  {url}  {info}")
            continue
        nt, nc = norm(t), norm(cit)
        if nc in nt:
            esito = "TROVATA"
        else:
            # la citazione a pezzi: quanti frammenti di 6 parole si trovano
            parole = nc.split()
            pezzi = [" ".join(parole[i:i + 6]) for i in range(0, max(1, len(parole) - 5), 3)]
            ok = sum(1 for p in pezzi if p in nt)
            esito = f"NON TROVATA ({ok}/{len(pezzi)} frammenti)"
        print(f"{esito:28} {info:16} {url}\n    {cit[:110]}")


if __name__ == "__main__":
    main(sys.argv[1])
