# Supabase統合 設計書

## テーブル設計

### user_profiles
```sql
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### skill_xp
```sql
CREATE TABLE skill_xp (
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
```

### xp_history
```sql
CREATE TABLE xp_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    scenario_id TEXT,
    xp_gains JSONB NOT NULL DEFAULT '{}',
    scores_snapshot JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_xp_history_user ON xp_history(user_id, created_at DESC);
```

### scenario_completions
```sql
CREATE TABLE scenario_completions (
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
```

### badges
```sql
CREATE TABLE badges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    badge_id TEXT NOT NULL,
    earned_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, badge_id)
);
```

### quests
```sql
CREATE TABLE quests (
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
CREATE INDEX idx_quests_user_active ON quests(user_id, completed, expires_at);
```

### conversations
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    mode TEXT NOT NULL CHECK (mode IN ('scenario', 'chat', 'watch')),
    scenario_id TEXT,
    history JSONB NOT NULL DEFAULT '[]',
    summary JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_conversations_user ON conversations(user_id, created_at DESC);
CREATE INDEX idx_conversations_mode ON conversations(user_id, mode);
```

### quiz_history
```sql
CREATE TABLE quiz_history (
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
```

### user_stats
```sql
CREATE TABLE user_stats (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    total_scenarios_completed INT DEFAULT 0,
    total_quizzes_answered INT DEFAULT 0,
    total_quizzes_correct INT DEFAULT 0,
    consecutive_days INT DEFAULT 0,
    unique_scenarios_tried INT DEFAULT 0,
    last_activity_date DATE,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## RLS (Row Level Security)

全テーブルに以下のポリシーを適用:
```sql
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only access own data"
    ON {table} FOR ALL
    USING (auth.uid() = user_id);
```

## サービス層アーキテクチャ

```
SupabaseClient (シングルトン)
    ↓
SupabaseUserDataService (UserDataService と同じインターフェース)
    ↓ フォールバック
UserDataService (JSONファイル、Supabase未設定時)
```

## 認証フロー

```
未ログイン → ゲストモード（セッションUUID、既存動作）
    ↓ 登録/ログイン
ログイン済み → Supabase Auth UID でデータアクセス
    ↓ オプション
ゲストデータ → アカウントに紐づけ（マイグレーション）
```
