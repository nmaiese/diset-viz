"""Fase 5: le figure del pezzo, disegnate dai numeri del dossier.

Ogni figura e' un SVG in `content/figure/<slug>/<nome>.svg` che l'articolo
richiama su una riga sua:

    <!-- figura: classifica-2024 -->

e che `app/blog.py` inserisce nella pagina al render, dentro un `<figure>`.
L'SVG e' in linea, non un `<img>`, per tre ragioni: i colori sono classi CSS
che leggono i token del design system (quindi la figura segue il tema scuro,
e nessun colore e' cotto nel file), i nomi e i valori sono testo che un
motore legge, e lo screen reader trova `<title>` e `<desc>`.

Regole di disegno, le stesse del sito:
- le barre sono neutre (`--cmp-2`), l'accento corallo va solo ai territori
  di cui il testo parla;
- nelle linee Centro-Nord e Mezzogiorno si distinguono per colore **e** per
  tratto (continuo e tratteggiato) e sono etichettate in fondo alla linea:
  la figura si legge anche senza distinguere i colori;
- titolo, unita', anno e fonte stanno dentro la figura: una figura copiata
  altrove si porta dietro da dove viene;
- niente giudizio nel colore: il corallo evidenzia, non dice "male".

    bin/py -m scripts.articoli_trend.grafici <slug> barre bes:03LAV007 \\
        --evidenzia Umbria,Lombardia --titolo "..." --nome classifica-2022
    bin/py -m scripts.articoli_trend.grafici <slug> estremi prov:03LAV007 --quanti 10 ...
    bin/py -m scripts.articoli_trend.grafici <slug> linee bes:03LAV007 --territori Umbria ...
"""

from __future__ import annotations

import argparse
import sys
from html import escape

from scripts.articoli_trend import comuni

LARGHEZZA = 680


def _dossier(slug: str, chiave: str) -> tuple[dict, dict]:
    dossier = comuni.leggi_json(comuni.ARTICOLI / slug / "dossier.json")
    for ind in dossier["indicatori"]:
        if ind["meta"]["chiave"] == chiave:
            return dossier, ind
    raise SystemExit(f"{chiave} non e' nel dossier di {slug}: rifai il dossier con quell'indicatore")


def _fonte(meta: dict) -> str:
    """Una riga che entra nella figura: istituzione e archivio, senza il dettaglio.

    La provenienza completa (rilevazione, dataflow, file) sta nel dossier, nel
    CSV scaricabile e nella sezione "Dati usati" del pezzo.
    """
    istituzione = meta["fonte"].split(" -")[0].split(",")[0].strip()
    archivio = meta["archivio"].split(",")[0].replace(" (Bes at local level)", "").strip()
    if archivio.startswith("Benessere equo"):
        archivio = "Benessere equo e sostenibile"
    return f"Fonte: {istituzione}, {archivio}. Elaborazione Divario Italia."


def _testa(titolo: str, sottotitolo: str, altezza: int, descrizione: str) -> list[str]:
    return [
        # @ID@ diventa il nome della figura: due figure nella stessa pagina
        # non devono condividere gli id a cui punta aria-labelledby.
        f'<svg class="fig" viewBox="0 0 {LARGHEZZA} {altezza}" role="img" aria-labelledby="@ID@-t @ID@-d" xmlns="http://www.w3.org/2000/svg">',
        f'<title id="@ID@-t">{escape(titolo)}</title>',
        f'<desc id="@ID@-d">{escape(descrizione)}</desc>',
        f'<text class="fig__titolo" x="0" y="20">{escape(titolo)}</text>',
        f'<text class="fig__sotto" x="0" y="40">{escape(sottotitolo)}</text>',
    ]


def _piede(meta: dict, y: int) -> str:
    return f'<text class="fig__fonte" x="0" y="{y}">{escape(_fonte(meta))}</text>'


