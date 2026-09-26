#!/usr/bin/env node
/*
 * L'audit del telefono: le pagine chiave del sito su un telefono vero
 * (contesto touch, 390x844, 320x640, 844x390 in orizzontale) e cinque
 * controlli, con le soglie scritte qui sotto.
 *
 *   node scripts/audit_viewport.cjs [--base URL] [--pagine /,/atlante] [--json]
 *
 * Serve Playwright per Node con un Chromium: il modulo si cerca come d'uso
 * (NODE_PATH compreso), il browser in PLAYWRIGHT_CHROMIUM, o in
 * /opt/pw-browsers se c'e'. Esce 1 se una soglia salta, 2 se manca
 * Playwright. La prova tests/integration/test_viewport_mobile.py lo lancia
 * contro l'app in un server locale, e si salta dicendolo dove Playwright non
 * c'e'.
 *
 * I controlli:
 *   1. niente scorrimento orizzontale della pagina (WCAG 1.4.10);
 *   2. le barre ferme in alto (testata, barra delle sezioni, striscia) a meta'
 *      pagina, scendendo e poi risalendo, sotto il 25% dello schermo in
 *      verticale e il 35% in orizzontale;
 *   3. i controlli (bottoni, campi, sommari, link fuori dal testo) alti almeno
 *      44 pixel al tocco, contando l'area allargata dall'::after; i link di
 *      testo dentro un paragrafo o un elenco almeno 24 (WCAG 2.5.8);
 *   4. ogni voce della barra delle sezioni porta la sua sezione sotto le barre;
 *   5. nessun errore JavaScript.
 */
"use strict";

const fs = require("fs");

const args = process.argv.slice(2);
function arg(name, fallback) {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
}
const BASE = arg("--base", process.env.BASE || "http://127.0.0.1:5050");
const PAGES = arg("--pagine", [
  "/", "/atlante", "/confronto", "/regioni", "/regione/campania", "/province", "/provincia/lecce",
  "/temi", "/tema/lavoro-e-conciliazione", "/indicatore/tasso-di-turisticita/ter-105",
  "/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001/province", "/qualita-della-vita",
  "/qualita-della-vita/classifica/province", "/divari-regionali", "/ricerca?q=lavoro", "/blog",
  "/metodologia", "/catalogo-dati",
].join(",")).split(",").filter(Boolean);
const VIEWPORTS = [
  { name: "390x844", width: 390, height: 844, stack: 0.25 },
  { name: "320x640", width: 320, height: 640, stack: 0.25 },
  { name: "844x390", width: 844, height: 390, stack: 0.35 },
];
const TARGET = 43.5, TEXT_TARGET = 23.5;

let chromium;
try { ({ chromium } = require("playwright")); }
catch (e) { console.error("audit_viewport: Playwright per Node non c'e' (npm i playwright, o NODE_PATH)."); process.exit(2); }

function executable() {
  if (process.env.PLAYWRIGHT_CHROMIUM) return process.env.PLAYWRIGHT_CHROMIUM;
  const root = "/opt/pw-browsers";
  if (!fs.existsSync(root)) return undefined;
  for (const dir of fs.readdirSync(root).filter((d) => d.startsWith("chromium")).sort().reverse()) {
    const bin = `${root}/${dir}/chrome-linux/chrome`;
    if (fs.existsSync(bin)) return bin;
  }
  return undefined;
}

async function stack(page) {
  return page.evaluate(() => {
    const H = innerHeight, W = innerWidth;
    let bottom = 0;
    for (const el of document.querySelectorAll("body *")) {
      const cs = getComputedStyle(el);
      if ((cs.position !== "fixed" && cs.position !== "sticky") || cs.display === "none" || cs.visibility === "hidden" || parseFloat(cs.opacity) < 0.1) continue;
      const r = el.getBoundingClientRect();
      if (r.top <= 200 && r.top >= -1 && r.bottom > 1 && r.width > W * 0.5 && r.height < H * 0.6) bottom = Math.max(bottom, r.bottom);
    }
    return bottom / H;
  });
}

