# Celery スケーラビリティガイド

## 概要

このガイドでは、タスクキューの分離とワーカーの最適化によるスケーラビリティ向上戦略について説明します。

## キュー設計

### キュー構成

1. **default** - 汎用タスク用（優先度: 5）
   - 一般的な処理
   - 中程度の処理時間

2. **llm** - LLM処理用（優先度: 3）
   - AIモデルを使用する重い処理
   - 長時間実行タスク

3. **analytics** - 分析タスク用（優先度: 7）
   - 強み分析
   - データ集計処理

4. **feedback** - フィードバック処理用（優先度: 5）
   - ユーザーフィードバック処理
   - 中程度の処理時間

5. **quick** - 高速処理用（優先度: 9）
   - 軽量タスク
   - 即座に完了すべき処理

## ワーカー設定

### ワーカー別の最適化

```yaml
# docker-compose.yml での設定例

# デフォルトワーカー
celery_worker_default:
  command: celery -A celery_app worker --concurrency=4 -Q default

# LLMワーカー（並行度低め、メモリ多め）
celery_worker_llm:
  command: celery -A celery_app worker --concurrency=2 -Q llm
  deploy:
    resources:
      limits:
        memory: 4G

# 分析ワーカー（中程度の並行度）
celery_worker_analytics:
  command: celery -A celery_app worker --concurrency=3 -Q analytics,feedback

# 高速処理ワーカー（並行度高め）
celery_worker_quick:
  command: celery -A celery_app worker --concurrency=8 -Q quick
```

## スケーリング戦略

### 水平スケーリング

```bash
# 特定のワーカーをスケールアウト
docker-compose up -d --scale celery_worker_llm=3
docker-compose up -d --scale celery_worker_quick=5
```

### 垂直スケーリング

```python
# celery_app.py での設定
celery.conf.update(
    # ワーカープロセスあたりのメモリ制限
    worker_max_memory_per_child=512000,  # 512MB
    
    # タスクごとのメモリ最適化
    task_annotations={
        'tasks.llm.*': {
            'max_memory_per_child': 1024000,  # 1GB
        },
        'tasks.quick.*': {
            'max_memory_per_child': 128000,   # 128MB
        }
    }
)
```

## パフォーマンスチューニング

### プリフェッチ設定

```python
# キュー別のプリフェッチ設定
CELERY_WORKER_PREFETCH_MULTIPLIER = {
    'llm': 1,      # 重いタスクは1つずつ
    'quick': 10,   # 軽いタスクは多めにプリフェッチ
    'default': 4,  # デフォルト
}
```

### タイムアウト設定

```python
# タスク別のタイムアウト
TASK_TIME_LIMITS = {
    'tasks.llm.*': 300,        # 5分
    'tasks.analytics.*': 180,  # 3分
    'tasks.quick.*': 30,       # 30秒
}
```

## モニタリング指標

### キュー別の監視項目

1. **Queue Length**
   - llm: < 50 (長時間タスクのため)
   - quick: < 1000 (短時間タスクのため)
   - analytics: < 100

2. **Worker Utilization**
   - llm: CPU 60-80% (I/O待機時間を考慮)
   - quick: CPU 80-90% (CPU集約的)
   - analytics: CPU 70-85%

3. **Task Latency**
   - llm: < 60秒
   - quick: < 1秒
   - analytics: < 10秒

## 自動スケーリング設定

### Kubernetes環境での例

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: celery-worker-llm-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: celery-worker-llm
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: External
    external:
      metric:
        name: celery_queue_length
        selector:
          matchLabels:
            queue: llm
      target:
        type: AverageValue
        averageValue: "30"
```

## 負荷分散戦略

### タスクルーティングの最適化

```python
# 動的ルーティング
def route_task(name, args, kwargs, options, task=None, **kw):
    """タスクを動的にルーティング"""
    if 'priority' in kwargs:
        if kwargs['priority'] >= 8:
            return {'queue': 'quick'}
        elif kwargs['priority'] <= 3:
            return {'queue': 'llm'}
    
    # デフォルトルーティング
    return None

celery.conf.task_routes = (route_task,)
```

## トラブルシューティング

### よくある問題

1. **特定のキューでタスクが滞留**
   - 該当ワーカーのスケールアウト
   - タスクの再ルーティング

2. **メモリ不足エラー**
   - ワーカーのメモリ制限を調整
   - タスクの分割処理を実装

3. **不均等な負荷分散**
   - ワーカーの並行度を調整
   - キューの優先度を見直し

## ベストプラクティス

1. **タスクの適切な分類**
   - 処理時間と重要度でキューを選択
   - 同じ特性のタスクは同じキューに

2. **ワーカーの専門化**
   - 各ワーカーは特定のキューに特化
   - リソース配分を最適化

3. **定期的な見直し**
   - メトリクスを継続的に監視
   - 負荷パターンに応じて調整