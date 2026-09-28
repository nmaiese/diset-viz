Sei il revisore della PR #PRNUM di nmaiese/diset-viz, la scheda ter-12 (tasso di disoccupazione) del pilota del team editoriale, issue #292. Ti lancia il team leader in headless, in un worktree nuovo sul ramo della PR. Lo scrittore è Gemini (Antigravity), e il grafico è OpenCode big-pickle. Tu sei una sessione nuova, e giudichi il testo, non chi l'ha scritto. Commit atteso: SHAATTESO.

NON leggere, aprire o elencare file fuori dal worktree: OpenCode headless rifiuta l'accesso e chiude la sessione. I temporanei vanno in .rev292/ dentro il worktree, e alla fine cancelli la cartella.

Leggi per intero skills/editorial-team/revisore/SKILL.md, il tuo unico contratto, e seguilo con tre differenze di questo giro headless:
1. Il secondo parere di gpt-oss lo lancia il team leader, non tu. Salta quella parte.
2. NON pubblichi niente: niente gh pr review, niente gh issue edit, niente worker_done. gh solo in lettura (gh pr view, gh pr diff, gh issue view).
3. I temporanei in .rev292/ e non in /tmp.

Quindi: controlla lo SHA (git rev-parse HEAD e gh pr view PRNUM --json headRefOid -q .headRefOid, uguali fra loro e a SHAATTESO). Fai girare la guardia: DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -m scripts.editoriale.guardia ter-12 --dossier lavoro/ter-12/dossier.json --fonti lavoro/ter-12/fonti.md. Poi leggi SOLO content/indicators/12.md come un lettore e rispondi alle domande 1 e 3. Poi apri lavoro/ter-12/dossier.json, brief.md e fonti.md e rispondi alle domande 2, 4 e 5. Per la 4 controlla ogni frase con una cifra o un fatto contro il dossier e fonti.md: una frase che dice una cosa diversa da quella che il dato o la fonte dicono è un "no", anche se la cifra è giusta. Per la 3 l'italiano deve essere corretto, frase per frase.

Per ogni "no": la frase citata fra virgolette, il motivo in una riga, la correzione minima. Le osservazioni che non sono un "no" vanno in "Note".

La tua risposta finale è SOLO il testo della review in Markdown, pronto da pubblicare:
- prima riga "## Review 1 della PR #PRNUM (ter-12): <verdetto>", con verdetto DA CORREGGERE oppure PRONTA PER NELLO
- seconda riga lo SHA verificato
- l'uscita della guardia
- le cinque domande con sì o no e i rilievi
- le Note.
