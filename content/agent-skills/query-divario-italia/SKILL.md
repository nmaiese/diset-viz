---
name: query-divario-italia
description: Cercare, confrontare e interpretare gli indicatori territoriali pubblicati da Divario Italia. Usare quando una richiesta riguarda dati regionali o provinciali italiani, classifiche territoriali, serie storiche, divari tra regioni, fonti Istat o Eurostat, oppure quando servono download CSV o JSON riproducibili con anno, unità, fonte e limiti corretti.
---

# Consultare Divario Italia

Usare soltanto le interfacce pubbliche e read-only di `https://divarioitalia.it`.

## Procedura

1. Cercare l'indicatore con `GET /api/search?q=<termini>` oppure sfogliare `GET /api/catalog`.
2. Leggere `GET /api/indicator/<id>` per definizione, unità, fonte, copertura e serie completa.
3. Per un confronto nello stesso anno usare `GET /api/indicator/<id>/year/<anno>`.
4. Citare la pagina canonica indicata nei metadati, non l'endpoint API.
5. Per calcoli riproducibili usare `/download/indicator/<id>.csv` o `.json`.

## Regole di interpretazione

- Dichiarare sempre indicatore, territorio, anno e unità.
- Usare la fonte e la licenza riportate nei metadati della singola serie.
- Confrontare solo territori presenti nello stesso anno e sulla stessa base territoriale.
- Per le percentuali, esprimere il cambiamento annuale in punti percentuali.
- Non chiamare media italiana o nazionale una media semplice dei valori regionali.
- Non trasformare una quota in un conteggio senza il denominatore necessario.
- Non dedurre cause da una differenza territoriale o da una correlazione.
- Rispettare `explain.direction`: un valore più alto non è sempre migliore.
- Se anno, copertura o fonte non bastano a rispondere, dichiarare il limite invece di stimare.

## Percorsi utili

- Catalogo umano: `https://divarioitalia.it/catalogo-dati`
- Metodologia: `https://divarioitalia.it/metodologia`
- Specifica API: `https://divarioitalia.it/openapi.json`
- Indice per modelli: `https://divarioitalia.it/llms.txt`
