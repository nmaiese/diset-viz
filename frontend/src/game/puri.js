// Le funzioni pure dei contratti condivisi del gioco. Niente React, niente DOM, niente
// rete: sono qui, e non in `shared.jsx`, perche' `node --test` le importa cosi' come sono
// (`puri.test.mjs`). `shared.jsx` le riesporta: i giochi importano da li'.

// -- Gli eventi ---------------------------------------------------------------

// Il parametro `game` di ogni evento del gioco (vedi docs/tracking_spec.md).
export const GIOCHI_EVENTO = ["regione", "provincia", "compare", "order", "mappa"];

// I parametri da mandare con un evento: `game` deve essere uno dei cinque, altrimenti
// si toglie (un valore inventato sporcherebbe ogni rapporto) e `valido` dice che non
// c'era. L'evento parte comunque: una misura incompleta vale piu' di una misura persa.
export function parametriEvento(params) {
  const { game, ...resto } = params && typeof params === "object" ? params : {};
  if (GIOCHI_EVENTO.includes(game)) return { valido: true, params: { ...resto, game } };
  return { valido: false, params: resto };
}

// -- Il conteggio di fine partita -----------------------------------------------

export const DURATA_CONTEGGIO_MS = 450;

// Il valore da mostrare dopo `trascorso` ms: da 0 a `finale` con ease-out cubico. Alla
// fine (o oltre) e' esattamente `finale`, mai un arrotondamento vicino. Un `finale` che
// non e' un numero finito si restituisce com'e': non c'e' niente da contare.
export function countUpValue(finale, trascorso, durata = DURATA_CONTEGGIO_MS) {
  if (!Number.isFinite(finale)) return finale;
  if (!(durata > 0) || trascorso >= durata) return finale;
  if (!(trascorso > 0)) return 0;
  const k = trascorso / durata;
  const ease = 1 - Math.pow(1 - k, 3);
  return Math.round(finale * ease);
}

// Dal titolo "7 su 10 posizioni corrette" ricava le parti attorno al numero che conta:
// `{ prima, valore, dopo }`. Solo il primo "N su M": un titolo senza numero non si conta.
export function titoloContabile(titolo) {
  const trovato = /^(.*?)(\d{1,4})(\s+su\s+\d{1,4}.*)$/s.exec(String(titolo || ""));
  if (!trovato) return null;
  return { prima: trovato[1], valore: Number(trovato[2]), dopo: trovato[3] };
}

// -- Il tono della fine partita -------------------------------------------------

export const TONI = ["pieno", "parziale", "nullo"];

export function tonoFinale(won, tono) {
  return TONI.includes(tono) ? tono : won ? "pieno" : "nullo";
}

// -- La sfida condivisa -----------------------------------------------------------

// Il punteggio massimo di ogni gioco a punteggio: serve a `leggiSfida` per scartare un
// frammento fuori scala. Il valore e' il massimo della sfida del giorno (le dieci coppie di
// Chi e' maggiore?, i cinque territori di Ordina, i venti punti della mappa a due punti per
// domanda). Senza un massimo nessun frammento e' valido (meglio nessuna sfida che una sfida
// fuori scala).
export const MASSIMI_SFIDA = { compare: 10, order: 5, mappa: 20 };

const FRAMMENTO_SFIDA = /^#sfida=(0|[1-9]\d{0,2})-([1-9]\d{0,5})$/;

// Valida il frammento `#sfida=<punteggio>-<numero>` e ritorna `{ punteggio, numero }`, o
// `null` se una sola regola non e' soddisfatta: un solo frammento e nient'altro, solo cifre
// ASCII senza zeri davanti, punteggio fra 0 e `massimo`, numero uguale a `numeroOggi`
// (quello che dice il server, non la data del browser). Il punteggio non e' firmato: chi
// lo legge non puo' fidarsi di chi l'ha scritto, per questo il testo non e' attributivo.
export function leggiSfida(hash, { massimo, numeroOggi } = {}) {
  if (typeof hash !== "string") return null;
  const trovato = FRAMMENTO_SFIDA.exec(hash);
  if (!trovato) return null;
  if (!Number.isInteger(massimo) || massimo <= 0) return null;
  const oggi = typeof numeroOggi === "string" && /^[1-9]\d{0,5}$/.test(numeroOggi) ? Number(numeroOggi) : numeroOggi;
  if (!Number.isInteger(oggi)) return null;
  const punteggio = Number(trovato[1]);
  const numero = Number(trovato[2]);
  if (punteggio > massimo || numero !== oggi) return null;
  return { punteggio, numero };
}

