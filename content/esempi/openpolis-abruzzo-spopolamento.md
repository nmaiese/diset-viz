# Openpolis, i limiti del dato come scansione del testo

- **Testata** Openpolis, edizione territoriale Abruzzo, rubrica "Italie a confronto"
- **Autore** Redazione (Openpolis non firma i singoli pezzi)
- **Data** 21 febbraio 2024
- **URL** https://www.openpolis.it/nellabruzzo-in-spopolamento-serve-un-nuovo-approccio-ai-bisogni-del-territorio/
- **Forma di storia** un dato che copre meno di quello che sembra
- **Da usare quando** scrivi la sezione `limiti`, o quando la copertura della
  serie e' il fatto principale invece di una nota a pie' di pagina

## Il testo

> Scendendo a livello comunale, ricostruire gli effetti dello spopolamento sul
> territorio è molto difficile per due motivi. In primo luogo, le previsioni di
> Istat attualmente riguardano solo i comuni sopra i 5mila abitanti. Un
> miglioramento importante rispetto ai precedenti rilasci, quando l'elaborazione
> si fermava al di sotto dei 20mila residenti, ma che lascia comunque fuori oltre
> 8 comuni abruzzesi su 10.
>
> Oltrettutto, anche per i comuni su cui il calcolo viene effettuato, l'istituto
> di statistica raccomanda una serie di cautele. Trattandosi di stime, le
> previsioni demografiche "divengono, infatti, tanto più incerte quanto più ci si
> allontana dalla base di partenza, in particolar modo in piccole realtà
> geografiche come quelle qui contemplate".
>
> Con questi caveat emerge che, tra i capoluoghi, solo l'Aquila dovrebbe
> accrescere la propria popolazione (+2,3%). In negativo le altre città, con un
> calo più contenuto a Pescara (-3,9%) e molto più consistente a Teramo (-12,4%) e
> Chieti (-12,5%).
>
> A perdere popolazione nei prossimi anni potrebbero essere soprattutto i comuni
> dell'entroterra abruzzese. Cali superiori al 20% si registrano infatti a
> Trasacco, Montorio al Vomano e Sulmona. Quest'ultima città potrebbe perdere un
> abitante su 4 da qui al 2042, passando da oltre 22mila a meno di 17mila
> residenti (-25,4%). E purtroppo non si hanno informazioni sui tanti piccoli
> comuni interni della regione che probabilmente affronteranno più di altri gli
> effetti dello spopolamento.

**Nota di fedelta'.** "Oltrettutto" e' un refuso dell'originale, lasciato dov'era:
e' una citazione, non una bozza da correggere.

## Perche' si legge al primo passaggio

**Annuncia quanti sono i limiti prima di elencarli, e li chiude con una formula
di ripresa.** "e' molto difficile per due motivi", poi "In primo luogo", poi
"Oltrettutto", poi **"Con questi caveat emerge che"**. La cautela scandisce il
testo invece di bloccarlo, e il lettore sa esattamente quando la parentesi
metodologica si e' chiusa. Le nostre sezioni `limiti` non hanno mai quella
formula di ripresa, e infatti si leggono come un obbligo assolto in coda.

**Il limite e' quantificato, non dichiarato.** Non "la copertura e' parziale", ma
"lascia comunque fuori oltre 8 comuni abruzzesi su 10". Un limite con un numero
e' un fatto, un limite senza numero e' una scusa.

**La citazione della fonte e' corta e sta dentro il ragionamento.** Due righe di
Istat, non un paragrafo. Serve a dire che la cautela non e' un'opinione della
redazione.

**"E purtroppo" e' una parola di voce, e si e' guadagnata il posto.** L'ultima
frase ammette quello che i dati non dicono, con un avverbio che in prosa
istituzionale sarebbe fuori posto. E' l'unica in tutto l'estratto: una per pezzo,
esattamente come chiede `content/STYLE.md`.

**Nota sul contatore.** Questo testo pesa 18,9 tic per mille parole, quasi nove
volte il ter-167 pubblicato che l'utente ha trovato illeggibile. E' prosa
professionale, chiara, e lo strumento la boccia. E' la prova che
`tic_count.py` misura un asse diverso dalla leggibilita', e che su questo
criterio il metro e' la lettura.
