<!--
Etichette (una per asse): chi ha scritto: run:lite | run:team | run:routine | umano
                          fase: gate-b (pezzo da giudicare) | config | docs | infra
                          esito, se serve: canary | bocciata | corretta-prima-del-merge
La review segue REVIEW.md. Commit senza trailer Co-Authored-By.
-->

## Che cosa

<!-- Una riga: che cosa cambia per chi legge il sito o per chi lavora al repo. -->

## Intent

<!-- `docs/intent/<id>.md` di platform. Obbligatorio per un pezzo (Gate A) e per un cambio di config. -->

## Per un pezzo (run:lite, run:team)

- **Angolo scelto**, e angoli scartati con le prove:
- **Fonti esterne** (istituzionali, riaperte sul grezzo, con data):
- **Esito del verificatore / dei revisori**: cifre controllate, smentite, giri di correzione:
- **Esito di `lab.controlla`**: `non_trovate`, `link_inesistenti`, `bloccanti`, `bozza_salvata`:
- **Consuntivo memoria** (solo team): consultata, candidati, promossi, scartati:
- **Costo e turni**:

## Per il codice (umano, config, infra)

- **Comandi di verifica eseguiti** e loro esito (`bin/py -m unittest discover -s tests`, `npm run build`, ...):
- **File di verifica toccati?** (`tests/`, hook, `.claude/rules/`): una run automatica non li tocca mai.
- **Documentazione aggiornata nello stesso commit** (CLAUDE.md, docs/): sì / non serve perché

## Review (REVIEW.md)

- [ ] Passaggio 1, cifre e fonti
- [ ] Passaggio 2, regole editoriali
- [ ] Passaggio 3, igiene e sicurezza
