"""非同期シナリオAPIエンドポイント"""
from flask import Blueprint, request, Response, jsonify, session
from typing import Dict, Any, Generator
import json
import logging
import traceback

logger = logging.getLogger(__name__)

bp = Blueprint("async_scenario", __name__, url_prefix="/api/async/scenario")


@bp.route("/stream", methods=["POST"])
def stream_scenario_message() -> Response:
    """シナリオメッセージをストリーミング形式で送信"""
    try:
        # サービスの遅延インポート
        from ..services.conversation_service import ConversationService
        from ..services.scenario_service import ScenarioService
        from ..models import db, ScenarioSession, SessionMessage
        
        conversation_service = ConversationService()
        scenario_service = ScenarioService()
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "リクエストボディが必要です"}), 400
        
        message = data.get("message", "").strip()
        scenario_id = data.get("scenario_id")
        is_initial = data.get("is_initial", False)
        
        if not scenario_id:
            return jsonify({"error": "scenario_idが必要です"}), 400
        
        # セッションからモデル情報を取得
        selected_models = session.get("selected_models", {})
        model_id = selected_models.get("scenario", "gemini/gemini-1.5-flash")
        
        # シナリオセッションを取得または作成
        session_id = session.get(f"scenario_session_{scenario_id}")
        if not session_id:
            # 新規セッション作成
            new_session = ScenarioSession(
                scenario_id=scenario_id,
                model_id=model_id,
                status="active"
            )
            db.session.add(new_session)
            db.session.commit()
            session_id = new_session.id
            session[f"scenario_session_{scenario_id}"] = session_id
        
        def generate() -> Generator[str, None, None]:
            """レスポンスをストリーミング生成"""
            try:
                if is_initial:
                    # 初回メッセージの場合
                    scenario_data = scenario_service.get_scenario(scenario_id)
                    if not scenario_data:
                        yield f"data: {json.dumps({'error': 'シナリオが見つかりません'})}\n\n"
                        return
                    
                    # シナリオの初回メッセージを生成
                    initial_prompt = scenario_data.get("initial_message", "")
                    if initial_prompt:
                        # AIペルソナからの初回メッセージ
                        stream = conversation_service.get_scenario_response_stream(
                            message="",  # 空メッセージ
                            scenario_id=scenario_id,
                            model_id=model_id,
                            is_initial=True
                        )
                        
                        for chunk in stream:
                            yield f"data: {json.dumps({'content': chunk})}\n\n"
                    else:
                        yield f"data: {json.dumps({'content': 'こんにちは。今日はどのようなお手伝いができますか？'})}\n\n"
                else:
                    # 通常のメッセージ処理
                    if not message:
                        yield f"data: {json.dumps({'error': 'メッセージが必要です'})}\n\n"
                        return
                    
                    # メッセージを保存
                    user_message = SessionMessage(
                        session_id=session_id,
                        role="user",
                        content=message
                    )
                    db.session.add(user_message)
                    db.session.commit()
                    
                    # AI応答を生成
                    stream = conversation_service.get_scenario_response_stream(
                        message=message,
                        scenario_id=scenario_id,
                        model_id=model_id,
                        is_initial=False
                    )
                    
                    full_response = ""
                    for chunk in stream:
                        full_response += chunk
                        yield f"data: {json.dumps({'content': chunk})}\n\n"
                    
                    # AI応答を保存
                    ai_message = SessionMessage(
                        session_id=session_id,
                        role="assistant",
                        content=full_response
                    )
                    db.session.add(ai_message)
                    db.session.commit()
                
                yield f"data: {json.dumps({'status': 'complete'})}\n\n"
                
            except Exception as e:
                logger.error(f"Streaming error: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        logger.error(f"Stream scenario message error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@bp.route("/history", methods=["GET"])
def get_scenario_history() -> tuple[Dict[str, Any], int]:
    """シナリオの会話履歴を取得"""
    try:
        # サービスの遅延インポート
        from ..models import SessionMessage
        scenario_id = request.args.get("scenario_id")
        if not scenario_id:
            return {"error": "scenario_idが必要です"}, 400
        
        session_id = session.get(f"scenario_session_{scenario_id}")
        if not session_id:
            return {"messages": []}, 200
        
        # 会話履歴を取得
        messages = SessionMessage.query.filter_by(
            session_id=session_id
        ).order_by(SessionMessage.created_at).all()
        
        return {
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.created_at.isoformat()
                }
                for msg in messages
            ]
        }, 200
        
    except Exception as e:
        logger.error(f"Get scenario history error: {str(e)}")
        return {"error": str(e)}, 500