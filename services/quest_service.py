"""
デイリー・ウィークリークエスト管理（ゲーミフィケーション）
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

DAILY_QUEST_TEMPLATES = [
    {
        "id": "daily_scenario",
        "description": "シナリオを1つ完了する",
        "target_key": "scenarios_today",
        "target_value": 1,
        "bonus_xp": 20,
    },
    {
        "id": "daily_journal",
        "description": "ジャーナルに記入する",
        "target_key": "journal_today",
        "target_value": 1,
        "bonus_xp": 15,
    },
    {
        "id": "daily_watch",
        "description": "観戦モードを体験する",
        "target_key": "watch_today",
        "target_value": 1,
        "bonus_xp": 15,
    },
]

WEEKLY_QUEST_TEMPLATES = [
    {
        "id": "weekly_scenarios",
        "description": "シナリオを3つ完了する",
        "target_key": "scenarios_week",
        "target_value": 3,
        "bonus_xp": 50,
    },
    {
        "id": "weekly_all_axes",
        "description": "全6軸でXPを獲得する",
        "target_key": "axes_gained_week",
        "target_value": 6,
        "bonus_xp": 60,
    },
    {
        "id": "weekly_quiz",
        "description": "クイズに5問正解する",
        "target_key": "quiz_correct_week",
        "target_value": 5,
        "bonus_xp": 40,
    },
]


class QuestService:
    """デイリー・ウィークリークエスト管理"""

    def __init__(
        self,
        user_data_service: Any,
        now: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self._uds = user_data_service
        self._now = now or (lambda: datetime.now(timezone.utc))

    def _now_dt(self) -> datetime:
        return self._now()

    def _is_quest_expired(self, quest: dict) -> bool:
        exp = quest.get("expires_at")
        if not exp:
            return True
        try:
            ex = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
        except Exception:
            return True
        if ex.tzinfo is None:
            ex = ex.replace(tzinfo=timezone.utc)
        return self._now_dt() >= ex

    def _end_of_day(self, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        d = dt.date()
        return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=dt.tzinfo) + timedelta(seconds=1)

    def _end_of_week(self, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # 日曜終了を週末とする（日曜日に呼ばれた場合は当日の日曜を期限にせず次の日曜にする）
        days_ahead = (6 - dt.weekday()) % 7 or 7
        end_date = (dt + timedelta(days=days_ahead)).date()
        return datetime(
            end_date.year,
            end_date.month,
            end_date.day,
            23,
            59,
            59,
            tzinfo=dt.tzinfo,
        ) + timedelta(seconds=1)

    def _generate_quests(self, templates: list, quest_type: str, id_suffix: str, expires: str) -> list:
        created = self._now_dt().isoformat()
        return [
            {
                "quest_id": f"{t['id']}_{id_suffix}",
                "type": quest_type,
                "description": t["description"],
                "target_value": int(t["target_value"]),
                "current_value": 0,
                "bonus_xp": int(t["bonus_xp"]),
                "target_key": t["target_key"],
                "created_at": created,
                "expires_at": expires,
                "completed": False,
            }
            for t in templates
        ]

    def generate_daily_quests(self, user_id: str) -> list:
        """デイリークエストを生成（当日終了）"""
        now = self._now_dt()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return self._generate_quests(
            DAILY_QUEST_TEMPLATES, "daily",
            now.date().isoformat(),
            self._end_of_day(now).isoformat(),
        )

    def generate_weekly_quests(self, user_id: str) -> list:
        """ウィークリークエストを生成（週末まで）"""
        now = self._now_dt()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        iso = now.isocalendar()
        return self._generate_quests(
            WEEKLY_QUEST_TEMPLATES, "weekly",
            f"{iso[0]}-W{iso[1]:02d}",
            self._end_of_week(now).isoformat(),
        )

    def get_active_quests(self, user_id: str) -> dict:
        """有効なデイリー/ウィークリークエスト。期限切れは再生成"""
        data = self._uds.get_user_data(user_id)
        q = data.setdefault("quests", {})
        daily: List[dict] = [d for d in (q.get("daily") or []) if not self._is_quest_expired(d)]
        weekly: List[dict] = [w for w in (q.get("weekly") or []) if not self._is_quest_expired(w)]
        dirty = False

        if not daily:
            daily = self.generate_daily_quests(user_id)
            dirty = True
        if not weekly:
            weekly = self.generate_weekly_quests(user_id)
            dirty = True

        q["daily"] = daily
        q["weekly"] = weekly
        if dirty:
            self._uds.save_user_data(user_id, data)
        return {"daily": daily, "weekly": weekly}

    def check_quest_completion(self, user_id: str, activity: dict) -> list:
        """アクティビティに基づきクエスト完了を判定。完了したクエストのリスト"""
        if activity is None:
            activity = {}
        data = self._uds.get_user_data(user_id)
        quests = data.setdefault("quests", {})
        daily = list(quests.get("daily") or [])
        weekly = list(quests.get("weekly") or [])
        completed: List[dict] = []
        key = activity.get("target_key") or activity.get("type")
        delta = int(activity.get("delta", 1) or 0)

        def process(lst: List[dict]) -> None:
            for qu in lst:
                if qu.get("completed"):
                    continue
                tk = qu.get("target_key")
                if key and tk == key:
                    qu["current_value"] = int(qu.get("current_value", 0) or 0) + max(delta, 0)
                tv = int(qu.get("target_value", 0) or 0)
                cv = int(qu.get("current_value", 0) or 0)
                if tv <= 0:
                    continue
                if cv >= tv:
                    qu["completed"] = True
                    completed.append(dict(qu))

        process(daily)
        process(weekly)
        quests["daily"] = daily
        quests["weekly"] = weekly

        skill = data.setdefault("skill_xp", {})
        for c in completed:
            bx = int(c.get("bonus_xp", 0) or 0)
            if bx > 0:
                # 均等配分せずボーナスを professionalism に集約（簡易）
                skill["professionalism"] = int(skill.get("professionalism", 0) or 0) + bx

        self._uds.save_user_data(user_id, data)
        return completed
