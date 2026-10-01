import React, { useEffect, useMemo, useRef, useState } from "react";
import { BarChart3 } from "lucide-react";
import { fetchJson, prefersReducedMotion, trackGameEvent, notifyAchievements } from "../shared.jsx";
import { getAccessToken } from "../../shared/supabase.js";
import { API, STORAGE_ONBOARDED_KEY } from "./api.js";
import { dataInChiaro, normalize } from "./helpers.js";
import { inviaJson } from "./rete.js";
import { aggiornaSerie, oggiRoma, serieAttuale } from "./serie.js";
import { segnaGiocata } from "../oggi.js";
import { leggiSerieServer } from "./giocatore.js";
import { loadProgress, loadStats, saveProgress, saveStats } from "./storage.js";
import { useMapInteractions } from "./Mappa.jsx";
import { ERRORE_LIMITE, SFIDA_CAMBIATA, messaggioTentativo } from "../testi.js";
import Completamento from "./Completamento.jsx";
import Scheletro from "./Scheletro.jsx";
import { CheCosaMisura, TabellaIndizi } from "./TabellaIndizi.jsx";
import Tentativi from "./Tentativi.jsx";
import ResultPanel from "./Risultato.jsx";
import OnboardingModal from "./Onboarding.jsx";
import ArchiveModal from "./Archivio.jsx";
import { StatsModal } from "./Statistiche.jsx";

const GAME = "regione";

