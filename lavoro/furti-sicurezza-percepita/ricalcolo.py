"""Reproduce regional comparisons from the repository BES CSV.

Run from any directory with: bin/py lavoro/furti-sicurezza-percepita/ricalcolo.py
Values are parsed and differenced as Decimal so published tenths retain ties.
"""

import csv
import math
from collections import Counter
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "app/static/data/Assoluti_BES_Regione.csv"
IDS = {
    "furti": "07SIC002",
    "rischio": "07SIC022",
    "rapine": "07SIC004",
    "borseggi": "07SIC003",
    "degrado": "07SIC021",
    "sicurezza": "07SIC020",
}
PAIRS = (("furti", "rischio"), ("rapine", "rischio"), ("furti", "rapine"))
EXCLUDED = {"Toscana", "Campania"}


def read_values():
    values = {}
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            if (
                row["Area"] == "Regione"
                and row["Livello/Variazione"] == "Livello"
                and row["idIndicatore"] in IDS.values()
            ):
                values[(row["idIndicatore"], row["Territorio"], int(row["Anno"]))] = Decimal(
                    row["Dato"].replace(",", ".")
                )
    return values


def midranks(values):
    return [
        sum(other < value for other in values)
        + (sum(other == value for other in values) + 1) / 2
        for value in values
    ]


def spearman(left, right):
    """Pearson correlation of exact average ranks; convert only final math."""
    x, y = midranks(left), midranks(right)
    mx, my = sum(x) / len(x), sum(y) / len(y)
    dx, dy = [v - mx for v in x], [v - my for v in y]
    numerator = sum(a * b for a, b in zip(dx, dy))
    denominator = math.sqrt(sum(a * a for a in dx) * sum(b * b for b in dy))
    return numerator / denominator


def main():
    data = read_values()
    regions = sorted({region for code, region, year in data if code == IDS["furti"] and year == 2025})
    for start in (2023, 2019):
        print(f"\nFinestra {start}-2025")
        for exclude in (set(), EXCLUDED):
            sample = [region for region in regions if region not in exclude]
            delta = {
                name: [data[IDS[name], region, 2025] - data[IDS[name], region, start] for region in sample]
                for name in IDS
            }
            divergent = sum(
                furti < 0 and rischio > 0
                for furti, rischio in zip(delta["furti"], delta["rischio"])
            )
            label = "tutte" if not exclude else "senza Toscana e Campania"
            print(f"{label}: N={len(sample)}, divergenze={divergent}/{len(sample)}")
            for left, right in PAIRS:
                print(f"  {left}/{right}: rho={spearman(delta[left], delta[right]):.9f}")

    print("\nLeave-one-out, rho minimo e massimo con esclusione")
    for start in (2023, 2019):
        for left, right in PAIRS[:2]:
            results = []
            for omitted in regions:
                sample = [region for region in regions if region != omitted]
                x = [data[IDS[left], region, 2025] - data[IDS[left], region, start] for region in sample]
                y = [data[IDS[right], region, 2025] - data[IDS[right], region, start] for region in sample]
                results.append((spearman(x, y), omitted))
            print(f"{start} {left}/{right}: min={min(results)}, max={max(results)}")

    print("\nZeri, segni e medie semplici")
    for start in (2023, 2019):
        for name, code in IDS.items():
            changes = [data[code, region, 2025] - data[code, region, start] for region in regions]
            signs = Counter(("pos" if value > 0 else "neg" if value < 0 else "zero") for value in changes)
            print(f"{start} {name}: {dict(signs)}, media_delta={sum(changes) / len(changes)}")
    print("\nMedie livelli")
    for name, code in IDS.items():
        means = [sum(data[code, region, year] for region in regions) / len(regions) for year in (2019, 2023, 2025)]
        print(f"{name}: 2019={means[0]}, 2023={means[1]}, 2025={means[2]}")


if __name__ == "__main__":
    main()
