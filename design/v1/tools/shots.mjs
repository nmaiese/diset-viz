// Screenshot e controlli dei prototipi con Chrome headless pilotato via CDP.
//
//   node design/v1/tools/shots.mjs prima   la produzione, prima del ridisegno
//   node design/v1/tools/shots.mjs dopo    i prototipi in dist/pagine
//   node design/v1/tools/shots.mjs check   scorrimento orizzontale e tastiera sui prototipi
//
// Zero dipendenze: Node 24 ha WebSocket e fetch globali. Un Chrome alla volta,
// pagine in sequenza, per non stressare una macchina da 8 GB.
//
// Le larghezze da telefono passano da Emulation.setDeviceMetricsOverride e mai da
// --window-size: nel nuovo headless la finestra ha un minimo di 500px, e con
// --window-size=375 la pagina vede 500. Dentro la sandbox di Claude Code Chrome
// non disegna: va lanciato fuori.

import { spawn } from "node:child_process";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const V1 = resolve(HERE, "..");
const CHROME = process.env.CHROME || "/usr/bin/google-chrome";
const PROD = "https://divarioitalia.it";

// Le pagine di esempio: stesse chiavi dei prototipi in dist/pagine.
const PAGES = {
  home: "/",
  indicatore: "/indicatore/pil-pro-capite/ter-901",
  regione: "/regione/puglia",
  provincia: "/provincia/lecce",
  articolo: "/blog/infortuni-lavoro-province",
  classifica: "/qualita-della-vita/classifica/regioni",
  "qualita-della-vita": "/qualita-della-vita",
};

const VIEWPORTS = {
  375: { width: 375, height: 812, deviceScaleFactor: 2, mobile: true },
  1440: { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false },
};
const THEMES = { chiaro: "light", scuro: "dark" };

// Terze parti che la produzione carica: consenso, annunci, analitica, login.
const BLOCKED = [
  "*googletagmanager.com*", "*googlesyndication.com*", "*doubleclick.net*",
  "*iubenda.com*", "*adtrafficquality.google*", "*cloudflareinsights.com*",
  "*supabase.co*", "*google-analytics.com*", "*fundingchoicesmessages.google.com*",
];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function launch() {
  const profile = mkdtempSync(join(tmpdir(), "divario-shots-"));
  const proc = spawn(CHROME, [
    "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    "--hide-scrollbars", "--mute-audio", "--remote-debugging-port=0",
    `--user-data-dir=${profile}`, "about:blank",
  ], { stdio: ["ignore", "ignore", "pipe"] });
  const wsUrl = await new Promise((ok, ko) => {
    let buf = "";
    const timer = setTimeout(() => ko(new Error(`Chrome non risponde. Stderr: ${buf.slice(-400)}`)), 20000);
    proc.stderr.on("data", (d) => {
      buf += d.toString();
      const m = buf.match(/DevTools listening on (ws:\/\/\S+)/);
      if (m) { clearTimeout(timer); ok(m[1]); }
    });
    proc.on("exit", (code) => ko(new Error(`Chrome uscito con ${code}. Stderr: ${buf.slice(-400)}`)));
  });
  const ws = new WebSocket(wsUrl);
  await new Promise((ok, ko) => { ws.onopen = ok; ws.onerror = () => ko(new Error("WebSocket CDP non aperto")); });
  let id = 0;
  const pending = new Map();
  const listeners = [];
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { ok, ko, method } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) ko(new Error(`${method}: ${msg.error.message}`));
      else ok(msg.result);
    } else if (msg.method) {
      for (const l of listeners) l(msg);
    }
  };
  const send = (method, params = {}, sessionId) => new Promise((ok, ko) => {
    const mid = ++id;
    pending.set(mid, { ok, ko, method });
    ws.send(JSON.stringify({ id: mid, method, params, ...(sessionId ? { sessionId } : {}) }));
  });
  const waitFor = (method, sessionId, timeout = 45000) => new Promise((ok, ko) => {
    const timer = setTimeout(() => ko(new Error(`attesa scaduta per ${method}`)), timeout);
    const l = (msg) => {
      if (msg.method === method && msg.sessionId === sessionId) {
        clearTimeout(timer);
        listeners.splice(listeners.indexOf(l), 1);
        ok(msg.params);
      }
    };
    listeners.push(l);
  });
  const close = () => { try { ws.close(); } catch {} proc.kill("SIGKILL"); rmSync(profile, { recursive: true, force: true }); };
  return { send, waitFor, close };
}

async function openPage(cdp, { viewport, theme, blocked, initScript }) {
  const { targetId } = await cdp.send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });
  const s = (m, p) => cdp.send(m, p, sessionId);
  await s("Page.enable");
  await s("Runtime.enable");
  await s("Network.enable");
  if (blocked) await s("Network.setBlockedURLs", { urls: blocked });
  await s("Emulation.setDeviceMetricsOverride", viewport);
  await s("Emulation.setEmulatedMedia", { features: [
    { name: "prefers-color-scheme", value: theme },
    { name: "prefers-reduced-motion", value: "reduce" },
  ] });
  if (initScript) await s("Page.addScriptToEvaluateOnNewDocument", { source: initScript });
  return { s, sessionId, targetId };
}

