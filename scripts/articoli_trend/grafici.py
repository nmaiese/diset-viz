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


def _sotto(nome: str, periodo: str, unita: str, extra: str = "") -> str:
    """Il sottotitolo sta su una riga: nome corto, periodo, unita' (se non e' gia' nel nome)."""
    nome = nome.replace(", Italia e ripartizioni", "")
    unita = "" if unita.lower() in nome.lower() else f" {unita[:1].upper()}{unita[1:]}."
    testo = f"{nome}, {periodo}.{extra}{unita}"
    if len(testo) > 105:
        import re
        testo = f"{re.sub(r'\s*\([^)]*\)', '', nome)}, {periodo}.{extra}{unita}"
    return testo


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


def _riferimento(slug, ind, anno, dec, riferimento):
    """La linea di riferimento: il valore Italia ufficiale se c'e', se no la media semplice dichiarata."""
    if riferimento:
        _, rif = _dossier(slug, riferimento)
        v = rif["serie"].get("Italia", {}).get(str(anno))
        if v is not None:
            return (f"Italia {comuni.fmt(v, dec)}", v)
    media = ind["medie"][str(anno)]["media_semplice"]
    return (f"media semplice {comuni.fmt(media, dec + 1)}", media)


def barre(slug, chiave, evidenzia, titolo, anno=None, riferimento=None):
    dossier, ind = _dossier(slug, chiave)
    meta = ind["meta"]
    anno = anno or ind["ultimo_anno"]
    dec = meta["decimali"]
    righe = sorted(((t, per[str(anno)]) for t, per in ind["serie"].items() if str(anno) in per), key=lambda kv: -kv[1])
    if righe and righe[0][1] >= 100:
        dec = 0  # sopra 100 i decimali sono rumore, come nel dossier
    dati = [(t, v, comuni.fmt(v, dec)) for t, v in righe]
    sotto = _sotto(meta["nome"], str(anno), meta["unita"])
    descr = f"Classifica di {len(dati)} territori nel {anno}: primo {dati[0][0]} con {dati[0][2]}, ultimo {dati[-1][0]} con {dati[-1][2]}."
    return _barre(dati, set(evidenzia), _riferimento(slug, ind, anno, dec, riferimento), titolo, sotto, meta, descr)


def estremi(slug, chiave, quanti, evidenzia, titolo, anno=None, riferimento=None):
    dossier, ind = _dossier(slug, chiave)
    meta = ind["meta"]
    anno = anno or ind["ultimo_anno"]
    dec = meta["decimali"]
    righe = sorted(((t, per[str(anno)]) for t, per in ind["serie"].items() if str(anno) in per), key=lambda kv: -kv[1])
    scelte = righe[:quanti] + righe[-quanti:]
    dati = [(t, v, comuni.fmt(v, dec)) for t, v in scelte]
    sotto = _sotto(meta["nome"], str(anno), meta["unita"], f" Le {quanti} province più alte e le {quanti} più basse su {len(righe)}.")
    descr = f"Le {quanti} province con il valore più alto e le {quanti} con il più basso nel {anno}: prima {dati[0][0]} con {dati[0][2]}, ultima {dati[-1][0]} con {dati[-1][2]}."
    return _barre(dati, set(evidenzia), _riferimento(slug, ind, anno, dec, riferimento), titolo, sotto, meta, descr, {quanti})


CLASSI_AREE = {"Nord": "nord", "Centro": "centro", "Mezzogiorno": "mz", "Italia": "it"}


