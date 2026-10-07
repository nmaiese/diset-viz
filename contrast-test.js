const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT_DIR = '/tmp/opencode/ux-lettura/out';
const PROPOSTA_CSS = fs.readFileSync(path.join(OUT_DIR, 'proposta.css'), 'utf-8');
const TRASFORMA_JS = fs.readFileSync(path.join(OUT_DIR, 'trasforma.js'), 'utf-8');

const PAGES = {
  articolo: 'https://divarioitalia.it/blog/reddito-pro-capite-regioni-non-e-il-pil',
  regione: 'https://divarioitalia.it/regione/molise',
  scheda: 'https://divarioitalia.it/indicatore/addetti-delle-nuove-imprese-nei-settori-culturali-e-creativi/ter-600'
};

const VIEWPORT = { width: 1024, height: 768 };

// WCAG contrast calculation
function getLuminance(r, g, b) {
  const srgb = [r, g, b].map(v => {
    v /= 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * srgb[0] + 0.7152 * srgb[1] + 0.0722 * srgb[2];
}

function getContrastRatio(fg, bg) {
  const l1 = getLuminance(fg.r, fg.g, fg.b);
  const l2 = getLuminance(bg.r, bg.g, bg.b);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

function parseColor(colorStr) {
  if (!colorStr || colorStr === 'transparent' || colorStr === 'rgba(0, 0, 0, 0)') return null;
  const match = colorStr.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*[\d.]+)?\)/);
  if (match) return { r: parseInt(match[1]), g: parseInt(match[2]), b: parseInt(match[3]) };
  // hex
  const hexMatch = colorStr.match(/^#([0-9a-f]{3,6})$/i);
  if (hexMatch) {
    const hex = hexMatch[1];
    const full = hex.length === 3 ? hex.split('').map(c => c + c).join('') : hex;
    return {
      r: parseInt(full.substr(0, 2), 16),
      g: parseInt(full.substr(2, 2), 16),
      b: parseInt(full.substr(4, 2), 16)
    };
  }
  return null;
}

function getEffectiveBackground(element) {
  let current = element;
  while (current && current !== document.body) {
    const bg = window.getComputedStyle(current).backgroundColor;
    const parsed = parseColor(bg);
    if (parsed && !(parsed.r === 0 && parsed.g === 0 && parsed.b === 0 && bg.includes('0)'))) {
      return parsed;
    }
    current = current.parentElement;
  }
  // fallback to body
  const bodyBg = window.getComputedStyle(document.body).backgroundColor;
  return parseColor(bodyBg) || { r: 255, g: 255, b: 255 };
}

function isLargeText(element) {
  const style = window.getComputedStyle(element);
  const fontSize = parseFloat(style.fontSize);
  const fontWeight = style.fontWeight;
  const numericWeight = parseInt(fontWeight) || (fontWeight === 'bold' ? 700 : 400);
  return fontSize >= 24 || (fontSize >= 18.5 && numericWeight >= 700);
}

function getRequiredRatio(element) {
  return isLargeText(element) ? 3 : 4.5;
}

async function measureContrast(page, state) {
  return await page.evaluate(() => {
    const results = {
      textElements: [],
      linkElements: [],
      summary: { min: null, median: null, belowThreshold: 0, total: 0 },
      linkSummary: { min: null, median: null, belowThreshold: 0, total: 0 }
    };

    // Select text elements (prose, headings, etc.)
    const textSelectors = [
      'main p', 'main li', 'main h1', 'main h2', 'main h3', 'main h4',
      '.prose p', '.prose li', '.indicator-article p', '.indicator-article li',
      '.art-brief p', '.regione-intro', '.regione-stacca__lead',
      '.page-lead', '.answer p', '.art-body p', '.art-body li',
      '.lead-figure__head', '.stripbar__t', '.source', '.chart-note',
      '.meta', '.byline', '.art-hero__caption', '.art-hero__credit',
      '.regionmap__cap', '.legend', '.subline', '.aside-block__label',
      '.qlist a', '.toc a', '.card__title', '.card__text', '.card__meta',
      '.minicard__title', '.minicard__meta', '.card__kicker',
      '.answer', '.answer p', 'figcaption', 'th', 'td', 'caption',
      'button', 'label', 'input', 'select', 'summary', '.qz-badge',
      '.status', '.n--nd', '.gi-verdict', '.gi-daily__text',
      '.gi-daily__kicker', '.gi-daily__title', '.gi-daily__meta'
    ];

    const elements = document.querySelectorAll(textSelectors.join(', '));
    
    const ratios = [];
    
    elements.forEach(el => {
      // Skip hidden elements
      if (!el.getClientRects().length) return;
      if (el.closest('svg')) return;
      if (['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(el.tagName)) return;
      
      // Check if element has direct text content
      let hasText = false;
      for (const node of el.childNodes) {
        if (node.nodeType === Node.TEXT_NODE && node.nodeValue.trim()) {
          hasText = true;
          break;
        }
      }
      if (!hasText && !['H1', 'H2', 'H3', 'H4', 'BUTTON', 'LABEL', 'INPUT', 'SELECT', 'SUMMARY'].includes(el.tagName)) {
        // Check if it's a link with text
        if (el.tagName !== 'A' || !el.textContent.trim()) return;
      }
      
      const style = window.getComputedStyle(el);
      const fgColor = parseColor(style.color);
      if (!fgColor) return;
      
      const bgColor = getEffectiveBackground(el);
      if (!bgColor) return;
      
      const ratio = getContrastRatio(fgColor, bgColor);
      const required = getRequiredRatio(el);
      const passed = ratio >= required;
      
      ratios.push(ratio);
      
      results.textElements.push({
        selector: getSelector(el),
        tag: el.tagName.toLowerCase(),
        class: el.className || '',
        text: el.textContent.trim().substring(0, 100),
        fontSize: parseFloat(style.fontSize),
        fontWeight: style.fontWeight,
        isLargeText: isLargeText(el),
        fgColor: `rgb(${fgColor.r},${fgColor.g},${fgColor.b})`,
        bgColor: `rgb(${bgColor.r},${bgColor.g},${bgColor.b})`,
        ratio: Math.round(ratio * 100) / 100,
        required,
        passed
      });
      
      if (!passed) results.summary.belowThreshold++;
    });
    
    // Calculate summary for text
    if (ratios.length > 0) {
      const sorted = [...ratios].sort((a, b) => a - b);
      results.summary.min = Math.round(sorted[0] * 100) / 100;
      const mid = Math.floor(sorted.length / 2);
      results.summary.median = sorted.length % 2 === 0 
        ? Math.round(((sorted[mid - 1] + sorted[mid]) / 2) * 100) / 100
        : Math.round(sorted[mid] * 100) / 100;
      results.summary.total = ratios.length;
    }
    
    // Links in text - contrast vs surrounding text
    const textLinks = document.querySelectorAll('.prose a, .indicator-article a, .art-body a, .art-brief a, .answer a, .regione-stacca__lead a, .text-link');
    const linkRatios = [];
    
    textLinks.forEach(link => {
      if (!link.getClientRects().length) return;
      if (link.closest('svg')) return;
      
      const linkStyle = window.getComputedStyle(link);
      const linkFg = parseColor(linkStyle.color);
      if (!linkFg) return;
      
      // Find surrounding text element (parent or sibling)
      let surroundingEl = link.parentElement;
      while (surroundingEl && surroundingEl !== document.body) {
        const style = window.getComputedStyle(surroundingEl);
        const surroundingFg = parseColor(style.color);
        if (surroundingFg && surroundingEl.textContent.trim().length > link.textContent.trim().length) {
          const ratio = getContrastRatio(linkFg, surroundingFg);
          linkRatios.push(ratio);
          
          results.linkElements.push({
            selector: getSelector(link),
            linkText: link.textContent.trim().substring(0, 100),
            surroundingSelector: getSelector(surroundingEl),
            surroundingText: surroundingEl.textContent.trim().substring(0, 100),
            linkColor: `rgb(${linkFg.r},${linkFg.g},${linkFg.b})`,
            surroundingColor: `rgb(${surroundingFg.r},${surroundingFg.g},${surroundingFg.b})`,
            ratio: Math.round(ratio * 100) / 100,
            required: 3,
            passed: ratio >= 3
          });
          
          if (ratio < 3) results.linkSummary.belowThreshold++;
          break;
        }
        surroundingEl = surroundingEl.parentElement;
      }
    });
    
    if (linkRatios.length > 0) {
      const sorted = [...linkRatios].sort((a, b) => a - b);
      results.linkSummary.min = Math.round(sorted[0] * 100) / 100;
      const mid = Math.floor(sorted.length / 2);
      results.linkSummary.median = sorted.length % 2 === 0
        ? Math.round(((sorted[mid - 1] + sorted[mid]) / 2) * 100) / 100
        : Math.round(sorted[mid] * 100) / 100;
      results.linkSummary.total = linkRatios.length;
    }
    
    return results;
    
    function getSelector(el) {
      if (el.id) return '#' + el.id;
      let path = el.tagName.toLowerCase();
      if (el.className) {
        const classes = el.className.split(' ').filter(c => c).slice(0, 3).join('.');
        if (classes) path += '.' + classes;
      }
      return path;
    }
    
    function parseColor(colorStr) {
      if (!colorStr || colorStr === 'transparent' || colorStr === 'rgba(0, 0, 0, 0)') return null;
      const match = colorStr.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*[\d.]+)?\)/);
      if (match) return { r: parseInt(match[1]), g: parseInt(match[2]), b: parseInt(match[3]) };
      const hexMatch = colorStr.match(/^#([0-9a-f]{3,6})$/i);
      if (hexMatch) {
        const hex = hexMatch[1];
        const full = hex.length === 3 ? hex.split('').map(c => c + c).join('') : hex;
        return { r: parseInt(full.substr(0, 2), 16), g: parseInt(full.substr(2, 2), 16), b: parseInt(full.substr(4, 2), 16) };
      }
      return null;
    }
    
    function getLuminance(r, g, b) {
      const srgb = [r, g, b].map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
      return 0.2126 * srgb[0] + 0.7152 * srgb[1] + 0.0722 * srgb[2];
    }
    
    function getContrastRatio(fg, bg) {
      const l1 = getLuminance(fg.r, fg.g, fg.b);
      const l2 = getLuminance(bg.r, bg.g, bg.b);
      const lighter = Math.max(l1, l2);
      const darker = Math.min(l1, l2);
      return (lighter + 0.05) / (darker + 0.05);
    }
    
    function isLargeText(element) {
      const style = window.getComputedStyle(element);
      const fontSize = parseFloat(style.fontSize);
      const fontWeight = style.fontWeight;
      const numericWeight = parseInt(fontWeight) || (fontWeight === 'bold' ? 700 : 400);
      return fontSize >= 24 || (fontSize >= 18.5 && numericWeight >= 700);
    }
    
    function getRequiredRatio(element) {
      return isLargeText(element) ? 3 : 4.5;
    }
    
    function getEffectiveBackground(element) {
      let current = element;
      while (current && current !== document.body) {
        const bg = window.getComputedStyle(current).backgroundColor;
        const parsed = parseColor(bg);
        if (parsed && !(parsed.r === 0 && parsed.g === 0 && parsed.b === 0 && bg.includes('0)'))) {
          return parsed;
        }
        current = current.parentElement;
      }
      const bodyBg = window.getComputedStyle(document.body).backgroundColor;
      return parseColor(bodyBg) || { r: 255, g: 255, b: 255 };
    }
  });
}

async function closeConsentBanner(page) {
  await page.evaluate(() => {
    const b = document.querySelector('#iubenda-cs-banner, .iubenda-cs-container');
    const btn = document.querySelector('.iubenda-cs-accept-btn, .iubenda-cs-reject-btn, #iubenda-cs-banner button');
    if (btn) btn.click();
    document.querySelectorAll('#iubenda-cs-banner, .iubenda-cs-overlay').forEach(x => x.remove());
  });
  await page.waitForTimeout(300);
}

async function setDarkTheme(page) {
  await page.evaluate(() => {
    document.documentElement.setAttribute('data-theme', 'dark');
  });
  await page.waitForTimeout(300);
}

async function runTest(page, pageName, url) {
  console.log(`Testing ${pageName}...`);
  
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  await closeConsentBanner(page);
  await setDarkTheme(page);
  await page.waitForTimeout(500);
  
  // Measure BEFORE
  const before = await measureContrast(page, 'before');
  
  // Apply proposta.css
  await page.addStyleTag({ content: PROPOSTA_CSS });
  await page.waitForTimeout(300);
  
  // Apply trasforma.js
  await page.addScriptTag({ content: TRASFORMA_JS });
  await page.waitForTimeout(500);
  
  // Measure AFTER
  const after = await measureContrast(page, 'after');
  
  return { page: pageName, url, before, after };
}

(async () => {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: VIEWPORT,
    colorScheme: 'dark',
    userAgent: 'DivarioCheck/1.0'
  });
  await context.route(/^https?:\/\/(?:[^/]+\.)?(?:(?:googletagmanager|google-analytics|googlesyndication)\.com|doubleclick\.net)(?:[/:?#]|$)/i, route => route.abort());
  
  const results = {};
  
  try {
    for (const [pageName, url] of Object.entries(PAGES)) {
      const page = await context.newPage();
      try {
        results[pageName] = await runTest(page, pageName, url);
        console.log(`  ${pageName}: before ${results[pageName].before.summary.belowThreshold}/${results[pageName].before.summary.total} below, after ${results[pageName].after.summary.belowThreshold}/${results[pageName].after.summary.total} below`);
      } catch (e) {
        console.error(`Error testing ${pageName}:`, e);
        results[pageName] = { page: pageName, url, error: e.message };
      } finally {
        await page.close();
      }
    }
  } finally {
    await browser.close();
  }
  
  // Write output
  const outputPath = path.join(OUT_DIR, 'contrast.json');
  fs.writeFileSync(outputPath, JSON.stringify(results, null, 2));
  console.log(`\nResults written to ${outputPath}`);
  
  // Print summary
  console.log('\n=== SUMMARY ===');
  for (const [pageName, data] of Object.entries(results)) {
    if (data.error) {
      console.log(`${pageName}: ERROR - ${data.error}`);
      continue;
    }
    console.log(`\n${pageName.toUpperCase()}:`);
    console.log(`  Text elements: ${data.before.summary.total} -> ${data.after.summary.total}`);
    console.log(`  Below threshold: ${data.before.summary.belowThreshold} -> ${data.after.summary.belowThreshold}`);
    console.log(`  Min ratio: ${data.before.summary.min} -> ${data.after.summary.min}`);
    console.log(`  Median ratio: ${data.before.summary.median} -> ${data.after.summary.median}`);
    console.log(`  Links below 3:1: ${data.before.linkSummary.belowThreshold}/${data.before.linkSummary.total} -> ${data.after.linkSummary.belowThreshold}/${data.after.linkSummary.total}`);
  }
})();
