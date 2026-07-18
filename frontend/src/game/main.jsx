import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { BarChart3 } from "lucide-react";
import CompareApp from "./compare.jsx";
import OrderApp from "./order.jsx";
import HubApp from "./hub.jsx";
import LeaderboardApp from "./leaderboard.jsx";
import { fetchJson, formatValue, prefersReducedMotion, trackGameEvent, SourceStrip, Modal } from "./shared.jsx";
import "./game.css";

const API = {
  regions: "/api/game/regions",
  daily: "/api/game/daily",
  dailyForDate: (iso) => `/api/game/daily/${iso}`,
  archive: "/api/game/archive",
  practice: "/api/game/practice",
  guess: "/api/game/guess",
};

const STORAGE_PROGRESS_PREFIX = "di-game-progress:";
const STORAGE_STATS_KEY = "di-game-stats";
const STORAGE_ONBOARDED_KEY = "di-game-onboarded";
const MAP_FRAME_ID = "game-map-frame";
const DIST_BUCKETS = ["1", "2", "3", "4", "5", "6", "fail"];

function normalize(value) {
  return (value || "")
    .toString()
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

function ordinal(rank) {
  return Number.isFinite(rank) ? `${rank}ª` : "n.d.";
}

function loadStats() {
  try {
    const raw = window.localStorage.getItem(STORAGE_STATS_KEY);
    if (!raw) throw new Error("empty");
    const parsed = JSON.parse(raw);
    return { played: 0, wins: 0, streak: 0, maxStreak: 0, lastWonPuzzleId: null, distribution: {}, ...parsed };
  } catch {
    return { played: 0, wins: 0, streak: 0, maxStreak: 0, lastWonPuzzleId: null, distribution: {} };
  }
}

function saveStats(stats) {
  try {
    window.localStorage.setItem(STORAGE_STATS_KEY, JSON.stringify(stats));
  } catch {
    // localStorage non disponibile: le statistiche restano solo in memoria per la sessione.
  }
}

function loadProgress(puzzleId) {
  try {
    const raw = window.localStorage.getItem(STORAGE_PROGRESS_PREFIX + puzzleId);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function saveProgress(puzzleId, progress) {
  try {
    window.localStorage.setItem(STORAGE_PROGRESS_PREFIX + puzzleId, JSON.stringify(progress));
  } catch {
    // Idem: modalità privata o quota piena, il gioco resta giocabile senza persistenza.
  }
}

function comparisonArrow(comparison) {
  if (comparison === "higher") return "↑";
  if (comparison === "lower") return "↓";
  if (comparison === "equal") return "=";
  return "?";
}

function comparisonText(comparison) {
  if (comparison === "higher") return "più alta della misteriosa";
  if (comparison === "lower") return "più bassa della misteriosa";
  if (comparison === "equal") return "uguale alla misteriosa";
  return "dato non disponibile";
}

function countdownParts(targetIso, nowMs) {
  if (!targetIso) return null;
  const diff = new Date(targetIso).getTime() - nowMs;
  if (!Number.isFinite(diff)) return null;
  const totalSec = Math.max(0, Math.floor(diff / 1000));
  const h = String(Math.floor(totalSec / 3600)).padStart(2, "0");
  const m = String(Math.floor((totalSec % 3600) / 60)).padStart(2, "0");
  const s = String(totalSec % 60).padStart(2, "0");
  return `${h}:${m}:${s}`;
}

function GameApp() {
  const [regions, setRegions] = useState([]);
  const [mode, setMode] = useState("daily"); // daily | practice | archive
  const [archiveDate, setArchiveDate] = useState(null);
  const [archiveList, setArchiveList] = useState(null);
  const [puzzle, setPuzzle] = useState(null);
  const [clues, setClues] = useState([]);
  const [guesses, setGuesses] = useState([]);
  const [status, setStatus] = useState("loading"); // loading | playing | won | lost | error
  const [solution, setSolution] = useState(null);
  const [recap, setRecap] = useState(null);
  const [query, setQuery] = useState("");
  const [highlighted, setHighlighted] = useState(-1);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [shareCopied, setShareCopied] = useState(false);
  const [shake, setShake] = useState(false);
  const [liveMessage, setLiveMessage] = useState("");
  const [stats, setStats] = useState(loadStats);
  const [now, setNow] = useState(() => Date.now());
  const [showOnboarding, setShowOnboarding] = useState(() => {
    try {
      return !window.localStorage.getItem(STORAGE_ONBOARDED_KEY);
    } catch {
      return false;
    }
  });
  const [showStats, setShowStats] = useState(false);
  const [showArchive, setShowArchive] = useState(false);

  const statsRecordedRef = useRef(false);
  const stateRef = useRef({ status: "loading", submitting: false });
  const cluesEndRef = useRef(null);

  const regionByKey = useMemo(() => {
    const map = {};
    regions.forEach((r) => { map[r.region_key] = r.region; });
    return map;
  }, [regions]);

  const suggestions = useMemo(() => {
    const q = normalize(query.trim());
    if (!q) return [];
    return regions
      .filter((r) => normalize(r.region).includes(q))
      .filter((r) => !guesses.some((g) => g.region_key === r.region_key))
      .slice(0, 6);
  }, [query, regions, guesses]);

  useEffect(() => {
    fetchJson(API.regions).then((data) => setRegions(data.regions || [])).catch(() => setRegions([]));
  }, []);

  useEffect(() => {
    if (mode === "archive" && !archiveDate) return;
    startGame(mode, { date: archiveDate });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, archiveDate]);

  useEffect(() => {
    stateRef.current = { status, submitting };
  }, [status, submitting]);

  useEffect(() => {
    setHighlighted(-1);
  }, [query]);

  useEffect(() => {
    if (clues.length > 1) {
      cluesEndRef.current?.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "nearest" });
    }
  }, [clues.length]);

  useEffect(() => {
    const isResult = status === "won" || status === "lost";
    if (mode !== "daily" || !isResult || !puzzle?.next_puzzle_at) return undefined;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [mode, status, puzzle]);

  useEffect(() => {
    if (showArchive && archiveList === null) {
      fetchJson(API.archive)
        .then((d) => setArchiveList(d.puzzles || []))
        .catch(() => setArchiveList([]));
    }
  }, [showArchive, archiveList]);

  function startGame(kind, opts = {}) {
    setError(null);
    setStatus("loading");
    setSolution(null);
    setRecap(null);
    setShareCopied(false);
    setLiveMessage("");
    statsRecordedRef.current = false;

    let load;
    if (kind === "practice") load = fetchJson(API.practice);
    else if (kind === "archive") load = fetchJson(API.dailyForDate(opts.date));
    else load = fetchJson(API.daily);

    load
      .then((data) => {
        setPuzzle(data);
        if (kind !== "practice") {
          const saved = loadProgress(data.puzzle_id);
          if (saved) {
            setClues(saved.clues);
            setGuesses(saved.guesses);
            setSolution(saved.solution || null);
            setRecap(saved.recap || null);
            statsRecordedRef.current = Boolean(saved.statsRecorded);
            setStatus(saved.status);
            return;
          }
        }
        setClues(data.clue ? [data.clue] : []);
        setGuesses([]);
        setStatus("playing");
        trackGameEvent("game_start", { mode: kind });
      })
      .catch(() => {
        setError(
          kind === "archive"
            ? "Questa sfida non è disponibile."
            : "Non è stato possibile caricare la sfida. Riprova tra poco."
        );
        setStatus("error");
      });
  }

  function persistProgress(nextClues, nextGuesses, nextStatus, nextSolution, nextRecap) {
    if (mode === "practice" || !puzzle) return;
    saveProgress(puzzle.puzzle_id, {
      clues: nextClues,
      guesses: nextGuesses,
      status: nextStatus,
      solution: nextSolution,
      recap: nextRecap,
      statsRecorded: statsRecordedRef.current,
    });
  }

  function recordStats(won, attemptCount) {
    if (mode !== "daily" || statsRecordedRef.current) return;
    statsRecordedRef.current = true;
    setStats((prev) => {
      const next = {
        played: prev.played + 1,
        wins: prev.wins + (won ? 1 : 0),
        streak: won ? prev.streak + 1 : 0,
        maxStreak: won ? Math.max(prev.maxStreak, prev.streak + 1) : prev.maxStreak,
        lastWonPuzzleId: won ? puzzle.puzzle_id : prev.lastWonPuzzleId,
        distribution: { ...prev.distribution },
      };
      const bucket = won ? String(attemptCount) : "fail";
      next.distribution[bucket] = (next.distribution[bucket] || 0) + 1;
      saveStats(next);
      return next;
    });
  }

  function submitGuess(regionKey) {
    if (!puzzle || stateRef.current.submitting || stateRef.current.status !== "playing") return;
    const attempt = guesses.length + 1;
    setSubmitting(true);
    setError(null);
    fetchJson(API.guess, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ puzzle_id: puzzle.puzzle_id, region_key: regionKey, attempt }),
    })
      .then((result) => {
        const nextGuesses = [...guesses, result];
        const nextClues = result.next_clue ? [...clues, result.next_clue] : clues;
        const nextStatus = result.finished ? (result.correct ? "won" : "lost") : "playing";
        setGuesses(nextGuesses);
        setClues(nextClues);
        setStatus(nextStatus);
        setQuery("");
        setHighlighted(-1);
        trackGameEvent("game_guess", { mode, attempt, correct: result.correct });

        const guessedName = regionByKey[regionKey] || result.region;
        if (result.correct) {
          setLiveMessage(`Hai indovinato! La regione era ${guessedName}.`);
        } else if (result.finished) {
          setLiveMessage(`Tentativi esauriti. La regione era ${result.solution?.region || ""}.`);
        } else {
          setLiveMessage(`Tentativo ${attempt}: ${guessedName} è sbagliata. Nuovo indizio rivelato.`);
          setShake(true);
          window.setTimeout(() => setShake(false), 420);
        }

        if (result.finished) {
          setSolution(result.solution);
          setRecap(result.recap);
          recordStats(result.correct, attempt);
          trackGameEvent("game_finish", { mode, won: result.correct, attempts: attempt });
        }
        persistProgress(nextClues, nextGuesses, nextStatus, result.solution, result.recap);
      })
      .catch(() => setError("Il tentativo non è andato a buon fine. Riprova."))
      .finally(() => setSubmitting(false));
  }

  useMapInteractions({ regions, guesses, status, solution, onGuess: submitGuess, submitting });

  const attemptsLeft = puzzle ? puzzle.attempts_total - guesses.length : 0;
  const finished = status === "won" || status === "lost";

  function shareText() {
    if (!puzzle || mode !== "daily") return "";
    const grid = guesses.map((g) => (g.correct ? "🟩" : "🟥")).join("");
    const outcome = status === "won" ? `${guesses.length}/${puzzle.attempts_total}` : `X/${puzzle.attempts_total}`;
    return `Indovina la Regione #${puzzle.number} ${outcome}\n${grid}\ndivarioitalia.it/quiz/indovina-la-regione`;
  }

  async function handleShare() {
    const text = shareText();
    if (!text) return;
    trackGameEvent("game_share", { mode });
    if (navigator.share) {
      try {
        await navigator.share({ text });
        return;
      } catch {
        // L'utente ha annullato la condivisione nativa: proviamo con il clipboard.
      }
    }
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(() => {
        setShareCopied(true);
        window.setTimeout(() => setShareCopied(false), 2500);
      });
    }
  }

  function openStats() {
    setShowStats(true);
    trackGameEvent("game_stats_open", { mode });
  }

  function openArchive() {
    setShowArchive(true);
    trackGameEvent("game_archive_open", {});
  }

  function pickArchiveDate(iso) {
    setShowArchive(false);
    setArchiveDate(iso);
    setMode("archive");
  }

  function backToToday() {
    setArchiveDate(null);
    setMode("daily");
  }

  const highlightBucket = mode === "daily" && finished ? (status === "won" ? String(guesses.length) : "fail") : null;

  return (
    <div className="game-app">
      <div className="game-toolbar" role="tablist" aria-label="Modalità di gioco">
        <button
          type="button"
          role="tab"
          aria-selected={mode === "daily"}
          className={mode === "daily" ? "game-tab is-active" : "game-tab"}
          onClick={backToToday}
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
        <button type="button" className="game-tab game-tab--ghost" onClick={openArchive}>
          Sfide passate
        </button>
        {mode === "practice" && status !== "loading" && (
          <button type="button" className="game-btn game-btn--ghost" onClick={() => startGame("practice")}>
            Nuova partita
          </button>
        )}
        <span className="game-toolbar-spacer" />
        <button type="button" className="game-icon-btn" onClick={openStats} aria-label="Statistiche">
          <BarChart3 size={16} strokeWidth={2} />
        </button>
        <button
          type="button"
          className="game-icon-btn"
          onClick={() => setShowOnboarding(true)}
          aria-label="Come si gioca"
        >
          ?
        </button>
      </div>

      <div className="visually-hidden" aria-live="polite">{liveMessage}</div>

      {status === "loading" && (
        <div aria-hidden="true">
          <div className="game-head">
            <span className="skel-bar" style={{ height: 22, width: "40%" }} />
            <div className="game-attempts">
              {Array.from({ length: 6 }).map((_, i) => (
                <span key={i} className="seg" />
              ))}
            </div>
          </div>
          <div className="skel-bars" style={{ marginTop: 18 }}>
            <span style={{ height: 96 }} />
            <span style={{ height: 96 }} />
          </div>
        </div>
      )}
      {status === "error" && <p className="game-error">{error}</p>}

      {(status === "playing" || finished) && puzzle && (
        <>
          <header className="game-head">
            <h2>
              {mode === "daily" && `Sfida #${puzzle.number}`}
              {mode === "practice" && "Allenamento"}
              {mode === "archive" && `Sfida #${puzzle.number} · archivio`}
              {puzzle.date && <span className="game-date"> · {puzzle.date}</span>}
            </h2>
            <div className="game-attempts-row">
              <span className="game-attempts-label">
                {finished ? "Partita conclusa" : `Tentativo ${guesses.length + 1} di ${puzzle.attempts_total}`}
              </span>
              <div className="game-attempts" aria-hidden="true">
                {Array.from({ length: puzzle.attempts_total }).map((_, i) => {
                  const g = guesses[i];
                  const cls = !g ? "seg" : g.correct ? "seg is-correct" : "seg is-wrong";
                  return <span key={i} className={cls} />;
                })}
              </div>
            </div>
          </header>

          {/* La mappa (.game-map-frame, id="game-map-frame") è il fratello server-
              renderizzato di #game-root: game.html la include via
              {% include "_italy_map.html" %} dentro lo stesso .game-layout a due
              colonne. Non è JSX perché duplicare ~60KB di path geografici nel
              bundle del gioco non avrebbe senso; useMapInteractions() la rende
              interattiva dall'esterno con querySelector/addEventListener. */}
          <div className="game-panel">
            <section className="game-clues" aria-label="Indizi">
              {clues.map((clue, i) => {
                const isLast = i === clues.length - 1;
                return (
                  <article
                    key={clue.id}
                    className={isLast && status === "playing" ? "clue-card is-latest" : "clue-card"}
                    ref={isLast ? cluesEndRef : null}
                  >
                    {isLast && status === "playing" && i > 0 && <span className="clue-badge">Nuovo</span>}
                    <span className="clue-index">Indizio {i + 1}</span>
                    <h3>{clue.name}</h3>
                    <p className="clue-meta">{clue.macro_area} · {clue.theme}</p>
                    {clue.description && (
                      <p className="clue-description">
                        <strong>Che cosa misura.</strong> {clue.description}
                      </p>
                    )}
                    {clue.value_explanation && (
                      <p className="clue-value-hint">
                        <strong>Come leggere il valore.</strong> {clue.value_explanation}
                      </p>
                    )}
                    {clue.reading && (
                      <p className="clue-reading">
                        <strong>Come leggere la posizione.</strong> {clue.reading}
                      </p>
                    )}
                    <SourceStrip year={clue.year} sourceLabel={clue.source_label} sourceUrl={clue.source_url} />
                    <div className="clue-stats">
                      <span className="clue-value">{formatValue(clue.value, clue.unit)}</span>
                      <span className="clue-rank">{ordinal(clue.rank)} su {clue.region_count}</span>
                    </div>
                  </article>
                );
              })}
            </section>

            {status === "playing" && (
              <section className="game-input" aria-label="Indovina la regione">
                <label htmlFor="game-guess-input">La tua ipotesi</label>
                <div className={shake ? "game-input-row is-shake" : "game-input-row"}>
                  <input
                    id="game-guess-input"
                    type="text"
                    autoComplete="off"
                    role="combobox"
                    aria-expanded={suggestions.length > 0}
                    aria-controls="game-suggestions-list"
                    placeholder="Scrivi il nome di una regione..."
                    value={query}
                    disabled={submitting}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "ArrowDown") {
                        e.preventDefault();
                        setHighlighted((h) => Math.min(h + 1, suggestions.length - 1));
                      } else if (e.key === "ArrowUp") {
                        e.preventDefault();
                        setHighlighted((h) => Math.max(h - 1, 0));
                      } else if (e.key === "Enter") {
                        if (highlighted >= 0 && suggestions[highlighted]) {
                          submitGuess(suggestions[highlighted].region_key);
                        } else if (suggestions.length === 1) {
                          submitGuess(suggestions[0].region_key);
                        }
                      } else if (e.key === "Escape") {
                        setHighlighted(-1);
                        setQuery("");
                      }
                    }}
                  />
                </div>
                {suggestions.length > 0 && (
                  <ul className="game-suggestions" id="game-suggestions-list" role="listbox">
                    {suggestions.map((r, i) => (
                      <li key={r.region_key} role="option" aria-selected={i === highlighted}>
                        <button
                          type="button"
                          className={i === highlighted ? "is-highlighted" : ""}
                          disabled={submitting}
                          onMouseEnter={() => setHighlighted(i)}
                          onClick={() => submitGuess(r.region_key)}
                        >
                          {r.region}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
                {error && <p className="game-error">{error}</p>}
              </section>
            )}

            {guesses.length > 0 && (
              <section className="game-history" aria-label="Tentativi">
                {guesses.map((g, i) => (
                  <div key={i} className={g.correct ? "guess-row is-correct" : "guess-row is-wrong"}>
                    <strong>{i + 1}. {regionByKey[g.region_key] || g.region}</strong>
                    {!g.correct && (
                      <ul className="guess-feedback">
                        {g.feedback.map((f) => (
                          <li key={f.id}>
                            <span className="guess-symbol">{comparisonArrow(f.comparison)}</span>
                            <span className="guess-feedback-body">
                              <strong>{f.name}</strong>
                              <span className="guess-feedback-detail">
                                {formatValue(f.guess_value, f.unit)}
                                {Number.isFinite(f.guess_rank) && ` · ${ordinal(f.guess_rank)} su ${f.region_count}`}
                                {" "}({comparisonText(f.comparison)}
                                {Number.isFinite(f.mystery_rank) && `, misteriosa ${ordinal(f.mystery_rank)}`})
                              </span>
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                    {g.ripartizione_hint && !g.correct && (
                      <p className="guess-ripartizione">
                        {g.ripartizione_hint.same
                          ? "Stessa ripartizione geografica della regione misteriosa."
                          : "Ripartizione geografica diversa da quella misteriosa."}
                      </p>
                    )}
                  </div>
                ))}
              </section>
            )}

            {finished && solution && (
              <ResultPanel
                status={status}
                mode={mode}
                puzzle={puzzle}
                solution={solution}
                recap={recap}
                stats={stats}
                highlightBucket={highlightBucket}
                shareCopied={shareCopied}
                onShare={handleShare}
                countdown={mode === "daily" ? countdownParts(puzzle.next_puzzle_at, now) : null}
                onNewPractice={mode === "practice" ? () => startGame("practice") : null}
              />
            )}
          </div>
        </>
      )}

      {showOnboarding && (
        <OnboardingModal
          onClose={() => {
            setShowOnboarding(false);
            try {
              window.localStorage.setItem(STORAGE_ONBOARDED_KEY, "1");
            } catch {
              // Niente di grave: il modal si riapre alla prossima visita.
            }
          }}
        />
      )}

      {showStats && <StatsModal stats={stats} onClose={() => setShowStats(false)} />}

      {showArchive && (
        <ArchiveModal
          list={archiveList}
          currentPuzzleId={puzzle?.puzzle_id}
          onPick={pickArchiveDate}
          onClose={() => setShowArchive(false)}
        />
      )}
    </div>
  );
}

function DistributionChart({ distribution, highlightBucket }) {
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

function ResultPanel({
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
            <tr><th>Indicatore</th><th>{solution.region}</th><th>Media Italia</th></tr>
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

function OnboardingModal({ onClose }) {
  return (
    <Modal title="Come si gioca" onClose={onClose} labelledBy="game-onboarding-title">
      <ol className="game-onboarding-steps">
        <li>
          <strong>Un indizio alla volta.</strong> Ogni sfida nasconde una regione italiana dietro sei indicatori
          Istat, uno per ogni macro-area: economia, lavoro e istruzione, società, ambiente, demografia e
          salute, istituzioni.
        </li>
        <li>
          <strong>Indovina o sbaglia, impari comunque.</strong> Ogni tentativo sbagliato rivela un nuovo indizio
          e ti dice se il tuo valore è più alto o più basso di quello della regione misteriosa. Dal terzo
          errore scopri anche la ripartizione geografica.
        </li>
        <li>
          <strong>Sei tentativi.</strong> Alla fine trovi il profilo completo della regione, con tutti gli
          indicatori usati e il confronto con la media nazionale.
        </li>
      </ol>
      <button type="button" className="game-btn" onClick={onClose}>Ho capito, gioco</button>
    </Modal>
  );
}

function StatsModal({ stats, onClose }) {
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

function ArchiveModal({ list, currentPuzzleId, onPick, onClose }) {
  return (
    <Modal title="Sfide passate" onClose={onClose} labelledBy="game-archive-title">
      {list === null && (
        <div className="skel-bars" style={{ marginTop: 0 }} aria-hidden="true">
          <span style={{ height: 44 }} />
          <span style={{ height: 44 }} />
          <span style={{ height: 44 }} />
        </div>
      )}
      {list !== null && list.length === 0 && <p>Nessuna sfida passata disponibile ancora.</p>}
      {list !== null && list.length > 0 && (
        <ul className="game-archive-list">
          {list.map((item) => (
            <li key={item.date}>
              <button
                type="button"
                className={currentPuzzleId === `daily:${item.date}` ? "is-active" : ""}
                onClick={() => onPick(item.date)}
              >
                <span>Sfida #{item.number}</span>
                <span>{item.date}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Modal>
  );
}

/**
 * La mappa è markup SVG statico, iniettato lato server dallo stesso partial
 * usato da /regioni (app/templates/_italy_map.html), non un componente React:
 * evita di duplicare ~60KB di path geografici nel bundle del gioco. Questo
 * hook la rende interattiva "dall'esterno" tramite DOM API imperative:
 * click/tastiera per tentare, tooltip col nome regione, classi di stato.
 */
function useMapInteractions({ regions, guesses, status, solution, onGuess, submitting }) {
  const latest = useRef({ onGuess, status, submitting });
  useEffect(() => {
    latest.current = { onGuess, status, submitting };
  });

  const regionNameByKey = useMemo(() => {
    const map = {};
    regions.forEach((r) => { map[r.region_key] = r.region; });
    return map;
  }, [regions]);

  useEffect(() => {
    const frame = document.getElementById(MAP_FRAME_ID);
    if (!frame) return undefined;
    const paths = Array.from(frame.querySelectorAll(".rmap-region"));
    const tooltip = frame.querySelector(".rmap-tooltip");

    function handleActivate(key) {
      const { onGuess: guess, status: currentStatus, submitting: busy } = latest.current;
      if (currentStatus !== "playing" || busy) return;
      guess(key);
    }

    function showTooltip(name, evt) {
      if (!tooltip || !name) return;
      tooltip.textContent = name;
      tooltip.hidden = false;
      moveTooltip(evt);
    }

    function moveTooltip(evt) {
      if (!tooltip || tooltip.hidden) return;
      const wrap = frame.getBoundingClientRect();
      const x = evt.clientX - wrap.left + 14;
      const y = evt.clientY - wrap.top + 14;
      tooltip.style.left = `${Math.max(8, Math.min(x, wrap.width - tooltip.offsetWidth - 8))}px`;
      tooltip.style.top = `${y}px`;
    }

    function hideTooltip() {
      if (tooltip) tooltip.hidden = true;
    }

    const cleanups = paths.map((path) => {
      const key = path.getAttribute("data-key");
      const name = regionNameByKey[key];
      if (name) {
        path.setAttribute("role", "button");
        path.setAttribute("tabindex", "0");
        path.setAttribute("aria-label", `Indovina ${name}`);
      }
      const onClick = () => handleActivate(key);
      const onKeydown = (evt) => {
        if (evt.key === "Enter" || evt.key === " ") {
          evt.preventDefault();
          handleActivate(key);
        }
      };
      const onEnter = (evt) => showTooltip(name, evt);
      const onMove = (evt) => moveTooltip(evt);
      const onFocus = (evt) => showTooltip(name, evt);
      path.addEventListener("click", onClick);
      path.addEventListener("keydown", onKeydown);
      path.addEventListener("mouseenter", onEnter);
      path.addEventListener("mousemove", onMove);
      path.addEventListener("mouseleave", hideTooltip);
      path.addEventListener("focus", onFocus);
      path.addEventListener("blur", hideTooltip);
      return () => {
        path.removeEventListener("click", onClick);
        path.removeEventListener("keydown", onKeydown);
        path.removeEventListener("mouseenter", onEnter);
        path.removeEventListener("mousemove", onMove);
        path.removeEventListener("mouseleave", hideTooltip);
        path.removeEventListener("focus", onFocus);
        path.removeEventListener("blur", hideTooltip);
      };
    });
    return () => cleanups.forEach((fn) => fn());
  }, [regionNameByKey]);

  useEffect(() => {
    const frame = document.getElementById(MAP_FRAME_ID);
    if (!frame) return;
    const paths = frame.querySelectorAll(".rmap-region");
    const finished = status === "won" || status === "lost";
    paths.forEach((path) => {
      const key = path.getAttribute("data-key");
      path.classList.remove("is-clickable", "is-guessed-correct", "is-guessed-wrong", "is-mystery", "is-mystery-reveal");
      const guess = guesses.find((g) => g.region_key === key);
      if (guess) {
        path.classList.add(guess.correct ? "is-guessed-correct" : "is-guessed-wrong");
      } else if (status === "playing") {
        path.classList.add("is-clickable");
      }
      if (finished && solution && key === solution.region_key) {
        path.classList.add("is-mystery");
        if (!prefersReducedMotion()) path.classList.add("is-mystery-reveal");
      }
    });
  }, [guesses, status, solution]);
}

// Un solo bundle per tutte le pagine del gioco: ogni template server ha il
// suo elemento root e il mount dell'app corrispondente scatta solo dove
// quell'elemento esiste (sulle altre pagine è un no-op).
const root = document.getElementById("game-root");
if (root) {
  createRoot(root).render(<GameApp />);
}

const compareRoot = document.getElementById("compare-root");
if (compareRoot) {
  createRoot(compareRoot).render(<CompareApp />);
}

const orderRoot = document.getElementById("order-root");
if (orderRoot) {
  createRoot(orderRoot).render(<OrderApp />);
}

const hubRoot = document.getElementById("hub-root");
if (hubRoot) {
  createRoot(hubRoot).render(<HubApp />);
}

const leaderboardRoot = document.getElementById("leaderboard-root");
if (leaderboardRoot) {
  createRoot(leaderboardRoot).render(<LeaderboardApp />);
}
