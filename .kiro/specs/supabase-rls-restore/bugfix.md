# Bugfix: Supabase public テーブルの RLS 無効化を解消

## Current Behavior（現在の動作）

Supabase セキュリティアドバイザーから Critical 警告「`rls_disabled_in_public`」が通知された（2026-04-13 検出）。

### 証拠

**1. 対象テーブル**
- `public.user_data` — `migrations/002_fix_rls.sql:17` で `DISABLE ROW LEVEL SECURITY`
- `public.conversations` — `migrations/002_fix_rls.sql:36` で `DISABLE ROW LEVEL SECURITY`

**2. 経緯**
- `migrations/001_initial.sql` では全テーブルに RLS 有効 + `auth.uid() = user_id` ポリシー
- `002_fix_rls.sql` で `user_id` を UUID → TEXT に変更（Flask サーバー側でユーザーID管理）
- `auth.uid()` との突合が不可能になり、RLS 自体を無効化してしまった

**3. リスク**
- public テーブルが anon / authenticated ロールに対して無防備
- Supabase プロジェクト URL と anon key が漏洩すると、全データの read/write/delete が可能
- `services/supabase_client.py:76` は service_role key を優先使用するため、アプリ動作自体には影響しない

## Expected Behavior（期待する動作）

- `public.user_data` と `public.conversations` で RLS を **有効化**
- anon / authenticated ロールには一切の権限を与えない（service_role のみアクセス可能）
- service_role は RLS を自動バイパスするため、アプリは変更不要で今まで通り動作
- Supabase セキュリティアドバイザーの Critical 警告が消える

## Unchanged Behavior（変更しない動作）

- `user_id` カラムの型（TEXT）は変更しない
- アプリケーションコード（`services/supabase_client.py` 等）は変更しない
- service_role key 経由の読み書きはすべて従来通り動作
- 他テーブル（`skill_xp`, `xp_history` 等）の既存 RLS 設定は変更しない

## Root Cause（根本原因）

`002_fix_rls.sql` 作成時、`user_id` 型変更により auth.uid() ポリシーが無効化されることへの対応として、RLS 自体を無効化してしまった。正しくは「RLS 有効 + anon/authenticated に権限なし」とすべきだった（service_role は RLS をバイパスするため、サーバーサイドアクセスには影響しない）。

## Fix Strategy（修正方針）

新規マイグレーション `migrations/003_enable_rls_server_only.sql` を作成：

1. `public.user_data` と `public.conversations` の RLS を `ENABLE`
2. anon / authenticated ロールから `REVOKE ALL` で権限剥奪（念のため明示）
3. ポリシーは作成しない（= service_role 以外はアクセス不可）
4. Supabase Dashboard の SQL Editor で手動実行する手順を README 追記

## Test Strategy（検証方法）

1. マイグレーション適用後、Supabase Dashboard の Advisors で Critical 警告が消えることを確認
2. アプリ起動後、ゲーミフィケーションの XP 保存・履歴取得が従来通り動作することを確認
3. anon key で直接 `user_data` を SELECT してみて、`permission denied` または空配列が返ることを確認

## Risk Assessment（リスク評価）

- **破壊的変更**: なし（テーブル構造・データ・アプリコードすべて不変）
- **ロールバック**: `ALTER TABLE ... DISABLE ROW LEVEL SECURITY` で即時復旧可能
- **副作用**: anon key で直接アクセスするクライアント実装があれば動かなくなるが、現状は service_role のみの想定で問題なし
