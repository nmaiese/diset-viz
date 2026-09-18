<!--
Etichette (una per asse): chi ha scritto: run:team | run:routine | umano
                          (run:lite non esiste piu': la catena semplice e' stata cancellata il 18/9/2026)
                          fase: gate-b (pezzo da giudicare) | config | docs | infra
                          esito, se serve: canary | bocciata | corretta-prima-del-merge
La review segue REVIEW.md. Commit senza trailer Co-Authored-By.
-->

## Che cosa

<!-- Una riga: che cosa cambia per chi legge il sito o per chi lavora al repo. -->

## Obiettivo

<!-- L'obiettivo del Quadro a cui questa PR risponde, es. div-famiglie. -->

## Per un pezzo (run:team, run:routine)

- **Angolo scelto**, e angoli scartati con le prove:
- **La scaletta**, e che cosa ha mosso il `redattore` (le porta gia' il corpo della PR):
- **Fonti esterne** (istituzionali, riaperte sul grezzo, con data):
- **Esito del verificatore / dei revisori**: cifre controllate, smentite, giri di correzione:
- **Esito di `motore verifica`**: `non_trovate`, `link_inesistenti`, `bloccanti`, `bozza_salvata`:
- **Costo e turni**:

## Per il codice (umano, config, infra)

- **Comandi di verifica eseguiti** e loro esito (`bin/py -m unittest discover -s tests`, `npm run build`, ...):
- **File di verifica toccati?** (`tests/`, hook, `.claude/rules/`): una run automatica non li tocca mai.
- **Documentazione aggiornata nello stesso commit** (CLAUDE.md, docs/): sì / non serve perché

## Review (REVIEW.md)

- [ ] Passaggio 1, cifre e fonti
- [ ] Passaggio 2, regole editoriali
- [ ] Passaggio 3, igiene e sicurezza
