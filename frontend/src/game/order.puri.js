// Le funzioni pure di "Ordina le regioni" (order.jsx): niente React, niente DOM,
// nessuna rete, cosi' `node --test` le prova come sono (`order.puri.test.mjs`),
// senza dover montare il gioco.
//
// Due regole del progetto vivono qui dentro, perche' sono il posto dove si
// possono far fallire un test invece di accorgersi a occhio:
// 1. un numero che non c'e' non si stampa MAI. `formatValue` di `shared.jsx`
//    (la funzione degli altri giochi, che non e' di questo file) con un valore
//    assente restituisce "n.d.": nell'esito finiva "Saldo migratorio: n.d.".
//    Qui un valore assente dà la stringa vuota e la riga mostra il solo nome.
// 2. il link a un territorio esce sempre dalla chiave del payload, mai dal
//    nome: "Valle d'Aosta" dava `/regione/valle-d'aosta`, che non esiste
//    (la chiave e' `valle-d-aosta`).

// I decimali li decide la grandezza, come `magnitude_decimals` in
// `app/design/numfmt.py`: lo zero non ha decimali ("0", non "0,00") e sotto i
// cento la precisione si vede, finche' la cifra non e' piu' uno zero che scrive.
export function decimaliPerGrandezza(value) {
  const m = Math.abs(value);
  if (m === 0 || m >= 100) return 0;
  if (m >= 1) return 1;
  if (m >= 0.01) return 2;
  return m >= 0.001 ? 3 : 4;
}

// La cifra all'italiana: il punto di migliaia e la virgola dei decimali li
// scrive qui, e non `Intl.NumberFormat`/`toLocaleString("it-IT")`: su Node con
// ICU ridotta quelle funzioni raggruppano con la virgola ("1234,6") e il numero
// stampato cambia da browser a browser e da macchina a macchina. Una funzione
// che il test verifica a mano deve dare lo stesso numero partout, quindi il
// formato e' qui dentro.
//
// I decimali sono fissi, come in `fmt` di `app/static/js/v1.js` e in
// `it_numbers.number`: `minimumFractionDigits` e `maximumFractionDigits` sono
// gli stessi, quindi 74 si scrive "74,0" e 1234,56 si scrive "1.235".
export function numeroIt(value, decimali = decimaliPerGrandezza(value)) {
  const [intero, decimaliTesto = ""] = value.toFixed(Math.max(0, Math.min(20, decimali))).split(".");
  const conPunti = intero.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return decimaliTesto ? `${conPunti},${decimaliTesto}` : conPunti;
}

// Le etichette che dicono che cosa si conta ma non sono un'unita' da scrivere
// accanto alla cifra: "29,0 numero" e "7,0 Valore medio" si leggono male. Le stesse
// di `phrase_unit` in `app/design/numfmt.py`, cosi' il numero di Ordina e quello
// delle pagine si scrivono uguale.
const UNITA_GENERICHE = new Set([
  "numero", "numero medio", "valore medio", "indice", "indice (0-1)", "rapporto", "classi",
]);
const PUNTI_PERCENTUALI = /punti\s+percentual/i;
const PERCENTUALE = /percentual|%/i;
// "228 centomila anziani" si legge come ventidue milioni: il tasso va detto.
const BASE_CENTO = /^(cento|mille|diecimila|centomila|un milione di)\s/i;

// Il valore con la sua unita'. Un valore assente (null, undefined, NaN,
// infinito, una stringa) non e' un numero: si stampa il vuoto, mai "n.d." e
// mai un numero inventato. L'unita' segue `phrase_unit` del lato Python: ogni
// percentuale della fonte diventa "%", i punti percentuali restano per intero,
// un'etichetta generica non viene scritta accanto alla cifra.
export function valoreConUnita(value, unit) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "";
  const testo = numeroIt(value);
  const unita = typeof unit === "string" ? unit.trim() : "";
  if (!unita || UNITA_GENERICHE.has(unita.toLowerCase())) return testo;
  if (PUNTI_PERCENTUALI.test(unita)) return `${testo} punti percentuali`;
  if (PERCENTUALE.test(unita)) return `${testo}%`;
  if (BASE_CENTO.test(unita)) return `${testo} ogni ${unita}`;
  return `${testo} ${unita}`;
}

// Il nome del territorio, come lo chiama il payload (le province hanno `name`,
// i round a serie hanno `region`).
export function nomeTerritorio(territorio) {
  if (!territorio || typeof territorio !== "object") return "";
  const nome = territorio.name || territorio.region;
  return typeof nome === "string" ? nome : "";
}

// Il link alla scheda del territorio: la chiave, che il server garantisce, e
// mai uno slug ricavato dal nome. Senza chiave non c'e' link (null): un link
// costruito a metà è un 404, e un 404 è peggio di nessun link.
export function percorsoTerritorio(territorio) {
  if (!territorio || typeof territorio !== "object") return null;
  const chiave = territorio.key || territorio.region_key;
  if (typeof chiave !== "string" || !chiave) return null;
  const provincia = territorio.region && territorio.name && territorio.name !== territorio.region;
  return provincia ? `/provincia/${chiave}` : `/regione/${chiave}`;
}

