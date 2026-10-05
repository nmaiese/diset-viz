const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT_DIR = '/tmp/opencode/ux-lettura/out';
fs.mkdirSync(OUT_DIR, { recursive: true });

const PROPOSTA_CSS = `table { width: 100%; border-collapse: collapse; } table td, table th { padding: 8px; border: 1px solid #ddd; } details { margin-bottom: 1rem; } details[open] summary::before { content: "▼ "; } details:not([open]) summary::before { content: "▶ "; }`;

const TRASFORMA_JS = `(function() { document.querySelectorAll('details.regione-area').forEach(d => d.removeAttribute('open')); })();`;

async function getState(page) {
  return await page.evaluate(() => {
    const openDetails = document.querySelectorAll('details.regione-area[open]');
    const closedDetails = document.querySelectorAll('details.regione-area:not([open])');
    
    let visibleRows = 0;
    let hiddenRows = 0;
    let totalRows = 0;
    
    openDetails.forEach(d => {
      const table = d.querySelector('table');
      if (table) {
        const rows = table.querySelectorAll('tbody tr');
        visibleRows += rows.length;
        totalRows += rows.length;
      }
    });
    
    closedDetails.forEach(d => {
      const table = d.querySelector('table');
      if (table) {
        const rows = table.querySelectorAll('tbody tr');
        hiddenRows += rows.length;
        totalRows += rows.length;
      }
    });
    
    // Check for rows with display:none or hidden attribute
    let actuallyVisible = 0;
    let actuallyHidden = 0;
    document.querySelectorAll('details.regione-area table tbody tr').forEach(tr => {
      const style = window.getComputedStyle(tr);
      const isHidden = tr.hasAttribute('hidden') || style.display === 'none' || style.visibility === 'hidden';
      if (isHidden) actuallyHidden++;
      else actuallyVisible++;
    });
    
    const counter = document.querySelector('.n--count');
    const counterValue = counter ? parseInt(counter.getAttribute('value')) || 0 : 0;
    
    return {
      openDetails: openDetails.length,
      closedDetails: closedDetails.length,
      visibleRows,
      hiddenRows,
      totalRows,
      actuallyVisible,
      actuallyHidden,
      counterValue
    };
  });
}

async function resetToClosed(page) {
  await page.evaluate(() => {
    document.querySelectorAll('details.regione-area').forEach(d => d.removeAttribute('open'));
  });
  await page.fill('#rf-q', '');
  // Click "Tutte" button
  const tutteBtn = await page.$('button[data-rf-area-btn=""]');
  if (tutteBtn) await tutteBtn.click();
  await page.waitForTimeout(300);
}

async function runTest(name, filterType, filterValue, page) {
  console.log(`\n=== ${name} ===`);
  
  await resetToClosed(page);
  await page.waitForTimeout(200);
  
  const before = await getState(page);
  console.log('Before:', before);
  
  const beforePath = path.join(OUT_DIR, `before-${name}.png`);
  await page.screenshot({ path: beforePath, fullPage: true });
  
  // Apply filter
  if (filterType === 'text') {
    await page.fill('#rf-q', '');
    await page.type('#rf-q', filterValue, { delay: 30 });
    await page.waitForTimeout(500);
  } else if (filterType === 'area') {
    const btn = await page.$(`button[data-rf-area-btn="${filterValue}"]`);
    if (btn) {
      await btn.click();
      await page.waitForTimeout(500);
    }
  }
  
  const after = await getState(page);
  console.log('After:', after);
  
  const afterPath = path.join(OUT_DIR, `after-${name}.png`);
  await page.screenshot({ path: afterPath, fullPage: true });
  
  return {
    filter_type: filterType,
    filter_value: filterValue,
    visible_rows_before: before.visibleRows,
    visible_rows_after: after.visibleRows,
    rows_in_closed_details_before: before.hiddenRows,
    rows_in_closed_details_after: after.hiddenRows,
    actually_visible_before: before.actuallyVisible,
    actually_visible_after: after.actuallyVisible,
    actually_hidden_before: before.actuallyHidden,
    actually_hidden_after: after.actuallyHidden,
    counter_before: before.counterValue,
    counter_after: after.counterValue,
    open_details_before: before.openDetails,
    open_details_after: after.openDetails,
    screenshot_before: beforePath,
    screenshot_after: afterPath
  };
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  await page.goto('https://divarioitalia.it/regione/molise', { waitUntil: 'networkidle' });
  await page.addStyleTag({ content: PROPOSTA_CSS });
  await page.addScriptTag({ content: TRASFORMA_JS });
  await page.waitForTimeout(300);
  
  const results = [];
  
  // Test text filters
  results.push(await runTest('text-occupazione', 'text', 'occupazione', page));
  results.push(await runTest('text-salute', 'text', 'salute', page));
  results.push(await runTest('text-ambiente', 'text', 'ambiente', page));
  results.push(await runTest('text-reddito', 'text', 'reddito', page));
  
  // Test area filters
  results.push(await runTest('area-economia', 'area', 'economia-e-opportunita', page));
  results.push(await runTest('area-persone', 'area', 'persone-e-conoscenza', page));
  results.push(await runTest('area-territorio', 'area', 'territorio-e-servizi', page));
  results.push(await runTest('area-comunita', 'area', 'comunita-e-benessere', page));
  
  await browser.close();
  
  console.log('\n=== RESULTS ===');
  console.log(JSON.stringify(results, null, 2));
  
  fs.writeFileSync(path.join(OUT_DIR, 'results.json'), JSON.stringify(results, null, 2));
  console.log(`\nResults saved to ${OUT_DIR}/results.json`);
})();
