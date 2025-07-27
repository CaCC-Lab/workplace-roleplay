"""
ペルソナ統合シナリオAPIエンドポイント

ペルソナシステムを活用したシナリオプレイのAPI
"""
import uuid
import logging
from flask import Blueprint, request, jsonify, session
from flask_login import current_user
from utils.redis_sse import RedisSSEBridge, AsyncTaskManager
from tasks.llm import stream_chat_response
from service_layer import SessionService, ConversationService
from services.persona_scenario_integration import PersonaScenarioIntegrationService
from models import SessionType
from errors import ValidationError

logger = logging.getLogger(__name__)

# ブループリントの作成
persona_scenarios_bp = Blueprint('persona_scenarios', __name__, url_prefix='/api/persona-scenarios')
task_manager = AsyncTaskManager()
integration_service = PersonaScenarioIntegrationService()


@persona_scenarios_bp.route('/suitable-personas/<scenario_id>', methods=['GET'])
def get_suitable_personas(scenario_id: str):
    """
    シナリオに適したペルソナのリストを取得
    
    Returns:
        {
            "personas": [
                {
                    "persona_code": str,
                    "name": str,
                    "role": str,
                    "industry": str,
                    "personality_type": str,
                    "description": str
                }
            ]
        }
    """
    try:
        user_id = current_user.id if current_user.is_authenticated else None
        
        # 適したペルソナを取得
        personas = integration_service.get_suitable_personas_for_scenario(
            scenario_id, user_id
        )
        
        # レスポンス用にフォーマット
        persona_list = []
        for persona in personas[:5]:  # 上位5つまで
            persona_list.append({
                'persona_code': persona.persona_code,
                'name': persona.name,
                'role': persona.role.value,
                'industry': persona.industry.value,
                'personality_type': persona.personality_type.value,
                'description': f"{persona.age}歳の{persona.industry.value}業界の{persona.role.value}",
                'years_experience': persona.years_experience
            })
        
        return jsonify({
            'personas': persona_list,
            'count': len(persona_list)
        })
        
    except Exception as e:
        logger.error(f"Error getting suitable personas: {str(e)}", exc_info=True)
        return jsonify({'error': '予期しないエラーが発生しました'}), 500