def _barre(righe: list[tuple[str, float, str]], evidenzia: set[str], riferimento: tuple[str, float] | None,
           titolo: str, sottotitolo: str, meta: dict, descrizione: str, stacchi: set[int] = frozenset()) -> str:
    passo, alto, sinistra, destra = 22, 60, 190, 60
    altezza = alto + passo * len(righe) + 22 * len(stacchi) + 50
    massimo = max(v for _, v, _ in righe) or 1
    scala = (LARGHEZZA - sinistra - destra) / massimo
    parti = _testa(titolo, sottotitolo, altezza, descrizione)
    y = alto
    for i, (nome, valore, testo) in enumerate(righe):
        if i in stacchi:
            parti.append(f'<text class="fig__stacco" x="{sinistra}" y="{y + 14}">· · ·</text>')
            y += 22
        on = " is-on" if nome in evidenzia else ""
        w = max(1.0, valore * scala)
        parti.append(f'<text class="fig__nome{on}" x="{sinistra - 8}" y="{y + 14}" text-anchor="end">{escape(nome)}</text>')
        parti.append(f'<rect class="fig__barra{on}" x="{sinistra}" y="{y + 3}" width="{w:.1f}" height="{passo - 7}"/>')
        parti.append(f'<text class="fig__valore{on}" x="{sinistra + w + 6:.1f}" y="{y + 14}">{escape(testo)}</text>')
        y += passo
    if riferimento:
        etichetta, valore = riferimento
        x = sinistra + valore * scala
        parti.append(f'<line class="fig__rif" x1="{x:.1f}" y1="{alto - 4}" x2="{x:.1f}" y2="{y}"/>')
        parti.append(f'<text class="fig__rif-testo" x="{x + 4:.1f}" y="{y + 14}">{escape(etichetta)}</text>')
    parti.append(_piede(meta, altezza - 6))
    parti.append("</svg>")
    return "\n".join(parti)


def barre(slug, chiave, evidenzia, titolo, anno=None):
    dossier, ind = _dossier(slug, chiave)
    meta = ind["meta"]
    anno = anno or ind["ultimo_anno"]
    dec = meta["decimali"]
    righe = sorted(((t, per[str(anno)]) for t, per in ind["serie"].items() if str(anno) in per), key=lambda kv: -kv[1])
    media = ind["medie"][str(anno)]["media_semplice"]
    dati = [(t, v, comuni.fmt(v, dec)) for t, v in righe]
    sotto = f"{meta['nome']}, {anno}. {meta['unita']}."
    descr = f"Classifica di {len(dati)} territori nel {anno}: primo {dati[0][0]} con {dati[0][2]}, ultimo {dati[-1][0]} con {dati[-1][2]}."
    return _barre(dati, set(evidenzia), (f"media semplice {comuni.fmt(media, dec + 1)}", media), titolo, sotto, meta, descr)


def estremi(slug, chiave, quanti, evidenzia, titolo, anno=None):
    dossier, ind = _dossier(slug, chiave)
    meta = ind["meta"]
    anno = anno or ind["ultimo_anno"]
    dec = meta["decimali"]
    righe = sorted(((t, per[str(anno)]) for t, per in ind["serie"].items() if str(anno) in per), key=lambda kv: -kv[1])
    scelte = righe[:quanti] + righe[-quanti:]
    dati = [(t, v, comuni.fmt(v, dec)) for t, v in scelte]
    media = ind["medie"][str(anno)]["media_semplice"]
    sotto = f"{meta['nome']}, {anno}. Le {quanti} province piu' alte e le {quanti} piu' basse su {len(righe)}. {meta['unita']}."
    descr = f"Le {quanti} province con il valore piu' alto e le {quanti} con il piu' basso nel {anno}: prima {dati[0][0]} con {dati[0][2]}, ultima {dati[-1][0]} con {dati[-1][2]}."
    return _barre(dati, set(evidenzia), (f"media semplice {comuni.fmt(media, dec + 1)}", media), titolo, sotto, meta, descr, {quanti})


