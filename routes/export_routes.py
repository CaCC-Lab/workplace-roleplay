"""
データエクスポート API ルート
"""

from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from services.session_service import SessionService
from services.user_data_service import UserDataService

export_bp = Blueprint("export", __name__, url_prefix="/api/export")

_session_svc = SessionService()


def _user_id() -> str:
    return _session_svc.get_user_id()


@export_bp.route("/csv", methods=["POST"])
def export_csv():
    """会話履歴をCSVエクスポート"""
    try:
        from services.export_service import ExportService

        uid = _user_id()
        payload = request.get_json(silent=True) or {}
        history = payload.get("history") or []
        svc = ExportService()
        csv_text = svc.export_conversations_csv(uid, history)
        return Response(csv_text, mimetype="text/csv",
                        headers={"Content-Disposition": "attachment; filename=conversations.csv"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@export_bp.route("/json", methods=["POST"])
def export_json():
    """会話履歴をJSONエクスポート"""
    try:
        from services.export_service import ExportService

        uid = _user_id()
        payload = request.get_json(silent=True) or {}
        history = payload.get("history") or []
        svc = ExportService()
        json_text = svc.export_conversations_json(uid, history)
        return Response(json_text, mimetype="application/json",
                        headers={"Content-Disposition": "attachment; filename=conversations.json"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@export_bp.route("/report", methods=["GET"])
def export_report():
    """学習レポート"""
    try:
        from services.export_service import ExportService

        uid = _user_id()
        uds = UserDataService()
        data = uds.get_user_data(uid)
        svc = ExportService()
        return jsonify(svc.export_learning_report(uid, data))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
