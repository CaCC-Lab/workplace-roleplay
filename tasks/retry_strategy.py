"""
Celeryタスクのリトライ戦略実装

指数バックオフ、部分レスポンス保存、進捗通知などの
高度なリトライ機能を提供
"""
import json
import logging
import random
import time
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass
from celery import Task
from celery.exceptions import Retry
import redis
from config.config import get_config
from .exceptions import (
    LLMError, TemporaryLLMError, PermanentLLMError,
    RateLimitError, NetworkError, ServiceUnavailableError,
    classify_error, get_error_metadata
)

logger = logging.getLogger(__name__)
config = get_config()

# Redis クライアント
redis_client = redis.Redis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    db=config.REDIS_DB,
    decode_responses=True
)


@dataclass
class RetryConfig:
    """リトライ設定のデータクラス"""
    max_retries: int
    base_delay: int  # 秒
    max_delay: int   # 秒
    backoff_factor: float
    jitter: bool = True


class RetryStrategy:
    """リトライ戦略の管理クラス"""
    
    # エラータイプ別のリトライ設定
    RETRY_CONFIGS = {
        RateLimitError: RetryConfig(
            max_retries=5,
            base_delay=60,
            max_delay=600,  # 10分
            backoff_factor=1.5
        ),
        NetworkError: RetryConfig(
            max_retries=4,
            base_delay=1,
            max_delay=30,
            backoff_factor=2.0
        ),
        ServiceUnavailableError: RetryConfig(
            max_retries=3,
            base_delay=30,
            max_delay=300,  # 5分
            backoff_factor=2.0
        ),
        TemporaryLLMError: RetryConfig(
            max_retries=3,
            base_delay=2,
            max_delay=300,  # 5分
            backoff_factor=2.0
        )
    }
    
    @classmethod
    def get_retry_config(cls, error: LLMError) -> RetryConfig:
        """エラータイプに応じたリトライ設定を取得"""
        for error_type, config in cls.RETRY_CONFIGS.items():
            if isinstance(error, error_type):
                return config
        
        # デフォルト設定
        return cls.RETRY_CONFIGS[TemporaryLLMError]
    
    @classmethod
    def calculate_delay(cls, retry_count: int, config: RetryConfig, error: LLMError) -> int:
        """
        リトライ遅延時間を計算
        
        Args:
            retry_count: 現在のリトライ回数
            config: リトライ設定
            error: 発生したエラー
            
        Returns:
            遅延時間（秒）
        """
        # エラー固有の推奨待機時間があれば使用
        if error.retry_after:
            base_delay = error.retry_after
        else:
            base_delay = config.base_delay
        
        # 指数バックオフ計算
        delay = base_delay * (config.backoff_factor ** retry_count)
        
        # 最大遅延時間でクランプ
        delay = min(delay, config.max_delay)
        
        # ジッター追加（同時リトライの分散）
        if config.jitter:
            jitter_range = delay * 0.1  # ±10%
            jitter = random.uniform(-jitter_range, jitter_range)
            delay = max(1, delay + jitter)
        
        return int(delay)
    
    @classmethod
    def should_retry(cls, error: LLMError, retry_count: int) -> Tuple[bool, str]:
        """
        リトライすべきかどうかを判定
        
        Args:
            error: 発生したエラー
            retry_count: 現在のリトライ回数
            
        Returns:
            (リトライすべきか, 理由)
        """
        # 永続的エラーはリトライしない
        if isinstance(error, PermanentLLMError):
            return False, f"Permanent error: {type(error).__name__}"
        
        # リトライ回数チェック
        config = cls.get_retry_config(error)
        if retry_count >= config.max_retries:
            return False, f"Max retries ({config.max_retries}) exceeded"
        
        # 一時的エラーはリトライ
        if isinstance(error, TemporaryLLMError):
            return True, f"Temporary error, retry {retry_count + 1}/{config.max_retries}"
        
        return False, "Unknown error type"


class PartialResponseManager:
    """部分レスポンスの管理クラス"""
    
    PARTIAL_RESPONSE_TTL = 3600  # 1時間
    
    @classmethod
    def save_partial_response(cls, task_id: str, chunks: List[Dict[str, Any]], metadata: Dict[str, Any] = None):
        """
        部分レスポンスをRedisに保存
        
        Args:
            task_id: タスクID
            chunks: 生成されたチャンクのリスト
            metadata: 追加のメタデータ
        """
        key = f"partial_response:{task_id}"
        
        data = {
            'chunks': chunks,
            'metadata': metadata or {},
            'saved_at': time.time(),
            'total_chunks': len(chunks)
        }
        
        try:
            redis_client.setex(
                key,
                cls.PARTIAL_RESPONSE_TTL,
                json.dumps(data, ensure_ascii=False)
            )
            logger.info(f"Saved partial response for task {task_id}: {len(chunks)} chunks")
        except Exception as e:
            logger.error(f"Failed to save partial response for task {task_id}: {e}")
    
    @classmethod
    def get_partial_response(cls, task_id: str) -> Optional[Dict[str, Any]]:
        """
        部分レスポンスをRedisから取得
        
        Args:
            task_id: タスクID
            
        Returns:
            部分レスポンスデータまたはNone
        """
        key = f"partial_response:{task_id}"
        
        try:
            data = redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Failed to get partial response for task {task_id}: {e}")
        
        return None
    
    @classmethod
    def delete_partial_response(cls, task_id: str):
        """部分レスポンスを削除"""
        key = f"partial_response:{task_id}"
        try:
            redis_client.delete(key)
            logger.debug(f"Deleted partial response for task {task_id}")
        except Exception as e:
            logger.error(f"Failed to delete partial response for task {task_id}: {e}")
    
    @classmethod
    def reconstruct_content(cls, chunks: List[Dict[str, Any]]) -> str:
        """チャンクから完全なコンテンツを再構築"""
        # チャンクをインデックス順にソート
        sorted_chunks = sorted(chunks, key=lambda x: x.get('chunk_index', 0))
        
        # コンテンツを結合
        content = ''.join(chunk.get('content', '') for chunk in sorted_chunks)
        
        return content


