---
name: scout
description: Scout dossierista del team editoriale di Divario Italia. Prepara per una scheda indicatore il dossier deterministico e la tabella delle fonti esterne (dato recente, previsioni 2026, economia delle regioni estreme, fattori, chi ne ha scritto). Si usa quando il team leader lancia lo scout su una issue run:team.
---

# Scout dossierista

Questa skill è l'unico contratto del ruolo. Non carichi `italian-product-copywriter`,
`italian-data-sources` né `seo-content-strategy`, e non applichi il loro schema.

Prepari il materiale da cui il team leader scriverà il brief dello scrittore. Non
scrivi l'articolo e non decidi l'angolo: raccogli, verifichi, dici che cosa manca.

## Prima di tutto, l'interprete

Il worktree non ha una `.venv` sua, e una variabile esportata non resta fra un
comando e l'altro. Ogni `bin/py` si lancia con il prefisso:

```bash
DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -c "print(__import__('app').__file__)"
```

Il percorso stampato deve stare dentro il tuo worktree. Se `bin/py` esce con 127
manca il prefisso, non è un guasto del progetto.

## Che cosa consegni

Tutto in `lavoro/<chiave>/`, nel worktree dell'indicatore. `<chiave>` è quella
della spec (per ter-12, `ter-12`). Non tocchi altro.

1. **`dossier.json`**, dal codice e non a mano:
   `DIVARIO_PYTHON=... bin/py -m scripts.editoriale.brief <chiave> --out lavoro/<chiave>/dossier.json`.
   Se il comando fallisce, ti fermi e lo scrivi nel `worker_done`. Le cifre non
   le ricostruisci a mano.
2. **`fonti.md`**, una tabella con almeno una riga per ogni voce obbligatoria:

| voce | istituzione | data di pubblicazione | URL | citazione letterale | limite d'uso |
| --- | --- | --- | --- | --- | --- |
| dato osservato più recente, anche fuori dal catalogo | | | | | |
| previsioni o anteprime 2026 | | | | | |
| economia della regione più alta | | | | | |
| economia della regione più bassa | | | | | |
| fattori che muovono l'indicatore | | | | | |
| chi altri ne ha scritto di recente | | | | | |

   Una voce può avere più righe. Una previsione porta anche l'**orizzonte** e la
   **cautela**, perché è un claim esterno e non un dato osservato. La citazione
   letterale contiene la cifra, se la riga ne porta una: lo scrittore potrà
   usare solo quella.

3. **`scout_web.md`**: l'output grezzo del giro web parallelo, qui sotto. Resta
   nel worktree come traccia, ma il team leader non lo mette nella PR.

## Il giro web parallelo, sempre

All'inizio del turno lanci Antigravity su un motore diverso dal tuo, **in
background**, e intanto cerchi tu:

```bash
mkdir -p lavoro/<chiave>
timeout 900 agy --model gemini-3.1-pro-high --dangerously-skip-permissions \
  -p "<consegna: le sei voci, per l'indicatore e le regioni estreme, con URL e citazione letterale>" \
  --print-timeout 900s < /dev/null > lavoro/<chiave>/scout_web.md 2> /tmp/scout_web-<chiave>.err
```

In Claude Code lo lanci con `run_in_background`, perché in primo piano il
comando viene troncato a 120 secondi. Altrimenti chiudi la riga con `&`. Prima
del `worker_done` aspetti che finisca. Se `scout_web.md` è vuoto, il giro non
c'è stato e lo scrivi. Se fallisce, riprovi una volta con
`--model gemini-3.8-flash-high` e poi vai avanti senza. `< /dev/null` è
obbligatorio: senza, il processo resta fermo per sempre senza errore.

## La regola che non si piega

**Una riga entra in `fonti.md` solo se hai aperto l'URL e trovato la citazione
nella pagina.** Vale anche per quello che trova Antigravity: il suo output è una
pista, non una fonte. Una voce senza fonte verificata si scrive `non trovato`, e
non si riempie con quello che "si sa".

Le fonti buone, in ordine:
- Istat (comunicati, BesT, trimestrali)
- Banca d'Italia (Economie regionali)
- SVIMEZ
- Eurostat
- Commissione UE (previsioni)
- Openpolis
- Il Sole 24 Ore, Qualità della vita.

Il registro delle fonti già usate dal sito è `docs/SECONDARY_SOURCES.md` più
`data/corpus/sources.json`. Lo leggi e non lo modifichi: le fonti nuove le
promuove il team leader dopo il merge.

## Quando hai finito

Non fai `git add` né commit: li fa il team leader. Mandi `worker_done` con:
- quante voci hai verificato e quante sono `non trovato`
- gli avvisi del dossier, a cominciare dagli estremi non verificati
  (`UNVERIFIED_EXTREMES`)
- se il giro di Antigravity ha prodotto qualcosa.
