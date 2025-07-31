"""
非同期チャットAPI
Celery + Redis Pub/Subを使用した非同期ストリーミング実装
"""
import uuid
import logging
from flask import Blueprint, request, jsonify, session
from flask_login import current_user
from utils.redis_sse import RedisSSEBridge, AsyncTaskManager
from tasks.llm import stream_chat_response, generate_feedback
from service_layer import SessionService, ConversationService
from models import SessionType
from errors import ValidationError

logger = logging.getLogger(__name__)

# ブループリントの作成
async_chat_bp = Blueprint('async_chat', __name__, url_prefix='/api/async')
task_manager = AsyncTaskManager()


@async_chat_bp.route('/chat/stream', methods=['POST'])
def stream_chat():
    """
    非同期チャットストリーミングエンドポイント
    
    Request JSON:
        {
            "message": str,
            "model": str (optional),
            "session_id": str (optional)
        }
    
    Returns:
        SSE stream
    """
    try:
        # リクエストデータの取得
        data = request.get_json()
        if not data:
            raise ValidationError("リクエストボディが必要です")
        
        message = data.get('message', '').strip()
        if not message:
            raise ValidationError("メッセージが必要です")
        
        model_name = data.get('model', 'gemini/gemini-1.5-flash')
        client_session_id = data.get('session_id')
        
        # セッションIDの生成または取得
        if client_session_id:
            session_id = client_session_id
        else:
            session_id = str(uuid.uuid4())
        
        # ユーザーIDの取得（認証済みの場合）
        user_id = current_user.id if current_user.is_authenticated else None
        
        # 練習セッションの作成または取得
        if user_id:
            practice_session = SessionService.create_session(
                user_id=user_id,
                session_type=SessionType.CHAT_PRACTICE.value,
                ai_model=model_name
            )
        else:
            practice_session = None
        
        # 会話履歴の取得（セッション or メモリから）
        if session.get('chat_memory'):
            messages = []
            for item in session['chat_memory']:
                if 'human' in item:
                    messages.append({'role': 'user', 'content': item['human']})
                if 'ai' in item:
                    messages.append({'role': 'assistant', 'content': item['ai']})
        else:
            messages = []
        
        # システムプロンプトの追加
        system_prompt = """あなたは日本の職場で働く同僚です。
適切な敬語を使いながら、親しみやすい雰囲気で会話してください。
職場での雑談として適切な話題を選び、相手との良好な関係を築くことを心がけてください。"""
        
        all_messages = [{'role': 'system', 'content': system_prompt}] + messages + [{'role': 'user', 'content': message}]
        
        # Redis Pub/Subチャンネルの作成
        channel = task_manager.create_session_channel(session_id)
        
        # Celeryタスクの起動
        task = stream_chat_response.delay(
            session_id=session_id,
            model_name=model_name,
            messages=all_messages,
            metadata={
                'user_id': user_id,
                'practice_session_id': practice_session.id if practice_session else None,
                'message_count': len(messages)
            }
        )
        
        # タスク開始を通知
        task_manager.notify_task_start(channel, task.id, 'chat_streaming')
        
        # 会話ログの保存（ユーザーメッセージ）
        if practice_session:
            ConversationService.add_log(
                session_id=practice_session.id,
                message=message,
                is_user=True
            )
        
        # セッションへの保存（メモリ）
        if 'chat_memory' not in session:
            session['chat_memory'] = []
        
        # SSEレスポンスを返す
        response = RedisSSEBridge.create_sse_response(channel)
        response.headers['X-Session-ID'] = session_id
        response.headers['X-Task-ID'] = task.id
        
        return response
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Async chat streaming error: {str(e)}", exc_info=True)
        return jsonify({'error': '予期しないエラーが発生しました'}), 500


