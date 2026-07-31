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

// Copy del punteggio per modalità: descrive la metrica reale calcolata dal
// server (serie di risposte corrette per "Chi è maggiore?", round perfetti
// consecutivi per "Ordina le regioni"). Niente numeri inventati.
const SCORING = {
  compare: "La serie di risposte corrette consecutive in una sessione di \"Chi è maggiore?\".",
  order: "Il numero di round perfetti consecutivi in una sessione di \"Ordina le regioni\".",
};

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

function Podium({ entries, mode }) {
  const top = entries.slice(0, 3);
  const labels = ["1° posto", "2° posto", "3° posto"];
  return (
    <div className="qz-podium">
      {top.map((entry, i) => (
        <div key={entry.rank} className={`qz-podium-card p${i + 1}`}>
          <small>{labels[i]}</small>
          <h3>{entry.nickname}</h3>
          <em>
            {detailBadge(mode, entry.detail) || " "}
            {entry.when && ` · ${relativeWhen(entry.when)}`}
          </em>
          <div className="qz-podium-pts">{entry.score} pt</div>
        </div>
      ))}
    </div>
  );
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
    fetchJson(`/api/game/leaderboard?mode=${mode}&period=${period}&limit=40`)
      .then((data) => setEntries(data.entries))
      .catch(() => setError(true));
  }, [mode, period]);

  const periodLabel = period === "week" ? "ultimi 7 giorni" : "tutti i tempi";

  return (
    <div className="qz-page qz-page--lb">
      <div className="qz-lb-main">
        <div className="qz-filters">
          {MODES.map((m) => (
            <button
              key={m.value}
              type="button"
              className={mode === m.value ? "qz-filter is-active" : "qz-filter"}
              aria-pressed={mode === m.value}
              onClick={() => setMode(m.value)}
            >
              {m.label}
            </button>
          ))}
          <span className="qz-filters-sep" aria-hidden="true" />
          {PERIODS.map((p) => (
            <button
              key={p.value}
              type="button"
              className={period === p.value ? "qz-filter is-active" : "qz-filter"}
              aria-pressed={period === p.value}
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
              <span style={{ height: 44, width: "100%" }} />
              <span style={{ height: 44, width: "100%" }} />
              <span style={{ height: 44, width: "100%" }} />
            </div>
          )}

          {!error && entries && entries.length === 0 && (
            <p className="hub-stats-empty">
              Ancora nessun punteggio in questo periodo: gioca una serie e sii il primo in classifica.
            </p>
          )}

          {!error && entries && entries.length > 0 && (
            <>
              {entries.length >= 3 && <Podium entries={entries} mode={mode} />}
              <div className="qz-lb-rows">
                {entries.map((entry) => (
                  <div key={entry.rank} className={entry.rank <= 3 ? "qz-lb-row top" : "qz-lb-row"}>
                    <span className="rank">{entry.rank}</span>
                    <span className="who">
                      <b>{entry.nickname}</b>
                      {detailBadge(mode, entry.detail) && <em>{detailBadge(mode, entry.detail)}</em>}
                    </span>
                    <span className="pts">{entry.score}</span>
                    <span className="when col-hide">{relativeWhen(entry.when)}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      <aside className="qz-side">
        <div className="qz-side-card qz-side-card--accent">
          <p className="eb">Entra in classifica</p>
          <p className="qz-side-body">
            Gioca una serie e invia il tuo risultato a fine partita. Il nickname è pubblico. Puoi giocare senza registrazione, o accedere per legare i punteggi al tuo account.
          </p>
          <div className="qz-side-cta">
            <a className="game-btn" href={mode === "order" ? "/quiz/ordina" : "/quiz/chi-e-maggiore"}>Gioca ora</a>
          </div>
        </div>

        <div className="qz-side-card">
          <p className="eb">Come si calcola</p>
          <p className="qz-side-body">{SCORING[mode]}</p>
        </div>

        <div className="qz-side-card">
          <p className="eb">Periodo</p>
          <p className="qz-side-body">
            Stai vedendo i punteggi dei <strong>{periodLabel}</strong>. La finestra settimanale scorre sugli
            ultimi sette giorni. I record personali restano salvati sul tuo dispositivo.
          </p>
        </div>
      </aside>
    </div>
  );
}
