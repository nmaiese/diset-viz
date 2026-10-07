"""Calcoli per la scheda ipr:pil-per-abitante. Scrive numeri.md.

    bin/py lavoro/pil-province/calcola.py
"""
import csv
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROV = ROOT / "app/static/data/nuovi/istat_prov.csv"
CODES = ROOT / "app/static/data/province_codes.csv"
ASS = ROOT / "app/static/data/Assoluti_Provincia.csv"
SERIE = "ISTATP_PIL_PRO_CAPITE"

names = {}
region = {}
with open(CODES, encoding="utf-8") as f:
    for r in csv.DictReader(f, delimiter=";"):
        names[r["province_key"]] = r["name"]
        region[r["province_key"]] = r["region"]

val = {}   # (key, year) -> (value, riga CSV)
with open(PROV, encoding="utf-8") as f:
    for n, r in enumerate(csv.DictReader(f, delimiter=";"), start=2):
        if r["indicator_id"] == SERIE:
            val[(r["territory_key"], int(r["year"]))] = (float(r["value"]), n)

keys = sorted({k for k, _ in val})
years = sorted({y for _, y in val})
out = []


def rec(label, value, formula, rows=""):
    out.append(f"| {label} | {value} | {formula} | {rows} |")


def fmt(x, d=0):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def rank(year):
    """Posto 1 = valore piu' alto. Parita' rotte per nome (regola del sito)."""
    order = sorted(keys, key=lambda k: (-val[(k, year)][0], names[k]))
    return {k: i + 1 for i, k in enumerate(order)}, order


rec("province con dato", len(keys), "territori distinti della serie")
rec("anni", f"{years[0]}-{years[-1]}", "min e max anno")
for y in (2015, 2023):
    r, order = rank(y)
    hi, lo = order[0], order[-1]
    rec(f"{y} massimo", f"{names[hi]} ({region[hi]}) {fmt(val[(hi,y)][0])} euro", "valore piu' alto", f"riga {val[(hi,y)][1]}")
    rec(f"{y} minimo", f"{names[lo]} ({region[lo]}) {fmt(val[(lo,y)][0])} euro", "valore piu' basso", f"riga {val[(lo,y)][1]}")
    rec(f"{y} rapporto max/min", fmt(val[(hi,y)][0] / val[(lo,y)][0], 2), "max / min (non arrotondati)")
    rec(f"{y} differenza max-min", f"{fmt(val[(hi,y)][0] - val[(lo,y)][0])} euro", "max - min")
    v = [val[(k, y)][0] for k in keys]
    rec(f"{y} mediana delle 107", f"{fmt(st.median(v))} euro", "mediana dei 107 valori")
    rec(f"{y} media semplice delle 107", f"{fmt(st.mean(v))} euro", "media aritmetica non ponderata")
    rec(f"{y} prime 5", ", ".join(f"{names[k]} {fmt(val[(k,y)][0])}" for k in order[:5]), "ordine decrescente")
    rec(f"{y} ultime 5", ", ".join(f"{names[k]} {fmt(val[(k,y)][0])}" for k in order[-5:]), "ordine crescente da fondo")

r15, o15 = rank(2015)
r23, o23 = rank(2023)

# Quante delle ultime 10 / prime 10 nel 2023 stanno in che regioni
rec("2023 prime 10", ", ".join(f"{names[k]}" for k in o23[:10]), "ordine decrescente")
rec("2023 ultime 10", ", ".join(f"{names[k]}" for k in o23[-10:]), "ordine crescente da fondo")
rec("2023 ultime 10 regioni", ", ".join(sorted({region[k] for k in o23[-10:]})), "regioni delle ultime 10")

# Crescita nominale
g = {k: (val[(k, 2023)][0] / val[(k, 2015)][0] - 1) * 100 for k in keys}
gd = {k: val[(k, 2023)][0] - val[(k, 2015)][0] for k in keys}
og = sorted(keys, key=lambda k: (-g[k], names[k]))
rec("crescita mediana 2015-2023", f"{fmt(st.median(g.values()),1)}%", "mediana di (v2023/v2015 - 1)*100")
rec("crescita minima", f"{names[og[-1]]} {fmt(g[og[-1]],1)}% ({fmt(val[(og[-1],2015)][0])} -> {fmt(val[(og[-1],2023)][0])})", "min crescita", f"righe {val[(og[-1],2015)][1]}, {val[(og[-1],2023)][1]}")
rec("crescita massima", f"{names[og[0]]} {fmt(g[og[0]],1)}% ({fmt(val[(og[0],2015)][0])} -> {fmt(val[(og[0],2023)][0])})", "max crescita", f"righe {val[(og[0],2015)][1]}, {val[(og[0],2023)][1]}")
rec("province con crescita sotto il 10%", sum(1 for k in keys if g[k] < 10), "conteggio g<10")
rec("province con calo 2015-2023", sum(1 for k in keys if g[k] < 0), "conteggio g<0")
rec("incremento assoluto mediano", f"{fmt(st.median(gd.values()))} euro", "mediana di v2023-v2015")
rec("incremento assoluto massimo", f"{names[max(keys,key=lambda k:gd[k])]} {fmt(max(gd.values()))} euro", "max(v2023-v2015)")
rec("incremento assoluto minimo", f"{names[min(keys,key=lambda k:gd[k])]} {fmt(min(gd.values()))} euro", "min(v2023-v2015)")
rec("prime 5 per crescita %", ", ".join(f"{names[k]} {fmt(g[k],1)}%" for k in og[:5]), "ordine decrescente")
rec("ultime 5 per crescita %", ", ".join(f"{names[k]} {fmt(g[k],1)}%" for k in og[-5:]), "ordine")

