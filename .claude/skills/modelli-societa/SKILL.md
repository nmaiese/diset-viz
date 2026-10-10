---
name: modelli-societa
description: "Sceglie modello e famiglia per coordinamento, worker, review e dati personali. Usala prima di assegnare lavoro o scegliere revisore."
---

# Modelli della società

Fonte unica: `~/dev/dev-tools/docs/MODELLI.md`; rileggi §7 e Regolamento prima di assegnare. Quote non lette restano «non letto».

## Quattro domande

1. Il lavoro tratta dati personali? Se sì, solo Claude Haiku o Sonnet; mai Codex, agy individuale o modelli gratuiti.
2. È codice, analisi, ricerca, documentazione o red team? Usa tabella e §7.
3. Chi autore e revisore? Revisore sempre di **famiglia del trainer diversa**, non solo di CLI diversa (vedi tabella).
4. Mix giornaliero vicino 40% per provider? Nessun tetto ai Codex vivi; il tetto del 40% circa vale per ciascun
   provider **a pagamento**, non per i gratuiti (regolamento v1.1 §5).

| Lavoro | Scelta / revisore |
|---|---|
| Codice ordinario | Codex GPT-6 Luna; Sol per codice impegnativo |
| Documenti lunghi o coordinamento | Codex GPT-6 Sol oppure Claude Sonnet secondo alternanza coordinatori |
| Dati personali | Claude Haiku per lavoro semplice; Sonnet per coordinamento o lavoro impegnativo |
| Review: autore Claude o Codex | Antigravity Gemini 3.1 Pro High; alternativa OpenCode LongCat gratuito |
| Review: autore Gemini | Codex GPT-6 Luna |
| Review: autore Ollama Cloud `gemma4:31b` | Claude Sonnet o Codex GPT-6 Luna; **mai** agy Gemini (Google = stessa famiglia) |
| Review: autore Ollama Cloud `gpt-oss:120b` | Claude Sonnet; alternativa Antigravity Gemini 3.1 Pro High solo se il lavoro non ha dati personali; **mai** Codex GPT (OpenAI = stessa famiglia) |
| Review: autore OpenCode Zen LongCat | Non trattare un altro modello OpenCode come indipendente: famiglia effettiva verificata; stessa famiglia → Codex o Claude |
| Ricerca su dati pubblici | Antigravity Gemini 3.8 Flash High; alternativa OpenCode LongCat gratuito |
| Test | OpenCode LongCat gratuito; alternativa Codex GPT-6 Luna low |
| Riepiloghi e compiti meccanici | OpenCode LongCat gratuito; alternativa Claude Haiku |
| Decisioni difficili dei coordinatori o direzione | Codex GPT-6 Astra o Claude Opus; per direzione, Opus solo per decisioni difficili |
| Red team a contesto pulito | Codex GPT-6 Astra, un giro; alternativa Antigravity Gemini 3.1 Pro High |
| Review | Famiglia diversa da autore; non basta cambiare modello nello stesso provider |

Gratuiti prima scelta per lavori adatti (regolamento v1.1 §5): OpenCode Zen (`longcat-2.5-preview-free`) prima;
Ollama Cloud solo con crediti inclusi **confermati** — oggi saldo/piano non verificato: non contarne i lanci come
gratuiti. Soglie: almeno metà dei lanci di worker del giorno su modelli gratuiti e ogni coordinatore con almeno un
worker gratuito al vivo quando ha coda (mix nel battito). Prova reale 08/10: `ctx_197cdbdc17b4`, gpt-oss:120b, calcolo
17×19=323 — risposta corretta, ma **non** prova credito incluso (fonte crediti: https://ollama.com/pricing, dove Free =
starter credits e solo starter models). Tariffe: `gpt-oss:120b` ha prezzo pubblicato; per `gemma4` la pagina ufficiale
dà la riga senza taglia di dimensione, quindi la tariffa esatta di **`gemma4:31b` non è verificata**. Lancio:
`orca-lancia.sh --agent opencode --model ollama-cloud/gpt-oss:120b` (codice) o `--model ollama-cloud/gemma4:31b`
(italiano), solo senza dati personali; verificare catalogo (`opencode models`) e disponibilità reale prima dell'uso.
Review di lavoro Ollama Cloud: famiglia del trainer diversa — `gemma4` (Google) → Claude o Codex, mai agy Gemini;
`gpt-oss` (OpenAI) → Claude, o agy Gemini solo senza dati personali, mai Codex GPT. Autore OpenCode Zen LongCat: un
altro modello OpenCode non è indipendente per default, famiglia effettiva verificata sul catalogo.

Coordinatori alternano Claude Sonnet ↔ Codex GPT-6 Sol: mai Luna o Haiku. Mix dei provider **a pagamento** circa 40%
(tetto v1.1 §5); nessun provider inattivo. Astra solo un giro, mai in catena di review. Non inferire quote non lette.

## Lancio

```bash
~/dev/dev-tools/scripts/orca-lancia.sh --agent <codex|claude|opencode|antigravity|grok> \
  [--model <slug>] [--effort <livello>] --worktree <compito> --spec-file <file>
~/dev/dev-tools/scripts/orca-lancia.sh --attivita <nome> --worktree <compito> --spec-file <file>
```

`--attivita` prende modello da `agents/ruoli.tsv`; non combinarlo con `--model`. `--model` è opzionale; agy non seleziona modello dal launcher e rifiuta `--effort` (modello ed effort nelle impostazioni Antigravity). Anche OpenCode rifiuta `--effort`. Mai headless. I modelli gratuiti non ricevono dati personali: nessuno.

## Rilettura catalogo

```bash
codex debug models
agy models
opencode models
grok models
claude --help
```

Catalogo e quote cambiano; non dichiararli verificati senza lettura odierna.
