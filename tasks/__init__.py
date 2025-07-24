"""
Celeryタスクパッケージ
"""
from celery_app import celery

# タスクを明示的にインポートしてCeleryに登録
from . import llm

__all__ = ['celery', 'llm']