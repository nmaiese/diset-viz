# MODELLI: quale modello usare per ogni lavoro, come lanciarlo, cosa sa fare

Unica fonte per tutti i progetti. Prima di lanciare un worker scegli il modello da qui.
Verificata sulle CLI vere (comandi in fondo) il 06/10/2026 dalle 21:00 e il 07/10/2026 fino alle 00:30 Roma.
Dove una riga dice «ricerca» il dato viene dalla spec di ricerca del 06/10/2026 (conservata sulla workstation) (fonti pubbliche, non
confrontato con la CLI); «NV» = non verificato; «non letto» = nessuna lettura reale oggi.
Il catalogo cambia in fretta: si rilegge con i comandi in fondo, non a memoria.

## 1. Come si lancia (sempre con orca-lancia)

```bash
# dal worktree del coordinatore, percorso assoluto, spec in un file
~/dev/dev-tools/scripts/orca-lancia.sh --agent <codex|claude|opencode|antigravity|grok> \
  [--model <slug>] [--effort <low|medium|high|xhigh|max|ultra>] \
  --worktree <compito> --spec-file <file> [--sola-lettura] [--scrivi-trust]
~/dev/dev-tools/scripts/orca-lancia.sh --attivita <nome> --worktree <compito> --spec-file <file>   # modello da agents/ruoli.tsv
```

- Mai headless (`codex exec`, `claude -p`, `opencode run`, `agy -p`): una guardia li nega, non si vedono in Orca.
- Il titolo della scheda in Orca è «<progetto> · worker · <compito> · <agente>:<modello>». `orca-ide terminal list`
  mostra invece il titolo che imposta l'agente («OpenCode»): il modello vero si legge dalla scheda o dal battito.
- `--effort`: codex (`-c model_reasoning_effort=`), claude (`--effort`), grok. **Non** per opencode né antigravity
  (rifiutato con exit 2). `--model` con `--attivita` non si combina.
- Un worker è concluso solo dopo `worker_done` letto dal coordinatore (`orca-ide orchestration check`). Poi
  `scripts/orca-fine-worker.sh --worktree <percorso>` chiude terminale, worktree e ramo.
- Un solo Codex alla volta per lancio, **max 2 Codex vivi nella società**: guarda prima i battiti.

## 2. Codex (ChatGPT, piano Pro Lite; CLI 0.157.1)

Catalogo vero (`codex debug models`), contesto 272.000 per tutti; livelli di ragionamento per modello:

| slug | default | livelli | uso |
|---|---|---|---|
| `gpt-6-astra` | medium | low…max, ultra | ragionamento difficile, red team di produzione, piani: **1 giro, riga nel battito**, mai in serie |
| `gpt-6-sol` | medium | low…max, ultra | codice impegnativo, documenti lunghi (ricerca: «GPT-6.1 Sol» **non è nel catalogo Codex**: esiste solo come `opencode/gpt-6.1-sol`) |
| `gpt-6-luna` | medium | low…max | **prima scelta per il codice** e per le review di codice; veloce, quota larga |
| `gpt-5.6-sol` / `-terra` / `-luna` | low / medium / medium | fino a ultra (luna max) | generazione precedente, ancora ok |
| `gpt-5.5` | medium | low…xhigh | ritiro annunciato per il 14/10/2026 (ricerca, NV): oggi è ancora nel catalogo |
| `gpt-reserve`, `codex-auto-review` | medium | low…max | riserva di quota; review automatica di diff |

Lancio: `orca-lancia.sh --agent codex --model gpt-6-luna --effort medium --worktree X --spec-file F`.
Peculiarità: livelli di ragionamento (alzare solo per codice di sicurezza), `/status` mostra la quota settimanale
(Pro Lite: «Weekly limit» comune; Luna ha in più una riserva), `codex review` e `codex exec` esistono ma qui si
usa solo il TUI via Orca, sandbox con `--sandbox`, `codex agents` elenca le sessioni del demone.
**Demone `remote-control` acceso: i lanci Orca falliscono (0 su 3), spento riescono (5 su 5). Tienilo spento mentre gli agenti lavorano.**
Quota: letta dal titolare 06/10 20:55 = 36% settimanale usato (reset 12/10 20:58); alle 12:00 era 70%: leggere `/status` prima di una raffica.
Privacy: dati personali **no** (provider esterno, uso del titolare solo per codice e documenti pubblici).

