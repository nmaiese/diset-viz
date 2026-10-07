"""Ricalcola i numeri del pezzo sui medici di famiglia oltre soglia (bes:12SER027).

Legge le righe `Livello` di app/static/data/Assoluti_BES_Regione.csv (venti regioni)
e data/derived/bes_areas_12SER027.csv (valori Istat Italia e ripartizioni).
Scrive numeri.md e app/static/data/articles/medici-di-famiglia-regioni.csv.

    py lavoro/medici-di-famiglia/calcola.py
"""
import csv
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BES = "app/static/data/Assoluti_BES_Regione.csv"
ARE = "data/derived/bes_areas_12SER027.csv"
NORD = {"Piemonte", "Valle d'Aosta", "Lombardia", "Trentino Alto Adige", "Veneto", "Friuli-Venezia Giulia", "Liguria", "Emilia-Romagna"}
CENTRO = {"Toscana", "Umbria", "Marche", "Lazio"}
KEY = {"Valle d'Aosta": "valle-d-aosta", "Trentino Alto Adige": "trentino-alto-adige", "Friuli-Venezia Giulia": "friuli-venezia-giulia", "Emilia-Romagna": "emilia-romagna"}

S: dict[str, dict[int, float]] = {}
for r in csv.DictReader(open(ROOT / BES, encoding="utf-8"), delimiter=";"):
    if r["idIndicatore"] == "12SER027" and r["Livello/Variazione"] == "Livello":
        S.setdefault(r["Territorio"], {})[int(r["Anno"])] = float(r["Dato"].replace(",", "."))
A: dict[str, dict[int, float]] = {}
for r in csv.DictReader(open(ROOT / ARE, encoding="utf-8")):
    A.setdefault(r["territory"], {})[int(r["year"])] = float(r["value"])


def area(t):
    return "Nord" if t in NORD else "Centro" if t in CENTRO else "Mezzogiorno"


def rank(y):
    return {t: i for i, (t, _) in enumerate(sorted(((t, S[t][y]) for t in S), key=lambda x: -x[1]), 1)}


