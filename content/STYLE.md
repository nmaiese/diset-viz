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

## Schemi da evitare (suonano da bot)

- Strutture parallele ripetute: "non solo X, ma anche Y", "non è X, è Y" usato di
  continuo, le triadi di aggettivi.
- Il "due punti drammatico" a fine di ogni paragrafo.
- Chiuse retoriche tipo "In conclusione", "In sintesi", "Insomma", "In definitiva".
- Avverbi gonfi: "davvero", "assolutamente", "incredibilmente", "chiaramente".
- Frasi-slogan tipo "Leggere X significa leggere Y".
- Gergo e paroloni quando basta una parola comune.

## Dati: sempre veri

- Usa solo numeri reali presi dagli indicatori. Puoi ricavarli dall'API
  (`/api/indicator/<id>` e `/api/indicator/<id>/year/<year>`) o dallo script dati.
  Non inventare cifre e non arrotondare in modo fuorviante.
- Cita la fonte (Istat) e spiega in una riga come hai calcolato eventuali medie.
- Collega l'articolo all'atlante: imposta `indicator` nel frontmatter e inserisci
  link interni come `[testo](/?indicator=105&year=2024)`.

## SEO (mantienila, ma naturale)

- Titolo con la keyword principale all'inizio, possibilmente entro 60 caratteri.
- `description` di 150-160 caratteri, naturale, con la keyword.
- Sottotitoli `##` e `###` sensati, con varianti della keyword senza forzature.
- Tag pertinenti (2-4).

## Frontmatter

Vedi il blocco di esempio nel README e l'articolo
`content/posts/2026-06-19-divario-turistico-nord-sud-2024.md`.
