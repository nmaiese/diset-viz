import React from "react";
import { createRoot } from "react-dom/client";
import GiocoMappa from "../mappa/GiocoMappa.jsx";
import "../game.css";
import "../mappa/mappa.css";

// Entry di "Dov'e' la provincia?": il template server ha l'elemento `game-root`, e la mappa muta
// (`#mappa-svg`) che il gioco rende viva dall'esterno.
const root = document.getElementById("game-root");
if (root) {
  createRoot(root).render(<GiocoMappa />);
}
