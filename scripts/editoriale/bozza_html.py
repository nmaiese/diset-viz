#!/usr/bin/env python3
"""Rende una bozza (articolo del blog o scheda) come pagina HTML autonoma, da aprire in locale.

Regola della pipeline editoriale dal 7 ottobre 2026 (decisione del titolare): ogni articolo,
prima del merge, si legge in una pagina HTML fatta come quella del sito, con testo, grafici,
foto, didascalie e fonti. Il merge è la pubblicazione e avviene solo dopo che la bozza è
nell'indice e la direzione ha dato l'ok.

    bin/py -m scripts.editoriale.bozza_html <slug> --pr 353
    bin/py -m scripts.editoriale.bozza_html <slug> --radice /percorso/del/worktree --pr 353 --stato "da leggere"

La pagina è quella che il sito serve per `/blog/<slug>`, renderizzata dal client di test di
Flask del worktree indicato (la bozza deve essere in `content/posts` con `draft: false`:
la CI prova lo stato finale, il merge resta fermo). Il foglio di stile e le immagini sono
incorporati, font compresi (così la pagina si legge anche senza rete); gli script
(tracciamento, consenso) sono tolti. I link interni diventano
assoluti verso https://divarioitalia.it: quelli a pagine nuove, non ancora online, daranno
404 finché non c'è il deploy. Il CSV del dataset si scarica dalla bozza stessa.

Scrive in `--out` (default `/mnt/c/Users/Nilo/orca/divario/bozze`) il file `AAAAMMGG-<slug>.html`
e aggiorna `indice.json` e `index.html` (titolo, data, stato, link alla bozza e alla PR).
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import mimetypes
import os
import posixpath
import re
import sys
from datetime import date
from pathlib import Path

SITO = "https://divarioitalia.it"
OUT_DEFAULT = Path("/mnt/c/Users/Nilo/orca/divario/bozze")
STATI = ("da leggere", "approvato", "pubblicato")
LIMITE_INCORPORA = 400_000  # byte: oltre, l'immagine resta un link al sito


def data_uri(contenuto: bytes, percorso: str) -> str:
    # python:3.12-slim non ha sempre .woff2 nel catalogo MIME di sistema.
    tipo = (
        "font/woff2"
        if Path(percorso).suffix.lower() == ".woff2"
        else (mimetypes.guess_type(percorso)[0] or "application/octet-stream")
    )
    return f"data:{tipo};base64,{base64.b64encode(contenuto).decode('ascii')}"


def assoluto(url: str) -> str:
    if url.startswith(("http://", "https://", "data:", "#", "mailto:", "tel:")):
        return url
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return SITO + url
    return url


def riscrivi_css(css: str, fetch, base: str = "/") -> str:
    """url(...) del foglio di stile: font e immagini piccole incorporati o assoluti."""

    def sost(m):
        url = m.group(2).strip()
        if url.startswith(("data:", "#")):
            return m.group(0)
        if not url.startswith(("/", "http://", "https://", "//")):
            url = posixpath.normpath(posixpath.join(base, url))
        pulito = url.split("?")[0]
        corpo = fetch(pulito) if pulito.startswith("/") else None
        if corpo is not None and len(corpo) <= LIMITE_INCORPORA:
            return f"url({m.group(1)}{data_uri(corpo, pulito)}{m.group(1)})"
        return f"url({m.group(1)}{assoluto(url)}{m.group(1)})"

    return re.sub(r"url\((['\"]?)([^)'\"]+)\1\)", sost, css)


def incorpora(pagina: str, fetch) -> str:
    """Toglie gli script, incorpora fogli di stile e immagini, rende assoluti i link."""
    pagina = re.sub(r"<script\b.*?</script>", "", pagina, flags=re.S | re.I)
    pagina = re.sub(r'<link\b[^>]*rel="(?:preload|prefetch|alternate|canonical|shortcut icon|icon)"[^>]*>', "", pagina, flags=re.I)

    def foglio(m):
        href = re.search(r'href="([^"]+)"', m.group(0))
        if not href:
            return m.group(0)
        corpo = fetch(href.group(1).split("?")[0]) if href.group(1).startswith("/") else None
        if corpo is None:
            return f'<link rel="stylesheet" href="{assoluto(href.group(1))}">'
        css = riscrivi_css(corpo.decode("utf-8", "replace"), fetch, posixpath.dirname(href.group(1).split("?")[0]) + "/")
        return f"<style>\n{css}\n</style>"

    pagina = re.sub(r'<link\b[^>]*rel="stylesheet"[^>]*>', foglio, pagina, flags=re.I)

    def immagine(m):
        percorso = m.group(2).split("?")[0]
        if m.group(2).startswith("/"):
            corpo = fetch(percorso)
            if corpo is not None and len(corpo) <= LIMITE_INCORPORA:
                return f'{m.group(1)}"{data_uri(corpo, percorso)}"'
            return f'{m.group(1)}"{assoluto(m.group(2))}"'
        return m.group(0)

    pagina = re.sub(r'(<img\b[^>]*?\bsrc=)"([^"]+)"', immagine, pagina, flags=re.I)

    def collegamento(m):
        percorso = m.group(2).split("?")[0]
        if percorso.endswith(".csv") and m.group(2).startswith("/static/"):
            corpo = fetch(percorso)
            if corpo is not None:
                return f'{m.group(1)}"{data_uri(corpo, percorso)}" download="{Path(percorso).name}"'
        return f'{m.group(1)}"{assoluto(m.group(2))}"'

    pagina = re.sub(r'(<a\b[^>]*?\bhref=)"([^"]+)"', collegamento, pagina, flags=re.I)
    return pagina


def banner(slug: str, pr: str | None, quando: str) -> str:
    link_pr = f' PR <a href="https://github.com/nmaiese/diset-viz/pull/{html.escape(pr)}">#{html.escape(pr)}</a>.' if pr else ""
    return (
        '<div style="position:sticky;top:0;z-index:99999;background:#a75001;color:#fff;'
        'font:600 14px/1.4 system-ui,sans-serif;padding:8px 16px;text-align:center">'
        f"BOZZA, non pubblicata ({html.escape(slug)}, generata il {html.escape(quando)}).{link_pr}"
        " I link a pagine nuove danno 404 finché non c'è il deploy.</div>"
    )


def metti_banner(pagina: str, testo: str) -> str:
    # L'ultimo <body ...>: il primo può stare dentro un commento o un blocco di testo.
    tutti = list(re.finditer(r"<body\b[^>]*>", pagina, flags=re.I))
    if not tutti:
        return testo + pagina
    fine = tutti[-1].end()
    return pagina[:fine] + testo + pagina[fine:]


def titolo_pagina(pagina: str) -> str:
    h1 = re.search(r"<h1\b[^>]*>(.*?)</h1>", pagina, flags=re.S | re.I)
    t = h1.group(1) if h1 else (re.search(r"<title>(.*?)</title>", pagina, flags=re.S | re.I) or [None, "Bozza"])[1]
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", t))).strip()


def aggiorna_registro(registro: list[dict], voce: dict) -> list[dict]:
    """Una voce per slug: se c'è già, si tengono lo stato e le date scelti a mano."""
    out = []
    trovata = False
    for v in registro:
        if v["slug"] == voce["slug"]:
            trovata = True
            out.append({**voce, "stato": v.get("stato", voce["stato"]) if not voce.get("stato_esplicito") else voce["stato"]})
        else:
            out.append(v)
    if not trovata:
        out.append(voce)
    for v in out:
        v.pop("stato_esplicito", None)
    return sorted(out, key=lambda v: (v["data"], v["slug"]), reverse=True)


