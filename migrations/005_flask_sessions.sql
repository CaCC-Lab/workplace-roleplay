-- 005: Flask セッションを保存する public.flask_sessions を作成（server-side only アクセス）
--
-- 背景:
--   Vercel（サーバーレス）ではローカルファイルにセッションを保存できないため、
--   services/supabase_session.py が会話履歴などのセッションをこのテーブルに保存する。
--
-- 方針:
--   - RLS を ENABLE し、ポリシーは作成しない（anon / authenticated からは読めない）
--   - service_role でアクセスする Flask サーバーからのみ読み書きする
--
-- ロールバック:
--   DROP TABLE IF EXISTS public.flask_sessions;

CREATE TABLE IF NOT EXISTS public.flask_sessions (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_flask_sessions_expires_at ON public.flask_sessions (expires_at);

ALTER TABLE public.flask_sessions ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.flask_sessions FROM anon;
REVOKE ALL ON public.flask_sessions FROM authenticated;

-- 既定の権限付与を無効にしているプロジェクトでも、サーバー（service_role）から読み書きできるようにする
GRANT SELECT, INSERT, UPDATE, DELETE ON public.flask_sessions TO service_role;
