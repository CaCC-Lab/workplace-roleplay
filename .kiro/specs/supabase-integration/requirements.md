# Supabase統合 要件定義

## 要件 1: Supabase DB統合

**ユーザーストーリー:** 開発者として、JSONファイルベースの永続化をSupabase PostgreSQLに移行し、同時アクセス・検索・集計を可能にしたい。

### 受入基準

1. WHEN アプリケーションが起動した時 THEN Supabase PostgreSQLに接続する SHALL
2. WHEN ユーザーデータを保存する時 THEN Supabase DBのテーブルに永続化する SHALL
3. WHEN ユーザーデータを取得する時 THEN Supabase DBから読み込む SHALL
4. WHEN Supabase接続が失敗した時 THEN JSONファイルにフォールバックする SHALL
5. WHEN 既存のJSONデータがある時 THEN DBへマイグレーションできる SHALL

---

## 要件 2: Supabase Auth統合

**ユーザーストーリー:** ユーザーとして、メールアドレスとパスワードで登録・ログインし、端末を変えてもデータを引き継ぎたい。

### 受入基準

1. WHEN ユーザーが登録画面にアクセスした時 THEN メール/パスワードで登録できる SHALL
2. WHEN ユーザーがログインした時 THEN Supabase Auth でセッションを確立する SHALL
3. WHEN ログイン済みユーザーがアクセスした時 THEN Auth UIDでデータを紐づける SHALL
4. WHEN 未ログインユーザーがアクセスした時 THEN 従来のセッションUUIDで動作する SHALL（ゲスト利用）
5. WHEN ゲストユーザーがログインした時 THEN ゲスト期間のデータをアカウントに紐づけできる SHALL

---

## 要件 3: 会話履歴の永続化

**ユーザーストーリー:** ユーザーとして、過去の会話履歴がセッションをまたいで保存され、検索・振り返りができるようにしたい。

### 受入基準

1. WHEN シナリオ/雑談/観戦の会話が行われた時 THEN 会話履歴をDBに保存する SHALL
2. WHEN ユーザーが過去の会話を閲覧する時 THEN DB から会話履歴を取得できる SHALL
3. WHEN 会話履歴を検索する時 THEN モード・日付・キーワードでフィルタできる SHALL
4. WHEN 会話をエクスポートする時 THEN DB からCSV/JSON形式で出力できる SHALL

---

## 設計原則

- Supabase クライアントは環境変数（SUPABASE_URL, SUPABASE_KEY）で設定
- 既存の UserDataService インターフェースを維持（SupabaseUserDataService で差し替え）
- Row Level Security (RLS) でユーザーごとのデータ分離
- Supabase 未設定時はJSONファイルにフォールバック（後方互換）
