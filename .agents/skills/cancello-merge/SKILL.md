---
name: cancello-merge
description: "Verifica review, prove e autorizzazioni prima di merge o deploy. Usala quando coordinatore decide se integrare cambiamento o rilasciarlo."
---

# Cancello merge e produzione

Un collaudo «tutto verde» è stato seguito da red team che ha trovato blocco e 11 problemi gravi; merge Divario ravvicinati hanno servito build vecchia con HTTP 200. Test e HTTP da soli non bastano.

## Livello richiesto

| Ambito | Requisiti |
|---|---|
| Interno: dev-tools, script, documenti, ricerca senza effetti | Test verdi e review di famiglia diversa; poi merge coordinatore di progetto, senza deploy. |
| Produzione: deploy Divario, servizi/timer Trade5, ponte | Requisiti interni, red team a contesto pulito al primo avvio, ok scritto direzione, prova post-deploy e rollback pronto. Un merge per volta. |
| Denaro vero, live, spese, cancellazioni irreversibili | Decide titolare; non è normale merge. |

Mantieni autorizzazioni Regolamento §2. Per Trade5 rispetta finestra ET 09:15–16:15 giorni di borsa: niente merge, deploy o modifiche servizi/timer; merge main solo C1.

## Review

- Famiglia diversa dall'autore; stesso provider con modello diverso non basta.
- Fornisci `SHA_base..SHA_testa`, scopo e criteri; chiedi P0/P1/P2 con file:riga e correzione proposta.
- Verifica nel codice P1 di revisori economici: ci sono stati falsi positivi.
- Massimo due giri. Dopo secondo giro con P1 aperti, invia rilievi e proposta alla direzione; niente terzo giro. Correzioni puntuali possono avere verifica mirata.
- Produzione: red team a contesto pulito solo al primo avvio, con modello forte.

## Merge

1. Produzione: un merge alla volta; attendi deploy e verifica precedente. Interno: test e review bastano; il coordinatore può fare merge senza aspettare deploy.
2. Prepara rollback: Trade5 tag `rollback-pre-<nome>`; Divario annota revisione Cloud Run al 100% traffico.
3. Esegui prova generale se esiste. Per Trade5: `bash ops/prova_generale.sh`.
4. Merge locale. Push dev-tools/Divario solo fast-forward e con ok direzione; Trade5 non si pusha.

## Prova post-deploy e rollback

- Divario: `bin/py -m scripts.editoriale.prova_dal_vivo --da <commit-prima> --a <commit-dopo>` deve mostrare frase nuova; controlla tre pagine campione. HTTP 200 non basta.
- Trade5: primo giro reale timer/servizio deve produrre file, riga journal o report atteso; `t5 doctor` verde.
- Prova fallita: rollback subito, poi diagnosi. Divario riporta revisione Cloud Run annotata al 100%; codice già in main si revoca con `git -C <repo> revert -m 1 <SHA-merge>` solo se SHA è merge commit. Per commit fast-forward: `git -C <repo> revert <SHA>`. `revert` conserva storia; mai `reset --hard`.

Esito alla direzione: branch e SHA, autore, reviewer/famiglia/giro, conteggi rilievi, prova e rollback. Senza review e prova merge non è completato.
