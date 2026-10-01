import React from "react";
import { createRoot } from "react-dom/client";
import HubApp from "../hub.jsx";
import "../game.css";

// Un entry per pagina: il template server ha l'elemento `hub-root`.
const root = document.getElementById("hub-root");
if (root) {
  createRoot(root).render(<HubApp />);
}
