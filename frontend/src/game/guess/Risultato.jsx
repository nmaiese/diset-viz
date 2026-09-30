import React from "react";
import { formatValue } from "../shared.jsx";
import { DistributionChart } from "./Statistiche.jsx";

export default function ResultPanel({
  status, mode, puzzle, solution, recap, stats, highlightBucket, shareCopied, onShare, countdown, onNewPractice,
}) {
  return (
    <section className="game-result">
      <h3>{status === "won" ? "Hai indovinato!" : "Regione misteriosa non indovinata"}</h3>
      <p className="game-result-region">
        <a href={solution.path}>{solution.region}</a>
      </p>
      <div className="game-result-actions">
        {mode === "daily" && (
          <button type="button" className="game-btn" onClick={onShare}>
            {shareCopied ? "Copiato!" : "Condividi il risultato"}
          </button>
        )}
        {onNewPractice && (
          <button type="button" className="game-btn" onClick={onNewPractice}>
            Ricomincia
          </button>
        )}
        <a className="game-btn game-btn--ghost" href={solution.path}>
          Scheda regione
        </a>
      </div>

      {mode === "daily" && countdown && (
        <p className="game-countdown">
          Prossima sfida tra <span>{countdown}</span>
        </p>
      )}

      {recap && (
        <table className="game-recap">
          <thead>
            <tr><th>Indicatore</th><th>{solution.region}</th><th>Media delle regioni</th></tr>
          </thead>
          <tbody>
            {recap.map((row) => (
              <tr key={row.id}>
                <td><a href={row.path}>{row.name}</a></td>
                <td>{formatValue(row.value, row.unit)}</td>
                <td>{formatValue(row.national_avg, row.unit)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {mode === "daily" && (
        <div className="game-stats-inline">
          <div className="game-stats-numbers">
            <div><strong>{stats.played}</strong><span>Partite</span></div>
            <div><strong>{stats.played ? Math.round((stats.wins / stats.played) * 100) : 0}%</strong><span>Vittorie</span></div>
            <div><strong>{stats.streak}</strong><span>Serie</span></div>
            <div><strong>{stats.maxStreak}</strong><span>Record</span></div>
          </div>
          <DistributionChart distribution={stats.distribution} highlightBucket={highlightBucket} />
        </div>
      )}
    </section>
  );
}
