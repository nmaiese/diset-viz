import React, { useEffect, useState } from "react";
import { AuthControl, fetchJson, trackGameEvent } from "./shared.jsx";

function loadJson(key, fallback) {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? { ...fallback, ...JSON.parse(raw) } : fallback;
  } catch {
    return fallback;
  }
}

function useHubStats() {
  const [stats, setStats] = useState(null);
  useEffect(() => {
    setStats({
      daily: loadJson("di-game-stats", { played: 0, wins: 0, maxStreak: 0 }),
      compare: loadJson("di-compare-stats", { bestStreak: 0, totalRounds: 0, totalCorrect: 0 }),
      order: loadJson("di-order-stats", { bestScore3: 0, bestScore5: 0, totalRounds: 0 }),
    });
  }, []);
  return stats;
}

// Le card modalità sono server-rendered (indicizzabili): qui aggiungiamo solo
// il tracciamento evento, senza duplicarne il markup in React.
function useHubCardTracking() {
  useEffect(() => {
    const cards = document.querySelectorAll(".hub-card");
    function onClick(event) {
      const mode = event.currentTarget.getAttribute("href");
      trackGameEvent("hub_mode_click", { mode });
    }
    cards.forEach((card) => card.addEventListener("click", onClick));
    return () => cards.forEach((card) => card.removeEventListener("click", onClick));
  }, []);
}

function useTop5() {
  const [entries, setEntries] = useState(null);
  useEffect(() => {
    fetchJson("/api/game/leaderboard?mode=compare&period=week&limit=4")
      .then((data) => setEntries(data.entries))
      .catch(() => setEntries([]));
  }, []);
  return entries;
}

// Statistiche locali del giocatore (salvate su questo dispositivo, mai sul
// server): serie migliore, partite totali sui tre giochi, regioni indovinate
// e accuratezza in "Chi è maggiore?".
function StatsPanel({ stats }) {
  const hasPlayed = stats && (stats.daily.played > 0 || stats.compare.totalRounds > 0 || stats.order.totalRounds > 0);
  const bestStreak = stats ? Math.max(stats.compare.bestStreak, stats.daily.maxStreak) : 0;
  const games = stats ? stats.daily.played + stats.compare.totalRounds + stats.order.totalRounds : 0;
  const accuracy = stats && stats.compare.totalRounds > 0
    ? Math.round((stats.compare.totalCorrect / stats.compare.totalRounds) * 100)
    : (stats && stats.daily.played > 0 ? Math.round((stats.daily.wins / stats.daily.played) * 100) : 0);

  return (
    <div className="qz-stats">
      <p className="qz-section-eb" style={{ margin: 0 }}>Le tue statistiche</p>
      {!stats && (
        <div className="skel-bars" style={{ marginTop: 14 }} aria-hidden="true">
          <span style={{ height: 14, width: "60%" }} />
        </div>
      )}
      {stats && !hasPlayed && (
        <p className="hub-stats-empty" style={{ marginTop: 12 }}>
          Gioca una prima partita: le tue statistiche appariranno qui, salvate su questo dispositivo.
        </p>
      )}
      {stats && hasPlayed && (
        <div className="qz-stats-row">
          <div><small>Miglior serie</small><strong>{bestStreak}</strong></div>
          <div><small>Partite</small><strong>{games}</strong></div>
          <div><small>Regioni indovinate</small><strong>{stats.daily.wins}</strong></div>
          <div><small>Accuratezza</small><strong>{accuracy}%</strong></div>
        </div>
      )}
    </div>
  );
}

function LeaderboardPanel() {
  const entries = useTop5();
  const max = entries && entries.length > 0 ? entries[0].score : 1;
  return (
    <div className="qz-lb">
      <div className="qz-lb-head">
        <p className="qz-section-eb" style={{ margin: 0 }}>Classifica · settimana</p>
        <a href="/quiz/classifica">Vedi tutta →</a>
      </div>
      {entries === null && (
        <div className="skel-bars" aria-hidden="true">
          <span style={{ height: 14, width: "70%" }} />
          <span style={{ height: 14, width: "60%" }} />
        </div>
      )}
      {entries && entries.length === 0 && (
        <p className="hub-stats-empty">Ancora nessun punteggio questa settimana: gioca a "Chi è maggiore?" e sii il primo.</p>
      )}
      {entries && entries.length > 0 && (
        <ol className="qz-lb-list">
          {entries.map((entry) => (
            <li key={entry.rank}>
              <span className="qz-lb-rank">{entry.rank}</span>
              <span className="qz-lb-name">{entry.nickname}</span>
              <span className="qz-lb-bar" aria-hidden="true">
                <i style={{ width: `${Math.max(8, (entry.score / max) * 100)}%` }} />
              </span>
              <span className="qz-lb-score">{entry.score}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export default function HubApp() {
  const stats = useHubStats();
  useHubCardTracking();

  return (
    <>
      <AuthControl />
      <section className="qz-two">
        <StatsPanel stats={stats} />
        <LeaderboardPanel />
      </section>
    </>
  );
}
