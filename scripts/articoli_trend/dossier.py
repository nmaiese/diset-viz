"""Fase 4: i numeri di un pezzo, tutti, con la loro provenienza.

Il dossier e' l'unico posto da cui chi scrive prende una cifra. Contiene:

- per ogni indicatore del pezzo: fonte, archivio, unita', anni, la pagina
  canonica sul sito (risolta dall'app, non indovinata);
- l'ultimo anno per tutti i territori, in ordine;
- la **media semplice dei territori** (non e' la media nazionale e non va mai
  chiamata cosi': la media nazionale pesa la popolazione e sta nelle
  pubblicazioni Istat), e le medie di Centro-Nord e Mezzogiorno;
- la serie completa per territorio e le variazioni fra primo e ultimo anno;
- `cifre`: l'elenco delle cifre ammesse nel testo, ognuna gia' scritta come
  comparira' (virgola decimale, precisione della fonte) e con da dove viene.
  `verifica.py` rifiuta un numero del pezzo che non stia qui o nel frontmatter.

Scrive anche il CSV scaricabile del pezzo in `app/static/data/articoli/`,
quello che lo schema `Dataset` dell'articolo dichiara come `distribution`.

    bin/py -m scripts.articoli_trend.dossier <slug> bes:03LAV007 prov:03LAV007
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys

from scripts.articoli_trend import comuni


def pagina_indicatore(meta: dict) -> str | None:
    """Il percorso canonico della scheda, chiesto all'app: segue il 301."""
    from app import app

    sigla = {"ter": "ter", "bes": "bes", "ims": "ims", "prov": "bes"}[meta["famiglia"]]
    codice = meta["codice"]
    client = app.test_client()
    percorso = f"/indicatore/{sigla}-{codice}"
    for _ in range(3):
        risposta = client.get(percorso)
        if risposta.status_code in (301, 302, 308):
            percorso = risposta.headers["Location"].replace("http://localhost", "")
            continue
        return percorso if risposta.status_code == 200 else None
    return None


def analizza(chiave: str) -> dict:
    s = comuni.serie(chiave)
    meta, valori = s["meta"], s["valori"]
    livello = meta["livello"]
    tutti = [v for per in valori.values() for v in per.values()]
    dec = comuni.decimali_di(tutti)
    ultimo = meta["anni"][1]
    primo = meta["anni"][0]

    ora = sorted(((t, per[ultimo]) for t, per in valori.items() if ultimo in per), key=lambda kv: -kv[1])
    cifre: list[dict] = []

    def cifra(valore: float, cosa: str, decimali: int = dec) -> str:
        testo = comuni.fmt(valore, decimali)
        cifre.append({"cifra": testo, "cosa": cosa, "indicatore": chiave})
        return testo

    classifica = []
    for posto, (t, v) in enumerate(ora, 1):
        classifica.append({"posto": posto, "territorio": t, "valore": v,
                           "testo": cifra(v, f"{t}, {ultimo}"),
                           "ripartizione": comuni.ripartizione(t, livello)})

    medie = {}
    for anno in sorted({a for per in valori.values() for a in per}):
        riga = [per[anno] for per in valori.values() if anno in per]
        if len(riga) < 3:
            continue
        gruppi: dict[str, list[float]] = {}
        for t, per in valori.items():
            if anno in per:
                gruppi.setdefault(comuni.ripartizione(t, livello), []).append(per[anno])
        medie[anno] = {
            "territori": len(riga),
            "media_semplice": round(statistics.fmean(riga), 4),
            **{f"media_{k.lower().replace('-', '_')}": round(statistics.fmean(g), 4) for k, g in gruppi.items()},
        }
    # Una media di valori a un decimale si puo' scrivere con un decimale in piu':
    # 0,825 e 0,592 dicono una distanza che 0,8 e 0,6 appiattiscono. Sono
    # ammesse tutte e due le scritture, e il testo sceglie.
    for anno, m in medie.items():
        for k, v in m.items():
            if k.startswith("media"):
                cosa = f"{k.replace('_', ' ')} dei territori, {anno} (media semplice, non pesata)"
                cifra(v, cosa)
                cifra(v, cosa, dec + 1)

    variazioni = []
    for t, per in valori.items():
        anni = sorted(per)
        if len(anni) >= 2:
            delta = per[anni[-1]] - per[anni[0]]
            variazioni.append({"territorio": t, "da": anni[0], "a": anni[-1], "delta": round(delta, 4),
                               "testo": cifra(abs(delta), f"variazione {t} {anni[0]}-{anni[-1]} (in valore assoluto)")})
    variazioni.sort(key=lambda r: r["delta"])

    if ora and ora[-1][1]:
        rapporto = ora[0][1] / ora[-1][1]
        cifra(rapporto, f"rapporto fra primo ({ora[0][0]}) e ultimo ({ora[-1][0]}) nel {ultimo}")

    for t, per in valori.items():
        for anno, v in per.items():
            if anno != ultimo:
                cifra(v, f"{t}, {anno}")

    return {
        "meta": {**meta, **comuni.definizione(chiave), "pagina": pagina_indicatore(meta), "decimali": dec},
        "ultimo_anno": ultimo, "primo_anno": primo,
        "classifica": classifica, "medie": medie, "variazioni": variazioni,
        "serie": {t: {str(a): v for a, v in sorted(per.items())} for t, per in valori.items()},
        "cifre": cifre,
    }


def scrivi_csv(slug: str, analisi: list[dict]) -> str:
    comuni.DOWNLOAD.mkdir(parents=True, exist_ok=True)
    percorso = comuni.DOWNLOAD / f"{slug}.csv"
    with percorso.open("w", encoding="utf-8", newline="") as file:
        w = csv.writer(file, lineterminator="\n")
        w.writerow(["indicatore", "codice", "livello", "territorio", "anno", "valore", "unita", "fonte", "archivio"])
        for a in analisi:
            m = a["meta"]
            for t, per in sorted(a["serie"].items()):
                for anno, v in per.items():
                    w.writerow([m["nome"], m["codice"], m["livello"], t, anno, v, m["unita"], m["fonte"], m["archivio"]])
    return "/" + str(percorso.relative_to(comuni.RADICE / "app")).replace("\\", "/")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("slug")
    parser.add_argument("indicatori", nargs="+", help="famiglia:codice, il primo e' il principale")
    args = parser.parse_args(argv)

    analisi = [analizza(k) for k in args.indicatori]
    download = scrivi_csv(args.slug, analisi)
    uscita = comuni.ARTICOLI / args.slug / "dossier.json"
    comuni.scrivi_json(uscita, {
        "slug": args.slug, "creato": comuni.oggi(), "download": download,
        "nota_medie": "Le medie sono medie semplici dei territori, non pesate per popolazione: non sono la media nazionale.",
        "indicatori": analisi,
    })
    for a in analisi:
        m = a["meta"]
        print(f"{m['chiave']}: {m['nome']} [{m['unita']}] {m['anni'][0]}-{m['anni'][1]}, {m['territori']} territori, pagina {m['pagina']}")
        testa = ", ".join(f"{r['territorio']} {r['testo']}" for r in a["classifica"][:3])
        coda = ", ".join(f"{r['territorio']} {r['testo']}" for r in a["classifica"][-3:])
        print(f"   {a['ultimo_anno']} in testa: {testa} | in fondo: {coda}")
    print(f"-> {uscita.relative_to(comuni.RADICE)}  csv {download}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
