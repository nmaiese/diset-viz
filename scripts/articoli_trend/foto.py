"""Fase 6: la foto di copertina, vera e con licenza, con l'attribuzione registrata.

La fonte e' **Wikimedia Commons**, per una ragione pratica e una di principio.
Pratica: ha un'API aperta che restituisce, per ogni file, autore, licenza e URL
della licenza in forma leggibile da una macchina (`extmetadata`), quindi
l'attribuzione non la trascrive a mano nessuno. Di principio: le licenze sono
Creative Commons o pubblico dominio, e dicono esattamente che cosa si deve
fare per usare la foto. Unsplash e Pexels restano un ripiego documentato
(vedi il workflow): hanno licenze proprie e chiedono una chiave API.

Due comandi:

    # 1. cerca: stampa i candidati con licenza ammessa, e salva le anteprime
    bin/py -m scripts.articoli_trend.foto cerca <slug> "cantiere edile" "construction site"

    # 2. scegli: scarica l'originale, ritaglia a 1200x630, salva JPG e metadati
    bin/py -m scripts.articoli_trend.foto scegli <slug> "File:Nome del file.jpg" [--fuoco 0.5,0.4]

`cerca` scarta tutto cio' che non ha una licenza fra quelle ammesse
(CC0, pubblico dominio, CC BY, CC BY-SA), i file che non sono fotografie
(SVG, disegni, mappe, loghi, scansioni di documenti) e quelli troppo piccoli
per una copertina. Le anteprime vanno **guardate** prima di scegliere: una
foto sbagliata per il pezzo e' peggio di nessuna foto, e nessun filtro lo sa.

`scegli` scrive:
- `app/static/img/blog/<slug>.jpg`, 1200x630, JPG qualita' 82;
- `app/static/img/blog/<slug>.foto.json`, la scheda della foto: titolo del file,
  pagina originale, autore, licenza con URL, data, dimensioni originali,
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

from scripts.articoli_trend import comuni

API = "https://commons.wikimedia.org/w/api.php"
AGENTE = "DivarioItaliaBot/1.0 (https://divarioitalia.it; redazione) python-requests"
LICENZE_AMMESSE = re.compile(r"^(cc0|public domain|pd|cc by(-sa)? [1-4]\.0|cc by(-sa)? 2\.5|cc by(-sa)? 2\.0)", re.IGNORECASE)
ESCLUSE = re.compile(
    r"\b(maps?|mappa|logo|stemma|coat of arms|diagram|chart|grafico|drawings?|disegno|scan|poster|flag|bandiera"
    r"|paintings?|dipinto|affresco|frescos?|engravings?|incisione|lithographs?|litografia|prints?|manuscripts?"
    r"|illustrations?|illustrazione|sculptures?|scultura|icons?)\b",
    re.IGNORECASE,
)
LARGHEZZA, ALTEZZA = 1200, 630


def _testo(valore: str | None) -> str:
    """extmetadata porta HTML: 'Artist' e' spesso un link. Serve il testo."""
    return html.unescape(re.sub(r"<[^>]+>", "", valore or "")).strip()


def _api(**parametri) -> dict:
    parametri.update(format="json", formatversion=2)
    risposta = requests.get(API, params=parametri, headers={"User-Agent": AGENTE}, timeout=30)
    risposta.raise_for_status()
    return risposta.json()


def _scheda(pagina: dict) -> dict | None:
    info = (pagina.get("imageinfo") or [None])[0]
    if not info:
        return None
    ext = info.get("extmetadata", {})
    licenza = _testo(ext.get("LicenseShortName", {}).get("value"))
    return {
        "titolo": pagina["title"],
        "pagina": info.get("descriptionurl"),
        "originale": info.get("url"),
        "anteprima": info.get("thumburl"),
        "mime": info.get("mime"),
        "larghezza": info.get("width"),
        "altezza": info.get("height"),
        "autore": _testo(ext.get("Artist", {}).get("value")) or "autore non indicato",
        "licenza": licenza,
        "licenza_url": ext.get("LicenseUrl", {}).get("value", ""),
        "attribuzione_richiesta": ext.get("AttributionRequired", {}).get("value", ""),
        "descrizione": _testo(ext.get("ImageDescription", {}).get("value"))[:300],
        "data": _testo(ext.get("DateTimeOriginal", {}).get("value")),
        "categorie": _testo(ext.get("Categories", {}).get("value")),
    }


def ammessa(s: dict) -> str | None:
    """None se la foto va bene, altrimenti il motivo per cui si scarta."""
    if s["mime"] not in ("image/jpeg", "image/png", "image/webp"):
        return f"formato {s['mime']}"
    if not LICENZE_AMMESSE.match(s["licenza"] or ""):
        return f"licenza non ammessa: {s['licenza']!r}"
    if (s["larghezza"] or 0) < LARGHEZZA or (s["altezza"] or 0) < ALTEZZA:
        return f"troppo piccola ({s['larghezza']}x{s['altezza']})"
    if ESCLUSE.search(f"{s['titolo']} {s['categorie']}"):
        return "non e' una fotografia (mappa, logo, grafico, disegno...)"
    return None


