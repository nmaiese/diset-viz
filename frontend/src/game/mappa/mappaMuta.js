// La mappa muta del server resa viva dall'esterno, come fa `useMapInteractions` di Indovina la
// Regione: il markup e' del template (`_mappa_muta.html`), qui si aggiungono gli ascoltatori,
// il riquadro, le classi di stato e i segni dell'esito. Niente React, ma DOM: la parte pura
// (riquadri, "la piu' vicina in quella direzione") sta in `geometria.js`, che `node --test` prova.
//
// Le regole che non si spezzano:
// - UN solo ascoltatore `click` sull'<svg>, mai `pointerdown` e mai `preventDefault` su un
//   evento di tocco: lo scorrimento e il pinch restano del browser. Si risolve il bersaglio con
//   `closest('[data-region]')` e `closest('[data-key]')`. Nessuna conversione con
//   `getScreenCTM()`: la sagoma colpita e' il bersaglio, e cio' che serve in unita' del viewBox
//   (i centri per la tastiera, il riquadro della rivelazione) viene da `getBBox()`;
// - i centri non vengono mai da un payload: la risposta non ha nessuna coordinata;
// - la mappa dice il suo scopo e mai il nome di una provincia: ogni sagoma e' "Provincia";
// - un solo punto di sosta (roving `tabindex`): le frecce spostano il focus, Invio sceglie, Esc
//   torna indietro, Tab porta a "Conferma".

import {
  VIEWBOX_ITALIA,
  centro,
  leggiViewBox,
  puntoInVista,
  riquadroRivelazione,
  testoViewBox,
  unitaPerPixel,
  versoDelTasto,
  vicinaInDirezione,
} from "./geometria.js";

const SVG_NS = "http://www.w3.org/2000/svg";

export const VISTA_ITALIA = "italia";

function elementoSvg(nome, attributi) {
  const el = document.createElementNS(SVG_NS, nome);
  for (const [k, v] of Object.entries(attributi || {})) el.setAttribute(k, String(v));
  return el;
}