@async_chat_bp.route('/chat/feedback', methods=['POST'])
def async_chat_feedback():
    """
    非同期フィードバック生成エンドポイント
    
    Request JSON:
        {
            "session_id": str,
            "model": str (optional)
        }
    
    Returns:
        {
            "task_id": str,
            "status": str
        }
    """
    try:
        data = request.get_json()
        if not data:
            raise ValidationError("リクエストボディが必要です")
        
        session_id = data.get('session_id')
        if not session_id:
            raise ValidationError("セッションIDが必要です")
        
        model_name = data.get('model', 'gemini/gemini-1.5-flash')
        
        # 会話履歴の取得
        conversation_history = []
        if session.get('chat_memory'):
            for item in session['chat_memory']:
                if 'human' in item:
                    conversation_history.append({'role': 'user', 'content': item['human']})
                if 'ai' in item:
                    conversation_history.append({'role': 'assistant', 'content': item['ai']})
        
        if not conversation_history:
            raise ValidationError("会話履歴がありません")
        
        # フィードバックタスクの起動
        task = generate_feedback.delay(
            session_id=session_id,
            model_name=model_name,
            conversation_history=conversation_history,
            feedback_type='chat'
        )
        
        return jsonify({
            'task_id': task.id,
            'status': 'processing',
            'message': 'フィードバックを生成中です'
        })
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Async feedback error: {str(e)}", exc_info=True)
        return jsonify({'error': '予期しないエラーが発生しました'}), 500


@async_chat_bp.route('/task/<task_id>/status', methods=['GET'])
def get_task_status(task_id: str):
    """
    タスクの状態を取得
    
    Returns:
        {
            "task_id": str,
            "status": str,
            "result": Any (optional)
        }
    """
    try:
        # Celeryタスクの結果を取得
        from celery.result import AsyncResult
        task_result = AsyncResult(task_id)
        
        response = {
            'task_id': task_id,
            'status': task_result.status
        }
        
        if task_result.ready():
            if task_result.successful():
                response['result'] = task_result.result
            else:
                response['error'] = str(task_result.info)
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Task status error: {str(e)}", exc_info=True)
        return jsonify({'error': 'タスク状態の取得に失敗しました'}), 500


@async_chat_bp.route('/chat/save-response', methods=['POST'])
def save_chat_response():
    """
    AIレスポンスを保存（ストリーミング完了後）
    
    Request JSON:
        {
            "session_id": str,
            "message": str,
            "practice_session_id": int (optional)
        }
    """
    try:
        data = request.get_json()
        if not data:
            raise ValidationError("リクエストボディが必要です")
        
        message = data.get('message', '').strip()
        if not message:
            raise ValidationError("メッセージが必要です")
        
        practice_session_id = data.get('practice_session_id')
        
        # 会話ログの保存（AIレスポンス）
        if practice_session_id:
            ConversationService.add_log(
                session_id=practice_session_id,
                message=message,
                is_user=False
            )
        
        # セッションメモリへの保存
        if 'chat_memory' not in session:
            session['chat_memory'] = []
        
        # 最後のエントリにAIレスポンスを追加
        if session['chat_memory'] and 'ai' not in session['chat_memory'][-1]:
            session['chat_memory'][-1]['ai'] = message
        session['chat_memory'].append({'ai': message})
        session.modified = True
        
        return jsonify({
            'status': 'success',
            'message': 'レスポンスを保存しました'
        })
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Save response error: {str(e)}", exc_info=True)
        return jsonify({'error': '保存に失敗しました'}), 500


