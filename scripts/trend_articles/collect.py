"""Fase 1: che cosa si cerca e di che cosa si parla oggi in Italia.

Tre famiglie di segnali, tutte da fonti aperte e senza chiavi:

- **Google Trends, ricerche di tendenza** per l'Italia (feed RSS pubblico
  `trends.google.com/trending/rss?geo=IT`): le ricerche che stanno crescendo
  nelle ultime ore, con il traffico approssimato e le notizie collegate.
- **Google News Italia**: le notizie principali del giorno e, per ogni tema di
  `config/trend_topics.json`, la ricerca degli ultimi sette giorni.
- **Istat**: le pubblicazioni appena uscite (feed del sito). Un dato appena
  pubblicato e' un trend a se'.

Ogni segnale viene salvato com'e' arrivato, con fonte, URL e ora di
rilevazione, in `data/trend/<giorno>/signals.json`. Il file e' la prova di
perche' un pezzo e' stato scelto: si committa insieme all'articolo.

    bin/py -m scripts.trend_articles.collect --day 2026-09-23
    bin/py -m scripts.trend_articles.collect --skip-topics   # solo i feed generali
"""

from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import re
import sys
import time
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

import requests

from scripts.trend_articles import common

USER_AGENT = "Mozilla/5.0 (compatible; divarioitalia-trend/1.0; +https://divarioitalia.it)"
GT_RSS = "https://trends.google.com/trending/rss?geo=IT"
GN_TOP = "https://news.google.com/rss?hl=it&gl=IT&ceid=IT:it"
GN_SEARCH = "https://news.google.com/rss/search?q={q}&hl=it&gl=IT&ceid=IT:it"
ISTAT_FEED = "https://www.istat.it/feed/?post_type=comunicato_stampa"
NS_HT = {"ht": "https://trends.google.com/trending/rss"}


def normalize(text: str) -> str:
    """Minuscolo e senza accenti: 'Povertà' e 'poverta' devono combaciare."""
    text = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in text if not unicodedata.combining(c)).replace("’", "'")


def _download(url: str) -> bytes:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    return response.content


def _rss_date(text: str | None) -> str | None:
    if not text:
        return None
    try:
        return email.utils.parsedate_to_datetime(text).isoformat()
    except (TypeError, ValueError):
        return text


def google_trends_rss() -> list[dict]:
    root = ET.fromstring(_download(GT_RSS))
    signals = []
    for item in root.iter("item"):
        news = [
            {
                "title": n.findtext("ht:news_item_title", default="", namespaces=NS_HT),
                "url": n.findtext("ht:news_item_url", default="", namespaces=NS_HT),
                "source": n.findtext("ht:news_item_source", default="", namespaces=NS_HT),
            }
            for n in item.findall("ht:news_item", NS_HT)
        ]
        signals.append({
            "type": "google_trends_tendenza",
            "term": item.findtext("title", default=""),
            "approx_traffic": item.findtext("ht:approx_traffic", default="", namespaces=NS_HT),
            "published": _rss_date(item.findtext("pubDate")),
            "source": "Google Trends, ricerche di tendenza, Italia",
            "url": "https://trends.google.com/trending?geo=IT",
            "news": news,
        })
    return signals


def _news(url: str, kind: str, source: str, topic: str | None = None) -> list[dict]:
    root = ET.fromstring(_download(url))
    return [
        {
            "type": kind,
            "title": item.findtext("title", default=""),
            "outlet": item.findtext("source", default=""),
            "url": item.findtext("link", default=""),
            "published": _rss_date(item.findtext("pubDate")),
            "source": source,
            **({"topic": topic} if topic else {}),
        }
        for item in root.iter("item")
    ]


def google_news_top() -> list[dict]:
    return _news(GN_TOP, "google_news_principali", "Google News Italia, notizie principali")


def google_news_topic(topic: dict) -> list[dict]:
    query = f"({topic['news']}) when:7d"
    url = GN_SEARCH.format(q=urllib.parse.quote(query))
    return _news(url, "google_news_tema", f"Google News Italia, ricerca: {query}", topic["id"])


def istat_releases() -> list[dict]:
    # Il feed mescola alle pubblicazioni i bandi di gara ("CIG ..."): non sono segnali.
    return [
        s for s in _news(ISTAT_FEED, "istat_comunicato", "Istat, pubblicazioni recenti")
        if not s["title"].startswith("CIG ")
    ]


def keyword_pattern(keyword: str) -> re.Pattern:
    """Una parola intera: 'rsa' non deve accendersi dentro 'borsa' o 'corsa'.

    Un asterisco finale la rende un prefisso: 'autosufficien*' prende
    'autosufficiente' e 'autosufficienza'.
    """
    keyword = normalize(keyword)
    prefix = keyword.endswith("*")
    body = re.escape(keyword.rstrip("*"))
    return re.compile(rf"(?<![a-z0-9]){body}" + ("" if prefix else r"(?![a-z0-9])"))


def match_topics(signals: list[dict], topics: list[dict]) -> None:
    """Scrive su ogni segnale i temi le cui parole compaiono nel suo testo.

    Una ricerca per tema porta gia' il suo tema, ma si tiene solo se il titolo
    lo conferma: Google News allarga la query e restituisce anche notizie che
    con il tema non c'entrano.
    """
    patterns = {t["id"]: [keyword_pattern(k) for k in t["keywords"]] for t in topics}
    for s in signals:
        text = normalize(" ".join([
            s.get("term", ""), s.get("title", ""),
            *[n["title"] for n in s.get("news", [])],
        ]))
        s["topics"] = sorted(tid for tid, pats in patterns.items() if any(p.search(text) for p in pats))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--day", help="cartella di lavoro AAAA-MM-GG (default: oggi, ora italiana)")
    parser.add_argument("--skip-topics", action="store_true", help="salta le ricerche per tema")
    args = parser.parse_args(argv)

    now = dt.datetime.now(ZoneInfo("Europe/Rome"))
    day = args.day or now.date().isoformat()
    topics = common.read_json(common.TOPICS_CONFIG)["topics"]
    signals: list[dict] = []
    errors: list[dict] = []

    steps = [("google_trends_rss", google_trends_rss),
             ("google_news_top", google_news_top),
             ("istat_releases", istat_releases)]
    if not args.skip_topics:
        steps += [(f"google_news_topic:{t['id']}", (lambda t=t: google_news_topic(t))) for t in topics]

    for name, step in steps:
        try:
            new = step()
        except (requests.RequestException, ET.ParseError) as error:
            # Un feed giu' non ferma gli altri, ma resta scritto nel file del giorno.
            errors.append({"step": name, "error": repr(error)})
            print(f"  {name}: ERRORE {error!r}", file=sys.stderr)
        else:
            signals.extend(new)
            print(f"  {name}: {len(new)} segnali")
        time.sleep(1)

    match_topics(signals, topics)
    out = common.day_dir(day) / "signals.json"
    common.write_json(out, {"detected": now.isoformat(timespec="seconds"), "signals": signals, "errors": errors})
    print(f"{len(signals)} segnali, {len(errors)} errori -> {out.relative_to(common.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
