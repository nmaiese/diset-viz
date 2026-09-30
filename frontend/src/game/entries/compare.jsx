import React from "react";
import { createRoot } from "react-dom/client";
import CompareApp from "../compare.jsx";
import "../game.css";

// Un entry per pagina: il template server ha l'elemento `compare-root`.
const root = document.getElementById("compare-root");
if (root) {
  createRoot(root).render(<CompareApp />);
}
