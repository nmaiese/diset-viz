import React from "react";
import { createRoot } from "react-dom/client";
import GameApp from "./guess/GiocoRegione.jsx";
import "./game.css";

// Entry di Indovina la Regione. Ogni pagina del quiz ha il suo entry (vedi
// vite.config.js): qui resta solo il mount di questo gioco, il resto sta in
// `guess/`.
const root = document.getElementById("game-root");
if (root) {
  createRoot(root).render(<GameApp />);
}
