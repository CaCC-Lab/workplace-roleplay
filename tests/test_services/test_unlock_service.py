"""
UnlockService のユニットテストおよびプロパティベーステスト

参照: .kiro/specs/gamification/requirements.md, design.md, tasks.md
"""

from __future__ import annotations

import tempfile
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings, strategies as st

from services.unlock_service import UnlockService, get_scenario_difficulty
from services.user_data_service import UserDataService


def _mock_scenario_service(mapping: dict):
    m = MagicMock()
    m.get_all_scenarios.return_value = mapping
    m.get_scenario_by_id.side_effect = lambda sid: mapping.get(sid)
    return m


def _base_data():
    return {
        "skill_xp": {},
        "xp_history": [],
        "scenario_completions": {},
        "unlock_status": {"beginner": True, "intermediate": False, "advanced": False},
        "quests": {"daily": [], "weekly": []},
        "badges": {"earned": []},
        "quiz_history": [],
        "stats": {},
    }


# Feature: gamification, Property 4: シナリオアンロック判定
@given(
    beg=st.integers(min_value=0, max_value=10),
    int_done=st.integers(min_value=0, max_value=10),
)
@settings(max_examples=100)
def test_property_4_unlock_thresholds(beg, int_done):
    # Given: beginner / intermediate 完了数
    # When: check_and_unlock
    # Then: 閾値以上でのみ該当レベルがアンロック（要件3.2, 3.3）
    with tempfile.TemporaryDirectory() as tmp:
        uds = UserDataService(data_dir=tmp)
        uid = "u"
        data = _base_data()
        data["scenario_completions"] = {
            "b1": {"count": beg, "difficulty": "beginner"},
            "i1": {"count": int_done, "difficulty": "intermediate"},
        }
        uds.save_user_data(uid, data)
        scenarios = {
            "sb": {"difficulty": "beginner"},
            "si": {"difficulty": "intermediate"},
            "sa": {"difficulty": "advanced"},
        }
        svc = UnlockService(uds, _mock_scenario_service(scenarios))
        svc.check_and_unlock(uid)
        d = uds.get_user_data(uid)
        us = d["unlock_status"]
        th_i = UnlockService.UNLOCK_THRESHOLDS["intermediate"]
        th_a = UnlockService.UNLOCK_THRESHOLDS["advanced"]
        assert us["intermediate"] == (beg >= th_i)
        assert us["advanced"] == (int_done >= th_a)


# Feature: gamification, Property 5: シナリオ一覧データの完全性
@given(unlocked=st.booleans())
@settings(max_examples=100)
def test_property_5_unlock_status_entries_contain_fields(unlocked):
    # Given: アンロック状態を操作したユーザーデータ
    # When: get_unlock_status
    # Then: 各シナリオに difficulty / unlocked が含まれ、ロック時は条件（要件3.4, 3.5）
    with tempfile.TemporaryDirectory() as tmp:
        uds = UserDataService(data_dir=tmp)
        uid = "u"
        data = _base_data()
        data["unlock_status"] = {
            "beginner": True,
            "intermediate": unlocked,
            "advanced": unlocked,
        }
        data["scenario_completions"] = {
            "b1": {"count": 3 if unlocked else 0, "difficulty": "beginner"},
            "i1": {"count": 3 if unlocked else 0, "difficulty": "intermediate"},
        }
        uds.save_user_data(uid, data)
        scenarios = {
            "s1": {"difficulty": "beginner"},
            "s2": {"difficulty": "intermediate"},
            "s3": {"difficulty": "advanced"},
        }
        svc = UnlockService(uds, _mock_scenario_service(scenarios))
        st_out = svc.get_unlock_status(uid)
        for ent in st_out["scenarios"]:
            assert "difficulty" in ent
            assert "unlocked" in ent
            assert "scenario_id" in ent
            if not ent["unlocked"]:
                assert "unlock_condition" in ent


class TestUnlockServiceUnit:
    def test_initial_beginner_only(self):
        # Given: 新規ユーザーデータ
        # When: get_unlock_status
        # Then: beginner のみアンロック（要件3.1）
        with tempfile.TemporaryDirectory() as tmp:
            uds = UserDataService(data_dir=tmp)
            uid = "new"
            uds.save_user_data(uid, uds.get_user_data(uid))
            svc = UnlockService(uds, _mock_scenario_service({"x": {"difficulty": "beginner"}}))
            st = svc.get_unlock_status(uid)
            assert st["unlock_status"]["beginner"] is True
            assert st["unlock_status"]["intermediate"] is False

    def test_threshold_minus_one_stays_locked(self):
        # Given: beginner 完了が閾値-1
        # When: check_and_unlock
        # Then: intermediate はロック
        with tempfile.TemporaryDirectory() as tmp:
            uds = UserDataService(data_dir=tmp)
            uid = "u"
            data = _base_data()
            th = UnlockService.UNLOCK_THRESHOLDS["intermediate"]
            data["scenario_completions"] = {"b": {"count": th - 1, "difficulty": "beginner"}}
            uds.save_user_data(uid, data)
            svc = UnlockService(uds, _mock_scenario_service({}))
            svc.check_and_unlock(uid)
            assert uds.get_user_data(uid)["unlock_status"]["intermediate"] is False

    def test_threshold_exact_unlocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            uds = UserDataService(data_dir=tmp)
            uid = "u"
            data = _base_data()
            th = UnlockService.UNLOCK_THRESHOLDS["intermediate"]
            data["scenario_completions"] = {"b": {"count": th, "difficulty": "beginner"}}
            uds.save_user_data(uid, data)
            svc = UnlockService(uds, _mock_scenario_service({}))
            svc.check_and_unlock(uid)
            assert uds.get_user_data(uid)["unlock_status"]["intermediate"] is True

    def test_is_scenario_unlocked_respects_difficulty(self):
        with tempfile.TemporaryDirectory() as tmp:
            uds = UserDataService(data_dir=tmp)
            uid = "u"
            data = _base_data()
            data["unlock_status"] = {"beginner": True, "intermediate": False, "advanced": False}
            uds.save_user_data(uid, data)
            svc = UnlockService(
                uds,
                _mock_scenario_service({"adv": {"difficulty": "advanced"}}),
            )
            assert svc.is_scenario_unlocked(uid, "adv") is False

    def test_get_unlock_progress_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            uds = UserDataService(data_dir=tmp)
            uid = "u"
            data = _base_data()
            data["scenario_completions"] = {"b": {"count": 2, "difficulty": "beginner"}}
            uds.save_user_data(uid, data)
            svc = UnlockService(uds, _mock_scenario_service({}))
            p = svc.get_unlock_progress(uid)
            assert p["intermediate"]["current"] == 2
            assert p["intermediate"]["needed"] == UnlockService.UNLOCK_THRESHOLDS["intermediate"]

    def test_get_scenario_difficulty_defaults(self):
        assert get_scenario_difficulty({}) == "beginner"
        assert get_scenario_difficulty({"difficulty": "intermediate"}) == "intermediate"
