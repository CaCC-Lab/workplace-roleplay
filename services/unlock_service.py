"""
シナリオの段階的アンロック管理（ゲーミフィケーション）
"""

from __future__ import annotations

from typing import Any, Dict, List

_DIFFICULTY_MAP = {
    "初級": "beginner", "beginner": "beginner",
    "中級": "intermediate", "intermediate": "intermediate",
    "上級": "advanced", "advanced": "advanced",
}


def get_scenario_difficulty(scenario_data: dict) -> str:
    """シナリオの難易度を取得。未設定は beginner"""
    if not scenario_data:
        return "beginner"
    d = scenario_data.get("difficulty", "beginner")
    if not isinstance(d, str):
        return "beginner"
    return _DIFFICULTY_MAP.get(d.lower(), "beginner")


class UnlockService:
    """シナリオの段階的アンロック管理"""

    UNLOCK_THRESHOLDS = {
        "intermediate": 3,
        "advanced": 3,
    }

    def __init__(self, user_data_service: Any, scenario_service: Any) -> None:
        self._uds = user_data_service
        self._scenarios = scenario_service

    def _count_completions_for_difficulty(self, data: dict, difficulty: str) -> int:
        total = 0
        for _sid, info in (data.get("scenario_completions") or {}).items():
            if not isinstance(info, dict):
                continue
            if info.get("difficulty") == difficulty:
                total += int(info.get("count", 0) or 0)
        return total

    def _ensure_unlock_flags(self, data: dict) -> dict:
        us = data.setdefault("unlock_status", {})
        us.setdefault("beginner", True)
        us.setdefault("intermediate", False)
        us.setdefault("advanced", False)
        return us

    def check_and_unlock(self, user_id: str) -> List[str]:
        """完了数に基づき新規アンロックを判定。新たにアンロックされたレベル名のリスト"""
        data = self._uds.get_user_data(user_id)
        us = self._ensure_unlock_flags(data)
        newly: List[str] = []

        beg_count = self._count_completions_for_difficulty(data, "beginner")
        int_count = self._count_completions_for_difficulty(data, "intermediate")

        if not us.get("intermediate") and beg_count >= self.UNLOCK_THRESHOLDS["intermediate"]:
            us["intermediate"] = True
            newly.append("intermediate")
        if not us.get("advanced") and int_count >= self.UNLOCK_THRESHOLDS["advanced"]:
            us["advanced"] = True
            newly.append("advanced")

        self._uds.save_user_data(user_id, data)
        return newly

    def is_scenario_unlocked(self, user_id: str, scenario_id: str) -> bool:
        data = self._uds.get_user_data(user_id)
        us = self._ensure_unlock_flags(data)
        scen = self._scenarios.get_scenario_by_id(scenario_id) if self._scenarios else None
        diff = get_scenario_difficulty(scen or {})
        if diff == "beginner":
            return bool(us.get("beginner"))
        if diff == "intermediate":
            return bool(us.get("intermediate"))
        if diff == "advanced":
            return bool(us.get("advanced"))
        return True

    def get_unlock_progress(self, user_id: str) -> dict:
        data = self._uds.get_user_data(user_id)
        us = self._ensure_unlock_flags(data)
        beg_done = self._count_completions_for_difficulty(data, "beginner")
        int_done = self._count_completions_for_difficulty(data, "intermediate")
        return {
            "beginner": {"unlocked": us.get("beginner", True), "current": beg_done, "needed": 0},
            "intermediate": {
                "unlocked": us.get("intermediate", False),
                "current": beg_done,
                "needed": self.UNLOCK_THRESHOLDS["intermediate"],
            },
            "advanced": {
                "unlocked": us.get("advanced", False),
                "current": int_done,
                "needed": self.UNLOCK_THRESHOLDS["advanced"],
            },
        }

    def get_unlock_status(self, user_id: str) -> dict:
        """全シナリオのアンロック状態と一覧を返す"""
        data = self._uds.get_user_data(user_id)
        us = self._ensure_unlock_flags(data)
        beg_done = self._count_completions_for_difficulty(data, "beginner")
        int_done = self._count_completions_for_difficulty(data, "intermediate")
        progress = {
            "intermediate": {"current": beg_done, "needed": self.UNLOCK_THRESHOLDS["intermediate"]},
            "advanced": {"current": int_done, "needed": self.UNLOCK_THRESHOLDS["advanced"]},
        }
        scenarios_raw = self._scenarios.get_all_scenarios() if self._scenarios else {}
        scenarios_out = []
        for sid, sdata in scenarios_raw.items():
            diff = get_scenario_difficulty(sdata if isinstance(sdata, dict) else {})
            unlocked = bool(us.get(diff, False))
            entry: Dict[str, Any] = {
                "scenario_id": sid,
                "difficulty": diff,
                "unlocked": unlocked,
            }
            if not unlocked and diff in progress:
                entry["unlock_condition"] = {
                    "level": diff,
                    "required_completions": progress[diff]["needed"],
                    "current_completions": progress[diff]["current"],
                }
            scenarios_out.append(entry)

        return {
            "unlock_status": {
                "beginner": us.get("beginner"),
                "intermediate": us.get("intermediate"),
                "advanced": us.get("advanced"),
            },
            "scenarios": scenarios_out,
        }