@async_chat_bp.route('/scenario/stream', methods=['POST'])
def stream_scenario_chat():
    """
    非同期シナリオチャットストリーミングエンドポイント
    
    Request JSON:
        {
            "message": str,
            "scenario_id": str,
            "model": str (optional),
            "session_id": str (optional)
        }
    
    Returns:
        SSE stream
    """
    try:
        # リクエストデータの取得
        data = request.get_json()
        if not data:
            raise ValidationError("リクエストボディが必要です")
        
        message = data.get('message', '').strip()
        scenario_id = data.get('scenario_id')
        if not scenario_id:
            raise ValidationError("シナリオIDが必要です")
        
        model_name = data.get('model', 'gemini/gemini-1.5-flash')
        client_session_id = data.get('session_id')
        
        # セッションIDの生成または取得
        if client_session_id:
            session_id = client_session_id
        else:
            session_id = str(uuid.uuid4())
        
        # ユーザーIDの取得（認証済みの場合）
        user_id = current_user.id if current_user.is_authenticated else None
        
        # シナリオ情報の取得
        from scenarios import get_scenario_by_id
        scenario = get_scenario_by_id(scenario_id)
        if not scenario:
            raise ValidationError("シナリオが見つかりません")
        
        # 練習セッションの作成または取得
        if user_id:
            practice_session = SessionService.create_session(
                user_id=user_id,
                session_type=SessionType.SCENARIO_PRACTICE.value,
                scenario_id=scenario_id,
                ai_model=model_name
            )
        else:
            practice_session = None
        
        # シナリオメモリの取得
        if f'scenario_memory_{scenario_id}' not in session:
            session[f'scenario_memory_{scenario_id}'] = []
        scenario_memory = session[f'scenario_memory_{scenario_id}']
        
        # 会話履歴の構築
        messages = []
        for item in scenario_memory:
            if 'human' in item:
                messages.append({'role': 'user', 'content': item['human']})
            if 'ai' in item:
                messages.append({'role': 'assistant', 'content': item['ai']})
        
        # システムプロンプトの設定
        system_prompt = scenario.get('system_prompt', scenario['description'])
        
        # 初回メッセージの場合
        if not message and len(messages) == 0:
            initial_message = scenario.get('initial_message', '初めまして。どのようなご用件でしょうか？')
            # 初回メッセージをそのまま返すのではなく、LLMに生成させる
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': 'シナリオを開始してください。'}
            ]
        else:
            messages = [{'role': 'system', 'content': system_prompt}] + messages
            if message:
                messages.append({'role': 'user', 'content': message})
        
        # Redis Pub/Subチャンネルの作成
        channel = task_manager.create_session_channel(f'scenario_{session_id}')
        
        # Celeryタスクの起動
        task = stream_chat_response.delay(
            session_id=session_id,
            model_name=model_name,
            messages=messages,
            metadata={
                'user_id': user_id,
                'practice_session_id': practice_session.id if practice_session else None,
                'scenario_id': scenario_id,
                'scenario_title': scenario.get('title', ''),
                'message_count': len(scenario_memory)
            }
        )
        
        # タスク開始を通知
        task_manager.notify_task_start(channel, task.id, 'scenario_streaming')
        
        # 会話ログの保存（ユーザーメッセージ）
        if practice_session and message:
            ConversationService.add_log(
                session_id=practice_session.id,
                message=message,
                is_user=True
            )
        
        # メモリへの保存
        if message:
            scenario_memory.append({'human': message})
            session.modified = True
        
        # SSEレスポンスを返す
        response = RedisSSEBridge.create_sse_response(channel)
        response.headers['X-Session-ID'] = session_id
        response.headers['X-Task-ID'] = task.id
        
        return response
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Async scenario streaming error: {str(e)}", exc_info=True)
        return jsonify({'error': '予期しないエラーが発生しました'}), 500


@async_chat_bp.route('/scenario/feedback', methods=['POST'])
def async_scenario_feedback():
    """
    非同期シナリオフィードバック生成エンドポイント
    
    Request JSON:
        {
            "scenario_id": str,
            "model": str (optional),
            "session_id": str (optional)
        }
    
    Returns:
        {
            "task_id": str,
            "status": str
        }
    """
    try:
        data = request.get_json()
        if not data:
            raise ValidationError("リクエストボディが必要です")
        
        scenario_id = data.get('scenario_id')
        if not scenario_id:
            raise ValidationError("シナリオIDが必要です")
        
        model_name = data.get('model', 'gemini/gemini-1.5-flash')
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        # シナリオ情報の取得
        from scenarios import get_scenario_by_id
        scenario = get_scenario_by_id(scenario_id)
        if not scenario:
            raise ValidationError("シナリオが見つかりません")
        
        # 会話履歴の取得
        conversation_history = []
        if f'scenario_memory_{scenario_id}' in session:
            for item in session[f'scenario_memory_{scenario_id}']:
                if 'human' in item:
                    conversation_history.append({'role': 'user', 'content': item['human']})
                if 'ai' in item:
                    conversation_history.append({'role': 'assistant', 'content': item['ai']})
        
        if not conversation_history:
            raise ValidationError("会話履歴がありません")
        
        # フィードバックタスクの起動
        task = generate_feedback.delay(
            session_id=session_id,
            model_name=model_name,
            conversation_history=conversation_history,
            feedback_type='scenario',
            metadata={
                'scenario_id': scenario_id,
                'scenario_title': scenario.get('title', ''),
                'feedback_points': scenario.get('feedback_points', [])
            }
        )
        
        return jsonify({
            'task_id': task.id,
            'status': 'processing',
            'message': 'フィードバックを生成中です'
        })
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Async scenario feedback error: {str(e)}", exc_info=True)
        return jsonify({'error': '予期しないエラーが発生しました'}), 500


