import React from "react";
import { formatValue } from "../shared.jsx";
import { comparisonArrow, comparisonText, ordinal } from "./helpers.js";

const ICONA_GIUSTO = "/static/img/gioco/stato-giusto.svg";
const ICONA_SBAGLIATO = "/static/img/gioco/stato-sbagliato.svg";

// L'icona dell'esito, il nome (`children`) e la parola dell'esito (mai il solo colore): giusto o non e' questa.
export function SegnoTentativo({ correct, children }) {
  return (
    <>
      <img className="guess-icona" src={correct ? ICONA_GIUSTO : ICONA_SBAGLIATO} alt="" width="18" height="18" />
      {children}
      <span className="guess-esito">{correct ? "Giusto" : "Non è questa"}</span>
    </>
  );
}

// Lo storico dei tentativi durante la partita, dal piu' recente: l'esito dell'ultimo sta subito sotto
// il campo di risposta (`esitoRef` e' la sua riga, dove scorre la pagina) e il confronto indizio per
// indizio e' aperto solo li', quelli di prima si aprono a richiesta.
export default function Tentativi({ guesses, regionByKey, esitoRef }) {
  const righe = guesses.map((g, i) => ({ g, i })).reverse();
  return (
    <section className="game-history" aria-label="Tentativi">
      {righe.map(({ g, i }, posizione) => (
        <div
          key={i}
          ref={posizione === 0 ? esitoRef : undefined}
          className={g.correct ? "guess-row is-correct" : "guess-row is-wrong"}
        >
          <p className="guess-titolo">
            <SegnoTentativo correct={g.correct}>
              <strong>{i + 1}. {regionByKey[g.region_key] || g.region}</strong>
            </SegnoTentativo>
          </p>
          {!g.correct && (
            <details className="guess-confronto" open={posizione === 0}>
              <summary>Confronto degli indizi</summary>
              <ul className="guess-feedback">
                {g.feedback.map((f) => (
                  <li key={f.id}>
                    <span className="guess-symbol" aria-hidden="true">{comparisonArrow(f.comparison)}</span>
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
            </details>
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

// I tentativi a partita finita: righe compatte, in ordine, dentro un riquadro chiuso. Il nome, l'esito
// con l'icona e, per la provincia, "a circa 120 km verso nord-est" (`distanza(g)`).
//   nome       (g) => stringa
//   distanza   (g) => stringa, opzionale
export function TentativiCompatti({ guesses, nome, distanza }) {
  return (
    <ol className="guess-compatti">
      {guesses.map((g, i) => {
        const vicino = distanza ? distanza(g) : "";
        return (
          <li key={i} className={g.correct ? "guess-compatto is-correct" : "guess-compatto is-wrong"}>
            <SegnoTentativo correct={g.correct}>
              <strong>{i + 1}. {nome(g)}</strong>
            </SegnoTentativo>
            {vicino && <span className="guess-compatto-distanza">{vicino}</span>}
          </li>
        );
      })}
    </ol>
  );
}
