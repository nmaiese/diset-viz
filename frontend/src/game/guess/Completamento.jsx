import React, { useEffect, useRef, useState } from "react";

// L'altezza che si vede davvero (`visualViewport`): con la tastiera virtuale aperta e' molto piu'
// piccola di `innerHeight`. Serve a limitare l'elenco dei suggerimenti a circa il 40% di quello
// che il giocatore ha sotto gli occhi. Senza `visualViewport` (o prima della misura) `null`.
function useAltezzaVisibile() {
  const [altezza, setAltezza] = useState(null);
  useEffect(() => {
    const vista = typeof window !== "undefined" ? window.visualViewport : null;
    if (!vista) return undefined;
    const aggiorna = () => setAltezza(Math.round(vista.height));
    aggiorna();
    vista.addEventListener("resize", aggiorna);
    return () => vista.removeEventListener("resize", aggiorna);
  }, []);
  return altezza;
}

// Campo di risposta con l'elenco dei suggerimenti. Presentazionale: lo stato
// (testo, voce evidenziata) sta in chi lo usa. `suggestions` e' una lista di
// { key, label }.
//
//   nota      stringa | "" | undefined. Il messaggio sotto il campo (`aria-live`): perche' il testo
//             non porta a nessun suggerimento. `undefined` = nessuna regione live, come prima.
//   error     il messaggio di un tentativo andato male.
//   ricarica  true: sotto l'errore c'e' "Ricarica la pagina" (la sfida e' cambiata, il token e' vecchio).
//   onRiprova funzione | undefined: sotto l'errore c'e' "Riprova", che rimanda lo stesso tentativo (la
//             rete non ha risposto, il tentativo non e' stato contato).
//
// Da telefono (<= 720 px, guess.css) l'elenco si apre SOPRA il campo, cosi' la tastiera virtuale non lo
// copre, e il campo e' a 16 px perche' iOS non zoomi. Le frecce e `aria-activedescendant` seguono
// l'ordine dell'elenco, dall'alto in basso, sopra o sotto che sia.
export default function Completamento({
  label,
  ariaLabel,
  placeholder,
  query,
  onQuery,
  suggestions,
  highlighted,
  onHighlight,
  onPick,
  disabled,
  shake,
  error,
  nota,
  ricarica,
  onRiprova,
}) {
  const altezza = useAltezzaVisibile();
  const elencoRef = useRef(null);

  // Con l'elenco piu' corto delle voci, la voce evidenziata deve restare in vista dentro l'elenco.
  useEffect(() => {
    const elenco = elencoRef.current;
    const voce = elenco && highlighted >= 0 && suggestions[highlighted]
      ? elenco.querySelector(`[id="game-opzione-${suggestions[highlighted].key}"]`)
      : null;
    if (!voce) return;
    if (voce.offsetTop < elenco.scrollTop) elenco.scrollTop = voce.offsetTop;
    else if (voce.offsetTop + voce.offsetHeight > elenco.scrollTop + elenco.clientHeight) {
      elenco.scrollTop = voce.offsetTop + voce.offsetHeight - elenco.clientHeight;
    }
  }, [highlighted, suggestions]);

  return (
    <section className="game-input" aria-label={ariaLabel} style={altezza ? { "--vv-h": `${altezza}px` } : undefined}>
      <label htmlFor="game-guess-input">{label}</label>
      <div className="game-input-campo">
        <div className={shake ? "game-input-row is-shake" : "game-input-row"}>
          <input
            id="game-guess-input"
            type="text"
            inputMode="search"
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
            spellCheck={false}
            role="combobox"
            aria-expanded={suggestions.length > 0}
            aria-controls="game-suggestions-list"
            aria-autocomplete="list"
            aria-activedescendant={highlighted >= 0 && suggestions[highlighted] ? `game-opzione-${suggestions[highlighted].key}` : undefined}
            placeholder={placeholder}
            value={query}
            disabled={disabled}
            onChange={(e) => onQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                onHighlight((h) => Math.min(h + 1, suggestions.length - 1));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                onHighlight((h) => Math.max(h - 1, 0));
              } else if (e.key === "Enter") {
                if (highlighted >= 0 && suggestions[highlighted]) {
                  onPick(suggestions[highlighted].key);
                } else if (suggestions.length === 1) {
                  onPick(suggestions[0].key);
                }
              } else if (e.key === "Escape") {
                onHighlight(-1);
                onQuery("");
              }
            }}
          />
        </div>
        {suggestions.length > 0 && (
          <ul className="game-suggestions" id="game-suggestions-list" role="listbox" ref={elencoRef}>
            {suggestions.map((s, i) => (
              <li key={s.key} id={`game-opzione-${s.key}`} role="option" aria-selected={i === highlighted}>
                <button
                  type="button"
                  className={i === highlighted ? "is-highlighted" : ""}
                  disabled={disabled}
                  onMouseEnter={() => onHighlight(i)}
                  onClick={() => onPick(s.key)}
                >
                  {s.label}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      {nota !== undefined && <p className="game-nota" role="status" aria-live="polite">{nota}</p>}
      {error && <p className="game-error">{error}</p>}
      {error && !ricarica && onRiprova && (
        <button type="button" className="game-btn" onClick={onRiprova}>Riprova</button>
      )}
      {error && ricarica && (
        <button type="button" className="game-btn" onClick={() => window.location.reload()}>Ricarica la pagina</button>
      )}
    </section>
  );
}
