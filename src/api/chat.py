"""チャットAPI"""
from flask import request, jsonify, current_app, session
from typing import Dict, Any

from ..services import ChatService, SessionService


def chat() -> tuple[Dict[str, Any], int]:
    """チャットエンドポイント
    
    Returns:
        レスポンスとHTTPステータスコード
    """
    try:
        # リクエストデータの取得
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        message = data.get("message", "").strip()
        if not message:
            return jsonify({"error": "Message is required"}), 400
        
        model_name = data.get("model", current_app.config["DEFAULT_MODEL"])
        
        # セッション管理
        session_service = SessionService()
        session_id = session.get("session_id")
        if not session_id:
            session_id = session_service.create_session()
            session["session_id"] = session_id
        
        # チャットサービスの初期化
        chat_service = ChatService()
        
        # メッセージの処理
        response = chat_service.process_message(
            session_id=session_id,
            message=message,
            model_name=model_name
        )
        
        return jsonify({
            "response": response,
            "session_id": session_id
        }), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Chat error: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": "チャット処理中にエラーが発生しました"
        }), 500