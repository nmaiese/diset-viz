// I testi di errore che i cinque giochi hanno in comune, in un posto solo: stesso evento, stessa
// frase (`docs/GIOCO.md`, "I testi"). Niente React, niente DOM, cosi' `node --test` li prova
// (`testi.test.mjs`). La voce e' impersonale o alla seconda persona, mai "non riesco" o "non sono
// riuscito": il sottomarchio parla a chi gioca, non di se'.

// Il server non risponde: rete assente, 5xx compreso il 503.
export const ERRORE_RETE = "Il server non risponde.";
// Un errore senza nome: non diciamo che cosa e' successo perche' non lo sappiamo.
export const ERRORE_GENERICO = "Non è andata a buon fine. Riprova.";
// Il blocco per frequenza, con lo stesso sostantivo ovunque.
export const ERRORE_LIMITE = "Troppe richieste in poco tempo. Riprova fra un minuto.";
// La partita (la sessione) non e' piu' utilizzabile. "Scaduta" resta al solo tempo del round.
export const PARTITA_INTERROTTA = "La partita si è interrotta, non per colpa tua.";
// Il giorno e' cambiato mentre si giocava.
export const SFIDA_CAMBIATA = "La sfida del giorno è cambiata mentre giocavi.";
// Il tentativo parte da solo un'altra volta (rete lenta): detto mentre i bottoni sono fermi.
export const NUOVO_TENTATIVO = "Connessione lenta: nuovo tentativo in corso.";

// Un errore di rete o del server che passa da solo: ha senso offrire "Riprova". `status` e' quello
// HTTP; `0`, `undefined` o un valore non numerico sono la rete che non risponde (fetch che lancia).
export function erroreDiRete(status) {
  return !Number.isInteger(status) || status === 0 || status >= 500;
}

// Il messaggio di un tentativo che non e' arrivato, dato lo stato HTTP: la rete e il 5xx dicono che
// il server non risponde, il 429 il blocco, il resto il generico.
export function messaggioTentativo(status) {
  if (status === 429) return ERRORE_LIMITE;
  if (erroreDiRete(status)) return `${ERRORE_RETE} Riprova.`;
  return ERRORE_GENERICO;
}
