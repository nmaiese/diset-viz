# Dove carica AdSense

Lo script AdSense è un solo tag, il loader in `app/templates/_third_party_head.html`
(`pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={{ ADSENSE_CLIENT }}`).
Non ci sono unità `<ins class="adsbygoogle">`: la macro `ui.ad()` è vuota.

Il loader compare solo quando sono vere tutte e tre le condizioni:

1. `ADSENSE_CLIENT` è configurato (`ca-pub-6806451730012282`, da `config.py`);
2. `ADS_OFF` è falso (`app/__init__.py`, `ADS_OFF_ENDPOINTS`);
3. `noindex` è falso nel contesto del template.

Quindi gli annunci non caricano su: ricerca, account, classifica del quiz (via
`ADS_OFF_ENDPOINTS`); le pagine del gioco sotto `/quiz` (via `_NOINDEX_FOLLOW_PATHS`);
le varianti `?profilo=` della classifica qualità della vita (via `noindex` dalla
view); le schede indicatore servite `noindex`.

Caricano invece sulle pagine indicizzabili con testo editoriale: home, atlante,
schede indicatore, regioni, province, temi, qualità della vita (le basi), blog e
pagine legali.

## La regola per le unità, quando arriveranno

Oggi non ci sono unità `<ins class="adsbygoogle">`: la macro `ui.ad()` è vuota.
Quando se ne aggiungerà una, il posto per decidere se mostrarla è
`app.ads_policy.ads_allowed(page, word_count=None)`, una funzione sola e non una
condizione sparsa nei template.

- **vera** solo per gli articoli del blog (`page` = `blog`) e per le pagine con
  almeno `MIN_WORDS` (500) parole di testo editoriale;
- **falsa** per le interfacce (`atlas`, `search`, `game`, `account`, `legacy`,
  `error`: atlante, confronto, ricerca, quiz) e per le pagine sotto soglia;
- **falsa** quando il numero di parole non si conosce, per non rischiare.

`page` è il `page_type` di `app/page_types.py`; `word_count` va calcolato dal
testo editoriale della pagina (la prosa, non le tabelle né la testata). La
prova sta in `tests/unit/test_ads_policy.py`.