async function evaluate(s, expression) {
  const r = await s("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(`eval: ${r.exceptionDetails.text} ${r.exceptionDetails.exception?.description || ""}`);
  return r.result.value;
}

// Scorre la pagina per far scattare IntersectionObserver e immagini lazy, poi
// aspetta font e immagini e torna in cima.
const SETTLE = `(async () => {
  const step = Math.max(200, Math.floor(innerHeight * 0.8));
  for (let y = 0; y < document.documentElement.scrollHeight; y += step) {
    scrollTo(0, y); await new Promise(r => setTimeout(r, 120));
  }
  await document.fonts.ready;
  await Promise.all([...document.images].map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; setTimeout(r, 4000); })));
  scrollTo(0, 0); await new Promise(r => setTimeout(r, 300));
  return { h: document.documentElement.scrollHeight, w: document.documentElement.clientWidth,
           sw: document.documentElement.scrollWidth, theme: document.documentElement.dataset.theme || null };
})()`;

async function capture(cdp, url, { viewport, theme, blocked, initScript }, outBase) {
  const { s, sessionId, targetId } = await openPage(cdp, { viewport, theme, blocked, initScript });
  const loaded = cdp.waitFor("Page.loadEventFired", sessionId);
  await s("Page.navigate", { url });
  await loaded;
  if (initScript) await evaluate(s, initScript);
  const info = await evaluate(s, SETTLE);
  const fold = await s("Page.captureScreenshot", { format: "webp", quality: 80 });
  writeFileSync(`${outBase}-fold.webp`, Buffer.from(fold.data, "base64"));
  // Pagina intera a 1x: con dpr 2 un profilo regione supererebbe i limiti del JPEG.
  const scale = 1 / viewport.deviceScaleFactor;
  const full = await s("Page.captureScreenshot", {
    format: "jpeg", quality: 70, captureBeyondViewport: true,
    clip: { x: 0, y: 0, width: viewport.width, height: Math.min(info.h, 30000), scale },
  });
  writeFileSync(`${outBase}-full.jpg`, Buffer.from(full.data, "base64"));
  await cdp.send("Target.closeTarget", { targetId });
  return { ...info, foldBytes: Buffer.from(fold.data, "base64").length, fullBytes: Buffer.from(full.data, "base64").length };
}

async function shoot(label, urlFor, { blocked, initScript } = {}) {
  const outDir = join(V1, "screens", label);
  mkdirSync(outDir, { recursive: true });
  const cdp = await launch();
  const manifest = { label, blocked: blocked || [], shots: [] };
  try {
    for (const [name, path] of Object.entries(PAGES)) {
      const url = urlFor(name, path);
      if (!url) continue;
      for (const [vw, viewport] of Object.entries(VIEWPORTS)) {
        for (const [tname, theme] of Object.entries(THEMES)) {
          const base = join(outDir, `${name}-${vw}-${tname}`);
          const info = await capture(cdp, url, { viewport, theme, blocked, initScript }, base);
          manifest.shots.push({ page: name, url, viewport: Number(vw), theme: tname, ...info });
          const over = info.sw > info.w ? `  SFORA di ${info.sw - info.w}px` : "";
          console.log(`${label} ${name} ${vw} ${tname}: ${info.h}px${over}`);
        }
      }
    }
  } finally {
    cdp.close();
  }
  writeFileSync(join(outDir, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
}

// Per ogni pagina dei prototipi, a 320/360/375 in chiaro e in scuro: niente
// scorrimento orizzontale (clientWidth, non innerWidth, che in emulazione mobile
// si allarga col contenuto), e un giro di Tab con focus visibile.
const OVERFLOW = `(() => {
  const de = document.documentElement, W = de.clientWidth, bad = [];
  if (de.scrollWidth > W) {
    for (const el of document.querySelectorAll("body *")) {
      const r = el.getBoundingClientRect();
      if (r.right > W + 0.5 && r.width > 0) {
        let clipped = false;
        for (let p = el.parentElement; p; p = p.parentElement) {
          const ox = getComputedStyle(p).overflowX;
          if (ox === "auto" || ox === "scroll" || ox === "hidden" || ox === "clip") { clipped = true; break; }
        }
        if (!clipped) bad.push((el.tagName + "." + [...el.classList].join(".")).slice(0, 80) + " " + Math.round(r.right));
      }
    }
  }
  return { W, SW: de.scrollWidth, bad: bad.slice(0, 8) };
})()`;

const FOCUS = `(() => {
  const el = document.activeElement;
  if (!el || el === document.body) return null;
  const cs = getComputedStyle(el);
  const visible = (cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) >= 2) || (cs.boxShadow && cs.boxShadow !== "none");
  const r = el.getBoundingClientRect();
  return { tag: el.tagName, cls: String(el.className).slice(0, 40), text: (el.textContent || "").trim().slice(0, 30),
           visible, inView: r.bottom > 0 && r.top < innerHeight };
})()`;

async function check() {
  const dist = join(V1, "dist", "pagine");
  const cdp = await launch();
  let failures = 0;
  try {
    for (const name of Object.keys(PAGES)) {
      const file = join(dist, `${name}.html`);
      if (!existsSync(file)) { console.log(`manca ${name}.html, salto`); continue; }
      for (const width of [320, 360, 375]) {
        for (const [tname, theme] of Object.entries(THEMES)) {
          const viewport = { width, height: 740, deviceScaleFactor: 1, mobile: true };
          const { s, sessionId, targetId } = await openPage(cdp, { viewport, theme, initScript: "document.documentElement.dataset.shot='1'" });
          const loaded = cdp.waitFor("Page.loadEventFired", sessionId);
          await s("Page.navigate", { url: pathToFileURL(file).href });
          await loaded;
          await evaluate(s, "document.documentElement.dataset.shot='1'");
          await evaluate(s, "document.fonts.ready.then(() => 1)");
          const o = await evaluate(s, OVERFLOW);
          if (o.SW > o.W) { failures++; console.log(`SFORA ${name} ${width} ${tname}: ${o.SW} su ${o.W}`, o.bad); }
          await cdp.send("Target.closeTarget", { targetId });
        }
      }
      // Tastiera a 1440 in chiaro: la prima fermata e' il salto al contenuto,
      // ogni fermata ha un focus visibile.
      const { s, sessionId, targetId } = await openPage(cdp, { viewport: VIEWPORTS[1440], theme: "light", initScript: "document.documentElement.dataset.shot='1'" });
      const loaded = cdp.waitFor("Page.loadEventFired", sessionId);
      await s("Page.navigate", { url: pathToFileURL(file).href });
      await loaded;
      const stops = [];
      for (let i = 0; i < 25; i++) {
        await s("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 });
        await s("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 });
        await sleep(30);
        const f = await evaluate(s, FOCUS);
        if (f) stops.push(f);
      }
      const first = stops[0];
      if (!first || !/contenuto/i.test(first.text + first.cls)) { failures++; console.log(`TASTIERA ${name}: la prima fermata non e' il salto al contenuto`, first); }
      const hidden = stops.filter((f) => !f.visible);
      if (hidden.length) { failures++; console.log(`TASTIERA ${name}: focus non visibile su`, hidden.slice(0, 4)); }
      await cdp.send("Target.closeTarget", { targetId });
      console.log(`check ${name}: fatto`);
    }
  } finally {
    cdp.close();
  }
  if (failures) { console.log(`${failures} problemi`); process.exit(1); }
  console.log("nessun problema");
}

const mode = process.argv[2];
if (mode === "prima") {
  const day = process.argv[3] || new Date().toISOString().slice(0, 10);
  await shoot(join("prima", day), (_n, path) => PROD + path, { blocked: BLOCKED });
} else if (mode === "dopo") {
  const dist = join(V1, "dist", "pagine");
  const only = process.argv[3] ? process.argv[3].split(",") : null;
  await shoot("dopo", (name) => {
    if (only && !only.includes(name)) return null;
    const f = join(dist, `${name}.html`);
    return existsSync(f) ? pathToFileURL(f).href : null;
  }, { initScript: "document.documentElement.dataset.shot='1'" });
} else if (mode === "artifact") {
  // Il file unico dell'Artifact, avvolto come lo avvolge claude.ai, con
  // l'ancora di ogni pagina: controlla che il router mostri la sezione giusta.
  const file = join(V1, "dist", "artifact", "divario-italia-1-0.html");
  const { readFileSync } = await import("node:fs");
  const wrapped = join(tmpdir(), "divario-artifact.html");
  writeFileSync(wrapped, '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>' + readFileSync(file, "utf-8") + "</body></html>");
  const outDir = join(V1, "screens", "artifact");
  mkdirSync(outDir, { recursive: true });
  const cdp = await launch();
  try {
    for (const hash of (process.argv[3] || "copertina,indicatore").split(",")) {
      for (const vw of ["1440", "375"]) {
        const info = await capture(cdp, pathToFileURL(wrapped).href + "#" + hash, { viewport: VIEWPORTS[vw], theme: "light" }, join(outDir, `${hash}-${vw}`));
        console.log(`artifact ${hash} ${vw}: ${info.h}px`);
      }
    }
  } finally { cdp.close(); }
} else if (mode === "check") {
  await check();
} else {
  console.error("uso: node design/v1/tools/shots.mjs prima|dopo|check");
  process.exit(2);
}
