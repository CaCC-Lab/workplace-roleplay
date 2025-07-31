"""
LLM関連の非同期タスク
"""
import json
import logging
import time
from typing import List, Dict, Any, Optional
from celery import Task
from celery_app import celery
import redis
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from config.config import get_config
from .retry_strategy import retry_with_backoff, track_streaming_chunks

logger = logging.getLogger(__name__)
config = get_config()

# Redisクライアント（Pub/Sub用）
redis_client = redis.Redis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    db=config.REDIS_DB,
    decode_responses=True
)


class LLMTask(Task):
    """LLMタスクの基底クラス（リトライ機能付き）"""
    
    def __init__(self):
        super().__init__()
        self._llm_cache = {}
    
    def get_llm(self, model_name: str) -> ChatGoogleGenerativeAI:
        """LLMインスタンスの取得（キャッシュ付き）"""
        if model_name not in self._llm_cache:
            # モデル名からプロバイダー/モデルを分離
            if "/" in model_name:
                provider, model_id = model_name.split("/", 1)
            else:
                provider = "gemini"
                model_id = model_name
            
            # Geminiモデルの作成
            if provider == "gemini":
                self._llm_cache[model_name] = ChatGoogleGenerativeAI(
                    model=model_id,
                    google_api_key=config.GOOGLE_API_KEY,
                    temperature=config.DEFAULT_TEMPERATURE,
                    streaming=True  # ストリーミング対応
                )
            else:
                raise ValueError(f"Unsupported provider: {provider}")
        
        return self._llm_cache[model_name]