@persona_scenarios_bp.route('/stream', methods=['POST'])
def stream_persona_scenario_chat():
    """
    ペルソナを使用した非同期シナリオチャットストリーミング
    
    Request JSON:
        {
            "message": str,
            "scenario_id": str,
            "persona_code": str (optional),
            "model": str (optional),
            "session_id": str (optional)
        }
    
    Returns:
        SSE stream with persona information
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
        
        persona_code = data.get('persona_code')
        model_name = data.get('model', 'gemini/gemini-1.5-flash')
        client_session_id = data.get('session_id')
        
        # セッションIDの生成または取得
        if client_session_id:
            session_id = client_session_id
        else:
            session_id = str(uuid.uuid4())
        
        # ユーザーIDの取得
        user_id = current_user.id if current_user.is_authenticated else None
        
        # シナリオ情報の取得
        from scenarios import get_scenario_by_id
        scenario = get_scenario_by_id(scenario_id)
        if not scenario:
            raise ValidationError("シナリオが見つかりません")
        
        # ペルソナの選択
        persona = integration_service.select_persona_for_scenario(
            scenario_id, user_id, persona_code
        )
        
        # セッションにペルソナ情報を保存
        if f'scenario_persona_{scenario_id}' not in session:
            session[f'scenario_persona_{scenario_id}'] = persona.persona_code
        
        # 練習セッションの作成
        practice_session = None
        if user_id:
            practice_session = SessionService.create_session(
                user_id=user_id,
                session_type=SessionType.SCENARIO_PRACTICE.value,
                scenario_id=scenario_id,
                ai_model=model_name
            )
            # ペルソナIDも記録
            practice_session.persona_id = persona.id
        
        # 会話メモリの取得・初期化
        memory_key = f'scenario_memory_{scenario_id}_{persona.persona_code}'
        if memory_key not in session:
            session[memory_key] = []
        scenario_memory = session[memory_key]
        
        # 会話履歴の構築
        conversation_history = []
        for item in scenario_memory:
            if 'human' in item:
                conversation_history.append({'role': 'user', 'content': item['human']})
            if 'ai' in item:
                conversation_history.append({'role': 'assistant', 'content': item['ai']})
        
        # ペルソナプロンプトの生成
        prompt = integration_service.create_scenario_prompt(
            scenario_id=scenario_id,
            persona=persona,
            user_message=message if message else 'シナリオを開始してください。',
            conversation_history=conversation_history,
            user_id=user_id
        )
        
        # メッセージリストの構築
        messages = [{'role': 'system', 'content': prompt}]
        if message:
            messages.append({'role': 'user', 'content': message})
        else:
            messages.append({'role': 'user', 'content': 'シナリオを開始してください。'})
        
        # Redis Pub/Subチャンネルの作成
        channel = task_manager.create_session_channel(f'persona_scenario_{session_id}')
        
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
                'persona_code': persona.persona_code,
                'persona_name': persona.name,
                'message_count': len(scenario_memory)
            }
        )
        
        # タスク開始を通知
        task_manager.notify_task_start(channel, task.id, 'persona_scenario_streaming')
        
        # 会話ログの保存
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
        
        # 対話記録
        if user_id and practice_session:
            integration_service.record_scenario_interaction(
                user_id=user_id,
                persona_id=persona.id,
                session_id=practice_session.id,
                scenario_id=scenario_id,
                interaction_data={
                    'total_exchanges': len(scenario_memory),
                    'user_word_count': len(message.split()) if message else 0
                }
            )
        
        # SSEレスポンスを返す
        response = RedisSSEBridge.create_sse_response(channel)
        response.headers['X-Session-ID'] = session_id
        response.headers['X-Task-ID'] = task.id
        response.headers['X-Persona-Code'] = persona.persona_code
        
        return response
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Persona scenario streaming error: {str(e)}", exc_info=True)
        return jsonify({'error': '予期しないエラーが発生しました'}), 500


@persona_scenarios_bp.route('/save-response', methods=['POST'])
def save_persona_response():
    """
    ペルソナのレスポンスを保存
    
    Request JSON:
        {
            "session_id": str,
            "scenario_id": str,
            "persona_code": str,
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
        
        scenario_id = data.get('scenario_id')
        persona_code = data.get('persona_code')
        practice_session_id = data.get('practice_session_id')
        
        # 会話ログの保存
        if practice_session_id:
            ConversationService.add_log(
                session_id=practice_session_id,
                message=message,
                is_user=False
            )
        
        # セッションメモリへの保存
        memory_key = f'scenario_memory_{scenario_id}_{persona_code}'
        if memory_key not in session:
            session[memory_key] = []
        
        session[memory_key].append({'ai': message})
        session.modified = True
        
        # ペルソナの応答語数を記録
        if practice_session_id and data.get('user_id'):
            from models import UserPersonaInteraction
            interaction = UserPersonaInteraction.query.filter_by(
                session_id=practice_session_id
            ).first()
            
            if interaction:
                interaction.persona_word_count += len(message.split())
                from models import db
                db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'レスポンスを保存しました'
        })
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Save persona response error: {str(e)}", exc_info=True)
        return jsonify({'error': '保存に失敗しました'}), 500


@persona_scenarios_bp.route('/persona-stats/<persona_code>', methods=['GET'])
def get_persona_stats(persona_code: str):
    """
    ペルソナの統計情報を取得
    
    Returns:
        {
            "total_interactions": int,
            "unique_users": int,
            "average_rapport": float,
            "scenario_breakdown": dict
        }
    """
    try:
        from models import AIPersona
        
        # ペルソナを取得
        persona = AIPersona.query.filter_by(persona_code=persona_code).first()
        if not persona:
            raise ValidationError("ペルソナが見つかりません")
        
        # 統計情報を取得
        stats = integration_service.get_persona_scenario_stats(persona.id)
        
        return jsonify(stats)
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Get persona stats error: {str(e)}", exc_info=True)
        return jsonify({'error': '統計情報の取得に失敗しました'}), 500