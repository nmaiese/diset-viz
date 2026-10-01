import React, { useEffect, useMemo, useRef, useState } from "react";
import { BarChart3 } from "lucide-react";
import {
  FinePartita, Modal, fetchJson, formatValue, notifyAchievements, prefersReducedMotion, trackGameEvent, useTerritorioMio,
} from "../shared.jsx";
import { getAccessToken } from "../../shared/supabase.js";
import {
  comparisonArrow, comparisonText, dataInChiaro, normalize, ordinal, titoloEsito, titoloIndizi, titoloTentativi,
} from "./helpers.js";
import { oggiRoma } from "./serie.js";
import { segnaGiocata } from "../oggi.js";
import {
  API_PROVINCIA,
  AVVISO_RIPRESA,
  LIVELLI,
  caricaProgresso,
  caricaStatistiche,
  decisioneErroreTentativo,
  direzione,
  inviaTentativo,
  livelloSalvato,
  messaggioFuoriElenco,
  nomeLivello,
  onboardingFatto,
  registraPartita,
  regioneConArticolo,
  rigaTerritorio,
  rimuoviProgresso,
  riassuntoProvincia,
  salvaLivello,
  salvaProgresso,
  segnaOnboarding,
  testoDistanza,
  testoDistanzaCompatta,
} from "./provincia.js";
import { ERRORE_LIMITE, PARTITA_INTERROTTA, SFIDA_CAMBIATA, messaggioTentativo } from "../testi.js";
import { useMappaProvince } from "./MappaProvince.jsx";
import Completamento from "./Completamento.jsx";
import Dettagli from "./Dettagli.jsx";
import Scheletro from "./Scheletro.jsx";
import { CheCosaMisura, TabellaIndizi } from "./TabellaIndizi.jsx";
import { SegnoTentativo, TentativiCompatti } from "./Tentativi.jsx";
import Riepilogo from "./Riepilogo.jsx";
import { DistributionChart } from "./Statistiche.jsx";

const GAME_NAME = "Indovina la Provincia";
const GAME = "provincia";
const MAX_SUGGERIMENTI = 6;

const MESSAGGI_ERRORE = {
  sfida_scaduta: `${SFIDA_CAMBIATA} Ricarica la pagina per giocare quella di oggi.`,
  token_superato: `${PARTITA_INTERROTTA} Ricarica la pagina per ripartire.`,
  provincia_gia_tentata: "Hai già provato questa provincia.",
  provincia_non_valida: "Questa provincia non è fra quelle del livello scelto.",
  partita_conclusa: "La partita di oggi è già conclusa.",
  rate_limited: ERRORE_LIMITE,
};

// Un tentativo: niente token, che resta nel salvataggio a parte.
function senzaToken(risultato) {
  const { token, ...resto } = risultato;
  return resto;
}

function etichettaSuggerimento(provincia, livello) {
  return livello === "province" ? `${provincia.name} (${provincia.region})` : provincia.name;
}

