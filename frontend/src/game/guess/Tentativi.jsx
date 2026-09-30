import React from "react";
import { formatValue } from "../shared.jsx";
import { comparisonArrow, comparisonText, ordinal } from "./helpers.js";

// Lo storico dei tentativi con il confronto indizio per indizio.
export default function Tentativi({ guesses, regionByKey }) {
  return (
    <section className="game-history" aria-label="Tentativi">
      {guesses.map((g, i) => (
        <div key={i} className={g.correct ? "guess-row is-correct" : "guess-row is-wrong"}>
          <strong>{i + 1}. {regionByKey[g.region_key] || g.region}</strong>
          {!g.correct && (
            <ul className="guess-feedback">
              {g.feedback.map((f) => (
                <li key={f.id}>
                  <span className="guess-symbol">{comparisonArrow(f.comparison)}</span>
                  <span className="guess-feedback-body">
                    <strong>{f.name}</strong>
                    <span className="guess-feedback-detail">
                      {formatValue(f.guess_value, f.unit)}
                      {Number.isFinite(f.guess_rank) && ` · ${ordinal(f.guess_rank)} su ${f.region_count}`}
                      {" "}({comparisonText(f.comparison)}
                      {Number.isFinite(f.mystery_rank) && `, misteriosa ${ordinal(f.mystery_rank)}`})
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          )}
          {g.ripartizione_hint && !g.correct && (
            <p className="guess-ripartizione">
              {g.ripartizione_hint.same
                ? "Stessa ripartizione geografica della regione misteriosa."
                : "Ripartizione geografica diversa da quella misteriosa."}
            </p>
          )}
        </div>
      ))}
    </section>
  );
}