def cerca(slug: str, query: list[str], quanti: int = 8) -> list[dict]:
    trovate, visti = [], set()
    for q in query:
        dati = _api(action="query", generator="search", gsrsearch=f"{q} filetype:bitmap", gsrnamespace=6,
                    gsrlimit=30, prop="imageinfo", iiprop="url|size|mime|extmetadata", iiurlwidth=640)
        for pagina in dati.get("query", {}).get("pages", []):
            s = _scheda(pagina)
            if not s or s["titolo"] in visti:
                continue
            visti.add(s["titolo"])
            s["scarto"] = ammessa(s)
            s["query"] = q
            trovate.append(s)
    buone = [s for s in trovate if not s["scarto"]][: quanti * len(query)]
    cartella = comuni.ARTICOLI / slug / "foto-candidate"
    cartella.mkdir(parents=True, exist_ok=True)
    for i, s in enumerate(buone, 1):
        try:
            img = requests.get(s["anteprima"], headers={"User-Agent": AGENTE}, timeout=30).content
            (cartella / f"{i:02d}.jpg").write_bytes(img)
            s["file_anteprima"] = str((cartella / f"{i:02d}.jpg").relative_to(comuni.RADICE))
        except requests.RequestException as errore:
            s["file_anteprima"] = f"anteprima non scaricata: {errore!r}"
    comuni.scrivi_json(cartella / "candidate.json", {"query": query, "ammesse": buone,
                                                     "scartate": [s for s in trovate if s["scarto"]]})
    return buone


def scegli(slug: str, titolo: str, fuoco: tuple[float, float] = (0.5, 0.5)) -> dict:
    if not titolo.startswith("File:"):
        titolo = f"File:{titolo}"
    dati = _api(action="query", titles=titolo, prop="imageinfo", iiprop="url|size|mime|extmetadata")
    s = _scheda(dati["query"]["pages"][0])
    if s is None:
        raise SystemExit(f"{titolo}: file non trovato su Commons")
    motivo = ammessa(s)
    if motivo:
        raise SystemExit(f"{titolo}: {motivo}")

    grezza = requests.get(s["originale"], headers={"User-Agent": AGENTE}, timeout=60).content
    img = Image.open(io.BytesIO(grezza)).convert("RGB")
    w, h = img.size
    rapporto = LARGHEZZA / ALTEZZA
    if w / h > rapporto:  # troppo larga: si taglia ai lati, attorno al fuoco
        nuova_w = int(h * rapporto)
        x0 = int(min(max(fuoco[0] * w - nuova_w / 2, 0), w - nuova_w))
        img = img.crop((x0, 0, x0 + nuova_w, h))
    else:  # troppo alta: si taglia sopra e sotto
        nuova_h = int(w / rapporto)
        y0 = int(min(max(fuoco[1] * h - nuova_h / 2, 0), h - nuova_h))
        img = img.crop((0, y0, w, y0 + nuova_h))
    img = img.resize((LARGHEZZA, ALTEZZA), Image.LANCZOS)

    comuni.IMG_BLOG.mkdir(parents=True, exist_ok=True)
    jpg = comuni.IMG_BLOG / f"{slug}.jpg"
    img.save(jpg, "JPEG", quality=82, optimize=True, progressive=True)

    credito = {
        "autore": s["autore"],
        "licenza": s["licenza"],
        "licenza_url": s["licenza_url"],
        "fonte_url": s["pagina"],
        "fonte_nome": "Wikimedia Commons",
        "modifiche": "Ritagliata e ridimensionata",
    }
    scheda = {**s, "scelta_il": comuni.oggi(), "file_sito": f"/static/img/blog/{slug}.jpg",
              "originale_dimensioni": [w, h], "fuoco": list(fuoco),
              "modifiche": "ritaglio a 1200x630 e compressione JPG", "cover_credit": credito}
    comuni.scrivi_json(comuni.IMG_BLOG / f"{slug}.foto.json", scheda)
    return scheda


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sotto = parser.add_subparsers(dest="comando", required=True)
    c = sotto.add_parser("cerca")
    c.add_argument("slug")
    c.add_argument("query", nargs="+")
    c.add_argument("--quanti", type=int, default=6)
    s = sotto.add_parser("scegli")
    s.add_argument("slug")
    s.add_argument("titolo")
    s.add_argument("--fuoco", default="0.5,0.5", help="x,y fra 0 e 1: il punto da tenere al centro del ritaglio")
    args = parser.parse_args(argv)

    if args.comando == "cerca":
        for i, f in enumerate(cerca(args.slug, args.query, args.quanti), 1):
            print(f"{i:02d} {f['titolo']}\n   {f['larghezza']}x{f['altezza']} | {f['licenza']} | {f['autore'][:60]}\n   {f['pagina']}")
        print(f"anteprime in data/articoli/{args.slug}/foto-candidate/")
    else:
        x, y = (float(v) for v in args.fuoco.split(","))
        scheda = scegli(args.slug, args.titolo, (x, y))
        print(f"-> {scheda['file_sito']}  ({scheda['licenza']}, {scheda['autore']})")
        print("cover_credit:")
        for k, v in scheda["cover_credit"].items():
            print(f'  {k}: "{v}"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
