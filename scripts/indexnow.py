"""Manda a IndexNow (Bing, Yandex, Seznam) gli URL della sitemap pubblicata.

Da lanciare dopo un deploy che cambia pagine indicizzabili:

    bin/py -m scripts.indexnow                 # tutta la sitemap
    bin/py -m scripts.indexnow /regione/lazio  # solo questi percorsi

Legge la sitemap dal sito vero, non dal codice locale: notifica cio' che e'
online, non cio' che lo sara'.
"""
import json
import re
import sys
import urllib.request

from app.config import SITE_URL
from app.views import INDEXNOW_KEY

ENDPOINT = "https://api.indexnow.org/indexnow"
# Cloudflare davanti al sito, e l'API, rispondono 403 allo user-agent di urllib.
HEADERS = {"User-Agent": "divarioitalia-indexnow/1.0 (+https://divarioitalia.it/contatti)"}
LOTTO = 10000


def _sitemap():
    req = urllib.request.Request(f"{SITE_URL}/sitemap.xml", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r:
        return re.findall(r"<loc>([^<]+)</loc>", r.read().decode("utf-8"))


def main(argv):
    urls = [SITE_URL + p if p.startswith("/") else p for p in argv] or _sitemap()
    host = SITE_URL.split("://", 1)[1].rstrip("/")
    for i in range(0, len(urls), LOTTO):
        corpo = {"host": host, "key": INDEXNOW_KEY,
                 "keyLocation": f"{SITE_URL}/{INDEXNOW_KEY}.txt",
                 "urlList": urls[i:i + LOTTO]}
        req = urllib.request.Request(ENDPOINT, json.dumps(corpo).encode(),
                                     {**HEADERS, "Content-Type": "application/json; charset=utf-8"})
        with urllib.request.urlopen(req, timeout=60) as r:
            print(f"{len(corpo['urlList'])} URL, HTTP {r.status}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
