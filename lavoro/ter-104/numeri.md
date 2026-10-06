# Numeri ricalcolati per ter-104 (istruzione)

Fonte dati: `app/static/data/Assoluti_Regione.csv` (idIndicatore 104, 901, 902).
Anni: 2018-2024. Regioni: 20 (ordine Istat standard).
Metodo Spearman: ranghi con media per pari merito (average ranks).

## 1. Valori 2018 e 2024 per regione (ordinati per 2024 decrescente)

| Regione | 2018 | 2024 | Variazione 2018-2024 (pp) |
|---------|------|------|---------------------------|
| Sicilia | 48.8954 | 44.1271 | -4.7684 |
  *Comando: grep '^104;Sicilia' CSV | awk -F';' '{print $9,$10}' | colonna Dato (Anno 2018/2024)*
| Sardegna | 49.1520 | 43.6810 | -5.4710 |
  *Comando: grep '^104;Sardegna' CSV | awk -F';' '{print $9,$10}' | colonna Dato (Anno 2018/2024)*
| Puglia | 50.0351 | 43.1714 | -6.8636 |
  *Comando: grep '^104;Puglia' CSV | awk -F';' '{print $9,$10}' | colonna Dato (Anno 2018/2024)*
| Campania | 47.1636 | 41.7161 | -5.4475 |
  *Comando: grep '^104;Campania' CSV | awk -F';' '{print $9,$10}' | colonna Dato (Anno 2018/2024)*
| Calabria | 45.9449 | 38.7224 | -7.2225 |
  *Comando: grep '^104;Calabria' CSV | awk -F';' '{print $9,$10}' | colonna Dato (Anno 2018/2024)*
| Valle d'Aosta | 39.1893 | 37.0490 | -2.1404 |
  *Comando: grep '^104;Valle d'Aosta' CSV | awk -F';' '{print $9,$10}' | colonna Dato (Anno 2018/2024)*
| Basilicata | 38.7251 | 34.1977 | -4.5274 |
  *Comando: grep '^104;Basilicata' CSV | awk -F';' '{print $9,$10}' | colonna Dato (Anno 2018/2024)*
| Piemonte | 37.4444 | 32.8003 | -4.6441 |
  *Comando: grep '^104;Piemonte' CSV | awk -F';' '{print $9,$10}' | colonna Dato (Anno 2018/2024)*
| Toscana | 35.2536 | 32.7278 | -2.5258 |
  *Comando: grep '^104;Toscana' CSV | awk -F';' '{print $9,$10}' | colonna Dato (Anno 2018/2024)*
| Molise | 38.2736 | 31.4061 | -6.8676 |
  *Comando: grep '^104;Molise' CSV | awk -F';' '{print $9,$10}' | colonna Dato (Anno 2018/2024)*
| Lombardia | 35.2675 | 30.8930 | -4.3745 |
  *Comando: grep '^104;Lombardia' CSV | awk -F';' '{print $9,$10}' | colonna Dato (Anno 2018/2024)*
| Veneto | 35.7371 | 30.7699 | -4.9672 |
  *Comando: grep '^104;Veneto' CSV | awk -F';' '{print $9,$10}' | colonna Dato (Anno 2018/2024)*
| Marche | 35.2774 | 29.9556 | -5.3217 |
  *Comando: grep '^104;Marche' CSV | awk -F';' '{print $9,$10}' | colonna Dato (Anno 2018/2024)*
| Liguria | 33.2406 | 28.9171 | -4.3235 |
  *Comando: grep '^104;Liguria' CSV | awk -F';' '{print $9,$10}' | colonna Dato (Anno 2018/2024)*
| Abruzzo | 33.4328 | 28.7687 | -4.6641 |
  *Comando: grep '^104;Abruzzo' CSV | awk -F';' '{print $9,$10}' | colonna Dato (Anno 2018/2024)*
| Emilia-Romagna | 32.1970 | 28.5692 | -3.6278 |
  *Comando: grep '^104;Emilia-Romagna' CSV | awk -F';' '{print $9,$10}' | colonna Dato (Anno 2018/2024)*
| Trentino Alto Adige | 32.5244 | 27.1058 | -5.4186 |
  *Comando: grep '^104;Trentino Alto Adige' CSV | awk -F';' '{print $9,$10}' | colonna Dato (Anno 2018/2024)*
| Friuli-Venezia Giulia | 31.6811 | 25.4155 | -6.2656 |
  *Comando: grep '^104;Friuli-Venezia Giulia' CSV | awk -F';' '{print $9,$10}' | colonna Dato (Anno 2018/2024)*
| Lazio | 30.2793 | 25.1729 | -5.1064 |
  *Comando: grep '^104;Lazio' CSV | awk -F';' '{print $9,$10}' | colonna Dato (Anno 2018/2024)*