// Il link di chi condivide: l'indirizzo senza il frammento che c'era, piu' il nuovo. Con un
// punteggio o un numero che non sono cifre sensate si da' il link pulito.
export function linkConSfida(url, punteggio, numero) {
  const base = String(url || "").split("#")[0];
  if (!Number.isInteger(punteggio) || punteggio < 0 || punteggio > 999) return base;
  if (!Number.isInteger(numero) || numero < 1 || numero > 999999) return base;
  return `${base}#sfida=${punteggio}-${numero}`;
}

// Il riquadro in cima all'isola. Non attributivo: il punteggio non e' firmato.
export function testoSfida(punteggio, massimo) {
  return `La sfida condivisa: ${punteggio} su ${massimo}. Riesci a superarla?`;
}

// La riga di fine partita che mette a confronto il tuo punteggio con quello della sfida.
export function testoConfrontoSfida(tuo, sfida) {
  return `Tu ${tuo}, la sfida condivisa ${sfida}`;
}

// -- Il territorio del giocatore (`di:mio`) -----------------------------------------

// La chiave e il formato sono quelli di `app/static/js/v1.js` (readMine e writeMine): qui
// si legge e basta, e non si scrive mai un formato diverso.
export const CHIAVE_TERRITORIO_MIO = "di:mio";

const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const LIVELLI_MIO = ["regione", "provincia"];
const CHIAVE_MAX = 60;
const NOME_MAX = 80;

function slugValido(v) {
  return typeof v === "string" && v.length <= CHIAVE_MAX && SLUG.test(v);
}

// Un nome si stampa come testo (React lo esce), ma il formato lo vieta lo stesso: niente
// markup, niente caratteri di controllo, lunghezza limitata.
function nomeValido(v) {
  return typeof v === "string" && v.trim() === v && v.length >= 1 && v.length <= NOME_MAX
    && !/[<>&"`\\\u0000-\u001f\u007f]/.test(v);
}

// Il contenuto grezzo di `di:mio` -> `{ level, key, name }` (e, per una provincia,
// `region` e `regionName` se ci sono), o `null`. Un livello fuori dalla lista, una chiave
// che non e' uno slug, un nome con markup o troppo lungo, un JSON rotto: tutto `null`.
// Mai un campo in piu' del formato: il resto si butta.
export function parseTerritorioMio(grezzo) {
  if (typeof grezzo !== "string" || grezzo.length > 2000) return null;
  let v;
  try {
    v = JSON.parse(grezzo);
  } catch {
    return null;
  }
  if (!v || typeof v !== "object" || Array.isArray(v)) return null;
  if (!LIVELLI_MIO.includes(v.level) || !slugValido(v.key) || !nomeValido(v.name)) return null;
  const mio = { level: v.level, key: v.key, name: v.name };
  if (v.level === "provincia" && (v.region !== undefined || v.regionName !== undefined)) {
    if (!slugValido(v.region) || !nomeValido(v.regionName)) return null;
    mio.region = v.region;
    mio.regionName = v.regionName;
  }
  return mio;
}

// Fra i territori di una partita (`{ key, level? }`), quello del giocatore, o `null`. Una
// provincia scelta accende anche la sua regione, come fa il resto del sito.
export function trovaTerritorioMio(mio, territori) {
  if (!mio || !Array.isArray(territori)) return null;
  const trovato = territori.find((t) => t && typeof t === "object" && t.key === mio.key
    && (t.level === undefined || t.level === mio.level));
  if (trovato) return trovato;
  if (mio.level === "provincia" && mio.region) {
    return territori.find((t) => t && typeof t === "object" && t.key === mio.region
      && (t.level === undefined || t.level === "regione")) || null;
  }
  return null;
}

export function fraseTerritorioMio(nome) {
  return `C'era anche il tuo territorio: ${nome}.`;
}

// -- Il giorno di fila (hub) --------------------------------------------------------

// Il testo dell'hub per la serie: il server, con il login, e il conto locale, senza.
export function giorniDiFila(profilo, locale) {
  const dalServer = profilo && Number.isInteger(profilo.current) && profilo.current >= 0 ? profilo.current : null;
  return dalServer !== null ? dalServer : Math.max(0, Number.isInteger(locale) ? locale : 0);
}

// -- Il fatto da portarti via -----------------------------------------------------

// Una frase del server che non rispetta le regole di stile non esce: meglio nessuna frase
// che una falsa o rotta. Un numero mancante non si stampa mai ("n.d." o un NaN finito nel
// testo), e niente dei caratteri che lo stile vieta.
const FATTO_ROTTO = /n\.\s?d\.|\bNaN\b|\bundefined\b|\bnull\b|\bInfinity\b/i;

export function fattoPresentabile(fatto) {
  if (typeof fatto !== "string") return null;
  const frase = fatto.trim();
  if (frase.length < 1 || frase.length > 400) return null;
  if (FATTO_ROTTO.test(frase) || /[—–;…]/.test(frase)) return null;
  return frase;
}
