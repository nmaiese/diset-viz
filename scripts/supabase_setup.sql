-- Setup Supabase per Divario Italia (Fase 4). Da eseguire UNA volta nel SQL
-- editor del progetto, DOPO `alembic upgrade head` (che crea le tabelle).
--
-- Due cose che Alembic non fa e che sono l'unica vera guardia della console:
--   1. Row Level Security: senza, l'anon key leggerebbe tutto. La policy lega la
--      lettura delle tabelle pipeline alla mail dell'admin nel JWT.
--   2. Publication Realtime: senza, la console non riceve mai un tick (nessun
--      errore, resta vuota per sempre).
--
-- L'admin e' cablato qui sotto. Se cambia MONITOR_ADMIN_EMAIL lato app, cambia
-- anche questa mail e ri-esegui le policy.

-- === RLS attiva su tutte le tabelle dell'app ===
-- Le scritture dell'app passano dalla connection string (ruolo `postgres`,
-- BYPASSRLS): il gioco, la catena e l'account continuano a scrivere e la RLS non
-- li tocca. La RLS conta solo per chi entra con l'anon key dal browser, ed e'
-- difesa in profondita': il confine per-utente vero e' il WHERE auth_id nel
-- backend. NON contare sulla RLS per le tabelle account.
ALTER TABLE public.scores            ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pipeline_activity ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pipeline_tokens   ENABLE ROW LEVEL SECURITY;

-- Tabelle account (Fase 5): RLS attiva, ogni utente vede/scrive solo le proprie
-- righe. Il browser non interroga queste tabelle direttamente (passa dal backend);
-- le policy sono difesa in profondita'.
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS own_profile ON public.profiles;
CREATE POLICY own_profile ON public.profiles
  FOR ALL TO authenticated
  USING ( (auth.jwt() ->> 'sub') = auth_id )
  WITH CHECK ( (auth.jwt() ->> 'sub') = auth_id );

ALTER TABLE public.favorites ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS own_favorites ON public.favorites;
CREATE POLICY own_favorites ON public.favorites
  FOR ALL TO authenticated
  USING ( (auth.jwt() ->> 'sub') = auth_id )
  WITH CHECK ( (auth.jwt() ->> 'sub') = auth_id );

-- Stats, storico giornaliero, achievements (Fase 5.2): stessa forma own-rows.
ALTER TABLE public.player_stats  ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS own_player_stats ON public.player_stats;
CREATE POLICY own_player_stats ON public.player_stats
  FOR ALL TO authenticated
  USING ( (auth.jwt() ->> 'sub') = auth_id ) WITH CHECK ( (auth.jwt() ->> 'sub') = auth_id );

ALTER TABLE public.daily_results ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS own_daily_results ON public.daily_results;
CREATE POLICY own_daily_results ON public.daily_results
  FOR ALL TO authenticated
  USING ( (auth.jwt() ->> 'sub') = auth_id ) WITH CHECK ( (auth.jwt() ->> 'sub') = auth_id );

ALTER TABLE public.achievements  ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS own_achievements ON public.achievements;
CREATE POLICY own_achievements ON public.achievements
  FOR ALL TO authenticated
  USING ( (auth.jwt() ->> 'sub') = auth_id ) WITH CHECK ( (auth.jwt() ->> 'sub') = auth_id );

-- Confronti salvati (Fase 5.3): own-rows. Niente public_slug, nessuna condivisione.
ALTER TABLE public.saved_comparisons ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS own_saved_comparisons ON public.saved_comparisons;
CREATE POLICY own_saved_comparisons ON public.saved_comparisons
  FOR ALL TO authenticated
  USING ( (auth.jwt() ->> 'sub') = auth_id ) WITH CHECK ( (auth.jwt() ->> 'sub') = auth_id );

-- scores: DENY-ALL deliberato per l'anon. Nessuna policy di lettura: la classifica
-- pubblica si serve dal backend Flask, non dal browser. Funziona perche' l'app si
-- connette come `postgres`, che ha BYPASSRLS: la RLS non lo tocca. NON aggiungere
-- una policy anon qui e NON contare sulla RLS per proteggere scores: se un domani
-- l'app girasse con un ruolo senza BYPASSRLS, la classifica tornerebbe vuota in
-- silenzio (il backend ha un fallback tollerante che maschera il vuoto).

-- pipeline_activity / pipeline_tokens: lettura SOLO per la mail admin.
DROP POLICY IF EXISTS admin_reads_activity ON public.pipeline_activity;
CREATE POLICY admin_reads_activity ON public.pipeline_activity
  FOR SELECT TO authenticated
  USING ( (auth.jwt() ->> 'email') = 'maiese.next@gmail.com' );

DROP POLICY IF EXISTS admin_reads_tokens ON public.pipeline_tokens;
CREATE POLICY admin_reads_tokens ON public.pipeline_tokens
  FOR SELECT TO authenticated
  USING ( (auth.jwt() ->> 'email') = 'maiese.next@gmail.com' );

-- === Realtime: le due tabelle nella publication ===
-- ALTER PUBLICATION ... ADD TABLE NON e' idempotente: rieseguirlo su una tabella
-- gia' presente solleva duplicate_object e aborta lo script. Lo si avvolge, cosi'
-- l'intero file resta rieseguibile (utile mentre si itera sulla mail della policy).
DO $$
BEGIN
  ALTER PUBLICATION supabase_realtime ADD TABLE public.pipeline_activity;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$
BEGIN
  ALTER PUBLICATION supabase_realtime ADD TABLE public.pipeline_tokens;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Realtime deve poter portare la riga vecchia su UPDATE/DELETE (replace_prs e
-- close_beat cancellano: e' il percorso di scrittura dominante). REPLICA IDENTITY
-- FULL lo garantisce.
ALTER TABLE public.pipeline_activity REPLICA IDENTITY FULL;
ALTER TABLE public.pipeline_tokens   REPLICA IDENTITY FULL;