def linee(slug, chiave, territori, titolo, ripartizioni=True, con=None):
    """Serie nel tempo.

    Se `chiave` e' un'elaborazione di ripartizioni ufficiali (ext:bes_ripartizioni_*),
    le linee sono Nord, Centro, Mezzogiorno e Italia come le calcola l'Istat, e
    `territori` si prendono da `con` (l'indicatore regionale). Altrimenti si
    disegnano le medie semplici di Centro-Nord e Mezzogiorno, dichiarate tali.
    """
    dossier, ind = _dossier(slug, chiave)
    meta = ind["meta"]
    dec = meta["decimali"]
    ufficiali = meta["livello"] == "ripartizione"
    serie: list[tuple[str, str, dict[int, float]]] = []
    if ufficiali:
        for area, classe in CLASSI_AREE.items():
            if area in ind["serie"]:
                serie.append((area, classe, {int(a): v for a, v in ind["serie"][area].items()}))
        fonte_territori = _dossier(slug, con)[1] if con else ind
    else:
        if ripartizioni:
            serie.append(("Centro-Nord", "cn", {int(a): m["media_centro_nord"] for a, m in ind["medie"].items() if "media_centro_nord" in m}))
            serie.append(("Mezzogiorno", "mz", {int(a): m["media_mezzogiorno"] for a, m in ind["medie"].items() if "media_mezzogiorno" in m}))
        fonte_territori = ind
    for t in territori:
        serie.append((t, "on", {int(a): v for a, v in fonte_territori["serie"][t].items()}))
    anni = sorted({a for _, _, s in serie for a in s})
    ripartizioni = ripartizioni and not ufficiali

    alto, basso, sinistra, destra = 60, 70, 48, 150
    altezza = 360
    tutti = [v for _, _, s in serie for v in s.values()]
    lo, hi = min(tutti), max(tutti)
    margine = (hi - lo) * 0.08 or 1
    lo, hi = max(0, lo - margine), hi + margine
    x = lambda a: sinistra + (a - anni[0]) / max(1, anni[-1] - anni[0]) * (LARGHEZZA - sinistra - destra)
    y = lambda v: altezza - basso - (v - lo) / (hi - lo) * (altezza - alto - basso)

    sotto = _sotto(meta["nome"], f"{anni[0]}-{anni[-1]}", meta["unita"])
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
        cifre = dec + 1 if classe in ("cn", "mz") and not ufficiali else dec
        etichette.append([y(s[ultimo]), f"{nome} {comuni.fmt(s[ultimo], cifre)}", classe, x(ultimo)])
    etichette.sort()
    for i in range(1, len(etichette)):  # le etichette non si sovrappongono
        etichette[i][0] = max(etichette[i][0], etichette[i - 1][0] + 14)
    for yy, testo, classe, xx in etichette:
        parti.append(f'<text class="fig__etichetta fig__etichetta--{classe}" x="{xx + 8:.1f}" y="{yy + 4:.1f}">{escape(testo)}</text>')
    if ripartizioni:
        parti.append(f'<text class="fig__nota" x="0" y="{altezza - 26}">Centro-Nord e Mezzogiorno: medie semplici dei territori, non pesate per popolazione.</text>')
    elif ufficiali:
        parti.append(f'<text class="fig__nota" x="0" y="{altezza - 26}">Italia, Nord, Centro e Mezzogiorno: valori calcolati dall\'Istat.</text>')
    parti.append(_piede(meta, altezza - 6))
    parti.append("</svg>")
    return "\n".join(parti)


