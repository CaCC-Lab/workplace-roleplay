# Azure Web App 設定ガイド

## 環境変数の設定

Azure Portalで以下の環境変数（アプリケーション設定）を設定してください：

```
# 基本設定
FLASK_SECRET_KEY=<ランダムな長い文字列>
OPENAI_API_KEY=<OpenAI APIキー>
GOOGLE_API_KEY=<Google Gemini APIキー>

# セッション設定（オプション1: ファイルシステム）
SESSION_TYPE=filesystem
SESSION_FILE_DIR=/home/site/wwwroot/sessions

# セッション設定（オプション2: Redisを使用）
# SESSION_TYPE=redis
# REDIS_HOST=<Redisホスト名>
# REDIS_PORT=6379
# REDIS_PASSWORD=<Redisパスワード>
# REDIS_DB=0
```

## フォルダ作成

SSHでAzure Web Appに接続し、セッションフォルダを作成してください：

```bash
mkdir -p /home/site/wwwroot/sessions
chmod 777 /home/site/wwwroot/sessions
```

## Redis接続の設定（推奨）

長期運用する場合は、Azure Cache for Redisを使用してセッションを保存することをお勧めします：

1. Azure Portalで「Azure Cache for Redis」を作成
2. 接続情報を取得してアプリケーション設定に設定
3. `SESSION_TYPE=redis`に変更

## アプリケーション設定へのアクセス方法

1. Azure Portalにログイン
2. Web Appリソースに移動
3. 左側メニューの「構成」をクリック
4. 「アプリケーション設定」タブで環境変数を追加/編集
5. 変更後は「保存」をクリックして、アプリを再起動 