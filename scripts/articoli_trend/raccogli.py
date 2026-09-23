"""Fase 1: che cosa si cerca e di che cosa si parla oggi in Italia.

Tre famiglie di segnali, tutte da fonti aperte e senza chiavi:

- **Google Trends, ricerche di tendenza** per l'Italia (feed RSS pubblico
  `trends.google.com/trending/rss?geo=IT`): le ricerche che stanno crescendo
  nelle ultime ore, con il traffico approssimato e le notizie collegate.
- **Google News Italia**: le notizie principali del giorno e, per ogni tema di
  `config/trend_temi.json`, la ricerca degli ultimi sette giorni.
- **Istat**: i comunicati stampa appena usciti (feed del sito). Un dato
  appena pubblicato e' un trend a se': chi cerca "occupati Istat" oggi trova
  chi ne ha scritto oggi.

Ogni segnale viene salvato com'e' arrivato, con fonte, URL e ora di
rilevazione, in `data/trend/<giorno>/segnali.json`. Il file e' la prova di
perche' un pezzo e' stato scelto: si committa insieme all'articolo.

    bin/py -m scripts.articoli_trend.raccogli
    bin/py -m scripts.articoli_trend.raccogli --senza-temi   # solo i feed generali
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

import requests

from scripts.articoli_trend import comuni

AGENTE = "Mozilla/5.0 (compatible; divarioitalia-trend/1.0; +https://divarioitalia.it)"
GT_RSS = "https://trends.google.com/trending/rss?geo=IT"
GN_TOP = "https://news.google.com/rss?hl=it&gl=IT&ceid=IT:it"
GN_CERCA = "https://news.google.com/rss/search?q={q}&hl=it&gl=IT&ceid=IT:it"
ISTAT_FEED = "https://www.istat.it/feed/?post_type=comunicato_stampa"
NS_HT = {"ht": "https://trends.google.com/trending/rss"}


def normalizza(testo: str) -> str:
    """Minuscolo e senza accenti: 'Povertà' e 'poverta' devono combaciare."""
    testo = unicodedata.normalize("NFKD", (testo or "").lower())
    return "".join(c for c in testo if not unicodedata.combining(c)).replace("’", "'")


def _scarica(url: str) -> bytes:
    risposta = requests.get(url, headers={"User-Agent": AGENTE}, timeout=30)
    risposta.raise_for_status()
    return risposta.content


def _data_rss(testo: str | None) -> str | None:
    if not testo:
        return None
    try:
        return email.utils.parsedate_to_datetime(testo).isoformat()
    except (TypeError, ValueError):
        return testo


def google_trends_rss() -> list[dict]:
    radice = ET.fromstring(_scarica(GT_RSS))
    segnali = []
    for item in radice.iter("item"):
        notizie = [
            {
                "titolo": n.findtext("ht:news_item_title", default="", namespaces=NS_HT),
                "url": n.findtext("ht:news_item_url", default="", namespaces=NS_HT),
                "fonte": n.findtext("ht:news_item_source", default="", namespaces=NS_HT),
            }
            for n in item.findall("ht:news_item", NS_HT)
        ]
        segnali.append({
            "tipo": "google_trends_tendenza",
            "termine": item.findtext("title", default=""),
            "traffico_approssimato": item.findtext("ht:approx_traffic", default="", namespaces=NS_HT),
            "pubblicato": _data_rss(item.findtext("pubDate")),
            "fonte": "Google Trends, ricerche di tendenza, Italia",
            "url": "https://trends.google.com/trending?geo=IT",
            "notizie": notizie,
        })
    return segnali


def _notizie(url: str, tipo: str, fonte: str, tema: str | None = None) -> list[dict]:
    radice = ET.fromstring(_scarica(url))
    segnali = []
    for item in radice.iter("item"):
        titolo = item.findtext("title", default="")
        testata = item.findtext("source", default="")
        segnali.append({
            "tipo": tipo,
            "titolo": titolo,
            "testata": testata,
            "url": item.findtext("link", default=""),
            "pubblicato": _data_rss(item.findtext("pubDate")),
            "fonte": fonte,
            **({"tema": tema} if tema else {}),
        })
    return segnali


def google_news_principali() -> list[dict]:
    return _notizie(GN_TOP, "google_news_principali", "Google News Italia, notizie principali")


def google_news_tema(tema: dict) -> list[dict]:
    query = f"({tema['news']}) when:7d"
    url = GN_CERCA.format(q=urllib.parse.quote(query))
    return _notizie(url, "google_news_tema", f"Google News Italia, ricerca: {query}", tema["id"])


def istat_comunicati() -> list[dict]:
    # Il feed mescola ai comunicati i bandi di gara ("CIG ..."): non sono segnali.
    return [
        s for s in _notizie(ISTAT_FEED, "istat_comunicato", "Istat, pubblicazioni recenti")
        if not s["titolo"].startswith("CIG ")
    ]


def modello(parola: str) -> re.Pattern:
    """Una parola intera: 'rsa' non deve accendersi dentro 'borsa' o 'corsa'.

    Un asterisco finale la rende un prefisso: 'autosufficien*' prende
    'autosufficiente' e 'autosufficienza'.
    """
    parola = normalizza(parola)
    prefisso = parola.endswith("*")
    corpo = re.escape(parola.rstrip("*"))
    return re.compile(rf"(?<![a-z0-9]){corpo}" + ("" if prefisso else r"(?![a-z0-9])"))


def abbina(segnali: list[dict], temi: list[dict]) -> None:
    """Scrive su ogni segnale i temi le cui parole compaiono nel suo testo.

    Una ricerca per tema porta gia' il suo tema, ma si tiene solo se il titolo
    lo conferma: Google News allarga la query e restituisce anche notizie che
    con il tema non c'entrano.
    """
    modelli = {t["id"]: [modello(p) for p in t["parole"]] for t in temi}
    for s in segnali:
        testo = normalizza(" ".join([
            s.get("termine", ""), s.get("titolo", ""),
            *[n["titolo"] for n in s.get("notizie", [])],
        ]))
        s["temi"] = sorted(
            tid for tid, lista in modelli.items() if any(m.search(testo) for m in lista)
        )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--giorno", help="cartella di lavoro (default: oggi)")
    parser.add_argument("--senza-temi", action="store_true", help="salta le ricerche per tema")
    args = parser.parse_args(argv)

    temi = comuni.leggi_json(comuni.CONFIG_TEMI)["temi"]
    rilevato = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
    segnali: list[dict] = []
    errori: list[dict] = []

    passi = [("google_trends_rss", google_trends_rss),
             ("google_news_principali", google_news_principali),
             ("istat_comunicati", istat_comunicati)]
    if not args.senza_temi:
        passi += [(f"google_news_tema:{t['id']}", (lambda t=t: google_news_tema(t))) for t in temi]

    for nome, passo in passi:
        try:
            nuovi = passo()
            segnali.extend(nuovi)
            print(f"  {nome}: {len(nuovi)} segnali")
        except Exception as errore:  # un feed giu' non ferma gli altri
            errori.append({"passo": nome, "errore": repr(errore)})
            print(f"  {nome}: ERRORE {errore!r}", file=sys.stderr)
        time.sleep(1)

    abbina(segnali, temi)
    uscita = comuni.cartella_giorno(args.giorno) / "segnali.json"
    comuni.scrivi_json(uscita, {"rilevato": rilevato, "segnali": segnali, "errori": errori})
    print(f"{len(segnali)} segnali, {len(errori)} errori -> {uscita.relative_to(comuni.RADICE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
