# Brief per lo scrittore: scheda ter-104 (materiale, non scaletta)

## Perche si cambia
La scheda e buona (909 parole, 5 sezioni, nessun rilievo di prosa) e NON va riscritta. Due difetti, trovati confrontando il testo con le fonti dello scout (`fonti.md`):
1. La sezione `dinamica` dice che il «passo cambia» dopo il 2022 e che «quasi tre quarti della distanza percorsa dal 2018» arrivano dopo, senza dire che le fonti non spiegano il salto: nella serie nazionale Istat c'e fra 2022 e 2023 un salto di circa 2,5 punti senza spiegazione trovata (`fonti.md` riga 4) e Eurostat segnala interruzioni di serie nel 2018 e nel 2021. Un lettore capisce una svolta; le fonti dicono solo che il dato e cambiato.
2. Manca un fatto che il sito ha e nessuno racconta: la distanza fra Mezzogiorno e Nord scende in punti ma non in proporzione.

## Dati verificati (ricalcolati dal CSV `Assoluti_Regione.csv`, idIndicatore 104, e confermati da una seconda persona)
- Media semplice delle 20 regioni: 38,1% nel 2018, 33,0% nel 2024 (non e la media nazionale).
- Media semplice per ripartizione (Mezzogiorno = Sud e Isole, 8 regioni, Abruzzo compreso): Nord 34,7% e 30,2%; Centro 33,2% e 28,0%; Mezzogiorno 44,0% e 38,2% (2018 e 2024).
- Distanza Mezzogiorno meno Nord: 9,3 punti nel 2018, 8,0 nel 2024. Rapporto Mezzogiorno/Nord: 1,268 e 1,266, cioe circa 1,27 in entrambi gli anni.
- Noi Italia (Istat), perimetro diverso (Mezzogiorno e Centro-Nord): 41,3% e 29,6% nel 2024 (rapporto circa 1,4). Va detto che non coincide con le medie regionali di sopra.
- Eurostat: Italia 33,0% contro UE 18,8% nel 2025 (dato nazionale; rapporto circa 1,8).
- Nessuna regione e peggiorata dal 2018 al 2024. Piu migliorate: Umbria -7,5, Calabria -7,2, Molise -6,9 punti. Meno: Valle d'Aosta -2,1, Toscana -2,5, Emilia-Romagna -3,6.
- Per il grafico di dispersione (istruzione contro `ter-901`, PIL pro capite, 2024): le regioni piu lontane dalla tendenza per posto in classifica: Valle d'Aosta (istruzione 15o, PIL 3o), Umbria (istruzione 1o, PIL 12o), Abruzzo (istruzione 6o, PIL 13o). Correlazione di rango sulle venti regioni: -0,60 con il PIL pro capite.

## Cose da NON scrivere
- Che il salto 2022-2023 sia «un miglioramento», «un'accelerazione» o abbia una causa (nessuna fonte la dice).
- Che il Sud abbia «il doppio» del Nord (il rapporto e 1,27 con i nostri dati, circa 1,4 per Istat).
- Una media semplice chiamata media nazionale. Cause del divario regionale senza fonte.
- Cifre non nel brief. Giudizi («bene», «male», «preoccupante»).

## Forma
Lascia il lead e le altre sezioni cosi come sono. Voce e ritmo della scheda attuale (frasi concrete, numeri uno per frase). Il marcatore del grafico: `<!-- grafico: dispersione con=ter-901 evidenzia="Valle d'Aosta,Umbria,Abruzzo" didascalia="..." -->` (formato esatto in `docs/INDICATOR_PAGES.md`; la didascalia dice la notizia in una frase, per esempio che la Valle d'Aosta ha un PIL alto e molti adulti fermi alla licenza media, l'Umbria l'opposto).
