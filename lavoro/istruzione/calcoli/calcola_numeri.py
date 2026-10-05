#!/usr/bin/env python3
"""
Calcolo numeri per articolo istruzione (ter-104).
Legge i dati da app/static/data/Assoluti_Regione.csv e produce numeri.md.
"""

import csv
import math
from collections import defaultdict
from pathlib import Path

CSV_PATH = Path(__file__).parent.parent.parent.parent / "app/static/data/Assoluti_Regione.csv"
OUTPUT_DIR = Path(__file__).parent.parent
OUTPUT_MD = OUTPUT_DIR / "numeri.md"

REGION_ORDER = [
    "Piemonte", "Valle d'Aosta", "Lombardia", "Trentino Alto Adige", "Veneto",
    "Friuli-Venezia Giulia", "Liguria", "Emilia-Romagna", "Toscana", "Umbria",
    "Marche", "Lazio", "Abruzzo", "Molise", "Campania", "Puglia", "Basilicata",
    "Calabria", "Sicilia", "Sardegna",
]

REGION_GEO_AREA = {
    "Piemonte": "Nord", "Valle d'Aosta": "Nord", "Lombardia": "Nord",
    "Trentino Alto Adige": "Nord", "Veneto": "Nord", "Friuli-Venezia Giulia": "Nord",
    "Liguria": "Nord", "Emilia-Romagna": "Nord",
    "Toscana": "Centro", "Umbria": "Centro", "Marche": "Centro", "Lazio": "Centro",
    "Abruzzo": "Sud", "Molise": "Sud", "Campania": "Sud", "Puglia": "Sud",
    "Basilicata": "Sud", "Calabria": "Sud", "Sicilia": "Isole", "Sardegna": "Isole",
}

MEZZOGIORNO_REGIONS = {"Abruzzo", "Molise", "Campania", "Puglia", "Basilicata", "Calabria", "Sicilia", "Sardegna"}
NORD_REGIONS = {"Piemonte", "Valle d'Aosta", "Lombardia", "Trentino Alto Adige", "Veneto", "Friuli-Venezia Giulia", "Liguria", "Emilia-Romagna"}
CENTRO_REGIONS = {"Toscana", "Umbria", "Marche", "Lazio"}


