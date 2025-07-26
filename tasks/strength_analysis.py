"""
強み分析関連の非同期タスク

Celeryを使用して会話履歴の強み分析処理を非同期化し、
メインのリクエスト/レスポンスサイクルから重い処理を分離
"""
import logging
import json
from typing import List, Dict, Any, Optional
from celery import shared_task, current_task
from celery.exceptions import MaxRetriesExceededError, Retry
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
    queue='analytics'  # analyticsキューを使用
)
@retry_with_backoff
def analyze_conversation_strengths_task(self, user_id: int, conversation_history: List[Dict[str, str]], session_type: str = 'chat') -> Dict[str, Any]:
    """
    会話履歴から強み分析を非同期で実行するCeleryタスク
    
    Args:
        user_id: ユーザーID
        conversation_history: 会話履歴のリスト
        session_type: セッション種別 ('chat', 'scenario')
        
    Returns:
        Dict containing analysis results and task status
        
    Raises:
        MaxRetriesExceededError: 最大リトライ回数を超えた場合
    """
    try:
        logger.info(f"Starting strength analysis task for user {user_id}, session type: {session_type}")
        
        # 進捗を更新
        current_task.update_state(
            state='PROGRESS',
            meta={
                'current': 10,
                'total': 100,
                'status': '分析を開始しています...'
            }
        )
        
        # Flaskアプリケーションコンテキストが必要なため、ここで設定
        from app import app
        from strength_analyzer import (
            create_strength_analysis_prompt,
            parse_strength_analysis,
            get_top_strengths,
            generate_encouragement_messages,
            analyze_user_strengths
        )
        from services import SessionService
        
        with app.app_context():
            # 進捗を更新
            current_task.update_state(
                state='PROGRESS',
                meta={
                    'current': 30,
                    'total': 100,
                    'status': 'AIモデルによる分析を実行中...'
                }
            )
            
            # LLMプロバイダーを取得してプロンプトを生成
            if conversation_history and len(conversation_history) > 0:
                # プロンプトを作成
                prompt = create_strength_analysis_prompt(conversation_history)
                
                # LLMで分析（実際のGemini APIを使用）
                model_name = "gemini/gemini-1.5-flash"  # 高速な分析用モデル
                llm = self.get_llm(model_name)
                
                # プロンプトメッセージの構築
                messages = [
                    {"role": "system", "content": "あなたは職場コミュニケーションの専門家です。会話履歴を分析し、ユーザーの強みを数値化してください。"},
                    {"role": "user", "content": prompt}
                ]
                
                # LLMで分析実行
                from langchain_core.messages import SystemMessage, HumanMessage
                langchain_messages = [
                    SystemMessage(content=messages[0]["content"]),
                    HumanMessage(content=messages[1]["content"])
                ]
                
                response = llm.invoke(langchain_messages)
                analysis_text = response.content
                
                # 分析結果をパース
                analysis_result = parse_strength_analysis(analysis_text)
                
                # 進捗を更新
                current_task.update_state(
                    state='PROGRESS',
                    meta={
                        'current': 60,
                        'total': 100,
                        'status': '分析結果を処理中...'
                    }
                )
                
                # トップ強みを取得
                top_strengths = get_top_strengths(analysis_result, top_n=3)
                
                # 励ましメッセージを生成
                # 履歴は空のリストとして扱う（非同期タスクではセッション管理が複雑なため）
                encouragement_messages = generate_encouragement_messages(analysis_result, [])
                
                # 進捗を更新
                current_task.update_state(
                    state='PROGRESS',
                    meta={
                        'current': 80,
                        'total': 100,
                        'status': '結果を保存中...'
                    }
                )
                
                # 結果を保存（必要に応じてDBに保存）
                result = {
                    'success': True,
                    'user_id': user_id,
                    'session_type': session_type,
                    'analysis': {
                        'scores': analysis_result,
                        'top_strengths': top_strengths,
                        'encouragement_messages': encouragement_messages
                    },
                    'task_id': self.request.id
                }
                
                # 進捗を更新（完了）
                current_task.update_state(
                    state='PROGRESS',
                    meta={
                        'current': 100,
                        'total': 100,
                        'status': '分析が完了しました！'
                    }
                )
                
                logger.info(f"Strength analysis completed for user {user_id}")
                return result
                
            else:
                # 会話履歴が空の場合
                logger.warning(f"No conversation history for user {user_id}")
                return {
                    'success': False,
                    'user_id': user_id,
                    'session_type': session_type,
                    'error': 'No conversation history available',
                    'task_id': self.request.id
                }
                
    except Exception as exc:
        logger.error(f"Error in strength analysis task: {str(exc)}")
        
        # エラーが発生した場合はリトライ
        raise self.retry(exc=exc, countdown=60)


@shared_task(
    bind=True,
    name='tasks.strength_analysis.get_analysis_status',
    queue='analytics'
)
def get_analysis_status_task(self, task_id: str) -> Dict[str, Any]:
    """
    分析タスクのステータスを取得
    
    Args:
        task_id: タスクID
        
    Returns:
        Dict containing task status and progress
    """
    try:
        from celery.result import AsyncResult
        
        result = AsyncResult(task_id)
        
        if result.state == 'PENDING':
            response = {
                'state': result.state,
                'current': 0,
                'total': 100,
                'status': 'タスクが開始されるのを待っています...'
            }
        elif result.state != 'FAILURE':
            response = {
                'state': result.state,
                'current': result.info.get('current', 0),
                'total': result.info.get('total', 100),
                'status': result.info.get('status', '')
            }
            
            if result.state == 'SUCCESS':
                response['result'] = result.info
        else:
            # エラーが発生した場合
            response = {
                'state': result.state,
                'current': 0,
                'total': 100,
                'status': 'エラーが発生しました',
                'error': str(result.info)
            }
            
        return response
        
    except Exception as exc:
        logger.error(f"Error getting task status: {str(exc)}")
        return {
            'state': 'ERROR',
            'current': 0,
            'total': 100,
            'status': 'ステータス取得中にエラーが発生しました',
            'error': str(exc)
        }