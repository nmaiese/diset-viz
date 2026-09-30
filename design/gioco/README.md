# Il sotto-marchio del gioco

Prototipo statico della sezione `/quiz`: l'hub con la sfida del giorno in
evidenza e una partita di Indovina la Regione a livello Provincia, con dati
veri. Si apre da `file://` e usa i fogli veri del sito (`system.css`,
`fonts.css`, `frontend/src/game/game.css`) piu' `proto.css`.

    bin/py design/gioco/build.py      rigenera index.html da index.template.html

Le regole del sotto-marchio stanno in `design/v1/SISTEMA.md`, "Il gioco: un
sotto-marchio, di proposito". I token si verificano con
`bin/py design/v1/tools/check_tokens.py`.

## Il nome, da decidere

L'URL resta `/quiz`. Tre proposte, il prototipo usa la prima come segnaposto.

1. **Divario in gioco**: il divario e' la posta in gioco. Tiene il nome della
   testata e dice che si gioca con i suoi dati, con un filo di ironia.
2. **Sfida Italia**: diretto, quotidiano, parla alla sfida del giorno. Piu'
   facile da ricordare, meno legato al marchio madre.
3. **Il Quiz del Divario**: descrittivo e coerente con l'URL, il tono piu'
   semplice dei tre. Rischia di sembrare una rubrica piu' che un luogo.