export default function GiocoProvincia() {
  const [level, setLevel] = useState(livelloSalvato);
  const [puzzle, setPuzzle] = useState(null);
  const [token, setToken] = useState(null);
  const [clues, setClues] = useState([]);
  const [guesses, setGuesses] = useState([]);
  const [status, setStatus] = useState("loading"); // loading | playing | won | lost | error
  const [solution, setSolution] = useState(null);
  const [recap, setRecap] = useState(null);
  const [query, setQuery] = useState("");
  const [highlighted, setHighlighted] = useState(-1);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [ricarica, setRicarica] = useState(false); // l'errore si risolve ricaricando la pagina
  const [daRiprovare, setDaRiprovare] = useState(null); // la provincia del tentativo da rimandare
  const [fatto, setFatto] = useState(null); // il "fatto da portarti via", se il server lo manda
  const [liveMessage, setLiveMessage] = useState("");
  const [shake, setShake] = useState(false);
  const [stats, setStats] = useState(caricaStatistiche);
  const [showOnboarding, setShowOnboarding] = useState(() => !onboardingFatto());
  const [showStats, setShowStats] = useState(false);

  const esitoRef = useRef(null);
  const [scorri, setScorri] = useState(0); // sale a ogni tentativo appena giocato
  const statsRecordedRef = useRef(false);
  const latestRef = useRef({ status: "loading", submitting: false });
  // La ripresa da sola dopo un tentativo perso: il contatore rilancia il caricamento, il testo si
  // mostra alla fine, e `ripresaRef` e' vero finche' la partita ripresa non ha un tentativo buono.
  const [riprese, setRiprese] = useState(0);
  const avvisoRef = useRef("");
  const ripresaRef = useRef(false);

  const finished = status === "won" || status === "lost";
  const locked = guesses.length > 0 || finished;

  useEffect(() => {
    latestRef.current = { status, submitting };
  }, [status, submitting]);

  useEffect(() => {
    setHighlighted(-1);
  }, [query]);

  // La provincia e' la stessa ai due livelli: se oggi hai gia' iniziato, il livello
  // e' quello dell'inizio, e la partita si riprende dal salvataggio.
  useEffect(() => {
    const salvato = caricaProgresso(`daily:${oggiRoma()}`);
    if (salvato && salvato.level !== level) {
      setLevel(salvato.level);
      return undefined;
    }
    let attivo = true;
    setStatus("loading");
    setError(null);
    setRicarica(false);
    setFatto(null);
    setLiveMessage("");
    fetchJson(API_PROVINCIA.daily(level))
      .then((data) => {
        if (!attivo) return;
        setPuzzle(data);
        const progresso = caricaProgresso(data.puzzle_id);
        if (progresso && progresso.level === level) {
          setToken(progresso.token);
          setClues(progresso.clues);
          setGuesses(progresso.guesses);
          setSolution(progresso.solution || null);
          setRecap(progresso.recap || null);
          setFatto(progresso.fatto || null);
          statsRecordedRef.current = Boolean(progresso.statsRecorded);
          setStatus(progresso.status);
          return;
        }
        statsRecordedRef.current = false;
        setToken(data.token);
        setClues(data.clue ? [data.clue] : []);
        setGuesses([]);
        setSolution(null);
        setRecap(null);
        setStatus("playing");
        if (avvisoRef.current) {
          setError(avvisoRef.current);
          avvisoRef.current = "";
        }
        trackGameEvent("game_start", { game: GAME, mode: "daily", level });
      })
      .catch(() => {
        if (!attivo) return;
        setError("Non è stato possibile caricare la sfida. Riprova fra poco.");
        setStatus("error");
      });
    return () => {
      attivo = false;
    };
  }, [level, riprese]);

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

  const opzioni = puzzle?.provinces;

  const suggestions = useMemo(() => {
    const q = normalize(query.trim());
    if (!q || !opzioni) return [];
    const tentate = new Set(guesses.map((g) => g.province_key));
    const trovate = opzioni.filter((p) => !tentate.has(p.key) && normalize(p.name).includes(q));
    // Prima quelle che iniziano come la ricerca.
    trovate.sort((a, b) => Number(!normalize(a.name).startsWith(q)) - Number(!normalize(b.name).startsWith(q)));
    return trovate.slice(0, MAX_SUGGERIMENTI).map((p) => ({ key: p.key, label: etichettaSuggerimento(p, level) }));
  }, [query, opzioni, guesses, level]);

  // Sotto il campo, quando il testo non porta a nessun suggerimento: perche' (una provincia di un'altra
  // regione, una gia' provata, nessuna). Vuoto finche' non si scrive, o se ci sono suggerimenti.
  const nota = useMemo(() => {
    if (!opzioni || suggestions.length > 0) return "";
    return messaggioFuoriElenco(query, {
      regione: level === "stessa_regione" ? puzzle?.region : null,
      opzioni,
      altre: puzzle?.other_provinces || [],
      tentate: guesses.map((g) => g.province_key),
    }) || "";
  }, [query, opzioni, suggestions, level, puzzle, guesses]);

  useMappaProvince({ options: opzioni, region: puzzle?.region, guesses, status, solution });

  function scegliLivello(nuovo) {
    if (locked || nuovo === level) return;
    salvaLivello(nuovo);
    setLevel(nuovo);
  }

  function registraFine(won, attempts) {
    if (statsRecordedRef.current) return;
    statsRecordedRef.current = true;
    setStats((prev) => registraPartita(prev, { won, attempts }));
  }

  function salva(next) {
    if (!puzzle) return;
    salvaProgresso(puzzle.puzzle_id, {
      level,
      token: next.token,
      clues: next.clues,
      guesses: next.guesses,
      status: next.status,
      solution: next.solution,
      recap: next.recap,
      fatto: next.fatto || null,
      statsRecorded: statsRecordedRef.current,
    });
  }

  function submitGuess(provinceKey) {
    if (!puzzle || latestRef.current.submitting || latestRef.current.status !== "playing") return;
    const attempt = guesses.length + 1;
    setSubmitting(true);
    setError(null);
    setRicarica(false);
    setDaRiprovare(null);
    // Col Bearer di chi ha fatto l'accesso, cosi' il server registra il punteggio e i traguardi; a fine
    // partita i traguardi sbloccati vanno al toast.
    inviaTentativo(token, provinceKey, { getToken: getAccessToken, notify: notifyAchievements })
      .then((result) => {
        const tentativo = senzaToken(result);
        const nextGuesses = [...guesses, tentativo];
        const nextClues = result.next_clue ? [...clues, result.next_clue] : clues;
        const nextStatus = result.finished ? (result.correct ? "won" : "lost") : "playing";
        ripresaRef.current = false;
        setGuesses(nextGuesses);
        setClues(nextClues);
        setToken(result.token);
        setStatus(nextStatus);
        setQuery("");
        setHighlighted(-1);
        trackGameEvent("game_guess", { game: GAME, mode: "daily", level, attempt, correct: result.correct });

        if (result.correct) {
          setLiveMessage(`Giusto. La provincia era ${result.province}.`);
        } else if (result.finished) {
          setLiveMessage(`Tentativi esauriti. La provincia era ${result.solution?.province || ""}.`);
        } else {
          setLiveMessage(
            `Tentativo ${attempt}: ${result.province} non è la provincia. ${testoDistanza(result)}. `
            + `${result.same_region ? "Stessa regione." : "Un'altra regione."} Nuovo indizio rivelato.`
          );
          setShake(true);
          window.setTimeout(() => setShake(false), 420);
        }

        // Il fatto viene dal server (`fatto`, o `fact`): senza il campo, niente riga.
        const nextFatto = result.finished ? (result.fatto || result.fact || null) : null;
        if (result.finished) {
          setSolution(result.solution);
          setRecap(result.recap);
          setFatto(nextFatto);
          registraFine(result.correct, attempt);
          segnaGiocata("provincia", puzzle.date, {
            ok: result.correct,
            testo: result.correct ? `Risolta in ${attempt} su ${puzzle.attempts_total}` : "Non risolta",
            tentativi: attempt,
          });
          trackGameEvent("game_finish", { game: GAME, mode: "daily", level, won: result.correct, attempts: attempt });
        }
        salva({
          token: result.token, clues: nextClues, guesses: nextGuesses, status: nextStatus,
          solution: result.solution, recap: result.recap, fatto: nextFatto,
        });
        setScorri((n) => n + 1);
      })
      .catch((e) => {
        const decisione = decisioneErroreTentativo({ status: e.status, code: e.code }, { giaRipresa: ripresaRef.current });
        if (decisione === "riprendi") {
          // Il token salvato e' superato: si dimentica il progresso e si ricarica la sfida.
          rimuoviProgresso(puzzle.puzzle_id);
          avvisoRef.current = AVVISO_RIPRESA;
          ripresaRef.current = true;
          setRiprese((n) => n + 1);
          return;
        }
        setError(MESSAGGI_ERRORE[e.code] || messaggioTentativo(e.status));
        setRicarica(decisione === "ricarica");
        // Rete, 5xx (503 compreso), limite e generico: il tentativo non e' stato contato, si rimanda.
        setDaRiprovare(!MESSAGGI_ERRORE[e.code] || e.code === "rate_limited" ? provinceKey : null);
      })
      .finally(() => setSubmitting(false));
  }

  const highlightBucket = finished ? (status === "won" ? String(guesses.length) : "fail") : null;

  return (
    <div className="game-app guess-app">
      <div className="game-toolbar" role="group" aria-label="Livello di gioco">
        {LIVELLI.map((l) => (
          <button
            key={l.key}
            type="button"
            aria-pressed={level === l.key}
            aria-disabled={locked && level !== l.key}
            disabled={locked && level !== l.key}
            className={level === l.key ? "game-tab is-active" : "game-tab"}
            onClick={() => scegliLivello(l.key)}
          >
            {l.label}
          </button>
        ))}
        <span className="game-toolbar-spacer" />
        <button
          type="button"
          className="game-icon-btn"
          onClick={() => { setShowStats(true); trackGameEvent("game_stats_open", { game: GAME, mode: "daily", level }); }}
          aria-label="Statistiche"
        >
          <BarChart3 size={16} strokeWidth={2} />
        </button>
        <button type="button" className="game-icon-btn" onClick={() => setShowOnboarding(true)} aria-label="Come si gioca">
          ?
        </button>
      </div>
      {locked && (
        <p className="game-livello-nota">
          La provincia di oggi è la stessa a tutti e due i livelli: hai già iniziato, quindi il livello resta quello
          {" "}{nomeLivello(level)}.
        </p>
      )}

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
              Sfida n. {puzzle.number}
              {puzzle.date && <span className="game-date"> · {dataInChiaro(puzzle.date)}</span>}
            </h2>
            {puzzle.region && (
              <p className="game-regione-nota">
                La provincia misteriosa è <strong>{regioneConArticolo(puzzle.region.name).in}</strong>.
              </p>
            )}
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

          {/* La mappa (#game-map-frame) e' il fratello server-renderizzato di
              #game-root, come in Indovina la Regione: useMappaProvince la
              rende viva dall'esterno. */}
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
                ariaLabel="Indovina la provincia"
                placeholder="Scrivi il nome di una provincia..."
                query={query}
                onQuery={setQuery}
                suggestions={suggestions}
                highlighted={highlighted}
                onHighlight={setHighlighted}
                onPick={submitGuess}
                disabled={submitting}
                shake={shake}
                error={error}
                ricarica={ricarica}
                onRiprova={daRiprovare ? () => submitGuess(daRiprovare) : undefined}
                nota={nota}
              />
            )}

            {!(finished && solution) && guesses.length > 0 && <TentativiProvincia guesses={guesses} esitoRef={esitoRef} />}

            {!(finished && solution) && <CheCosaMisura clues={clues} game={GAME} />}

            {finished && solution && (
              <FineProvincia
                won={status === "won"}
                puzzle={puzzle}
                level={level}
                solution={solution}
                recap={recap}
                guesses={guesses}
                stats={stats}
                highlightBucket={highlightBucket}
                fatto={fatto}
                esitoRef={esitoRef}
              />
            )}
          </div>
        </>
      )}

      {showOnboarding && (
        <Modal
          title="Come si gioca"
          labelledBy="game-onboarding-title"
          onClose={() => { setShowOnboarding(false); segnaOnboarding(); }}
        >
          <ol className="game-onboarding-steps">
            <li>Una provincia italiana è nascosta, e cambia ogni giorno a mezzanotte di Roma. Hai sei tentativi.</li>
            <li>Scrivi il nome di una provincia e scegline una dall'elenco. La mappa segna il tentativo con un numero.</li>
            <li>
              Ogni errore ti dice a che distanza sei, in chilometri (una stima) e in quale direzione cercare.
              Svela anche un indizio nuovo, un dato Istat.
            </li>
          </ol>
          <button type="button" className="game-btn" onClick={() => { setShowOnboarding(false); segnaOnboarding(); }}>
            Ho capito, gioco
          </button>
        </Modal>
      )}

      {showStats && (
        <Modal title="Le tue statistiche" onClose={() => setShowStats(false)} labelledBy="game-stats-title">
          <div className="game-stats-numbers game-stats-numbers--due">
            <div><strong>{stats.played}</strong><span>Partite</span></div>
            <div><strong>{stats.played ? Math.round((stats.wins / stats.played) * 100) : 0}%</strong><span>Vittorie</span></div>
          </div>
          <DistributionChart distribution={stats.distribution} highlightBucket={null} />
          <p className="game-stats-note">
            Le statistiche restano su questo browser. La serie e la classifica di Indovina la Provincia arrivano più avanti.
          </p>
        </Modal>
      )}
    </div>
  );
}

