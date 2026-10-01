import { useEffect, useMemo } from "react";
import { direzione } from "./provincia.js";

export const MAPPA_ID = "prov-map";
const VIEWBOX_ITALIA = "0 0 560 660";
const LARGHEZZA_ITALIA = 560;
const SVG_NS = "http://www.w3.org/2000/svg";

function elemento(nome, attributi = {}, testo = "") {
  const el = document.createElementNS(SVG_NS, nome);
  Object.entries(attributi).forEach(([k, v]) => el.setAttribute(k, v));
  if (testo) el.textContent = testo;
  return el;
}

// Un segno per tentativo, con la forma e il numero, mai il solo colore: un
// rombo per chi ha sbagliato, un cerchio per la provincia giusta.
function segno({ x, y, r, numero, tipo, etichetta, fontSize }) {
  const g = elemento("g", { class: `prov-segno is-${tipo}`, transform: `translate(${x} ${y})` });
  g.appendChild(elemento("title", {}, etichetta));
  if (tipo === "sbagliato") {
    g.appendChild(elemento("rect", { x: -r, y: -r, width: 2 * r, height: 2 * r, transform: "rotate(45)" }));
  } else {
    g.appendChild(elemento("circle", { r: r * 1.15 }));
  }
  g.appendChild(elemento("text", { "text-anchor": "middle", "dominant-baseline": "central", "font-size": fontSize }, numero));
  return g;
}

function freccia({ x, y, sigla, lunghezza }) {
  const punto = direzione(sigla);
  if (!punto) return null;
  const rad = (punto.gradi * Math.PI) / 180;
  const dx = Math.sin(rad);
  const dy = -Math.cos(rad);
  const x1 = x + dx * lunghezza * 0.55;
  const y1 = y + dy * lunghezza * 0.55;
  const x2 = x + dx * lunghezza * 1.7;
  const y2 = y + dy * lunghezza * 1.7;
  const testa = lunghezza * 0.35;
  const sx = (angolo) => x2 - (dx * Math.cos(angolo) - dy * Math.sin(angolo)) * testa;
  const sy = (angolo) => y2 - (dy * Math.cos(angolo) + dx * Math.sin(angolo)) * testa;
  const g = elemento("g", { class: "prov-freccia" });
  g.appendChild(elemento("line", { x1, y1, x2, y2 }));
  g.appendChild(elemento("polyline", {
    points: `${sx(0.5)},${sy(0.5)} ${x2},${y2} ${sx(-0.5)},${sy(-0.5)}`,
  }));
  return g;
}

/**
 * La mappa delle 107 province e' markup statico del template (`#prov-map`, con i
 * tracciati dallo sprite) e qui la rende viva dall'esterno: e' solo feedback,
 * non un bersaglio da cliccare. Il riquadro si stringe sulla regione al livello
 * "della regione", le sagome tentate prendono il tratteggio, la misteriosa il
 * pieno a partita finita, e ogni tentativo porta il suo numero.
 */
export function useMappaProvince({ options, region, guesses, status, solution }) {
  const centri = useMemo(() => {
    const mappa = {};
    (options || []).forEach((o) => { mappa[o.key] = o; });
    return mappa;
  }, [options]);

  useEffect(() => {
    const svg = document.getElementById(MAPPA_ID);
    if (!svg) return;
    const viewbox = region?.viewbox || VIEWBOX_ITALIA;
    svg.setAttribute("viewBox", viewbox);
    const larghezza = Number(viewbox.split(" ")[2]) || LARGHEZZA_ITALIA;
    svg.style.setProperty("--prov-tratto", String(0.8 * (larghezza / LARGHEZZA_ITALIA)));
  }, [region]);

  useEffect(() => {
    const svg = document.getElementById(MAPPA_ID);
    if (!svg) return;
    const finita = status === "won" || status === "lost";
    const inRegione = region ? new Set(Object.keys(centri)) : null;
    svg.querySelectorAll(".prov-tile").forEach((tile) => {
      const key = tile.getAttribute("data-key");
      tile.classList.remove("is-context", "is-guessed-wrong", "is-guessed-correct", "is-mystery");
      if (inRegione && !inRegione.has(key)) tile.classList.add("is-context");
      const tentativo = guesses.find((g) => g.province_key === key);
      if (tentativo) tile.classList.add(tentativo.correct ? "is-guessed-correct" : "is-guessed-wrong");
      if (finita && solution && key === solution.province_key) tile.classList.add("is-mystery");
    });

    const segni = document.getElementById("prov-marks");
    if (!segni) return;
    segni.replaceChildren();
    const viewbox = region?.viewbox || VIEWBOX_ITALIA;
    const scala = (Number(viewbox.split(" ")[2]) || LARGHEZZA_ITALIA) / LARGHEZZA_ITALIA;
    const r = 7 * scala;
    guesses.forEach((g, i) => {
      const c = centri[g.province_key];
      if (!c) return;
      segni.appendChild(segno({
        x: c.x, y: c.y, r, numero: String(i + 1), fontSize: 9 * scala,
        tipo: g.correct ? "giusto" : "sbagliato",
        etichetta: `Tentativo ${i + 1}: ${g.province}`,
      }));
    });
    const ultimo = guesses[guesses.length - 1];
    if (status === "playing" && ultimo && !ultimo.correct && centri[ultimo.province_key]) {
      const c = centri[ultimo.province_key];
      const f = freccia({ x: c.x, y: c.y, sigla: ultimo.direction, lunghezza: r * 2.4 });
      if (f) segni.appendChild(f);
    }
    if (finita && solution && !guesses.some((g) => g.correct) && centri[solution.province_key]) {
      const c = centri[solution.province_key];
      segni.appendChild(segno({
        x: c.x, y: c.y, r, numero: "✓", fontSize: 10 * scala, tipo: "giusto",
        etichetta: `La provincia era ${solution.province}`,
      }));
    }
  }, [guesses, status, solution, centri, region]);
}