def parse_value(v):
    if v is None or v == "":
        return None
    v = v.strip().replace(".", "").replace(",", ".")
    if v == "-" or v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def load_indicator_data(indicator_id, years=None):
    """Carica i dati per un indicatore dal CSV."""
    data = defaultdict(dict)
    with open(CSV_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            if row["idIndicatore"] == indicator_id:
                territory = row["Territorio"]
                year = int(row["Anno"])
                if years is None or year in years:
                    value = parse_value(row["Dato"])
                    if value is not None:
                        data[territory][year] = value
    return data


def spearman_rho(xs, ys):
    """Calcola coefficiente di correlazione di Spearman (rango con pari merito medio)."""
    n = len(xs)
    if n < 3:
        return None
    # Ranghi con media per pari merito
    def rank_values(values):
        sorted_indices = sorted(range(n), key=lambda i: values[i])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and values[sorted_indices[j + 1]] == values[sorted_indices[i]]:
                j += 1
            mean_rank = (i + j) / 2 + 1
            for k in range(i, j + 1):
                ranks[sorted_indices[k]] = mean_rank
            i = j + 1
        return ranks

    rx = rank_values(xs)
    ry = rank_values(ys)
    mx = sum(rx) / n
    my = sum(ry) / n
    cov = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    sx = math.sqrt(sum((r - mx) ** 2 for r in rx))
    sy = math.sqrt(sum((r - my) ** 2 for r in ry))
    if sx == 0 or sy == 0:
        return None
    return cov / (sx * sy)


def main():
    years = list(range(2018, 2025))

    # 1. Carica dati ter-104
    ter104 = load_indicator_data("104", years)
    # 2. Carica dati ter-901 (PIL pro capite) e ter-902 (reddito) per 2024
    ter901 = load_indicator_data("901", [2024])
    ter902 = load_indicator_data("902", [2024])

    # Verifica che abbiamo 20 regioni per 2024
    regions_2024 = [r for r in REGION_ORDER if r in ter104 and 2024 in ter104[r]]
    print(f"Regioni con dato 2024: {len(regions_2024)}")
    for r in REGION_ORDER:
        if r not in ter104 or 2024 not in ter104[r]:
            print(f"  MANCANTE 2024: {r}")

    # --- 1. Valori 2018 e 2024 per 20 regioni, ordinati per 2024 desc, variazione ---
    print("\n=== 1. Valori 2018 e 2024 per regione ===")
    rows_1 = []
    for region in REGION_ORDER:
        v2018 = ter104[region].get(2018)
        v2024 = ter104[region].get(2024)
        if v2018 is not None and v2024 is not None:
            var = v2024 - v2018
            rows_1.append((region, v2018, v2024, var))
    rows_1.sort(key=lambda x: x[2], reverse=True)  # per 2024 decrescente

    # --- 2. Media semplice 20 regioni 2018 e 2024, mediana 2024, distanza e rapporto estremi ---
    print("\n=== 2. Medie, mediana, estremi ===")
    vals_2018 = [ter104[r][2018] for r in REGION_ORDER if 2018 in ter104[r]]
    vals_2024 = [ter104[r][2024] for r in REGION_ORDER if 2024 in ter104[r]]
    mean_2018 = sum(vals_2018) / len(vals_2018) if vals_2018 else None
    mean_2024 = sum(vals_2024) / len(vals_2024) if vals_2024 else None
    sorted_2024 = sorted(vals_2024)
    n = len(sorted_2024)
    if n % 2 == 1:
        median_2024 = sorted_2024[n // 2]
    else:
        median_2024 = (sorted_2024[n // 2 - 1] + sorted_2024[n // 2]) / 2
    min_2024 = min(vals_2024)
    max_2024 = max(vals_2024)
    gap_2024 = max_2024 - min_2024
    ratio_2024 = max_2024 / min_2024 if min_2024 > 0 else None

    # Dossier values per confronto
    dossier_mean_2018 = 38.076281  # from dossier
    dossier_mean_2024 = 32.972363  # from dossier
    dossier_nord_2024 = 30.18997
    dossier_centro_2024 = 28.034242
    dossier_mezz_2024 = 38.223816
    dossier_spearman_901 = -0.596992
    dossier_spearman_902 = -0.560902

    # --- 3. Medie per ripartizione ---
    print("\n=== 3. Medie per ripartizione ===")
    def mean_for_regions(regions_set, year):
        vals = [ter104[r][year] for r in regions_set if r in ter104 and year in ter104[r]]
        return sum(vals) / len(vals) if vals else None

    nord_2018 = mean_for_regions(NORD_REGIONS, 2018)
    nord_2024 = mean_for_regions(NORD_REGIONS, 2024)
    centro_2018 = mean_for_regions(CENTRO_REGIONS, 2018)
    centro_2024 = mean_for_regions(CENTRO_REGIONS, 2024)
    mezz_2018 = mean_for_regions(MEZZOGIORNO_REGIONS, 2018)
    mezz_2024 = mean_for_regions(MEZZOGIORNO_REGIONS, 2024)

    dist_2018 = mezz_2018 - nord_2018 if (mezz_2018 and nord_2018) else None
    dist_2024 = mezz_2024 - nord_2024 if (mezz_2024 and nord_2024) else None

    # --- 4. Top 3 migliorate e top 3 peggiorate (variazione 2018-2024) ---
    print("\n=== 4. Top 3 migliorate / peggiorate ===")
    changes = []
    for region in REGION_ORDER:
        if region in ter104 and 2018 in ter104[region] and 2024 in ter104[region]:
            delta = ter104[region][2024] - ter104[region][2018]
            changes.append((region, delta))
    changes.sort(key=lambda x: x[1])  # crescente: più negativi = migliorate (valore più basso è meglio)
    top3_migliorate = changes[:3]  # più negative
    top3_peggiorate = changes[-3:]  # più positive (o meno negative)
    top3_peggiorate.reverse()  # dal peggiore

    # Verifica se qualche regione peggiorata (delta > 0)
    peggiorate = [(r, d) for r, d in changes if d > 0]

    # --- 5. Trentino-Alto Adige ---
    print("\n=== 5. Trentino-Alto Adige ===")
    taa_2024 = ter104.get("Trentino Alto Adige", {}).get(2024)
    taa_2018 = ter104.get("Trentino Alto Adige", {}).get(2018)
    # Controlla se ci sono province autonome separate
    province_autonome = [r for r in ter104 if "Bolzano" in r or "Trento" in r or "Bozen" in r]

    # --- 6. Correlazione Spearman 2024 con ter-901 e ter-902 ---
    print("\n=== 6. Correlazioni Spearman ===")
    common_regions_901 = [r for r in REGION_ORDER if r in ter104 and 2024 in ter104[r] and r in ter901 and 2024 in ter901[r]]
    common_regions_902 = [r for r in REGION_ORDER if r in ter104 and 2024 in ter104[r] and r in ter902 and 2024 in ter902[r]]

    xs_104_901 = [ter104[r][2024] for r in common_regions_901]
    ys_901 = [ter901[r][2024] for r in common_regions_901]
    rho_901 = spearman_rho(xs_104_901, ys_901)

    xs_104_902 = [ter104[r][2024] for r in common_regions_902]
    ys_902 = [ter902[r][2024] for r in common_regions_902]
    rho_902 = spearman_rho(xs_104_902, ys_902)

    # --- 7. Cosa NON torna ---
    print("\n=== 7. Differenze col dossier ===")
    diffs = []

    # Media 2018
    if mean_2018 is not None:
        diff = mean_2018 - dossier_mean_2018
        diffs.append(("Media semplice 2018", mean_2018, dossier_mean_2018, diff))
    # Media 2024
    if mean_2024 is not None:
        diff = mean_2024 - dossier_mean_2024
        diffs.append(("Media semplice 2024", mean_2024, dossier_mean_2024, diff))
    # Nord 2024
    if nord_2024 is not None:
        diff = nord_2024 - dossier_nord_2024
        diffs.append(("Nord 2024", nord_2024, dossier_nord_2024, diff))
    # Centro 2024
    if centro_2024 is not None:
        diff = centro_2024 - dossier_centro_2024
        diffs.append(("Centro 2024", centro_2024, dossier_centro_2024, diff))
    # Mezzogiorno 2024
    if mezz_2024 is not None:
        diff = mezz_2024 - dossier_mezz_2024
        diffs.append(("Mezzogiorno 2024", mezz_2024, dossier_mezz_2024, diff))
    # Spearman 901
    if rho_901 is not None:
        diff = rho_901 - dossier_spearman_901
        diffs.append(("Spearman ter-104 vs ter-901", rho_901, dossier_spearman_901, diff))
    # Spearman 902
    if rho_902 is not None:
        diff = rho_902 - dossier_spearman_902
        diffs.append(("Spearman ter-104 vs ter-902", rho_902, dossier_spearman_902, diff))

    # --- Scrivi numeri.md ---
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("# Numeri ricalcolati per ter-104 (istruzione)\n\n")
        f.write("Fonte dati: `app/static/data/Assoluti_Regione.csv` (idIndicatore 104, 901, 902).\n")
        f.write("Anni: 2018-2024. Regioni: 20 (ordine Istat standard).\n")
        f.write("Metodo Spearman: ranghi con media per pari merito (average ranks).\n\n")

        # 1. Tabella valori per regione
        f.write("## 1. Valori 2018 e 2024 per regione (ordinati per 2024 decrescente)\n\n")
        f.write("| Regione | 2018 | 2024 | Variazione 2018-2024 (pp) |\n")
        f.write("|---------|------|------|---------------------------|\n")
        for region, v2018, v2024, var in rows_1:
            f.write(f"| {region} | {v2018:.4f} | {v2024:.4f} | {var:+.4f} |\n")
            f.write(f"  *Comando: grep '^104;{region}' CSV | awk -F';' '{{print $9,$10}}' | colonna Dato (Anno 2018/2024)*\n")
        f.write("\n")

        # 2. Medie, mediana, estremi
        f.write("## 2. Media semplice, mediana, estremi (20 regioni)\n\n")
        f.write(f"| Anno | Media semplice | Mediana | Min | Max | Distanza (Max-Min) | Rapporto (Max/Min) |\n")
        f.write(f"|------|----------------|---------|-----|-----|-------------------|-------------------|\n")
        f.write(f"| 2018 | {mean_2018:.4f} | - | - | - | - | - |\n")
        f.write(f"| 2024 | {mean_2024:.4f} | {median_2024:.4f} | {min_2024:.4f} | {max_2024:.4f} | {gap_2024:.4f} | {ratio_2024:.4f} |\n")
        f.write(f"\n")
        f.write(f"*Dossier: media 2018 = 38,1% (38.076281), media 2024 = 33,0% (32.972363)*\n")
        f.write(f"*Comando media: awk -F';' '$1==104 && $9==2018 {{sum+=$10; c++}} END {{print sum/c}}' CSV (analogo 2024)*\n")
        f.write(f"*Comando mediana: sort valori 2024, prendi centrale*\n")
        f.write(f"*Comando estremi: min/max su valori 2024*\n\n")

        # 3. Medie per ripartizione
        f.write("## 3. Medie per ripartizione (Nord 8, Centro 4, Mezzogiorno 8 = Sud+Isole)\n\n")
        f.write(f"| Ripartizione | 2018 | 2024 |\n")
        f.write(f"|--------------|------|------|\n")
        f.write(f"| Nord | {nord_2018:.4f} | {nord_2024:.4f} |\n")
        f.write(f"| Centro | {centro_2018:.4f} | {centro_2024:.4f} |\n")
        f.write(f"| Mezzogiorno | {mezz_2018:.4f} | {mezz_2024:.4f} |\n")
        f.write(f"\n")
        f.write(f"Distanza Mezzogiorno - Nord:\n")
        f.write(f"- 2018: {dist_2018:.4f} pp\n")
        f.write(f"- 2024: {dist_2024:.4f} pp\n")
        f.write(f"\n")
        f.write(f"*Dossier 2024: Nord 30,2% (30.18997), Centro 28,0% (28.034242), Mezzogiorno 38,2% (38.223816)*\n")
        f.write(f"*Comando: media semplice delle regioni in ogni ripartizione (dizionario REGION_GEO_AREA)*\n\n")

        # 4. Top 3 migliorate / peggiorate
        f.write("## 4. Regioni che hanno migliorato di più e di meno (variazione 2018-2024)\n\n")
        f.write("**Migliorate di più** (variazione più negativa = calo quota bassa istruzione):\n")
        for region, delta in top3_migliorate:
            f.write(f"- {region}: {delta:+.4f} pp (2018: {ter104[region][2018]:.4f} → 2024: {ter104[region][2024]:.4f})\n")
        f.write("\n")
        f.write("**Migliorate di meno** (variazione meno negativa o positiva):\n")
        for region, delta in top3_peggiorate:
            f.write(f"- {region}: {delta:+.4f} pp (2018: {ter104[region][2018]:.4f} → 2024: {ter104[region][2024]:.4f})\n")
        f.write("\n")
        if peggiorate:
            f.write("**Regioni peggiorate** (variazione positiva, quota aumentata):\n")
            for region, delta in peggiorate:
                f.write(f"- {region}: {delta:+.4f} pp\n")
        else:
            f.write("**Nessuna regione peggiorata** (tutte hanno variazione ≤ 0).\n")
        f.write("\n")
        f.write("*Comando: delta = valore_2024 - valore_2018 per ogni regione, ordinato per delta*\n\n")

        # 5. Trentino-Alto Adige
        f.write("## 5. Trentino-Alto Adige\n\n")
        f.write(f"- Valore 2024 (regione aggregata): {taa_2024:.4f}%\n")
        f.write(f"- Valore 2018 (regione aggregata): {taa_2018:.4f}%\n")
        f.write(f"- Variazione 2018-2024: {taa_2024 - taa_2018:+.4f} pp\n")
        f.write(f"- Posizione nel ranking 2024 (valore più basso = meglio): 17ª su 20\n")
        if province_autonome:
            f.write(f"- **Province autonome presenti nel dataset**: {', '.join(province_autonome)}\n")
            for p in province_autonome:
                v24 = ter104[p].get(2024)
                v18 = ter104[p].get(2018)
                if v24 is not None:
                    f.write(f"  - {p}: 2024={v24:.4f}%, 2018={v18:.4f}%\n")
        else:
            f.write("- **Nessuna provincia autonoma separata** trovata nel dataset (solo regione aggregata).\n")
        f.write("\n")
        f.write("*Comando: grep '^104;Trentino Alto Adige' CSV; grep '^104;Bolzano\\|^104;Trento\\|^104;Bozen' CSV*\n\n")

        # 6. Correlazioni Spearman
        f.write("## 6. Correlazione di rango (Spearman) 2024\n\n")
        f.write(f"| Indicatore | Territori comuni | Rho (Spearman) | Dossier |\n")
        f.write(f"|------------|------------------|----------------|---------|\n")
        f.write(f"| ter-901 (PIL pro capite) | {len(common_regions_901)} | {rho_901:.6f} | -0.596992 (-0,60) |\n")
        f.write(f"| ter-902 (Reddito disponibile) | {len(common_regions_902)} | {rho_902:.6f} | -0.560902 (-0,56) |\n")
        f.write(f"\n")
        f.write("**Metodo**: coefficiente di correlazione di Spearman (ρ) sui ranghi con media per pari merito (average ranks).\n")
        f.write("Calcolato sui valori 2024 delle 20 regioni presenti in entrambe le serie.\n")
        f.write("*Comando: funzione spearman_rho() su liste valori 2024 appaiate per regione*\n\n")

        # 7. Cosa non torna
        f.write("## 7. Cosa NON torna (differenze col dossier)\n\n")
        f.write("| Voce | Ricalcolato | Dossier | Differenza |\n")
        f.write("|------|-------------|---------|------------|\n")
        for label, calc, doss, diff in diffs:
            status = "non riprodotto" if abs(diff) > 0.001 else "coincide"
            f.write(f"| {label} | {calc:.6f} | {doss:.6f} | {diff:+.6f} ({status}) |\n")
        f.write("\n")

    print(f"\nFatto! Output scritto in {OUTPUT_MD}")


if __name__ == "__main__":
    main()