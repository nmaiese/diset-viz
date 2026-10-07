const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ userAgent: 'DivarioCheck/1.0' });
  await page.route(/^https?:\/\/(?:[^/]+\.)?(?:googletagmanager|google-analytics|googlesyndication)\.com(?:[/:?#]|$)/i, route => route.abort());
  await page.goto('https://divarioitalia.it/regione/molise', { waitUntil: 'networkidle' });
  
  // Search for "Cerca un indicatore" text
  const elements = await page.$$eval('*', els => 
    els.filter(el => el.textContent && el.textContent.includes('Cerca un indicatore'))
      .map(el => ({
        tag: el.tagName,
        id: el.id,
        className: el.className,
        text: el.textContent.trim().substring(0, 100)
      }))
  );
  console.log('Elements with "Cerca un indicatore":', JSON.stringify(elements, null, 2));
  
  // Find all labels
  const labels = await page.$$eval('label', els => els.map(el => ({
    for: el.htmlFor,
    text: el.textContent.trim(),
    id: el.id
  })));
  console.log('Labels:', JSON.stringify(labels, null, 2));
  
  // Find input near "Cerca un indicatore"
  const inputsNear = await page.$$eval('input', els => els.map(el => ({
    id: el.id,
    type: el.type,
    placeholder: el.placeholder,
    name: el.name,
    className: el.className,
    ariaLabel: el.getAttribute('aria-label')
  })));
  console.log('All inputs:', JSON.stringify(inputsNear, null, 2));
  
  await browser.close();
})();
