import os

SITE_NAME = "Divario Italia"
SITE_URL = os.getenv("SITE_URL", "https://divarioitalia.it").rstrip("/")

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = os.getenv("SECRET_KEY", "")
# Percorso del file SQLite locale, usato solo quando DATABASE_URL è vuota (cioè
# sviluppo/test): in produzione lo stato mutabile è su Supabase Postgres e questo
# file non viene toccato. Litestream è stato ritirato con la Fase 4.
LEADERBOARD_DB = os.getenv("LEADERBOARD_DB", os.path.join(_REPO_ROOT, "data", "leaderboard.sqlite3"))

# Il backend mutabile (classifica + stato vivo della catena). Vuoto = SQLite
# locale ricavato da LEADERBOARD_DB (default in sviluppo, in test/CI e in
# produzione finché Supabase non è provisionato): così la suite gira senza un
# server Postgres. Impostato (Supabase) = Postgres via pooler Supavisor 6543
# transaction mode. DIRECT_URL (5432) lo usa solo Alembic per le migrazioni.
DATABASE_URL = os.getenv("DATABASE_URL", "")
DIRECT_URL = os.getenv("DIRECT_URL", "")

# Identità Supabase esposte al browser (Auth Google + Realtime). Pubbliche per
# natura (anon key protetta da RLS lato Postgres): stanno in env, non in Secret
# Manager, e si iniettano nei template senza rebuild del frontend.
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
# Verifica del Bearer JWT lato server. HS256 con questo segreto condiviso, oppure
# vuoto e si passa a JWKS (vedi app/auth.py). Segreto: Secret Manager.
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
# Secret key Supabase (server-side): usata SOLO per la cancellazione account
# (admin API che elimina l'utente su Supabase Auth). Segreto: Secret Manager.
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")
# La sola mail ammessa alla console di monitoraggio (sostituisce ?token=).

# Segreto del ping di keep-alive (/_keepalive), come gli altri endpoint interni:
# se impostato, serve l'header X-Keepalive-Key giusto, altrimenti 404. Vuoto =
# aperto (locale). Cloud Scheduler lo manda come header. Evita che un endpoint
# che fa lavoro sul DB e tiene caldo il container sia colpibile da chiunque.
KEEPALIVE_TOKEN = os.getenv("KEEPALIVE_TOKEN", "")

GA_MEASUREMENT_ID = os.getenv("GA_MEASUREMENT_ID", "")
GOOGLE_TAG_MANAGER_ID = os.getenv("GOOGLE_TAG_MANAGER_ID", "")
ADSENSE_CLIENT = os.getenv("ADSENSE_CLIENT", "")
ADSENSE_SLOT_BANNER = os.getenv("ADSENSE_SLOT_BANNER", "")
GOOGLE_SITE_VERIFICATION = os.getenv("GOOGLE_SITE_VERIFICATION", "")
BING_SITE_VERIFICATION = os.getenv("BING_SITE_VERIFICATION", "")

