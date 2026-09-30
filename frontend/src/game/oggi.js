// Lo stato di oggi, in un punto solo: quali sfide del giorno ha giocato questo
// dispositivo e come sono andate. Lo scrivono i quattro giochi a fine partita
// (`segnaGiocata`), lo legge l'hub (`statoOggi`, `serieLocale`). Sta nel
// localStorage con la chiave `di-oggi:<gioco>:<ISO>`, il giorno e' quello di
// Roma. Niente React qui: le funzioni sono pure salvo la lettura e la scrittura
// del localStorage, e se questo manca (navigazione privata) tutto tace.

import { giorniTra, oggiRoma } from "./guess/serie.js";

export { oggiRoma };

export const GIOCHI = ["indovina", "provincia", "compare", "order"];

const PREFISSO = "di-oggi:";
// Quanti giorni indietro si guarda per la serie: oltre la serie e' gia' finita
// o, se no, l'hub non la mostrerebbe comunque per intero.
const GIORNI_INDIETRO = 400;

function chiave(gioco, iso) {
  return `${PREFISSO}${gioco}:${iso}`;
}

// `esito` e' `{ ok: boolean, testo: string }`: `ok` decide l'icona (giusto o
// sbagliato), `testo` e' la riga che la accompagna ("Risolta in 3 tentativi").
export function segnaGiocata(gioco, iso, esito) {
  if (!GIOCHI.includes(gioco) || !/^\d{4}-\d{2}-\d{2}$/.test(iso || "")) return;
  try {
    window.localStorage.setItem(chiave(gioco, iso), JSON.stringify({ ok: Boolean(esito && esito.ok), testo: String((esito && esito.testo) || "") }));
  } catch {
    // Senza localStorage l'hub non sa che hai giocato: nessun danno per la partita.
  }
}

// L'esito di oggi di un gioco, o null se non e' stato giocato.
export function statoOggi(gioco, iso = oggiRoma()) {
  try {
    const grezzo = window.localStorage.getItem(chiave(gioco, iso));
    if (!grezzo) return null;
    const esito = JSON.parse(grezzo);
    return { ok: Boolean(esito.ok), testo: String(esito.testo || "") };
  } catch {
    return null;
  }
}

// I giorni di fila, fino a oggi, con almeno una sfida del giorno giocata.
// Come sul server: se oggi non hai ancora giocato, la serie di ieri vale
// ancora, e si spezza solo quando passa un giorno intero senza sfide.
// `giorni` e' un insieme di date ISO. Funzione pura.
export function serieDaGiorni(giorni, oggiIso) {
  const insieme = giorni instanceof Set ? giorni : new Set(giorni);
  let cursore = insieme.has(oggiIso) ? oggiIso : giornoPrima(oggiIso);
  let serie = 0;
  while (insieme.has(cursore) && serie < GIORNI_INDIETRO) {
    serie += 1;
    cursore = giornoPrima(cursore);
  }
  return serie;
}

function giornoPrima(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d - 1)).toISOString().slice(0, 10);
}

// La serie di questo dispositivo, dalle chiavi `di-oggi:*`.
export function serieLocale(oggiIso = oggiRoma()) {
  const giorni = new Set();
  try {
    for (let i = 0; i < window.localStorage.length; i += 1) {
      const k = window.localStorage.key(i);
      if (k && k.startsWith(PREFISSO)) giorni.add(k.slice(k.lastIndexOf(":") + 1));
    }
  } catch {
    return 0;
  }
  return serieDaGiorni([...giorni].filter((g) => giorniTra(g, oggiIso) >= 0), oggiIso);
}