def retry_with_backoff(task_func: Callable):
    """
    高度なリトライ機能を提供するデコレータ
    
    Args:
        task_func: デコレートするタスク関数
        
    Returns:
        リトライ機能付きの関数
    """
    def wrapper(self: Task, *args, **kwargs):
        task_id = self.request.id
        retry_count = self.request.retries
        session_id = args[0] if args else kwargs.get('session_id', 'unknown')
        channel = f"stream:{session_id}"
        
        # 部分レスポンス管理
        partial_chunks = []
        partial_metadata = {}
        
        try:
            # オリジナル関数を実行
            result = task_func(self, *args, **kwargs)
            
            # 成功時は部分レスポンスを削除
            PartialResponseManager.delete_partial_response(task_id)
            
            return result
            
        except Exception as original_error:
            # エラーを分類
            classified_error = classify_error(original_error)
            error_metadata = get_error_metadata(classified_error)
            
            logger.warning(
                f"Task {task_id} failed with {type(classified_error).__name__}: {classified_error}",
                extra={
                    'task_id': task_id,
                    'retry_count': retry_count,
                    'error_metadata': error_metadata
                }
            )
            
            # リトライ判定
            should_retry, reason = RetryStrategy.should_retry(classified_error, retry_count)
            
            if not should_retry:
                # リトライしない場合、部分レスポンスがあれば送信
                partial_data = PartialResponseManager.get_partial_response(task_id)
                if partial_data:
                    partial_content = PartialResponseManager.reconstruct_content(
                        partial_data.get('chunks', [])
                    )
                    
                    # 部分レスポンスをクライアントに送信
                    redis_client.publish(channel, json.dumps({
                        'type': 'partial_complete',
                        'content': partial_content,
                        'error': str(classified_error),
                        'error_type': type(classified_error).__name__,
                        'partial': True,
                        'timestamp': time.time()
                    }))
                
                # 最終エラーを送信
                redis_client.publish(channel, json.dumps({
                    'type': 'error',
                    'error': str(classified_error),
                    'error_type': type(classified_error).__name__,
                    'retry_count': retry_count,
                    'reason': reason,
                    'timestamp': time.time()
                }))
                
                # 部分レスポンスを削除
                PartialResponseManager.delete_partial_response(task_id)
                
                raise classified_error
            
            # リトライする場合
            retry_config = RetryStrategy.get_retry_config(classified_error)
            delay = RetryStrategy.calculate_delay(retry_count, retry_config, classified_error)
            
            # リトライ通知をクライアントに送信
            redis_client.publish(channel, json.dumps({
                'type': 'retry',
                'error_type': type(classified_error).__name__,
                'retry_count': retry_count + 1,
                'max_retries': retry_config.max_retries,
                'retry_delay': delay,
                'estimated_retry_time': time.time() + delay,
                'error': str(classified_error),
                'reason': reason,
                'timestamp': time.time()
            }))
            
            # 部分レスポンスがあれば保存
            if hasattr(self, '_partial_chunks') and self._partial_chunks:
                PartialResponseManager.save_partial_response(
                    task_id,
                    self._partial_chunks,
                    {
                        'error_occurred': True,
                        'retry_count': retry_count,
                        'error_type': type(classified_error).__name__
                    }
                )
            
            # Celeryリトライを実行
            raise self.retry(
                countdown=delay,
                exc=classified_error,
                max_retries=retry_config.max_retries
            )
    
    return wrapper


def track_streaming_chunks(task_instance: Task, chunk_data: Dict[str, Any]):
    """
    ストリーミング中のチャンクを追跡
    
    Args:
        task_instance: タスクインスタンス
        chunk_data: チャンクデータ
    """
    if not hasattr(task_instance, '_partial_chunks'):
        task_instance._partial_chunks = []
    
    chunk_info = {
        'content': chunk_data.get('content', ''),
        'timestamp': chunk_data.get('timestamp', time.time()),
        'chunk_index': len(task_instance._partial_chunks)
    }
    
    # メタデータがあれば追加
    if chunk_data.get('speaker'):
        chunk_info['speaker'] = chunk_data['speaker']
    
    task_instance._partial_chunks.append(chunk_info)


def get_retry_status(task_id: str) -> Dict[str, Any]:
    """
    タスクのリトライ状態を取得
    
    Args:
        task_id: タスクID
        
    Returns:
        リトライ状態の辞書
    """
    partial_data = PartialResponseManager.get_partial_response(task_id)
    
    status = {
        'task_id': task_id,
        'has_partial_response': partial_data is not None,
        'partial_chunks_count': 0,
        'last_error_type': None,
        'retry_count': 0
    }
    
    if partial_data:
        status.update({
            'partial_chunks_count': partial_data.get('total_chunks', 0),
            'saved_at': partial_data.get('saved_at'),
            'metadata': partial_data.get('metadata', {})
        })
        
        metadata = partial_data.get('metadata', {})
        status['last_error_type'] = metadata.get('error_type')
        status['retry_count'] = metadata.get('retry_count', 0)
    
    return status