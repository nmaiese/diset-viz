"""Verifica le citazioni letterali di un `fonti.md`: scarica ogni URL e cerca
la stringa normalizzata nel testo della pagina o del PDF.

Il contratto e' che una riga entra in `fonti.md` solo se la citazione e' stata
ritrovata aprendo l'URL. Il 28 settembre 2026 un modello gratuito ne aveva
date 1 su 18, e le altre erano parafrasi o frasi composte
(`docs/design_drafts/team/09_valutazione_pilota_ter12.md`): il difetto e' la
citazione inventata, non un esito che questo script possa riparare.

    bin/py -m scripts.trend_articles.verifica_citazioni lavoro/<slug>/fonti.md

Esce con 1 se almeno una citazione non e' ritrovata, 0 altrimenti. Le quattro
esito per riga:

- `TROVATA`: la citazione intera c'e' nel testo, normalizzata.
- `NON TROVATA`: non c'e'. La riga **esce dalla tabella**, e non viene
  sostituita con una parafrasi.
- `NON APERTO`: 403, 404, paywall, rete. Non e' un verdetto sulla citazione:
  si ritenta (o si cerca la copia stampata, per esempio il PDF).
- `NON VERIFICABILE`: il testo c'e' ma non si puo' leggere (un PDF senza
  `pypdf` importabile). Va detta nel `worker_done`, non data per buona.

Le chiamate HTTP sono di `urllib`, non di `requests`: il venv del progetto non
ha `requests` e questo script gira in un worktree, senza pip. `pypdf` serve solo
per i PDF ed e' facoltativo.
"""

from __future__ import annotations

import argparse
import html
import io
import logging
import re
import sys
import unicodedata
import urllib.error
import urllib.request

UA = {
    "User-Agent": "Mozilla/5.0 (X11 Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it",
}

NON_TROVATA = "NON TROVATA"
NON_APERTO = "NON APERTO"
NON_VERIFICABILE = "NON VERIFICABILE"
TROVATA = "TROVATA"

# Una riga non vuota e non "non trovato" non e' una citazione da verificare:
# il tavolo e' fatto per riportare che non si e' trovato niente.
VUOTO = {"", "-", "non trovato", "non trovata", "n/d", "non applicabile"}


def normalizza(testo: str) -> str:
    """Appiattisce quello che cambia fra la pagina e la riga che la cita.

    Le virgolette curve diventano dritte, la sillabazione a fine riga sparisce,
    ogni spazio (anche non breaking) diventa uno spazio e il confronto e' senza
    maiuscole: la ricerca e' sul testo, non sui caratteri.
    """
    testo = unicodedata.normalize("NFKC", testo)
    testo = testo.replace("’", "'").replace("‘", "'")
    testo = testo.replace("“", '"').replace("”", '"')
    testo = testo.replace("­", "").replace("-\n", "").replace("\xa0", " ")
    testo = re.sub(r"(?is)<(script|style).*?</\1>", " ", testo)
    testo = re.sub(r"<[^>]+>", " ", testo)
    testo = re.sub(r"\s+", " ", html.unescape(testo))
    return testo.strip().lower()


def frammenti(citazione: str, parole: int = 6, passo: int = 3) -> list[str]:
    """La citazione a pezzi sovrapposti, per capire *come* e' falsa.

    Una parafrasi non ha nessun frammento. Una citazione composta da due frasi
    di pagine diverse ne ha metà. La differenza serve a chi corregge, non solo
    allo script.
    """
    parole_citazione = normalizza(citazione).split()
    if len(parole_citazione) <= parole:
        return [" ".join(parole_citazione)]
    return [
        " ".join(parole_citazione[i:i + parole])
        for i in range(0, len(parole_citazione) - parole + 1, passo)
    ]


def valuta(testo: str, citazione: str) -> dict:
    """`TROVATA` se la citazione c'e' intera, altrimenti quanti frammenti ci sono."""
    testo_norm = normalizza(testo)
    citazione_norm = normalizza(citazione)
    if not citazione_norm:
        return {"esito": NON_VERIFICABILE, "frammenti": "", "motivo": "citazione vuota"}
    if citazione_norm in testo_norm:
        return {"esito": TROVATA, "frammenti": "", "motivo": ""}
    pezzi = frammenti(citazione_norm)
    trovati = sum(1 for p in pezzi if p in testo_norm)
    return {
        "esito": NON_TROVATA,
        "frammenti": f"{trovati}/{len(pezzi)}",
        "motivo": "",
    }


def celle(riga: str) -> list[str]:
    """Le celle di una riga di tabella markdown, senza le pipe di bordo."""
    riga = riga.strip()
    if riga.startswith("|"):
        riga = riga[1:]
    if riga.endswith("|"):
        riga = riga[:-1]
    return [c.strip() for c in riga.split("|")]


# Una nota di chi ha preso la citazione sta dentro la cella, dopo la virgoletta
# di chiusura: "(leader)", "(leader, da una pista di nemotron)". Non fa parte
# della citazione, e lasciarla dentro farebbe dichiarare false delle righe vere.
NOTA_CHI = re.compile(r"\s*\((leader|scout)(,[^)]*)?\)\s*$", re.IGNORECASE)


def _pulita(citazione: str) -> str:
    citazione = NOTA_CHI.sub("", citazione.strip())
    return citazione.strip().strip('"“”‘’"')


