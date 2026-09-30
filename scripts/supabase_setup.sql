-- Setup Supabase per Divario Italia (Fase 4). Da eseguire UNA volta nel SQL
-- editor del progetto, DOPO `alembic upgrade head` (che crea le tabelle).
--
-- Row Level Security: senza, l'anon key leggerebbe tutto. Ogni utente vede solo
-- le proprie righe.
--
-- Il 5 settembre 2026 sono cadute le due tabelle del cruscotto della catena
-- (`pipeline_run`, `pipeline_agente`, migrazione 0009): con loro se ne sono
-- andate la policy della mail admin, la publication Realtime e REPLICA IDENTITY,
-- che esistevano solo per la console.

-- === RLS attiva su tutte le tabelle dell'app ===
-- Le scritture dell'app passano dalla connection string (ruolo `postgres`,
-- BYPASSRLS): il gioco, la catena e l'account continuano a scrivere e la RLS non
-- li tocca. La RLS conta solo per chi entra con l'anon key dal browser, ed e'
-- difesa in profondita': il confine per-utente vero e' il WHERE auth_id nel
-- backend. NON contare sulla RLS per le tabelle account.
ALTER TABLE public.scores          ENABLE ROW LEVEL SECURITY;

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

-- Stats, storico giornaliero, achievements (Fase 5.2): le scrive solo il server (BYPASSRLS),
-- il giocatore puo' solo leggere le proprie righe. Erano `FOR ALL ... WITH CHECK`: con la
-- chiave anon e il proprio JWT il browser poteva scrivere `daily_results` (tentativi,
-- vinto) e `player_stats`, e da li' i traguardi. Il file si rilancia su una base che ha
-- gia' le vecchie policy: ogni CREATE e' preceduto dal DROP IF EXISTS dello stesso nome.
ALTER TABLE public.player_stats  ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS own_player_stats ON public.player_stats;
CREATE POLICY own_player_stats ON public.player_stats
  FOR SELECT TO authenticated
  USING ( (auth.jwt() ->> 'sub') = auth_id );

ALTER TABLE public.daily_results ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS own_daily_results ON public.daily_results;
CREATE POLICY own_daily_results ON public.daily_results
  FOR SELECT TO authenticated
  USING ( (auth.jwt() ->> 'sub') = auth_id );

ALTER TABLE public.achievements  ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS own_achievements ON public.achievements;
CREATE POLICY own_achievements ON public.achievements
  FOR SELECT TO authenticated
  USING ( (auth.jwt() ->> 'sub') = auth_id );

-- Confronti salvati (Fase 5.3): own-rows. Niente public_slug, nessuna condivisione.
ALTER TABLE public.saved_comparisons ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS own_saved_comparisons ON public.saved_comparisons;
CREATE POLICY own_saved_comparisons ON public.saved_comparisons
  FOR ALL TO authenticated
  USING ( (auth.jwt() ->> 'sub') = auth_id ) WITH CHECK ( (auth.jwt() ->> 'sub') = auth_id );

-- Punteggi delle sfide del giorno (migrazione 0010): DENY-ALL come `scores`. Il server li
-- scrive con il suo ruolo (BYPASSRLS) e contano per i traguardi: con `FOR ALL` il browser,
-- con la chiave anon e il proprio JWT, poteva scrivere il punteggio che voleva. Si toglie la
-- vecchia policy e non se ne crea nessuna: RLS attiva e nessuna policy, il browser non la
-- legge ne' la scrive.
ALTER TABLE public.daily_scores ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS own_daily_scores ON public.daily_scores;

-- quiz_answered (migrazione 0010): i round gia' risposti, solo backend. DENY-ALL
-- come scores: RLS attiva e nessuna policy, il browser non la legge ne' la scrive.
ALTER TABLE public.quiz_answered ENABLE ROW LEVEL SECURITY;

-- scores: DENY-ALL deliberato per l'anon. Nessuna policy di lettura: la classifica
-- pubblica si serve dal backend Flask, non dal browser. Funziona perche' l'app si
-- connette come `postgres`, che ha BYPASSRLS: la RLS non lo tocca. NON aggiungere
-- una policy anon qui e NON contare sulla RLS per proteggere scores: se un domani
-- l'app girasse con un ruolo senza BYPASSRLS, la classifica tornerebbe vuota in
-- silenzio (il backend ha un fallback tollerante che maschera il vuoto).
