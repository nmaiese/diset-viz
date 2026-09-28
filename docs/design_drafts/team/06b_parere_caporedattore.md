# Secondo parere sul piano, dal punto di vista della prosa

Prodotto da OpenCode in headless, modello `ollama-cloud/gpt-oss:120b`, gratuito,
28 settembre 2026. Ha letto `PIANO.md` e `content/esempi/ilpost-redditi-comuni.md`,
con la consegna di fare il caporedattore esigente e criticare il piano solo
sulla domanda: ne uscirà un articolo discorsivo o di nuovo un testo tecnico?

**Nota del team leader.** I numeri di riga citati non corrispondono al file.
Tre rilievi si accolgono:

- **1 e 3, il perché.** Nello chiede "cosa influenza quel tema e come mai
  abbiamo questi numeri". Nel piano il perché sta solo nella parte 5 del brief,
  in una a tre frasi dello scout. Diventa una parte a sé del brief, con le
  spiegazioni che le fonti danno davvero, e un criterio passa/non passa nella
  rubrica.
- **6, grafici richiamati dal testo.** Un grafico che il testo non nomina non
  spiega niente. Diventa un criterio del revisore.
- **7, secondo parere anche sulla leggibilità.** Era già così, perché rifà da
  zero L1 e L2. Va detto in chiaro.

Due si respingono. Il **4**, una guardia deterministica che verifica la presenza
di un ragionamento: una macchina non lo sa verificare, quindi finirebbe per
contare parole chiave, ed è il revisore che lo giudica. Il **brief ideale** qui
sotto è proprio la scaletta che Nello non vuole: definizione, estremi, andamento,
aneddoto, conclusione. In più invita a inventare cause e aneddoti ("una regione
che ha ridotto la disoccupazione grazie a un programma di incentivazione") che
nessuna fonte ha dato. Resta qui come esempio di cosa non fare.

---

**Rilievi al piano**

1. *Sezione 3 – Il brief* richiede “cinque parti” ma non indica la necessità di contestualizzare le cause dei valori; rischio di testi che elencano solo le cifre senza spiegare il perché; aggiungere al brief un punto esplicito “spiegare i fattori alla base dei cambiamenti”​.  
2. *Ruolo Scrittore* (riga 88) prevede “scrivere la scheda in forma `libera`” ma non indica fonti analitiche o domande guida; rischio di narrazioni superficiali; fornire al scrittore una griglia di domande “perché è cambiato il valore, quali fattori macro‑economici influenzano”​.  
3. *Rubrica Revisore* (riga 90) controlla “testo da solo, poi testo con brief e dossier”; il revisore non verifica la presenza di spiegazioni causali; rischio di approvare testi tecnici; includere nel controllo un criterio “presenza di spiegazione dei driver”​.  
4. *Guardia deterministica* (riga 249) verifica solo “cifre contro il dossier”; non controlla coerenza narrativa; rischio di numeri corretti ma senza contesto; ampliare la guardia con “verifica della presenza di almeno un ragionamento esplicativo per ogni variazione”​.  
5. *Brief* (riga 123‑135) specifica “che cosa misura… in una riga” ma non richiede esempi comparativi o trend; rischio di descrizioni statiche; inserire “includere un confronto storico e regionale”​.  
6. *Grafico* (riga 89) aggiunge marcatori ma non richiede che il testo li richiami; rischio di grafici isolati senza spiegazione; obbligare il grafico a indicare “perché il grafico è inserito”​.  
7. *Secondo parere sul revisore* (riga 91) ricontrolla solo accuratezza, non la capacità comunicativa; rischio di confermare testi stilli; chiedere al secondo parere di valutare “chiarezza e narrazione”​.  
8. *Team leader* (riga 85) apre issue con “riga del brief” ma non definisce “tone” o “stile”; rischio di tono tecnico; aggiungere al template della issue un campo “stile discorsivo, tono informale”​.  
9. *Mancanza di esempi di storytelling* nel piano; i redattori non hanno linee guida su analogie o aneddoti; rischio di testi piatti; inserire una sezione “esempi di narrazione” nel brief.  
10. *Assenza di indicazioni su riferimento a fonti istituzionali* (riga 66‑68) limita la credibilità; rischio di affermazioni non supportate; specificare che ogni spiegazione deve citare la fonte del dato.

---

**Brief ideale per lo scrittore – “tasso di disoccupazione per regione”**

Il tasso di disoccupazione misura la percentuale di persone in età lavorativa che, nel periodo considerato, non hanno un lavoro ma cercano attivamente occupazione.  
Nel brief troverai per ogni regione i dati più recenti “[cifra dal dossier]” e, per gli ultimi cinque anni, le variazioni annuali “[cifra dal dossier]”.  

Spiega innanzitutto **cosa significa** il tasso e perché è un indicatore utile per capire la salute del mercato del lavoro.  
Poi evidenzia **le regioni con i valori più alti e più bassi**, raccontando brevemente **le ragioni strutturali** (es. presenza di settori industriali, livello di istruzione, politiche regionali) che hanno influenzato quei risultati; usa le informazioni contenute nel dossier “[cifra dal dossier]”.  
Descrivi **i trend**: se il tasso è cresciuto o diminuito negli ultimi anni, collega il cambiamento a **eventi macro‑economici** (riforme fiscali, crisi, investimenti) o a **fenomeni locali** (chiusura di grandi imprese, programmi di formazione).  
Inserisci **un aneddoto o esempio concreto** (es. una regione che ha ridotto la disoccupazione grazie a un programma di incentivazione) per rendere il racconto più umano.  
Concludi con una **riflessione sintetica** su quali sono le prospettive future, indicando le incognite più importanti e il loro possibile impatto.  

Mantieni un tono chiaro, accessibile a un lettore non esperto, evitando elenchi di numeri e privilegiando una narrazione fluida e motivata.
