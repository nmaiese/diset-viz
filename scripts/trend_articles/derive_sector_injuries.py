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
quote (con intercetta). Il tasso "atteso" e' quello che la provincia avrebbe
se contassero solo i settori. La quota di variabilita' spiegata (R quadro, e
R quadro corretto per il numero di variabili) dice quanto delle differenze
fra province i settori spiegano.

Limiti: e' un confronto fra province, non fra lavoratori. Le branche sono
larghe (dentro "industria" ci sono cave e uffici). Il tasso Istat divide gli
infortuni per gli occupati residenti, mentre qui le quote vengono dagli
occupati per luogo di lavoro. Gli infortuni non denunciati non sono contati.

    bin/py -m scripts.trend_articles.derive_sector_injuries
"""

from __future__ import annotations

import csv
import io
import sys

import requests

from scripts.trend_articles import common

SDMX = ("https://esploradati.istat.it/SDMXWS/rest/data/IT1,93_379_DF_DCCN_OCCTSEC2010_2,1.0/"
        "A..PS......?startPeriod=2022&endPeriod=2022")
YEAR = 2022
BASE = common.DERIVED_DIR / "injuries_expected_by_sector"
SHARE = common.DERIVED_DIR / "employment_share_agri_ind_constr"


def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    """Eliminazione di Gauss: il sistema e' 4x4, non serve una libreria."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        pivot = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[pivot] = m[pivot], m[c]
        for r in range(n):
            if r != c:
                f = m[r][c] / m[c][c]
                m[r] = [x - f * y for x, y in zip(m[r], m[c], strict=True)]
    return [m[i][n] / m[i][i] for i in range(n)]


def employment() -> dict[str, dict[str, float]]:
    response = requests.get(SDMX, headers={"Accept": "application/vnd.sdmx.data+csv;version=1.0.0"}, timeout=300)
    response.raise_for_status()
    records = list(csv.DictReader(io.StringIO(response.text)))
    edition = max(r["EDITION"] for r in records)
    result: dict[str, dict[str, float]] = {}
    for r in records:
        if (r["EDITION"] == edition and r["TIME_PERIOD"] == str(YEAR) and r["EMPLOYMENT_STATUS"] == "9"
                and r["DATA_TYPE_AGGR"] == "PS" and len(r["REF_AREA"]) == 5):
            result.setdefault(r["REF_AREA"], {})[r["BRKDW_INDUSTRY_NACE_REV2"]] = float(r["OBS_VALUE"])
    if not result:
        raise ValueError(f"nessuna provincia per il {YEAR} nella risposta di {SDMX}")
    return result


def main() -> int:
    with (common.SITE_DATA / "province_codes.csv").open(encoding="utf-8") as f:
        code_of = {r["name"]: r["code"] for r in csv.DictReader(f, delimiter=";")}
    rate = {t: per[YEAR] for t, per in common.series("prov:03LAV007")["values"].items() if YEAR in per}
    jobs = employment()

    data = []
    for name, v in rate.items():
        o = jobs.get(code_of.get(name, ""))
        if not o or not o.get("_T"):
            continue
        data.append((name, v, [100 * o.get(s, 0) / o["_T"] for s in ("A", "BTE", "F")]))
    x = [[1.0, *q] for _, _, q in data]
    y = [v for _, v, _ in data]
    xtx = [[sum(r[i] * r[j] for r in x) for j in range(4)] for i in range(4)]
    xty = [sum(r[i] * yy for r, yy in zip(x, y, strict=True)) for i in range(4)]
    beta = _solve(xtx, xty)
    expected = [sum(b * xi for b, xi in zip(beta, r, strict=True)) for r in x]
    mean = sum(y) / len(y)
    ss_res = sum((a - b) ** 2 for a, b in zip(y, expected, strict=True))
    ss_tot = sum((a - mean) ** 2 for a in y)
    r2 = 1 - ss_res / ss_tot
    n, k = len(y), 3
    r2_adj = 1 - (1 - r2) * (n - 1) / (n - k - 1)

    common.DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    with BASE.with_suffix(".csv").open("w", encoding="utf-8") as f:
        f.write("territory,year,value,observed,share_agriculture,share_industry,share_construction\n")
        for (name, v, q), e in zip(data, expected, strict=True):
            f.write(f"{name},{YEAR},{e:.1f},{v},{q[0]:.1f},{q[1]:.1f},{q[2]:.1f}\n")
    with SHARE.with_suffix(".csv").open("w", encoding="utf-8") as f:
        f.write("territory,year,value\n")
        for name, _, q in data:
            f.write(f"{name},{YEAR},{sum(q):.1f}\n")
    method = __doc__.split("Metodo:")[1].split("Limiti:")[0].strip().replace("\n", " ")
    common.write_json(BASE.with_suffix(".json"), {
        "name": "Tasso di infortuni atteso in base ai settori",
        "unit": "per 10.000 occupati",
        "source": "Istat",
        "archive": "BES dei territori (03LAV007) e Conti territoriali, occupati per branca (93_379_DF_DCCN_OCCTSEC2010_2)",
        "source_url": SDMX,
        "method": method,
        "script": "scripts/trend_articles/derive_sector_injuries.py",
        "provinces": n,
        "r2": round(r2, 3),
        "r2_adjusted": round(r2_adj, 3),
        "coefficients": {"intercept": round(beta[0], 3), "agriculture": round(beta[1], 3),
                         "industry": round(beta[2], 3), "construction": round(beta[3], 3)},
    })
    common.write_json(SHARE.with_suffix(".json"), {
        "name": "Occupati in agricoltura, industria e costruzioni",
        "unit": "percentuale sugli occupati totali",
        "source": "Istat",
        "archive": "Conti territoriali, occupati per branca e provincia",
        "source_url": SDMX,
        "method": "Somma delle persone occupate nelle branche A, B-E e F divisa per il totale delle persone occupate, per provincia, 2022.",
        "script": "scripts/trend_articles/derive_sector_injuries.py",
    })
    gaps = sorted(((v - e, name, v, e) for (name, v, _), e in zip(data, expected, strict=True)), reverse=True)
    print(f"province {n}, R2 {r2:.3f}, R2 corretto {r2_adj:.3f}, beta {[round(b, 3) for b in beta]}")
    for d, name, v, e in gaps[:8] + gaps[-5:]:
        print(f"  {name:25s} osservato {v:5.1f} atteso {e:5.1f} scarto {d:+5.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
