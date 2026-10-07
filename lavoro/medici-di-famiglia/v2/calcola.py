#!/usr/bin/env python3
"""Riproduce correlazioni e controlli dello scout medici di famiglia.

Usa le viste complete del catalogo del worktree, senza dipendenze statistiche
esterne. Eseguire dalla radice con DIVARIO_PYTHON impostato come da SPEC.
"""
from __future__ import annotations

from math import sqrt
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from app.indicator_view import build_indicator_view

SERIES = {
    "oltre_soglia": ("bes", "12SER027"),
    "rinunce": ("bes", "12SER026"),
    "medici": ("bes", "SDG-3"),
    "infermieri": ("bes", "SDG-4"),
    "specialisti": ("bes", "12SER002P"),
    "posti_letto": ("bes", "12SER003P-N25"),
    "adi": ("bes", "12SER003"),
    "eta65": ("istat_demografia", "POP65OVER"),
    "costo_adi": ("territorial", "145"),
    "pronto_soccorso": ("multiscopo", "MULTI_PRONTO_SOCCORSO"),
    "guardia_medica": ("multiscopo", "MULTI_GUARDIA_MEDICA"),
    "emigrazione": ("bes", "12SER025"),
    "fila_asl": ("multiscopo", "MULTI_ASL_FILA_OLTRE_20_MIN"),
    "adi_socioassistenziale": ("territorial", "415"),
    "posti_letto_alta_assistenza": ("bes", "12SER022"),
    "salute_75": ("bes", "01SAL021"),
    "difficolta_servizi": ("bes", "12SER004"),
}


def load():
    result = {}
    for name, (family, raw_id) in SERIES.items():
        view = build_indicator_view(family, raw_id)
        regional = next((level for level in view["levels"] if level["key"] == "regione"), None)
        result[name] = regional["matrix"] if regional else {}
    return result


def ranks(values):
    order = sorted(range(len(values)), key=values.__getitem__)
    output = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        rank = (i + 1 + j) / 2
        for pos in range(i, j):
            output[order[pos]] = rank
        i = j
    return output


def spearman(left, right):
    if len(left) < 2 or len(left) != len(right):
        return None
    x, y = ranks(left), ranks(right)
    mx, my = sum(x) / len(x), sum(y) / len(y)
    denominator = sqrt(sum((v - mx) ** 2 for v in x) * sum((v - my) ** 2 for v in y))
    if not denominator:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / denominator


def year_values(data, key, year):
    return {territory: value for territory, value in data[key].get(str(year), {}).items()
            if value is not None}


def paired(data, left, right, year):
    a, b = year_values(data, left, year), year_values(data, right, year)
    keys = sorted(a.keys() & b.keys())
    return keys, spearman([a[k] for k in keys], [b[k] for k in keys])


def delta_pair(data, left, right, start, end):
    a0, a1 = year_values(data, left, start), year_values(data, left, end)
    b0, b1 = year_values(data, right, start), year_values(data, right, end)
    keys = sorted(a0.keys() & a1.keys() & b0.keys() & b1.keys())
    da = [a1[k] - a0[k] for k in keys]
    db = [b1[k] - b0[k] for k in keys]
    return keys, da, db, spearman(da, db)


def fmt(value):
    return "n/d" if value is None else f"{value:.3f}"


def main():
    data = load()
    print("Spearman 2023: H1/H2 e matrice a ultimo anno comune (regioni, N=20)")
    names = ["oltre_soglia", "rinunce", "medici", "infermieri", "adi", "eta65",
             "pronto_soccorso", "guardia_medica", "emigrazione", "fila_asl",
             "posti_letto_alta_assistenza", "salute_75", "difficolta_servizi"]
    print("codice;" + ";".join(names))
    for left in names:
        cells = []
        for right in names:
            keys, rho = paired(data, left, right, 2023)
            cells.append(fmt(rho) if len(keys) == 20 else "n/d")
        print(left + ";" + ";".join(cells))
    print("\nControlli H1 e H2, stesso campione regionale")
    for left, right in [("oltre_soglia", "rinunce"), ("oltre_soglia", "medici"),
                        ("oltre_soglia", "infermieri"), ("oltre_soglia", "eta65"),
                        ("oltre_soglia", "adi"), ("oltre_soglia", "emigrazione"),
                        ("oltre_soglia", "fila_asl")]:
        for year in (2023, 2022):
            keys, rho = paired(data, left, right, year)
            print(f"{left} vs {right}, {year}: N={len(keys)}, rho={fmt(rho)}, territori={','.join(keys)}")
    print("\nH3: variazione 2018-2023; controllo alternativo con fine 2022")
    for left, right in [("oltre_soglia", "pronto_soccorso"),
                        ("oltre_soglia", "guardia_medica"),
                        ("pronto_soccorso", "guardia_medica")]:
        for end in (2023, 2022):
            keys, da, db, rho = delta_pair(data, left, right, 2018, end)
            print(f"{left} vs {right}, delta 2018-{end}: N={len(keys)}, rho={fmt(rho)}")
    print("\nRiscontri descrittivi 2023: prime/ultime tre osservazioni per valore")
    for key in ["oltre_soglia", "rinunce", "medici", "eta65", "adi",
                "pronto_soccorso", "guardia_medica", "emigrazione", "fila_asl"]:
        rows = sorted(year_values(data, key, 2023).items(), key=lambda row: row[1])
        print(f"{key}: bassi={rows[:3]}; alti={rows[-3:]}")


if __name__ == "__main__":
    main()
