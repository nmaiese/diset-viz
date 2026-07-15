import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./game.css";

const API = {
  regions: "/api/game/regions",
  daily: "/api/game/daily",
  practice: "/api/game/practice",
  guess: "/api/game/guess",
};

const STORAGE_PROGRESS_PREFIX = "di-game-progress:";
const STORAGE_STATS_KEY = "di-game-stats";
const MAP_FRAME_ID = "game-map-frame";

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(`Request failed: ${url}`);
  return response.json();
}

function normalize(value) {
  return (value || "")
    .toString()
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

function formatValue(value, unit) {
  if (value === null || value === undefined || !Number.isFinite(value)) return "n.d.";
  const decimals = Math.abs(value) >= 1000 ? 0 : 1;
  const formatted = value.toLocaleString("it-IT", { maximumFractionDigits: decimals, minimumFractionDigits: 0 });
  const lower = (unit || "").toLowerCase();
  if (lower.includes("percentuale")) return `${formatted}%`;
  return `${formatted} ${unit || ""}`.trim();
}

function loadStats() {
  try {
    const raw = window.localStorage.getItem(STORAGE_STATS_KEY);
    if (!raw) throw new Error("empty");
    return JSON.parse(raw);
  } catch {
    return { played: 0, wins: 0, streak: 0, maxStreak: 0, lastWonPuzzleId: null, distribution: {} };
  }
}

function saveStats(stats) {
  window.localStorage.setItem(STORAGE_STATS_KEY, JSON.stringify(stats));
}

function loadProgress(puzzleId) {
  try {
    const raw = window.localStorage.getItem(STORAGE_PROGRESS_PREFIX + puzzleId);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function saveProgress(puzzleId, progress) {
  try {
    window.localStorage.setItem(STORAGE_PROGRESS_PREFIX + puzzleId, JSON.stringify(progress));
  } catch {
    // localStorage non disponibile (modalità privata, quota piena): il gioco
    // resta funzionante, solo senza persistenza tra un refresh e l'altro.
  }
}

function comparisonLabel(comparison) {
  if (comparison === "higher") return { text: "più alta della misteriosa", symbol: "↑" };
  if (comparison === "lower") return { text: "più bassa della misteriosa", symbol: "↓" };
  if (comparison === "equal") return { text: "uguale", symbol: "=" };
  return { text: "dato non disponibile", symbol: "?" };
}

function GameApp() {
  const [regions, setRegions] = useState([]);
  const [mode, setMode] = useState("daily");
  const [puzzle, setPuzzle] = useState(null); // {puzzle_id, number, date, clues_total, attempts_total}
  const [clues, setClues] = useState([]); // indizi rivelati finora
  const [guesses, setGuesses] = useState([]); // esito di ogni tentativo
  const [status, setStatus] = useState("loading"); // loading | playing | won | lost
  const [solution, setSolution] = useState(null);
  const [recap, setRecap] = useState(null);
  const [query, setQuery] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [shareCopied, setShareCopied] = useState(false);
  const [stats, setStats] = useState(loadStats);

  const statsRecordedRef = useRef(false);
  const stateRef = useRef({ status: "loading", puzzleId: null, submitting: false });

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
    startGame(mode === "practice" ? "practice" : "daily");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  useEffect(() => {
    stateRef.current = { status, puzzleId: puzzle?.puzzle_id || null, submitting };
  }, [status, puzzle, submitting]);

  function startGame(kind) {
    setError(null);
    setStatus("loading");
    setSolution(null);
    setRecap(null);
    setShareCopied(false);
    statsRecordedRef.current = false;

    const load = kind === "practice" ? fetchJson(API.practice) : fetchJson(API.daily);
    load
      .then((data) => {
        setPuzzle(data);
        if (kind === "daily") {
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
      })
      .catch(() => {
        setError("Non è stato possibile caricare la sfida. Riprova tra poco.");
        setStatus("error");
      });
  }

  function persistDailyProgress(nextClues, nextGuesses, nextStatus, nextSolution, nextRecap) {
    if (mode !== "daily" || !puzzle) return;
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
    if (!puzzle || stateRef.current.submitting) return;
    if (stateRef.current.status !== "playing") return;
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
        if (result.finished) {
          setSolution(result.solution);
          setRecap(result.recap);
          recordStats(result.correct, attempt);
        }
        persistDailyProgress(nextClues, nextGuesses, nextStatus, result.solution, result.recap);
      })
      .catch(() => setError("Il tentativo non è andato a buon fine. Riprova."))
      .finally(() => setSubmitting(false));
  }

  useMapInteractions({ regions, guesses, status, solution, onGuess: submitGuess, submitting });

  const attemptsLeft = puzzle ? puzzle.attempts_total - guesses.length : 0;
  const guessedKeys = guesses.map((g) => g.region_key);

  function shareText() {
    if (!puzzle || mode !== "daily") return "";
    const grid = guesses
      .map((g) => (g.correct ? "🟩" : "🟥"))
      .join("");
    const outcome = status === "won" ? `${guesses.length}/${puzzle.attempts_total}` : `X/${puzzle.attempts_total}`;
    return `Indovina la Regione #${puzzle.number} ${outcome}\n${grid}\ndivarioitalia.it/gioco`;
  }

  function handleShare() {
    const text = shareText();
    if (!text || !navigator.clipboard) return;
    navigator.clipboard.writeText(text).then(() => {
      setShareCopied(true);
      window.setTimeout(() => setShareCopied(false), 2500);
    });
  }

  return (
    <div className="game-app">
      <div className="game-toolbar" role="tablist" aria-label="Modalità di gioco">
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
        {mode === "practice" && status !== "loading" && (
          <button type="button" className="game-btn game-btn--ghost" onClick={() => startGame("practice")}>
            Nuova partita
          </button>
        )}
      </div>

      {status === "loading" && <p className="game-loading">Preparazione della sfida...</p>}
      {status === "error" && <p className="game-error">{error}</p>}

      {(status === "playing" || status === "won" || status === "lost") && puzzle && (
        <>
          <header className="game-head">
            <h2>
              {mode === "daily" ? `Sfida #${puzzle.number}` : "Allenamento"}
              {mode === "daily" && puzzle.date && <span className="game-date"> · {puzzle.date}</span>}
            </h2>
            <div className="game-attempts" aria-label={`${attemptsLeft} tentativi rimasti su ${puzzle.attempts_total}`}>
              {Array.from({ length: puzzle.attempts_total }).map((_, i) => {
                const g = guesses[i];
                const cls = !g ? "dot" : g.correct ? "dot is-correct" : "dot is-wrong";
                return <span key={i} className={cls} />;
              })}
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
                {clues.map((clue, i) => (
                  <article key={clue.id} className="clue-card">
                    <span className="clue-index">Indizio {i + 1}</span>
                    <h3>{clue.name}</h3>
                    <p className="clue-meta">{clue.macro_area} · {clue.theme} · {clue.year}</p>
                    <p className="clue-value">{formatValue(clue.value, clue.unit)}</p>
                  </article>
                ))}
              </section>

              {status === "playing" && (
                <section className="game-input" aria-label="Indovina la regione">
                  <label htmlFor="game-guess-input">La tua ipotesi</label>
                  <div className="game-input-row">
                    <input
                      id="game-guess-input"
                      type="text"
                      autoComplete="off"
                      placeholder="Scrivi il nome di una regione..."
                      value={query}
                      disabled={submitting}
                      onChange={(e) => setQuery(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && suggestions.length === 1) {
                          submitGuess(suggestions[0].region_key);
                        }
                      }}
                    />
                  </div>
                  {suggestions.length > 0 && (
                    <ul className="game-suggestions">
                      {suggestions.map((r) => (
                        <li key={r.region_key}>
                          <button type="button" disabled={submitting} onClick={() => submitGuess(r.region_key)}>
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
                          {g.feedback.map((f) => {
                            const label = comparisonLabel(f.comparison);
                            return (
                              <li key={f.id}>
                                <span className="guess-symbol">{label.symbol}</span> {f.name}: {label.text}
                              </li>
                            );
                          })}
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

              {(status === "won" || status === "lost") && solution && (
                <section className="game-result">
                  <h3>{status === "won" ? "Hai indovinato!" : "Regione misteriosa non indovinata"}</h3>
                  <p className="game-result-region">
                    <a href={solution.path}>{solution.region}</a>
                  </p>
                  {mode === "daily" && (
                    <button type="button" className="game-btn" onClick={handleShare}>
                      {shareCopied ? "Copiato!" : "Condividi il risultato"}
                    </button>
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
                    <p className="game-stats">
                      Partite: {stats.played} · Vittorie: {stats.wins} · Serie attuale: {stats.streak} · Serie
                      migliore: {stats.maxStreak}
                    </p>
                  )}
                </section>
              )}
            </div>
          </>
      )}
    </div>
  );
}

/**
 * La mappa è markup SVG statico, iniettato lato server dallo stesso partial
 * usato da /regioni (app/templates/_italy_map.html), non un componente React:
 * evita di duplicare ~60KB di path geografici nel bundle del gioco. Questo
 * hook la rende interattiva "dall'esterno" tramite DOM API imperative.
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

  // Listener stabili, allacciati una sola volta: leggono sempre lo stato più
  // recente tramite il ref "latest", così non serve ri-bindare a ogni render.
  useEffect(() => {
    const frame = document.getElementById(MAP_FRAME_ID);
    if (!frame) return undefined;
    const paths = Array.from(frame.querySelectorAll(".rmap-region"));
    function handleActivate(key) {
      const { onGuess: guess, status: currentStatus, submitting: busy } = latest.current;
      if (currentStatus !== "playing" || busy) return;
      guess(key);
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
      path.addEventListener("click", onClick);
      path.addEventListener("keydown", onKeydown);
      return () => {
        path.removeEventListener("click", onClick);
        path.removeEventListener("keydown", onKeydown);
      };
    });
    return () => cleanups.forEach((fn) => fn());
  }, [regionNameByKey]);

  // Classi visive: ricalcolate a ogni cambio di tentativi/esito.
  useEffect(() => {
    const frame = document.getElementById(MAP_FRAME_ID);
    if (!frame) return;
    const paths = frame.querySelectorAll(".rmap-region");
    const finished = status === "won" || status === "lost";
    paths.forEach((path) => {
      const key = path.getAttribute("data-key");
      path.classList.remove("is-clickable", "is-guessed-correct", "is-guessed-wrong", "is-mystery");
      const guess = guesses.find((g) => g.region_key === key);
      if (guess) {
        path.classList.add(guess.correct ? "is-guessed-correct" : "is-guessed-wrong");
      } else if (status === "playing") {
        path.classList.add("is-clickable");
      }
      if (finished && solution && key === solution.region_key) {
        path.classList.add("is-mystery");
      }
    });
  }, [guesses, status, solution]);
}

const root = document.getElementById("game-root");
if (root) {
  createRoot(root).render(<GameApp />);
}