// Lo storico dei tentativi durante la partita, dal piu' recente: l'esito dell'ultimo sta subito sotto il
// campo di risposta (`esitoRef` e' la sua riga, dove scorre la pagina) e il confronto indizio per indizio
// e' aperto solo li'. Per ognuno la distanza e la direzione, se e' nella stessa regione. L'esito si legge
// dal testo e dall'icona, non dal solo colore.
function TentativiProvincia({ guesses, esitoRef }) {
  const righe = guesses.map((g, i) => ({ g, i })).reverse();
  return (
    <section className="game-history" aria-label="Tentativi">
      {righe.map(({ g, i }, posizione) => {
        const punto = direzione(g.direction);
        return (
          <div
            key={g.province_key}
            ref={posizione === 0 ? esitoRef : undefined}
            className={g.correct ? "guess-row is-correct" : "guess-row is-wrong"}
          >
            <p className="guess-titolo">
              <SegnoTentativo correct={g.correct}>
                <strong>{i + 1}. {g.province}</strong>
              </SegnoTentativo>
            </p>
            {!g.correct && (
              <p className="guess-distanza">
                {punto && <span className="guess-freccia" aria-hidden="true">{punto.freccia}</span>}
                <span>{testoDistanza(g)}.</span>{" "}
                <span>{g.same_region ? "Stessa regione." : "Un'altra regione."}</span>
              </p>
            )}
            {!g.correct && (
              <details className="guess-confronto" open={posizione === 0}>
                <summary>Confronto degli indizi</summary>
                <ul className="guess-feedback">
                  {g.feedback.map((f) => (
                    <li key={f.id}>
                      <span className="guess-symbol" aria-hidden="true">{comparisonArrow(f.comparison)}</span>
                      <span className="guess-feedback-body">
                        <strong>{f.name}</strong>
                        <span className="guess-feedback-detail">
                          {formatValue(f.guess_value, f.unit)}
                          {Number.isFinite(f.guess_rank) && ` · ${ordinal(f.guess_rank)} su ${f.province_count}`}
                          {" "}({comparisonText(f.comparison)}
                          {Number.isFinite(f.mystery_rank) && `, misteriosa ${ordinal(f.mystery_rank)}`})
                        </span>
                      </span>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        );
      })}
    </section>
  );
}

// La fine di una partita a livelli: prima l'esito (il tono, la provincia e la regione coi loro link, in
// quanti tentativi, il conto alla rovescia, "Condividi"), poi, in riquadri chiusi, gli indizi con le
// definizioni intere, i tentativi e le statistiche. `fatto` viene dal server, se c'e'.
function FineProvincia({ won, puzzle, level, solution, recap, guesses, stats, highlightBucket, fatto, esitoRef }) {
  const mio = useTerritorioMio();
  const tuo = rigaTerritorio(mio, solution, puzzle.provinces);
  const condividi = {
    gameName: GAME_NAME,
    game: GAME,
    puzzleNumber: puzzle.number,
    esiti: guesses.map((g) => (g.correct ? "exact" : "miss")),
    summary: riassuntoProvincia({ won, tentativi: guesses.length, totale: puzzle.attempts_total, level }),
    url: `${window.location.origin}/quiz/indovina-la-provincia`,
    eventParams: { mode: "daily", level, game: GAME },
  };
  return (
    <div className="game-result" ref={esitoRef}>
      <FinePartita
        won={won}
        tono={won ? "pieno" : "nullo"}
        game={GAME}
        titolo={titoloEsito("provincia", won, guesses.length)}
        dettaglio={`La provincia era ${solution.province}, ${regioneConArticolo(solution.region).in}.${tuo ? ` ${tuo}` : ""}`}
        fatto={fatto || undefined}
        territori={[
          { name: `Scheda di ${solution.province}`, path: solution.path },
          { name: `Scheda ${regioneConArticolo(solution.region).di}`, path: solution.region_path },
        ]}
        nextPuzzleAt={puzzle.next_puzzle_at}
        condividi={condividi}
      />

      {recap && (
        <Dettagli titolo={titoloIndizi(recap.length)}>
          <Riepilogo
            titolo={null}
            soggetto={solution.province}
            mediaLabel="Media delle province"
            rows={recap.map((row) => ({ ...row, media: row.province_avg }))}
          />
        </Dettagli>
      )}

      <Dettagli titolo={titoloTentativi(guesses.length)}>
        <TentativiCompatti guesses={guesses} nome={(g) => g.province} distanza={testoDistanzaCompatta} />
      </Dettagli>

      <Dettagli titolo="Le tue statistiche">
        <div className="game-stats-numbers game-stats-numbers--due">
          <div><strong>{stats.played}</strong><span>Partite</span></div>
          <div><strong>{stats.played ? Math.round((stats.wins / stats.played) * 100) : 0}%</strong><span>Vittorie</span></div>
        </div>
        <DistributionChart distribution={stats.distribution} highlightBucket={highlightBucket} />
      </Dettagli>
    </div>
  );
}
