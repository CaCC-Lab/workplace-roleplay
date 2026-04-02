"""
BadgeService のユニットテストおよびプロパティベーステスト

参照: .kiro/specs/gamification/requirements.md, design.md, tasks.md
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings, strategies as st

from services.badge_service import BADGE_DEFINITIONS, BadgeService


def _data_with_stats(stats: dict, earned=None, skill_xp=None):
    return {
        "stats": stats,
        "badges": {"earned": earned or []},
        "skill_xp": skill_xp or {},
    }


def _svc(data: dict):
    uds = MagicMock()
    uds.get_user_data = MagicMock(return_value=data)
    uds.save_user_data = MagicMock()
    return BadgeService(uds)


# Feature: gamification, Property 13: バッジ獲得条件判定
@given(n=st.integers(min_value=0, max_value=100))
@settings(max_examples=100)
def test_property_13_first_step_eligibility_matches_scenario_count(n):
    # Given: total_scenarios_completed = n、未獲得の状態
    # When: check_badge_eligibility
    # Then: n >= 1 のときのみ first_step が候補に含まれる（要件6.1）
    data = _data_with_stats(
        {
            "total_scenarios_completed": n,
            "total_quizzes_answered": 0,
            "consecutive_days": 0,
            "unique_scenarios_tried": 0,
        }
    )
    svc = _svc(data)
    new = svc.check_badge_eligibility("u")
    ids = {b["badge_id"] for b in new}
    assert ("first_step" in ids) == (n >= 1)


# Feature: gamification, Property 14: バッジ一覧の完全性
@given(seed=st.integers(min_value=0, max_value=1000))
@settings(max_examples=100)
def test_property_14_all_badges_listed_with_state(seed):
    # Given: 任意のシードに基づく skill_xp / stats
    # When: get_all_badges
    # Then: 全定義バッジが含まれ、未獲得には条件・進捗（要件6.3, 6.5）
    skill = {
        "empathy": seed % 40,
        "clarity": seed % 30,
        "active_listening": seed % 20,
        "adaptability": seed % 10,
        "positivity": seed % 5,
        "professionalism": seed % 15,
    }
    data = _data_with_stats(
        {
            "total_scenarios_completed": seed % 3,
            "total_quizzes_answered": seed % 12,
            "consecutive_days": seed % 8,
            "unique_scenarios_tried": seed % 7,
        },
        earned=[],
        skill_xp=skill,
    )
    svc = _svc(data)
    out = svc.get_all_badges("u")["badges"]
    defined_ids = {b["badge_id"] for b in BADGE_DEFINITIONS}
    listed = set()
    for wrap in out:
        b = wrap["badge"]
        listed.add(b["badge_id"])
        assert "earned" in b
        if not b["earned"]:
            assert "current_value" in b and "target_value" in b
    assert defined_ids == listed


class TestBadgeServiceUnit:
    def test_award_badge_notification(self):
        # Given: 未獲得バッジ
        # When: award_badge
        # Then: 通知オブジェクトが返る（要件6.4）
        data = _data_with_stats({})
        svc = _svc(data)
        r = svc.award_badge("u", "first_step")
        assert r["notification"] is not None
        assert r["notification"]["type"] == "badge_earned"

    def test_three_categories_in_definitions(self):
        # Given: BADGE_DEFINITIONS
        # Then: カテゴリが継続性・多様性・改善度の3種（要件6.2）
        cats = {b["category"] for b in BADGE_DEFINITIONS}
        assert cats == {"継続性", "多様性", "改善度"}

    def test_get_badge_progress_unknown(self):
        svc = _svc(_data_with_stats({}))
        r = svc.get_badge_progress("u", "no_such_badge")
        assert "error" in r
