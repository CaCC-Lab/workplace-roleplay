"""
学習・スキル分析（練習時間、6軸、弱点、週次サマリー）
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from services.gamification_constants import SIX_AXES


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


def _xp_to_rank(xp: int) -> str:
    if xp < 100:
        return "bronze"
    if xp < 300:
        return "silver"
    if xp < 600:
        return "gold"
    return "platinum"


class AnalyticsService:
    """user_data から練習統計・スキル進捗・弱点・週次比較を算出する。"""

    EST_MINUTES_PER_SESSION = 5

    def __init__(self, now: Optional[Callable[[], datetime]] = None) -> None:
        self._now = now or (lambda: datetime.now(timezone.utc))

    def get_practice_stats(self, user_id: str, user_data: Any) -> dict:
        try:
            ud = user_data if isinstance(user_data, dict) else {}
            stats = ud.get("stats") if isinstance(ud.get("stats"), dict) else {}
            history: List[dict] = list(ud.get("xp_history") or [])

            session_count = _safe_int(stats.get("session_count"), -1)
            if session_count < 0:
                session_count = len(history)

            total_time = _safe_int(stats.get("total_time_minutes"), -1)
            if total_time < 0:
                total_time = session_count * self.EST_MINUTES_PER_SESSION

            denom = max(session_count, 1)
            avg_session = round(total_time / denom, 2)

            most_active_day = self._most_active_weekday(history)

            return {
                "total_time_minutes": total_time,
                "session_count": session_count,
                "avg_session_minutes": avg_session,
                "most_active_day": most_active_day,
            }
        except Exception:
            return {
                "total_time_minutes": 0,
                "session_count": 0,
                "avg_session_minutes": 0.0,
                "most_active_day": "—",
            }

    def _most_active_weekday(self, history: List[dict]) -> str:
        weekdays = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
        counts: Counter[str] = Counter()
        for e in history:
            ts = e.get("timestamp")
            if not ts:
                continue
            try:
                dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            except Exception:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            counts[weekdays[dt.weekday()]] += 1
        if not counts:
            return "—"
        return counts.most_common(1)[0][0]

    def get_skill_progress(self, user_id: str, user_data: Any) -> dict:
        try:
            ud = user_data if isinstance(user_data, dict) else {}
            skill = ud.get("skill_xp") if isinstance(ud.get("skill_xp"), dict) else {}
            history: List[dict] = list(ud.get("xp_history") or [])

            growth = self._growth_rate_by_axis(history)

            out: Dict[str, Dict[str, Any]] = {}
            for axis in SIX_AXES:
                current = _safe_int(skill.get(axis, 0))
                out[axis] = {
                    "current": current,
                    "growth_rate": float(growth.get(axis, 0.0)),
                    "rank": _xp_to_rank(current),
                }
            return out
        except Exception:
            return {
                axis: {"current": 0, "growth_rate": 0.0, "rank": "bronze"}
                for axis in SIX_AXES
            }

    def _growth_rate_by_axis(self, history: List[dict]) -> Dict[str, float]:
        if len(history) < 2:
            return {a: 0.0 for a in SIX_AXES}

        mid = len(history) // 2
        first = history[:mid]
        second = history[mid:]

        def _avg(entries: List[dict]) -> Dict[str, float]:
            acc = {a: 0.0 for a in SIX_AXES}
            for e in entries:
                g = e.get("xp_gains") or {}
                for a in SIX_AXES:
                    acc[a] += float(_safe_int(g.get(a)))
            n = max(len(entries), 1)
            return {a: acc[a] / n for a in SIX_AXES}

        a1 = _avg(first)
        a2 = _avg(second)
        out: Dict[str, float] = {}
        for a in SIX_AXES:
            prev = a1[a]
            if prev <= 0:
                out[a] = 0.0 if a2[a] <= 0 else 1.0
            else:
                out[a] = round((a2[a] - prev) / prev, 4)
        return out

    def get_weakness_report(self, user_id: str, user_data: Any) -> List[dict]:
        try:
            ud = user_data if isinstance(user_data, dict) else {}
            skill = ud.get("skill_xp") if isinstance(ud.get("skill_xp"), dict) else {}
            rows: List[dict] = []
            for axis in SIX_AXES:
                score = _safe_int(skill.get(axis, 0))
                rows.append(
                    {
                        "axis": axis,
                        "score": score,
                        "recommendation": self._recommendation_for_axis(axis, score),
                    }
                )
            rows.sort(key=lambda r: (r["score"], r["axis"]))
            return rows
        except Exception:
            return [
                {"axis": a, "score": 0, "recommendation": "データを蓄積すると詳細な提案が表示されます。"}
                for a in SIX_AXES
            ]

    def _recommendation_for_axis(self, axis: str, score: int) -> str:
        tips = {
            "empathy": "相手の立場に立った一言を意識してみましょう。",
            "clarity": "結論から短く伝える練習をしてみましょう。",
            "active_listening": "要約の確認を入れてみましょう。",
            "adaptability": "状況に合わせて表現を変えてみましょう。",
            "positivity": "前向きな言い換えを一つ試してみましょう。",
            "professionalism": "敬語とトーンを揃えてみましょう。",
        }
        base = tips.get(axis, "この軸の練習を続けましょう。")
        if score < 100:
            return f"{base}（優先度: 高）"
        return base

    def get_weekly_summary(self, user_id: str, user_data: Any) -> dict:
        try:
            ud = user_data if isinstance(user_data, dict) else {}
            history: List[dict] = list(ud.get("xp_history") or [])

            now = self._now()
            if now.tzinfo is None:
                now = now.replace(tzinfo=timezone.utc)
            week_start = now - timedelta(days=7)
            prev_week_start = now - timedelta(days=14)

            def _entry_total(entry: dict) -> int:
                gains = entry.get("xp_gains") or {}
                return sum(_safe_int(gains.get(a)) for a in SIX_AXES)

            parsed: List[tuple] = []
            for e in history:
                ts = e.get("timestamp")
                if not ts:
                    continue
                try:
                    dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                except Exception:
                    continue
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                parsed.append((dt, e))

            this_week = sum(_entry_total(e) for dt, e in parsed if week_start <= dt <= now + timedelta(seconds=1))
            last_week = sum(_entry_total(e) for dt, e in parsed if prev_week_start <= dt < week_start)

            if last_week <= 0:
                improvement = 0.0 if this_week <= 0 else 1.0
            else:
                improvement = round((this_week - last_week) / last_week, 4)

            return {
                "this_week": {"xp_total": this_week},
                "last_week": {"xp_total": last_week},
                "improvement": improvement,
            }
        except Exception:
            return {
                "this_week": {"xp_total": 0},
                "last_week": {"xp_total": 0},
                "improvement": 0.0,
            }
