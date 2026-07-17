import React, { useEffect, useState } from "react";
import { fetchJson, trackGameEvent } from "./shared.jsx";

const MODES = [
  { value: "compare", label: "Chi è maggiore?" },
  { value: "order", label: "Ordina le regioni" },
];

const PERIODS = [
  { value: "week", label: "Ultimi 7 giorni" },
  { value: "all", label: "Sempre" },
];

function relativeWhen(iso) {
  const then = new Date(iso).getTime();
  if (!Number.isFinite(then)) return "";
  const diffH = Math.round((Date.now() - then) / 3600000);
  if (diffH < 1) return "meno di un'ora fa";
  if (diffH < 24) return `${diffH} ${diffH === 1 ? "ora" : "ore"} fa`;
  const diffD = Math.round(diffH / 24);
  return `${diffD} ${diffD === 1 ? "giorno" : "giorni"} fa`;
}

function detailBadge(mode, detail) {
  if (mode === "order" && detail && detail.count) return `${detail.count} regioni`;
  return null;
}

export default function LeaderboardApp() {
  const [mode, setMode] = useState("compare");
  const [period, setPeriod] = useState("week");
  const [entries, setEntries] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setEntries(null);
    setError(false);
    trackGameEvent("leaderboard_view", { mode, period });
    fetchJson(`/api/game/leaderboard?mode=${mode}&period=${period}&limit=20`)
      .then((data) => setEntries(data.entries))
      .catch(() => setError(true));
  }, [mode, period]);

  return (
    <div className="leaderboard-app">
      <div className="lb-tabs" role="tablist" aria-label="Modalità">
        {MODES.map((m) => (
          <button
            key={m.value}
            type="button"
            role="tab"
            aria-selected={mode === m.value}
            className={mode === m.value ? "game-tab is-active" : "game-tab"}
            onClick={() => setMode(m.value)}
          >
            {m.label}
          </button>
        ))}
      </div>
      <div className="lb-tabs lb-tabs--period" role="tablist" aria-label="Periodo">
        {PERIODS.map((p) => (
          <button
            key={p.value}
            type="button"
            role="tab"
            aria-selected={period === p.value}
            className={period === p.value ? "game-tab is-active" : "game-tab"}
            onClick={() => setPeriod(p.value)}
          >
            {p.label}
          </button>
        ))}
      </div>

      <div aria-live="polite">
        {error && <p className="game-error">Impossibile caricare la classifica. Riprova.</p>}

        {!error && entries === null && (
          <div className="skel-bars" aria-hidden="true" style={{ marginTop: 16 }}>
            <span style={{ height: 14, width: "90%" }} />
            <span style={{ height: 14, width: "80%" }} />
            <span style={{ height: 14, width: "85%" }} />
          </div>
        )}

        {!error && entries && entries.length === 0 && (
          <p className="hub-stats-empty">
            Ancora nessun punteggio in questo periodo: gioca una serie e sii il primo in classifica.
          </p>
        )}

        {!error && entries && entries.length > 0 && (
          <table className="lb-table">
            <thead>
              <tr>
                <th scope="col">#</th>
                <th scope="col">Nickname</th>
                <th scope="col">Punteggio</th>
                <th scope="col">Quando</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.rank}>
                  <td>{entry.rank}</td>
                  <td>
                    {entry.nickname}
                    {detailBadge(mode, entry.detail) && (
                      <span className="lb-detail-badge">{detailBadge(mode, entry.detail)}</span>
                    )}
                  </td>
                  <td>{entry.score}</td>
                  <td>{relativeWhen(entry.when)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
