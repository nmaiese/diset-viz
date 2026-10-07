# Numeri e pre-registrazione

## Fonti del calcolo e separazione dal sondaggio

Sondaggio Astra (ipotesi, non prova): H1 richiede che il segno opposto tra furti in abitazione e rischio percepito compaia su 2023-2025, sopravviva togliendo Toscana e Campania e si controlli anche 2019-2025. H2 propone che borseggi, rapine o degrado divergano dai furti nei territori H1. Matrici ricostruite dal CSV Istat locale `app/static/data/Assoluti_BES_Regione.csv` con chiavi `idIndicatore`, `Territorio`, `Anno`, `Livello/Variazione`, `Dato`, e ricalcolo di variazioni, ranghi e medie via le matrici regionali di `app.indicator_view.build_indicator_view`. Confronto puntuale CSV/view model su tutti i sei indicatori core, 20 regioni, anni 2019, 2023 e 2025: 360/360 celle coincidenti entro <1e-9. I valori di Toscana e Campania sono quindi verificati anche direttamente nel CSV BES.

Unità: furti per 1.000 famiglie; borseggi e rapine per 1.000 abitanti; rischio, degrado e sicurezza percepita in percentuale. Sono popolazioni e unità diverse. I livelli BES dei furti/borseggi/rapine stimano vittime e correggono il sommerso secondo la definizione Istat. Non confrontare i loro livelli direttamente con denunce provinciali per 100.000 residenti.

## Formula e chiavi

- Universo: le 20 chiavi di regione condivise dalle matrici per ciascun anno richiesto. Trentino-Alto Adige è una singola unità regionale. N=20, salvo rimozioni dichiarate.
- Variazione: `x[regione, anno_finale] - x[regione, anno_iniziale]`, senza ponderazione.
- Divergente H1: `delta_furti < 0 AND delta_rischio > 0`. Esiti esattamente zero non contano come aumento o calo.
- Spearman: Pearson sui ranghi medi in presenza di ex aequo, formula `corr(rank(x), rank(y))`. Non sono p-value, non sono test inferenziali, non correggono selezione multipla.
- Medie riportate: media aritmetica semplice delle 20 variazioni o valori regionali, non media nazionale ponderata.

## H1, 2023-2025

N=20. Divergenza in **8/20**: Emilia-Romagna, Friuli-Venezia Giulia, Lazio, Molise, Piemonte, Sardegna, Toscana, Umbria. Media semplice furti: 7,38 a 6,86 per 1.000 famiglie, delta -0,52. Media semplice rischio: 18,83% a 22,61%, delta +3,78 punti. Sono medie regionali non ponderate, non valori italiani.

Spearman tra livelli 2025 furti e rischio: rho=0,635, N=20. Spearman tra le variazioni 2023-2025: rho=-0,014, N=20. Associazione dei livelli territoriali non descrive l’associazione tra i cambiamenti.

Esclusione pre-registrata Toscana e Campania: N=18, divergenze 7/18, Spearman tra variazioni rho=0,100. Il segno opposto resta presente, ma rho cambia e non è una misura di “tenuta” statistica. Valori CSV: Toscana furti 14,8→12,6, rischio 20,5→27,8; Campania furti 6,2→5,5, rischio 39,0→38,0. Le unità restano diverse.