@async_chat_bp.route('/scenario/assist', methods=['POST'])
def async_scenario_assist():
    """
    非同期シナリオAIアシスト取得エンドポイント
    
    Request JSON:
        {
            "scenario_id": str,
            "current_context": str,
            "model": str (optional),
            "session_id": str (optional)
        }
    
    Returns:
        {
            "suggestion": str,
            "fallback": bool (optional),
            "fallback_model": str (optional)
        }
    """
    try:
        data = request.get_json()
        if not data:
            raise ValidationError("リクエストボディが必要です")
        
        scenario_id = data.get('scenario_id')
        if not scenario_id:
            raise ValidationError("シナリオIDが必要です")
        
        current_context = data.get('current_context', '')
        model_name = data.get('model', 'gemini/gemini-1.5-flash')
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        # シナリオ情報の取得
        from scenarios import get_scenario_by_id
        scenario = get_scenario_by_id(scenario_id)
        if not scenario:
            raise ValidationError("シナリオが見つかりません")
        
        # アシストプロンプトの構築
        system_prompt = f"""
        あなたは職場コミュニケーションのコーチです。
        シナリオ: {scenario.get('title', '')}
        状況: {scenario.get('description', '')}
        
        現在の会話の流れを踏まえて、ユーザーが次に言うべき適切な返答のヒントを提供してください。
        ヒントは具体的で実践的なものにし、1-2文で簡潔にまとめてください。
        """
        
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': f"現在の会話:\n{current_context}\n\n適切な返答のヒントを教えてください。"}
        ]
        
        # 簡易的な同期実行（将来的には非同期化）
        from service_layer import LLMService
        llm_service = LLMService()
        
        try:
            suggestion = llm_service.generate_response(messages, model_name)
            return jsonify({
                'suggestion': suggestion,
                'model_used': model_name
            })
        except Exception as e:
            # フォールバックモデルの使用
            fallback_model = 'gemini/gemini-1.5-flash'
            if model_name == fallback_model:
                raise e
            
            suggestion = llm_service.generate_response(messages, fallback_model)
            return jsonify({
                'suggestion': suggestion,
                'fallback': True,
                'fallback_model': fallback_model
            })
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Async scenario assist error: {str(e)}", exc_info=True)
        return jsonify({'error': '予期しないエラーが発生しました'}), 500