def righe_fonti(testo: str) -> list[dict]:
    """Le righe con un URL, nell'ordine del file.

    Il contratto delle colonne e' quello dello scout delle schede: istituzione,
    data, URL aperto, citazione letterale, limite d'uso. Non si pretende la
    stessa posizione delle colonne: l'URL e' la prima cella che comincia con
    `http` e la citazione e' quella subito dopo, come nel file del pilota.
    """
    righe = []
    for numero, riga in enumerate(testo.splitlines(), 1):
        if "|" not in riga or "http" not in riga:
            continue
        if set(riga.strip()) <= set("| -:"):
            continue
        celle_riga = celle(riga)
        indice = next(
            (i for i, c in enumerate(celle_riga) if c.startswith("http")), None
        )
        if indice is None:
            continue
        if len(celle_riga) > indice + 1:
            citazione = _pulita(celle_riga[indice + 1])
        else:
            citazione = ""
        righe.append({
            "numero": numero,
            "voce": celle_riga[0] if celle_riga else "",
            "istituzione": celle_riga[indice - 1] if indice > 0 else "",
            "url": celle_riga[indice],
            "citazione": citazione,
            "limite": celle_riga[indice + 2] if len(celle_riga) > indice + 2 else "",
        })
    return righe


def _pdf_text(contenuto: bytes) -> str | None:
    """Il testo di un PDF, se `pypdf` e' importabile. Altrimenti None."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    reader = PdfReader(io.BytesIO(contenuto))
    return " ".join((pagina.extract_text() or "") for pagina in reader.pages)


def scarica(url: str, timeout: int = 60) -> tuple[str | None, str]:
    """Il testo della pagina, o `(None, motivo)` se non si puo' avere.

    Un 403 o un paywall non e' una citazione falsa: torna `NON APERTO` e chi
    verifica prova un'altra strada.
    """
    richiesta = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
            grezzo = risposta.read()
            tipo = risposta.headers.get("Content-Type", "")
    except urllib.error.HTTPError as errore:
        return None, f"http {errore.code}"
    except Exception as errore:  # rete, DNS, timeout, certificato
        return None, f"{type(errore).__name__}: {errore}"[:120]
    if url.lower().split("?")[0].endswith(".pdf") or "application/pdf" in tipo:
        testo = _pdf_text(grezzo)
        return testo, ("pdf" if testo is not None else "pdf, serve pypdf")
    charset = "utf-8"
    if "charset=" in tipo:
        charset = re.split(r"[;,]", tipo.split("charset=")[-1])[0].strip() or "utf-8"
    try:
        return grezzo.decode(charset, errors="replace"), f"html {len(grezzo)} byte"
    except LookupError:
        return grezzo.decode("utf-8", errors="replace"), "html (charset ignota)"


def verifica(path, scarica_url=None) -> list[dict]:
    """Verifica ogni riga di un `fonti.md`. Un URL viene scaricato una volta.

    `scarica_url` si inietta perche' la rete non c'e' nei test: il default si
    risolve qui dentro, non nella firma, cosi' chi lo sostituisce vede
    cambiare quello che usa `main`.
    """
    scarica_url = scarica_url or scarica
    with open(path, encoding="utf-8") as file:
        righe = righe_fonti(file.read())
    cache: dict[str, tuple[str | None, str]] = {}
    for riga in righe:
        if not riga["citazione"] or riga["citazione"].lower() in VUOTO:
            riga["esito"] = NON_VERIFICABILE
            riga["motivo"] = "riga senza citazione"
            riga["info"] = ""
            continue
        if riga["url"] not in cache:
            try:
                cache[riga["url"]] = scarica_url(riga["url"])
            except Exception as errore:  # uno script iniettato puo' fallire
                cache[riga["url"]] = (None, f"{type(errore).__name__}: {errore}"[:120])
        testo, info = cache[riga["url"]]
        riga["info"] = info
        if testo is None:
            riga["esito"] = NON_VERIFICABILE if "pypdf" in info else NON_APERTO
            riga["motivo"] = info
            riga["frammenti"] = ""
            continue
        giudizio = valuta(testo, riga["citazione"])
        riga["esito"] = giudizio["esito"]
        riga["frammenti"] = giudizio["frammenti"]
        riga["motivo"] = giudizio["motivo"]
    return righe


def _riga_console(riga: dict) -> str:
    esito = riga["esito"]
    if riga.get("frammenti"):
        esito = f"{esito} ({riga['frammenti']} frammenti)"
    motivo = riga.get("motivo") or ""
    if motivo and motivo != riga.get("info"):
        esito = f"{esito}, {motivo}"
    return (
        f"{esito:40} {riga['url']}\n"
        f"{'':40} riga {riga['numero']}, {riga['voce']}: {riga['citazione'][:100]}"
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("fonti", help="il file fonti.md del pezzo")
    args = parser.parse_args(argv)

    righe = verifica(args.fonti)
    if not righe:
        print(f"{args.fonti}: nessuna riga con un URL. Il tavolo delle fonti e' vuoto.")
        return 0
    for riga in righe:
        print(_riga_console(riga))
    conto: dict[str, int] = {}
    for riga in righe:
        conto[riga["esito"]] = conto.get(riga["esito"], 0) + 1
    non_trovate = [r for r in righe if r["esito"] == NON_TROVATA]
    print()
    print("righe: " + ", ".join(f"{k} {v}" for k, v in sorted(conto.items())))
    if non_trovate:
        print(f"\nDa togliere dalla tabella, righe {', '.join(str(r['numero']) for r in non_trovate)}:")
        for riga in non_trovate:
            print(f"  {riga['numero']}: {riga['voce']} | {riga['citazione'][:100]}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
