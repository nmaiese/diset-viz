import React, { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { AuthControl, fetchJson, formatCountdown, trackGameEvent, notifyAchievements } from "./shared.jsx";
import { GIOCHI, serieLocale, statoOggi } from "./oggi.js";
import { getAccessToken, getUser, isAuthConfigured, mergeLocalStatsOnce, onAuthChange } from "../shared/supabase.js";

// Un'icona SVG che prende il colore del testo: il file e' una maschera, cosi'
// segue il tema chiaro e scuro (un <img> non legge le variabili del sito).
function Icona({ nome, cartella = "gioco" }) {
  return <span className="ico" style={{ "--ico": `url(/static/img/${cartella}/${nome}.svg)` }} aria-hidden="true" />;
}

// Caricamento, vuoto ed errore sono tre cose diverse: un errore di rete non
// deve passare per "nessun dato". `carica` ritorna una promise del dato.
function useCaricamento(carica, dipendenze) {
  const [stato, setStato] = useState({ fase: "caricamento", dati: null });
  const [tentativo, setTentativo] = useState(0);
  useEffect(() => {
    let attivo = true;
    setStato({ fase: "caricamento", dati: null });
    carica()
      .then((dati) => attivo && setStato({ fase: "pronto", dati }))
      .catch(() => attivo && setStato({ fase: "errore", dati: null }));
    return () => {
      attivo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...dipendenze, tentativo]);
  const riprova = useCallback(() => setTentativo((n) => n + 1), []);
  return [stato, riprova];
}

function Errore({ testo, onRiprova }) {
  return (
    <p className="hub-errore" role="alert">
      {testo}{" "}
      <button type="button" className="game-btn game-btn--ghost" onClick={onRiprova}>Riprova</button>
    </p>
  );
}

// Statistiche e traguardi dell'account (quando loggato). Alla prima connessione
// fonde i progressi locali nell'account (una volta), poi carica la vetrina.
// `fase` dice se sta caricando, e' pronta o e' fallita; `dati` e' null anche
// per chi non ha il login (fase "anonimo").
function useAccount() {
  const [utente, setUtente] = useState(undefined);
  useEffect(() => {
    if (!isAuthConfigured()) {
      setUtente(null);
      return undefined;
    }
    let attivo = true;
    let unsub = () => {};
    getUser().then((u) => attivo && setUtente(u || null)).catch(() => attivo && setUtente(null));
    onAuthChange((u) => attivo && setUtente(u || null)).then((fn) => (attivo ? (unsub = fn) : fn()));
    return () => {
      attivo = false;
      unsub();
    };
  }, []);

  const [stato, riprova] = useCaricamento(async () => {
    if (!utente) return null;
    const sbloccati = await mergeLocalStatsOnce(utente.id);
    if (sbloccati && sbloccati.length) notifyAchievements(sbloccati);
    const token = await getAccessToken();
    if (!token) throw new Error("senza sessione");
    const r = await fetch("/api/player/me", { headers: { Authorization: `Bearer ${token}` } });
    if (!r.ok) throw new Error(`player/me ${r.status}`);
    return r.json();
  }, [utente]);

  if (utente === undefined) return { fase: "caricamento", dati: null, riprova };
  if (utente === null) return { fase: "anonimo", dati: null, riprova };
  return { ...stato, riprova };
}

function AchievementsPanel({ account }) {
  if (account.fase === "anonimo") return null;
  if (account.fase === "caricamento") {
    return (
      <div className="qz-stats" aria-busy="true">
        <p className="qz-section-eb" style={{ margin: 0 }}>Traguardi</p>
        <div className="skel-bars" style={{ marginTop: 14 }} aria-hidden="true"><span style={{ height: 14, width: "60%" }} /></div>
      </div>
    );
  }
  if (account.fase === "errore") {
    return (
      <div className="qz-stats">
        <p className="qz-section-eb" style={{ margin: 0 }}>Traguardi</p>
        <Errore testo="Non riesco a caricare i tuoi traguardi." onRiprova={account.riprova} />
      </div>
    );
  }
  const lista = account.dati && Array.isArray(account.dati.achievements) ? account.dati.achievements : [];
  if (lista.length === 0) return null;
  const sbloccati = lista.filter((a) => a.unlocked).length;
  return (
    <div className="qz-stats">
      <p className="qz-section-eb" style={{ margin: 0 }}>Traguardi · {sbloccati}/{lista.length}</p>
      <div className="achv-grid">
        {lista.map((a) => (
          <div key={a.id} className={a.unlocked ? "achv-card" : "achv-card is-locked"}>
            {a.icon_url
              ? <span className="ico achv-card-ic" style={{ "--ico": `url(${a.icon_url})` }} aria-hidden="true" />
              : <span className="achv-card-ic" aria-hidden="true">{a.icon}</span>}
            <div>
              <div className="achv-card-t">{a.title}</div>
              <div className="achv-card-d">{a.description}</div>
              <div className="achv-card-s">{a.unlocked ? "Sbloccato" : "Da sbloccare"}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

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

// -- La sfida di oggi ---------------------------------------------------------
// Il markup e' del server (game_hub.html): qui si riempiono gli elementi
// `data-oggi-*` con portali, cosi' la pagina indicizzabile non dipende dal JS.

// Gli elementi del server da riempire, svuotati una volta sola: un portale
// aggiunge i suoi figli a quelli che trova, e il testo del server vale solo
// finche' il JS non e' partito.
function useBersagli() {
  const [bersagli, setBersagli] = useState(null);
  useEffect(() => {
    const uno = (selettore) => {
      const el = document.querySelector(selettore);
      if (el) el.replaceChildren();
      return el;
    };
    setBersagli({
      numero: uno("[data-oggi-numero]"),
      conto: uno("[data-oggi-countdown]"),
      serie: uno("[data-oggi-serie]"),
      giochi: Object.fromEntries(GIOCHI.map((g) => [g, uno(`[data-gioco="${g}"] [data-oggi-stato]`)])),
    });
  }, []);
  return bersagli;
}

function useSecondiAlCambio(prossimaIso) {
  const [secondi, setSecondi] = useState(null);
  useEffect(() => {
    const fine = Date.parse(prossimaIso || "");
    if (!Number.isFinite(fine)) return undefined;
    const tick = () => setSecondi(Math.max(0, Math.round((fine - Date.now()) / 1000)));
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [prossimaIso]);
  return secondi;
}

function StatoGioco({ esito }) {
  if (!esito) return <>Gioca <span aria-hidden="true">→</span></>;
  return (
    <>
      <Icona nome={esito.ok ? "stato-giusto" : "stato-sbagliato"} />
      <span>
        <strong>Giocata oggi</strong>
        {esito.testo && <> · {esito.testo}</>}
      </span>
    </>
  );
}

function SfidaDiOggi({ account }) {
  const [daily, riprovaDaily] = useCaricamento(() => fetchJson("/api/game/daily"), []);
  const secondi = useSecondiAlCambio(daily.dati && daily.dati.next_puzzle_at);
  const [esiti, setEsiti] = useState(null);
  const [serie, setSerie] = useState(0);
  useEffect(() => {
    setEsiti(Object.fromEntries(GIOCHI.map((g) => [g, statoOggi(g)])));
    setSerie(serieLocale());
  }, []);

  // Chi ha il login ha la serie dal profilo (ricalcolata dal server), gli altri
  // quella di questo dispositivo.
  const serieProfilo = account.dati && account.dati.stats && account.dati.stats.daily
    ? account.dati.stats.daily.current_daily_streak : null;
  const giorni = serieProfilo !== null && serieProfilo !== undefined ? serieProfilo : serie;

  const b = useBersagli();
  if (!b) return null;
  return (
    <>
      {b.numero && daily.dati && daily.dati.number ? createPortal(`n. ${daily.dati.number}`, b.numero) : null}
      {b.conto && createPortal(
        daily.fase === "errore"
          ? <>Non riesco a leggere l'orario della prossima sfida. <button type="button" className="hub-link" onClick={riprovaDaily}>Riprova</button></>
          : secondi === null
            ? "Una nuova sfida ogni giorno, a mezzanotte"
            : secondi > 0
              ? <>Prossima sfida tra <span role="timer" className="hub-oggi__conto">{formatCountdown(secondi)}</span></>
              : "La nuova sfida è pronta: ricarica la pagina.",
        b.conto,
      )}
      {b.serie && giorni > 0 && createPortal(
        <>{giorni === 1 ? "1 giorno di fila" : `${giorni} giorni di fila`} con almeno una sfida</>,
        b.serie,
      )}
      {esiti && GIOCHI.map((gioco) => {
        const el = b.giochi[gioco];
        if (!el) return null;
        el.closest("[data-gioco]").classList.toggle("is-giocata", Boolean(esiti[gioco]));
        return createPortal(<StatoGioco esito={esiti[gioco]} />, el, gioco);
      })}
    </>
  );
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
  const [top, riprova] = useCaricamento(
    () => fetchJson("/api/game/leaderboard?mode=compare&period=week&limit=4").then((d) => d.entries || []),
    [],
  );
  const entries = top.dati;
  const max = entries && entries.length > 0 ? entries[0].score : 1;
  return (
    <div className="qz-lb">
      <div className="qz-lb-head">
        <p className="qz-section-eb" style={{ margin: 0 }}>Classifica · settimana</p>
        <a href="/quiz/classifica">Vedi tutta →</a>
      </div>
      {top.fase === "caricamento" && (
        <div className="skel-bars" aria-hidden="true">
          <span style={{ height: 14, width: "70%" }} />
          <span style={{ height: 14, width: "60%" }} />
        </div>
      )}
      {top.fase === "errore" && <Errore testo="Non riesco a caricare la classifica." onRiprova={riprova} />}
      {top.fase === "pronto" && entries.length === 0 && (
        <p className="hub-stats-empty">Ancora nessun punteggio questa settimana: gioca a "Chi è maggiore?" e sii il primo.</p>
      )}
      {top.fase === "pronto" && entries.length > 0 && (
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
  const account = useAccount();

  return (
    <>
      <SfidaDiOggi account={account} />
      <AuthControl />
      <section className="qz-two">
        <StatsPanel stats={stats} />
        <LeaderboardPanel />
      </section>
      <AchievementsPanel account={account} />
    </>
  );
}