async function audit(browser, vp) {
  const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, isMobile: true, hasTouch: true });
  const page = await context.newPage();
  const out = [];
  for (const path of PAGES) {
    const errors = [];
    page.removeAllListeners("pageerror");
    page.on("pageerror", (e) => errors.push(e.message.slice(0, 120)));
    const res = await page.goto(BASE + path, { waitUntil: "networkidle" });
    const fail = [];
    if (!res || res.status() !== 200) { out.push({ vp: vp.name, path, fail: [`stato ${res && res.status()}`] }); continue; }
    const shape = await page.evaluate(({ TARGET, TEXT_TARGET }) => {
      const small = {};
      for (const el of document.querySelectorAll("a[href], button, summary, select, input:not([type=hidden])")) {
        const cs = getComputedStyle(el);
        if (cs.display === "none" || cs.visibility === "hidden" || el.closest("[hidden], svg, .sr-only") || el.classList.contains("sr-only") || el.classList.contains("skiplink")) continue;
        const r = el.getBoundingClientRect();
        if (!r.width || !r.height) continue;
        let h = r.height;
        // Una casella o un bottone radio dentro la sua etichetta: il bersaglio
        // e' l'etichetta intera.
        const label = (el.type === "radio" || el.type === "checkbox") && el.closest("label");
        if (label) h = Math.max(h, label.getBoundingClientRect().height);
        const af = getComputedStyle(el, "::after");
        if (af.content && af.content !== "none" && af.position === "absolute") h = Math.max(h, r.height - (parseFloat(af.top) || 0) - (parseFloat(af.bottom) || 0));
        // un link esteso a tutta la scheda (::after con inset 0) vale quanto la scheda
        const card = el.closest(".card, .story, .door, .game, .dr-card, .terr, li");
        if (af.content && af.content !== "none" && af.position === "absolute" && card) h = Math.max(h, card.getBoundingClientRect().height);
        // Un link dentro una frase segue l'interlinea del testo: e' l'eccezione
        // della WCAG 2.5.8 e non si conta. Un link che e' tutta la voce di un
        // elenco deve arrivare almeno a 24.
        const inline = cs.display === "inline" && el.tagName === "A";
        const alone = inline && el.parentElement && el.parentElement.tagName === "LI" && el.parentElement.textContent.trim() === el.textContent.trim();
        if (inline && !alone) continue;
        const text = alone;
        const need = text ? TEXT_TARGET : TARGET;
        if (h < need) {
          const k = `${el.tagName.toLowerCase()}.${String(el.className).split(" ")[0] || "-"}${text ? " (testo)" : ""}`;
          small[k] = (small[k] || 0) + 1;
        }
      }
      return { overflow: document.documentElement.scrollWidth > innerWidth, height: document.documentElement.scrollHeight, small };
    }, { TARGET, TEXT_TARGET });
    if (shape.overflow) fail.push("scorre di lato");
    for (const [k, n] of Object.entries(shape.small)) fail.push(`bersaglio piccolo ${k} x${n}`);
    // barre ferme: a meta' pagina scendendo, e dopo una risalita
    await page.evaluate(() => scrollTo(0, document.documentElement.scrollHeight * 0.3));
    await page.waitForTimeout(150);
    await page.evaluate(() => scrollTo(0, document.documentElement.scrollHeight * 0.5));
    await page.waitForTimeout(450);
    const down = await stack(page);
    await page.evaluate(() => scrollBy(0, -240));
    await page.waitForTimeout(450);
    const up = await stack(page);
    if (Math.max(down, up) > vp.stack) fail.push(`barre ferme ${Math.round(Math.max(down, up) * 100)}% (soglia ${vp.stack * 100}%)`);
    // ancore della barra delle sezioni
    const ids = await page.evaluate(() => [...document.querySelectorAll(".toc a[href^='#']")].map((a) => a.getAttribute("href")));
    for (const id of ids) {
      await page.goto(BASE + path + id, { waitUntil: "networkidle" });
      await page.waitForTimeout(400);
      const r = await page.evaluate((sel) => {
        const t = document.querySelector(sel);
        if (!t) return null;
        let cover = 0;
        for (const el of document.querySelectorAll(".hdr, .toc, .stripbar.is-on")) {
          const cs = getComputedStyle(el);
          if ((cs.position === "sticky" || cs.position === "fixed") && cs.visibility !== "hidden") {
            const b = el.getBoundingClientRect();
            if (b.top <= 1 && b.bottom > 0) cover = Math.max(cover, b.bottom);
          }
        }
        return { top: t.getBoundingClientRect().top, cover };
      }, id);
      if (!r) fail.push(`ancora ${id} senza sezione`);
      else if (r.top < r.cover - 1) fail.push(`ancora ${id} sotto le barre (${Math.round(r.top)} < ${Math.round(r.cover)})`);
    }
    if (errors.length) fail.push(`errori JavaScript: ${errors.join(" | ")}`);
    out.push({ vp: vp.name, path, height: shape.height, stack: Math.round(Math.max(down, up) * 100), fail });
  }
  await context.close();
  return out;
}

(async () => {
  const browser = await chromium.launch({ executablePath: executable() });
  let rows = [];
  try { for (const vp of VIEWPORTS) rows = rows.concat(await audit(browser, vp)); }
  finally { await browser.close(); }
  if (args.includes("--json")) console.log(JSON.stringify(rows));
  else for (const r of rows) console.log(`${r.fail.length ? "NO" : "ok"}  ${r.vp}  ${r.path}  ${r.stack ?? "-"}%  ${r.fail.join(", ")}`);
  process.exit(rows.some((r) => r.fail.length) ? 1 : 0);
})();
