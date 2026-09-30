import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

// Un entry per pagina del quiz (hub, indovina, compare, order, leaderboard,
// serviti sotto "/quiz") più il controllo di accesso della testata ("site",
// vanilla, su ogni pagina SSR). Vite chiama JS e CSS di ogni entry con la sua
// chiave, e i moduli condivisi (React, supabase, shared.jsx) finiscono in
// chunk con hash. Gli entry hanno nome fisso e i template li caricano con
// `asset_url()`, vedi docs/ACCOUNT.md. L'atlante e il confronto React
// ("index") se ne sono andati il 25 settembre 2026: sono pagine della 1.0 rese
// dal server, con le loro isole in app/static/js/.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../app/static/dist",
    emptyOutDir: true,
    assetsDir: "assets",
    rollupOptions: {
      input: {
        "quiz-hub": resolve(__dirname, "src/game/entries/hub.jsx"),
        "quiz-indovina": resolve(__dirname, "src/game/main.jsx"),
        "quiz-provincia": resolve(__dirname, "src/game/entries/provincia.jsx"),
        "quiz-compare": resolve(__dirname, "src/game/entries/compare.jsx"),
        "quiz-order": resolve(__dirname, "src/game/entries/order.jsx"),
        "quiz-leaderboard": resolve(__dirname, "src/game/entries/leaderboard.jsx"),
        // Controllo login/account nel masthead (Fase 5), su ogni pagina SSR.
        // Vanilla, supabase caricato solo se serve. blog_base.html carica
        // dist/assets/site.js.
        site: resolve(__dirname, "src/site/auth.js"),
      },
      output: {
        entryFileNames: "assets/[name].js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name][extname]",
      },
    },
  },
});