| Regione | Furti 2023 | Furti 2025 | Δ furti | Rischio 2023 | Rischio 2025 | Δ rischio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Abruzzo | 7.7 | 7.9 | +0.2 | 18.4 | 19.2 | +0.8 |
| Basilicata | 3.2 | 2.9 | -0.3 | 14.0 | 11.3 | -2.7 |
| Calabria | 3.2 | 2.2 | -1.0 | 10.7 | 10.3 | -0.4 |
| Campania | 6.2 | 5.5 | -0.7 | 39.0 | 38.0 | -1.0 |
| Emilia-Romagna | 10.1 | 9.6 | -0.5 | 21.4 | 25.5 | +4.1 |
| Friuli-Venezia Giulia | 8.9 | 8.2 | -0.7 | 13.3 | 20.3 | +7.0 |
| Lazio | 9.9 | 7.0 | -2.9 | 32.8 | 35.8 | +3.0 |
| Liguria | 5.3 | 5.3 | +0.0 | 17.8 | 22.6 | +4.8 |
| Lombardia | 9.7 | 9.8 | +0.1 | 25.8 | 32.8 | +7.0 |
| Marche | 7.5 | 8.0 | +0.5 | 14.5 | 18.7 | +4.2 |
| Molise | 6.5 | 4.1 | -2.4 | 11.5 | 22.2 | +10.7 |
| Piemonte | 7.5 | 7.4 | -0.1 | 19.7 | 25.8 | +6.1 |
| Puglia | 5.9 | 5.4 | -0.5 | 25.3 | 24.6 | -0.7 |
| Sardegna | 3.0 | 2.7 | -0.3 | 10.3 | 12.9 | +2.6 |
| Sicilia | 4.9 | 3.5 | -1.4 | 22.4 | 19.0 | -3.4 |
| Toscana | 14.8 | 12.6 | -2.2 | 20.5 | 27.8 | +7.3 |
| Trentino Alto Adige | 5.7 | 6.8 | +1.1 | 12.0 | 18.8 | +6.8 |
| Umbria | 12.6 | 11.5 | -1.1 | 23.1 | 32.5 | +9.4 |
| Valle d'Aosta | 4.1 | 5.1 | +1.0 | 4.5 | 7.9 | +3.4 |
| Veneto | 10.9 | 11.7 | +0.8 | 19.6 | 26.2 | +6.6 |

## H1 finestra alternativa 2019-2025

N=20. Divergenza in 11/20 regioni: Campania, Lazio, Liguria, Lombardia, Molise, Piemonte, Puglia, Sardegna, Toscana, Trentino Alto Adige, Umbria. Spearman tra variazioni furti/rischio rho=0.100. Senza Toscana e Campania: N=18, divergenza 9/18, rho=0.139. Media semplice 2019→2025 furti: 9.380→6.860, Δ=-2.520; rischio: 22.095→22.610, Δ=+0.515. La Toscana passa da 18,1 a 12,6 furti e da 25,9% a 27,8% rischio. La Campania da 7,0 a 5,5 furti e da 36,4% a 38,0% rischio: l’esito contrario del controllo 2023-25 non resta tale nella finestra lunga.

| Regione | Furti 2019 | Furti 2025 | Δ furti | Rischio 2019 | Rischio 2025 | Δ rischio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Abruzzo | 9.3 | 7.9 | -1.4 | 21.6 | 19.2 | -2.4 |
| Basilicata | 4.0 | 2.9 | -1.1 | 12.8 | 11.3 | -1.5 |
| Calabria | 5.5 | 2.2 | -3.3 | 19.0 | 10.3 | -8.7 |
| Campania | 7.0 | 5.5 | -1.5 | 36.4 | 38.0 | +1.6 |
| Emilia-Romagna | 14.0 | 9.6 | -4.4 | 26.6 | 25.5 | -1.1 |
| Friuli-Venezia Giulia | 8.2 | 8.2 | +0.0 | 15.0 | 20.3 | +5.3 |
| Lazio | 10.3 | 7.0 | -3.3 | 35.1 | 35.8 | +0.7 |
| Liguria | 8.6 | 5.3 | -3.3 | 21.3 | 22.6 | +1.3 |
| Lombardia | 11.1 | 9.8 | -1.3 | 26.4 | 32.8 | +6.4 |
| Marche | 10.5 | 8.0 | -2.5 | 26.5 | 18.7 | -7.8 |
| Molise | 6.5 | 4.1 | -2.4 | 15.6 | 22.2 | +6.6 |
| Piemonte | 11.6 | 7.4 | -4.2 | 23.2 | 25.8 | +2.6 |
| Puglia | 8.9 | 5.4 | -3.5 | 23.3 | 24.6 | +1.3 |
| Sardegna | 5.3 | 2.7 | -2.6 | 12.6 | 12.9 | +0.3 |
| Sicilia | 7.5 | 3.5 | -4.0 | 23.8 | 19.0 | -4.8 |
| Toscana | 18.1 | 12.6 | -5.5 | 25.9 | 27.8 | +1.9 |
| Trentino Alto Adige | 8.9 | 6.8 | -2.1 | 12.4 | 18.8 | +6.4 |
| Umbria | 16.4 | 11.5 | -4.9 | 29.9 | 32.5 | +2.6 |
| Valle d'Aosta | 4.5 | 5.1 | +0.6 | 11.9 | 7.9 | -4.0 |
| Veneto | 11.4 | 11.7 | +0.3 | 22.6 | 26.2 | +3.6 |

