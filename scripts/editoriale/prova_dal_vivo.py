"""Verifica sul sito live che prosa aggiunta tra due commit sia pubblicata."""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import frontmatter
import requests

ROOT = Path(__file__).resolve().parents[2]
HEADERS = {"User-Agent": "DivarioCheck/1.0"}


@dataclass(frozen=True)
class Frase:
    testo: str
    riga: int


def _puliscimarkdown(testo: str) -> str:
    testo = re.sub(r"<!--.*?-->", " ", testo)
    testo = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", testo)
    testo = re.sub(r"!\[([^]]*)\]\([^)]*\)", r"\1", testo)
    testo = re.sub(r"[*_`~]", "", testo)
    return re.sub(r"^\s*(?:>\s?|[-+]\s+|\d+[.)]\s+)", "", testo)


def estrai_frasi_nuove(diff: str, body_start: int | None = None) -> list[Frase]:
    frasi, in_frontmatter, delimiter_count = [], False, 0
    new_line = 0
    for line in diff.splitlines():
        hunk = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
        if hunk:
            new_line = int(hunk.group(1))
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            content = line[1:]
            if content.strip() == "---":
                delimiter_count += 1
                in_frontmatter = delimiter_count == 1
            elif ((body_start is not None and new_line >= body_start)
                  or (body_start is None and not in_frontmatter and delimiter_count >= 2)):
                clean = _puliscimarkdown(content).strip()
                # Una riga di Markdown e un paragrafo intero: si confronta una frase
                # alla volta, cosi un link o un tag che spezza il testo nella pagina
                # non fa mancare un paragrafo di dieci frasi per una virgola.
                for frase in re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ý\"'«(])", clean):
                    if len(re.findall(r"\b[\wÀ-ÿ’'-]+\b", frase)) >= 8:
                        frasi.append(Frase(frase.strip(), new_line))
            new_line += 1
        elif line.startswith(" "):
            if line[1:].strip() == "---":
                delimiter_count += 1
                in_frontmatter = delimiter_count == 1
            new_line += 1
        elif line.startswith("-"):
            continue
    return frasi


def campiona(frasi: list[Frase], numero: int) -> list[Frase]:
    return sorted(frasi, key=lambda f: (-len(f.testo), f.riga))[:max(0, numero)]


def url_post(path, meta):
    slug = meta.get("slug") or re.sub(r"^\d{4}-\d{2}-\d{2}-", "", Path(path).stem)
    return f"/blog/{slug}"


def url_indicatore(path, meta):
    from app import indicator_view, sources
    key = str(meta.get("key", ""))
    family, raw_id = sources.split_internal_id(key)
    view = indicator_view.build_indicator_view(family, raw_id)
    if view:
        for level in view["levels"]:
            if not meta.get("level") or level["key"] == meta["level"]:
                return level["canonical_path"]
    raise ValueError(f"URL scheda non risolto: {path} ({key})")


def url_contenuto(path, meta):
    path = str(path)
    if path.startswith("content/posts/"):
        return url_post(path, meta)
    return url_indicatore(path, meta)


def normalizza(testo):
    testo = html.unescape(testo).replace("’", "'").replace("‘", "'").replace("\u00a0", " ")
    testo = unicodedata.normalize("NFKC", testo)
    testo = re.sub(r"<[^>]+>", " ", testo)
    return re.sub(r"\s+", " ", testo).strip().casefold()


def _compatta(testo):
    """Il testo senza nessuno spazio: nell'HTML un link o un tag spezza le parole con
    uno spazio o senza («nell' audizione» contro «nell'audizione»), e per sapere se
    una frase c'e conta l'ordine dei caratteri, non la spaziatura."""
    return re.sub(r"\s+", "", normalizza(testo))


def frase_trovata(pagina, frase):
    return _compatta(frase) in _compatta(pagina)