// L'ordine giosto, una riga per territorio, con quello che il giocatore aveva
// risposto. `correct_order` porta il valore e la posizione vera, `positions`
// quello che è stato messo dove: si uniscono per chiave e si ordinano per
// posizione vera, che è l'ordine da mostrare.
//
// Il valore e l'unita' si prendono da `correct_order` e, se lì mancano, da
// `positions`: il payload della sfida del giorno porta l'unita' su entrambe le
// liste, ma un round del passato può non averla e la riga resta leggibile con
// l'unita' dell'indicatore (`unita`).
export function righeEsito(positions, correctOrder, unitaIndicatore = "") {
  const perChiave = new Map();
  for (const posizione of Array.isArray(positions) ? positions : []) {
    if (posizione && typeof posizione === "object" && posizione.region_key) {
      perChiave.set(posizione.region_key, posizione);
    }
  }
  const ordine = Array.isArray(correctOrder) ? correctOrder : [];
  const righe = [];
  for (let indice = 0; indice < ordine.length; indice += 1) {
    const riga = ordine[indice];
    if (!riga || typeof riga !== "object") continue;
    const chiave = riga.region_key;
    if (!chiave) continue;
    const risposta = perChiave.get(chiave) || null;
    const posizione = Number.isInteger(riga.correct_position) ? riga.correct_position : indice + 1;
    const tua = risposta && Number.isInteger(risposta.guessed_position) ? risposta.guessed_position : null;
    const valore = typeof riga.value === "number" ? riga.value
      : risposta && typeof risposta.value === "number" ? risposta.value : null;
    const unita = riga.unit || (risposta && risposta.unit) || unitaIndicatore || "";
    righe.push({
      posizione,
      chiave,
      nome: nomeTerritorio(riga) || (risposta ? nomeTerritorio(risposta) : ""),
      valore,
      unita,
      tua,
      esatta: tua === posizione,
    });
  }
  if (righe.length === 0) {
    // Senza `correct_order` (un payload vecchio) le righe sono quelle del
    // giocatore, nell'ordine in cui le ha date, senza riordinarle: la posizione
    // vera non c'e' da nessuna parte e riordinare qui mostrerebbe un ordine che
    // nessuno ha detto.
    for (const risposta of Array.isArray(positions) ? positions : []) {
      if (!risposta || !risposta.region_key) continue;
      const indice = righe.length;
      righe.push({
        posizione: indice + 1,
        chiave: risposta.region_key,
        nome: nomeTerritorio(risposta),
        valore: typeof risposta.value === "number" ? risposta.value : null,
        unita: risposta.unit || unitaIndicatore || "",
        tua: Number.isInteger(risposta.guessed_position) ? risposta.guessed_position : null,
        esatta: risposta.correct === true,
      });
    }
    return righe;
  }
  return righe.sort((a, b) => a.posizione - b.posizione);
}

// Il segno di una riga dell'esito: un glifo per lo schermo e una frase per chi
// legge con un lettore di schermo. Mai il solo colore, mai una croce per un
// risultato parziale: qui la croce c'è solo sulla posizione sbagliata.
export function segnoPosizione(riga) {
  if (!riga || riga.esatta) {
    return { glifo: "✓", testo: "nella posizione giusta", esatta: true };
  }
  const tua = Number.isInteger(riga && riga.tua) ? riga.tua : null;
  const giusta = Number.isInteger(riga && riga.posizione) ? riga.posizione : null;
  const testo = tua !== null && giusta !== null
    ? `eri alla ${tua}, era la ${giusta}`
    : "non era la posizione giusta";
  return { glifo: "✗", testo, esatta: false };
}

// Il tono della fine partita: pieno solo se tutte le posizioni sono giuste,
// nullo se nessuna, parziale in mezzo. Un parziale non è una croce.
export function tonoDaPunteggio(score, total) {
  const punti = Number.isFinite(score) ? score : 0;
  const max = Number.isFinite(total) ? total : 0;
  if (max <= 0 || punti >= max) return "pieno";
  if (punti <= 0) return "nullo";
  return "parziale";
}

// Le parti di una riga di metadati (tema, area, unita', anno) in una riga sola,
// senza spaziatori vuoti: un separatore senza testo accanto e' rumore.
export function metaUnita(parts) {
  return (Array.isArray(parts) ? parts : [])
    .map((parte) => (typeof parte === "string" ? parte.trim() : ""))
    .filter(Boolean)
    .join(" · ");
}

// Invio e Spazio attivano la RIGA solo se il tasto nasce sulla riga. Sui bottoni
// freccia (figli della riga) il keydown risale fino a lei: se la riga lo
// intercettasse con preventDefault, il bottone non scatterebbe mai da tastiera.
export function tastoPerLaRiga(key, target, currentTarget) {
  return target === currentTarget && (key === "Enter" || key === " ");
}
