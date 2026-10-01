import React from "react";
import { createRoot } from "react-dom/client";
import LeaderboardApp from "../leaderboard.jsx";
import "../game.css";

// Un entry per pagina: il template server ha l'elemento `leaderboard-root`.
const root = document.getElementById("leaderboard-root");
if (root) {
  createRoot(root).render(<LeaderboardApp />);
}
