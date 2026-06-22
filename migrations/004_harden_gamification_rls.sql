-- 004: ゲーミフィケーション系 public テーブルのクライアント向け RLS ポリシーを撤去し
--      service_role 専用アクセスに統一する
--
-- 背景:
--   Supabase セキュリティアドバイザーが WARN「auth_allow_anonymous_sign_ins」を
--   以下 8 テーブルで検出。いずれも 001_initial.sql で作成した
--   `auth.uid() = user_id` ベースのクライアント向けポリシーが残存しており、
--   匿名サインイン有効時に anon / authenticated ロールへアクセスを許可する形になっている。
--
--   一方、本アプリのフロントエンド（static/js, templates）は Supabase へ
--   一切直接アクセスせず、すべて Flask サーバー側の service_role 経由で読み書きする
--   （services/supabase_client.py は SERVICE_KEY を優先使用）。
--   よってこれらのクライアント向けポリシーは実アクセス制御に使われておらず、
--   002/003 で user_data・conversations に適用した「service_role 専用」モデルと不整合。
--
-- 方針（003 と同一）:
--   - RLS は ENABLE のまま維持
--   - クライアント向けポリシーを DROP（= anon / authenticated からのアクセスは全拒否）
--   - anon / authenticated から明示的に REVOKE ALL
--   - service_role は RLS を自動バイパスするため、アプリは無変更で従来通り動作
--
-- 対象（本リポジトリ所有テーブルのみ。dify / occupations / gamify 等の同居アプリには触れない）:
--   badges, quests, quiz_history, scenario_completions,
--   skill_xp, user_profiles, user_stats, xp_history
--
-- ロールバック:
--   001_initial.sql の該当 CREATE POLICY 文を再実行する。

-- ---------------------------------------------------------------------------
-- "Users can only access own data" ポリシーを持つテーブル
-- ---------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can only access own data" ON public.badges;
DROP POLICY IF EXISTS "Users can only access own data" ON public.quests;
DROP POLICY IF EXISTS "Users can only access own data" ON public.quiz_history;
DROP POLICY IF EXISTS "Users can only access own data" ON public.scenario_completions;
DROP POLICY IF EXISTS "Users can only access own data" ON public.skill_xp;
DROP POLICY IF EXISTS "Users can only access own data" ON public.user_stats;
DROP POLICY IF EXISTS "Users can only access own data" ON public.xp_history;

-- ---------------------------------------------------------------------------
-- user_profiles はポリシー名が異なる
-- ---------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can only access own profile" ON public.user_profiles;

-- ---------------------------------------------------------------------------
-- RLS を明示的に再確認（既に有効だが冪等性のため）＋ anon/authenticated 権限剥奪
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    t text;
    tables text[] := ARRAY[
        'badges', 'quests', 'quiz_history', 'scenario_completions',
        'skill_xp', 'user_profiles', 'user_stats', 'xp_history'
    ];
BEGIN
    FOREACH t IN ARRAY tables LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', t);
        EXECUTE format('REVOKE ALL ON public.%I FROM anon;', t);
        EXECUTE format('REVOKE ALL ON public.%I FROM authenticated;', t);
    END LOOP;
END $$;