## H2, misure incrociate e controlli contrari

La matrice sotto incrocia sei misure su tutte le 20 regioni: furti, rischio percepito, rapine, borseggi, degrado e percezione di sicurezza. Le ultime quattro rispondono al controllo H2. Non sono popolazioni o unità omogenee. Variazioni indicate in unità originali: pp per percentuali, valori per 1.000 per reati.

H2 selezionando i soli otto territori divergenti 2023-25: degrado cresce in 8/8 (+1,64 punti di media semplice), percezione di sicurezza diminuisce in 8/8 (-6,68 punti). Il controllo contrario è il gruppo non divergente: degrado cresce già in 10/12 e sicurezza cala in 11/12. Quindi il segnale percettivo non è specifico delle otto regioni, e non spiega il motivo del divario. Rapine aumentano in 4/8, borseggi aumentano in 4/8: supporto misto, da conservare. Intero campione: degrado sale in 18/20, sicurezza scende in 19/20, rapine salgono in 6/20 e borseggi in 6/20.

| Regione | Furti 23→25 | Rischio 23→25 | Rapine 23→25 | Borseggi 23→25 | Degrado 23→25 | Sicurezza 23→25 | H1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Abruzzo | +0.2 | +0.8 | +0.0 | -0.2 | +0.2 | -3.8 | no |
| Basilicata | -0.3 | -2.7 | +0.0 | -0.2 | +1.2 | -6.1 | no |
| Calabria | -1.0 | -0.4 | +0.0 | -0.1 | +0.4 | -7.7 | no |
| Campania | -0.7 | -1.0 | -0.4 | -0.3 | +2.4 | +0.5 | no |
| Emilia-Romagna | -0.5 | +4.1 | +0.2 | +0.2 | +4.0 | -5.9 | sì |
| Friuli-Venezia Giulia | -0.7 | +7.0 | +0.1 | +0.1 | +1.4 | -9.7 | sì |
| Lazio | -2.9 | +3.0 | -0.1 | -2.1 | +0.7 | -4.4 | sì |
| Liguria | +0.0 | +4.8 | -0.3 | +0.0 | +1.1 | -7.4 | no |
| Lombardia | +0.1 | +7.0 | -0.1 | -1.1 | +1.6 | -11.4 | no |
| Marche | +0.5 | +4.2 | +0.0 | -0.2 | +0.0 | -2.3 | no |
| Molise | -2.4 | +10.7 | +0.0 | +0.1 | +2.0 | -6.4 | sì |
| Piemonte | -0.1 | +6.1 | -0.2 | -0.7 | +1.2 | -5.9 | sì |
| Puglia | -0.5 | -0.7 | +0.0 | -0.2 | +0.6 | -5.0 | no |
| Sardegna | -0.3 | +2.6 | +0.1 | -0.1 | +1.0 | -3.4 | sì |
| Sicilia | -1.4 | -3.4 | -0.1 | -0.5 | -0.3 | -2.1 | no |
| Toscana | -2.2 | +7.3 | -0.2 | +2.0 | +2.1 | -8.5 | sì |
| Trentino Alto Adige | +1.1 | +6.8 | +0.1 | -0.3 | +1.5 | -4.2 | no |
| Umbria | -1.1 | +9.4 | +0.2 | -0.4 | +0.7 | -9.2 | sì |
| Valle d'Aosta | +1.0 | +3.4 | +0.1 | +0.1 | +2.1 | -5.6 | no |
| Veneto | +0.8 | +6.6 | -0.1 | +0.2 | +2.0 | -7.8 | no |


