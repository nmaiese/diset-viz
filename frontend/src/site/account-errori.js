// Gli errori leggibili di "Esporta i miei dati" ed "Elimina account".
//
// Puri, senza DOM: li prova `account-errori.test.mjs`. Dicono che cosa e'
// successo e che cosa fare. Non cambiano cosa fanno le chiamate.

export const ESPORTA_FALLITO =
  "Non siamo riusciti a preparare i tuoi dati. Riprova tra qualche istante.";
export const ELIMINA_FALLITO =
  "L'account non è stato eliminato. Riprova tra qualche istante. Se il problema resta, scrivici dalla pagina Contatti.";
export const SESSIONE_SCADUTA =
  "Il tuo accesso è scaduto. Esci, accedi di nuovo e riprova.";

// `res` e' la Response di `authFetch`, o null senza token. Con il token
// mancante o respinto la causa e' l'accesso; con la rete caduta o un errore
// del servizio, no.
export function messaggioErrore(res, generico) {
  if (!res || res.status === 401) return SESSIONE_SCADUTA;
  return generico;
}