def scarica(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
    except requests.RequestException:
        return 0, ""
    return response.status_code, response.text


def _leggi_meta(path):
    return frontmatter.load(path).metadata


def _contenuti_cambiati(da, a):
    raw = subprocess.check_output(["git", "diff", "--name-status", da, a, "--"], cwd=ROOT, text=True)
    files = []
    for row in raw.splitlines():
        parts = row.split("\t")
        if parts[0] == "D":
            continue
        path = parts[-1]
        if re.fullmatch(r"content/(?:posts|indicators)/[^/]+\.md", path):
            files.append(path)
    return files


def _diff_file(da, a, path):
    return subprocess.check_output(["git", "diff", "--unified=0", da, a, "--", path], cwd=ROOT, text=True)


def _body_start(commit, path):
    content = subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT, text=True)
    delimiters = [i for i, line in enumerate(content.splitlines(), 1) if line.strip() == "---"]
    return delimiters[1] + 1 if len(delimiters) >= 2 else 1


def verifica_file(path, url, meta, frasi, scarica=scarica, tentativi=3, pausa=20, base="https://divarioitalia.it"):
    status, body = 0, ""
    trovate = [False] * len(frasi)
    for tentativo in range(tentativi):
        status, body = scarica(urljoin(base.rstrip("/") + "/", url.lstrip("/")))
        if status == 200:
            trovate = [frase_trovata(body, f.testo) for f in frasi]
            if all(trovate):
                break
        if tentativo + 1 < tentativi:
            time.sleep(pausa)
    download_status = None
    download = (meta.get("dataset") or {}).get("download") if isinstance(meta.get("dataset"), dict) else None
    if download:
        download_status, _ = scarica(urljoin(base.rstrip("/") + "/", download.lstrip("/")))
    esito = int(status != 200 or not all(trovate) or (download_status is not None and download_status != 200))
    return {"file": str(path), "url": url, "pagina_status": status, "download_status": download_status,
            "frasi": [{"testo": f.testo, "riga": f.riga, "trovata": ok} for f, ok in zip(frasi, trovate)], "esito": esito}


def esegui(da, a, campione=4, scarica=scarica, tentativi=3, pausa=20, base="https://divarioitalia.it"):
    files = _contenuti_cambiati(da, a)
    results = []
    for path in files:
        meta = _leggi_meta(ROOT / path)
        diff = _diff_file(da, a, path)
        frasi = campiona(estrai_frasi_nuove(diff, _body_start(a, path)), campione)
        results.append(verifica_file(path, url_contenuto(path, meta), meta, frasi, scarica, tentativi, pausa, base))
    return {"esito": max((r["esito"] for r in results), default=0), "nessun_file": not files, "risultati": results}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--da", required=True)
    parser.add_argument("--a", required=True)
    parser.add_argument("--base", default="https://divarioitalia.it")
    parser.add_argument("--campione", type=int, default=4)
    parser.add_argument("--tentativi", type=int, default=3)
    parser.add_argument("--pausa", type=float, default=20)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.campione < 0 or args.tentativi < 1 or args.pausa < 0:
        parser.error("campione e pausa non negativi, tentativi almeno 1")
    try:
        result = esegui(args.da, args.a, args.campione, tentativi=args.tentativi, pausa=args.pausa, base=args.base)
    except (subprocess.CalledProcessError, OSError, ValueError) as error:
        print(f"Errore: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["nessun_file"]:
        print("Nessun file di contenuto cambiato.")
    else:
        for r in result["risultati"]:
            trovate = sum(f["trovata"] for f in r["frasi"])
            print(f"{r['file']} -> {r['url']}: {trovate} frasi su {len(r['frasi'])} trovate (pagina {r['pagina_status']})")
            for f in r["frasi"]:
                if not f["trovata"]:
                    print(f"  MANCANTE riga {f['riga']}: {f['testo']}")
            if r["download_status"] not in (None, 200):
                print(f"  CSV dataset.download: HTTP {r['download_status']}")
    return result["esito"]


if __name__ == "__main__":
    raise SystemExit(main())
