const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT_DIR = '/tmp/opencode/ux-lettura/out';
fs.mkdirSync(OUT_DIR, { recursive: true });

// Simple CSS to apply (proposta.css)
const PROPOSTA_CSS = `
/* proposta.css - custom styles for testing */
table { width: 100%; border-collapse: collapse; }
table td, table th { padding: 8px; border: 1px solid #ddd; }
details { margin-bottom: 1rem; }
details[open] summary::before { content: "▼ "; }
details:not([open]) summary::before { content: "▶ "; }
`;

// JS to close all details (trasforma.js)
const TRASFORMA_JS = `
// trasforma.js - closes all table details
(function() {
  document.querySelectorAll('details.regione-area').forEach(d => d.removeAttribute('open'));
})();
`;

async function countVisibleRows(page) {
  return await page.$$eval('details.regione-area[open] table tbody tr', rows => rows.length);
}

async function countRowsInClosedDetails(page) {
  return await page.$$eval('details.regione-area:not([open]) table tbody tr', rows => rows.length);
}

async function getFilterCount(page) {
  const el = await page.$('.n--count');
  if (el) {
    const value = await el.getAttribute('value');
    return parseInt(value) || 0;
  }
  return 0;
}

async function runTest(filterType, filterValue, page) {
  console.log(`\n=== Testing ${filterType}: "${filterValue}" ===`);
  
  // Screenshot before filter
  const beforePath = path.join(OUT_DIR, `before-${filterType}.png`);
  await page.screenshot({ path: beforePath, fullPage: true });
  
  const visibleBefore = await countVisibleRows(page);
  const closedBefore = await countRowsInClosedDetails(page);
  const countBefore = await getFilterCount(page);
  
  console.log(`Visible rows before: ${visibleBefore}`);
  console.log(`Rows in closed details before: ${closedBefore}`);
  console.log(`Counter before: ${countBefore}`);
  
  // Apply filter
  if (filterType === 'text') {
    const input = await page.$('#rf-q');
    await input.fill('');
    await input.type(filterValue, { delay: 50 });
    await page.waitForTimeout(500); // Wait for filter to apply
  } else if (filterType === 'area') {
    const btn = await page.$(`button[data-rf-area-btn="${filterValue}"]`);
    if (btn) {
      await btn.click();
      await page.waitForTimeout(500);
    }
  }
  
  // Screenshot after filter
  const afterPath = path.join(OUT_DIR, `after-${filterType}.png`);
  await page.screenshot({ path: afterPath, fullPage: true });
  
  const visibleAfter = await countVisibleRows(page);
  const closedAfter = await countRowsInClosedDetails(page);
  const countAfter = await getFilterCount(page);
  
  console.log(`Visible rows after: ${visibleAfter}`);
  console.log(`Rows in closed details after: ${closedAfter}`);
  console.log(`Counter after: ${countAfter}`);
  
  return {
    filter_type: filterType,
    filter_value: filterValue,
    visible_rows_before: visibleBefore,
    visible_rows_after: visibleAfter,
    rows_in_closed_details_before: closedBefore,
    rows_in_closed_details_after: closedAfter,
    counter_before: countBefore,
    counter_after: countAfter,
    screenshot_before: beforePath,
    screenshot_after: afterPath
  };
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  // Go to page
  await page.goto('https://divarioitalia.it/regione/molise', { waitUntil: 'networkidle' });
  
  // Inject proposta.css
  await page.addStyleTag({ content: PROPOSTA_CSS });
  
  // Inject trasforma.js (close all details)
  await page.addScriptTag({ content: TRASFORMA_JS });
  await page.waitForTimeout(300);
  
  // Verify details are closed
  const openDetails = await page.$$eval('details.regione-area[open]', els => els.length);
  console.log(`Open details after trasforma.js: ${openDetails}`);
  
  const results = [];
  
  // Test 1: Text filter - "occupazione"
  results.push(await runTest('text', 'occupazione', page));
  
  // Reset text filter
  await page.fill('#rf-q', '');
  await page.waitForTimeout(300);
  
  // Test 2: Text filter - "salute"
  results.push(await runTest('text', 'salute', page));
  
  // Reset text filter
  await page.fill('#rf-q', '');
  await page.waitForTimeout(300);
  
  // Test 3: Area filter - "economia-e-opportunita"
  results.push(await runTest('area', 'economia-e-opportunita', page));
  
  // Reset area filter (click "Tutte")
  await page.click('button[data-rf-area-btn=""]');
  await page.waitForTimeout(300);
  
  // Test 4: Area filter - "persone-e-conoscenza"
  results.push(await runTest('area', 'persone-e-conoscenza', page));
  
  // Reset
  await page.click('button[data-rf-area-btn=""]');
  await page.waitForTimeout(300);
  
  // Test 5: Area filter - "territorio-e-servizi"
  results.push(await runTest('area', 'territorio-e-servizi', page));
  
  // Reset
  await page.click('button[data-rf-area-btn=""]');
  await page.waitForTimeout(300);
  
  // Test 6: Area filter - "comunita-e-benessere"
  results.push(await runTest('area', 'comunita-e-benessere', page));
  
  await browser.close();
  
  // Output JSON
  console.log('\n=== RESULTS ===');
  console.log(JSON.stringify(results, null, 2));
  
  // Save to file
  fs.writeFileSync(path.join(OUT_DIR, 'results.json'), JSON.stringify(results, null, 2));
  console.log(`\nResults saved to ${OUT_DIR}/results.json`);
})();
