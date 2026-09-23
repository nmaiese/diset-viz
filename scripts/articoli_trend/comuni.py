"""Percorsi, lettura dei dataset del sito e formattazione dei numeri in italiano.

I dataset sono quelli che il sito serve (`app/static/data/Assoluti_*.csv`), con
lo stesso contratto a dodici colonne: ogni riga porta gia' fonte e archivio di
provenienza. Il workflow non scarica una seconda copia dei dati per scriverci
sopra un articolo: un numero nel pezzo deve essere lo stesso numero che il
lettore trova nella scheda dell'indicatore.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
from functools import cache, lru_cache
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
DATI_SITO = RADICE / "app" / "static" / "data"
LAVORO = RADICE / "data" / "trend"
ARTICOLI = RADICE / "data" / "articoli"
CONFIG_TEMI = RADICE / "config" / "trend_temi.json"
POSTS = RADICE / "content" / "posts"
FIGURE = RADICE / "content" / "figure"
IMG_BLOG = RADICE / "app" / "static" / "img" / "blog"
DOWNLOAD = RADICE / "app" / "static" / "data" / "articoli"

# Famiglia -> file del sito e livello territoriale. La chiave e' quella che
# `config/trend_temi.json` usa per nominare un indicatore: `bes:03LAV007`.
DATASET = {
    "ter": ("Assoluti_Regione.csv", "regione"),
    "bes": ("Assoluti_BES_Regione.csv", "regione"),
    "ims": ("Assoluti_Multiscopo_Regione.csv", "regione"),
    "prov": ("Assoluti_Provincia.csv", "provincia"),
}

MEZZOGIORNO = {
    "Abruzzo", "Molise", "Campania", "Puglia", "Basilicata", "Calabria",
    "Sicilia", "Sardegna",
}


@lru_cache(maxsize=1)
def regione_di_provincia() -> dict[str, str]:
    with (DATI_SITO / "province_codes.csv").open(encoding="utf-8") as file:
        return {r["name"]: r["region"] for r in csv.DictReader(file, delimiter=";")}


def ripartizione(territorio: str, livello: str) -> str:
    regione = regione_di_provincia().get(territorio, territorio) if livello == "provincia" else territorio
    return "Mezzogiorno" if regione in MEZZOGIORNO else "Centro-Nord"


@lru_cache(maxsize=1)
def _definizioni() -> dict[str, dict]:
    percorso = RADICE / "data" / "definitions" / "federated.csv"
    with percorso.open(encoding="utf-8") as file:
        return {r["id"]: r for r in csv.DictReader(file, delimiter=";")}


def definizione(chiave: str) -> dict:
    """La definizione della fonte e l'URL del file da cui viene il dato.

    `data/definitions/federated.csv` e' lo stesso registro che usa
    `scripts/definition_check.py`: la definizione nel pezzo va confrontata
    con questa, non con il nome dell'indicatore.
    """
    famiglia, codice = chiave.split(":", 1)
    cerca = {"bes": f"bes:{codice}", "prov": f"bes:{codice}", "ims": f"multiscopo:{codice}", "ter": codice}[famiglia]
    riga = _definizioni().get(cerca) or {}
    if not riga and famiglia == "ter":
        with (RADICE / "data" / "definitions" / "istat_territoriali.csv").open(encoding="utf-8") as file:
            riga = next((r for r in csv.DictReader(file, delimiter=";") if r["id"] == codice), {})
    return {
        "definizione": riga.get("definizione", ""),
        "fonti": riga.get("fonti", ""),
        "source_url": riga.get("source_url", ""),
        "source_reference": riga.get("source_reference", ""),
    }


def oggi() -> str:
    return dt.date.today().isoformat()


def cartella_giorno(giorno: str | None = None) -> Path:
    percorso = LAVORO / (giorno or oggi())
    percorso.mkdir(parents=True, exist_ok=True)
    return percorso


def scrivi_json(percorso: Path, dati) -> None:
    percorso.parent.mkdir(parents=True, exist_ok=True)
    percorso.write_text(json.dumps(dati, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def leggi_json(percorso: Path):
    return json.loads(percorso.read_text(encoding="utf-8"))


def numero(testo: str) -> float | None:
    testo = (testo or "").strip()
    if not testo:
        return None
    try:
        return float(testo.replace(".", "").replace(",", ".")) if "," in testo else float(testo)
    except ValueError:
        return None


@cache
def righe(famiglia: str) -> tuple[dict, ...]:
    nome, _ = DATASET[famiglia]
    with (DATI_SITO / nome).open(encoding="utf-8") as file:
        tutte = [r for r in csv.DictReader(file, delimiter=";") if r["Territorio"] != "Territorio"]
    return tuple(tutte)


def serie(chiave: str) -> dict:
    """`bes:03LAV007` -> metadati e valori {territorio: {anno: valore}}."""
    famiglia, codice = chiave.split(":", 1)
    valori: dict[str, dict[int, float]] = {}
    meta = None
    for r in righe(famiglia):
        if r["idIndicatore"] != codice or r["Livello/Variazione"] not in ("Livello", ""):
            continue
        v = numero(r["Dato"])
        if v is None:
            continue
        valori.setdefault(r["Territorio"], {})[int(r["Anno"])] = v
        if meta is None:
            meta = {
                "chiave": chiave,
                "famiglia": famiglia,
                "codice": codice,
                "livello": DATASET[famiglia][1],
                "tema": r["Tema"],
                "nome": r["Indicatore"],
                "unita": r["UDM"],
                "fonte": r["Fonte"],
                "archivio": r["Archivio"],
                "file": f"app/static/data/{DATASET[famiglia][0]}",
            }
    if meta is None:
        raise KeyError(f"indicatore {chiave} assente dai dati del sito")
    anni = sorted({a for per in valori.values() for a in per})
    meta["anni"] = [anni[0], anni[-1]]
    meta["territori"] = len(valori)
    return {"meta": meta, "valori": valori}


def fmt(valore: float, decimali: int = 1) -> str:
    """12345.6 -> '12.345,6': la forma in cui la cifra compare nel testo."""
    testo = f"{valore:,.{decimali}f}"
    return testo.replace(",", "X").replace(".", ",").replace("X", ".")


def decimali_di(valori) -> int:
    """Quanti decimali porta la fonte: si scrive con la sua precisione, non di piu'."""
    massimo = 0
    for v in valori:
        testo = repr(float(v)).rstrip("0").rstrip(".")
        if "." in testo:
            massimo = max(massimo, len(testo.split(".")[1]))
    return min(massimo, 2)


def slug(testo: str) -> str:
    testo = testo.lower()
    for a, b in (("à", "a"), ("è", "e"), ("é", "e"), ("ì", "i"), ("ò", "o"), ("ù", "u"), ("'", "-")):
        testo = testo.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", testo).strip("-")
