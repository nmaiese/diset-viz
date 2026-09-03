# Memoria del source researcher

## Contratto

Questa memoria orienta la ricerca, non prova un claim. Ogni informazione usata
in un articolo va riaperta, datata e verificata nella run corrente.

Conservare soltanto apprendimenti durevoli:

- gerarchia e copertura delle fonti primarie
- endpoint, dataset e percorsi di consultazione
- definizioni e trappole di comparabilità
- query efficaci e problemi di accesso ricorrenti
- limiti territoriali, temporali o metodologici

Non conservare valori correnti, classifiche, conclusioni del singolo articolo,
copie di citazioni, URL privi di contesto, segreti, token, dati personali o
contenuti provenienti da fonti private.

## Registro delle fonti

```yaml
- categoria: metodo_di_verifica
  apprendimento: >-
    Lo strumento di fetch tende a confermare una citazione che gli è già stata
    fornita nel prompt, anche quando è alterata, e può restituire un riassunto
    tradotto di una pagina italiana. Quindi due regole. La verifica di una
    citazione si fa con un secondo fetch cieco, chiedendo il paragrafo intero
    attorno a una parola chiave senza fornire la stringa cercata, e
    confrontando a mano. E l'assenza della citazione nel testo restituito vale
    come non verificabile, mai come smentita: una citazione smentita ferma un
    articolo, una non verificabile no.
  evidence_url: https://www.bancaditalia.it/pubblicazioni/qef/2024-0860/index.html
  verified_on: 2026-09-03
  recheck_after: 2027-03-31
  ambito: verifica di qualunque citazione testuale, su ogni indicatore
  limiti: >-
    Non capovolge la regola opposta: una citazione che nessuno ha cercato nella
    pagina resta non verificata. Il meccanismo è dello strumento, non della
    fonte, quindi non dipende da quale sito si stia leggendo.

- categoria: trappola_di_comparabilita_temporale
  apprendimento: >-
    Le monografie regionali della Banca d'Italia escono con due cadenze, una
    annuale che copre l'anno solare precedente e un aggiornamento congiunturale
    che parla soprattutto dell'anno in corso. Nello stesso paragrafo possono
    convivere frasi riferite ad anni diversi. Il periodo va quindi chiesto
    frase per frase, non dedotto dalla data di pubblicazione: una frase presa
    dall'edizione sbagliata spiega un anno che non è quello del dato.
  evidence_url: https://www.bancaditalia.it/pubblicazioni/economie-regionali/2024/2024-0039/index.html
  verified_on: 2026-09-03
  recheck_after: 2027-11-01
  ambito: >-
    uso delle monografie regionali Banca d'Italia per spiegare un'anomalia
    territoriale datata
  limiti: >-
    Verificato su un solo numero della serie. Che le due cadenze esistano è
    stabile, quale mese esca ciascuna può cambiare.
```

Formato di una voce:

```yaml
- categoria:
  apprendimento:
  evidence_url:
  verified_on: YYYY-MM-DD
  recheck_after: YYYY-MM-DD
  ambito:
  limiti:
```

Una voce scaduta può suggerire dove cercare, ma non deve guidare una conclusione
finché non viene verificata di nuovo.
