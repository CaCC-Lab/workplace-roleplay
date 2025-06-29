# 環境変数設定ガイド

このドキュメントでは、workplace-roleplayアプリケーションで使用される環境変数について説明します。

## 必須環境変数

### GOOGLE_API_KEY
- **説明**: Google Gemini APIを使用するためのAPIキー
- **必須**: はい（本番環境）
- **例**: `AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ`
- **取得方法**: [Google AI Studio](https://aistudio.google.com/)でアカウントを作成し、APIキーを発行

## オプション環境変数

### Flask設定

#### FLASK_ENV
- **説明**: Flaskの実行環境
- **デフォルト**: `development`
- **値**: `development`, `production`, `testing`

#### FLASK_SECRET_KEY
- **説明**: セッション管理用の秘密鍵
- **デフォルト**: `default-secret-key-change-in-production`
- **推奨**: 本番環境では必ず変更してください
- **生成方法**: `python -c "import secrets; print(secrets.token_hex(32))"`

#### FLASK_DEBUG
- **説明**: デバッグモードの有効/無効
- **デフォルト**: `false`（開発環境では自動的に`true`）
- **値**: `true`, `false`

### APIとモデル設定

#### DEFAULT_TEMPERATURE
- **説明**: LLMの創造性パラメータ（0-1）
- **デフォルト**: `0.7`
- **範囲**: `0.0`（決定的）～`1.0`（創造的）

#### DEFAULT_MODEL
- **説明**: デフォルトで使用するGeminiモデル
- **デフォルト**: `gemini/gemini-1.5-flash`
- **値**: 
  - `gemini/gemini-1.5-pro`
  - `gemini/gemini-1.5-flash`

### セッション設定

#### SESSION_TYPE
- **説明**: セッションの保存方式
- **デフォルト**: `filesystem`
- **値**: `filesystem`, `redis`

#### SESSION_LIFETIME_MINUTES
- **説明**: セッションの有効期限（分）
- **デフォルト**: `30`

#### SESSION_FILE_DIR
- **説明**: filesystemセッション使用時のファイル保存先
- **デフォルト**: Flaskのデフォルトディレクトリ
- **例**: `/tmp/flask_sessions`

### Redis設定（SESSION_TYPE=redisの場合）

#### REDIS_HOST
- **説明**: Redisサーバーのホスト名
- **デフォルト**: `localhost`

#### REDIS_PORT
- **説明**: Redisサーバーのポート番号
- **デフォルト**: `6379`

#### REDIS_PASSWORD
- **説明**: Redisサーバーのパスワード
- **デフォルト**: （空文字）

#### REDIS_DB
- **説明**: 使用するRedisデータベース番号
- **デフォルト**: `0`

### サーバー設定

#### PORT
- **説明**: アプリケーションのリスニングポート
- **デフォルト**: `5000`
- **注意**: デフォルトは5000ですが、app.pyで5001にハードコードされていたため、移行時は5000に変更されます

#### HOST
- **説明**: アプリケーションのバインドアドレス
- **デフォルト**: `0.0.0.0`

#### HOT_RELOAD
- **説明**: ファイル変更時の自動リロード
- **デフォルト**: `false`（開発環境では自動的に`true`）

### ログ設定

#### LOG_LEVEL
- **説明**: ログの出力レベル
- **デフォルト**: `INFO`
- **値**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

#### LOG_FORMAT
- **説明**: ログの出力形式
- **デフォルト**: `json`
- **値**: `json`, `text`

### その他の設定

#### ENABLE_DEBUG
- **説明**: 追加のデバッグ機能を有効化
- **デフォルト**: `false`

#### WTF_CSRF_ENABLED
- **説明**: CSRF保護の有効/無効
- **デフォルト**: `true`
- **注意**: テスト環境では自動的に`false`に設定されます

#### SECURE_COOKIES
- **説明**: セキュアなクッキーの使用
- **デフォルト**: `false`（本番環境では自動的に`true`）

## 環境別の設定

### 開発環境（FLASK_ENV=development）

```bash
# 最小限の設定
export GOOGLE_API_KEY="your-api-key-here"
export FLASK_ENV="development"
```

### 本番環境（FLASK_ENV=production）

```bash
# 必須設定
export GOOGLE_API_KEY="your-production-api-key"
export FLASK_SECRET_KEY="your-secure-secret-key"
export FLASK_ENV="production"

# 推奨設定
export SESSION_TYPE="redis"
export REDIS_HOST="your-redis-host"
export REDIS_PASSWORD="your-redis-password"
export LOG_LEVEL="WARNING"
export SECURE_COOKIES="true"
```

### テスト環境（FLASK_ENV=testing）

```bash
# テスト用設定
export FLASK_ENV="testing"
# GOOGLE_API_KEYは自動的にダミー値が使用されます
```

## .envファイルの使用

環境変数は`.env`ファイルに記述することもできます：

```bash
# .env
GOOGLE_API_KEY=AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ
FLASK_ENV=development
FLASK_SECRET_KEY=dev-secret-key
DEFAULT_TEMPERATURE=0.8
SESSION_TYPE=filesystem
LOG_LEVEL=DEBUG
```

## 設定の確認

アプリケーション起動時に現在の設定を確認できます（機密情報はマスクされます）：

```python
from config import get_config

config = get_config()
print(config.to_dict(mask_secrets=True))
```

## 移行時の注意点

1. **ポート番号の変更**: 以前は5001番ポートを使用していましたが、設定のデフォルトは5000番です。必要に応じて`PORT=5001`を設定してください。

2. **APIキーの複数設定**: 以前の実装では`GOOGLE_API_KEY_2`～`GOOGLE_API_KEY_4`もサポートしていました。新しい設定システムでは、これらは`extra`フィールドとして保持されますが、推奨されません。

3. **セッション設定**: `SESSION_LIFETIME_MINUTES`は分単位で設定しますが、内部的には秒に変換されます。