"""
チュートリアル・ヘルプ API ルート
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from services.session_service import SessionService

tutorial_bp = Blueprint("tutorial", __name__, url_prefix="/api/tutorial")

_session_svc = SessionService()


def _user_id() -> str:
    return _session_svc.get_user_id()


@tutorial_bp.route("/steps", methods=["GET"])
def get_steps():
    """チュートリアルステップ取得"""
    try:
        from services.tutorial_service import TutorialService

        mode = request.args.get("mode", "scenario")
        svc = TutorialService()
        return jsonify(svc.get_tutorial_steps(mode))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tutorial_bp.route("/progress", methods=["GET"])
def get_progress():
    """ユーザー進捗取得"""
    try:
        from services.tutorial_service import TutorialService

        uid = _user_id()
        svc = TutorialService()
        return jsonify(svc.get_user_progress(uid))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tutorial_bp.route("/complete", methods=["POST"])
def mark_complete():
    """ステップ完了マーク"""
    try:
        from services.tutorial_service import TutorialService

        uid = _user_id()
        payload = request.get_json(silent=True) or {}
        mode = payload.get("mode", "scenario")
        step = int(payload.get("step", 0))
        svc = TutorialService()
        return jsonify(svc.mark_step_complete(uid, mode, step))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tutorial_bp.route("/faq", methods=["GET"])
def get_faq():
    """FAQ取得"""
    try:
        from services.tutorial_service import TutorialService

        svc = TutorialService()
        return jsonify(svc.get_faq())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tutorial_bp.route("/first-visit", methods=["GET"])
def check_first_visit():
    """初回訪問チェック"""
    try:
        from services.tutorial_service import TutorialService

        uid = _user_id()
        svc = TutorialService()
        return jsonify({"first_visit": svc.is_first_visit(uid)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