// `svg` e' `#mappa-svg`. `opzioni.onCambio({vista, selezionata, reselezioni})` dopo ogni
// cambio di vista o di selezione, `opzioni.suggerimento` e' l'elemento `role="status"` dove
// finisce la riga "Tocca una regione".
export function creaMappa(svg, { onCambio, suggerimento } = {}) {
  const gruppi = new Map();
  for (const g of svg.querySelectorAll("[data-region]")) {
    const riquadro = leggiViewBox(g.getAttribute("data-viewbox"));
    if (riquadro) gruppi.set(g.getAttribute("data-region"), { el: g, riquadro });
  }
  const tessere = new Map();
  const regioneDi = new Map();
  for (const el of svg.querySelectorAll("[data-key]")) {
    const chiave = el.getAttribute("data-key");
    tessere.set(chiave, el);
    const gruppo = el.closest("[data-region]");
    if (gruppo) regioneDi.set(chiave, gruppo.getAttribute("data-region"));
  }
  const segni = svg.querySelector("#mappa-segni");

  let vista = VISTA_ITALIA; // "italia", la chiave di una regione, o "rivelazione"
  let riquadro = VIEWBOX_ITALIA.slice();
  let selezionata = null;
  let reselezioni = 0;
  let bloccata = true;
  let rivelate = null; // {giusta, scelta} per ridisegnare i segni al ridimensionamento
  let sosta = null; // l'elemento col tabindex 0
  const bbox = new Map();

  // -- Misure dal DOM -----------------------------------------------------------------

  function scatola(el, chiave) {
    if (bbox.has(chiave)) return bbox.get(chiave);
    try {
      const r = el.getBBox();
      const voce = { x: r.x, y: r.y, width: r.width, height: r.height };
      bbox.set(chiave, voce);
      return voce;
    } catch {
      return null; // nascosta (display: none): niente misura, e niente tastiera
    }
  }

  const scatolaTessera = (chiave) => scatola(tessere.get(chiave), `t:${chiave}`);
  const scatolaRegione = (chiave) => scatola(gruppi.get(chiave).el, `r:${chiave}`);

  // Cio' che si vede davvero: con `meet` il riquadro e' centrato in un'area piu' larga o piu' alta.
  function visibile() {
    const r = svg.getBoundingClientRect();
    if (!(r.width > 0) || !(r.height > 0)) return riquadro;
    const u = unitaPerPixel(r.width, r.height, riquadro);
    const w = r.width * u;
    const h = r.height * u;
    return [riquadro[0] + riquadro[2] / 2 - w / 2, riquadro[1] + riquadro[3] / 2 - h / 2, w, h];
  }

  function aggiornaScala() {
    const r = svg.getBoundingClientRect();
    svg.style.setProperty("--mappa-u", String(Math.round(unitaPerPixel(r.width, r.height, riquadro) * 1000) / 1000));
  }

  // -- Vista, ruoli e punto di sosta -----------------------------------------------------

  function tessereVisibili() {
    const area = visibile();
    const lista = [];
    for (const chiave of tessere.keys()) {
      const s = scatolaTessera(chiave);
      if (s && puntoInVista(centro(s), area)) lista.push(chiave);
    }
    return lista;
  }

  function candidati() {
    if (vista === VISTA_ITALIA) {
      return [...gruppi.keys()].map((chiave) => {
        const s = scatolaRegione(chiave);
        return s ? { id: chiave, ...centro(s) } : null;
      }).filter(Boolean);
    }
    return tessereVisibili().map((chiave) => ({ id: chiave, ...centro(scatolaTessera(chiave)) }));
  }

  function elementoDi(id) {
    return vista === VISTA_ITALIA ? gruppi.get(id)?.el : tessere.get(id);
  }

  function mettiSosta(el) {
    if (sosta && sosta !== el) sosta.setAttribute("tabindex", "-1");
    sosta = el || null;
    if (sosta) sosta.setAttribute("tabindex", "0");
  }

  // L'etichetta e' sempre neutra ("Regione", "Provincia"): la mappa e' muta anche per chi legge.
  function applicaVista() {
    const regioni = vista === VISTA_ITALIA;
    svg.setAttribute("data-vista", regioni ? "italia" : "regione");
    for (const { el } of gruppi.values()) {
      if (regioni) {
        el.setAttribute("role", "button");
        el.setAttribute("aria-label", "Regione");
        el.setAttribute("tabindex", "-1");
      } else {
        el.removeAttribute("role");
        el.removeAttribute("aria-label");
        el.removeAttribute("tabindex");
      }
    }
    const visibili = regioni ? new Set() : new Set(tessereVisibili());
    for (const [chiave, el] of tessere) {
      if (visibili.has(chiave)) {
        el.setAttribute("role", "button");
        el.setAttribute("aria-pressed", chiave === selezionata ? "true" : "false");
        el.removeAttribute("aria-hidden");
        el.setAttribute("tabindex", "-1");
      } else {
        el.removeAttribute("role");
        el.removeAttribute("aria-pressed");
        el.setAttribute("aria-hidden", "true");
        el.removeAttribute("tabindex");
      }
    }
    sosta = null;
    if (vista === "rivelazione") return;
    if (regioni) {
      mettiSosta(gruppi.values().next().value?.el);
    } else {
      mettiSosta(selezionata ? tessere.get(selezionata) : tessereDelCentro());
    }
  }

  // La sagoma piu' vicina al centro della vista: da li' parte la tastiera nel riquadro.
  function tessereDelCentro() {
    const mio = { x: riquadro[0] + riquadro[2] / 2, y: riquadro[1] + riquadro[3] / 2 };
    let migliore = null;
    let distanza = Infinity;
    for (const chiave of tessereVisibili()) {
      const c = centro(scatolaTessera(chiave));
      const d = (c.x - mio.x) ** 2 + (c.y - mio.y) ** 2;
      if (d < distanza) {
        distanza = d;
        migliore = tessere.get(chiave);
      }
    }
    return migliore;
  }

  function mettiRiquadro(nuovo) {
    riquadro = nuovo;
    svg.setAttribute("viewBox", testoViewBox(nuovo));
    aggiornaScala();
  }

  function notifica() {
    if (onCambio) onCambio({ vista, selezionata, reselezioni });
  }

  function suggerisci(testo) {
    if (suggerimento) suggerimento.textContent = testo || "";
  }

  // -- Le azioni ------------------------------------------------------------------------

  function deseleziona() {
    if (selezionata && tessere.has(selezionata)) {
      tessere.get(selezionata).classList.remove("is-selected");
      tessere.get(selezionata).setAttribute("aria-pressed", "false");
    }
    selezionata = null;
  }

  function vaiItalia({ focus = false } = {}) {
    deseleziona();
    vista = VISTA_ITALIA;
    mettiRiquadro(VIEWBOX_ITALIA.slice());
    suggerisci("");
    applicaVista();
    if (focus && sosta) sosta.focus({ preventScroll: true });
    notifica();
  }

  function vaiRegione(chiave, { focus = false } = {}) {
    const gruppo = gruppi.get(chiave);
    if (!gruppo) return;
    deseleziona();
    vista = chiave;
    mettiRiquadro(gruppo.riquadro.slice());
    suggerisci("");
    applicaVista();
    if (focus && sosta) sosta.focus({ preventScroll: true });
    notifica();
  }

  function seleziona(chiave, { focus = false } = {}) {
    if (bloccata || vista === VISTA_ITALIA || !tessere.has(chiave)) return;
    if (selezionata === chiave) return;
    if (selezionata) reselezioni += 1;
    deseleziona();
    selezionata = chiave;
    const el = tessere.get(chiave);
    el.classList.add("is-selected");
    el.setAttribute("aria-pressed", "true");
    suggerisci("");
    mettiSosta(el);
    if (focus) el.focus({ preventScroll: true });
    notifica();
  }

  // -- Ascoltatori ----------------------------------------------------------------------

  function alClick(evento) {
    if (bloccata) return;
    const bersaglio = evento.target;
    if (!bersaglio || typeof bersaglio.closest !== "function") return;
    if (vista === VISTA_ITALIA) {
      const gruppo = bersaglio.closest("[data-region]");
      if (!gruppo) {
        suggerisci("Tocca una regione.");
        return;
      }
      vaiRegione(gruppo.getAttribute("data-region"));
      return;
    }
    const tessera = bersaglio.closest("[data-key]");
    if (!tessera) {
      suggerisci("Tocca una provincia, oppure torna indietro.");
      return;
    }
    seleziona(tessera.getAttribute("data-key"));
  }

  function chiaveDelFocus() {
    const attivo = document.activeElement;
    if (!attivo || !svg.contains(attivo)) return null;
    return vista === VISTA_ITALIA
      ? attivo.closest("[data-region]")?.getAttribute("data-region") || null
      : attivo.getAttribute("data-key");
  }

  function alTasto(evento) {
    if (bloccata || evento.altKey || evento.ctrlKey || evento.metaKey) return;
    const verso = versoDelTasto(evento.key);
    if (verso) {
      const lista = candidati();
      const corrente = lista.find((c) => c.id === chiaveDelFocus()) || lista.find((c) => elementoDi(c.id) === sosta);
      if (!corrente) return;
      evento.preventDefault();
      const prossima = vicinaInDirezione(corrente, lista, verso);
      const el = prossima ? elementoDi(prossima) : null;
      if (el) {
        mettiSosta(el);
        el.focus({ preventScroll: true });
      }
      return;
    }
    if (evento.key === "Enter" || evento.key === " ") {
      const chiave = chiaveDelFocus();
      if (!chiave) return;
      evento.preventDefault();
      if (vista === VISTA_ITALIA) vaiRegione(chiave, { focus: true });
      else seleziona(chiave, { focus: true });
      return;
    }
    if (evento.key === "Escape" && vista !== VISTA_ITALIA) {
      evento.preventDefault();
      vaiItalia({ focus: true });
    }
  }

  svg.addEventListener("click", alClick);
  svg.addEventListener("keydown", alTasto);

  let osservatore = null;
  if (typeof ResizeObserver === "function") {
    osservatore = new ResizeObserver(() => {
      aggiornaScala();
      if (rivelate) disegnaSegni();
    });
    osservatore.observe(svg);
  }

  // -- La rivelazione -------------------------------------------------------------------

  function disegnaSegni() {
    if (!segni) return;
    segni.replaceChildren();
    if (!rivelate) return;
    const r = svg.getBoundingClientRect();
    const u = unitaPerPixel(r.width, r.height, riquadro);
    const { giusta, scelta } = rivelate;
    if (scelta && scelta !== giusta && tessere.has(scelta)) {
      const c = centro(scatolaTessera(scelta));
      const g = elementoSvg("g", { class: "mappa-segno mappa-segno--scelta", transform: `translate(${c.x} ${c.y})` });
      g.append(
        elementoSvg("rect", { x: -10 * u, y: -10 * u, width: 20 * u, height: 20 * u }),
        elementoSvg("path", { d: `M${-5 * u} ${-5 * u}L${5 * u} ${5 * u}M${5 * u} ${-5 * u}L${-5 * u} ${5 * u}` }),
      );
      segni.append(g);
    }
    if (tessere.has(giusta)) {
      const c = centro(scatolaTessera(giusta));
      const g = elementoSvg("g", { class: "mappa-segno mappa-segno--giusta", transform: `translate(${c.x} ${c.y})` });
      g.append(
        elementoSvg("circle", { r: 11 * u }),
        elementoSvg("path", { d: `M${-5 * u} ${0}L${-1.5 * u} ${4 * u}L${5.5 * u} ${-4.5 * u}` }),
      );
      segni.append(g);
    }
  }

  // Rivela l'esito: blocca la mappa, segna la giusta (forma piena, con la spunta) e la scelta
  // sbagliata (tratteggio e croce), e, se non stanno nella vista, la allarga quanto basta. Ritorna
  // `{giustaInVista}`: la provincia giusta era visibile nel riquadro in cui si e' risposto?
  function rivela({ giusta, scelta }) {
    bloccata = true;
    const prima = visibile();
    const sGiusta = tessere.has(giusta) ? scatolaTessera(giusta) : null;
    const sScelta = scelta && tessere.has(scelta) ? scatolaTessera(scelta) : null;
    const giustaInVista = Boolean(sGiusta && puntoInVista(centro(sGiusta), prima));
    if (selezionata && tessere.has(selezionata)) tessere.get(selezionata).classList.remove("is-selected");
    if (tessere.has(giusta)) tessere.get(giusta).classList.add("is-right");
    if (scelta && scelta !== giusta && tessere.has(scelta)) tessere.get(scelta).classList.add("is-chosen-wrong");
    if (sGiusta) {
      const nuovo = riquadroRivelazione(prima, sGiusta, sScelta);
      if (nuovo !== prima) {
        vista = "rivelazione";
        mettiRiquadro(nuovo);
        applicaVista();
      }
    }
    rivelate = { giusta, scelta };
    disegnaSegni();
    notifica();
    return { giustaInVista };
  }

  // -- Il ciclo di una domanda -------------------------------------------------------------

  function pulisci() {
    for (const el of tessere.values()) el.classList.remove("is-selected", "is-right", "is-chosen-wrong");
    rivelate = null;
    if (segni) segni.replaceChildren();
    selezionata = null;
    reselezioni = 0;
    suggerisci("");
  }

  // Una domanda nuova: tutto pulito, e si parte dall'Italia o, al livello facile, dal riquadro
  // della regione detta.
  function inizia({ regione } = {}) {
    pulisci();
    bloccata = false;
    if (regione && gruppi.has(regione)) vaiRegione(regione);
    else vaiItalia();
  }

  return {
    inizia,
    seleziona,
    vaiItalia,
    rivela,
    selezione: () => selezionata,
    vista: () => vista,
    reselezioni: () => reselezioni,
    blocca() {
      bloccata = true;
    },
    // Il focus sulla mappa, per chi arriva da tastiera.
    focalizza() {
      if (sosta) sosta.focus({ preventScroll: true });
    },
    distruggi() {
      svg.removeEventListener("click", alClick);
      svg.removeEventListener("keydown", alTasto);
      if (osservatore) osservatore.disconnect();
    },
  };
}
