"""
3者会話（ユーザー介入）API ルート
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from services.session_service import SessionService

three_way_bp = Blueprint("three_way", __name__, url_prefix="/api/three-way")

_session_svc = SessionService()


def _user_id() -> str:
    return _session_svc.get_user_id()


@three_way_bp.route("/join", methods=["POST"])
def join():
    """観戦モードから3者会話に参加"""
    try:
        from services.three_way_service import ThreeWayConversationService

        uid = _user_id()
        history = session.get("watch_history") or []
        svc = ThreeWayConversationService()
        result = svc.join_conversation(uid, history)
        if result.get("joined"):
            session["three_way_turn_order"] = result["turn_order"]
            session["three_way_active"] = True
            session.modified = True
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@three_way_bp.route("/message", methods=["POST"])
def send_message():
    """ユーザー発言を追加"""
    try:
        from services.three_way_service import ThreeWayConversationService

        payload = request.get_json(silent=True) or {}
        message = payload.get("message", "")
        if not message.strip():
            return jsonify({"error": "メッセージが空です"}), 400
        history = session.get("watch_history") or []
        turn_order = session.get("three_way_turn_order") or ["A", "B", "user"]
        svc = ThreeWayConversationService()
        result = svc.add_user_message(history, message, turn_order)
        session["watch_history"] = result["updated_history"]
        session.modified = True
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@three_way_bp.route("/leave", methods=["POST"])
def leave():
    """3者会話を退出して観戦モードに戻る"""
    try:
        from services.three_way_service import ThreeWayConversationService

        uid = _user_id()
        svc = ThreeWayConversationService()
        result = svc.leave_conversation(uid)
        session.pop("three_way_turn_order", None)
        session["three_way_active"] = False
        session.modified = True
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
