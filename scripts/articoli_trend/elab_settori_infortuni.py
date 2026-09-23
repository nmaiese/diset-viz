"""Elaborazione: quanto i settori spiegano gli infortuni gravi fra province.

Domanda: le province con piu' infortuni mortali o invalidanti ogni 10.000
occupati (Istat BES 03LAV007) sono solo quelle dove si lavora di piu' nei
campi, nelle fabbriche e nei cantieri? Se fosse cosi', a parita' di settori il
rischio sarebbe simile ovunque.

Dati:
- tasso di infortuni 03LAV007 per provincia, 2022, dal dataset del sito
  (`app/static/data/Assoluti_Provincia.csv`, Istat BES dei territori);
- occupati per branca e provincia, 2022, Istat Conti territoriali
  (dataflow 93_379_DF_DCCN_OCCTSEC2010_2, persone occupate, totale
  dipendenti e indipendenti, edizione piu' recente).

Metodo: per ogni provincia si calcola la quota di occupati in agricoltura
(A), industria in senso stretto (B-E) e costruzioni (F). Si stima con i
minimi quadrati il tasso di infortuni come combinazione lineare delle tre
quote (una retta in tre dimensioni, con intercetta). Il tasso "atteso" e'
quello che la provincia avrebbe se contassero solo i settori. La quota di
variabilita' spiegata (R quadro) dice quanto delle differenze fra province
i settori spiegano. Il resto dipende da altro: dimensione delle imprese,
eta' dei lavoratori, controlli, sottodenuncia, caso.

Limiti: e' un confronto fra province, non fra lavoratori. Le branche sono
larghe (dentro "industria" ci sono cave e uffici). Il lavoro irregolare non
e' assicurato Inail, quindi dove e' piu' diffuso il tasso misurato si
abbassa invece di alzarsi.

    bin/py -m scripts.articoli_trend.elab_settori_infortuni
"""

from __future__ import annotations

import csv
import io
import sys

import requests

from scripts.articoli_trend import comuni

SDMX = ("https://esploradati.istat.it/SDMXWS/rest/data/IT1,93_379_DF_DCCN_OCCTSEC2010_2,1.0/"
        "A..PS......?startPeriod=2022&endPeriod=2022")
ANNO = 2022
BASE = comuni.ELABORAZIONI / "infortuni_attesi_settori"


def _risolvi(a: list[list[float]], b: list[float]) -> list[float]:
    """Eliminazione di Gauss: il sistema e' 4x4, non serve una libreria."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        for r in range(n):
            if r != c:
                f = m[r][c] / m[c][c]
                m[r] = [x - f * y for x, y in zip(m[r], m[c])]
    return [m[i][n] / m[i][i] for i in range(n)]


def occupati() -> dict[str, dict[str, float]]:
    testo = requests.get(SDMX, headers={"Accept": "application/vnd.sdmx.data+csv;version=1.0.0"}, timeout=300).text
    righe = list(csv.DictReader(io.StringIO(testo)))
    edizione = max(r["EDITION"] for r in righe)
    esito: dict[str, dict[str, float]] = {}
    for r in righe:
        if (r["EDITION"] == edizione and r["TIME_PERIOD"] == str(ANNO) and r["EMPLOYMENT_STATUS"] == "9"
                and r["DATA_TYPE_AGGR"] == "PS" and len(r["REF_AREA"]) == 5):
            esito.setdefault(r["REF_AREA"], {})[r["BRKDW_INDUSTRY_NACE_REV2"]] = float(r["OBS_VALUE"])
    return esito


def main() -> int:
    with (comuni.DATI_SITO / "province_codes.csv").open(encoding="utf-8") as f:
        codice = {r["name"]: r["code"] for r in csv.DictReader(f, delimiter=";")}
    tasso = {t: per[ANNO] for t, per in comuni.serie("prov:03LAV007")["valori"].items() if ANNO in per}
    occ = occupati()

    dati = []
    for nome, v in tasso.items():
        o = occ.get(codice.get(nome, ""))
        if not o or not o.get("_T"):
            continue
        quote = [100 * o.get(s, 0) / o["_T"] for s in ("A", "BTE", "F")]
        dati.append((nome, v, quote))
    x = [[1.0, *q] for _, _, q in dati]
    y = [v for _, v, _ in dati]
    xtx = [[sum(r[i] * r[j] for r in x) for j in range(4)] for i in range(4)]
    xty = [sum(r[i] * yy for r, yy in zip(x, y)) for i in range(4)]
    beta = _risolvi(xtx, xty)
    attesi = [sum(b * xi for b, xi in zip(beta, r)) for r in x]
    media = sum(y) / len(y)
    r2 = 1 - sum((a - b) ** 2 for a, b in zip(y, attesi)) / sum((a - media) ** 2 for a in y)

    comuni.ELABORAZIONI.mkdir(parents=True, exist_ok=True)
    with BASE.with_suffix(".csv").open("w", encoding="utf-8") as f:
        f.write("territorio,anno,valore,osservato,quota_agricoltura,quota_industria,quota_costruzioni\n")
        for (nome, v, q), att in zip(dati, attesi):
            f.write(f"{nome},{ANNO},{att:.1f},{v},{q[0]:.1f},{q[1]:.1f},{q[2]:.1f}\n")
    with (comuni.ELABORAZIONI / "quota_occupati_agri_ind_costr.csv").open("w", encoding="utf-8") as f:
        f.write("territorio,anno,valore\n")
        for nome, _, q in dati:
            f.write(f"{nome},{ANNO},{sum(q):.1f}\n")
    metodo = __doc__.split("Metodo:")[1].split("Limiti:")[0].strip().replace("\n", " ")
    comuni.scrivi_json(BASE.with_suffix(".json"), {
        "nome": "Tasso di infortuni atteso in base ai settori",
        "unita": "per 10.000 occupati",
        "fonte": "Istat",
        "archivio": "BES dei territori (03LAV007) e Conti territoriali, occupati per branca (93_379_DF_DCCN_OCCTSEC2010_2)",
        "source_url": SDMX,
        "method": metodo,
        "script": "scripts/articoli_trend/elab_settori_infortuni.py",
        "province": len(dati),
        "r2": round(r2, 3),
        "coefficienti": {"intercetta": round(beta[0], 3), "agricoltura": round(beta[1], 3),
                         "industria": round(beta[2], 3), "costruzioni": round(beta[3], 3)},
    })
    comuni.scrivi_json(comuni.ELABORAZIONI / "quota_occupati_agri_ind_costr.json", {
        "nome": "Occupati in agricoltura, industria e costruzioni",
        "unita": "percentuale sugli occupati totali",
        "fonte": "Istat",
        "archivio": "Conti territoriali, occupati per branca e provincia",
        "source_url": SDMX,
        "method": "Somma delle persone occupate nelle branche A, B-E e F divisa per il totale delle persone occupate, per provincia, 2022.",
        "script": "scripts/articoli_trend/elab_settori_infortuni.py",
    })
    residui = sorted(((v - a, n, v, a) for (n, v, _), a in zip(dati, attesi)), reverse=True)
    print(f"province {len(dati)}, R2 {r2:.3f}, beta {[round(b, 3) for b in beta]}")
    for d, n, v, a in residui[:8] + residui[-5:]:
        print(f"  {n:25s} osservato {v:5.1f} atteso {a:5.1f} scarto {d:+5.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
