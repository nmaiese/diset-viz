const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ userAgent: 'DivarioCheck/1.0' });
  await page.route(/^https?:\/\/(?:[^/]+\.)?(?:(?:googletagmanager|google-analytics|googlesyndication)\.com|doubleclick\.net)(?:[/:?#]|$)/i, route => route.abort());
  await page.goto('https://divarioitalia.it/regione/molise', { waitUntil: 'networkidle' });
  
  // Find the filter "Cerca un indicatore" 
  const rfq = await page.$('#rf-q');
  console.log('rf-q element:', !!rfq);
  
  if (rfq) {
    const placeholder = await rfq.getAttribute('placeholder');
    console.log('rf-q placeholder:', placeholder);
  }
  
  // Find all tables inside open details.regione-area
  const openDetails = await page.$$('.regione-area[open]');
  console.log('Open regione-area details:', openDetails.length);
  
  for (let i = 0; i < openDetails.length; i++) {
    const summary = await openDetails[i].$('summary');
    const summaryText = summary ? await summary.textContent() : 'no summary';
    const table = await openDetails[i].$('table');
    const rows = table ? await table.$$eval('tbody tr', trs => trs.length) : 0;
    console.log(`  Detail ${i}: "${summaryText.trim()}" - table rows: ${rows}`);
  }
  
  // Check for proposta.css and trasforma.js
  const stylesheets = await page.$$eval('link[rel="stylesheet"]', els => els.map(el => el.href));
  console.log('Stylesheets:', stylesheets);
  
  const scripts = await page.$$eval('script[src]', els => els.map(el => el.src));
  console.log('Scripts:', scripts);
  
  await browser.close();
})();
