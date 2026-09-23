"""Fase 6: la foto di copertina, vera e con licenza, con l'attribuzione registrata.

La fonte e' **Wikimedia Commons**, per una ragione pratica e una di principio.
Pratica: ha un'API aperta che restituisce, per ogni file, autore, licenza e URL
della licenza in forma leggibile da una macchina (`extmetadata`), quindi
l'attribuzione non la trascrive a mano nessuno. Di principio: le licenze sono
Creative Commons o pubblico dominio, e dicono esattamente che cosa si deve
fare per usare la foto. Unsplash e Pexels restano un ripiego documentato
(vedi il workflow): hanno licenze proprie e chiedono una chiave API.

Due comandi:

    # 1. search: stampa i candidati con licenza ammessa, e salva le anteprime
    bin/py -m scripts.trend_articles.photo search <slug> "cantiere edile" "construction site"

    # 2. choose: scarica l'originale, ritaglia a 1200x630, salva JPG e scheda
    bin/py -m scripts.trend_articles.photo choose <slug> "File:Nome del file.jpg" --focus 0.5,0.4 --date 2026-09-23

`search` scarta tutto cio' che non ha una licenza fra quelle ammesse
(CC0, pubblico dominio, CC BY, CC BY-SA), i file che non sono fotografie
(disegni, mappe, loghi, dipinti, scansioni di documenti) e quelli troppo
piccoli per una copertina. Le anteprime vanno **guardate** prima di scegliere:
una foto sbagliata per il pezzo e' peggio di nessuna foto, e nessun filtro lo sa.

`choose` scrive:
- `app/static/img/blog/<slug>.jpg`, 1200x630, JPG qualita' 82;
- `app/static/img/blog/<slug>.photo.json`, la scheda della foto: titolo del
  file, pagina originale, autore, licenza con URL, data, dimensioni originali,
  modifiche fatte (il ritaglio) e il frontmatter `cover_credit` gia' pronto.
"""

from __future__ import annotations

import argparse
import html
import io
import re
import sys

import requests
from PIL import Image

from scripts.trend_articles import common

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "DivarioItaliaBot/1.0 (https://divarioitalia.it; redazione) python-requests"
ALLOWED_LICENSES = re.compile(r"^(cc0|public domain|pd|cc by(-sa)? [1-4]\.0|cc by(-sa)? 2\.5|cc by(-sa)? 2\.0)", re.IGNORECASE)
NOT_A_PHOTO = re.compile(
    r"\b(maps?|mappa|logo|stemma|coat of arms|diagram|chart|grafico|drawings?|disegno|scan|poster|flag|bandiera"
    r"|paintings?|dipinto|affresco|frescos?|engravings?|incisione|lithographs?|litografia|prints?|manuscripts?"
    r"|illustrations?|illustrazione|sculptures?|scultura|icons?)\b",
    re.IGNORECASE,
)
WIDTH, HEIGHT = 1200, 630


