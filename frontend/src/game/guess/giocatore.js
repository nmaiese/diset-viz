import { getAccessToken, isAuthConfigured } from "../../shared/supabase.js";
import { API } from "./api.js";

// La serie a giorni che il server ha ricalcolato da `daily_results`, per chi ha
// fatto il login. Senza login (o se il profilo non risponde) ritorna null e il
// gioco usa quella locale.
export async function leggiSerieServer() {
  if (!isAuthConfigured()) return null;
  try {
    const token = await getAccessToken();
    if (!token) return null;
    const res = await fetch(API.playerMe, { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) return null;
    const daily = (await res.json())?.stats?.daily;
    if (!daily) return null;
    return { current: daily.current_daily_streak || 0, max: daily.max_daily_streak || 0 };
  } catch {
    return null;
  }
}
