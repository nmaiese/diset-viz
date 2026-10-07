# Gate A indipendente: furti e sicurezza percepita, giro 2

Esito: **PASSA**. Giudice: Antigravity Gemini 3.1 Pro, contesto nuovo e famiglia diversa dal leader Claude. SHA esaminato: `608a8c8bd247065ff028fb2f7bf6a6b53e4aebea`. Rapporto consegnato nel terminale del giudice e trascritto qui dal coordinatore; il worktree del giudice è rimasto pulito.

| Criterio | Esito | Prova del giudice | Limite |
| --- | --- | --- | --- |
| 1. Domanda e tesi | Sì | Domanda territoriale in `brief.md:13`; tesi descrittiva in `brief.md:23`, senza promessa causale o individuale. | Analisi ecologica descrittiva, non test inferenziale. |
| 2. Tre misure | Sì | Furti `bes-07SIC002`, rischio `bes-07SIC022`, rapine `bes-07SIC004`, su venti regioni e tre anni. | Denominatori e popolazioni distinti. |
| 3. Numeri | Sì | `numeri.md` e `ricalcolo.py` usano decimali pubblicati e ranghi medi per ex aequo; N=20 e N=18. | Le stime non portano qui una misura dell'errore campionario. |
| 4. Interpretazione | Sì | Brief vieta cause non provate, inferenze individuali e medie regionali presentate come nazionali. | Il perché di una persona resta ignoto. |
| 5. Controllo contrario | Sì | H2 negativa conservata; rapine e degrado non spiegano specificamente le regioni divergenti. | Scelta del candidato guidata dai risultati; lettura esplorativa. |

## Verifica numerica del coordinatore

Eseguito `DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py lavoro/furti-sicurezza-percepita/ricalcolo.py` sullo SHA sopra. Il calcolo usa `Decimal` prima delle differenze e ranghi medi sugli ex aequo. Risultati:

| Finestra | Campione | Divergenze | ρ furti/rischio | ρ rapine/rischio |
| --- | ---: | ---: | ---: | ---: |
| 2023–2025 | 20 | 8/20 | -0,001129518 | 0,136080712 |
| 2023–2025, senza Toscana/Campania | 18 | 7/18 | 0,103359187 | 0,126582566 |
| 2019–2025 | 20 | 11/20 | 0,107802495 | 0,510114496 |
| 2019–2025, senza Toscana/Campania | 18 | 9/18 | 0,148109808 | 0,579710433 |

Media semplice del rischio 2019: 22,095%, arrotondata a 22,10%. Minimo della serie disponibile: 2021, non 2023. Dal 2019 al 2025 i furti calano in 17 regioni, salgono in 2 e restano invariati in 1. La precedente verifica Astra ha riconciliato 360/360 celle con lo ZIP Istat; il secondo giudice ne ha confermato la traccia nel dossier, senza documentare un nuovo campione ZIP indipendente. Reati 2025 provvisori e serie ricostruita dal 2019 restano limiti obbligatori.

## Vincoli per autore e grafico

1. Scrivere «non coincide sempre» e «debole associazione», mai «prova», «dimostra» o «indipendenti».
2. Dire che confronto regionale non spiega cause individuali e non è preregistrazione confermativa.
3. Dichiarare provvisorietà dei reati 2025 e diversa granularità dei denominatori.
4. Mostrare le variazioni su venti regioni; Toscana e Campania sono casi descrittivi, non prova.

Formulazione massima autorizzata dal giudice: «Nelle venti regioni, il calo dei furti in casa non coincide sempre con un calo del rischio percepito. I cambiamenti dei furti e del rischio mostrano una debole associazione fra i ranghi nelle due finestre considerate. Per le rapine l'associazione è maggiore dal 2019 al 2025 e molto più debole dal 2023 al 2025. Questi confronti regionali non spiegano perché una persona si senta insicura.»

Il giudice autorizza il passaggio alla scrittura. Gate B resta obbligatorio dopo bozza e grafico.
