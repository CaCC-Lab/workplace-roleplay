-- 002: user_data テーブルの user_id を TEXT に変更し、FK制約とRLSを緩和
-- サーバーサイド（Flask）からの書き込みを許可するため

-- 既存テーブルを再作成（DROP + CREATE）
DROP TABLE IF EXISTS public.user_data CASCADE;

CREATE TABLE IF NOT EXISTS public.user_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

-- RLSは無効化（サーバーサイドでアクセス制御）
ALTER TABLE public.user_data DISABLE ROW LEVEL SECURITY;

-- conversations テーブルも同様に修正
DROP TABLE IF EXISTS public.conversations CASCADE;

CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('scenario', 'chat', 'watch')),
    scenario_id TEXT,
    history JSONB NOT NULL DEFAULT '[]',
    summary JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user ON public.conversations(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_mode ON public.conversations(user_id, mode);

ALTER TABLE public.conversations DISABLE ROW LEVEL SECURITY;
