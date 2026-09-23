"""Percorsi, lettura dei dataset del sito e formattazione dei numeri in italiano.

I dataset sono quelli che il sito serve (`app/static/data/Assoluti_*.csv`), con
lo stesso contratto a dodici colonne: ogni riga porta gia' fonte e archivio di
provenienza. Il workflow non scarica una seconda copia dei dati per scriverci
sopra un articolo: un numero nel pezzo deve essere lo stesso numero che il
lettore trova nella scheda dell'indicatore.
"""

from __future__ import annotations

import csv
import json
import re
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE_DATA = ROOT / "app" / "static" / "data"
TREND_DIR = ROOT / "data" / "trend"
ARTICLES_DIR = ROOT / "data" / "articles"
DERIVED_DIR = ROOT / "data" / "derived"
TOPICS_CONFIG = ROOT / "config" / "trend_topics.json"
POSTS_DIR = ROOT / "content" / "posts"
FIGURES_DIR = ROOT / "content" / "figures"
BLOG_IMG_DIR = ROOT / "app" / "static" / "img" / "blog"
DOWNLOAD_DIR = ROOT / "app" / "static" / "data" / "articles"

# Famiglia -> file del sito e livello territoriale. La chiave e' quella che
# `config/trend_topics.json` usa per nominare un indicatore: `bes:03LAV007`.
DATASETS = {
    "ter": ("Assoluti_Regione.csv", "regione"),
    "bes": ("Assoluti_BES_Regione.csv", "regione"),
    "ims": ("Assoluti_Multiscopo_Regione.csv", "regione"),
    "prov": ("Assoluti_Provincia.csv", "provincia"),
}

MEZZOGIORNO = {
    "Abruzzo", "Molise", "Campania", "Puglia", "Basilicata", "Calabria",
    "Sicilia", "Sardegna",
}
AREAS = ("Italia", "Nord", "Centro", "Mezzogiorno")


@cache
def province_regions() -> dict[str, str]:
    with (SITE_DATA / "province_codes.csv").open(encoding="utf-8") as file:
        return {r["name"]: r["region"] for r in csv.DictReader(file, delimiter=";")}


def macro_area(territory: str, level: str) -> str:
    """Mezzogiorno o Centro-Nord, per una regione o una provincia."""
    region = province_regions().get(territory, territory) if level == "provincia" else territory
    return "Mezzogiorno" if region in MEZZOGIORNO else "Centro-Nord"


@cache
def _definitions() -> dict[str, dict]:
    with (ROOT / "data" / "definitions" / "federated.csv").open(encoding="utf-8") as file:
        return {r["id"]: r for r in csv.DictReader(file, delimiter=";")}


def definition(key: str) -> dict:
    """La definizione della fonte e l'URL del file da cui viene il dato.

    `data/definitions/federated.csv` e' lo stesso registro che usa
    `scripts/definition_check.py`: la definizione nel pezzo va confrontata
    con questa, non con il nome dell'indicatore.
    """
    family, code = key.split(":", 1)
    if family == "ext":
        meta = derived_series(code)["meta"]
        return {"definition": meta["method"], "sources": meta["source"],
                "source_url": meta["derived_source_url"], "source_reference": meta["script"]}
    lookup = {"bes": f"bes:{code}", "prov": f"bes:{code}", "ims": f"multiscopo:{code}", "ter": code}[family]
    row = _definitions().get(lookup) or {}
    if not row and family == "ter":
        with (ROOT / "data" / "definitions" / "istat_territoriali.csv").open(encoding="utf-8") as file:
            row = next((r for r in csv.DictReader(file, delimiter=";") if r["id"] == code), {})
    return {
        "definition": row.get("definizione", ""),
        "sources": row.get("fonti", ""),
        "source_url": row.get("source_url", ""),
        "source_reference": row.get("source_reference", ""),
    }


