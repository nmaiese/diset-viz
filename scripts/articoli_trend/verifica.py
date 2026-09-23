"""Fase 8: le guardie che fermano un pezzo prima della PR.

Ogni guardia e' una smentita ricalcolabile, non un giudizio di stile. Un
**ERRORE** ferma il pezzo, un **AVVISO** va letto da una persona.

1. Frontmatter: titolo, descrizione, data, copertina, alt, il trend d'origine
   (`trend:` con tema, segnali, fonte, URL, data di rilevazione), il blocco
   `dataset:` con metodo e download, l'attribuzione della foto.
2. Foto: la scheda `<slug>.foto.json` esiste, la licenza e' fra quelle
   ammesse, e `cover_credit` del pezzo dice le stesse cose della scheda.
3. Tipografia: niente `—`, `–`, `;`, `…` (content/STYLE.md).
4. Cifre: ogni numero del testo sta nel dossier del pezzo (con la stessa
   scrittura, virgola decimale e precisione), oppure fra le `cifre_esterne`
   del frontmatter con la loro fonte. Anni e piccoli conteggi passano come
   avvisi.
5. "Media nazionale" e "media italiana" sono vietate sulle medie semplici dei
   territori, che sono le sole che il dossier calcola.
6. Link interni: ogni `/indicatore/`, `/tema/`, `/blog/`, `/regione/`,
   `/provincia/` risponde 200 dall'app, senza redirect.
7. Link esterni nel testo: rispondono, e stanno anche nella sezione delle fonti.
8. Figure: ogni `<!-- figura: nome -->` ha il suo SVG.
9. Lunghezza: oltre mille parole e' un avviso (REVIEW.md).

    bin/py -m scripts.articoli_trend.verifica content/posts/2026-09-23-<slug>.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import frontmatter
import requests

from scripts.articoli_trend import comuni
from scripts.articoli_trend.foto import LICENZE_AMMESSE

VIETATI = {"—": "em-dash", "–": "en-dash", ";": "punto e virgola", "…": "ellissi"}
NUMERO = re.compile(r"(?<![\w/.-])(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)(?![\w/])")
LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
INTERNI = ("/indicatore/", "/tema/", "/blog/", "/regione/", "/provincia/", "/qualita-della-vita")


def _corpo_pulito(testo: str) -> str:
    testo = re.sub(r"<!--.*?-->", " ", testo, flags=re.DOTALL)
    testo = LINK.sub(lambda m: m.group(1), testo)  # il testo del link resta, l'URL no
    testo = re.sub(r"\{:[^}]*\}", " ", testo)
    return testo


def verifica(percorso: Path) -> tuple[list[str], list[str]]:
    errori, avvisi = [], []
    post = frontmatter.load(percorso)
    m, corpo = post.metadata, post.content
    slug = m.get("slug") or re.sub(r"^\d{4}-\d{2}-\d{2}-", "", percorso.stem)

    # 1. frontmatter
    for campo in ("title", "description", "date", "cover", "cover_alt", "cover_credit", "trend", "dataset"):
        if not m.get(campo):
            errori.append(f"frontmatter: manca `{campo}`")
    trend = m.get("trend") or {}
    for campo in ("tema", "rilevato", "segnali"):
        if not trend.get(campo):
            errori.append(f"trend: manca `{campo}` (perche' questo pezzo, oggi?)")
    for i, s in enumerate(trend.get("segnali") or []):
        for campo in ("tipo", "testo", "fonte", "url", "data"):
            if not s.get(campo):
                errori.append(f"trend.segnali[{i}]: manca `{campo}`")
    ds = m.get("dataset") or {}
    for campo in ("name", "description", "method", "download", "source_url"):
        if not ds.get(campo):
            errori.append(f"dataset: manca `{campo}`")
    if ds.get("download") and not (comuni.RADICE / "app" / ds["download"].lstrip("/")).is_file():
        errori.append(f"dataset.download: {ds['download']} non esiste")
    if len(m.get("description", "")) > 160:
        avvisi.append(f"description di {len(m['description'])} caratteri (oltre 160 Google la taglia)")

    # 2. foto
    scheda_path = comuni.IMG_BLOG / f"{slug}.foto.json"
    if not scheda_path.is_file():
        errori.append(f"foto: manca la scheda {scheda_path.relative_to(comuni.RADICE)} (usa foto.py scegli)")
    else:
        scheda = comuni.leggi_json(scheda_path)
        if not LICENZE_AMMESSE.match(scheda.get("licenza", "")):
            errori.append(f"foto: licenza non ammessa {scheda.get('licenza')!r}")
        credito = m.get("cover_credit") or {}
        for campo in ("autore", "licenza", "licenza_url", "fonte_url"):
            if str(credito.get(campo, "")).strip() != str(scheda["cover_credit"].get(campo, "")).strip():
                errori.append(f"cover_credit.{campo} diverso dalla scheda della foto")
        if m.get("cover") != scheda.get("file_sito"):
            errori.append(f"cover {m.get('cover')} diversa dalla foto registrata {scheda.get('file_sito')}")

    # 3. tipografia
    testo_tutto = corpo + " " + " ".join(str(m.get(k, "")) for k in ("title", "description", "cover_alt", "seo_title"))
    for carattere, nome in VIETATI.items():
        n = testo_tutto.count(carattere)
        if n:
            errori.append(f"tipografia: {n} volte {nome} {carattere!r}")

    # 4. cifre
    dossier_path = comuni.ARTICOLI / slug / "dossier.json"
    if not dossier_path.is_file():
        errori.append(f"cifre: manca il dossier {dossier_path.relative_to(comuni.RADICE)}")
    else:
        dossier = comuni.leggi_json(dossier_path)
        ammesse = {c["cifra"] for ind in dossier["indicatori"] for c in ind["cifre"]}
        ammesse |= {c.replace(".", "") for c in list(ammesse)}
        # le cifre che fanno parte della definizione (15-34 anni, per 10.000)
        for ind in dossier["indicatori"]:
            testo_meta = " ".join(str(ind["meta"].get(k, "")) for k in ("nome", "unita", "definizione"))
            ammesse |= set(re.findall(r"\d+(?:\.\d{3})*(?:,\d+)?", testo_meta))
        esterne = m.get("cifre_esterne") or []
        for e in esterne:
            if not e.get("fonte") or not e.get("url"):
                errori.append(f"cifre_esterne: {e.get('cifra')} senza fonte o url")
        ammesse |= {str(e.get("cifra")) for e in esterne}
        pulito = _corpo_pulito(corpo) + " " + m.get("description", "") + " " + m.get("title", "")
        for n in sorted(set(NUMERO.findall(pulito))):
            if n in ammesse:
                continue
            if re.fullmatch(r"(19|20)\d\d", n):
                continue
            if re.fullmatch(r"\d{1,3}", n) and int(n) <= 110:
                avvisi.append(f"cifre: {n} non e' nel dossier (un conteggio? controllalo)")
                continue
            errori.append(f"cifre: {n} non sta nel dossier ne' fra le cifre_esterne")

    # 5. media nazionale
    for frase in ("media nazionale", "media italiana", "media dell'italia"):
        # "non e' la media nazionale" e' proprio la frase giusta: si guarda solo
        # l'uso affermativo.
        usi = [m_.start() for m_ in re.finditer(re.escape(frase), corpo.lower())]
        if any("non " not in corpo.lower()[max(0, i - 20):i] for i in usi):
            esterne_txt = " ".join(str(e.get("cosa", "")) for e in (m.get("cifre_esterne") or []))
            if frase not in esterne_txt.lower():
                errori.append(f"'{frase}': il dossier ha solo medie semplici dei territori")

    # 6-7. link
    from app import app

    client = app.test_client()
    esterni_testo = set()
    sezione_fonti = corpo.split("## Fonti", 1)[1] if "## Fonti" in corpo else ""
    for _, url in LINK.findall(corpo):
        if url.startswith(INTERNI) or url.startswith("/"):
            percorso_url = url.split("#")[0]
            stato = client.get(percorso_url).status_code
            if stato != 200:
                errori.append(f"link interno {url} risponde {stato}")
        elif url.startswith("http"):
            esterni_testo.add(url)
    for url in sorted(esterni_testo):
        if url not in sezione_fonti:
            errori.append(f"fonte {url} citata nel testo ma assente dalla sezione '## Fonti'")
        try:
            r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 divarioitalia-verifica"}, allow_redirects=True)
            if r.status_code >= 400:
                errori.append(f"fonte {url} risponde {r.status_code}")
        except requests.RequestException as errore:
            avvisi.append(f"fonte {url} non raggiunta: {errore.__class__.__name__}")

    # 8. figure
    for nome in re.findall(r"<!--\s*figura:\s*([a-z0-9-]+)\s*-->", corpo):
        if not (comuni.FIGURE / slug / f"{nome}.svg").is_file():
            errori.append(f"figura {nome}: manca content/figure/{slug}/{nome}.svg")

    # 9. lunghezza
    parole = len(re.findall(r"\w+", _corpo_pulito(re.sub(r"^\|.*\|$", "", corpo, flags=re.MULTILINE))))
    if parole > 1000:
        avvisi.append(f"lunghezza: {parole} parole fuori dalle tabelle (REVIEW.md ne chiede al massimo mille)")
    return errori, avvisi


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("articoli", nargs="+")
    args = parser.parse_args(argv)
    esito = 0
    for a in args.articoli:
        errori, avvisi = verifica(Path(a))
        print(f"\n{a}: {len(errori)} errori, {len(avvisi)} avvisi")
        for e in errori:
            print(f"  ERRORE  {e}")
        for w in avvisi:
            print(f"  avviso  {w}")
        esito |= bool(errori)
    return esito


if __name__ == "__main__":
    sys.exit(main())
