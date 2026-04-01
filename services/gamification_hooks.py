"""
ゲーミフィケーション統合フック

既存ルート（シナリオ / 雑談 / 観戦）のフィードバック完了時に呼び出し、
XP計算 → クエスト進捗 → バッジ判定 → アンロック判定 のチェーンを実行する。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.badge_service import BadgeService
from services.gamification_service import GamificationService
from services.quest_service import QuestService
from services.session_service import SessionService
from services.unlock_service import UnlockService, get_scenario_difficulty
from services.user_data_service import UserDataService


_session_svc = SessionService()


def _get_user_id() -> str:
    return _session_svc.get_user_id()


def on_scenario_feedback(
    scores: Dict[str, Any],
    scenario_id: str,
    scenario_data: Optional[dict] = None,
) -> Dict[str, Any]:
    """シナリオフィードバック完了時のゲーミフィケーションフック。

    Returns:
        追加レスポンスデータ（newly_unlocked, new_badges, quest_completed 等）
    """
    uid = _get_user_id()
    uds = UserDataService()
    gs = GamificationService(uds)

    gains = gs.calculate_xp_from_scores(scores, "normal")
    gains["scores_snapshot"] = scores
    gains["scenario_id"] = scenario_id
    xp_result = gs.add_xp(uid, gains, "scenario_completion")

    data = uds.get_user_data(uid)
    difficulty = get_scenario_difficulty(scenario_data or {})
    now = datetime.now(timezone.utc).isoformat()
    sc = data.setdefault("scenario_completions", {})
    if scenario_id not in sc:
        sc[scenario_id] = {
            "count": 0,
            "first_completed_at": now,
            "last_completed_at": now,
            "best_scores": {},
            "difficulty": difficulty,
        }
    sc[scenario_id]["count"] = int(sc[scenario_id]["count"]) + 1
    sc[scenario_id]["last_completed_at"] = now
    sc[scenario_id]["difficulty"] = difficulty

    stats = data.setdefault("stats", {})
    stats["total_scenarios_completed"] = int(stats.get("total_scenarios_completed", 0) or 0) + 1

    tried = set()
    for sid in sc:
        tried.add(sid)
    stats["unique_scenarios_tried"] = len(tried)

    uds.save_user_data(uid, data)

    qs = QuestService(uds)
    qs.get_active_quests(uid)
    completed_quests = qs.check_quest_completion(uid, {"target_key": "scenarios_today", "delta": 1})

    bs = BadgeService(uds)
    new_badges = bs.check_badge_eligibility(uid)
    for b in new_badges:
        bs.award_badge(uid, b["badge_id"])

    from services.scenario_service import ScenarioService
    us = UnlockService(uds, ScenarioService())
    newly_unlocked = us.check_and_unlock(uid)

    result: Dict[str, Any] = {}
    if newly_unlocked:
        result["newly_unlocked_levels"] = newly_unlocked
    if new_badges:
        result["new_badges"] = [b["badge_id"] for b in new_badges]
    if completed_quests:
        result["quests_completed"] = [q["quest_id"] for q in completed_quests]
    result["xp_gained"] = xp_result.get("xp_history_entry", {}).get("xp_gains", {})

    return result


def on_chat_feedback(scores: Dict[str, Any]) -> Dict[str, Any]:
    """雑談フィードバック完了時のゲーミフィケーションフック。"""
    uid = _get_user_id()
    uds = UserDataService()
    gs = GamificationService(uds)

    gains = gs.calculate_xp_from_scores(scores, "normal")
    gains["scores_snapshot"] = scores
    xp_result = gs.add_xp(uid, gains, "chat_completion")

    qs = QuestService(uds)
    qs.get_active_quests(uid)
    completed_quests = qs.check_quest_completion(uid, {"target_key": "scenarios_today", "delta": 1})

    bs = BadgeService(uds)
    new_badges = bs.check_badge_eligibility(uid)
    for b in new_badges:
        bs.award_badge(uid, b["badge_id"])

    result: Dict[str, Any] = {}
    if new_badges:
        result["new_badges"] = [b["badge_id"] for b in new_badges]
    if completed_quests:
        result["quests_completed"] = [q["quest_id"] for q in completed_quests]
    result["xp_gained"] = xp_result.get("xp_history_entry", {}).get("xp_gains", {})

    return result
