# Celery モニタリングガイド

## 概要

このガイドでは、Flowerを使用したCeleryタスクのモニタリング戦略について説明します。

## Flowerの起動方法

### Docker Composeを使用（推奨）

```bash
# すべてのサービスを起動
docker-compose up -d

# Flowerのみを起動
docker-compose up -d flower
```

FlowerのWebインターフェースは [http://localhost:5555](http://localhost:5555) でアクセスできます。

### スタンドアロンで起動

```bash
celery -A celery_app flower --port=5555
```

## 主要なモニタリング項目

### 1. タスク監視

- **Tasks**: 実行されたタスクの一覧と状態
- **Success/Failure Rate**: タスクの成功率・失敗率
- **Average Runtime**: タスクの平均実行時間

### 2. ワーカー監視

- **Workers**: アクティブなワーカーの一覧
- **Pool**: 各ワーカーのプロセス/スレッド数
- **Load Average**: ワーカーの負荷状況

### 3. キュー監視

- **Queues**: 各キューの長さと処理待ちタスク数
- **Routing**: タスクのルーティング状況

## アラート設定

### Celeryイベントの監視

```python
# celery_monitoring.py
from celery import Celery
from celery.events import EventReceiver

app = Celery('workplace_roleplay')

def monitor_failed_tasks():
    """失敗したタスクを監視してアラートを送信"""
    def on_task_failed(event):
        task_name = event.get('name', 'Unknown')
        task_id = event.get('uuid', 'Unknown')
        exception = event.get('exception', 'Unknown error')
        
        # ログ出力
        logger.error(f"Task failed: {task_name} ({task_id}) - {exception}")
        
        # 必要に応じてSlack/Email通知を追加
        # send_alert_notification(task_name, task_id, exception)
    
    with app.connection() as connection:
        recv = EventReceiver(connection, handlers={
            'task-failed': on_task_failed,
        })
        recv.capture(limit=None, timeout=None, wakeup=True)
```

## パフォーマンス最適化の指標

### 重要なメトリクス

1. **Task Latency**: タスクがキューに入ってから実行開始までの時間
2. **Queue Length**: 各キューの待機タスク数
3. **Worker Utilization**: ワーカーのCPU/メモリ使用率
4. **Retry Rate**: リトライが発生する頻度

### 推奨閾値

- Task Latency: < 5秒（通常タスク）、< 30秒（重いタスク）
- Queue Length: < 100（通常時）、< 1000（ピーク時）
- Worker Utilization: CPU < 80%、Memory < 70%
- Retry Rate: < 5%

## Prometheus/Grafana連携（上級編）

### Celery Exporterの設定

```yaml
# docker-compose.yml追加設定
celery_exporter:
  image: ovalmoney/celery-exporter
  ports:
    - "9540:9540"
  environment:
    - CELERY_BROKER_URL=redis://redis:6379/0
  depends_on:
    - redis
```

### Grafanaダッシュボード

Celery用の公式Grafanaダッシュボード（ID: 11497）をインポートして使用。

## トラブルシューティング

### よくある問題と対処法

1. **タスクが実行されない**
   - Flower でワーカーの状態を確認
   - キューのルーティング設定を確認

2. **メモリリーク**
   - Flower でメモリ使用量の推移を監視
   - タスクのメモリプロファイリングを実施

3. **高レイテンシ**
   - キューの長さを確認
   - ワーカー数の調整を検討

## セキュリティ設定

### Flower認証の有効化

```python
# flower_config.py
from flower.utils.broker import Broker

# Basic認証の設定
flower_basic_auth = ['admin:secure_password']

# OAuth2認証（Google）
oauth2_redirect_uri = 'http://localhost:5555/login'
oauth2_provider = 'google'
oauth2_key = 'your-client-id'
oauth2_secret = 'your-client-secret'
```

### アクセス制限

本番環境では、Flowerへのアクセスを内部ネットワークのみに制限することを推奨。

```nginx
# nginx設定例
location /flower/ {
    proxy_pass http://localhost:5555;
    proxy_set_header Host $host;
    allow 10.0.0.0/8;  # 内部ネットワーク
    deny all;
}
```