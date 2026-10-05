// trasforma.js - trasformazioni DOM per test UX lettura

(function () {
  const results = {
    closedDetails: 0,
    openedDetails: 0,
    addedClasses: [],
    modifiedElements: 0
  };

  // 1. Chiudi tutti i <details> che sono tabelle espandibili
  document.querySelectorAll('details.regione-area, details.more, details[data-rf-area]').forEach(d => {
    if (d.open) {
      d.removeAttribute('open');
      results.closedDetails++;
    }
  });

  // 2. Apri i <details> che contengono contenuto essenziale (toc, aside-block)
  document.querySelectorAll('details.toc, details.aside-block').forEach(d => {
    if (!d.open) {
      d.setAttribute('open', '');
      results.openedDetails++;
    }
  });

  // 3. Aggiungi classi per identificare elementi trasformati
  document.querySelectorAll('main p, main li, main h1, main h2, main h3, main .answer, main .prose p, main .prose li, .indicator-article p, .indicator-article li, .art-brief p, .regione-intro, .regione-stacca__lead').forEach(el => {
    if (!el.classList.contains('prosa-text')) {
      el.classList.add('prosa-text');
      results.addedClasses.push('prosa-text');
      results.modifiedElements++;
    }
  });

  // 4. Identifica link nel testo (non navigazione)
  document.querySelectorAll('.prose a, .indicator-article a, .art-body a, .art-brief a, .answer a, .regione-stacca__lead a').forEach(el => {
    if (!el.classList.contains('text-link')) {
      el.classList.add('text-link');
      results.addedClasses.push('text-link');
      results.modifiedElements++;
    }
  });

  // 5. Identifica heading
  document.querySelectorAll('main h1, main h2, main h3, .h-display, .h-title, .h-section, .h-sub, .pagehead h1, .pagehead h2').forEach(el => {
    if (!el.classList.contains('page-heading')) {
      el.classList.add('page-heading');
      results.addedClasses.push('page-heading');
      results.modifiedElements++;
    }
  });

  // 6. Chiudi stripbar se presente (duplica la striscia)
  document.querySelectorAll('.stripbar').forEach(el => {
    el.hidden = true;
    results.modifiedElements++;
  });

  // 7. Rimuovi elementi decorativi che non portano contenuto
  document.querySelectorAll('.gi-proto-note, .gi-ph, .achv-card.is-locked').forEach(el => {
    el.hidden = true;
    results.modifiedElements++;
  });

  return results;
})();