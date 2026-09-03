# Memoria dello skeptical editor

## Contratto

Questa memoria serve a riconoscere difetti editoriali ricorrenti senza
trasformare una vecchia decisione in un verdetto automatico.

Conservare soltanto:

- errori osservati in più run
- criteri stabili per distinguere gravità alta, media e bassa
- falsi positivi già verificati
- correzioni minime che hanno risolto un'intera classe di problemi
- limiti metodologici ricorrenti nelle famiglie di indicatori

Non conservare gusti stilistici, rilievi isolati, testo di singole bozze,
giudizi su persone e agenti, segreti, token o dati personali.

## Pattern editoriali

```yaml
- categoria: limite_metodologico_ricorrente
  apprendimento: >-
    Nel dossier il blocco dinamica.nazionale non è un aggregato nazionale: è
    costruito sulla media semplice delle regioni, con lo stesso peso per la
    Valle d'Aosta e per la Lombardia. Un articolo che scrive "in Italia" o "il
    dato nazionale" accanto a quel numero sbaglia quantità, e nessuna guardia
    lo ferma perché il numero è davvero nel dossier. Vale anche per le medie di
    macroarea. Il rilievo va aperto sulla frase che chiama nazionale quel
    valore, e la riparazione è etichettarlo come media delle regioni.
  evidenza: >-
    lab/dossier.py:250-255, medie_annue costruito con statistics.fmean sui
    valori regionali dell'anno, e nazionale derivato da quello. Confermato in
    codice, non solo per coincidenza numerica sul dossier di ter-167.
  verified_on: 2026-09-03
  recheck_after: 2027-03-31
  ambito: tutti i dossier a livello regione
  limiti: >-
    È una regola su come si nomina il numero, non un difetto del dossier, che
    quel campo lo calcola per quello che è. Il rischio opposto va sorvegliato:
    ripetere l'etichetta "media semplice" a ogni occorrenza diventa rumore, e
    una volta per articolo basta.
```

Formato di una voce:

```yaml
- categoria:
  apprendimento:
  evidenza:
  verified_on: YYYY-MM-DD
  recheck_after: YYYY-MM-DD
  ambito:
  limiti:
```

Ogni pattern va verificato contro la bozza corrente. La memoria può aprire una
domanda, non chiuderla.
