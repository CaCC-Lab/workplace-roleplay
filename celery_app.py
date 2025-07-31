"""
Celery アプリケーション設定
非同期タスク処理のためのCelery設定とタスク定義
"""
import os
from celery import Celery
from kombu import Queue
from config.config import get_config

# 設定の取得
config = get_config()

# Celeryインスタンスの作成
celery = Celery('workplace_roleplay')

# Redis URL構築（パスワード対応）
def build_redis_url():
    host = getattr(config, 'REDIS_HOST', 'localhost')
    port = getattr(config, 'REDIS_PORT', 6379)
    password = getattr(config, 'REDIS_PASSWORD', '')
    db = getattr(config, 'REDIS_DB', 0)
    
    if password:
        return f'redis://:{password}@{host}:{port}/{db}'
    else:
        return f'redis://{host}:{port}/{db}'

# Celery設定
default_redis_url = build_redis_url()
celery.conf.update(
    broker_url=os.getenv('CELERY_BROKER_URL', default_redis_url),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', default_redis_url),
    
    # タスク設定
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Tokyo',
    enable_utc=True,
    
    # タスクルーティング（優先度付き）
    task_routes={
        'tasks.llm.*': {'queue': 'llm', 'priority': 3},
        'tasks.feedback.*': {'queue': 'feedback', 'priority': 5},
        'tasks.analytics.*': {'queue': 'analytics', 'priority': 7},
        'tasks.strength_analysis.*': {'queue': 'analytics', 'priority': 6},
        'tasks.quick.*': {'queue': 'quick', 'priority': 9},  # 高速処理用
    },
    
    # キュー設定（優先度とルーティング設定）
    task_queues=(
        Queue('default', routing_key='task.#', max_priority=5),
        Queue('llm', routing_key='llm.#', max_priority=3),  # 重いタスク、低優先度
        Queue('feedback', routing_key='feedback.#', max_priority=5),
        Queue('analytics', routing_key='analytics.#', max_priority=7),
        Queue('quick', routing_key='quick.#', max_priority=9),  # 軽量タスク、高優先度
    ),
    
    # ワーカー設定
    worker_prefetch_multiplier=1,  # LLMタスクは重いので1つずつ処理
    worker_max_tasks_per_child=50,  # メモリリーク対策
    
    # タイムアウト設定
    task_soft_time_limit=120,  # ソフトタイムアウト: 2分
    task_time_limit=180,  # ハードタイムアウト: 3分
    
    # リトライ設定
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # 結果の保持期間
    result_expires=3600,  # 1時間
)

# タスクの自動検出
celery.autodiscover_tasks(['tasks'])