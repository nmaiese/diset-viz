# Monitoraggio delle fonti ufficiali

## Fonti integrate e controllate automaticamente

| Fonte | Frequenza attesa | Uso | Processo |
|---|---|---|---|
| [Istat, Indicatori territoriali per le politiche di sviluppo](https://www.istat.it/sistema-informativo-6/banca-dati-territoriale-per-le-politiche-di-sviluppo/) | mensile, circa il giorno 20 | atlante, profili regionali, quiz | `scripts/refresh_official_data.py` e `scripts/update_data.py` |
| [Istat, indicatori BES](https://www.istat.it/statistiche-per-temi/focus/benessere-e-sostenibilita/la-misurazione-del-benessere-bes/gli-indicatori-del-bes/) | aggiornamento intermedio e rapporto annuale | qualità della vita regionale, schede BES, quiz confronto e ordine | `scripts/refresh_official_data.py` e `scripts/update_bes_regions.py` |
| [Istat, BES dei Territori](https://www.istat.it/statistiche-per-temi/focus/benessere-e-sostenibilita/la-misurazione-del-benessere-bes/il-bes-dei-territori/) | annuale, storicamente in estate | qualità della vita provinciale | client SDMX cache-first e pipeline provinciale |

Il workflow `.github/workflows/data-refresh.yml` controlla ogni lunedì gli hash
dei primi due artefatti. Se non cambiano, non scrive file. Se cambiano, rigenera
i dataset, aggiorna i report, esegue test e build e apre una pull request.

## Watchlist ufficiale

Queste fonti vanno monitorate perché possono anticipare o arricchire il backbone,
ma non entrano automaticamente nello scoring finché non esiste una serie
relativa, omogenea e confrontabile su almeno 19 regioni.

- [Istat, indicatori demografici](https://www.istat.it/comunicato-stampa/indicatori-demografici-anno-2025/), diffusione tipica a marzo. Il BES e il backbone territoriale restano le vie preferite per l'integrazione.
- [INVALSI Open](https://invalsiopen.it/dati-rilevazione-invalsi-2025/), diffusione tipica a luglio. Le due misure regionali 2025 sulle competenze non adeguate sono già acquisite tramite il BES nazionale.
- [InfoCamere, Movimprese](https://www.infocamere.it/principali-soluzioni/movimprese.html), trimestrale. Dal primo trimestre 2026 usa ATECO 2025: i confronti settoriali richiedono un controllo di discontinuità.
- [Terna, dati statistici](https://dati.terna.it/fabbisogno/dati-statistici), mensile e annuale. Consumi assoluti e produzione non entrano nello score senza un denominatore coerente.
- [Istat, A misura di Comune](https://www.istat.it/statistica-sperimentale/aggiornamento-degli-indicatori-del-sistema-informativo-a-misura-di-comune/), aggiornamento periodico. È prioritario per future estensioni comunali o provinciali, non per sostituire serie regionali già esatte.
- Infratel, AGCOM e ISPRA/SNPA restano fonti verticali per banda, ambiente e suolo. Prima dell'integrazione servono aggregazione territoriale riproducibile, licenza verificata e match di definizione.

## Regole di promozione

1. `exact`: stessa definizione, unità, popolazione, frequenza e territorio. Può aggiornare una serie esistente.
2. `compatible`: utile nelle schede, ma richiede revisione prima del punteggio.
3. `proxy`: resta un nuovo indicatore descrittivo e non sostituisce mai l'originale.
4. Una serie entra nel punteggio regionale solo con anno almeno 2025, copertura almeno 80%, categoria valida e direzione curata.
5. I dati assoluti non entrano nello scoring se dimensione demografica o economica del territorio ne altera direttamente il valore.
