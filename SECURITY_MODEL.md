# workplace-roleplay の脅威モデル

## 対象と根拠

対象は `CaCC-Lab/workplace-roleplay`。利用者が AI と職場での会話を練習し、 フィードバックや学習履歴を振り返る Flask アプリである。コード・構成ファイルを静的に確認した。参照したアプリのコミットは `f58ff26`。既存の [SECURITY.md](https://github.com/CaCC-Lab/workplace-roleplay/blob/f58ff26/SECURITY.md) が示すセッション隔離、入力検証、出力エスケープ、CSRF 対策、本番の秘密鍵管理を、以下の境界と実装に対応づけた。

## コンポーネントと信頼境界

| コンポーネント | 役割と境界 | 主なコード・設定 |
| --- | --- | --- |
| Web UI | 利用者のブラウザ。会話入力、AI 出力、保存内容を表示し、同一オリジンの API・SSE に接続する。 | `templates/`、`static/js/` |
| Flask API | Nginx から HTTP を受け、会話・評価・観戦・エクスポート・学習進捗を処理する。外部入力とサーバー側の権限の境界。 | `app.py`、`core/`、`routes/`、各ドメインサービス |
| 認証・セッション | ブラウザの Cookie と Flask-Session、Redis またはファイルによるサーバー側状態を管理する。Supabase Auth のトークンとアプリのセッション UUID は別の識別子。 | `routes/auth_routes.py`、`services/supabase_auth_service.py`、`services/session_service.py`、`core/extensions.py`、`utils/redis_manager.py` |
| 学習データストア | Flask から利用者ごとの進捗・履歴を読み書きする。構成により Supabase/PostgreSQL とローカル保存を使う。 | `services/supabase_client.py`、`services/user_data_factory.py`、`services/supabase_user_data_service.py`、`services/user_data_service.py`、`services/conversation_persistence_service.py`、`migrations/` |
| AI プロバイダー連携 | 会話・評価の入力が Flask から Google Gemini または Ollama Cloud へ渡る。返されたテキストや構造化出力は外部入力として扱う。画像・音声生成にも外部サービスを使う経路がある。 | `services/llm_service.py`、`services/feedback_service.py`、`services/model_selector.py`、`routes/image_routes.py`、`routes/tts_routes.py` |
| デプロイ・公開境界 | リポジトリは、GitHub Actions から SSH で Azure VM に配備し、Nginx で TLS を終端し、systemd で Flask を起動する構成を示す。 | `.github/workflows/deploy-production.yml`、`deployment/nginx-site.conf`、`deployment/workplace-roleplay.service`、`DEPLOYMENT.md` |

## 入口と想定する攻撃者

- **利用者が確認**。本番は誰でも匿名で利用できる。メール登録・ログインは本番の運用で使用しない。メール用 Blueprint の経路はコードに残っており、現行環境でアクセスが遮断されているかは未確認。
- 入口は公開ページ、匿名サインイン、会話・シナリオ・観戦の API と SSE、履歴・進捗・エクスポート、およびヘルスチェック・メトリクス。状態やデータの利用可否はルートごとのセッション、構成、権限に依存する。
- 想定する攻撃者はインターネットから到達する未認証者、匿名セッションを取得した利用者、他の利用者のブラウザに外部コンテンツを表示させられる者。CI 実行権限や外部サービスの認証情報を得た場合の影響も考慮する。

## 保護対象

- **利用者が最重要と指定**。利用者間で分離される会話履歴・フィードバック、および Supabase と AI サービスの認証情報。両方を最重要として扱う。
- 学習進捗・スコア・エクスポートデータ、匿名識別子、セッショントークン、Flask 署名鍵、デプロイ資格情報、サービス可用性および AI 使用枠も保護する。匿名識別子を使う環境でも、自由記述の会話には実際の人物や職場に関する情報が入り得る。

## セキュリティ上の不変条件

| 領域 | 守る条件と実装上の境界 |
| --- | --- |
| 認証・セッション（CWE-287、CWE-384） | `routes/auth_routes.py` がサーバー側セッションに保存した Supabase トークンは `SupabaseAuthService.get_current_user()` で検証する。Supabase Auth の本人性と `SessionService.get_user_id()` が返すアプリ内 UUID は別に検証する。セッション開始・終了時の ID 更新や状態破棄、および Redis とファイルの両方での Cookie 保護と期限を確認する。 |
| 利用者間の認可（CWE-639、CWE-862） | 履歴、学習進捗、エクスポートの操作ごとに、サーバー側のセッションから所有者を決め、読み書きの条件にその所有者を含める。`SupabaseUserDataService` と `ConversationPersistenceService` のクエリにこの条件を保つ。service role での操作には Flask 側の認可が必要で、直接アクセスへの RLS は `migrations/003_enable_rls_server_only.sql` と `004_harden_gamification_rls.sql` が示す分離方針に従う。 |
| SQL・テンプレート注入（CWE-89、CWE-1336） | 検索値は Supabase/PostgREST のクエリビルダーにデータとして渡し、検索式や SQL 文の組み立てと分離する。Flask の `render_template()` は固定の Jinja テンプレートを使い、利用者入力や AI 出力をテンプレート本体として評価する `render_template_string()` への受け渡しを避ける。 |
| XSS（CWE-79） | `core/extensions.py` が有効にする Jinja の自動エスケープを維持する。会話、評価、SSE 出力のブラウザ表示は `textContent` または文脈に合うサニタイズを使う。`\|safe` や `innerHTML` を使う表示処理は入力元と安全化を確認する。CSP は補助防御であり、`utils/csp_middleware.py` の初期化は、確認した `create_app()` の経路では確認できなかった。 |
| CSRF（CWE-352） | Cookie を使う状態変更は `utils/security.py` の `CSRFToken.validate()` 相当の検証を通す。`core/middleware.py` の保護対象は POST の明示リストに限られるため、新規ルート・既存ルート・HTTP メソッドを含めた適用範囲を点検する。 |
| 外部通信・AI 入出力（CWE-918） | `LLMService` の Ollama 向け接続先は管理構成から取得する。モデルやシナリオの選択値が送信先 URL・内部ホストを決めないようにする。評価プロンプトには必要な会話だけを渡し、AI の返答はテキストまたは検証済みデータとして扱う。 |
| ファイル・エクスポート（CWE-22、CWE-1236） | ファイル応答は `routes/main_routes.py` や `routes/docs_routes.py` のように固定ディレクトリと固定名で配信する。`scenarios/__init__.py` はリポジトリの YAML を `yaml.safe_load()` で読む。`ExportService.export_conversations_csv()` では表計算ソフトで数式として読まれない形に未信頼のセルを無害化する。確認した実装は CSV の構文上の引用処理のみを行う。 |
| 認証情報・ログ（CWE-798、CWE-532） | 本番設定は `ProductionConfig.require_secret_key()` の検証を通し、署名鍵、Supabase service role、外部 API キー、SSH 鍵の値はサーバー側または CI の管理範囲に限定する。ログ、エラー応答、成果物、バックアップでは、`SecurityUtils.get_safe_error_message()` などで秘密と会話の露出を防ぐ。 |
| 可用性・CI（CWE-770、CWE-494） | 会話生成や画像・音声 API に入力上限、同時実行数、利用量の制御を適用する。Nginx のレート制限設定と一部ルートの `RateLimiter.rate_limit()` は適用範囲を確認する。本番デプロイのワークフローは変更できる権限を絞り、SSH 接続先の真正性、GitHub Actions の依存、実行成果物とバックアップを保護する。 |

## インフラ資料と未確認事項

- 参考資料 [CaCC-Lab/azure-vm-setup](https://github.com/CaCC-Lab/azure-vm-setup/tree/ca790ef) の `setup.sh` は別のアプリ `roleplay-chatbot-wepapp` を取得し、`roleplay-gunicorn.service` と Nginx の 8000 番ポート向け設定を作る。workplace-roleplay 側のワークフロー、サービス名、起動コマンド、Nginx の 5000 番ポート向け設定とは異なる。アプリ側から同セットアップを参照する記述は確認できず、過去の環境構築資料として参照した。
- workplace-roleplay 自体にも、`scripts/workplace-app.service` と `scripts/nginx-workplace.conf` による別の Gunicorn 構成がある。2025 年 8 月のコミットで追加され、`deployment/` の systemd ユニットと配備先・起動方法が異なる。どちらが現行本番で有効かは未確認。
- 現行本番への適用状況は未確認。稼働中のプロセス、実際の待受・プロキシ・ネットワーク境界、Supabase マイグレーションと Auth 設定、セッションと AI プロバイダーの設定、保存期間はリポジトリから確定できない。本番環境へのアクセスや秘密情報の取得は行わず、利用者から指定された読み取り専用の範囲で調べた。
- 利用者が承認済みリスクとして指定した項目はない。補助リポジトリは本番構成との関係を確認するための資料であり、今回のコードスキャン対象は `CaCC-Lab/workplace-roleplay`。
