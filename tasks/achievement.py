"""
アチーブメント関連の非同期タスク

Celeryを使用してアチーブメントチェック処理を非同期化し、
メインのリクエスト/レスポンスサイクルから重い処理を分離
"""
import logging
from typing import List, Dict, Any, Optional
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError, Retry

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@shared_task(
    bind=True, 
    name='tasks.achievement.check_achievements',
    max_retries=3, 
    default_retry_delay=60,  # 60秒後にリトライ
    queue='analytics'  # analyticsキューを使用
)
def check_achievements_task(self, user_id: int, event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    アチーブメントチェックを非同期で実行するCeleryタスク
    
    Args:
        user_id: ユーザーID
        event_type: イベント種別 ('session_completed', 'scenario_completed', etc.)
        event_data: イベント関連データ
        
    Returns:
        Dict containing unlocked achievements and task status
        
    Raises:
        MaxRetriesExceededError: 最大リトライ回数を超えた場合
    """
    try:
        logger.info(f"Starting achievement check task for user {user_id}, event: {event_type}")
        
        # Flaskアプリケーションコンテキストが必要なため、ここで設定
        from app import app
        from services import AchievementService
        
        with app.app_context():
            # 既存のAchievementServiceを呼び出し
            unlocked_achievements = AchievementService.check_and_unlock_achievements(
                user_id=user_id,
                event_type=event_type,
                event_data=event_data
            )
            
            # 結果をログに記録
            achievement_count = len(unlocked_achievements)
            logger.info(f"Achievement check completed for user {user_id}: {achievement_count} achievements unlocked")
            
            # 結果を辞書形式で返す
            result = {
                'user_id': user_id,
                'event_type': event_type,
                'unlocked_count': achievement_count,
                'unlocked_achievements': [
                    {
                        'id': achievement.id,
                        'title': achievement.title,
                        'description': achievement.description,
                        'badge_icon': achievement.badge_icon
                    }
                    for achievement in unlocked_achievements
                ],
                'status': 'success'
            }
            
            # 新しいアチーブメントがある場合、将来の通知システム用にログ出力
            if achievement_count > 0:
                logger.info(f"New achievements unlocked for user {user_id}: {[a.title for a in unlocked_achievements]}")
                
                # TODO: 将来的にはWebSocketやSSEで即座にフロントエンドに通知
                # await notify_user_achievement(user_id, unlocked_achievements)
            
            return result
            
    except Exception as exc:
        # エラーの詳細をログに記録
        logger.error(f"Achievement check failed for user {user_id}: {str(exc)}", exc_info=True)
        
        # 一時的なエラー（DB接続など）の場合はリトライ
        if should_retry_error(exc):
            try:
                logger.warning(f"Retrying achievement check for user {user_id} (attempt {self.request.retries + 1})")
                raise self.retry(exc=exc, countdown=calculate_retry_delay(self.request.retries))
            except MaxRetriesExceededError:
                logger.error(f"Achievement check task failed permanently for user {user_id} after {self.max_retries} retries")
                # 永続的な失敗として記録
                return {
                    'user_id': user_id,
                    'event_type': event_type,
                    'status': 'failed',
                    'error': str(exc),
                    'retries_exhausted': True
                }
        else:
            # 永続的なエラー（データ不整合など）はリトライしない
            logger.error(f"Permanent error in achievement check for user {user_id}: {str(exc)}")
            return {
                'user_id': user_id,
                'event_type': event_type,
                'status': 'failed',
                'error': str(exc),
                'permanent_error': True
            }


@shared_task(
    name='tasks.achievement.bulk_check_achievements',
    queue='analytics'
)
def bulk_check_achievements_task(user_achievement_pairs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    複数ユーザーのアチーブメントを一括チェック（管理機能用）
    
    Args:
        user_achievement_pairs: [{'user_id': int, 'event_type': str, 'event_data': dict}, ...]
        
    Returns:
        Dict containing bulk operation results
    """
    try:
        logger.info(f"Starting bulk achievement check for {len(user_achievement_pairs)} users")
        
        from app import app
        
        results = []
        with app.app_context():
            for pair in user_achievement_pairs:
                # 個別のアチーブメントチェックタスクを呼び出し
                result = check_achievements_task.delay(
                    user_id=pair['user_id'],
                    event_type=pair['event_type'],
                    event_data=pair['event_data']
                )
                results.append({
                    'user_id': pair['user_id'],
                    'task_id': result.id,
                    'status': 'queued'
                })
        
        logger.info(f"Bulk achievement check queued {len(results)} tasks")
        return {
            'queued_tasks': len(results),
            'results': results,
            'status': 'success'
        }
        
    except Exception as exc:
        logger.error(f"Bulk achievement check failed: {str(exc)}", exc_info=True)
        return {
            'status': 'failed',
            'error': str(exc)
        }


def should_retry_error(exc: Exception) -> bool:
    """
    エラーがリトライ可能かどうかを判定
    
    Args:
        exc: 発生した例外
        
    Returns:
        bool: リトライすべきかどうか
    """
    # データベース接続エラーやネットワークエラーはリトライ
    retry_error_types = (
        'OperationalError',      # SQLAlchemy データベース接続エラー
        'TimeoutError',          # タイムアウトエラー
        'ConnectionError',       # 接続エラー
        'InterfaceError',        # データベースインターフェースエラー
    )
    
    error_name = type(exc).__name__
    return error_name in retry_error_types


def calculate_retry_delay(retry_count: int) -> int:
    """
    リトライ回数に基づいて遅延時間を計算（指数バックオフ）
    
    Args:
        retry_count: 現在のリトライ回数
        
    Returns:
        int: 遅延時間（秒）
    """
    import random
    
    # 指数バックオフ: 60, 120, 240秒 + ジッター
    base_delay = 60 * (2 ** retry_count)
    jitter = random.randint(0, 30)  # 0-30秒のランダムジッター
    
    return min(base_delay + jitter, 300)  # 最大5分