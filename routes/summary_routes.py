"""
会話まとめ・要約 API ルート
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from services.session_service import SessionService

summary_bp = Blueprint("summary", __name__, url_prefix="/api/summary")

_session_svc = SessionService()


def _user_id() -> str:
    return _session_svc.get_user_id()


@summary_bp.route("/generate", methods=["POST"])
def generate_summary():
    """会話要約を生成"""
    try:
        from services.summary_service import SummaryService

        payload = request.get_json(silent=True) or {}
        history = payload.get("history") or []
        mode = payload.get("mode", "scenario")

        svc = SummaryService()
        result = svc.generate_summary(history, mode)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