# Posizioni
dp = {k: r15[k] - r23[k] for k in keys}   # >0 = salito
up = sorted(keys, key=lambda k: (-dp[k], names[k]))
rec("posti guadagnati (top 5)", ", ".join(f"{names[k]} {dp[k]:+d} ({r15[k]} -> {r23[k]})" for k in up[:6]), "posto2015 - posto2023")
rec("posti persi (top 5)", ", ".join(f"{names[k]} {dp[k]:+d} ({r15[k]} -> {r23[k]})" for k in up[-6:]), "posto2015 - posto2023")
rec("province che nel 2023 stanno nelle prime 10 e c'erano nel 2015", len(set(o15[:10]) & set(o23[:10])), "intersezione prime 10")
rec("province che nel 2023 stanno nelle ultime 10 e c'erano nel 2015", len(set(o15[-10:]) & set(o23[-10:])), "intersezione ultime 10")
rec("province che hanno cambiato posto", sum(1 for k in keys if dp[k] != 0), "conteggio dp!=0")
rec("scostamento medio assoluto di posto", fmt(st.mean(abs(dp[k]) for k in keys), 1), "media di |posto2015-posto2023|")
for k in ("milano", "roma", "napoli", "bolzano-bozen", "torino", "bologna", "trieste", "reggio-di-calabria", "crotone"):
    if (k, 2023) in val:
        rec(f"{names[k]}", f"2015: {fmt(val[(k,2015)][0])} (posto {r15[k]}) 2023: {fmt(val[(k,2023)][0])} (posto {r23[k]})", "valori e posti", f"righe {val[(k,2015)][1]}, {val[(k,2023)][1]}")

# Anno per anno max/min
for y in years:
    r_, o_ = rank(y)
    rec(f"{y} rapporto max/min", fmt(val[(o_[0], y)][0] / val[(o_[-1], y)][0], 2), f"{names[o_[0]]} / {names[o_[-1]]}")

# Reddito disponibile pro capite provinciale (04BEC001P), per il confronto produzione/reddito
inc = {}
with open(ASS, encoding="utf-8") as f:
    for n, r in enumerate(csv.DictReader(f, delimiter=";"), start=2):
        if r["idIndicatore"] == "04BEC001P" and r["Livello/Variazione"] == "Livello" and r["Anno"] == "2023":
            inc[r["Territorio"]] = (float(r["Dato"].replace(".", "").replace(",", ".")), n)
rec("reddito 04BEC001P: province con dato 2023", len(inc), "righe idIndicatore=04BEC001P, Anno=2023, Livello")
byname = {names[k]: k for k in keys}
miss = [n for n in inc if n not in byname]
rec("nomi del reddito senza corrispondenza", ", ".join(miss) or "nessuno", "confronto nomi")
if inc:
    ihi = max(inc, key=lambda n: inc[n][0]); ilo = min(inc, key=lambda n: inc[n][0])
    rec("reddito 2023 massimo", f"{ihi} {fmt(inc[ihi][0])} euro", "max", f"riga {inc[ihi][1]}")
    rec("reddito 2023 minimo", f"{ilo} {fmt(inc[ilo][0])} euro", "min", f"riga {inc[ilo][1]}")
    rec("reddito 2023 rapporto max/min", fmt(inc[ihi][0] / inc[ilo][0], 2), "max / min")
    for k in (o23[0], o23[1], o23[-1], "milano", "roma"):
        n = names[k]
        if n in inc:
            rec(f"reddito 2023 {n}", f"{fmt(inc[n][0])} euro, posto {sorted(inc, key=lambda x:-inc[x][0]).index(n)+1} su {len(inc)}", "posto per reddito", f"riga {inc[n][1]}")
    # rapporto PIL / reddito
    for k in (o23[0], "milano", "roma", o23[-1]):
        n = names[k]
        if n in inc:
            rec(f"PIL/reddito 2023 {n}", fmt(val[(k, 2023)][0] / inc[n][0], 2), "PIL per abitante / reddito disponibile pro capite (euro su euro, grandezze diverse: confronto non quota)")
    common = [k for k in keys if names[k] in inc]
    # correlazione di rango semplice
    def ranks(xs):
        o = sorted(range(len(xs)), key=lambda i: xs[i]); r = [0]*len(xs)
        for p, i in enumerate(o): r[i] = p
        return r
    a = ranks([val[(k, 2023)][0] for k in common]); b = ranks([inc[names[k]][0] for k in common])
    n = len(common); ma = sum(a)/n
    cov = sum((x-ma)*(y-ma) for x, y in zip(a, b)); va = sum((x-ma)**2 for x in a)
    rec("correlazione di rango PIL/reddito 2023", fmt(cov/va, 2), f"Spearman su {n} province")

(ROOT / "lavoro/pil-province/numeri.md").write_text(
    "# Numeri\n\nGenerato da `lavoro/pil-province/calcola.py`. Serie `ISTATP_PIL_PRO_CAPITE` in "
    "`app/static/data/nuovi/istat_prov.csv` (riga = numero di riga del file, intestazione = 1). "
    "Posti: 1 = valore piu' alto, parita' rotte per nome.\n\n"
    "| numero | valore | formula | riga CSV |\n|---|---|---|---|\n" + "\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
