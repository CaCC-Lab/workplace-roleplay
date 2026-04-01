"""
ゲーミフィケーション API ルート
"""

from __future__ import annotations

from flask import Blueprint, jsonify, session

from utils.security import RateLimiter

from services.badge_service import BadgeService
from services.gamification_service import GamificationService
from services.quest_service import QuestService
from services.scenario_service import ScenarioService
from services.session_service import SessionService
from services.unlock_service import UnlockService
from services.user_data_service import UserDataService

gamification_bp = Blueprint("gamification", __name__, url_prefix="/api/gamification")

_session_svc = SessionService()

# グローバル rate_limiter と競合しないようダッシュボード専用
_gamification_dashboard_limiter = RateLimiter(max_requests=200, window_seconds=60)


def _user_id() -> str:
    return _session_svc.get_user_id()


@gamification_bp.route("/dashboard", methods=["GET"])
@_gamification_dashboard_limiter.rate_limit(max_requests=200, window_seconds=60)
def dashboard():
    """ダッシュボード（XP、クエスト、バッジ概要）"""
    try:
        uid = _user_id()
        uds = UserDataService()
        return jsonify(
            {
                "skill_xp": GamificationService(uds).get_skill_summary(uid),
                "quests": QuestService(uds).get_active_quests(uid),
                "badges_overview": BadgeService(uds).get_all_badges(uid),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@gamification_bp.route("/growth", methods=["GET"])
def growth():
    """成長グラフデータ"""
    try:
        return jsonify(GamificationService(UserDataService()).get_growth_data(_user_id()))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@gamification_bp.route("/quests", methods=["GET"])
def quests():
    """アクティブクエスト一覧"""
    try:
        return jsonify(QuestService(UserDataService()).get_active_quests(_user_id()))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@gamification_bp.route("/badges", methods=["GET"])
def badges():
    """バッジ一覧"""
    try:
        return jsonify(BadgeService(UserDataService()).get_all_badges(_user_id()))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@gamification_bp.route("/unlock-status", methods=["GET"])
def unlock_status():
    """シナリオアンロック状態"""
    try:
        return jsonify(UnlockService(UserDataService(), ScenarioService()).get_unlock_status(_user_id()))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