Rapine: media semplice regionale 0,810→0,775 per 1.000 abitanti (Δ -0,035) nel 2023-25; sale in 6/20. Borseggi: calano in media da 3.295 a 3.110 per 1.000 abitanti (Δ -0.185), sale in 6/20. Nel 2019-25 media rapine 0,680→0,775 per 1.000 abitanti (aumento), perciò non si può estendere la conclusione “la criminalità diminuisce” al periodo lungo.

| Coppia di variazioni | N | Spearman | Lettura descrittiva |
| --- | ---: | ---: | --- |
| Δ furti vs Δ rischio (2023-2025) | 20 | -0.014 | Esplorativa, descrittiva; correlazione tra cambiamenti regionali. |
| Δ furti vs Δ rapine (2023-2025) | 20 | +0.166 | Esplorativa, descrittiva; correlazione tra cambiamenti regionali. |
| Δ furti vs Δ borseggi (2023-2025) | 20 | +0.074 | Esplorativa, descrittiva; correlazione tra cambiamenti regionali. |
| Δ furti vs Δ degrado (2023-2025) | 20 | +0.086 | Esplorativa, descrittiva; correlazione tra cambiamenti regionali. |
| Δ furti vs Δ sicurezza (2023-2025) | 20 | +0.144 | Esplorativa, descrittiva; correlazione tra cambiamenti regionali. |


## Controllo serie percettive sovrapposte

`ter-43` e `bes-07SIC022` hanno definizione pubblicata molto simile e sovrappongono il periodo 2018-2024 per tutte le 20 regioni (140 coppie), ma i valori non sono identici: scarto assoluto massimo annuo tra 0,23 e 0,52 punti percentuali. Correlazione di Spearman sulle 140 coppie regione-anno = 0 (ρ=1.000); le serie possono condividere rilevazione o input ma non si può provare qui identità di processo. Non contarle come due conferme indipendenti. I valori sono distinti, quindi tenerle separate nel censimento.

`ims-MULTI_ZONA_CRIMINALITA` ha denominazione “Famiglie che lamentano criminalità nella zona di residenza”, copertura 17, 16, 14, 16, 14, 16, 18, 17 regioni dal 2018 al 2025. Toscana e Campania sono disponibili ma i livelli sono molto diversi dal rischio Bes: per esempio 2025 Toscana 11,2%, Campania 15,5%, contro Bes 27,8% e 38,0%. È una misura distinta, con missingness e formulazione diverse, quindi non prova indipendente né sostituto dell’indicatore BES.

## Fuori estremi, limiti e stato

Esclusione Toscana/Campania lascia 7 divergenze su 18 nel 2023-25 e 9 su 18 nel 2019-25. L’esito non dipende solo dai due casi evidenziati. Non è un test campionario né una prova che la percezione individuale non segua gli eventi: dati regionali aggregati, due misure soggettive campionarie/di popolazione e denominatori diversi.

Limiti non verificati: errore campionario e intervalli di confidenza a livello regionale, differenze di composizione demografica, spiegazioni causali, rapporto individuale tra esposizione e percezione, verifica diretta della tavola sorgente scaricata nell’appendice online 2026 per tutti i record. Il file Istat ufficiale dell’appendice apribile online è archivio ZIP e lo strumento browser non ha potuto leggerne il contenuto; il CSV locale dell’app è stato usato e il controllo richiesto Toscana/Campania è riproducibile al suo interno.
