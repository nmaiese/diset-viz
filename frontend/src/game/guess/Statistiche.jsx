import React from "react";
import { Modal } from "../shared.jsx";
import { DIST_BUCKETS } from "./api.js";

export function DistributionChart({ distribution, highlightBucket }) {
  const max = Math.max(1, ...DIST_BUCKETS.map((b) => distribution[b] || 0));
  return (
    <div className="dist-chart">
      {DIST_BUCKETS.map((bucket) => {
        const count = distribution[bucket] || 0;
        const widthPct = count > 0 ? Math.max((count / max) * 100, 6) : 0;
        return (
          <div className="dist-row" key={bucket}>
            <span className="dist-label">{bucket === "fail" ? "X" : bucket}</span>
            <div className="dist-bar-track">
              <div
                className={bucket === highlightBucket ? "dist-bar is-current" : "dist-bar"}
                style={{ width: `${widthPct}%` }}
              />
            </div>
            <span className="dist-count">{count}</span>
          </div>
        );
      })}
    </div>
  );
}

export function StatsModal({ stats, onClose }) {
  return (
    <Modal title="Le tue statistiche" onClose={onClose} labelledBy="game-stats-title">
      <div className="game-stats-numbers">
        <div><strong>{stats.played}</strong><span>Partite</span></div>
        <div><strong>{stats.played ? Math.round((stats.wins / stats.played) * 100) : 0}%</strong><span>Vittorie</span></div>
        <div><strong>{stats.streak}</strong><span>Serie attuale</span></div>
        <div><strong>{stats.maxStreak}</strong><span>Serie migliore</span></div>
      </div>
      <DistributionChart distribution={stats.distribution} highlightBucket={null} />
      <p className="game-stats-note">Le statistiche contano solo le sfide del giorno, non l'allenamento o l'archivio.</p>
    </Modal>
  );
}