def it(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


R04, R23 = rank(2004), rank(2023)
L: list[tuple[str, str, str]] = []  # (affermazione, formula, valore)


def add(c, f, v):
    L.append((c, f, v))


assert len(S) == 20 and all(sorted(v) == list(range(2004, 2024)) for v in S.values())
add("Serie", "righe Livello di 12SER027, venti regioni, ogni anno presente", "2004-2023, 20 anni, nessun buco")
for t in ("Italia", "Nord", "Centro", "Mezzogiorno"):
    add(f"{t} 2004, 2010, 2019, 2023 (valori Istat, pesati)", f"{ARE} riga {t}", ", ".join(it(A[t][y]) for y in (2004, 2010, 2019, 2023)))
add("Italia oltre la meta per la prima volta", "max Italia 2004-2022 contro 2023", f"max prima {it(max(A['Italia'][y] for y in range(2004, 2023)))}, 2023 {it(A['Italia'][2023])}")
add("Rapporto Italia 2023 / 2004", "51,7 / 15,8", it(A["Italia"][2023] / A["Italia"][2004], 2))
gap = {y: A["Nord"][y] - A["Mezzogiorno"][y] for y in A["Nord"]}
add("Distanza Nord - Mezzogiorno 2004, 2010, 2019, 2023", "Nord meno Mezzogiorno, valori Istat", ", ".join(f"{y}: {it(gap[y])}" for y in (2004, 2010, 2019, 2023)))
add("Anno di massima distanza", "max sulla serie delle distanze", f"{max(gap, key=gap.get)} ({it(max(gap.values()))})")
add("Crescita 2019-2023 per ripartizione (punti)", "valore 2023 meno 2019", ", ".join(f"{t} {it(A[t][2023] - A[t][2019])}" for t in ("Nord", "Centro", "Mezzogiorno")))
add("Media semplice delle venti regioni 2004 e 2023 (non e il dato nazionale)", "mean dei venti valori", f"{it(st.mean(S[t][2004] for t in S))}, {it(st.mean(S[t][2023] for t in S))}")
top = sorted(S, key=lambda t: -S[t][2023])
add("Prime tre 2023", "ordinamento per valore", ", ".join(f"{t} {it(S[t][2023])}" for t in top[:3]))
add("Ultime quattro 2023", "ordinamento per valore", ", ".join(f"{t} {it(S[t][2023])}" for t in top[-4:]))
over = [t for t in S if S[t][2023] > 50]
add("Regioni sopra 50 nel 2023", "conteggio valori > 50", f"{len(over)}: " + ", ".join(sorted(over, key=lambda t: -S[t][2023])))
assert NORD <= set(over)
add("Regioni del Mezzogiorno sopra 50", "intersezione", ", ".join(t for t in over if area(t) == "Mezzogiorno"))
add("Posto 2004 e 2023 (da valore piu alto, nessun pari merito)", "ordinamento", "; ".join(f"{t} {R04[t]}->{R23[t]}" for t in ("Trentino Alto Adige", "Campania", "Sardegna", "Liguria", "Sicilia", "Puglia")))
add("Sardegna 2004, 2023, variazione", "valore 2023 meno 2004", f"{it(S['Sardegna'][2004])}, {it(S['Sardegna'][2023])}, +{it(S['Sardegna'][2023] - S['Sardegna'][2004])}")
add("Campania 2017, 2019, 2023", "righe serie", ", ".join(it(S["Campania"][y]) for y in (2017, 2019, 2023)))
add("Campania variazione 2019-2023", "58,8 meno 34,8", it(S["Campania"][2023] - S["Campania"][2019]))
add("Variazione 2004-2023, estremi", "valore 2023 meno 2004", "; ".join(f"{t} {it(S[t][2004])}->{it(S[t][2023])} (+{it(S[t][2023] - S[t][2004])})" for t in ("Lombardia", "Veneto", "Molise", "Sicilia")))
ch = sorted(S, key=lambda t: -(S[t][2023] - S[t][2004]))
add("Maggiori e minori aumenti", "ordinamento per variazione", f"piu alti {ch[0]}, {ch[1]}, {ch[2]}; piu bassi {ch[-1]}, {ch[-2]}")
add("Sicilia 2011, 2012, 2013, 2014 (scatto nella serie)", "righe serie", ", ".join(it(S["Sicilia"][y]) for y in (2011, 2012, 2013, 2014)))
add("Abruzzo, Basilicata 2023", "righe serie", f"{it(S['Abruzzo'][2023])}, {it(S['Basilicata'][2023])}")

with open(ROOT / "lavoro/medici-di-famiglia/numeri.md", "w", encoding="utf-8") as fh:
    fh.write("# Numeri\n\nGenerato da `lavoro/medici-di-famiglia/calcola.py`. Fonte: Istat, Bes, indicatore 12SER027, elaborazione su dati del Ministero della Salute (`app/static/data/Assoluti_BES_Regione.csv`, righe `Livello`; i valori di Italia e ripartizioni da `data/derived/bes_areas_12SER027.csv`, letti dall'appendice statistica Istat). Ripartizioni come `app/data.py` (`REGION_GEO_AREA`), Sud e Isole insieme come Mezzogiorno. Posti dal valore piu alto.\n\n| Affermazione | Formula o riga | Valore |\n| --- | --- | --- |\n")
    for c, f, v in L:
        fh.write(f"| {c} | {f} | {v} |\n")

with open(ROOT / "app/static/data/articles/medici-di-famiglia-regioni.csv", "w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["territorio", "chiave", "livello", "ripartizione", "quota_2004", "quota_2010", "quota_2019", "quota_2022", "quota_2023", "variazione_2004_2023", "posto_2004", "posto_2023", "fonte"])
    SRC = "Istat, Bes, elaborazione su dati Ministero della Salute"
    for t in sorted(S, key=lambda t: R23[t]):
        w.writerow([t, KEY.get(t, t.lower()), "regione", area(t), *(f"{S[t][y]:.1f}" for y in (2004, 2010, 2019, 2022, 2023)), f"{S[t][2023] - S[t][2004]:.1f}", R04[t], R23[t], SRC])
    for t in ("Italia", "Nord", "Centro", "Mezzogiorno"):
        w.writerow([t, t.lower(), "ripartizione" if t != "Italia" else "paese", "", *(f"{A[t][y]:.1f}" for y in (2004, 2010, 2019, 2022, 2023)), f"{A[t][2023] - A[t][2004]:.1f}", "", "", SRC + ", valori di ripartizione"])
    w.writerow(["Media semplice delle venti regioni", "media-semplice", "calcolo", "", *(f"{st.mean(S[t][y] for t in S):.1f}" for y in (2004, 2010, 2019, 2022, 2023)), f"{st.mean(S[t][2023] for t in S) - st.mean(S[t][2004] for t in S):.1f}", "", "", "Elaborazione Divario Italia, non e il dato nazionale"])
    w.writerow(["Distanza Nord meno Mezzogiorno", "distanza-nord-mezzogiorno", "calcolo", "", *(f"{A['Nord'][y] - A['Mezzogiorno'][y]:.1f}" for y in (2004, 2010, 2019, 2022, 2023)), f"{gap[2023] - gap[2004]:.1f}", "", "", "Elaborazione Divario Italia su valori Istat"])
print("ok")
