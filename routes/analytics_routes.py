"""
学習分析ダッシュボード API ルート
"""

from __future__ import annotations

from flask import Blueprint, jsonify

from services.session_service import SessionService
from services.user_data_service import UserDataService

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")

_session_svc = SessionService()


def _user_id() -> str:
    return _session_svc.get_user_id()


@analytics_bp.route("/practice-stats", methods=["GET"])
def practice_stats():
    """練習統計"""
    try:
        from services.analytics_service import AnalyticsService

        uid = _user_id()
        uds = UserDataService()
        data = uds.get_user_data(uid)
        svc = AnalyticsService()
        return jsonify(svc.get_practice_stats(uid, data))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/skill-progress", methods=["GET"])
def skill_progress():
    """6軸スキル進捗"""
    try:
        from services.analytics_service import AnalyticsService

        uid = _user_id()
        uds = UserDataService()
        data = uds.get_user_data(uid)
        svc = AnalyticsService()
        return jsonify(svc.get_skill_progress(uid, data))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/weakness", methods=["GET"])
def weakness_report():
    """弱点レポート"""
    try:
        from services.analytics_service import AnalyticsService

        uid = _user_id()
        uds = UserDataService()
        data = uds.get_user_data(uid)
        svc = AnalyticsService()
        return jsonify(svc.get_weakness_report(uid, data))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/weekly-summary", methods=["GET"])
def weekly_summary():
    """週次サマリー"""
    try:
        from services.analytics_service import AnalyticsService

        uid = _user_id()
        uds = UserDataService()
        data = uds.get_user_data(uid)
        svc = AnalyticsService()
        return jsonify(svc.get_weekly_summary(uid, data))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
