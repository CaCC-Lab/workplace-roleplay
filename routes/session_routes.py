"""
Session management routes for the workplace-roleplay application.
Handles session health, info, and management API endpoints.
"""

import sys

from flask import Blueprint, current_app, jsonify, request, session

from errors import secure_error_handler

# セキュリティ関連のインポート
try:
    from utils.security import SecurityUtils
except ImportError:

    class SecurityUtils:
        @staticmethod
        def get_safe_error_message(e):
            return str(e)


# Blueprint作成
session_bp = Blueprint("session_api", __name__)


@session_bp.route("/api/session/health", methods=["GET"])
@secure_error_handler
def session_health_check():
    """セッションストアの健全性チェック"""
    try:
        from core.extensions import get_redis_session_manager

        redis_session_manager = get_redis_session_manager()

        if redis_session_manager:
            health = redis_session_manager.health_check()
            connection_info = redis_session_manager.get_connection_info()

            return jsonify(
                {
                    "status": "healthy" if health["connected"] else "degraded",
                    "session_store": "redis" if health["connected"] else "fallback",
                    "details": {
                        "redis_connected": health["connected"],
                        "fallback_active": health["fallback_active"],
                        "connection_info": connection_info,
                        "error": health.get("error"),
                    },
                }
            )
        else:
            return jsonify(
                {
                    "status": "healthy",
                    "session_store": "filesystem",
                    "details": {
                        "redis_connected": False,
                        "fallback_active": False,
                        "session_dir": current_app.config.get(
                            "SESSION_FILE_DIR", "./flask_session"
                        ),
                    },
                }
            )

    except Exception as e:
        print(f"Error in session_health_check: {str(e)}")
        return (
            jsonify(
                {
                    "error": f"セッションヘルスチェックに失敗しました: {SecurityUtils.get_safe_error_message(e)}"
                }
            ),
            500,
        )


@session_bp.route("/api/session/info", methods=["GET"])
@secure_error_handler
def session_info():
    """現在のセッション情報を取得"""
    try:
        session_data = {
            "session_id": session.get("_id", "N/A"),
            "session_keys": list(session.keys()),
            "session_type": current_app.config.get("SESSION_TYPE", "unknown"),
            "permanent": session.permanent,
            "has_chat_history": "chat_history" in session,
            "has_scenario_history": "scenario_chat_history" in session,
            "current_scenario": session.get("current_scenario_id"),
            "model_choice": session.get("model_choice", "N/A"),
        }

        session_size = sys.getsizeof(str(dict(session)))
        session_data["estimated_size_bytes"] = session_size

        return jsonify(session_data)

    except Exception as e:
        print(f"Error in get_session_info: {str(e)}")
        return (
            jsonify(
                {
                    "error": f"セッション情報取得に失敗しました: {SecurityUtils.get_safe_error_message(e)}"
                }
            ),
            500,
        )


@session_bp.route("/api/session/clear", methods=["POST"])
def clear_session_data():
    """セッションデータのクリア"""
    try:
        data = request.json or {}
        clear_type = data.get("type", "all")

        if clear_type == "all":
            session.clear()
            message = "全セッションデータをクリアしました"
        elif clear_type == "chat":
            session.pop("chat_history", None)
            message = "チャット履歴をクリアしました"
        elif clear_type == "scenario":
            session.pop("scenario_chat_history", None)
            session.pop("current_scenario_id", None)
            message = "シナリオ履歴をクリアしました"
        elif clear_type == "watch":
            session.pop("watch_history", None)
            message = "観戦履歴をクリアしました"
        else:
            return jsonify({"error": "無効なクリアタイプです"}), 400

        return jsonify(
            {"status": "success", "message": message, "cleared_type": clear_type}
        )

    except Exception as e:
        return jsonify({"error": f"セッションクリアエラー: {str(e)}"}), 500