def dispersione(slug, chiave_x, chiave_y, anni_x, anni_y, evidenzia, titolo, nome_x, nome_y, sottotitolo=None):
    """Una regione per punto: la variazione di un indicatore contro quella di un altro.

    Serve a mettere alla prova un'ipotesi ("dove e' cresciuto X e' peggiorato
    Y?"), non a dimostrarla: i punti sono regioni, non persone. Le regioni del
    Mezzogiorno e del Centro-Nord hanno due forme diverse, cosi' si vede se la
    relazione vale per tutte o per un gruppo solo.
    """
    _, ix = _dossier(slug, chiave_x)
    _, iy = _dossier(slug, chiave_y)
    punti = []
    # Due anni: la variazione fra i due. Un anno solo: il livello.
    valore = lambda s, anni: s[str(anni[1])] - s[str(anni[0])] if len(anni) == 2 else s[str(anni[0])]  # noqa: E731
    for t in sorted(set(ix["serie"]) & set(iy["serie"])):
        sx, sy = ix["serie"][t], iy["serie"][t]
        if all(str(a) in sx for a in anni_x) and all(str(a) in sy for a in anni_y):
            punti.append((t, valore(sx, anni_x), valore(sy, anni_y)))
    alto, basso, sinistra, destra = 60, 86, 56, 24
    altezza = 440
    xs, ys = [p[1] for p in punti], [p[2] for p in punti]
    variazioni = len(anni_x) == 2
    # Il legame si misura anche dentro ciascun gruppo: un legame che esiste solo
    # fra Nord e Sud puo' dipendere da qualunque cosa distingua le due aree.
    import statistics
    province = comuni.regione_di_provincia()
    gruppo = {t: comuni.ripartizione(t, "provincia" if t in province else "regione") for t, _, _ in punti}
    legami = {}
    for nome, sel in (("tutti", punti), ("Centro-Nord", [p for p in punti if gruppo[p[0]] == "Centro-Nord"]),
                      ("Mezzogiorno", [p for p in punti if gruppo[p[0]] == "Mezzogiorno"])):
        if len(sel) >= 4:
            legami[nome] = {"punti": len(sel), "correlazione": round(statistics.correlation([p[1] for p in sel], [p[2] for p in sel]), 2)}
    comuni.scrivi_json(comuni.ARTICOLI / slug / f"legame_{chiave_x.split(':')[1]}_{chiave_y.split(':')[1]}.json", {
        "x": chiave_x, "y": chiave_y, "anni_x": anni_x, "anni_y": anni_y, "legami": legami,
        "nota": "Correlazione di Pearson fra territori. Misura se due grandezze si muovono insieme, non una causa.",
    })
    print("legami:", legami)
    # Con le variazioni lo zero deve stare nel disegno: separa chi e' salito da chi e' sceso.
    x0, x1 = (min(xs + [0]) if variazioni else min(xs)), max(xs)
    y0, y1 = (min(ys + [0]) if len(anni_y) == 2 else min(ys)), max(ys)
    mx, my = (x1 - x0) * 0.08, (y1 - y0) * 0.08
    x0, x1, y0, y1 = x0 - mx, x1 + mx, y0 - my, y1 + my
    X = lambda v: sinistra + (v - x0) / (x1 - x0) * (LARGHEZZA - sinistra - destra)  # noqa: E731
    Y = lambda v: altezza - basso - (v - y0) / (y1 - y0) * (altezza - alto - basso)  # noqa: E731
    sotto = sottotitolo or ((f"Variazione {anni_x[0]}-{anni_x[1]}, in punti percentuali." if anni_x == anni_y else f"Variazione {anni_x[0]}-{anni_x[1]} e {anni_y[0]}-{anni_y[1]}, in punti percentuali.")
                            if variazioni else "Una regione per punto.")
    descr = "; ".join(f"{t}: {comuni.fmt(dx, 1)} e {comuni.fmt(dy, 1)}" for t, dx, dy in punti)
    parti = _testa(titolo, sotto, altezza, descr)
    if x0 < 0 < x1:
        parti.append(f'<line class="fig__griglia" x1="{X(0):.1f}" y1="{alto}" x2="{X(0):.1f}" y2="{altezza - basso}"/>')
    if y0 < 0 < y1:
        parti.append(f'<line class="fig__griglia" x1="{sinistra}" y1="{Y(0):.1f}" x2="{LARGHEZZA - destra}" y2="{Y(0):.1f}"/>')
    for k in range(5):
        v = x0 + (x1 - x0) * k / 4
        parti.append(f'<text class="fig__asse" x="{X(v):.1f}" y="{altezza - basso + 16}" text-anchor="middle">{escape(comuni.fmt(v, 1))}</text>')
        w = y0 + (y1 - y0) * k / 4
        parti.append(f'<text class="fig__asse" x="{sinistra - 6}" y="{Y(w) + 4:.1f}" text-anchor="end">{escape(comuni.fmt(w, 1))}</text>')
    parti.append(f'<text class="fig__asse-nome" x="{LARGHEZZA - destra}" y="{altezza - basso + 34}" text-anchor="end">{escape(nome_x)} →</text>')
    parti.append(f'<text class="fig__asse-nome" x="{sinistra}" y="{alto - 8}">↑ {escape(nome_y)}</text>')
    province = comuni.regione_di_provincia()
    tutti_i_nomi = len(punti) <= 25  # con 100 province si nominano solo quelle di cui il testo parla
    etichette = []
    for t, dx, dy in punti:
        on = " is-on" if t in evidenzia else ""
        sud = comuni.ripartizione(t, "provincia" if t in province else "regione") == "Mezzogiorno"
        forma = (f'<rect class="fig__pt fig__pt--mz{on}" x="{X(dx) - 4:.1f}" y="{Y(dy) - 4:.1f}" width="8" height="8"/>'
                 if sud else
                 f'<circle class="fig__pt fig__pt--cn{on}" cx="{X(dx):.1f}" cy="{Y(dy):.1f}" r="4.5"/>')
        parti.append(forma)
        if tutti_i_nomi or on:
            destra_ok = X(dx) < LARGHEZZA - 140
            larghezza = 6.2 * len(t)
            x_testo = X(dx) + (7 if destra_ok else -7)
            sinistra_testo = x_testo if destra_ok else x_testo - larghezza
            etichette.append([Y(dy) + 4, sinistra_testo, larghezza, x_testo, destra_ok, on, t])
    # Le etichette che si toccano scivolano in basso di una riga, una dopo l'altra.
    etichette.sort()
    posate: list[list] = []
    for e in etichette:
        while any(abs(e[0] - p[0]) < 12 and e[1] < p[1] + p[2] and p[1] < e[1] + e[2] for p in posate):
            e[0] += 12
        posate.append(e)
        yy, _, _, x_testo, destra_ok, on, t = e
        parti.append(f'<text class="fig__pt-nome{on}" x="{x_testo:.1f}" y="{yy:.1f}"'
                     f'{"" if destra_ok else " text-anchor=\"end\""}>{escape(t)}</text>')
    unita = "Una provincia" if not tutti_i_nomi else "Una regione"
    parti.append(f'<text class="fig__nota" x="0" y="{altezza - 26}">{unita} per punto. Cerchi: Centro-Nord. Quadrati: Mezzogiorno.</text>')
    istituzioni = []
    for m in (ix["meta"], iy["meta"]):
        nome = m["fonte"].split(" -")[0].split(",")[0].strip()
        if nome not in istituzioni:
            istituzioni.append(nome)
    fonti = f"Fonte: {' e '.join(istituzioni)}. Elaborazione Divario Italia."
    parti.append(f'<text class="fig__fonte" x="0" y="{altezza - 6}">{escape(fonti)}</text>')
    parti.append("</svg>")
    return "\n".join(parti)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("slug")
    parser.add_argument("tipo", choices=["barre", "estremi", "linee", "dispersione"])
    parser.add_argument("indicatore")
    parser.add_argument("--con", help="linee: indicatore regionale per --territori; dispersione: indicatore sull'asse y")
    parser.add_argument("--anni-x", help="dispersione: due anni, es. 2018,2025")
    parser.add_argument("--anni-y", help="dispersione: due anni, es. 2018,2025")
    parser.add_argument("--nome-x", default="")
    parser.add_argument("--nome-y", default="")
    parser.add_argument("--sottotitolo")
    parser.add_argument("--riferimento", help="barre/estremi: ext:bes_ripartizioni_* da cui prendere il valore Italia")
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
        svg = barre(args.slug, args.indicatore, lista(args.evidenzia), args.titolo, args.anno, args.riferimento)
    elif args.tipo == "estremi":
        svg = estremi(args.slug, args.indicatore, args.quanti, lista(args.evidenzia), args.titolo, args.anno, args.riferimento)
    elif args.tipo == "dispersione":
        ax = [int(a) for a in lista(args.anni_x)]
        ay = [int(a) for a in lista(args.anni_y)]
        svg = dispersione(args.slug, args.indicatore, args.con, ax, ay, set(lista(args.evidenzia)), args.titolo,
                          args.nome_x, args.nome_y, args.sottotitolo)
    else:
        svg = linee(args.slug, args.indicatore, lista(args.territori), args.titolo, not args.senza_ripartizioni, args.con)

    uscita = comuni.FIGURE / args.slug / f"{args.nome}.svg"
    uscita.parent.mkdir(parents=True, exist_ok=True)
    uscita.write_text(svg.replace("@ID@", f"fig-{args.nome}") + "\n", encoding="utf-8")
    print(f"-> {uscita.relative_to(comuni.RADICE)}   marcatore: <!-- figura: {args.nome} -->")
    return 0


if __name__ == "__main__":
    sys.exit(main())
