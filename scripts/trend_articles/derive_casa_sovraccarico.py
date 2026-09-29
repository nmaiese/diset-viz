"""Prova: che cosa accompagna il sovraccarico del costo dell'abitazione.

Confronta il sovraccarico regionale 2025 (`bes:SDG-222`) con la quota di
famiglie in affitto (`ims:MULTI_ABIT_AFFITTO`, 2025), la spesa per l'abitazione
ogni 100 euro di reddito (`ims:MULTI_ABIT_SPESA_REDDITO`, 2025) e il reddito
netto mediano delle famiglie (`ims:MULTI_REDD_MEDIANO`, 2024, ultimo anno),
sulle sole regioni che hanno il dato 2025 del sovraccarico. Con tre metodi:
Pearson, Spearman e Pearson lasciando fuori una regione per volta. In piu',
quanta parte della varianza del sovraccarico sta fra le ripartizioni
(Nord, Centro, Mezzogiorno) e quanta dentro.

E' materiale per chi coordina: campione di 14 regioni al massimo (6 non hanno
il dato 2025), correlazioni fra territori, nessuna causa.

    bin/py -m scripts.trend_articles.derive_casa_sovraccarico

Scrive `data/derived/casa_sovraccarico_prove.{csv,json}`.
"""

from __future__ import annotations

import statistics

from scripts.trend_articles import common

TARGET = "bes:SDG-222"
PREDICTORS = {
    "affitto": ("ims:MULTI_ABIT_AFFITTO", 2025),
    "spesa_reddito": ("ims:MULTI_ABIT_SPESA_REDDITO", 2025),
    "reddito_mediano": ("ims:MULTI_REDD_MEDIANO", 2024),
}


def pearson(x, y):
    if len(x) < 3:
        return None
    mx, my = statistics.fmean(x), statistics.fmean(y)
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    if sxx == 0 or syy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sxx * syy) ** 0.5


def ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return out


def spearman(x, y):
    return pearson(ranks(x), ranks(y))


def loo_range(x, y):
    vals = [pearson(x[:i] + x[i + 1:], y[:i] + y[i + 1:]) for i in range(len(x))]
    vals = [v for v in vals if v is not None]
    return (min(vals), max(vals)) if vals else (None, None)


def main() -> int:
    target = common.series(TARGET)["values"]
    regions = sorted(t for t, per in target.items() if 2025 in per)
    area = {r: ("Mezzogiorno" if common.macro_area(r, "regione") == "Mezzogiorno" else "Centro-Nord") for r in regions}
    data = {name: common.series(key)["values"] for name, (key, _) in PREDICTORS.items()}
    rows = []
    print(f"regioni con sovraccarico 2025: {len(regions)}; Mezzogiorno: {[r for r in regions if area[r] == 'Mezzogiorno']}")
    for name, (key, year) in PREDICTORS.items():
        for group in ("tutte", "Centro-Nord", "Mezzogiorno"):
            pts = [(data[name][r][year], target[r][2025]) for r in regions
                   if r in data[name] and year in data[name][r] and (group == "tutte" or area[r] == group)]
            x, y = [p[0] for p in pts], [p[1] for p in pts]
            lo, hi = loo_range(x, y)
            rows.append({
                "misura": name, "gruppo": group, "n": len(pts),
                "pearson": pearson(x, y), "spearman": spearman(x, y),
                "pearson_loo_min": lo, "pearson_loo_max": hi,
            })
    # varianza fra ripartizioni
    ys = [target[r][2025] for r in regions]
    grand = statistics.fmean(ys)
    total = sum((v - grand) ** 2 for v in ys)
    between = 0.0
    for g in ("Centro-Nord", "Mezzogiorno"):
        vs = [target[r][2025] for r in regions if area[r] == g]
        between += len(vs) * (statistics.fmean(vs) - grand) ** 2
    share_between = between / total
    rows.append({"misura": "quota_varianza_fra_ripartizioni", "gruppo": "tutte", "n": len(ys),
                 "pearson": share_between, "spearman": None, "pearson_loo_min": None, "pearson_loo_max": None})
    for r in rows:
        print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()})

    common.DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    base = common.DERIVED_DIR / "casa_sovraccarico_prove"
    fields = ["misura", "gruppo", "n", "pearson", "spearman", "pearson_loo_min", "pearson_loo_max"]
    with base.with_suffix(".csv").open("w", encoding="utf-8") as f:
        f.write(",".join(fields) + "\n")
        for r in rows:
            f.write(",".join("" if r[k] is None else (f"{r[k]:.3f}" if isinstance(r[k], float) else str(r[k])) for k in fields) + "\n")
    common.write_json(base.with_suffix(".json"), {
        "name": "Sovraccarico del costo dell'abitazione 2025 e sue possibili compagne, per gruppo di regioni",
        "unit": "coefficiente (Pearson, Spearman); per la riga quota_varianza_fra_ripartizioni e' una quota fra 0 e 1",
        "source": "Istat, elaborazione su BES (SDG-222) e Indagine Multiscopo",
        "method": "Pearson e Spearman fra regioni, Pearson lasciando fuori una regione per volta, sulle sole regioni con il sovraccarico 2025. Nel campo pearson della riga quota_varianza_fra_ripartizioni c'e' la quota di varianza del sovraccarico che sta fra Centro-Nord e Mezzogiorno. Sono associazioni fra territori, non cause, su pochi punti.",
        "script": "scripts/trend_articles/derive_casa_sovraccarico.py",
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
