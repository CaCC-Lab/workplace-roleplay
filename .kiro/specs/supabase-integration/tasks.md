# 実装計画: Supabase統合

## タスク

- [ ] 1. Supabaseクライアント基盤
  - [ ] 1.1 `services/supabase_client.py` — シングルトン接続、環境変数読み込み、フォールバック判定
  - [ ] 1.2 テスト: 接続成功/失敗、フォールバック動作
  - _要件: 1.1, 1.4_

- [ ] 2. DBテーブル作成
  - [ ] 2.1 SQLマイグレーションファイル作成（`migrations/001_initial.sql`）
  - [ ] 2.2 Supabase Dashboard or CLI でテーブル作成
  - [ ] 2.3 RLSポリシー適用
  - _要件: 1.1_

- [ ] 3. SupabaseUserDataService
  - [ ] 3.1 `services/supabase_user_data_service.py` — UserDataServiceと同じインターフェース
  - [ ] 3.2 get_user_data: DBから読み込み、未登録時はデフォルト作成
  - [ ] 3.3 save_user_data: DBに書き込み（UPSERT）
  - [ ] 3.4 テスト: CRUD、デフォルト作成、フォールバック
  - _要件: 1.2, 1.3, 1.4_

- [ ] 4. データマイグレーションツール
  - [ ] 4.1 `scripts/migrate_json_to_supabase.py` — 既存JSONデータをDBに移行
  - [ ] 4.2 テスト: マイグレーション前後のデータ整合
  - _要件: 1.5_

- [ ] 5. 認証サービス
  - [ ] 5.1 `services/supabase_auth_service.py` — sign_up, sign_in, sign_out, get_current_user
  - [ ] 5.2 `routes/auth_routes.py` — /auth/register, /auth/login, /auth/logout, /auth/me
  - [ ] 5.3 `templates/auth.html` — 登録/ログインフォーム
  - [ ] 5.4 テスト: 登録、ログイン、ログアウト、ゲスト動作
  - _要件: 2.1, 2.2, 2.3, 2.4_

- [ ] 6. ゲストデータ紐づけ
  - [ ] 6.1 ゲストUUIDのデータをAuth UIDに移行するサービス
  - [ ] 6.2 テスト: 紐づけ前後のデータ整合
  - _要件: 2.5_

- [ ] 7. 会話履歴永続化
  - [ ] 7.1 `services/conversation_persistence_service.py` — 会話のDB保存/取得/検索
  - [ ] 7.2 既存ルートに保存フック追加（scenario_routes, chat_routes, watch_routes）
  - [ ] 7.3 `routes/history_routes.py` 拡張 — 検索・フィルタAPI
  - [ ] 7.4 テスト: 保存、取得、検索、エクスポート連携
  - _要件: 3.1, 3.2, 3.3, 3.4_

- [ ] 8. UserDataService切り替え
  - [ ] 8.1 環境変数でSupabase/JSONを切り替えるファクトリ関数
  - [ ] 8.2 全サービス・ルートのUserDataServiceをファクトリ経由に変更
  - [ ] 8.3 テスト: 切り替え動作確認
  - _要件: 1.4_

- [ ] 9. 最終チェックポイント
  - 全テストPASS
  - Supabase設定時: DBで動作
  - Supabase未設定時: JSONフォールバックで既存動作維持
