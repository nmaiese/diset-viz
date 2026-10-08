# Gate B: pilota-pensioni
Issue: C-DIV
Worktree: pilota-pensioni

Esito: FERMO
SHA bozza: 0853143eba545845b0989ae08c16bb5872b18908
Hash bozza: d79056deaa78ff51eb37397cba3e196542378ee4e3c01af493bde7b7df42b372
Famiglie autore/revisore: Claude Sonnet 5.5 / Codex GPT-6
T: sì — la quota scende in 106 province su 106 con dato in entrambi gli anni, 2015 e 2023; il CSV conferma.
R: sì — Crotone e Biella rendono concreta la distanza fra 16,9% e 4,9%; Isernia al 9,2% e Verbano-Cusio-Ossola all'8,9% mostrano il confine quasi assente fra le due aree.
L: no — la prima frase spiega la distinzione dall'integrazione INPS, ma apre con «La scheda non conta» e accosta 16,9% e «circa uno su sei»: un lettore non esperto incontra prima la correzione tecnica, poi riceve due volte il dato.
N: sì — la quota cala in tutte le province comparabili mentre il divario fra gli estremi resta quasi stabile, da 13,2 a 12,8 punti; riscontro ricalcolato sul CSV.
Controllo anti-invenzione: nessuna persona o causa inventata. Le frasi su pensionati e quote usano il denominatore giusto; il riferimento INPS dichiara che riguarda pensioni, non persone. Nessun controllo visivo di HTML svolto, nessun grafico nella bozza.
Bloccanti: 1 semantico-editoriale nel lead (R1).
Voto: 3 — T, R e N soddisfatti; L no. La frase di apertura resta debole per racconto e duplica la stessa misura.
Motivo: ho ricontrollato le frasi modificate. Il CSV provinciale conferma Crotone 16,9% e Bolzano 4,1% nel 2023, Crotone 19,3% nel 2015, calo in 106 province su 106, e distanze agli estremi di 13,2 e 12,8 punti. Conferma inoltre Biella 4,9%, Barletta-Andria-Trani 15,9%, Napoli 15,6%, Isernia 9,2% e Verbano-Cusio-Ossola 8,9%. «A Crotone la quota riguarda circa un pensionato su sei» è coerente col denominatore dell'indicatore. Le prime menzioni delle otto province citate puntano a `/provincia/<chiave>`; il client Flask restituisce HTTP 200 per tutti gli otto percorsi e per il link all'indicatore correlato. H2 «Dove la quota è più alta» è descrittivo e coerente. Prosa: 722 parole; `level: provincia`; `seo_title` 53 caratteri; nessun `—`, `–`, `;` o `…`; link indicatore canonico presente. Il lead ha distinzione INPS nella prima frase, ma «La scheda non conta» è un avvio metatestuale, e «16,9% ... circa uno su sei» ripete il medesimo valore. Suggerimento preciso: «Nel 2023, il 16,9% dei pensionati di Crotone aveva un reddito pensionistico lordo sotto i 500 euro al mese. Questa misura non coincide con la pensione minima dell'INPS: conta i pensionati sotto una soglia di reddito, non chi riceve l'integrazione al trattamento minimo.» Così il lettore incontra subito misura e territorio e la cifra compare in una sola forma nel lead.
Rilievi localizzati: R1 [alta, bloccante, ancora aperto], prima frase: la distinzione INPS è presente, ma il lead parte da «La scheda non conta» e duplica Crotone con percentuale e immagine. Usare il significato positivo e una sola forma numerica, come nella correzione proposta. R2 [risolto], seconda sezione: «a Crotone la quota riguarda circa un pensionato su sei» usa correttamente pensionati come denominatore. R3 [risolto], le prime menzioni con valore di Crotone, Bolzano, Biella, Barletta-Andria-Trani, Napoli, Isernia, Verbano-Cusio-Ossola e Milano hanno link canonici funzionanti (HTTP 200). R4 [risolto], H2 «Dove la quota è più alta» descrive la distribuzione senza chiamare regola un valore massimo del 16,9%.
Guardia: esito del precedente giro: due residui con `dossier.json` e `fonti.md`, `42,2` falso positivo dovuto al parser e `16.309` non censito in `fonti.md` pur presente nel CSV e in `numeri.md`. Non ho rilanciato la guardia: non ho cambiato gli input e questi residui non incidono sui rilievi di questo giro.
Giri: 2
Decisione: dopo il secondo e ultimo giro, FERMO alla direzione. Non chiedere un terzo giro.
