import React from "react";
import { formatValue, FinePartita } from "../shared.jsx";
import { DistributionChart } from "./Statistiche.jsx";

const GAME_NAME = "Indovina la Regione";

function titoloEsito(won, tentativi) {
  if (!won) return "Regione non indovinata";
  return tentativi === 1 ? "Indovinata al primo tentativo" : `Indovinata in ${tentativi} tentativi`;
}

// "Che cosa misura" di un indicatore: la descrizione, come si legge il valore e
// la lettura, i tre testi che il backend passa a ogni riga del recap.
function CheCosaMisura({ row }) {
  const testi = [row.description, row.value_explanation, row.reading].filter(Boolean);
  if (!testi.length) return null;
  return (
    <p className="game-recap-misura">
      <strong>Che cosa misura.</strong> {testi.join(" ")}
    </p>
  );
}

export default function ResultPanel({
  status, mode, puzzle, solution, recap, stats, serie, highlightBucket, guesses, onNewPractice,
}) {
  const won = status === "won";
  const daily = mode === "daily";
  const condividi = daily
    ? {
        gameName: GAME_NAME,
        puzzleNumber: puzzle.number,
        esiti: guesses.map((g) => (g.correct ? "exact" : "miss")),
        summary: won ? `${guesses.length} su ${puzzle.attempts_total}` : `X su ${puzzle.attempts_total}`,
        url: `${window.location.origin}/quiz/indovina-la-regione`,
        eventParams: { mode, level: "regioni" },
      }
    : undefined;

  return (
    <div className="game-result">
      <FinePartita
        won={won}
        titolo={titoloEsito(won, guesses.length)}
        dettaglio={`La regione era ${solution.region}.`}
        territori={[{ name: `Scheda di ${solution.region}`, path: solution.path }]}
        nextPuzzleAt={daily ? puzzle.next_puzzle_at : undefined}
        condividi={condividi}
        onPlayAgain={onNewPractice || undefined}
        playAgainLabel="Ricomincia"
      />

      {recap && (
        <section className="game-recap" aria-label="Gli indicatori della sfida">
          <h3>Gli indicatori, uno per uno</h3>
          <ol className="game-recap-list">
            {recap.map((row) => (
              <li key={row.id}>
                <p className="game-recap-nome">
                  <a href={row.path}>{row.name}</a>
                </p>
                <p className="game-recap-valori">
                  <span>{solution.region}: <strong>{formatValue(row.value, row.unit)}</strong></span>
                  <span>Media delle regioni: {formatValue(row.national_avg, row.unit)}</span>
                </p>
                <CheCosaMisura row={row} />
              </li>
            ))}
          </ol>
        </section>
      )}

      {daily && (
        <div className="game-stats-inline">
          <div className="game-stats-numbers">
            <div><strong>{stats.played}</strong><span>Partite</span></div>
            <div><strong>{stats.played ? Math.round((stats.wins / stats.played) * 100) : 0}%</strong><span>Vittorie</span></div>
            <div><strong>{serie.current}</strong><span>Giorni di fila</span></div>
            <div><strong>{serie.max}</strong><span>Record</span></div>
          </div>
          <DistributionChart distribution={stats.distribution} highlightBucket={highlightBucket} />
        </div>
      )}
    </div>
  );
}
