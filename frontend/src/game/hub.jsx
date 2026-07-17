import React, { useEffect, useState } from "react";
import { fetchJson, trackGameEvent } from "./shared.jsx";

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
      compare: loadJson("di-compare-stats", { bestStreak: 0, totalRounds: 0 }),
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
    fetchJson("/api/game/leaderboard?mode=compare&period=week&limit=5")
      .then((data) => setEntries(data.entries))
      .catch(() => setEntries([]));
  }, []);
  return entries;
}

function TopFivePanel() {
  const entries = useTop5();
  return (
    <div className="hub-top5">
      <h2 className="hub-stats-title">Classifica della settimana</h2>
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
        <ol className="hub-top5-list">
          {entries.map((entry) => (
            <li key={entry.rank}>
              <span className="hub-top5-rank">{entry.rank}</span>
              <span className="hub-top5-nickname">{entry.nickname}</span>
              <span className="hub-top5-score">{entry.score}</span>
            </li>
          ))}
        </ol>
      )}
      <a className="hub-card-cta" href="/quiz/classifica">Vedi la classifica completa →</a>
    </div>
  );
}

export default function HubApp() {
  const stats = useHubStats();
  useHubCardTracking();

  const hasPlayed = stats && (stats.daily.played > 0 || stats.compare.totalRounds > 0 || stats.order.totalRounds > 0);

  return (
    <>
      <div className="hub-stats">
        {!stats && (
          <div aria-hidden="true">
            <div className="skel-bars" style={{ marginTop: 0 }}>
              <span style={{ height: 14, width: "50%" }} />
            </div>
          </div>
        )}
        {stats && hasPlayed && (
          <>
            <h2 className="hub-stats-title">Le tue statistiche</h2>
            <div className="hub-stat-row">
              <div className="hub-stat">
                <strong>{stats.daily.wins}</strong>
                <span>Regioni indovinate</span>
              </div>
              <div className="hub-stat">
                <strong>{stats.compare.bestStreak}</strong>
                <span>Record "Chi è maggiore?"</span>
              </div>
              <div className="hub-stat">
                <strong>{Math.max(stats.order.bestScore3, stats.order.bestScore5)}</strong>
                <span>Miglior punteggio "Ordina"</span>
              </div>
            </div>
          </>
        )}
        {stats && !hasPlayed && (
          <p className="hub-stats-empty">Gioca una prima partita: le tue statistiche appariranno qui, salvate su questo dispositivo.</p>
        )}
      </div>
      <TopFivePanel />
    </>
  );
}
