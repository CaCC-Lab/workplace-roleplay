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

## 要件 2: 匿名サインイン

**ユーザーストーリー:** ユーザーとして、個人情報を入力せずワンクリックで利用開始し、同じブラウザ内でデータを継続利用したい。

### 受入基準

1. WHEN ユーザーが初めてアクセスした時 THEN ワンクリックで匿名ユーザーを作成できる SHALL
2. WHEN 匿名サインインした時 THEN Supabase Auth に匿名ユーザーIDが作成される SHALL（PIIなし）
3. WHEN 匿名ユーザーがアクセスした時 THEN authenticated ロールでDBにアクセスする SHALL
4. WHEN 同一ブラウザで再アクセスした時 THEN 保存済みセッションで同じユーザーとして継続する SHALL
5. WHEN サインアウト・ブラウザデータ削除・別端末の場合 THEN 同じ匿名ユーザーには原則復旧不可とする SHALL
6. WHEN 匿名ユーザーが望む場合 THEN 後からメール/OAuthを後付けでリンクできる SHALL（将来拡張）
7. WHEN Supabase未設定時 THEN 従来のセッションUUIDで動作する SHALL（ゲスト利用フォールバック）

---

## 要件 3: 会話履歴の永続化

**ユーザーストーリー:** ユーザーとして、過去の会話履歴がセッションをまたいで保存され、検索・振り返りができるようにしたい。

### 受入基準

1. WHEN シナリオ/雑談/観戦の会話が行われた時 THEN 会話履歴をDBに保存する SHALL
2. WHEN ユーザーが過去の会話を閲覧する時 THEN DB から会話履歴を取得できる SHALL
3. WHEN 会話履歴を検索する時 THEN モード・日付・キーワードでフィルタできる SHALL
4. WHEN 会話をエクスポートする時 THEN DB からCSV/JSON形式で出力できる SHALL

---

## 要件 4: アクセス制御

### 受入基準

1. WHEN 匿名ユーザーがDBにアクセスする時 THEN RLSで自分のデータのみアクセスできる SHALL
2. WHEN RLSポリシーを定義する時 THEN JWTの is_anonymous クレームで匿名/恒久ユーザーを区別する SHALL

---

## 要件 5: 不正対策・保守

### 受入基準

1. WHEN 匿名サインインのリクエストが来た時 THEN IPあたり1時間30回のレート制限を適用する SHALL（Supabase既定）
2. WHEN 本番環境で運用する時 THEN Cloudflare Turnstile によるCAPTCHA保護を適用する SHOULD
3. WHEN 匿名ユーザーが90日間非アクティブの場合 THEN 定期削除の対象とする SHALL

---

## 設計原則

- 個人情報（PII）を一切要求しない
- Supabase クライアントは環境変数（SUPABASE_URL, SUPABASE_KEY）で設定
- 匿名ユーザーは auth.users に authenticated ロールで作成される
- RLS で is_anonymous を明示的に判定
- Supabase 未設定時はJSONファイルにフォールバック（後方互換）
- 同一ブラウザの保存済みセッションで継続（localStorage）
- サインアウト・ブラウザデータ削除・別端末では原則復旧不可
