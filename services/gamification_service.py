"""
スキルXP計算と成長データ管理（ゲーミフィケーション）
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from services.gamification_constants import SIX_AXES


def _clamp_score(v: Any) -> int:
    try:
        x = int(v)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, x))


def calculate_xp_from_scores(scores: Dict[str, Any], scenario_type: str) -> Dict[str, int]:
    """
    6軸スコア（0-100）からXPを計算する。
    scenario_type が harassment の場合も計算式は同じ（要件2.5は表示側で非ゲーム的表現）。
    """
    xp_gains: Dict[str, int] = {}
    for axis in SIX_AXES:
        xp_gains[axis] = _clamp_score(scores.get(axis, 0))
    return xp_gains


class GamificationService:
    """スキルXP計算と成長データ管理"""

    HARASSMENT_SCENARIO = "harassment"

    def __init__(
        self,
        user_data_service: Any,
        now: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self._uds = user_data_service
        self._now = now or (lambda: datetime.now(timezone.utc))

    def calculate_xp_from_scores(self, scores: dict, scenario_type: str) -> dict:
        """6軸スコアからXPを計算（ハラスメントも同式。表示の非ゲーム化は scenario_type で区別）"""
        return calculate_xp_from_scores(scores, scenario_type)

    def add_xp(self, user_id: str, xp_gains: dict, source: str) -> dict:
        """XPを加算し、ユーザーデータを更新"""
        data = self._uds.get_user_data(user_id)
        skill = data.setdefault("skill_xp", {})
        for axis in SIX_AXES:
            g = int(xp_gains.get(axis, 0) or 0)
            skill[axis] = int(skill.get(axis, 0) or 0) + g
        entry = {
            "timestamp": self._now().isoformat(),
            "source": source,
            "scenario_id": xp_gains.get("scenario_id"),
            "xp_gains": {k: int(xp_gains.get(k, 0) or 0) for k in SIX_AXES},
            "scores_snapshot": xp_gains.get("scores_snapshot") or {},
        }
        hist = data.setdefault("xp_history", [])
        hist.append(entry)
        self._uds.save_user_data(user_id, data)
        try:
            from services.gamification_vibelogger import get_gamification_vibe_logger

            get_gamification_vibe_logger().info(
                operation="GamificationService.add_xp",
                message="XP added and persisted",
                context={
                    "user_id": user_id,
                    "source": source,
                    "scenario_id": xp_gains.get("scenario_id"),
                },
            )
        except Exception:
            pass
        return {"skill_xp": skill, "xp_history_entry": entry}

    def get_growth_data(self, user_id: str) -> dict:
        """成長グラフ用データ（履歴、個人ベスト、週次比較、直近10回平均）"""
        data = self._uds.get_user_data(user_id)
        history: List[dict] = list(data.get("xp_history") or [])
        personal_best: Dict[str, int] = {a: 0 for a in SIX_AXES}
        for snap in history:
            for axis in SIX_AXES:
                ss = snap.get("scores_snapshot") or {}
                if axis in ss:
                    try:
                        personal_best[axis] = max(
                            personal_best[axis],
                            int(ss[axis]),
                        )
                    except (TypeError, ValueError):
                        pass

        now = self._now()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        week_start = now - timedelta(days=7)
        prev_week_start = now - timedelta(days=14)

        def _entry_total(entry: dict) -> int:
            gains = entry.get("xp_gains") or {}
            return sum(int(gains.get(a, 0) or 0) for a in SIX_AXES)

        parsed: list = []
        for e in history:
            ts = e.get("timestamp")
            if not ts:
                continue
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            parsed.append((dt, e))

        this_week = sum(_entry_total(e) for dt, e in parsed if week_start <= dt < now + timedelta(seconds=1))
        last_week = sum(_entry_total(e) for dt, e in parsed if prev_week_start <= dt < week_start)

        recent = history[-10:] if len(history) > 10 else history
        n = len(recent)
        last_n_avg: Dict[str, float] = {}
        if n > 0:
            for axis in SIX_AXES:
                vals = []
                for e in recent:
                    g = e.get("xp_gains") or {}
                    try:
                        vals.append(int(g.get(axis, 0) or 0))
                    except (TypeError, ValueError):
                        vals.append(0)
                last_n_avg[axis] = sum(vals) / len(vals)
        else:
            last_n_avg = {a: 0.0 for a in SIX_AXES}

        return {
            "personal_best": personal_best,
            "week_comparison": {
                "this_week_xp_total": this_week,
                "last_week_xp_total": last_week,
            },
            "last_10_average": last_n_avg,
            "history_count": len(history),
            "recent_entries_used": n,
        }

    def get_skill_summary(self, user_id: str) -> dict:
        """現在のスキルXPサマリーを返す"""
        data = self._uds.get_user_data(user_id)
        skill = data.get("skill_xp") or {}
        return {a: int(skill.get(a, 0) or 0) for a in SIX_AXES}
