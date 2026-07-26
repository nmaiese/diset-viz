# Guida di stile per gli articoli di Divario Italia

Questa guida vale per ogni articolo in `content/posts/`. Serve a tenere i testi
coerenti e a farli sembrare scritti da una persona, non da un bot. Vale sia per
chi scrive a mano sia per gli agenti AI (Claude, Codex) che pubblicano in
automatico.

## Regole tipografiche (vincolanti)

1. **Mai il trattino lungo `—` (em-dash) né il trattino medio `–` (en-dash)** nel
   testo. Per gli incisi usa le virgole o due frasi separate. Per gli intervalli
   scrivi "dal 1981 al 2024", oppure usa il trattino normale `-` solo dentro le
   tabelle (`1981-2024`).
2. **Mai il punto e virgola `;`**. Spezza in due frasi oppure usa la virgola.
3. **Mai i puntini di sospensione come carattere unico `…`**. Se proprio servono,
   scrivi tre punti normali `...`.
4. Non scrivere `--`, `---` o sequenze pensando che diventino trattini o ellissi:
   l'engine non li converte (l'estensione `smarty` è disattivata di proposito) e
   comunque non li vogliamo.
5. Usa virgolette dritte normali (`"` e `'`).

## Tono: scrivi come una persona

- Frasi di lunghezza varia. Ogni tanto una corta. Va bene iniziare con "Ma" o "E".
- Una sola idea per paragrafo. Niente riempitivi.
- Voce attiva, soggetti concreti, verbi semplici.
- Numeri precisi e verificati al posto degli aggettivi vaghi.

## Tecniche da giornalista (fai così)

I numeri, da soli, non sono un articolo. Un buon desk di data journalism
(Openpolis, Pagella Politica, lavoce.info, Info Data del Sole 24 Ore) parte dalle
stesse cifre e scrive un pezzo che il lettore ricorda. Sei mosse:

- **Rispondi a "e allora?".** Ogni pezzo fa un punto, non un inventario. Il
  lettore deve finire sapendo perché quei numeri contano, non solo che forma ha la
  classifica. Un rapporto tra fasce d'età è un peso previdenziale e di cura, la
  spesa in ricerca è la scommessa di un territorio sul proprio futuro. Di' la
  posta in gioco una volta, in parole semplici, senza inventare una causa che il
  dato non mostra.
- **Decidi il filo prima di scrivere, poi tienilo.** Una frase sola: qual è
  l'unica cosa vera che questo dato dice quest'anno? Il titolo la annuncia, i
  paragrafi la reggono. Non paragrafi separati messi in fila, un'idea che avanza.
- **Apri sul significato, non sulla meccanica.** Un incipit tipo "la distanza si è
  ridotta di 0,22 punti" fa lavorare il lettore. Parti da cosa vuol dire quella
  distanza, la cifra arriva dopo.
- **Trasforma un numero in una scala umana.** "Quasi sette volte più veloce", "una
  donna su tre al lavoro", "tre volte la media". Un'immagine che resta, non un
  decimale nudo.
- **Dai al pezzo un ancoraggio concreto.** Un solo contrasto vivido che il lettore
  porta via, due territori che quasi non si sfiorano, un valore che era il fondo e
  ora è la vetta. Uno che se lo merita, non una lista.
- **Varia il ritmo, usa la frase corta.** Quasi tutte le frasi hanno una
  subordinata. Ogni tanto una no. Una riga di tre parole dopo una lunga è lo
  strumento più antico del mestiere, e questi testi non lo usano quasi mai.

## Schemi da evitare (suonano da bot)

- Strutture parallele ripetute: "non solo X, ma anche Y", "non è X, è Y" usato di
  continuo, le triadi di aggettivi.
