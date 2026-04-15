-- 003: public.user_data / public.conversations の RLS を有効化（server-side only アクセス）
--
-- 背景:
--   002_fix_rls.sql で user_id を TEXT 化した際に RLS を DISABLE してしまった。
--   Supabase セキュリティアドバイザーが Critical「rls_disabled_in_public」を検出。
--
-- 方針:
--   - RLS を ENABLE
--   - ポリシーは作成しない（= anon / authenticated からのアクセスはすべて拒否）
--   - service_role は RLS を自動バイパスするため、Flask サーバーサイドからの
--     アクセス（services/supabase_client.py）は影響を受けない
--
-- ロールバック:
--   ALTER TABLE public.user_data DISABLE ROW LEVEL SECURITY;
--   ALTER TABLE public.conversations DISABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------------
-- user_data
-- ---------------------------------------------------------------------------
ALTER TABLE public.user_data ENABLE ROW LEVEL SECURITY;

-- 念のため anon / authenticated から明示的に権限剥奪
REVOKE ALL ON public.user_data FROM anon;
REVOKE ALL ON public.user_data FROM authenticated;

-- ---------------------------------------------------------------------------
-- conversations
-- ---------------------------------------------------------------------------
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.conversations FROM anon;
REVOKE ALL ON public.conversations FROM authenticated;
