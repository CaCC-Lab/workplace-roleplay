"""
QuestService のユニットテストおよびプロパティベーステスト

参照: .kiro/specs/gamification/requirements.md, design.md, tasks.md
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone

import pytest
from hypothesis import given, settings, strategies as st

from services.quest_service import QuestService
from services.user_data_service import UserDataService


def _fixed_now(dt: datetime):
    return lambda: dt


# Feature: gamification, Property 6: クエスト生成の有効性
@given(seed=st.integers(min_value=0, max_value=10_000))
@settings(max_examples=100)
def test_property_6_generated_quests_have_required_fields(seed):
    # Given: 固定時刻とユーザーID
    # When: generate_daily_quests / generate_weekly_quests
    # Then: 必須フィールドと値の妥当性（要件4.1, 4.2）
    now = datetime(2025, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory() as tmp:
        uds = UserDataService(data_dir=tmp)
        qs = QuestService(uds, now=_fixed_now(now))
        uid = f"user_{seed}"
        for gen, label in (
            (qs.generate_daily_quests(uid), "daily"),
            (qs.generate_weekly_quests(uid), "weekly"),
        ):
            assert len(gen) > 0
            for q in gen:
                assert "quest_id" in q and q["quest_id"]
                assert "description" in q
                assert int(q["target_value"]) >= 1
                assert int(q["bonus_xp"]) >= 0
                exp = datetime.fromisoformat(str(q["expires_at"]).replace("Z", "+00:00"))
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                assert exp > now


# Feature: gamification, Property 7: クエスト完了判定とXP付与
@given(
    target=st.integers(min_value=1, max_value=20),
    current=st.integers(min_value=0, max_value=30),
)
@settings(max_examples=100)
def test_property_7_completion_iff_current_ge_target(target, current):
    # Given: 単一クエストの target_value / current_value
    # When: check_quest_completion で該当キーのデルタを適用
    # Then: current >= target のときのみ完了リストに含まれる（要件4.3, 4.4）
    with tempfile.TemporaryDirectory() as tmp:
        uds = UserDataService(data_dir=tmp)
        uid = "u"
        data = uds.get_user_data(uid)
        data["quests"] = {
            "daily": [
                {
                    "quest_id": "q1",
                    "type": "daily",
                    "description": "d",
                    "target_key": "k1",
                    "target_value": target,
                    "current_value": current,
                    "bonus_xp": 10,
                    "completed": False,
                }
            ],
            "weekly": [],
        }
        uds.save_user_data(uid, data)
        qs = QuestService(uds)
        done = qs.check_quest_completion(uid, {"target_key": "k1", "delta": 0})
        completed_now = len(done) > 0
        expected = current >= target
        assert completed_now == expected


# Feature: gamification, Property 8: 期限切れクエストの置き換え
@given(steps=st.integers(min_value=0, max_value=3))
@settings(max_examples=100)
def test_property_8_expired_quests_replaced(steps):
    # Given: 期限切れのデイリークエストのみ
    # When: get_active_quests
    # Then: 返却に期限切れが含まれない（要件4.5）
    now = datetime(2025, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory() as tmp:
        uds = UserDataService(data_dir=tmp)
        uid = "u"
        data = uds.get_user_data(uid)
        past = (now - timedelta(days=2)).isoformat()
        data["quests"] = {
            "daily": [
                {
                    "quest_id": "old",
                    "type": "daily",
                    "description": "x",
                    "target_value": 1,
                    "current_value": 0,
                    "bonus_xp": 1,
                    "completed": False,
                    "expires_at": past,
                }
            ],
            "weekly": [],
        }
        uds.save_user_data(uid, data)
        qs = QuestService(uds, now=_fixed_now(now))
        for _ in range(steps):
            pass
        active = qs.get_active_quests(uid)
        for q in active["daily"] + active["weekly"]:
            exp = datetime.fromisoformat(str(q["expires_at"]).replace("Z", "+00:00"))
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            assert exp > now


class TestQuestServiceUnit:
    def test_completion_applies_bonus_xp(self):
        # Given: 未完了クエスト
        # When: current が target に到達
        # Then: completed に含まれ skill_xp が増える
        with tempfile.TemporaryDirectory() as tmp:
            uds = UserDataService(data_dir=tmp)
            uid = "u"
            data = uds.get_user_data(uid)
            data["quests"] = {
                "daily": [
                    {
                        "quest_id": "q1",
                        "type": "daily",
                        "description": "d",
                        "target_key": "scenarios_today",
                        "target_value": 1,
                        "current_value": 0,
                        "bonus_xp": 20,
                        "completed": False,
                    }
                ],
                "weekly": [],
            }
            uds.save_user_data(uid, data)
            qs = QuestService(uds)
            qs.check_quest_completion(uid, {"target_key": "scenarios_today", "delta": 1})
            d = uds.get_user_data(uid)
            assert d["quests"]["daily"][0]["completed"] is True
            assert d["skill_xp"]["professionalism"] >= 20

    def test_target_value_zero_never_completes_via_check(self):
        # Given: target_value が 0（無効）
        # When: check_quest_completion
        # Then: 完了にしない（エッジ）
        with tempfile.TemporaryDirectory() as tmp:
            uds = UserDataService(data_dir=tmp)
            uid = "u"
            data = uds.get_user_data(uid)
            data["quests"] = {
                "daily": [
                    {
                        "quest_id": "q0",
                        "type": "daily",
                        "description": "d",
                        "target_key": "k",
                        "target_value": 0,
                        "current_value": 5,
                        "bonus_xp": 10,
                        "completed": False,
                    }
                ],
                "weekly": [],
            }
            uds.save_user_data(uid, data)
            qs = QuestService(uds)
            done = qs.check_quest_completion(uid, {"target_key": "k", "delta": 1})
            assert done == []