def render_indice(registro: list[dict]) -> str:
    righe = []
    for v in registro:
        pr = (f'<a href="https://github.com/nmaiese/diset-viz/pull/{html.escape(str(v["pr"]))}">PR #{html.escape(str(v["pr"]))}</a>' if v.get("pr") else "")
        righe.append(
            "<tr>"
            f'<td><a href="{html.escape(v["file"])}">{html.escape(v["titolo"])}</a></td>'
            f'<td>{html.escape(v["data"])}</td>'
            f'<td><span class="stato s-{html.escape(v["stato"].replace(" ", "-"))}">{html.escape(v["stato"])}</span></td>'
            f"<td>{pr}</td></tr>"
        )
    return (
        '<!doctype html><html lang="it"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Bozze di Divario Italia</title><style>"
        "body{font:16px/1.5 system-ui,sans-serif;max-width:60rem;margin:2rem auto;padding:0 1rem;color:#121519}"
        "table{width:100%;border-collapse:collapse}td,th{padding:.5rem .4rem;border-bottom:1px solid #d5d9de;text-align:left;vertical-align:top}"
        "a{color:#a75001}.stato{padding:.1rem .5rem;border:1px solid #121519;font-size:.85rem}"
        ".s-approvato{background:#e4f1e4}.s-pubblicato{background:#e6edf5}.s-da-leggere{background:#fff3e0}"
        "</style></head><body><h1>Bozze di Divario Italia</h1>"
        "<p>Ogni articolo si legge qui prima del merge (che è la pubblicazione). Stato: da leggere, approvato, pubblicato.</p>"
        "<table><thead><tr><th>Titolo</th><th>Data</th><th>Stato</th><th>Richiesta di modifica</th></tr></thead><tbody>"
        + "".join(righe)
        + "</tbody></table></body></html>"
    )


