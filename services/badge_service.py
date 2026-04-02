"""
学習態度ベースのバッジ管理（ゲーミフィケーション）
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.gamification_constants import SIX_AXES, utc_now_iso

BADGE_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "badge_id": "first_step",
        "name": "はじめの一歩",
        "category": "継続性",
        "target_value": 1,
        "metric": "total_scenarios_completed",
    },
    {
        "badge_id": "three_day_streak",
        "name": "3日連続",
        "category": "継続性",
        "target_value": 3,
        "metric": "consecutive_days",
    },
    {
        "badge_id": "seven_day_streak",
        "name": "1週間の習慣",
        "category": "継続性",
        "target_value": 7,
        "metric": "consecutive_days",
    },
    {
        "badge_id": "explorer",
        "name": "探検家",
        "category": "多様性",
        "target_value": 5,
        "metric": "unique_scenarios_tried",
    },
    {
        "badge_id": "all_rounder",
        "name": "オールラウンダー",
        "category": "多様性",
        "target_value": 6,
        "metric": "axes_with_xp",
    },
    {
        "badge_id": "quiz_challenger",
        "name": "クイズチャレンジャー",
        "category": "多様性",
        "target_value": 10,
        "metric": "total_quizzes_answered",
    },
    {
        "badge_id": "growth_spurt",
        "name": "急成長",
        "category": "改善度",
        "target_value": 1,
        "metric": "weekly_growth_20pct",
    },
    {
        "badge_id": "personal_best",
        "name": "自己ベスト更新",
        "category": "改善度",
        "target_value": 1,
        "metric": "personal_best_hit",
    },
    {
        "badge_id": "balanced_growth",
        "name": "バランス成長",
        "category": "改善度",
        "target_value": 1,
        "metric": "balanced_growth",
    },
]


class BadgeService:
    """学習態度ベースのバッジ管理"""

    def __init__(self, user_data_service: Any) -> None:
        self._uds = user_data_service

    def _stats(self, data: dict) -> dict:
        return data.get("stats") or {}

    def _earned_ids(self, data: dict) -> set:
        earned = data.get("badges", {}).get("earned") or []
        return {e.get("badge_id") for e in earned if isinstance(e, dict)}

    def _metric_value(self, data: dict, metric: str) -> int:
        st = self._stats(data)
        if metric == "total_scenarios_completed":
            return int(st.get("total_scenarios_completed", 0) or 0)
        if metric == "consecutive_days":
            return int(st.get("consecutive_days", 0) or 0)
        if metric == "unique_scenarios_tried":
            return int(st.get("unique_scenarios_tried", 0) or 0)
        if metric == "total_quizzes_answered":
            return int(st.get("total_quizzes_answered", 0) or 0)
        if metric == "axes_with_xp":
            skill = data.get("skill_xp") or {}
            return sum(1 for a in SIX_AXES if int(skill.get(a, 0) or 0) > 0)
        if metric == "weekly_growth_20pct":
            return 1 if st.get("weekly_growth_20pct") else 0
        if metric == "personal_best_hit":
            return 1 if st.get("personal_best_hit") else 0
        if metric == "balanced_growth":
            return 1 if st.get("balanced_growth") else 0
        return 0

    def check_badge_eligibility(self, user_id: str) -> list:
        """新規獲得バッジのリスト"""
        data = self._uds.get_user_data(user_id)
        earned = self._earned_ids(data)
        new_badges: List[dict] = []
        for b in BADGE_DEFINITIONS:
            bid = b["badge_id"]
            if bid in earned:
                continue
            cur = self._metric_value(data, b["metric"])
            need = int(b["target_value"])
            if cur >= need:
                new_badges.append(b)
        return new_badges

    def get_all_badges(self, user_id: str) -> dict:
        data = self._uds.get_user_data(user_id)
        earned = self._earned_ids(data)
        out = []
        for b in BADGE_DEFINITIONS:
            bid = b["badge_id"]
            cur = self._metric_value(data, b["metric"])
            need = int(b["target_value"])
            item = {
                "badge_id": bid,
                "name": b["name"],
                "category": b["category"],
                "earned": bid in earned,
            }
            if bid not in earned:
                item["condition"] = b["metric"]
                item["current_value"] = cur
                item["target_value"] = need
            out.append({"badge": item})
        return {"badges": out}

    def award_badge(self, user_id: str, badge_id: str) -> dict:
        data = self._uds.get_user_data(user_id)
        badges = data.setdefault("badges", {})
        earned = badges.setdefault("earned", [])
        if any(e.get("badge_id") == badge_id for e in earned if isinstance(e, dict)):
            return {"notification": None, "already_earned": True}
        rec = {"badge_id": badge_id, "earned_at": utc_now_iso()}
        earned.append(rec)
        self._uds.save_user_data(user_id, data)
        try:
            from services.gamification_vibelogger import get_gamification_vibe_logger

            get_gamification_vibe_logger().info(
                operation="BadgeService.award_badge",
                message="Badge awarded",
                context={"user_id": user_id, "badge_id": badge_id},
            )
        except Exception:
            pass
        meta = next((b for b in BADGE_DEFINITIONS if b["badge_id"] == badge_id), None)
        title = meta["name"] if meta else badge_id
        return {
            "notification": {
                "type": "badge_earned",
                "badge_id": badge_id,
                "title": title,
                "message": f"バッジ「{title}」を獲得しました。",
            },
            "already_earned": False,
        }

    def get_badge_progress(self, user_id: str, badge_id: str) -> dict:
        data = self._uds.get_user_data(user_id)
        b = next((x for x in BADGE_DEFINITIONS if x["badge_id"] == badge_id), None)
        if not b:
            return {"error": "unknown badge"}
        cur = self._metric_value(data, b["metric"])
        need = int(b["target_value"])
        return {
            "badge_id": badge_id,
            "current_value": cur,
            "target_value": need,
            "condition": b["metric"],
        }