| Umbria | 31.8112 | 24.2806 | -7.5306 |
  *Comando: grep '^104;Umbria' CSV | awk -F';' '{print $9,$10}' | colonna Dato (Anno 2018/2024)*

## 2. Media semplice, mediana, estremi (20 regioni)

| Anno | Media semplice | Mediana | Min | Max | Distanza (Max-Min) | Rapporto (Max/Min) |
|------|----------------|---------|-----|-----|-------------------|-------------------|
| 2018 | 38.0763 | - | - | - | - | - |
| 2024 | 32.9724 | 31.1495 | 24.2806 | 44.1271 | 19.8465 | 1.8174 |

*Dossier: media 2018 = 38,1% (38.076281), media 2024 = 33,0% (32.972363)*
*Comando media: awk -F';' '$1==104 && $9==2018 {sum+=$10; c++} END {print sum/c}' CSV (analogo 2024)*
*Comando mediana: sort valori 2024, prendi centrale*
*Comando estremi: min/max su valori 2024*

## 3. Medie per ripartizione (Nord 8, Centro 4, Mezzogiorno 8 = Sud+Isole)

| Ripartizione | 2018 | 2024 |
|--------------|------|------|
| Nord | 34.6602 | 30.1900 |
| Centro | 33.1554 | 28.0342 |
| Mezzogiorno | 43.9528 | 38.2238 |

Distanza Mezzogiorno - Nord:
- 2018: 9.2927 pp
- 2024: 8.0338 pp

*Dossier 2024: Nord 30,2% (30.18997), Centro 28,0% (28.034242), Mezzogiorno 38,2% (38.223816)*
*Comando: media semplice delle regioni in ogni ripartizione (dizionario REGION_GEO_AREA)*

## 4. Regioni che hanno migliorato di più e di meno (variazione 2018-2024)

**Migliorate di più** (variazione più negativa = calo quota bassa istruzione):
- Umbria: -7.5306 pp (2018: 31.8112 → 2024: 24.2806)
- Calabria: -7.2225 pp (2018: 45.9449 → 2024: 38.7224)
- Molise: -6.8676 pp (2018: 38.2736 → 2024: 31.4061)

**Migliorate di meno** (variazione meno negativa o positiva):
- Valle d'Aosta: -2.1404 pp (2018: 39.1893 → 2024: 37.0490)
- Toscana: -2.5258 pp (2018: 35.2536 → 2024: 32.7278)
- Emilia-Romagna: -3.6278 pp (2018: 32.1970 → 2024: 28.5692)

**Nessuna regione peggiorata** (tutte hanno variazione ≤ 0).

*Comando: delta = valore_2024 - valore_2018 per ogni regione, ordinato per delta*

## 5. Trentino-Alto Adige

- Valore 2024 (regione aggregata): 27.1058%
- Valore 2018 (regione aggregata): 32.5244%
- Variazione 2018-2024: -5.4186 pp
- Posizione nel ranking 2024 (valore più basso = meglio): 17ª su 20
- **Nessuna provincia autonoma separata** trovata nel dataset (solo regione aggregata).

*Comando: grep '^104;Trentino Alto Adige' CSV; grep '^104;Bolzano\|^104;Trento\|^104;Bozen' CSV*

## 6. Correlazione di rango (Spearman) 2024

| Indicatore | Territori comuni | Rho (Spearman) | Dossier |
|------------|------------------|----------------|---------|
| ter-901 (PIL pro capite) | 20 | -0.596992 | -0.596992 (-0,60) |
| ter-902 (Reddito disponibile) | 20 | -0.560902 | -0.560902 (-0,56) |

**Metodo**: coefficiente di correlazione di Spearman (ρ) sui ranghi con media per pari merito (average ranks).
Calcolato sui valori 2024 delle 20 regioni presenti in entrambe le serie.
*Comando: funzione spearman_rho() su liste valori 2024 appaiate per regione*

## 7. Cosa NON torna (differenze col dossier)

| Voce | Ricalcolato | Dossier | Differenza |
|------|-------------|---------|------------|
| Media semplice 2018 | 38.076281 | 38.076281 | +0.000000 (coincide) |
| Media semplice 2024 | 32.972363 | 32.972363 | -0.000000 (coincide) |
| Nord 2024 | 30.189970 | 30.189970 | +0.000000 (coincide) |
| Centro 2024 | 28.034242 | 28.034242 | -0.000000 (coincide) |
| Mezzogiorno 2024 | 38.223816 | 38.223816 | -0.000000 (coincide) |
| Spearman ter-104 vs ter-901 | -0.596992 | -0.596992 | -0.000000 (coincide) |
| Spearman ter-104 vs ter-902 | -0.560902 | -0.560902 | -0.000000 (coincide) |

