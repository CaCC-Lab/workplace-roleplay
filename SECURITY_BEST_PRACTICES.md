# セキュリティベストプラクティスガイド

このドキュメントは、Workplace Roleplayアプリケーションのセキュリティを確保するためのベストプラクティスをまとめたものです。

## 1. 環境変数の管理

### 必須の環境変数

以下の環境変数は必ず設定してください：

- `FLASK_SECRET_KEY`: セッション暗号化用の秘密鍵（最小32文字、本番環境では64文字推奨）
- `GOOGLE_API_KEY`: Google Gemini APIキー（本番環境では必須）

### 秘密鍵の生成

安全な秘密鍵の生成には、提供されているスクリプトを使用してください：

```bash
# 開発環境用（32文字）
python scripts/generate_secret_key.py

# 本番環境用（64文字）
python scripts/generate_secret_key.py --length 64

# 既存のキーの強度チェック
python scripts/generate_secret_key.py --check "your-existing-key"
```

### 環境変数のセキュリティ

1. **`.env`ファイルの保護**
   - `.env`ファイルは`.gitignore`に含めて、GitHubにコミットしない
   - ファイルの権限を制限する：`chmod 600 .env`

2. **本番環境での管理**
   - 環境変数は環境変数管理サービス（AWS Secrets Manager、HashiCorp Vault等）を使用
   - CI/CDパイプラインでは、暗号化されたシークレットを使用

## 2. 認証情報の取り扱い

### 禁止事項

以下のような脆弱なパターンは自動的に検出・拒否されます：

- デフォルト値のハードコーディング
- 予測可能なパターン（`password123`、`secret123`、`admin`等）
- 単純な繰り返しパターン
- 数字のみ、または文字種が少ない鍵

### パスワードポリシー

データベースパスワードには以下の要件を適用してください：

- 最小16文字以上
- 大文字・小文字・数字・特殊文字を含む
- 定期的な更新（90日ごと）

## 3. セッション管理

### セッションセキュリティ設定

```python
# config/config.py での設定例
SESSION_COOKIE_SECURE = True  # HTTPS環境でのみ
SESSION_COOKIE_HTTPONLY = True  # JavaScriptからのアクセスを防止
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF攻撃を防止
```

### セッションタイムアウト

- デフォルト：30分
- 機密性の高い操作後は即座にセッションを再生成

## 4. API セキュリティ

### レート制限

API エンドポイントには適切なレート制限を設定：

```python
# 例：1分あたり60リクエストまで
from flask_limiter import Limiter
limiter = Limiter(
    app,
    key_func=lambda: get_remote_address(),
    default_limits=["60 per minute"]
)
```

### 入力検証

すべてのユーザー入力は検証・サニタイズ：

- XSS対策：HTMLエスケープ
- SQLインジェクション対策：パラメータ化クエリ
- コマンドインジェクション対策：シェルコマンドの使用を避ける

## 5. 本番環境のチェックリスト

### デプロイ前の確認事項

- [ ] すべての環境変数が適切に設定されている
- [ ] デバッグモードが無効になっている（`FLASK_DEBUG=False`）
- [ ] 強力な秘密鍵が設定されている（64文字以上）
- [ ] HTTPS が有効になっている
- [ ] セキュリティヘッダーが設定されている
- [ ] エラーメッセージが一般化されている（詳細なエラー情報を表示しない）
- [ ] ログに機密情報が含まれていない

### 定期的なセキュリティ監査

1. **依存関係の更新**
   ```bash
   pip list --outdated
   pip-audit  # 脆弱性のチェック
   ```

2. **秘密鍵のローテーション**
   - 3ヶ月ごとに秘密鍵を更新
   - 侵害の疑いがある場合は即座に更新

3. **アクセスログの監視**
   - 異常なアクセスパターンの検出
   - 失敗した認証試行の監視

## 6. 開発環境のセキュリティ

開発環境でも以下のセキュリティ対策を実施：

1. **ローカル環境の保護**
   - 開発用の秘密鍵も適切に生成する
   - テストデータに実際の個人情報を使用しない

2. **コードレビュー**
   - セキュリティの観点からコードレビューを実施
   - 自動化されたセキュリティスキャンの導入

## 7. インシデント対応

セキュリティインシデントが発生した場合：

1. **即座の対応**
   - 影響を受けたシステムの隔離
   - すべての秘密鍵とトークンの無効化・再生成

2. **調査と報告**
   - インシデントの範囲と影響の特定
   - 必要に応じて関係者への通知

3. **再発防止**
   - 根本原因の分析
   - セキュリティ対策の強化

## 8. 参考資料

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Guide](https://flask.palletsprojects.com/en/2.3.x/security/)
- [Python Security Best Practices](https://python.org/dev/security/)