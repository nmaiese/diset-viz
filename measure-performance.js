const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const URL = 'https://divarioitalia.it/regione/molise';
const RUNS = 3;
const VIEWPORT = { width: 1024, height: 768 };

async function measureRun(page, label) {
  const htmlSizeKB = await page.evaluate(() => {
    return document.documentElement.outerHTML.length / 1024;
  });

  const domNodeCount = await page.evaluate(() => {
    return document.querySelectorAll('*').length;
  });

  const lcp = await page.evaluate(() => {
    return new Promise((resolve) => {
      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const lastEntry = entries[entries.length - 1];
        resolve(Math.round(lastEntry.startTime));
        observer.disconnect();
      });
      observer.observe({ type: 'largest-contentful-paint', buffered: true });
    });
  });

  return { htmlSizeKB: Math.round(htmlSizeKB * 100) / 100, domNodeCount, lcp };
}

async function runBaseline(browser) {
  console.log('Running baseline (no transformations)...');
  const runs = [];
  for (let i = 0; i < RUNS; i++) {
    const page = await browser.newPage({ viewport: VIEWPORT });
    await page.goto(URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(500);
    const metrics = await measureRun(page, 'baseline');
    console.log(`  Run ${i + 1}:`, metrics);
    runs.push(metrics);
    await page.close();
  }
  return runs;
}

async function runWithTransformations(browser) {
  console.log('Running with proposta.css + trasforma.js...');
  const propostaCSS = fs.readFileSync(path.join(__dirname, 'proposta.css'), 'utf-8');
  const trasformaJS = fs.readFileSync(path.join(__dirname, 'trasforma.js'), 'utf-8');

  const runs = [];
  for (let i = 0; i < RUNS; i++) {
    const page = await browser.newPage({ viewport: VIEWPORT });
    await page.goto(URL, { waitUntil: 'networkidle' });
    
    await page.addStyleTag({ content: propostaCSS });
    await page.evaluate(trasformaJS);
    await page.waitForTimeout(500);
    
    const metrics = await measureRun(page, 'after');
    console.log(`  Run ${i + 1}:`, metrics);
    runs.push(metrics);
    await page.close();
  }
  return runs;
}

function computeAverage(runs) {
  if (runs.length === 0) return { htmlSizeKB: 0, domNodeCount: 0, lcp: 0 };
  return {
    htmlSizeKB: Math.round((runs.reduce((a, b) => a + b.htmlSizeKB, 0) / runs.length) * 100) / 100,
    domNodeCount: Math.round(runs.reduce((a, b) => a + b.domNodeCount, 0) / runs.length),
    lcp: Math.round(runs.reduce((a, b) => a + b.lcp, 0) / runs.length)
  };
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  
  try {
    const baseline = await runBaseline(browser);
    const after = await runWithTransformations(browser);
    
    const output = {
      viewport: VIEWPORT,
      theme: 'dark (local only)',
      url: URL,
      runs: RUNS,
      baseline: {
        runs: baseline,
        average: computeAverage(baseline)
      },
      after: {
        runs: after,
        average: computeAverage(after)
      }
    };
    
    const outPath = '/tmp/opencode/ux-lettura/out/performance.json';
    fs.writeFileSync(outPath, JSON.stringify(output, null, 2));
    console.log('\nResults saved to:', outPath);
    console.log('\nBaseline average:', output.baseline.average);
    console.log('After average:', output.after.average);
    
  } finally {
    await browser.close();
  }
}

main().catch(console.error);