def day_dir(day: str) -> Path:
    path = TREND_DIR / day
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def parse_number(text: str) -> float | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return float(text.replace(".", "").replace(",", ".")) if "," in text else float(text)
    except ValueError:
        return None


@cache
def rows(family: str) -> tuple[dict, ...]:
    name, _ = DATASETS[family]
    with (SITE_DATA / name).open(encoding="utf-8") as file:
        return tuple(r for r in csv.DictReader(file, delimiter=";") if r["Territorio"] != "Territorio")


def derived_series(name: str) -> dict:
    """`ext:<name>`: un'elaborazione versionata in data/derived/.

    Il CSV porta territory, year, value. Il JSON accanto porta name, unit,
    source, archive, source_url e **method**: un'elaborazione senza metodo non
    entra in un dossier.
    """
    meta_file = read_json(DERIVED_DIR / f"{name}.json")
    if not meta_file.get("method"):
        raise ValueError(f"elaborazione {name} senza method: aggiungilo nel JSON accanto al CSV")
    values: dict[str, dict[int, float]] = {}
    with (DERIVED_DIR / f"{name}.csv").open(encoding="utf-8") as file:
        for r in csv.DictReader(file):
            values.setdefault(r["territory"], {})[int(r["year"])] = float(r["value"])
    years = sorted({y for per in values.values() for y in per})
    if set(values) <= set(AREAS):
        level = "ripartizione"
    elif set(values) <= set(province_regions()):
        level = "provincia"
    else:
        level = "regione"
    meta = {
        "key": f"ext:{name}", "family": "ext", "code": name, "level": level,
        "theme": "", "name": meta_file["name"], "unit": meta_file["unit"],
        "source": meta_file["source"], "archive": meta_file.get("archive", ""),
        "file": f"data/derived/{name}.csv", "method": meta_file["method"],
        "script": meta_file.get("script", ""), "derived_source_url": meta_file.get("source_url", ""),
        "years": [years[0], years[-1]], "territories": len(values),
    }
    return {"meta": meta, "values": values}


def series(key: str) -> dict:
    """`bes:03LAV007` -> metadati e valori {territorio: {anno: valore}}."""
    family, code = key.split(":", 1)
    if family == "ext":
        return derived_series(code)
    values: dict[str, dict[int, float]] = {}
    meta = None
    for r in rows(family):
        if r["idIndicatore"] != code or r["Livello/Variazione"] not in ("Livello", ""):
            continue
        v = parse_number(r["Dato"])
        if v is None:
            continue
        values.setdefault(r["Territorio"], {})[int(r["Anno"])] = v
        if meta is None:
            meta = {
                "key": key, "family": family, "code": code, "level": DATASETS[family][1],
                "theme": r["Tema"], "name": r["Indicatore"], "unit": r["UDM"],
                "source": r["Fonte"], "archive": r["Archivio"],
                "file": f"app/static/data/{DATASETS[family][0]}",
            }
    if meta is None:
        raise KeyError(f"indicatore {key} assente dai dati del sito ({DATASETS[family][0]})")
    years = sorted({y for per in values.values() for y in per})
    meta["years"] = [years[0], years[-1]]
    meta["territories"] = len(values)
    return {"meta": meta, "values": values}


def fmt(value: float, decimals: int = 1) -> str:
    """12345.6 -> '12.345,6': la forma in cui la cifra compare nel testo."""
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def source_decimals(values) -> int:
    """Quanti decimali porta la fonte: si scrive con la sua precisione, non di piu'."""
    most = 0
    for v in values:
        text = repr(float(v)).rstrip("0").rstrip(".")
        if "." in text:
            most = max(most, len(text.split(".")[1]))
    return min(most, 2)


def slugify(text: str) -> str:
    text = text.lower()
    for a, b in (("à", "a"), ("è", "e"), ("é", "e"), ("ì", "i"), ("ò", "o"), ("ù", "u"), ("'", "-")):
        text = text.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")
