"""
強み分析関連の非同期タスク

Celeryを使用して会話履歴の強み分析処理を非同期化し、
メインのリクエスト/レスポンスサイクルから重い処理を分離
"""
import logging
from typing import List, Dict, Any
from celery import shared_task, current_task
from .llm import LLMTask
from celery_app import celery
from .retry_strategy import retry_with_backoff

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@celery.task(
    bind=True,
    base=LLMTask,
    name='tasks.strength_analysis.analyze_conversation_strengths',
    max_retries=3,
    default_retry_delay=60,  # 60秒後にリトライ
    retry_backoff=True,  # 指数的バックオフを有効化
    retry_jitter=True,   # ジッターを有効化
    retry_backoff_max=600,  # 最大バックオフ時間（10分）
    queue='analytics'  # analyticsキューを使用
)
@retry_with_backoff
def analyze_conversation_strengths_task(self, user_id: int, conversation_history: List[Dict[str, str]], session_type: str = 'chat') -> Dict[str, Any]:
    """
    会話履歴から強み分析を非同期で実行するCeleryタスク
    
    このタスクは、ユーザーの会話履歴を分析し、コミュニケーションスキルの
    強みを数値化します。LLM（Gemini）を使用して分析を行い、結果を構造化
    されたデータとして返します。
    
    Args:
        user_id (int): 分析対象のユーザーID
        conversation_history (List[Dict[str, str]]): 会話履歴のリスト。
            各要素は {'role': 'user'|'assistant', 'content': str} の形式
        session_type (str, optional): セッション種別。'chat' または 'scenario'。
            デフォルトは 'chat'
        
    Returns:
        Dict[str, Any]: 分析結果を含む辞書。以下のキーを含む：
            - success (bool): 処理の成功/失敗
            - user_id (int): ユーザーID
            - session_type (str): セッション種別
            - analysis (dict): 分析結果（scores, top_strengths, encouragement_messages）
            - task_id (str): タスクID
            - error (str): エラーメッセージ（エラー時のみ）
            
    Raises:
        各種例外はLLMTaskとretry_with_backoffデコレータによって処理される
    """
    try:
        # タスクIDとメタデータを記録
        task_id = current_task.request.id
        logger.info(f"Starting strength analysis task {task_id} for user {user_id}")
        
        # 進捗状態を更新 (20%)
        current_task.update_state(
            state='PROCESSING',
            meta={
                'current': 20,
                'total': 100,
                'status': '会話履歴を分析中...'
            }
        )
        
        # 分析前のバリデーション
        if not conversation_history:
            logger.warning(f"Empty conversation history for user {user_id}")
            return {
                'success': False,
                'user_id': user_id,
                'session_type': session_type,
                'task_id': task_id,
                'error': '会話履歴が空です'
            }
        
        logger.info(f"Analyzing {len(conversation_history)} messages for user {user_id}")
        
        # 進捗状態を更新 (40%)
        current_task.update_state(
            state='PROCESSING',
            meta={
                'current': 40,
                'total': 100,
                'status': 'AIモデルに分析を依頼中...'
            }
        )
        
        # 強み分析を実行（strength_analyzer.pyから移動）
        from strength_analyzer import analyze_conversation_strengths
        analysis_result = analyze_conversation_strengths(conversation_history, session_type)
        
        # 進捗状態を更新 (80%)
        current_task.update_state(
            state='PROCESSING',
            meta={
                'current': 80,
                'total': 100,
                'status': '分析結果を処理中...'
            }
        )
        
        # 結果の構築
        result = {
            'success': True,
            'user_id': user_id,
            'session_type': session_type,
            'task_id': task_id,
            'analysis': analysis_result
        }
        
        # 進捗状態を更新 (100%)
        current_task.update_state(
            state='SUCCESS',
            meta={
                'current': 100,
                'total': 100,
                'status': '分析が完了しました'
            }
        )
        
        logger.info(f"Successfully completed strength analysis task {task_id} for user {user_id}")
        return result
        
    except Exception as e:
        # エラーログとタスクの失敗を記録
        logger.error(f"Error in strength analysis task for user {user_id}: {str(e)}")
        
        # エラー情報をタスクステートに記録
        current_task.update_state(
            state='FAILURE',
            meta={
                'current': 0,
                'total': 100,
                'status': f'エラーが発生しました: {str(e)}'
            }
        )
        
        # エラー結果を返す
        return {
            'success': False,
            'user_id': user_id,
            'session_type': session_type,
            'task_id': current_task.request.id,
            'error': str(e)
        }


@celery.task(
    name='tasks.strength_analysis.get_analysis_status',
    queue='analytics'
)
def get_analysis_status_task(task_id: str) -> Dict[str, Any]:
    """
    分析タスクの進捗状況を取得
    
    Args:
        task_id (str): タスクID
        
    Returns:
        Dict[str, Any]: 進捗情報を含む辞書
            - state (str): タスクの状態
            - meta (dict): 進捗メタデータ
            - result (Any): タスク結果（完了時）
    """
    from celery.result import AsyncResult
    result = AsyncResult(task_id, app=celery)
    
    response = {
        'task_id': task_id,
        'state': result.state,
        'meta': result.info if result.info else {}
    }
    
    if result.state == 'SUCCESS':
        response['result'] = result.result
    elif result.state == 'FAILURE':
        response['error'] = str(result.info)
        
    return response


def get_latest_analysis_result(user_id: int) -> Dict[str, Any]:
    """
    ユーザーの最新の分析結果を取得（同期関数）
    
    Args:
        user_id: ユーザーID
        
    Returns:
        最新の分析結果またはNone
    """
    try:
        # 実際の実装では、データベースやRedisから最新の結果を取得
        # ここでは簡易的な実装
        from database import db, StrengthAnalysisResult
        from sqlalchemy import desc
        
        latest_result = db.session.query(StrengthAnalysisResult)\
            .filter_by(user_id=user_id)\
            .order_by(desc(StrengthAnalysisResult.created_at))\
            .first()
        
        if latest_result:
            return {
                'strengths_analysis': {
                    'skill_scores': latest_result.skill_scores,
                    'overall_score': latest_result.overall_score
                }
            }
        return None
    except Exception as e:
        logger.error(f"Error fetching latest analysis result for user {user_id}: {str(e)}")
        return None