import { useEffect, useMemo, useRef } from "react";
import { prefersReducedMotion } from "../shared.jsx";
import { MAP_FRAME_ID } from "./api.js";

/**
 * La mappa è markup SVG statico, iniettato lato server dallo stesso partial
 * usato da /regioni (app/templates/_italy_map.html), non un componente React:
 * evita di duplicare ~60KB di path geografici nel bundle del gioco. Questo
 * hook la rende interattiva "dall'esterno" tramite DOM API imperative:
 * click/tastiera per tentare, tooltip col nome regione, classi di stato.
 */
export function useMapInteractions({ regions, guesses, status, solution, onGuess, submitting }) {
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
