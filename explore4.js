const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('https://divarioitalia.it/regione/molise', { waitUntil: 'networkidle' });
  
  // Find select elements (area filter)
  const selects = await page.$$eval('select', els => els.map(el => ({
    id: el.id,
    name: el.name,
    className: el.className,
    options: Array.from(el.options).map(o => ({ value: o.value, text: o.textContent.trim() }))
  })));
  console.log('Selects:', JSON.stringify(selects, null, 2));
  
  // Check the toolbar structure
  const toolbar = await page.$('.toolbar.regione-filter');
  if (toolbar) {
    const html = await toolbar.evaluate(el => el.outerHTML);
    console.log('Toolbar HTML:', html.substring(0, 2000));
  }
  
  await browser.close();
})();
