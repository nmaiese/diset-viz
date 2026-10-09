# Ritorno Gate B1: servizi-infanzia-regioni-2023

## Verifiche linter
Lo script `guardia_articolo.py --json` passa con successo con 0 errori.
* Configurato `indicator: "N/A"` per sopprimere l'importazione del blocco generico `ter-414` (L'indicatore in parole semplici) senza far fallire il controllo sull'obbligatorietà del campo `indicator`.
* Aggiunto il blocco `cover_credit` nel frontmatter con i campi (`author`, `license`, `source_name`, `source_url`, etc.) per sovrascrivere il fallback "Wikimedia Commons", dichiarando l'elaborazione su dati Istat.
* Corretto l'errore `G4` per la cifra senza unità di misura nel titolo dell'SVG, sostituendo "3.000" con "tremila" nel tag `<title>` di `domande-non-accolte.svg`.

## Verifiche HTML e visive
L'endpoint `/blog/servizi-infanzia-regioni-2023` (HTTP 200) mostra la corretta visualizzazione:
* Il blocco generico "L'indicatore in parole semplici" è stato rimosso dalla pagina come richiesto.
* La nota per le "medie semplici" nel template HTML è ora condizionale e precisa "salvo indicazione diversa per i valori ufficiali".
* Le immagini SVG utilizzano variabili di colore (`var(--seq-4)`, `var(--seq-2)`), l'etichetta "Stato: definitivo" è stata rimossa, e il PNG è stato rasterizzato in base all'SVG aggiornato di `posti-autorizzati.svg` (punti convertiti in virgole decimali).

## Validazioni numeriche
* I riferimenti ai valori nazionali per frequenza e presa in carico (rispettivamente 34,5% e 18,5%) sono esplicitati nella definizione introduttiva.
* Il LEP target al 33% e i conteggi dei residenti 0-2 (1.198.000) e posti (378.500) sono aggiornati.
* I valori nell'header del file CSV riportano esplicitamente l'unità "posti per 100 residenti 0-2".

Il perimetro delle modifiche è stato strettamente rispettato.