@async_chat_bp.route('/watch/start', methods=['POST'])
def stream_watch_start():
    """
    非同期観戦モード開始エンドポイント
    
    Request JSON:
        {
            "model_a": str,
            "model_b": str,
            "partner_type": str,
            "situation": str,
            "topic": str,
            "session_id": str (optional)
        }
    
    Returns:
        SSE stream
    """
    try:
        # リクエストデータの取得
        data = request.get_json()
        if not data:
            raise ValidationError("リクエストボディが必要です")
        
        model_a = data.get('model_a', 'gemini/gemini-1.5-flash')
        model_b = data.get('model_b', 'gemini/gemini-1.5-flash')
        partner_type = data.get('partner_type', 'colleague')
        situation = data.get('situation', 'lunch')
        topic = data.get('topic', 'general')
        client_session_id = data.get('session_id')
        
        # セッションIDの生成または取得
        if client_session_id:
            session_id = client_session_id
        else:
            session_id = str(uuid.uuid4())
        
        # ユーザーIDの取得（認証済みの場合）
        user_id = current_user.id if current_user.is_authenticated else None
        
        # 練習セッションの作成または取得
        if user_id:
            practice_session = SessionService.create_session(
                user_id=user_id,
                session_type=SessionType.WATCH_MODE.value,
                ai_model=model_a  # 主モデルを記録
            )
        else:
            practice_session = None
        
        # 会話設定を構築
        context = f"""
        設定:
        - 相手: {partner_type}
        - シチュエーション: {situation}
        - 話題: {topic}
        
        太郎さんと花子さんが自然な雑談をしています。
        太郎さんが話題を開始してください。
        """
        
        messages = [
            {'role': 'system', 'content': '太郎さんとして自然な雑談を開始してください。'},
            {'role': 'user', 'content': context}
        ]
        
        # Redis Pub/Subチャンネルの作成
        channel = task_manager.create_session_channel(f'watch_{session_id}')
        
        # Celeryタスクの起動（太郎の初回発言）
        task = stream_chat_response.delay(
            session_id=session_id,
            model_name=model_a,
            messages=messages,
            metadata={
                'user_id': user_id,
                'practice_session_id': practice_session.id if practice_session else None,
                'watch_mode': True,
                'speaker': '太郎',
                'partner_type': partner_type,
                'situation': situation,
                'topic': topic
            }
        )
        
        # タスク開始を通知
        task_manager.notify_task_start(channel, task.id, 'watch_streaming')
        
        # メモリの初期化
        if 'watch_memory' not in session:
            session['watch_memory'] = []
        
        # SSEレスポンスを返す
        response = RedisSSEBridge.create_sse_response(channel)
        response.headers['X-Session-ID'] = session_id
        response.headers['X-Task-ID'] = task.id
        
        return response
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Async watch start error: {str(e)}", exc_info=True)
        return jsonify({'error': '予期しないエラーが発生しました'}), 500


@async_chat_bp.route('/watch/next', methods=['POST'])
def stream_watch_next():
    """
    非同期観戦モード次の発言エンドポイント
    
    Request JSON:
        {
            "session_id": str,
            "model_a": str (optional),
            "model_b": str (optional)
        }
    
    Returns:
        SSE stream
    """
    try:
        # リクエストデータの取得
        data = request.get_json()
        if not data:
            raise ValidationError("リクエストボディが必要です")
        
        session_id = data.get('session_id')
        if not session_id:
            raise ValidationError("セッションIDが必要です")
        
        model_a = data.get('model_a', 'gemini/gemini-1.5-flash')
        model_b = data.get('model_b', 'gemini/gemini-1.5-flash')
        
        # 会話履歴の取得
        watch_memory = session.get('watch_memory', [])
        if not watch_memory:
            raise ValidationError("会話履歴がありません")
        
        # 次の話者を決定（交互に発言）
        last_speaker = watch_memory[-1].get('speaker', '太郎')
        next_speaker = '花子' if last_speaker == '太郎' else '太郎'
        model_name = model_b if next_speaker == '花子' else model_a
        
        # 会話履歴を構築
        conversation_context = "\n".join([
            f"{item['speaker']}: {item['message']}"
            for item in watch_memory
        ])
        
        messages = [
            {'role': 'system', 'content': f'あなたは{next_speaker}さんです。自然な雑談を続けてください。'},
            {'role': 'user', 'content': f"これまでの会話:\n{conversation_context}\n\n{next_speaker}さんとして自然に返答してください。"}
        ]
        
        # Redis Pub/Subチャンネルの作成
        channel = task_manager.create_session_channel(f'watch_{session_id}')
        
        # Celeryタスクの起動
        task = stream_chat_response.delay(
            session_id=session_id,
            model_name=model_name,
            messages=messages,
            metadata={
                'watch_mode': True,
                'speaker': next_speaker,
                'message_count': len(watch_memory)
            }
        )
        
        # タスク開始を通知
        task_manager.notify_task_start(channel, task.id, 'watch_streaming')
        
        # SSEレスポンスを返す
        response = RedisSSEBridge.create_sse_response(channel)
        response.headers['X-Session-ID'] = session_id
        response.headers['X-Task-ID'] = task.id
        
        return response
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Async watch next error: {str(e)}", exc_info=True)
        return jsonify({'error': '予期しないエラーが発生しました'}), 500


