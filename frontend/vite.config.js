import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

// Two independent SPA entries sharing one Vite build: the atlas (input key
// "index", served at "/", app.html hardcodes dist/assets/index.js|css) and
// the region-guessing game (input key "game", served at "/gioco",
// game.html hardcodes dist/assets/game.js|css). Vite names each entry's JS
// and CSS output after its rollupOptions.input key, so "index" preserves
// the atlas filenames exactly.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../app/static/dist",
    emptyOutDir: true,
    assetsDir: "assets",
    rollupOptions: {
      input: {
        index: resolve(__dirname, "src/main.jsx"),
        game: resolve(__dirname, "src/game/main.jsx"),
        // Console di monitoraggio (Fase 4): JS puro, solo supabase-js Realtime,
        // niente React. pipeline_console.html carica dist/assets/monitor.js.
        monitor: resolve(__dirname, "src/monitor/main.js"),
      },
      output: {
        entryFileNames: "assets/[name].js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name][extname]",
      },
    },
  },
});
