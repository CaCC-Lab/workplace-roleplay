"""
Celeryタスクパッケージ
"""
from celery_app import celery

# タスクを明示的にインポートしてCeleryに登録
from . import achievement
from . import llm
from . import strength_analysis

__all__ = ['celery', 'achievement', 'llm', 'strength_analysis']
