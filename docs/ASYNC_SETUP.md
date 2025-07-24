# 非同期処理セットアップガイド

このドキュメントでは、Celery + Redis Pub/Subを使用した非同期処理のセットアップ方法を説明します。

## 概要

本アプリケーションでは、LLM呼び出しのパフォーマンス改善のため、以下のアーキテクチャを採用しています：

- **Celery**: 非同期タスクキュー
- **Redis**: メッセージブローカー & Pub/Sub
- **SSE (Server-Sent Events)**: リアルタイムストリーミング

## セットアップ手順

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. Redisの起動

#### macOSの場合
```bash
brew services start redis
```

#### Linuxの場合
```bash
sudo systemctl start redis
```

#### Dockerの場合
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### 3. Celeryワーカーの起動

#### スクリプトを使用する場合（推奨）
```bash
./scripts/start_celery.sh
```

#### 手動で起動する場合
```bash
celery -A celery_app worker --loglevel=info --concurrency=4
```

#### Docker Composeを使用する場合
```bash
docker-compose up -d
```

## 非同期チャット機能の使用

### フロントエンド実装

新しい非同期チャットクライアントを使用します：

```javascript
// 非同期チャットクライアントの初期化
const asyncChatClient = new AsyncChatClient({
    baseUrl: '/api/async',
    onMessage: (data) => {
        // ストリーミングメッセージの処理
        console.log('Streaming:', data.content);
    },
    onComplete: (data) => {
        // 完了時の処理
        console.log('Complete:', data.content);
    },
    onError: (error) => {
        // エラー処理
        console.error('Error:', error);
    }
});

// メッセージの送信
await asyncChatClient.sendMessage('こんにちは', 'gemini/gemini-1.5-flash');
```

### APIエンドポイント

#### ストリーミングチャット
```
POST /api/async/chat/stream
Content-Type: application/json

{
    "message": "ユーザーのメッセージ",
    "model": "gemini/gemini-1.5-flash",
    "session_id": "optional-session-id"
}

Response: Server-Sent Events stream
```

#### フィードバック生成
```
POST /api/async/chat/feedback
Content-Type: application/json

{
    "session_id": "session-id",
    "model": "gemini/gemini-1.5-flash"
}

Response:
{
    "task_id": "celery-task-id",
    "status": "processing"
}
```

## アーキテクチャ詳細

### データフロー

1. **クライアント** → **Flask API** → **Celeryタスク**
2. **Celeryタスク** → **LLM API** → **Redis Pub/Sub**
3. **Redis Pub/Sub** → **SSE Bridge** → **クライアント**

### キュー構成

- `default`: 一般的なタスク
- `llm`: LLM呼び出しタスク
- `feedback`: フィードバック生成タスク
- `analytics`: 分析タスク

### タイムアウト設定

- ソフトタイムアウト: 2分
- ハードタイムアウト: 3分
- SSEタイムアウト: 5分

## モニタリング

### Flower（Celery監視ツール）

Flowerを使用してCeleryワーカーの状態を監視できます：

```bash
celery -A celery_app flower --port=5555
```

アクセスURL: http://localhost:5555

### ログ確認

```bash
# Celeryワーカーのログ
tail -f logs/celery/worker.log

# アプリケーションログ
tail -f logs/app.log
```

## トラブルシューティング

### Redis接続エラー

```bash
# Redis接続確認
redis-cli ping

# 応答があればOK
PONG
```

### Celeryワーカーが起動しない

```bash
# 既存プロセスの確認
pgrep -f "celery.*workplace_roleplay"

# プロセスの停止
pkill -f "celery.*workplace_roleplay"

# 再起動
./scripts/start_celery.sh
```

### SSEストリーミングが動作しない

1. ブラウザの開発者ツールでネットワークタブを確認
2. `text/event-stream`のContent-Typeが設定されているか確認
3. Nginxを使用している場合は、バッファリング無効化を確認：
   ```nginx
   proxy_buffering off;
   proxy_cache off;
   proxy_set_header X-Accel-Buffering no;
   ```

## パフォーマンスチューニング

### Celeryワーカー数の調整

```bash
# CPUコア数に応じて調整
celery -A celery_app worker --concurrency=8
```

### Redis接続プールの設定

```python
# config.pyで設定
REDIS_POOL_MAX_CONNECTIONS = 50
```

### タスクのプリフェッチ設定

```python
# celery_app.pyで設定
worker_prefetch_multiplier = 1  # LLMタスクは重いので1つずつ
```

## セキュリティ考慮事項

1. **Redis認証**: 本番環境では必ずパスワードを設定
2. **ネットワーク分離**: Redisは内部ネットワークのみアクセス可能に
3. **タスクの検証**: 受信したタスクデータは必ず検証
4. **レート制限**: 過度なタスク投入を防ぐ仕組みを実装

## 今後の拡張計画

1. **バッチ処理**: 複数のLLM呼び出しをまとめて処理
2. **優先度キュー**: 重要なタスクを優先的に処理
3. **結果キャッシュ**: 同じ入力に対する結果をキャッシュ
4. **分散処理**: 複数のワーカーノードでの処理