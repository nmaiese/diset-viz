import React, { useEffect, useState } from "react";
import { fetchJson, trackGameEvent } from "./shared.jsx";
import { statoOggi } from "./oggi.js";
import { getUser, isAuthConfigured, signInWithGoogle } from "../shared/supabase.js";

const MODES = [
  { value: "oggi", label: "Indovina la Regione · oggi" },
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
  oggi: "I tentativi usati per risolvere la sfida di oggi di Indovina la Regione: meno sono, meglio è. A parità conta chi ha finito prima.",
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

function oraArrivo(iso) {
  const t = new Date(iso);
  if (!Number.isFinite(t.getTime())) return "";
  return t.toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Rome" });
}

// La classifica di oggi di Indovina la Regione: per tentativi, poi per ora di
// arrivo. Ci compare solo chi ha un account. Il server non manda mai id o email.
function ClassificaOggi() {
  const [dati, setDati] = useState(null);
  const [errore, setErrore] = useState(false);
  const [tentativo, setTentativo] = useState(0);
  const [utente, setUtente] = useState(undefined);
  const locale = statoOggi("indovina");

  useEffect(() => {
    let attivo = true;
    setDati(null);
    setErrore(false);
    fetchJson("/api/game/daily/leaderboard")
      .then((d) => attivo && setDati(d))
      .catch(() => attivo && setErrore(true));
    return () => {
      attivo = false;
    };
  }, [tentativo]);

  useEffect(() => {
    if (!isAuthConfigured()) {
      setUtente(null);
      return;
    }
    getUser().then((u) => setUtente(u || null)).catch(() => setUtente(null));
  }, []);

  const voci = dati ? dati.entries : null;
  return (
    <div aria-live="polite">
      <p className="hub-stats-empty" style={{ marginBottom: 12 }}>
        {dati && dati.number ? `Sfida n. ${dati.number}. ` : ""}Conta chi ha risolto la sfida di oggi: prima chi ha usato meno tentativi, poi chi è arrivato prima.
      </p>
      {errore && (
        <p className="game-error">
          Impossibile caricare la classifica di oggi.{" "}
          <button type="button" className="game-btn game-btn--ghost" onClick={() => setTentativo((n) => n + 1)}>Riprova</button>
        </p>
      )}
      {!errore && voci === null && (
        <div className="skel-bars" aria-hidden="true" style={{ marginTop: 16 }}>
          <span style={{ height: 44, width: "100%" }} />
          <span style={{ height: 44, width: "100%" }} />
        </div>
      )}
      {!errore && voci && voci.length === 0 && (
        <p className="hub-stats-empty">Nessuno ha ancora risolto la sfida di oggi: accedi, gioca e sii il primo.</p>
      )}
      {!errore && voci && voci.length > 0 && (
        <div className="qz-lb-rows">
          {voci.map((v) => (
            <div key={v.rank} className={v.rank <= 3 ? "qz-lb-row top" : "qz-lb-row"}>
              <span className="rank">{v.rank}</span>
              <span className="who"><b>{v.nickname}</b></span>
              <span className="pts">{v.attempts} {v.attempts === 1 ? "tentativo" : "tentativi"}</span>
              <span className="when col-hide">{v.when ? `alle ${oraArrivo(v.when)}` : ""}</span>
            </div>
          ))}
        </div>
      )}
      {utente === null && (
        <div className="hub-oggi__altre" style={{ marginTop: 16 }}>
          {locale ? <p>Il tuo risultato di oggi: <strong>{locale.testo || "giocata"}</strong>. </p> : null}
          <p>Per comparire in classifica serve un account.{" "}
            {isAuthConfigured() && <button type="button" className="hub-link" onClick={() => signInWithGoogle()}>Accedi con Google</button>}
          </p>
        </div>
      )}
    </div>
  );
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
  const [mode, setMode] = useState("oggi");
  const [period, setPeriod] = useState("week");
  const [entries, setEntries] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setEntries(null);
    setError(false);
    trackGameEvent("leaderboard_view", { mode, period });
    if (mode === "oggi") return;
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
          {mode !== "oggi" && <span className="qz-filters-sep" aria-hidden="true" />}
          {mode !== "oggi" && PERIODS.map((p) => (
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

        {mode === "oggi" && <ClassificaOggi />}

        {mode !== "oggi" && <div aria-live="polite">
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
        </div>}
      </div>

      <aside className="qz-side">
        <div className="qz-side-card qz-side-card--accent">
          <p className="eb">Entra in classifica</p>
          <p className="qz-side-body">
            Gioca una serie e invia il tuo risultato a fine partita. Il nickname è pubblico. Puoi giocare senza registrazione, o accedere per legare i punteggi al tuo account.
          </p>
          <div className="qz-side-cta">
            <a className="game-btn" href={{ oggi: "/quiz/indovina-la-regione", order: "/quiz/ordina" }[mode] || "/quiz/chi-e-maggiore"}>Gioca ora</a>
          </div>
        </div>

        <div className="qz-side-card">
          <p className="eb">Come si calcola</p>
          <p className="qz-side-body">{SCORING[mode]}</p>
        </div>

        {mode !== "oggi" && (
        <div className="qz-side-card">
          <p className="eb">Periodo</p>
          <p className="qz-side-body">
            Stai vedendo i punteggi dei <strong>{periodLabel}</strong>. La finestra settimanale scorre sugli
            ultimi sette giorni. I record personali restano salvati sul tuo dispositivo.
          </p>
        </div>
        )}
      </aside>
    </div>
  );
}
