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
-- Le scritture dell'app passano dalla connection string (service role / owner),
-- che bypassa la RLS: il gioco e la catena continuano a scrivere. La RLS conta
-- solo per chi entra con l'anon key dal browser.
ALTER TABLE public.scores            ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pipeline_activity ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pipeline_tokens   ENABLE ROW LEVEL SECURITY;

-- scores: nessuna policy di lettura per l'anon (la classifica pubblica si serve
-- dal backend Flask, non dal browser). Deny-all e' il default con RLS attiva.

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
-- Idempotente: ignora l'errore se sono gia' nella publication.
ALTER PUBLICATION supabase_realtime ADD TABLE public.pipeline_activity;
ALTER PUBLICATION supabase_realtime ADD TABLE public.pipeline_tokens;
