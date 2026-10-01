// La geometria pura della mappa muta. Niente React, niente DOM, niente rete: `node --test`
// la importa cosi' com'e' (`geometria.test.mjs`).
//
// Le coordinate sono quelle del viewBox dell'Italia (560x660). Nessuna conversione dal
// punto toccato: la sagoma colpita e' il bersaglio del `click`, e non serve sapere in che
// punto dello schermo (`getScreenCTM` su iOS Safari non e' verificato). Qui stanno solo i
// calcoli sui riquadri e sui centri che la tastiera e la rivelazione usano.

export const VIEWBOX_ITALIA = [0, 0, 560, 660];

// Un riquadro non puo' stringersi sotto questa misura (come `min_side` di `maps.zoom`).
export const LATO_MINIMO = 90;

// "x y larghezza altezza" -> [x, y, w, h], o null se non sono quattro numeri veri con
// larghezza e altezza positive.
export function leggiViewBox(testo) {
  if (typeof testo !== "string") return null;
  const parti = testo.trim().split(/[\s,]+/).map(Number);
  if (parti.length !== 4 || !parti.every(Number.isFinite)) return null;
  if (!(parti[2] > 0) || !(parti[3] > 0)) return null;
  return parti;
}

export function testoViewBox(riquadro) {
  return riquadro.map((n) => String(Math.round(n * 10) / 10)).join(" ");
}

// Il centro di un riquadro `{x, y, width, height}` (un `getBBox()`).
export function centro(r) {
  return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
}

export function puntoInVista(punto, vista) {
  return punto.x >= vista[0] && punto.x <= vista[0] + vista[2]
    && punto.y >= vista[1] && punto.y <= vista[1] + vista[3];
}

// Unita' del viewBox per pixel di schermo con `preserveAspectRatio="xMidYMid meet"`: la scala
// e' la piu' piccola fra le due, quindi un pixel vale `1 / min(larghezza/w, altezza/h)` unita'.
// Serve a tenere i tratti e i segni della stessa misura sullo schermo a ogni riquadro.
export function unitaPerPixel(larghezzaPx, altezzaPx, vista) {
  if (!(larghezzaPx > 0) || !(altezzaPx > 0)) return 1;
  return 1 / Math.min(larghezzaPx / vista[2], altezzaPx / vista[3]);
}

const VERSI = { su: [0, -1], giu: [0, 1], sinistra: [-1, 0], destra: [1, 0] };

// La freccia premuta -> il versore, o null.
export function versoDelTasto(tasto) {
  return { ArrowUp: "su", ArrowDown: "giu", ArrowLeft: "sinistra", ArrowRight: "destra" }[tasto] || null;
}

// La piu' vicina in quella direzione. `corrente` e ogni candidato sono `{id, x, y}`, i centri
// presi dal DOM con `getBBox()`. Prima si cerca fra quelli dentro un cono di 90 gradi in quella
// direzione, il piu' vicino lungo la direzione con una penale sullo scarto laterale. Se il cono
// e' vuoto si ripiega su qualunque candidato che stia di la' (davanti alla retta perpendicolare),
// cosi' la freccia non resta muta quando sul bordo c'e' ancora qualcosa da raggiungere. Senza
// niente di la' si resta fermi: `null`. A parita' vince l'id piu' piccolo (risposta stabile).
export function vicinaInDirezione(corrente, candidati, direzione) {
  const verso = VERSI[direzione];
  if (!verso || !corrente || !Array.isArray(candidati)) return null;
  let nelCono = null;
  let altrove = null;
  for (const c of candidati) {
    if (!c || c.id === corrente.id) continue;
    const dx = c.x - corrente.x;
    const dy = c.y - corrente.y;
    const avanti = dx * verso[0] + dy * verso[1];
    if (!(avanti > 0)) continue;
    const lato = Math.abs(dx * verso[1] - dy * verso[0]);
    const voce = { id: c.id, punteggio: avanti + 2 * lato };
    const meglio = (attuale) => !attuale || voce.punteggio < attuale.punteggio
      || (voce.punteggio === attuale.punteggio && String(voce.id) < String(attuale.id));
    if (lato <= avanti) {
      if (meglio(nelCono)) nelCono = voce;
    } else if (meglio(altrove)) {
      altrove = voce;
    }
  }
  const scelta = nelCono || altrove;
  return scelta ? scelta.id : null;
}

// Il riquadro da mostrare dopo la rivelazione. Se la provincia giusta e quella scelta stanno
// gia' nella vista, non si muove niente. Altrimenti si prende un riquadro che le contiene entrambe,
// con un margine, non piu' stretto di `LATO_MINIMO`. `giusta` e `scelta` sono `{x, y, width,
// height}` (i `getBBox()`), `scelta` puo' mancare. Torna il riquadro di partenza, o uno nuovo.
export function riquadroRivelazione(vista, giusta, scelta, margine = 0.15) {
  const scatole = [giusta, scelta].filter(Boolean);
  if (scatole.length === 0) return vista;
  if (scatole.every((s) => puntoInVista(centro(s), vista))) return vista;
  const x0 = Math.min(...scatole.map((s) => s.x));
  const y0 = Math.min(...scatole.map((s) => s.y));
  const x1 = Math.max(...scatole.map((s) => s.x + s.width));
  const y1 = Math.max(...scatole.map((s) => s.y + s.height));
  const w = Math.max(x1 - x0, LATO_MINIMO) * (1 + 2 * margine);
  const h = Math.max(y1 - y0, LATO_MINIMO) * (1 + 2 * margine);
  const cx = (x0 + x1) / 2;
  const cy = (y0 + y1) / 2;
  return [cx - w / 2, cy - h / 2, w, h];
}
