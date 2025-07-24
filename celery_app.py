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

# Celery設定
celery.conf.update(
    broker_url=os.getenv('CELERY_BROKER_URL', f'redis://{config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB}'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', f'redis://{config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB}'),
    
    # タスク設定
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Tokyo',
    enable_utc=True,
    
    # タスクルーティング
    task_routes={
        'tasks.llm.*': {'queue': 'llm'},
        'tasks.feedback.*': {'queue': 'feedback'},
        'tasks.analytics.*': {'queue': 'analytics'},
    },
    
    # キュー設定
    task_queues=(
        Queue('default', routing_key='task.#'),
        Queue('llm', routing_key='llm.#'),
        Queue('feedback', routing_key='feedback.#'),
        Queue('analytics', routing_key='analytics.#'),
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