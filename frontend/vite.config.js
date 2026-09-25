import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

// Due entry in una build sola: il gioco (input "game", servito sotto "/quiz",
// game.html carica dist/assets/game.js|css) e il controllo di accesso della
// testata (input "site", vanilla, su ogni pagina SSR). Vite chiama JS e CSS
// di ogni entry con la sua chiave. L'atlante e il confronto React ("index")
// se ne sono andati il 25 settembre 2026: sono pagine della 1.0 rese dal
// server, con le loro isole in app/static/js/.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../app/static/dist",
    emptyOutDir: true,
    assetsDir: "assets",
    rollupOptions: {
      input: {
        game: resolve(__dirname, "src/game/main.jsx"),
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