@celery.task(bind=True, base=LLMTask, name='tasks.llm.stream_chat_response')
@retry_with_backoff
def stream_chat_response(
    self,
    session_id: str,
    model_name: str,
    messages: List[Dict[str, str]],
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    チャット応答をストリーミングで生成し、Redis Pub/Subで配信
    
    Args:
        session_id: セッションID（Pub/Subチャンネル名）
        model_name: 使用するLLMモデル名
        messages: メッセージ履歴
        metadata: 追加のメタデータ
    
    Returns:
        完了ステータスと生成されたテキスト
    """
    start_time = time.time()
    channel = f"stream:{session_id}"
    generated_text = ""
    token_count = 0
    
    try:
        # LLMインスタンスの取得
        llm = self.get_llm(model_name)
        
        # メッセージの変換
        langchain_messages = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'system':
                langchain_messages.append(SystemMessage(content=content))
            elif role == 'assistant':
                langchain_messages.append(AIMessage(content=content))
            else:
                langchain_messages.append(HumanMessage(content=content))
        
        # ストリーミング開始を通知
        redis_client.publish(channel, json.dumps({
            'type': 'start',
            'session_id': session_id,
            'model': model_name,
            'timestamp': time.time()
        }))
        
        # LLMからストリーミング応答を取得
        for chunk in llm.stream(langchain_messages):
            if hasattr(chunk, 'content'):
                chunk_text = chunk.content
            else:
                chunk_text = str(chunk)
            
            if chunk_text:
                generated_text += chunk_text
                token_count += 1
                
                # チャンクをRedisに配信
                chunk_message = {
                    'type': 'chunk',
                    'content': chunk_text,
                    'timestamp': time.time()
                }
                
                # 観戦モードの場合は話者情報を含める
                if metadata and metadata.get('watch_mode'):
                    chunk_message['speaker'] = metadata.get('speaker', '不明')
                
                # 部分レスポンス追跡
                track_streaming_chunks(self, chunk_message)
                
                redis_client.publish(channel, json.dumps(chunk_message))
        
        # 完了を通知
        response_time = time.time() - start_time
        complete_message = {
            'type': 'complete',
            'total_content': generated_text,
            'token_count': token_count,
            'response_time': response_time,
            'timestamp': time.time()
        }
        
        # 観戦モードの場合は話者情報を含める
        if metadata and metadata.get('watch_mode'):
            complete_message['speaker'] = metadata.get('speaker', '不明')
            complete_message['formatted_content'] = f"{metadata.get('speaker', '不明')}: {generated_text}"
        
        redis_client.publish(channel, json.dumps(complete_message))
        
        # 結果を返す
        return {
            'status': 'success',
            'session_id': session_id,
            'content': generated_text,
            'token_count': token_count,
            'response_time': response_time,
            'model': model_name
        }
        
    except Exception as e:
        logger.error(f"LLM streaming error: {str(e)}", exc_info=True)
        
        # 部分レスポンスを保存（可能な場合）
        if generated_text:
            self.save_partial_response(self.request.id, {
                'content': generated_text,
                'timestamp': time.time(),
                'metadata': {
                    'error_occurred': True,
                    'error_message': str(e),
                    'tokens_generated': token_count,
                    'partial_response_time': time.time() - start_time
                }
            })
        
        # リトライ戦略を適用
        try:
            self.retry_with_strategy(e, (session_id, model_name, messages, metadata), {})
        except Exception as retry_error:
            # 最終エラー処理
            error_message = f"申し訳ございません。応答の生成中にエラーが発生しました: {str(retry_error)}"
            
            # エラーを通知
            redis_client.publish(channel, json.dumps({
                'type': 'error',
                'error': str(retry_error),
                'message': error_message,
                'timestamp': time.time(),
                'retry_count': self.request.retries,
                'partial_content': generated_text if generated_text else None
            }))
            
            return {
                'status': 'error',
                'session_id': session_id,
                'error': str(retry_error),
                'message': error_message,
                'retry_count': self.request.retries,
                'partial_content': generated_text if generated_text else None
            }


@celery.task(bind=True, base=LLMTask, name='tasks.llm.generate_feedback')
@retry_with_backoff
def generate_feedback(
    self,
    session_id: str,
    model_name: str,
    conversation_history: List[Dict[str, str]],
    feedback_type: str,
    scenario_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    会話履歴に基づいてフィードバックを生成
    
    Args:
        session_id: セッションID
        model_name: 使用するLLMモデル名
        conversation_history: 会話履歴
        feedback_type: フィードバックタイプ（chat/scenario）
        scenario_info: シナリオ情報（シナリオモードの場合）
    
    Returns:
        フィードバック結果
    """
    try:
        llm = self.get_llm(model_name)
        
        # フィードバック生成用のプロンプト作成
        if feedback_type == 'scenario' and scenario_info:
            prompt = _create_scenario_feedback_prompt(conversation_history, scenario_info)
        else:
            prompt = _create_chat_feedback_prompt(conversation_history)
        
        # フィードバック生成
        response = llm.invoke([SystemMessage(content=prompt)])
        
        if hasattr(response, 'content'):
            feedback_text = response.content
        else:
            feedback_text = str(response)
        
        # 強み分析（簡易版）
        analysis_result = _analyze_strengths(feedback_text)
        
        return {
            'status': 'success',
            'session_id': session_id,
            'feedback': feedback_text,
            'analysis': analysis_result,
            'model': model_name
        }
        
    except Exception as e:
        logger.error(f"Feedback generation error: {str(e)}", exc_info=True)
        
        # リトライ戦略を適用
        try:
            self.retry_with_strategy(e, (session_id, model_name, conversation_history, feedback_type, scenario_info), {})
        except Exception as retry_error:
            # 最終エラー処理
            return {
                'status': 'error',
                'session_id': session_id,
                'error': str(retry_error),
                'message': 'フィードバックの生成中にエラーが発生しました',
                'retry_count': self.request.retries
            }


def _create_scenario_feedback_prompt(history: List[Dict[str, str]], scenario: Dict) -> str:
    """シナリオフィードバック用のプロンプト作成"""
    # ユーザーのメッセージのみを抽出
    user_messages = [msg for msg in history if msg['role'] == 'user']
    conversation_text = "\n".join([
        f"ユーザー: {msg['content']}" for msg in user_messages
    ])
    
    return f"""
以下の職場シナリオでのユーザーの発言を分析し、建設的なフィードバックを提供してください。

シナリオ: {scenario.get('title', '')}
説明: {scenario.get('description', '')}
学習ポイント: {', '.join(scenario.get('learning_points', []))}

ユーザーの発言:
{conversation_text}

以下の観点からフィードバックを提供してください：
1. シナリオの学習ポイントに対する達成度
2. コミュニケーションの強み
3. 改善できる点
4. 具体的な改善提案

フィードバックは励ましと具体的なアドバイスを含めて、300-500文字程度でお願いします。
"""


def _create_chat_feedback_prompt(history: List[Dict[str, str]]) -> str:
    """雑談フィードバック用のプロンプト作成"""
    # ユーザーのメッセージのみを抽出
    user_messages = [msg for msg in history if msg['role'] == 'user']
    conversation_text = "\n".join([
        f"ユーザー: {msg['content']}" for msg in user_messages
    ])
    
    return f"""
以下の職場での雑談におけるユーザーの発言を分析し、建設的なフィードバックを提供してください。

ユーザーの発言:
{conversation_text}

以下の観点からフィードバックを提供してください：
1. 話題選びの適切さ
2. 相手への配慮
3. 会話の流れの作り方
4. 職場での関係構築への貢献

フィードバックは励ましと具体的なアドバイスを含めて、300-500文字程度でお願いします。
"""


def _analyze_strengths(feedback_text: str) -> Dict[str, float]:
    """フィードバックテキストから強みを分析（簡易版）"""
    # 実際の実装では、より高度な分析を行う
    # ここでは簡易的なキーワードマッチングで実装
    strengths = {
        'empathy': 0.5,
        'clarity': 0.5,
        'listening': 0.5,
        'problem_solving': 0.5,
        'assertiveness': 0.5,
        'flexibility': 0.5
    }
    
    # キーワードに基づいてスコアを調整
    positive_keywords = {
        'empathy': ['共感', '気持ち', '理解', '配慮'],
        'clarity': ['明確', 'わかりやすい', '具体的', '論理的'],
        'listening': ['傾聴', '聞く', '確認', '質問'],
        'problem_solving': ['解決', '提案', '改善', 'アイデア'],
        'assertiveness': ['主張', '意見', '伝える', '表現'],
        'flexibility': ['柔軟', '適応', '調整', '対応']
    }
    
    for skill, keywords in positive_keywords.items():
        for keyword in keywords:
            if keyword in feedback_text:
                strengths[skill] = min(strengths[skill] + 0.1, 1.0)
    
    return strengths