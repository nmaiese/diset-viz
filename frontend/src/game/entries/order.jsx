import React from "react";
import { createRoot } from "react-dom/client";
import OrderApp from "../order.jsx";
import "../game.css";

// Un entry per pagina: il template server ha l'elemento `order-root`.
const root = document.getElementById("order-root");
if (root) {
  createRoot(root).render(<OrderApp />);
}