@async_chat_bp.route('/watch/save-message', methods=['POST'])
def save_watch_message():
    """
    観戦モードのメッセージを保存
    
    Request JSON:
        {
            "session_id": str,
            "speaker": str,
            "message": str,
            "practice_session_id": int (optional)
        }
    """
    try:
        data = request.get_json()
        if not data:
            raise ValidationError("リクエストボディが必要です")
        
        speaker = data.get('speaker', '').strip()
        message = data.get('message', '').strip()
        if not speaker or not message:
            raise ValidationError("話者とメッセージが必要です")
        
        practice_session_id = data.get('practice_session_id')
        
        # 会話ログの保存
        if practice_session_id:
            ConversationService.add_log(
                session_id=practice_session_id,
                message=f"{speaker}: {message}",
                is_user=False  # 観戦モードではすべてAI
            )
        
        # セッションメモリへの保存
        if 'watch_memory' not in session:
            session['watch_memory'] = []
        
        session['watch_memory'].append({
            'speaker': speaker,
            'message': message,
            'timestamp': uuid.uuid4().hex  # タイムスタンプ代わり
        })
        
        # セッションを保存
        session.modified = True
        
        return jsonify({
            'status': 'success',
            'message': 'メッセージを保存しました'
        })
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Save watch message error: {str(e)}", exc_info=True)
        return jsonify({'error': '保存に失敗しました'}), 500


@async_chat_bp.route('/strength-analysis/start', methods=['POST'])
def start_strength_analysis():
    """
    強み分析を非同期で開始するエンドポイント
    
    Request JSON:
        {
            "session_type": str ('chat' or 'scenario'),
            "scenario_id": str (optional, for scenario type),
            "session_id": str (optional)
        }
    
    Returns:
        {
            "task_id": str,
            "status": str,
            "message": str
        }
    """
    try:
        data = request.get_json()
        if not data:
            raise ValidationError("リクエストボディが必要です")
        
        session_type = data.get('session_type', 'chat')
        scenario_id = data.get('scenario_id')
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        # ユーザーIDの取得（認証済みの場合）
        user_id = current_user.id if current_user.is_authenticated else 0
        
        # 会話履歴の取得
        conversation_history = []
        
        if session_type == 'chat':
            # 雑談練習の履歴
            if 'chat_memory' in session:
                for item in session['chat_memory']:
                    if 'human' in item:
                        conversation_history.append({'role': 'user', 'content': item['human']})
                    if 'ai' in item:
                        conversation_history.append({'role': 'assistant', 'content': item['ai']})
        elif session_type == 'scenario' and scenario_id:
            # シナリオ練習の履歴
            if f'scenario_memory_{scenario_id}' in session:
                for item in session[f'scenario_memory_{scenario_id}']:
                    if 'human' in item:
                        conversation_history.append({'role': 'user', 'content': item['human']})
                    if 'ai' in item:
                        conversation_history.append({'role': 'assistant', 'content': item['ai']})
        else:
            raise ValidationError("無効なセッションタイプです")
        
        if not conversation_history:
            raise ValidationError("分析する会話履歴がありません")
        
        # 強み分析タスクの起動
        from tasks.strength_analysis import analyze_conversation_strengths_task
        task = analyze_conversation_strengths_task.delay(
            user_id=user_id,
            conversation_history=conversation_history,
            session_type=session_type
        )
        
        return jsonify({
            'task_id': task.id,
            'status': 'processing',
            'message': '強み分析を開始しました'
        })
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Start strength analysis error: {str(e)}", exc_info=True)
        return jsonify({'error': '予期しないエラーが発生しました'}), 500


@async_chat_bp.route('/strength-analysis/status/<task_id>', methods=['GET'])
def get_strength_analysis_status(task_id):
    """
    強み分析タスクのステータスと進捗を取得
    
    Returns:
        {
            "task_id": str,
            "state": str,
            "current": int,
            "total": int,
            "status": str,
            "result": dict (optional, when completed)
        }
    """
    try:
        from tasks.strength_analysis import get_analysis_status_task
        
        # ステータス取得タスクを実行（軽量なので同期的に実行）
        result = get_analysis_status_task(task_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Get strength analysis status error: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'ステータスの取得に失敗しました',
            'task_id': task_id,
            'state': 'ERROR'
        }), 500