- Il "due punti drammatico" a fine di ogni paragrafo.
- Chiuse retoriche tipo "In conclusione", "In sintesi", "Insomma", "In definitiva".
- La domanda retorica in chiusura di paragrafo ("il mercato assume di più o le
  giovani restano fuori?"). Non risponde a niente e suona da bot. Fai il punto o
  taglia la frase.
- Avverbi gonfi: "davvero", "assolutamente", "incredibilmente", "chiaramente".
- Frasi-slogan tipo "Leggere X significa leggere Y".
- Gergo e paroloni quando basta una parola comune.

## Struttura: utile, non seriale

- `In breve` e `Dati usati` sono ammessi e spesso utili. Servono a far capire
  subito fonte, periodo, territorio, unita e limite.
- Non usare lo stesso telaio completo in ogni articolo. Se molti post hanno tutti
  `In breve`, `Dati usati`, `Le regioni agli estremi`, `Perche conta`, il lettore
  percepisce una produzione a stampo.
- Mantieni i blocchi di fiducia quando servono, ma varia gli H2 narrativi:
  "Dove il problema pesa di piu", "Cosa segnala sul mercato del lavoro",
  "Dove si produce piu valore", "Cosa cambia per servizi e territorio".
- Le chiusure devono portare a un prossimo passo concreto: atlante, indicatore,
  tema, metodologia o articolo correlato. Niente chiuse da riassunto scolastico.

## Dati: sempre veri

- Usa solo numeri reali presi dagli indicatori. Puoi ricavarli dall'API
  (`/api/indicator/<id>` e `/api/indicator/<id>/year/<year>`) o dallo script dati.
  Non inventare cifre e non arrotondare in modo fuorviante.
- Cita la fonte (Istat) e spiega in una riga come hai calcolato eventuali medie.
- Collega l'articolo al catalogo: imposta `indicator` nel frontmatter e inserisci
  link interni con il **percorso canonico** dell'indicatore, per esempio
  `[testo](/indicatore/tasso-di-turisticita/ter-105)`. È il `path` che il
  catalogo espone per ogni voce. Non usare `/?indicator=...` né
  `/atlante?indicator=...`: la prima forma oggi apre la home, la seconda resta
  sull'Atlante e arriva alla scheda solo via JavaScript.
- Prima di pubblicare, prepara una claim table anche se non entra nel testo:
  claim, fonte, periodo, territorio, unita, trasformazione e confidenza.
- Se usi una seconda fonte di contesto, deve essere autorevole e verificata. Se
  non esiste una seconda fonte pertinente, dichiaralo invece di inventarla.

## SEO (mantienila, ma naturale)

- Titolo con la keyword principale all'inizio, possibilmente entro 60 caratteri.
- `description` di 150-160 caratteri, naturale, con la keyword.
- `seo_title` opzionale per tenere il tag `<title>` piu corto dell'H1.
- `updated` opzionale nel frontmatter (stessa sintassi di `date`, es. `2026-07-20`):
  impostalo solo quando aggiorni davvero i dati o il testo di un articolo gia
  pubblicato. Guida `dateModified` nello schema Article e mostra "Aggiornato il..."
  in pagina; senza `updated`, `dateModified` resta uguale a `date`.
- Sottotitoli `##` e `###` sensati, con varianti della keyword senza forzature.
- Tag pertinenti (2-4).
- Schema candidate solo se il contenuto e visibile in pagina. Niente FAQ o
  Dataset schema di riempimento.

## Controlli prima di pubblicare

```bash
rg -n "[—–;]" content/posts
```

Il comando deve tornare vuoto. Per template, frontend e SVG testuali controlla
anche il testo visibile, ma ignora i punti e virgola di CSS, JS, JSON-LD e CSV.

Controlla anche che non ci siano sequenze identiche di H2 tra piu articoli. I
blocchi `In breve` e `Dati usati` possono ripetersi, gli H2 interpretativi no.

Controlla infine: link a metodologia o fonte, link a indicatore o tema, caveat,
next step concreto, title/description/H1 coerenti e non identici.

## Frontmatter

Vedi il blocco di esempio nel README e l'articolo
`content/posts/2026-06-19-divario-turistico-nord-sud-2024.md`.
