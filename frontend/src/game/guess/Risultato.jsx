import React from "react";
import { FinePartita } from "../shared.jsx";
import Riepilogo from "./Riepilogo.jsx";
import { DistributionChart } from "./Statistiche.jsx";

const GAME_NAME = "Indovina la Regione";

function titoloEsito(won, tentativi) {
  if (!won) return "Regione non indovinata";
  return tentativi === 1 ? "Indovinata al primo tentativo" : `Indovinata in ${tentativi} tentativi`;
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
        <Riepilogo
          soggetto={solution.region}
          mediaLabel="Media delle regioni"
          rows={recap.map((row) => ({ ...row, media: row.national_avg }))}
        />
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
