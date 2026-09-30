import React from "react";
import { createRoot } from "react-dom/client";
import GiocoProvincia from "../guess/GiocoProvincia.jsx";
import "../game.css";

// Entry di Indovina la Provincia: il template server ha l'elemento `game-root`.
const root = document.getElementById("game-root");
if (root) {
  createRoot(root).render(<GiocoProvincia />);
}