def data_dal_file(radice: Path, slug: str) -> str:
    for p in (radice / "content" / "posts").glob(f"*-{slug}.md"):
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})-", p.name)
        if m:
            return "".join(m.groups())
    return date.today().strftime("%Y%m%d")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("slug")
    ap.add_argument("--radice", default=str(Path(__file__).resolve().parents[2]), help="worktree che contiene la bozza")
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    ap.add_argument("--pr")
    ap.add_argument("--stato", choices=STATI)
    args = ap.parse_args(argv)

    radice = Path(args.radice).resolve()
    sys.path.insert(0, str(radice))
    os.chdir(radice)
    from run import app  # noqa: E402

    client = app.test_client()
    risposta = client.get(f"/blog/{args.slug}")
    if risposta.status_code != 200:
        print(f"/blog/{args.slug}: {risposta.status_code}. La bozza è in content/posts con draft: false?", file=sys.stderr)
        return 1

    def fetch(percorso: str):
        r = client.get(percorso)
        return r.get_data() if r.status_code == 200 else None

    oggi = date.today().isoformat()
    pagina = incorpora(risposta.get_data(as_text=True), fetch)
    pagina = metti_banner(pagina, banner(args.slug, args.pr, oggi))
    giorno = data_dal_file(radice, args.slug)
    nome = f"{giorno}-{args.slug}.html"
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / nome).write_text(pagina, encoding="utf-8")

    reg_path = out / "indice.json"
    registro = json.loads(reg_path.read_text(encoding="utf-8")) if reg_path.exists() else []
    voce = {
        "slug": args.slug, "titolo": titolo_pagina(risposta.get_data(as_text=True)),
        "data": f"{giorno[:4]}-{giorno[4:6]}-{giorno[6:]}", "file": nome,
        "stato": args.stato or "da leggere", "stato_esplicito": bool(args.stato),
        "pr": args.pr or next((v.get("pr") for v in registro if v["slug"] == args.slug), None),
    }
    registro = aggiorna_registro(registro, voce)
    reg_path.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "index.html").write_text(render_indice(registro), encoding="utf-8")
    print(f"{out / nome} ({len(pagina) // 1024} KB)\n{out / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
