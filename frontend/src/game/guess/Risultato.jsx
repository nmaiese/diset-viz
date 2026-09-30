import React from "react";
import { FinePartita } from "../shared.jsx";
import Dettagli from "./Dettagli.jsx";
import Riepilogo from "./Riepilogo.jsx";
import { DistributionChart } from "./Statistiche.jsx";
import { TentativiCompatti } from "./Tentativi.jsx";
import { riassuntoRegione, titoloEsito, titoloIndizi, titoloTentativi } from "./helpers.js";

const GAME_NAME = "Indovina la Regione";

// La fine di una partita a livelli: prima l'esito (il tono, la regione col suo link, in quanti tentativi,
// il conto alla rovescia, "Condividi"), poi, in riquadri chiusi, gli indizi con le definizioni intere, i
// tentativi e le statistiche. `fatto` viene dal server, se c'e' (un campo `fatto` o `fact` del payload):
// FinePartita lo mostra solo se e' presentabile, e non lo calcoliamo qui. `esitoRef` e' dove scorre la pagina.
export default function ResultPanel({
  status, mode, puzzle, solution, recap, stats, serie, highlightBucket, guesses, regionByKey, fatto, esitoRef, onNewPractice,
}) {
  const won = status === "won";
  const daily = mode === "daily";
  const condividi = daily
    ? {
        gameName: GAME_NAME,
        game: "regione",
        puzzleNumber: puzzle.number,
        esiti: guesses.map((g) => (g.correct ? "exact" : "miss")),
        summary: riassuntoRegione({ won, tentativi: guesses.length, totale: puzzle.attempts_total }),
        url: `${window.location.origin}/quiz/indovina-la-regione`,
        eventParams: { mode, level: "regioni", game: "regione" },
      }
    : undefined;

  return (
    <div className="game-result" ref={esitoRef}>
      <FinePartita
        won={won}
        tono={won ? "pieno" : "nullo"}
        game="regione"
        titolo={titoloEsito("regione", won, guesses.length)}
        dettaglio={`La regione era ${solution.region}.`}
        fatto={fatto || undefined}
        territori={[{ name: `Scheda di ${solution.region}`, path: solution.path }]}
        nextPuzzleAt={daily ? puzzle.next_puzzle_at : undefined}
        condividi={condividi}
        onPlayAgain={onNewPractice || undefined}
        playAgainLabel="Ricomincia"
      />

      {recap && (
        <Dettagli titolo={titoloIndizi(recap.length)}>
          <Riepilogo
            titolo={null}
            soggetto={solution.region}
            mediaLabel="Media delle regioni"
            rows={recap.map((row) => ({ ...row, media: row.national_avg }))}
          />
        </Dettagli>
      )}

      <Dettagli titolo={titoloTentativi(guesses.length)}>
        <TentativiCompatti guesses={guesses} nome={(g) => regionByKey[g.region_key] || g.region} />
      </Dettagli>

      {daily && (
        <Dettagli titolo="Le tue statistiche">
          <div className="game-stats-numbers">
            <div><strong>{stats.played}</strong><span>Partite</span></div>
            <div><strong>{stats.played ? Math.round((stats.wins / stats.played) * 100) : 0}%</strong><span>Vittorie</span></div>
            <div><strong>{serie.current}</strong><span>Giorni di fila</span></div>
            <div><strong>{serie.max}</strong><span>Record</span></div>
          </div>
          <DistributionChart distribution={stats.distribution} highlightBucket={highlightBucket} />
        </Dettagli>
      )}
    </div>
  );
}
