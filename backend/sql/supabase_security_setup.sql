-- ============================================================
-- INSIGHTIQ SUPABASE POSTGRESQL SECURITY CONFIGURATION
-- ============================================================
-- Purpose: Resolve Supabase Security Advisor CRITICAL warnings:
-- 1. rls_disabled_in_public ("Table publicly accessible")
-- 2. sensitive_columns_exposed ("A table with columns containing sensitive data is accessible through PostgREST API without access restrictions")
--
-- Architecture Note:
-- React frontend NEVER connects directly to Supabase PostgREST API using anon key.
-- All client interactions go through Render FastAPI backend via HTTPS.
-- FastAPI connects directly to PostgreSQL using SQLAlchemy database credentials (psycopg2-binary).
--
-- Running these statements enables Row Level Security (RLS) on public tables.
-- Because no public policies are granted to the 'anon' or 'authenticated' roles for PostgREST API,
-- direct REST API calls via Supabase URL + anon key will be BLOCKED.
-- FastAPI's direct PostgreSQL connection (which operates as table owner / postgres role)
-- bypasses RLS in PostgreSQL and continues working cleanly.
-- ============================================================

-- 1. Enable RLS on all public tables
ALTER TABLE IF EXISTS public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.datasets ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.dataset_file_blobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.dashboard_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.training_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.chat_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.refresh_tokens ENABLE ROW LEVEL SECURITY;

-- 2. Explicitly revoke public PostgREST permissions from 'anon' and 'authenticated' roles
REVOKE ALL ON TABLE public.users FROM anon, authenticated;
REVOKE ALL ON TABLE public.datasets FROM anon, authenticated;
REVOKE ALL ON TABLE public.dataset_file_blobs FROM anon, authenticated;
REVOKE ALL ON TABLE public.dashboard_configs FROM anon, authenticated;
REVOKE ALL ON TABLE public.training_runs FROM anon, authenticated;
REVOKE ALL ON TABLE public.chat_conversations FROM anon, authenticated;
REVOKE ALL ON TABLE public.refresh_tokens FROM anon, authenticated;

-- ============================================================
-- END OF SCRIPT
-- ============================================================
