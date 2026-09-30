import React from "react";

// Campo di risposta con l'elenco dei suggerimenti. Presentazionale: lo stato
// (testo, voce evidenziata) sta in chi lo usa. `suggestions` e' una lista di
// { key, label }.
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
}) {
  return (
    <section className="game-input" aria-label={ariaLabel}>
      <label htmlFor="game-guess-input">{label}</label>
      <div className={shake ? "game-input-row is-shake" : "game-input-row"}>
        <input
          id="game-guess-input"
          type="text"
          autoComplete="off"
          role="combobox"
          aria-expanded={suggestions.length > 0}
          aria-controls="game-suggestions-list"
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
        <ul className="game-suggestions" id="game-suggestions-list" role="listbox">
          {suggestions.map((s, i) => (
            <li key={s.key} role="option" aria-selected={i === highlighted}>
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
      {error && <p className="game-error">{error}</p>}
    </section>
  );
}