export default function GameApp() {
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
  const [daRiprovare, setDaRiprovare] = useState(null); // la regione del tentativo da rimandare
  const [ricarica, setRicarica] = useState(false); // l'errore si risolve ricaricando la pagina
  const [fatto, setFatto] = useState(null); // il "fatto da portarti via", se il server lo manda
  const [shake, setShake] = useState(false);
  const [liveMessage, setLiveMessage] = useState("");
  const [stats, setStats] = useState(loadStats);
  const [serverSerie, setServerSerie] = useState(null);
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
  const esitoRef = useRef(null);
  const [scorri, setScorri] = useState(0); // sale a ogni tentativo appena giocato

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

  // Dopo ogni tentativo la pagina porta in vista l'esito: la riga del tentativo sotto il campo o, a fine
  // partita, la schermata finale. `nearest` muove la pagina il minimo, e liscio solo se non si e' chiesto
  // di ridurre il movimento. Non parte al caricamento: `scorri` sale solo quando si gioca.
  useEffect(() => {
    if (scorri === 0) return;
    const esito = esitoRef.current;
    if (esito && esito.scrollIntoView) {
      esito.scrollIntoView({ block: "nearest", behavior: prefersReducedMotion() ? "auto" : "smooth" });
    }
  }, [scorri]);

  // Da loggato la serie a giorni la ricalcola il server dalle giornaliere.
  useEffect(() => {
    leggiSerieServer().then((serie) => serie && setServerSerie(serie));
  }, []);

  useEffect(() => {
    if (showArchive && archiveList === null) {
      fetchJson(API.archive)
        .then((d) => setArchiveList(d.puzzles || []))
        .catch(() => setArchiveList([]));
    }
  }, [showArchive, archiveList]);

  function mostraErrore(testo, conRicarica = false) {
    setError(testo);
    setRicarica(conRicarica);
  }

  function startGame(kind, opts = {}) {
    setError(null);
    setRicarica(false);
    setStatus("loading");
    setSolution(null);
    setRecap(null);
    setFatto(null);
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
            setFatto(saved.fatto || null);
            statsRecordedRef.current = Boolean(saved.statsRecorded);
            setStatus(saved.status);
            return;
          }
        }
        setClues(data.clue ? [data.clue] : []);
        setGuesses([]);
        setStatus("playing");
        trackGameEvent("game_start", { game: GAME, mode: kind, level: "regioni" });
      })
      .catch(() => {
        setError(
          kind === "archive"
            ? "Questa sfida non è disponibile."
            : "Non è stato possibile caricare la sfida. Riprova fra poco."
        );
        setStatus("error");
      });
  }

  function persistProgress(nextClues, nextGuesses, nextStatus, nextSolution, nextRecap, nextFatto) {
    if (mode === "practice" || !puzzle) return;
    saveProgress(puzzle.puzzle_id, {
      clues: nextClues,
      guesses: nextGuesses,
      status: nextStatus,
      solution: nextSolution,
      recap: nextRecap,
      fatto: nextFatto || null,
      statsRecorded: statsRecordedRef.current,
    });
  }

  function recordStats(won, attemptCount) {
    if (mode !== "daily" || statsRecordedRef.current) return;
    statsRecordedRef.current = true;
    setStats((prev) => {
      const next = {
        ...aggiornaSerie(prev, { won, giorno: puzzle.date }),
        played: prev.played + 1,
        wins: prev.wins + (won ? 1 : 0),
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
    setDaRiprovare(null);
    // `mode` dice al server che cosa stiamo giocando: a una "daily" rimasta aperta oltre la mezzanotte
    // risponde 410 `puzzle_changed` invece di valutare la sfida di ieri.
    inviaJson(API.guess, { puzzle_id: puzzle.puzzle_id, region_key: regionKey, attempt, mode }, { getToken: getAccessToken })
      .then((result) => {
        notifyAchievements(result.achievements, GAME);
        const nextGuesses = [...guesses, result];
        const nextClues = result.next_clue ? [...clues, result.next_clue] : clues;
        const nextStatus = result.finished ? (result.correct ? "won" : "lost") : "playing";
        setGuesses(nextGuesses);
        setClues(nextClues);
        setStatus(nextStatus);
        setQuery("");
        setHighlighted(-1);
        trackGameEvent("game_guess", { game: GAME, mode, level: "regioni", attempt, correct: result.correct });

        const guessedName = regionByKey[regionKey] || result.region;
        if (result.correct) {
          setLiveMessage(`Giusto. La regione era ${guessedName}.`);
        } else if (result.finished) {
          setLiveMessage(`Tentativi esauriti. La regione era ${result.solution?.region || ""}.`);
        } else {
          setLiveMessage(`Tentativo ${attempt}: ${guessedName} non è la regione misteriosa. Nuovo indizio rivelato.`);
          setShake(true);
          window.setTimeout(() => setShake(false), 420);
        }

        // Il fatto viene dal server (`fatto`, o `fact`): senza il campo, niente riga.
        const nextFatto = result.finished ? (result.fatto || result.fact || null) : null;
        if (result.finished) {
          setSolution(result.solution);
          setRecap(result.recap);
          setFatto(nextFatto);
          recordStats(result.correct, attempt);
          if (mode === "daily") segnaGiocata("indovina", puzzle.date, { ok: result.correct, testo: result.correct ? `Risolta in ${attempt} su ${puzzle.attempts_total}` : "Non risolta" });
          if (mode === "daily") leggiSerieServer().then((serie) => serie && setServerSerie(serie));
          trackGameEvent("game_finish", { game: GAME, mode, level: "regioni", won: result.correct, attempts: attempt });
        }
        persistProgress(nextClues, nextGuesses, nextStatus, result.solution, result.recap, nextFatto);
        setScorri((n) => n + 1);
      })
      .catch((e) => {
        if (e && e.code === "puzzle_changed") mostraErrore(`${SFIDA_CAMBIATA} Ricarica la pagina per giocare quella di oggi.`, true);
        else {
          mostraErrore(e && e.code === "rate_limited" ? ERRORE_LIMITE : messaggioTentativo(e && e.status));
          setDaRiprovare(regionKey);
        }
      })
      .finally(() => setSubmitting(false));
  }

  useMapInteractions({ regions, guesses, status, solution, onGuess: submitGuess, submitting });

  const attemptsLeft = puzzle ? puzzle.attempts_total - guesses.length : 0;
  const finished = status === "won" || status === "lost";

  function openStats() {
    setShowStats(true);
    trackGameEvent("game_stats_open", { game: GAME, mode, level: "regioni" });
  }

  function openArchive() {
    setShowArchive(true);
    trackGameEvent("game_archive_open", { game: GAME, level: "regioni" });
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

  const serie = serverSerie || { current: serieAttuale(stats, oggiRoma()), max: stats.maxStreak };
  const highlightBucket = mode === "daily" && finished ? (status === "won" ? String(guesses.length) : "fail") : null;

  return (
    <div className="game-app guess-app">
      <div className="game-toolbar" role="group" aria-label="Modalità di gioco">
        <button
          type="button"
          aria-pressed={mode === "daily"}
          className={mode === "daily" ? "game-tab is-active" : "game-tab"}
          onClick={backToToday}
        >
          Sfida del giorno
        </button>
        <button
          type="button"
          aria-pressed={mode === "practice"}
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

      {status === "loading" && <Scheletro />}
      {status === "error" && (
        <>
          <p className="game-error">{error}</p>
          <button type="button" className="game-btn" onClick={() => window.location.reload()}>Riprova</button>
        </>
      )}

      {(status === "playing" || finished) && puzzle && (
        <>
          <header className="game-head">
            <h2>
              {mode === "daily" && `Sfida n. ${puzzle.number}`}
              {mode === "practice" && "Allenamento"}
              {mode === "archive" && `Sfida del ${dataInChiaro(puzzle.date)}`}
              {mode === "daily" && puzzle.date && <span className="game-date"> · {dataInChiaro(puzzle.date)}</span>}
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
            {/* A partita finita la tabella sparisce: gli indizi tutti e sei stanno nel riquadro chiuso della
                schermata finale, con le loro definizioni. */}
            {!(finished && solution) && (
              <>
                <p className="qz-section-label">Indizi svelati</p>
                <TabellaIndizi clues={clues} total={puzzle.attempts_total} playing={status === "playing"} />
              </>
            )}

            {status === "playing" && (
              <Completamento
                label="La tua ipotesi"
                ariaLabel="Indovina la regione"
                placeholder="Scrivi il nome di una regione..."
                query={query}
                onQuery={setQuery}
                suggestions={suggestions.map((r) => ({ key: r.region_key, label: r.region }))}
                highlighted={highlighted}
                onHighlight={setHighlighted}
                onPick={submitGuess}
                disabled={submitting}
                shake={shake}
                error={error}
                ricarica={ricarica}
                onRiprova={daRiprovare ? () => submitGuess(daRiprovare) : undefined}
              />
            )}

            {!(finished && solution) && guesses.length > 0 && (
              <Tentativi guesses={guesses} regionByKey={regionByKey} esitoRef={esitoRef} />
            )}

            {!(finished && solution) && <CheCosaMisura clues={clues} game={GAME} />}

            {finished && solution && (
              <ResultPanel
                status={status}
                mode={mode}
                puzzle={puzzle}
                solution={solution}
                recap={recap}
                stats={stats}
                highlightBucket={highlightBucket}
                serie={serie}
                guesses={guesses}
                regionByKey={regionByKey}
                fatto={fatto}
                esitoRef={esitoRef}
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

      {showStats && <StatsModal stats={stats} serie={serie} onClose={() => setShowStats(false)} />}

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
