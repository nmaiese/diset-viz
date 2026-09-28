# Assegnazione dei modelli ai ruoli, proposta di nemotron

Prodotto da OpenCode in headless, modello `opencode/nemotron-3-ultra-free`,
28 settembre 2026, dai file `~/dev/dev-tools/docs/opencode-quota.md` e
`opencode-modelli.md`. Primo tentativo bloccato 14 minuti: `opencode run` in
background aspetta la fine dello stdin, che non arriva mai. Rilanciato con
`< /dev/null`, ha finito in un minuto.

**Nota del team leader.** Le stime di token per indicatore qui sotto non sono
misurate e vanno lette come ordine di grandezza inventato: il pilota carceri ha
consumato molto di più. Dove questa tabella diverge da `PIANO.md`, sezione 2, la
decisione e il motivo stanno lì. La riga del secondo parere è superata dal
fatto del giorno: i crediti Hugging Face del mese sono finiti ("Payment
Required: You have depleted your monthly included credits"), quindi GLM-5.3-Flash
non è disponibile fino al rinnovo.

| Ruolo | Modello primario (agente + id + effort) | 1° ripiego | 2° ripiego | Perché (qualità, quota, carico) | Quota stimata / indicatore |
|-------|------------------------------------------|------------|------------|----------------------------------|----------------------------|
| **TEAM LEADER** | `claude` (opus) — fisso | — | — | Orchestrazione, specifiche, decisioni; nessun conflitto di quota | ~2k token (solo prompt/coord.) |
| **SCOUT DOSSIERISTA** | `codex` → `gpt-5.6-sol` **high** | `claude` → `sonnet` | `openrouter/liquid/lfm-2.5-2.6b:free` (headless) | Ricerca pesante, tool use esteso; gpt-5.6-sol eccelle su web + sintesi, ma finestra 5h al 98% → usare a raffica, non a goccia. Sonnet fallback se quota codex esaurita. OpenRouter solo se serve banda extra e si accetta 429. | 8–12k token (ricerca + estrazione dati) |
| **SCRITTORE** | `claude` → `opus` | `codex` → `gpt-5.6-sol` **high** | `opencode/big-pickle` (headless) | Qualità prosa giornalistica ineccepibile: Opus è il migliore. Se Opus occupato, gpt-5.6-sol high effort regge. big-pickle (Zen free) qualità verificata ma lento (16 tok/s) e promo temporanea. | 4–6k token (stesura + rifinitura) |
| **GRAFICO** | `codex` → `gpt-5.6-sol` **medium** | `claude` → `sonnet` | `opencode/nemotron-3-ultra-free` (headless) | Genera Python/SVG da numeri dati; medium effort sufficiente, quota codex meno pressata. Sonnet alternativa solida. nemotron-3-ultra-free (36 tok/s, ragionamento) per codice non banale. | 2–3k token (codice + eventuali fix) |
| **REVISORE** (spawn PR, modello ≠ scrittore) | `codex` → `gpt-5.6-sol` **high** (se scrittore=claude) / `claude` → `sonnet` (se scrittore=codex) | `opencode/nemotron-3-ultra-free` (headless) | `ollama-cloud/gpt-oss:120b` (headless, 1 req) | Controllo cifre, fonti, prosa: serve modello forte e diverso da chi ha scritto. gpt-5.6-sol high o sonnet secondo disponibilità. nemotron-3-ultra-free headless per risparmiare quota. gpt-oss:120b (189 tok/s) solo se ollama-cloud libero (1 concorrente). | 2–3k token (lettura + commenti) |
| **REVISORE 2° PARERE** (opzionale, headless, economico) | `opencode/ling-3.0-flash-fin-free` | `ollama-cloud/gemma4:31b` | `huggingface/zai-org/GLM-5.3-Flash` | Veloce, gratuito, solo controlli leggeri (coerenza, refusi). ling-3.0: 80 tok/s, miglior micro-test. gemma4:31b (129 tok/s, italiano) se ollama libero. GLM-5.3-Flash (118 tok/s) ma $0,10/mese → usare solo se serve. | 1–2k token (passata rapida) |

---

### Rischi dell'assegnazione

1. **Quota codex (gpt-5.6-sol) al limite** — Finestra 5h al 98% (probe 27/09). Scout + Scrittore + Revisore + Grafico tutti su codex la saturano in 1–2 indicatori. *Mitigazione*: alternare claude/codex per ruolo, usare headless OpenCode/Ollama per ruoli non critici, processare indicatori a batch sequenziali (non paralleli).

2. **Ollama-cloud = collo di bottiglia seriale** — 1 richiesta alla volta. Se Grafico + Revisore 2° parere + Scout (fallback) collidono, si incolonnano. *Mitigazione*: assegnare ollama-cloud a un solo ruolo per indicatore (es. Revisore 2°), usare OpenCode Zen free per gli altri fallback.

3. **Zen free è promo temporanea** — `big-pickle`, `ling-3.0-flash-fin-free`, `nemotron-3-ultra-free` possono sparire o diventare a pagamento senza preavviso. *Mitigazione*: non costruire pipeline che ne dipendano; trattarli come banda "bonus", non come default.

4. **OpenRouter free = slot machine** — 429 frequenti, modelli `:free` che spariscono. *Mitigazione*: solo come ripiego estremo, mai nel path critico.

5. **Hugging Face $0,10/mese = esaurimento improvviso** — Nessun warning, poi 4xx. *Mitigazione*: usare solo per Revisore 2° parere opzionale, monitorare saldo via API se possibile.

6. **OpenCode in orchestrazione perde il prompt** — I modelli Zen/ollama/hf/openrouter vanno bene **solo in headless** (`opencode run -m`, `curl`). Se Orca lancia un worker OpenCode supervisionato, il prompt non arriva. *Mitigazione*: ruoli headless (Revisore 2°, eventuali task batch) usano OpenCode; ruoli orchestrati (Scout, Scrittore, Grafico, Revisore primario) usano **solo claude/codex**.

7. **RAM 8 GB → max 4 agenti concorrenti** — TEAM LEADER (Claude) + 3 worker max. Se Scout + Scrittore + Grafico girano insieme, Revisore deve aspettare. *Mitigazione*: pipeline sequenziale per indicatore (Scout → Scrittore → Grafico → Revisore), parallelizzare *tra* indicatori diversi solo se RAM regge.

8. **Grok/xAI senza quota API** — Probe conferma chiave valida ma 403 (no crediti/licenza). *Non usabile* finché non si attiva OAuth SuperGrok/X Premium o crediti API.

9. **Revisore deve avere modello ≠ Scrittore** — Se Scrittore usa Opus, Revisore primario deve usare codex/gpt-5.6-sol (o sonnet). Se Scrittore usa codex, Revisore usa claude/sonnet. Questo vincolo riduce flessibilità quando quota codex è bassa.

10. **Nessun piano free affidabile per volume** — Groq (chiave da fixare), Google (progetto free da creare), AnyAPI (modelli free da dichiarare) richiedono interventi manuali prima di diventare operativi. *Non contati nell'assegnazione attuale*.
