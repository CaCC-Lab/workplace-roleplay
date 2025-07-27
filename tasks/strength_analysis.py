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
            - task_id (str): CeleryタスクID
            - error (str, optional): エラーメッセージ（失敗時のみ）
        
    Raises:
        Retry: エラー発生時にリトライを実行
        
    Note:
        - 進捗は current_task.update_state() で更新される
        - LLMエラー時は自動的にリトライされる（最大3回）
        - 会話履歴が空の場合はエラーを返す
    """
    try:
        logger.info(f"Starting strength analysis task for user {user_id}, session type: {session_type}")
        
        # リトライ時は部分レスポンスをチェック
        partial_result = None
        if self.request.retries > 0:
            from .retry_strategy import PartialResponseManager
            partial_data = PartialResponseManager.get_partial_response(self.request.id)
            if partial_data:
                partial_result = partial_data.get('partial_analysis')
                logger.info(f"Resuming from partial response for task {self.request.id}")
        
        # 進捗を更新
        current_task.update_state(
            state='PROGRESS',
            meta={
                'current': 10,
                'total': 100,
                'status': '分析を開始しています...',
                'partial_response': partial_result
            }
        )
        
        # Flaskアプリケーションコンテキストが必要なため、ここで設定
        from app import app
        from strength_analyzer import (
            create_strength_analysis_prompt,
            parse_strength_analysis,
            get_top_strengths,
            generate_encouragement_messages
        )
        
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
                
                # 進捗を更新（部分結果を保存）
                current_task.update_state(
                    state='PROGRESS',
                    meta={
                        'current': 60,
                        'total': 100,
                        'status': '分析結果を処理中...',
                        'partial_response': {
                            'analysis_text': analysis_text,
                            'parsed_result': analysis_result
                        }
                    }
                )
                
                # 部分レスポンスをRedisにも保存
                from .retry_strategy import PartialResponseManager
                PartialResponseManager.save_partial_response(
                    self.request.id,
                    chunks=[{'content': analysis_text, 'type': 'analysis_result'}],
                    metadata={
                        'partial_analysis': analysis_result,
                        'stage': 'analysis_completed'
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
        raise self.retry(exc=exc, countdown=60) from exc


@shared_task(
    bind=True,
    name='tasks.strength_analysis.get_analysis_status',
    queue='analytics'
)
def get_analysis_status_task(self, task_id: str) -> Dict[str, Any]:
    """
    分析タスクのステータスと進捗を取得
    
    指定されたタスクIDの現在の状態、進捗、結果を取得します。
    このタスクは軽量なため、同期的に実行されます。
    
    Args:
        task_id (str): 確認するCeleryタスクのID
        
    Returns:
        Dict[str, Any]: タスクの状態情報を含む辞書。以下のキーを含む：
            - state (str): タスクの状態（PENDING, PROGRESS, SUCCESS, FAILURE, ERROR）
            - current (int): 現在の進捗値（0-100）
            - total (int): 進捗の最大値（通常100）
            - status (str): 人間が読めるステータスメッセージ
            - result (dict, optional): 完了時の結果（SUCCESS時のみ）
            - error (str, optional): エラーメッセージ（FAILURE/ERROR時のみ）
            
    Note:
        - PENDING: タスクがまだ開始されていない
        - PROGRESS: タスクが実行中で進捗を報告している
        - SUCCESS: タスクが正常に完了した
        - FAILURE: タスクが失敗した
        - ERROR: ステータス取得中にエラーが発生した
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