import React, { useEffect, useRef, useState } from "react";
import {
  fetchJson,
  formatValue,
  trackGameEvent,
  SourceStrip,
  SubmitScoreModal,
  prefersReducedMotion,
  postGame,
  notifyAchievements,
  FinePartita,
} from "./shared.jsx";
import { oggiRoma, segnaGiocata } from "./oggi.js";

const API = {
  round: (count, token) =>
    `/api/game/order/round?count=${count}${token ? `&token=${encodeURIComponent(token)}` : ""}`,
  answer: "/api/game/order/answer",
};

const STORAGE_STATS_KEY = "di-order-stats";
const STORAGE_ONBOARDED_KEY = "di-order-onboarded";

function loadStats() {
  try {
    const raw = window.localStorage.getItem(STORAGE_STATS_KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    return { bestScore3: 0, bestScore5: 0, totalRounds: 0, totalPositionsCorrect: 0, ...parsed };
  } catch {
    return { bestScore3: 0, bestScore5: 0, totalRounds: 0, totalPositionsCorrect: 0 };
  }
}

function saveStats(stats) {
  try {
    window.localStorage.setItem(STORAGE_STATS_KEY, JSON.stringify(stats));
  } catch {
    // localStorage non disponibile
  }
}

export default function OrderApp() {
  const [mode, setMode] = useState("daily"); // daily | practice
  const [level, setLevel] = useState("regioni"); // regioni | stessa_regione | province
  const [count, setCount] = useState(3); // 3 | 5 per allenamento
  const [round, setRound] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | loading | ordering | revealed | error
  const [orderKeys, setOrderKeys] = useState([]);
  const [dragIndex, setDragIndex] = useState(null);
  const [selectedIdx, setSelectedIdx] = useState(null);
  const [announcement, setAnnouncement] = useState("");
  const [result, setResult] = useState(null);
  const [stats, setStats] = useState(loadStats);
  const [sessionBest, setSessionBest] = useState(0);
  const [showScoreModal, setShowScoreModal] = useState(false);
  const [started, setStarted] = useState(false);
  const [hasPlayedBefore] = useState(() => {
    try {
      return !!window.localStorage.getItem(STORAGE_ONBOARDED_KEY);
    } catch {
      return false;
    }
  });

  const submittingRef = useRef(false);
  const tokenRef = useRef(null);
  const promptedBestRef = useRef(0);

  useEffect(() => {
    if (!started) return;
    trackGameEvent("order_start", { mode, level, count: mode === "daily" ? 5 : count });
    if (mode === "daily") {
      loadDailySession(level);
    } else {
      loadPracticeRound(count);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, level, count, started]);

  function startGame() {
    try {
      window.localStorage.setItem(STORAGE_ONBOARDED_KEY, "1");
    } catch {
      // localStorage non disponibile
    }
    setStarted(true);
  }

  function loadDailySession(lvl) {
    window.scrollTo({ top: 0, behavior: prefersReducedMotion() ? "auto" : "smooth" });
    setStatus("loading");
    setResult(null);
    setDragIndex(null);
    setSelectedIdx(null);
    submittingRef.current = false;
    fetchJson(`/api/game/order/daily/session?level=${encodeURIComponent(lvl)}${tokenRef.current ? `&token=${encodeURIComponent(tokenRef.current)}` : ""}`)
      .then((data) => {
        tokenRef.current = data.token;
        setRound(data);
        setOrderKeys((data.territories || []).map((t) => t.key));
        setStatus("ordering");
      })
      .catch(() => setStatus("error"));
  }

  function loadPracticeRound(n) {
    window.scrollTo({ top: 0, behavior: prefersReducedMotion() ? "auto" : "smooth" });
    setStatus("loading");
    setResult(null);
    setDragIndex(null);
    setSelectedIdx(null);
    submittingRef.current = false;
    fetchJson(API.round(n, tokenRef.current))
      .then((data) => {
        tokenRef.current = data.token;
        setRound(data);
        setOrderKeys((data.regions || []).map((r) => r.region_key));
        setStatus("ordering");
      })
      .catch(() => setStatus("error"));
  }

  function reloadCurrent() {
    if (mode === "daily") {
      loadDailySession(level);
    } else {
      loadPracticeRound(count);
    }
  }

  function handleRowClick(idx) {
    if (status !== "ordering") return;
    const terrs = round?.territories || round?.regions || [];
    const terrMap = Object.fromEntries(terrs.map((t) => [t.key || t.region_key, t]));
    const key = orderKeys[idx];
    const terr = terrMap[key];
    const name = terr ? (terr.name || terr.region) : `Elemento ${idx + 1}`;

    if (selectedIdx === null) {
      setSelectedIdx(idx);
      setAnnouncement(`Selezionato ${name} in posizione ${idx + 1}. Tocca la posizione di destinazione.`);
    } else if (selectedIdx === idx) {
      setSelectedIdx(null);
      setAnnouncement("Selezione annullata.");
    } else {
      const fromIdx = selectedIdx;
      const toIdx = idx;
      const fromKey = orderKeys[fromIdx];
      const fromTerr = terrMap[fromKey];
      const fromName = fromTerr ? (fromTerr.name || fromTerr.region) : `Elemento ${fromIdx + 1}`;

      setOrderKeys((prev) => {
        const next = [...prev];
        const [moved] = next.splice(fromIdx, 1);
        next.splice(toIdx, 0, moved);
        return next;
      });
      setSelectedIdx(null);
      setAnnouncement(`${fromName} spostato in posizione ${toIdx + 1}.`);
    }
  }

  function moveItem(index, direction, e) {
    if (e) e.stopPropagation();
    if (status !== "ordering") return;
    const target = index + direction;
    if (target < 0 || target >= orderKeys.length) return;
    const terrs = round?.territories || round?.regions || [];
    const terrMap = Object.fromEntries(terrs.map((t) => [t.key || t.region_key, t]));
    const key = orderKeys[index];
    const terr = terrMap[key];
    const name = terr ? (terr.name || terr.region) : `Elemento ${index + 1}`;

    setOrderKeys((prev) => {
      const next = [...prev];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
    setAnnouncement(`${name} spostato in posizione ${target + 1}.`);
  }

  function shuffleOrder() {
    if (status !== "ordering") return;
    setOrderKeys((prev) => {
      const next = [...prev];
      for (let i = next.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [next[i], next[j]] = [next[j], next[i]];
      }
      return next;
    });
    setSelectedIdx(null);
    setAnnouncement("Ordine mescolato.");
  }

  function handleDragStart(index) {
    if (status !== "ordering") return;
    setDragIndex(index);
  }

  function handleDragOver(e) {
    if (status !== "ordering") return;
    e.preventDefault();
  }

  function handleDrop(index) {
    if (status !== "ordering" || dragIndex === null || dragIndex === index) {
      setDragIndex(null);
      return;
    }
    const terrs = round?.territories || round?.regions || [];
    const terrMap = Object.fromEntries(terrs.map((t) => [t.key || t.region_key, t]));
    const key = orderKeys[dragIndex];
    const terr = terrMap[key];
    const name = terr ? (terr.name || terr.region) : `Elemento ${dragIndex + 1}`;

    setOrderKeys((prev) => {
      const next = [...prev];
      const [moved] = next.splice(dragIndex, 1);
      next.splice(index, 0, moved);
      return next;
    });
    setDragIndex(null);
    setAnnouncement(`${name} spostato in posizione ${index + 1}.`);
  }

  function confirmOrder() {
    const totalCount = mode === "daily" ? 5 : round?.count;
    if (status !== "ordering" || orderKeys.length !== totalCount || submittingRef.current) return;
    submittingRef.current = true;
    setStatus("loading");

    const isDaily = mode === "daily";
    const url = isDaily ? "/api/game/order/daily/answer" : API.answer;
    const body = isDaily
      ? { level, region_keys: orderKeys, token: tokenRef.current }
      : {
          indicator_id: round.indicator.id,
          year: round.indicator.year,
          region_keys: orderKeys,
          token: tokenRef.current,
        };

    postGame(url, body)
      .then((data) => {
        setResult(data);
        setStatus("revealed");
        tokenRef.current = data.token;
        notifyAchievements(data.achievements);
        setStats((prev) => {
          const currentCount = mode === "daily" ? 5 : round.count;
          const bestKey = currentCount === 3 ? "bestScore3" : "bestScore5";
          const next = {
            ...prev,
            [bestKey]: Math.max(prev[bestKey], data.score),
            totalRounds: prev.totalRounds + 1,
            totalPositionsCorrect: prev.totalPositionsCorrect + data.score,
          };
          saveStats(next);
          return next;
        });
        if (data.session) {
          setSessionBest(data.session.best);
          const isPerfect = data.score === data.total;
          if (!isDaily && !isPerfect && data.session.best > promptedBestRef.current && data.session.best >= 2) {
            promptedBestRef.current = data.session.best;
            setShowScoreModal(true);
          }
        }
        trackGameEvent("order_answer", { mode, level, score: data.score, total: data.total });
        if (isDaily) segnaGiocata("order", oggiRoma(), { ok: data.score === data.total, testo: `${data.score} su ${data.total} al posto giusto` });
      })
      .catch(() => setStatus("error"));
  }

  const currentCount = mode === "daily" ? 5 : count;
  const best = currentCount === 3 ? stats.bestScore3 : stats.bestScore5;
  const resultBySide = result
    ? Object.fromEntries((result.positions || []).map((p) => [p.region_key, p]))
    : {};
  const territoryList = round?.territories || round?.regions || [];
  const territoryByKey = Object.fromEntries(
    territoryList.map((t) => [t.key || t.region_key, t])
  );

  return (
    <div className="order-app">
      <div className="aria-live-announcer" aria-live="polite" className="visually-hidden">
        {announcement}
      </div>

      <div className="order-toolbar">
        <div className="order-modes" role="tablist" aria-label="Modalità di gioco">
          <button
            type="button"
            role="tab"
            aria-selected={mode === "daily"}
            className={mode === "daily" ? "game-tab is-active" : "game-tab"}
            onClick={() => setMode("daily")}
          >
            Sfida del giorno
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "practice"}
            className={mode === "practice" ? "game-tab is-active" : "game-tab"}
            onClick={() => setMode("practice")}
          >
            Allenamento
          </button>
        </div>

        {mode === "daily" && (
          <div className="order-counts" role="tablist" aria-label="Livello sfida del giorno">
            {[
              { id: "regioni", label: "Regioni" },
              { id: "stessa_regione", label: "Stessa regione" },
              { id: "province", label: "Province" },
            ].map((lvl) => (
              <button
                key={lvl.id}
                type="button"
                role="tab"
                aria-selected={level === lvl.id}
                className={level === lvl.id ? "game-tab is-active" : "game-tab"}
                onClick={() => setLevel(lvl.id)}
              >
                {lvl.label}
              </button>
            ))}
          </div>
        )}

        {mode === "practice" && (
          <div className="order-counts" role="tablist" aria-label="Livello di difficoltà">
            {[3, 5].map((n) => (
              <button
                key={n}
                type="button"
                role="tab"
                aria-selected={count === n}
                className={count === n ? "game-tab is-active" : "game-tab"}
                onClick={() => setCount(n)}
              >
                {n} regioni
              </button>
            ))}
          </div>
        )}

        {mode === "practice" && sessionBest > 0 && (
          <button
            type="button"
            className="game-tab game-tab--ghost"
            style={{ marginLeft: "auto" }}
            onClick={() => setShowScoreModal(true)}
          >
            Entra in classifica
          </button>
        )}
      </div>

      {status === "idle" && (
        <div className="order-start">
          <h2>Ordina le regioni</h2>
          <ol className="game-onboarding-steps">
            <li>
              <strong>Tocca due volte, trascina o usa le frecce.</strong> Seleziona una riga e tocca la
              destinazione, trascina con l'icona ⋮⋮, oppure sposta ogni riga su o giù per ordinarle dal valore più alto al più basso.
            </li>
            <li>
              <strong>Verifica quando l'ordine ti convince.</strong> Vedrai la classifica reale con i
              valori Istat.
            </li>
            <li>
              <strong>Un punto per ogni posizione azzeccata.</strong> Gioca la sfida del giorno uguale per tutti o allenati liberamente.
            </li>
          </ol>
          <button type="button" className="game-btn" onClick={startGame}>
            {hasPlayedBefore ? "Inizia" : "Inizia a giocare"}
          </button>
        </div>
      )}

      {status === "error" && (
        <div className="order-status">
          <p className="game-error">Qualcosa non ha funzionato. Riprova.</p>
          <button type="button" className="game-btn" onClick={reloadCurrent}>
            Riprova
          </button>
        </div>
      )}

      {round && status !== "error" && (
        <div className="order-layout">
          <div className="order-main">
            {mode === "daily" && status === "revealed" && result ? (
              <FinePartita
                won={result.score === result.total}
                titolo={
                  result.score === result.total
                    ? "Perfetto! 5 su 5 posizioni corrette."
                    : `${result.score} su 5 posizioni corrette.`
                }
                dettaglio={round.number ? `Sfida del giorno n. ${round.number}` : ""}
                dato={{
                  name: round.indicator.name,
                  value: null,
                  unit: round.indicator.unit,
                  year: round.indicator.year,
                  sourceLabel: result.indicator?.source_label || round.indicator.source_label,
                  sourceUrl: result.indicator?.source_url || round.indicator.source_url,
                  description: result.indicator?.description || round.indicator.description,
                  path: result.indicator?.path || round.indicator.path,
                }}
                territori={(round.territories || round.regions || []).map((t) => ({
                  name: t.name || t.region,
                  path:
                    t.region && t.name && t.name !== t.region
                      ? `/provincia/${t.key}`
                      : `/regione/${t.key || (t.region ? t.region.toLowerCase().replace(/ /g, "-") : "")}`,
                }))}
                nextPuzzleAt={round.next_puzzle_at}
                condividi={{
                  gameName: "Ordina le regioni",
                  puzzleNumber: round.number,
                  esiti: orderKeys.map((k) => (resultBySide[k]?.correct ? "exact" : "miss")),
                  summary: `${result.score} su ${result.total}`,
                  url: typeof window !== "undefined" ? window.location.href : "",
                  eventParams: { level },
                }}
                onPlayAgain={() => {
                  setMode("practice");
                  setCount(5);
                }}
                playAgainLabel="Passa all'allenamento"
              />
            ) : (
              <>
                <div className="order-question">
                  <span className="order-kicker">
                    {mode === "daily"
                      ? `Sfida del giorno · Livello ${level === "stessa_regione" ? "stessa regione" : level}`
                      : "Trascina, tocca due volte o usa le frecce per ordinare"}
                  </span>
                  <h2>{round.indicator.name}</h2>
                  <p className="order-meta">
                    {round.indicator.macro_area && `${round.indicator.macro_area} · `}
                    {round.indicator.theme && `${round.indicator.theme} · `}
                    {round.indicator.unit && round.indicator.unit}
                  </p>
                  <SourceStrip
                    year={round.indicator.year}
                    sourceLabel={round.indicator.source_label}
                    sourceUrl={round.indicator.source_url}
                  />
                  <div className="quiz-explanation">
                    {round.indicator.description && (
                      <p className="quiz-description">
                        <strong>Che cosa misura.</strong> {round.indicator.description}
                      </p>
                    )}
                    {round.indicator.value_explanation && (
                      <p className="quiz-value-hint">
                        <strong>Come leggere il valore.</strong> {round.indicator.value_explanation}
                      </p>
                    )}
                    <p className="quiz-rule-note">
                      Ordina dal valore più alto al più basso, non dal risultato migliore al peggiore.
                    </p>
                  </div>
                </div>

                <div className="order-list" role="list">
                  {orderKeys.map((key, idx) => {
                    const terr = territoryByKey[key];
                    if (!terr) return null;
                    const revealed = status === "revealed" && resultBySide[key];
                    let cls = "order-row";
                    if (status === "ordering") cls += " is-draggable";
                    if (dragIndex === idx) cls += " is-dragging";
                    if (selectedIdx === idx) cls += " is-selected";
                    if (revealed) cls += revealed.correct ? " is-correct" : " is-wrong";

                    const displayName = terr.name || terr.region;
                    const regionName = terr.region && terr.name && terr.name !== terr.region ? terr.region : null;

                    return (
                      <div
                        key={key}
                        tabIndex={status === "ordering" ? 0 : -1}
                        role="listitem"
                        aria-selected={selectedIdx === idx}
                        className={cls}
                        draggable={status === "ordering"}
                        onClick={() => handleRowClick(idx)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            handleRowClick(idx);
                          }
                        }}
                        onDragStart={() => handleDragStart(idx)}
                        onDragOver={handleDragOver}
                        onDrop={() => handleDrop(idx)}
                        onDragEnd={() => setDragIndex(null)}
                      >
                        <span className="order-rank">{idx + 1}</span>
                        <div className="order-row-heading">
                          <strong className="order-row-name">{displayName}</strong>
                          {regionName && (
                            <span className="order-row-region">{regionName}</span>
                          )}
                        </div>
                        <span className="order-row-value">
                          {revealed ? formatValue(revealed.value, round.indicator.unit) : "nascosto"}
                          {revealed && (
                            <span className="order-row-status">
                              {revealed.correct ? "posizione corretta" : `era ${revealed.correct_position}ª`}
                            </span>
                          )}
                        </span>
                        <span className="order-row-controls">
                          {status === "ordering" && (
                            <>
                              <button
                                type="button"
                                className="order-move-btn"
                                aria-label={`Sposta ${displayName} più in alto`}
                                disabled={idx === 0}
                                onClick={(e) => moveItem(idx, -1, e)}
                              >
                                ▲
                              </button>
                              <button
                                type="button"
                                className="order-move-btn"
                                aria-label={`Sposta ${displayName} più in basso`}
                                disabled={idx === orderKeys.length - 1}
                                onClick={(e) => moveItem(idx, 1, e)}
                              >
                                ▼
                              </button>
                              <span className="order-handle" aria-hidden="true">⋮⋮</span>
                            </>
                          )}
                        </span>
                      </div>
                    );
                  })}
                </div>

                {status === "ordering" && (
                  <div className="order-actions">
                    <button type="button" className="game-btn" onClick={confirmOrder}>
                      Verifica ordine
                    </button>
                    <button type="button" className="game-btn game-btn--ghost" onClick={shuffleOrder}>
                      Mischia
                    </button>
                    {mode === "practice" && (
                      <button type="button" className="game-btn game-btn--ghost" onClick={() => loadPracticeRound(count)}>
                        Salta round
                      </button>
                    )}
                  </div>
                )}

                <div className="order-feedback" aria-live="polite">
                  {status === "revealed" && result && (
                    <p className={result.score === result.total ? "order-verdict is-perfect" : "order-verdict"}>
                      {result.score === result.total
                        ? `Perfetto! ${result.score} su ${result.total}.`
                        : `${result.score} su ${result.total} posizioni corrette.`}
                    </p>
                  )}
                </div>

                {mode === "practice" && status === "revealed" && result && (
                  <>
                    <div className="order-solution">
                      <h3>La classifica reale</h3>
                      <ol>
                        {result.correct_order.map((row) => (
                          <li key={row.region_key}>
                            <span>{row.region}</span>
                            <strong>{formatValue(row.value, round.indicator.unit)}</strong>
                          </li>
                        ))}
                      </ol>
                    </div>
                    <button type="button" className="game-btn order-next" onClick={() => loadPracticeRound(count)}>
                      {result.score === result.total ? "Avanti" : "Ricomincia"}
                    </button>
                  </>
                )}
              </>
            )}
          </div>

          <aside className="order-side">
            <div className="card">
              <p className="order-side-eyebrow">Punteggio</p>
              <div className="order-score-grid">
                <div>
                  <small>Record</small>
                  <strong>{best}/{currentCount}</strong>
                </div>
                <div>
                  <small>Serie perfetta</small>
                  <strong>{sessionBest}</strong>
                </div>
              </div>
            </div>
            <div className="card order-rules-card">
              <p className="order-side-eyebrow">Regole rapide</p>
              <ul>
                <li>+1 per ogni territorio nella posizione esatta</li>
                <li>Punteggio massimo: {currentCount}</li>
                <li>Tocca due volte o trascina per riordinare</li>
              </ul>
            </div>
          </aside>
        </div>
      )}

      {status === "loading" && !round && (
        <div aria-hidden="true">
          <div className="skel-bars" style={{ marginTop: 0 }}>
            <span style={{ height: 12, width: "55%" }} />
            <span style={{ height: 22, width: "70%" }} />
          </div>
          <div className="order-list" style={{ marginTop: 18 }}>
            {Array.from({ length: currentCount }).map((_, i) => (
              <span key={i} className="skel-bar" style={{ height: 56 }} />
            ))}
          </div>
        </div>
      )}

      {showScoreModal && (
        <SubmitScoreModal
          mode="order"
          token={tokenRef.current}
          score={sessionBest}
          scoreLabel={`${sessionBest} round perfetti di fila`}
          onClose={() => setShowScoreModal(false)}
        />
      )}
    </div>
  );
}