def _text(value: str | None) -> str:
    """extmetadata porta HTML: 'Artist' e' spesso un link. Serve il testo."""
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def _api(**params) -> dict:
    params.update(format="json", formatversion=2)
    response = requests.get(API, params=params, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    return response.json()


def _record(page: dict) -> dict | None:
    info = (page.get("imageinfo") or [None])[0]
    if not info:
        return None
    ext = info.get("extmetadata", {})
    return {
        "title": page["title"],
        "page": info.get("descriptionurl"),
        "original": info.get("url"),
        "preview": info.get("thumburl"),
        "mime": info.get("mime"),
        "width": info.get("width"),
        "height": info.get("height"),
        "author": _text(ext.get("Artist", {}).get("value")) or "autore non indicato",
        "license": _text(ext.get("LicenseShortName", {}).get("value")),
        "license_url": ext.get("LicenseUrl", {}).get("value", ""),
        "attribution_required": ext.get("AttributionRequired", {}).get("value", ""),
        "description": _text(ext.get("ImageDescription", {}).get("value"))[:300],
        "date": _text(ext.get("DateTimeOriginal", {}).get("value")),
        "categories": _text(ext.get("Categories", {}).get("value")),
    }


def rejection(r: dict) -> str | None:
    """None se la foto va bene, altrimenti il motivo per cui si scarta."""
    if r["mime"] not in ("image/jpeg", "image/png", "image/webp"):
        return f"formato {r['mime']}"
    if not ALLOWED_LICENSES.match(r["license"] or ""):
        return f"licenza non ammessa: {r['license']!r}"
    if (r["width"] or 0) < WIDTH or (r["height"] or 0) < HEIGHT:
        return f"troppo piccola ({r['width']}x{r['height']})"
    if NOT_A_PHOTO.search(f"{r['title']} {r['categories']}"):
        return "non e' una fotografia (mappa, logo, grafico, disegno, dipinto...)"
    return None


def search(slug: str, queries: list[str], per_query: int = 8) -> list[dict]:
    found, seen = [], set()
    for q in queries:
        data = _api(action="query", generator="search", gsrsearch=f"{q} filetype:bitmap", gsrnamespace=6,
                    gsrlimit=30, prop="imageinfo", iiprop="url|size|mime|extmetadata", iiurlwidth=640)
        for page in data.get("query", {}).get("pages", []):
            r = _record(page)
            if not r or r["title"] in seen:
                continue
            seen.add(r["title"])
            r["rejected"] = rejection(r)
            r["query"] = q
            found.append(r)
    good = [r for r in found if not r["rejected"]][: per_query * len(queries)]
    folder = common.ARTICLES_DIR / slug / "photo-candidates"
    folder.mkdir(parents=True, exist_ok=True)
    for i, r in enumerate(good, 1):
        try:
            response = requests.get(r["preview"], headers={"User-Agent": USER_AGENT}, timeout=30)
            response.raise_for_status()
        except requests.RequestException as error:
            r["preview_file"] = f"anteprima non scaricata: {error!r}"
            continue
        (folder / f"{i:02d}.jpg").write_bytes(response.content)
        r["preview_file"] = str((folder / f"{i:02d}.jpg").relative_to(common.ROOT))
    common.write_json(folder / "candidates.json", {"queries": queries, "accepted": good,
                                                    "rejected": [r for r in found if r["rejected"]]})
    return good


def choose(slug: str, title: str, focus: tuple[float, float], chosen_on: str) -> dict:
    if not title.startswith("File:"):
        title = f"File:{title}"
    data = _api(action="query", titles=title, prop="imageinfo", iiprop="url|size|mime|extmetadata")
    r = _record(data["query"]["pages"][0])
    if r is None:
        raise LookupError(f"{title}: file non trovato su Commons")
    reason = rejection(r)
    if reason:
        raise ValueError(f"{title}: {reason}")

    response = requests.get(r["original"], headers={"User-Agent": USER_AGENT}, timeout=60)
    response.raise_for_status()
    img = Image.open(io.BytesIO(response.content)).convert("RGB")
    w, h = img.size
    ratio = WIDTH / HEIGHT
    if w / h > ratio:  # troppo larga: si taglia ai lati, attorno al fuoco
        new_w = int(h * ratio)
        x0 = int(min(max(focus[0] * w - new_w / 2, 0), w - new_w))
        img = img.crop((x0, 0, x0 + new_w, h))
    else:  # troppo alta: si taglia sopra e sotto
        new_h = int(w / ratio)
        y0 = int(min(max(focus[1] * h - new_h / 2, 0), h - new_h))
        img = img.crop((0, y0, w, y0 + new_h))
    img = img.resize((WIDTH, HEIGHT), Image.LANCZOS)

    common.BLOG_IMG_DIR.mkdir(parents=True, exist_ok=True)
    img.save(common.BLOG_IMG_DIR / f"{slug}.jpg", "JPEG", quality=82, optimize=True, progressive=True)

    credit = {
        "author": r["author"],
        "license": r["license"],
        "license_url": r["license_url"],
        "source_url": r["page"],
        "source_name": "Wikimedia Commons",
        "changes": "Ritagliata e ridimensionata",
    }
    record = {**r, "chosen_on": chosen_on, "site_file": f"/static/img/blog/{slug}.jpg",
              "original_size": [w, h], "focus": list(focus),
              "changes": "ritaglio a 1200x630 e compressione JPG", "cover_credit": credit}
    common.write_json(common.BLOG_IMG_DIR / f"{slug}.photo.json", record)
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("search")
    s.add_argument("slug")
    s.add_argument("queries", nargs="+")
    s.add_argument("--per-query", type=int, default=6)
    c = sub.add_parser("choose")
    c.add_argument("slug")
    c.add_argument("title")
    c.add_argument("--focus", default="0.5,0.5", help="x,y fra 0 e 1: il punto da tenere al centro del ritaglio")
    c.add_argument("--date", required=True, help="data della scelta AAAA-MM-GG, scritta nella scheda")
    args = parser.parse_args(argv)

    if args.command == "search":
        for i, r in enumerate(search(args.slug, args.queries, args.per_query), 1):
            print(f"{i:02d} {r['title']}\n   {r['width']}x{r['height']} | {r['license']} | {r['author'][:60]}\n   {r['page']}")
        print(f"anteprime in data/articles/{args.slug}/photo-candidates/")
    else:
        x, y = (float(v) for v in args.focus.split(","))
        record = choose(args.slug, args.title, (x, y), args.date)
        print(f"-> {record['site_file']}  ({record['license']}, {record['author']})")
        print("cover_credit:")
        for k, v in record["cover_credit"].items():
            print(f'  {k}: "{v}"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
