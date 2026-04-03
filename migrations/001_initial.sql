-- Supabase 初期スキーマ（.kiro/specs/supabase-integration/design.md 準拠）
-- auth.users は Supabase が提供

-- ---------------------------------------------------------------------------
-- user_profiles
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only access own profile"
    ON public.user_profiles FOR ALL
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- ---------------------------------------------------------------------------
-- skill_xp
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.skill_xp (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    empathy INT DEFAULT 0,
    clarity INT DEFAULT 0,
    active_listening INT DEFAULT 0,
    adaptability INT DEFAULT 0,
    positivity INT DEFAULT 0,
    professionalism INT DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

ALTER TABLE public.skill_xp ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only access own data"
    ON public.skill_xp FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- xp_history
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.xp_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    scenario_id TEXT,
    xp_gains JSONB NOT NULL DEFAULT '{}',
    scores_snapshot JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_xp_history_user ON public.xp_history(user_id, created_at DESC);

ALTER TABLE public.xp_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only access own data"
    ON public.xp_history FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- scenario_completions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.scenario_completions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    scenario_id TEXT NOT NULL,
    difficulty TEXT DEFAULT 'beginner',
    count INT DEFAULT 1,
    best_scores JSONB DEFAULT '{}',
    first_completed_at TIMESTAMPTZ DEFAULT NOW(),
    last_completed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, scenario_id)
);

ALTER TABLE public.scenario_completions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only access own data"
    ON public.scenario_completions FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- badges
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.badges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    badge_id TEXT NOT NULL,
    earned_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, badge_id)
);

ALTER TABLE public.badges ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only access own data"
    ON public.badges FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- quests
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.quests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    quest_id TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('daily', 'weekly')),
    description TEXT,
    target_key TEXT,
    target_value INT DEFAULT 1,
    current_value INT DEFAULT 0,
    bonus_xp INT DEFAULT 0,
    completed BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quests_user_active ON public.quests(user_id, completed, expires_at);

ALTER TABLE public.quests ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only access own data"
    ON public.quests FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- conversations
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    mode TEXT NOT NULL CHECK (mode IN ('scenario', 'chat', 'watch')),
    scenario_id TEXT,
    history JSONB NOT NULL DEFAULT '[]',
    summary JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user ON public.conversations(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_mode ON public.conversations(user_id, mode);

ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only access own data"
    ON public.conversations FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- quiz_history
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.quiz_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    question TEXT,
    choices JSONB,
    correct_answer INT,
    user_answer INT,
    is_correct BOOLEAN,
    xp_earned INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.quiz_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only access own data"
    ON public.quiz_history FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- user_stats
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.user_stats (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    total_scenarios_completed INT DEFAULT 0,
    total_quizzes_answered INT DEFAULT 0,
    total_quizzes_correct INT DEFAULT 0,
    consecutive_days INT DEFAULT 0,
    unique_scenarios_tried INT DEFAULT 0,
    last_activity_date DATE,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.user_stats ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only access own data"
    ON public.user_stats FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);