## 3. Claude (abbonamento; Claude Code 2.1.292)

| alias | modello | contesto | uso |
|---|---|---|---|
| `fable` | Fable 5.1 | 1M (ricerca, NV) | ragionamento più difficile, red team; quota alta |
| `opus` | Opus 5.5 | 1M | direzione, codice agentico lungo |
| `sonnet` | Sonnet 5.5 | 1M | coordinatori, lavori che li richiedono |
| `haiku` | Haiku 4.5 | 200k (ricerca, NV) | lavori semplici e **dati personali** |

Lancio: `orca-lancia.sh --agent claude --model haiku [--effort low]`. `--fallback-model`, sottoagenti (`--agents`),
skill, piano, `/usage` (quota: leggerla da un terminale Claude, **non letta oggi**). Privacy: è l'unico provider
dove i dati personali sono ammessi (con l'opt-out dal training del titolare).

## 4. Antigravity (`agy` 1.3.0, account individuale)

Catalogo vero (`agy models`): `gemini-3.8-flash-{high,medium,low}`, `gemini-3.7-flash-*`, `gemini-3.6-flash-*`,
`gemini-3.1-pro-{high,low}`, `claude-sonnet-4-6`, `claude-opus-4-6-thinking`, `gpt-oss-120b-medium`.
Nano Banana **non compare** nell'elenco (immagini: NV).

- Ricerca web su dati pubblici, studi, red team e review di altra famiglia: `gemini-3.8-flash-high` (lavoro corrente),
  `gemini-3.1-pro-high` (ragionamento lungo, interi repository, multimodale).
- Lancio: `orca-lancia.sh --agent antigravity --worktree X --spec-file F --scrivi-trust` (la prima volta in un
  worktree nuovo). **`--model` ed `--effort` non passano da orca-lancia**: il modello è quello di
  `~/.gemini/antigravity-cli/settings.json` (oggi «Gemini 3.8 Flash (Medium)»); per cambiarlo si modifica quel file
  (globale: ripristinarlo dopo).
- Peculiarità della CLI: `--mode plan|accept-edits`, `--effort`, `--json-schema` (output strutturato), `--sandbox`,
  una sola sessione alla volta; 429 giornaliero visibile solo nel log.
- Privacy: l'account individuale conserva prompt e interazioni (ricerca, NV) → **mai dati personali**, per prudenza.

## 5. OpenCode (`opencode` 1.18.35): Zen gratuiti, Go, Ollama Cloud

Catalogo vero: `opencode models` (775 righe). Lancio: `orca-lancia.sh --agent opencode --model <provider/modello>`.
In Orca: `/models` nel TUI per cambiare; `opencode stats` il consumo; `--effort` non supportato.

**Zen gratuiti (`opencode/…`):**

| modello | stato oggi | uso |
|---|---|---|
| `longcat-2.5-preview-free` | **ok**, zero retention (ricerca) | prima scelta gratuita: review meccaniche, lavori semplici, test |
| `space-bunny-free` | zero retention (ricerca); lento (10 tok/s misurati) | 2ª scelta se longcat è occupato |
| `nemotron-3-ultra-free` | 503 «upstream overloaded» a tratti (06/10) | bozze; log NVIDIA: solo dati pubblici |
| `big-pickle` | **quota esaurita 06/10 dalle 17:40** («retry 8 h») | bozze; dati usati dal fornitore |
| `fledge-alpha-free`, `mimo-v2.6-flash-free`, `ling-3.1-flash-free`, `muse-spark-1.3-*-free` | non provati o instabili (mimo e nemotron-3.5-lightning: 0 token in 100 s) | evitare |

Regola: i gratuiti **non ricevono dati personali**, mai.

**Go (`opencode-go/…`, a consumo): il titolare ha detto «quota esaurita» il 06/10, ma il lancio di prova con `opencode-go/deepseek-v4.1-flash` il 07/10 alle 00:0x è riuscito (98 s). Reset e consumo: non letti; riprova prima di escluderlo:**
`kimi-k3`, `kimi-k2.7-code` (codice), `glm-5.3` (cybersecurity/test), `deepseek-v4-pro` e `deepseek-v4.1-flash`
(qualità/prezzo), `qwen3.8-max`, `qwen3.8-flash`, `qwen3.7-plus`, `minimax-m3` (documenti lunghi), `mimo-v2.5-pro`,
`longcat-2.0`, `grok-4.7`, `gpt-6-luna`. Dati personali: ricerca dice 0 giorni di conservazione per GLM/Kimi/DeepSeek (NV).
Nota: `opencode-go/qwen3.6-plus` **non esiste** (c'è `opencode/qwen3.6-plus` in Zen).

**Ollama Cloud (`opencode -m ollama-cloud/…`, crediti mensili gratuiti, una richiesta alla volta):**
`gpt-oss:120b` (codice rapido, 189 tok/s misurati), `gemma4:31b` (italiano naturale), `nemotron-3-ultra`/`-super`/`-nano:30b`.
Mistral-large-3 e qwen3.5:397b risultano a pagamento (ricerca, NV).

## 6. Grok (CLI 1.0.46)

`grok models` → solo `grok-4.7`, account collegato a grok.com (le prime righe di `grok models` possono dire «not authenticated»: il lancio funziona). Lancio `--agent grok [--effort …]`
(`-m`, `--reasoning-effort`, `--always-approve`). Prova 07/10: primo lancio rc=1 dopo 86 s (causa non registrata), secondo riuscito.
Quota gratuita ~1M token / 24 h (ricerca, NV). Uso: second opinion matematica; non è nel flusso corrente.

## 7. Quale per quale lavoro (1ª / 2ª scelta)

| lavoro | 1ª | 2ª | note |
|---|---|---|---|
| codice | codex `gpt-6-luna` (medium; high se sicurezza) | codex `gpt-6-sol` medium | Astra solo se il disegno è difficile |
| review di altra famiglia | autore Claude/Codex → agy `gemini-3.1-pro-high` | opencode `longcat-2.5-preview-free` | mai Astra in catena; autore Gemini → Codex Luna |
| red team a contesto pulito | codex `gpt-6-astra` (1 giro) | agy `gemini-3.1-pro-high` | riga nel battito |
| ricerca su dati pubblici | agy `gemini-3.8-flash-high` | opencode `longcat-2.5-preview-free` | citare fonti; «non trovato» al posto di numeri inventati |
| documenti e spec | Sonnet 5.5 (coordinatore) / codex `gpt-6-sol` | opencode Go `kimi-k3` (quando c'è quota) | |
| UI e immagini | agy `gemini-3.8-flash-high` | Sonnet 5.5 | immagini: Nano Banana NV |
| test | opencode `longcat-2.5-preview-free` | codex `gpt-6-luna` low | |
| riepiloghi, compiti meccanici | opencode `longcat-2.5-preview-free` | claude `haiku` | |
| **dati personali** | claude `haiku` | claude `sonnet` | mai gratuiti, mai agy individuale, mai Codex |

## 8. Ruoli fissi (modello attuale, consumo, alternativa)

| ruolo | oggi | consumo oggi | alternativa più adatta |
|---|---|---|---|
| direzione (Cowork) | Claude Opus 5.5 (ricerca: «oggi Opus») | non letto | Opus resta; Fable solo per decisioni difficili |
| Cowork esecutivo trade5 | non verificato da dev-tools | non letto | da decidere con C1 |
| coordinatori C1, C2, C3, C-DIV | Sonnet 5.5, ctx 5–50% a fine giornata | non letto (limiti.json a mano, fermo al 05/10) | Sonnet va bene; rilancio sopra il 60% di contesto |
| trader discrezionale | Sonnet ogni 15 min | non letto | Haiku se non serve ragionamento lungo (da provare) |
| worker | vedi §7 | mix per modello nel battito | nessun provider inattivo |

## 9. Come si rilegge (comandi)

```bash
codex debug models | jq -r '.models[]|[.slug,.default_reasoning_level]|@tsv'     # Codex
agy models                                                                       # Antigravity
opencode models                                                                  # OpenCode (tutti i provider)
grok models                                                                      # Grok
claude --help | grep -E -- '--(model|effort|fallback)'                           # alias Claude
~/dev/dev-tools/scripts/orca-lancia.sh ...                                       # lancio; titolo e modello nel battito
```

## 10. Aperti

- Quote vere: la tabella «Quote» di `stato.md` è a mano (limiti.json, C1 la corregge); finché non è letta, scrivi «non letto».
- Verifica per provider con un lancio reale: tabella in `docs/MODELLI-prove.md` (stessa data).
- Nano Banana, reset di Go, chiave Grok, ruoli «Cowork esecutivo» e «trader discrezionale»: da completare.
