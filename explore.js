const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ userAgent: 'DivarioCheck/1.0' });
  await page.route(/^https?:\/\/(?:[^/]+\.)?(?:(?:googletagmanager|google-analytics|googlesyndication)\.com|doubleclick\.net)(?:[/:?#]|$)/i, route => route.abort());
  await page.goto('https://divarioitalia.it/regione/molise', { waitUntil: 'networkidle' });
  
  // Find filter elements
  const filters = await page.$$eval('input, select', els => els.map(el => ({
    tag: el.tagName,
    type: el.type,
    id: el.id,
    name: el.name,
    placeholder: el.placeholder,
    className: el.className
  })));
  
  // Find table structure
  const tables = await page.$$eval('table', els => els.map(t => ({
    id: t.id,
    className: t.className,
    rows: t.querySelectorAll('tr').length
  })));
  
  // Find details elements
  const details = await page.$$eval('details', els => els.map(d => ({
    open: d.open,
    id: d.id,
    className: d.className,
    summary: d.querySelector('summary')?.textContent?.trim()
  })));
  
  console.log('FILTERS:', JSON.stringify(filters, null, 2));
  console.log('TABLES:', JSON.stringify(tables, null, 2));
  console.log('DETAILS:', JSON.stringify(details, null, 2));
  
  await browser.close();
})();
