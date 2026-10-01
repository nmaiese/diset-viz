# Il sotto-marchio del gioco

Prototipo statico della sezione `/quiz`: l'hub con la sfida del giorno in
evidenza e una partita di Indovina la Regione a livello Provincia, con dati
veri. Si apre da `file://` e usa i fogli veri del sito (`system.css`,
`fonts.css`, `frontend/src/game/game.css`) piu' `proto.css`.

    bin/py design/gioco/build.py      rigenera index.html da index.template.html

Le regole del sotto-marchio stanno in `design/v1/SISTEMA.md`, "Il gioco: un
sotto-marchio, di proposito". I token si verificano con
`bin/py design/v1/tools/check_tokens.py`.

## Il nome

Deciso il 30 settembre 2026: **Sfida Italia**. L'URL resta `/quiz`. Le altre due proposte
(Divario in gioco, Il Quiz del Divario) sono state scartate: Sfida Italia parla alla sfida del giorno
e si ricorda meglio. Il prototipo qui sotto porta ancora il segnaposto della prima.
