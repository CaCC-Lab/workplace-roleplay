# Bugfix: ゲーミフィケーション系 public テーブルの匿名アクセスポリシーを撤去

## Current Behavior（現在の動作）

Supabase セキュリティアドバイザーが WARN「`auth_allow_anonymous_sign_ins`」を
本リポジトリ所有の 8 テーブルで検出している。

### 証拠

**1. 対象テーブル（policy 名）**
- `public.badges` / `public.quests` / `public.quiz_history` / `public.scenario_completions`
  / `public.skill_xp` / `public.user_stats` / `public.xp_history` — `"Users can only access own data"`
- `public.user_profiles` — `"Users can only access own profile"`

いずれも `migrations/001_initial.sql` で作成した `auth.uid() = user_id`（user_profiles は
`auth.uid() = id`）ベースの FOR ALL ポリシー。

**2. アドバイザー検出内容**
- 各テーブルが anon / authenticated ロールへアクセスを許可するポリシーを持つ（匿名サインイン有効時）。

**3. 実アクセス経路の確認**
- フロントエンド（`static/`, `templates/`）に Supabase 直接アクセスは皆無
  （`createClient` / anon key / `rest/v1` / `signInAnonymously` のいずれも不在）。
- 全アクセスは Flask サーバー経由で、`services/supabase_client.py` は SERVICE_KEY を優先使用。
- よってクライアント向けポリシーは実アクセス制御に使われていない。

## Expected Behavior（期待する動作）

- 上記 8 テーブルで RLS は有効のまま、クライアント向けポリシーを撤去。
- anon / authenticated ロールには一切の権限を与えない（service_role のみアクセス可）。
- 002/003 で user_data・conversations に適用済みの「service_role 専用」モデルに統一。
- アドバイザーの該当 WARN（本リポジトリ分 8 件）が消える。

## Unchanged Behavior（変更しない動作）

- テーブル構造・データ・`user_id` 型は不変。
- アプリケーションコードは無変更（service_role は RLS をバイパスするため従来通り動作）。
- 同居する別アプリ（`dify` スキーマ / `occupations`・`gatb` 系 / `gamify` スキーマ等）の
  オブジェクトには一切触れない。

## Root Cause（根本原因）

001 ではクライアント直アクセス（匿名サインイン + `auth.uid()` 突合）を想定して
ポリシーを作成したが、その後 002/003 でサーバー側 service_role 専用アクセスへ移行した。
user_data・conversations は 003 でポリシー撤去済みだが、ゲーミフィケーション系
8 テーブルは 001 のポリシーが残存していた。

## Fix Strategy（修正方針）

新規マイグレーション `migrations/004_harden_gamification_rls.sql`:

1. 8 テーブルのクライアント向けポリシーを `DROP POLICY IF EXISTS`
2. RLS を `ENABLE`（冪等）し、anon / authenticated から `REVOKE ALL`
3. Supabase Dashboard → SQL Editor で手動実行（README 手順に 004 を追記）

## Test Strategy（検証方法）

1. 適用後、アドバイザー（Advisors → Security）で本リポジトリ分 8 件の
   `auth_allow_anonymous_sign_ins` WARN が消えることを確認。
2. アプリ起動後、ゲーミフィケーション（XP 加算・クエスト・バッジ・履歴・統計）が
   従来通り動作することを確認。
3. anon key で直接これらのテーブルを SELECT し、`permission denied` または空配列を確認。

## Risk Assessment（リスク評価）

- **破壊的変更**: なし（構造・データ・アプリコード不変）。
- **ロールバック**: 001 の該当 CREATE POLICY 文を再実行すれば即時復旧。
- **副作用**: 将来クライアント直アクセスを再導入する場合は、anon を除外した
  適切なポリシーを別途設計する必要がある（現状は service_role 専用のため問題なし）。

## Out of Scope（本修正の対象外 — 別管轄）

同一 Supabase プロジェクトに同居する別アプリ由来の警告は本リポジトリでは対処しない:
- `function_search_path_mutable`（career系 / dify / gamify の関数）
- `extension_in_public`（pg_trgm, vector）
- `rls_policy_always_true`（occupations / gatb 系）
- `anon/authenticated_security_definer_function_executable`（`public.rls_auto_enable()`）
- ダッシュボード設定: `auth_leaked_password_protection`
