-- Run ONCE in Supabase -> SQL Editor, after `python manage.py migrate`.
-- Django connects as the `postgres` role (bypasses RLS), so the site keeps working,
-- but Supabase's public REST API can no longer read/write your tables with the anon key.
DO $$
DECLARE t record;
BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t.tablename);
  END LOOP;
END $$;
