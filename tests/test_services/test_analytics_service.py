"""
AnalyticsService のユニットテスト
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.analytics_service import AnalyticsService
from services.gamification_constants import SIX_AXES


@pytest.fixture
def svc():
    return AnalyticsService()


def _sample_user_data():
    now = datetime.now(timezone.utc)
    return {
        "skill_xp": {
            "empathy": 5,
            "clarity": 120,
            "active_listening": 80,
            "adaptability": 90,
            "positivity": 100,
            "professionalism": 110,
        },
        "xp_history": [
            {
                "timestamp": (now - timedelta(days=10)).isoformat(),
                "xp_gains": {a: 2 for a in SIX_AXES},
            },
            {
                "timestamp": (now - timedelta(days=2)).isoformat(),
                "xp_gains": {a: 4 for a in SIX_AXES},
            },
        ],
        "stats": {"total_time_minutes": 30, "session_count": 2},
    }


class TestPracticeStats:
    def test_practice_stats_has_required_keys(self, svc):
        r = svc.get_practice_stats("u1", _sample_user_data())
        for key in ("total_time_minutes", "session_count", "avg_session_minutes", "most_active_day"):
            assert key in r
        assert r["session_count"] == 2
        assert r["total_time_minutes"] == 30


class TestSkillProgress:
    def test_skill_progress_includes_all_six_axes(self, svc):
        r = svc.get_skill_progress("u1", _sample_user_data())
        assert set(r.keys()) == set(SIX_AXES)
        for axis in SIX_AXES:
            assert "current" in r[axis]
            assert "growth_rate" in r[axis]
            assert "rank" in r[axis]


class TestWeaknessReport:
    def test_weakness_report_includes_lowest_axis_first(self, svc):
        data = _sample_user_data()
        report = svc.get_weakness_report("u1", data)
        assert len(report) >= 1
        assert report[0]["axis"] == "empathy"
        assert report[0]["score"] == 5
        assert "recommendation" in report[0]


class TestWeeklySummary:
    def test_weekly_summary_has_this_week_and_last_week(self, svc):
        r = svc.get_weekly_summary("u1", _sample_user_data())
        assert "this_week" in r
        assert "last_week" in r
        assert "improvement" in r
        assert "xp_total" in r["this_week"]
        assert "xp_total" in r["last_week"]


class TestEmptyData:
    def test_empty_user_data_no_exception(self, svc):
        for fn in (
            svc.get_practice_stats,
            svc.get_skill_progress,
            svc.get_weakness_report,
            svc.get_weekly_summary,
        ):
            out = fn("uid", {})
            assert out is not None
        out2 = svc.get_practice_stats("uid", None)
        assert out2["session_count"] == 0