def linee(slug, chiave, territori, titolo, ripartizioni=True):
    dossier, ind = _dossier(slug, chiave)
    meta = ind["meta"]
    dec = meta["decimali"]
    anni = sorted(int(a) for a in ind["medie"])
    serie: list[tuple[str, str, dict[int, float]]] = []
    if ripartizioni:
        serie.append(("Centro-Nord", "cn", {int(a): m["media_centro_nord"] for a, m in ind["medie"].items() if "media_centro_nord" in m}))
        serie.append(("Mezzogiorno", "mz", {int(a): m["media_mezzogiorno"] for a, m in ind["medie"].items() if "media_mezzogiorno" in m}))
    for t in territori:
        serie.append((t, "on", {int(a): v for a, v in ind["serie"][t].items()}))

    alto, basso, sinistra, destra = 60, 70, 48, 150
    altezza = 360
    tutti = [v for _, _, s in serie for v in s.values()]
    lo, hi = min(tutti), max(tutti)
    margine = (hi - lo) * 0.08 or 1
    lo, hi = max(0, lo - margine), hi + margine
    x = lambda a: sinistra + (a - anni[0]) / max(1, anni[-1] - anni[0]) * (LARGHEZZA - sinistra - destra)
    y = lambda v: altezza - basso - (v - lo) / (hi - lo) * (altezza - alto - basso)

    sotto = f"{meta['nome']}, {anni[0]}-{anni[-1]}. {meta['unita']}."
    descr = "; ".join(
        f"{nome}: da {comuni.fmt(s[min(s)], dec)} nel {min(s)} a {comuni.fmt(s[max(s)], dec)} nel {max(s)}"
        for nome, _, s in serie if s
    )
    parti = _testa(titolo, sotto, altezza, descr)
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        parti.append(f'<line class="fig__griglia" x1="{sinistra}" y1="{y(v):.1f}" x2="{LARGHEZZA - destra}" y2="{y(v):.1f}"/>')
        parti.append(f'<text class="fig__asse" x="{sinistra - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{escape(comuni.fmt(v, dec if hi - lo < 10 else 0))}</text>')
    for a in anni:
        if len(anni) <= 12 or a % 2 == anni[-1] % 2:
            parti.append(f'<text class="fig__asse" x="{x(a):.1f}" y="{altezza - basso + 18}" text-anchor="middle">{a}</text>')
    etichette = []
    for nome, classe, s in serie:
        punti = " ".join(f"{x(a):.1f},{y(v):.1f}" for a, v in sorted(s.items()))
        parti.append(f'<polyline class="fig__linea fig__linea--{classe}" points="{punti}"/>')
        ultimo = max(s)
        parti.append(f'<circle class="fig__punto fig__punto--{classe}" cx="{x(ultimo):.1f}" cy="{y(s[ultimo]):.1f}" r="3.5"/>')
        # le medie portano un decimale in piu' dei dati, come nel dossier
        cifre = dec + 1 if classe in ("cn", "mz") else dec
        etichette.append([y(s[ultimo]), f"{nome} {comuni.fmt(s[ultimo], cifre)}", classe, x(ultimo)])
    etichette.sort()
    for i in range(1, len(etichette)):  # le etichette non si sovrappongono
        etichette[i][0] = max(etichette[i][0], etichette[i - 1][0] + 14)
    for yy, testo, classe, xx in etichette:
        parti.append(f'<text class="fig__etichetta fig__etichetta--{classe}" x="{xx + 8:.1f}" y="{yy + 4:.1f}">{escape(testo)}</text>')
    if ripartizioni:
        parti.append(f'<text class="fig__nota" x="0" y="{altezza - 26}">Centro-Nord e Mezzogiorno: medie semplici dei territori, non pesate per popolazione.</text>')
    parti.append(_piede(meta, altezza - 6))
    parti.append("</svg>")
    return "\n".join(parti)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("slug")
    parser.add_argument("tipo", choices=["barre", "estremi", "linee"])
    parser.add_argument("indicatore")
    parser.add_argument("--titolo", required=True, help="il titolo dice la notizia, non il nome dell'indicatore")
    parser.add_argument("--nome", required=True, help="nome del file, e del marcatore nell'articolo")
    parser.add_argument("--evidenzia", default="")
    parser.add_argument("--territori", default="")
    parser.add_argument("--quanti", type=int, default=10)
    parser.add_argument("--anno", type=int)
    parser.add_argument("--senza-ripartizioni", action="store_true")
    args = parser.parse_args(argv)

    lista = lambda s: [p.strip() for p in s.split(",") if p.strip()]
    if args.tipo == "barre":
        svg = barre(args.slug, args.indicatore, lista(args.evidenzia), args.titolo, args.anno)
    elif args.tipo == "estremi":
        svg = estremi(args.slug, args.indicatore, args.quanti, lista(args.evidenzia), args.titolo, args.anno)
    else:
        svg = linee(args.slug, args.indicatore, lista(args.territori), args.titolo, not args.senza_ripartizioni)

    uscita = comuni.FIGURE / args.slug / f"{args.nome}.svg"
    uscita.parent.mkdir(parents=True, exist_ok=True)
    uscita.write_text(svg.replace("@ID@", f"fig-{args.nome}") + "\n", encoding="utf-8")
    print(f"-> {uscita.relative_to(comuni.RADICE)}   marcatore: <!-- figura: {args.nome} -->")
    return 0


if __name__ == "__main__":
    sys.exit(main())
