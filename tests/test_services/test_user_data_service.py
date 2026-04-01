"""
UserDataService のユニットテストおよびプロパティベーステスト

参照: .kiro/specs/gamification/requirements.md, design.md, tasks.md
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest
from hypothesis import given, settings, strategies as st

from services.user_data_service import UserDataService

_AXES = (
    "empathy",
    "clarity",
    "active_listening",
    "adaptability",
    "positivity",
    "professionalism",
)

_skill_xp_st = st.fixed_dictionaries({a: st.integers(min_value=0, max_value=50000) for a in _AXES})

_unlock_st = st.fixed_dictionaries(
    {
        "beginner": st.booleans(),
        "intermediate": st.booleans(),
        "advanced": st.booleans(),
    }
)

_badge_earned_st = st.lists(
    st.fixed_dictionaries(
        {
            "badge_id": st.text(min_size=1, max_size=32, alphabet=st.characters(whitelist_categories=("L", "N"))),
            "earned_at": st.text(min_size=8, max_size=32),
        }
    ),
    max_size=5,
)

_quest_list_st = st.lists(
    st.fixed_dictionaries(
        {
            "quest_id": st.text(min_size=1, max_size=40),
            "type": st.sampled_from(["daily", "weekly"]),
            "description": st.text(max_size=80),
            "target_value": st.integers(min_value=1, max_value=100),
            "current_value": st.integers(min_value=0, max_value=100),
            "bonus_xp": st.integers(min_value=0, max_value=500),
            "completed": st.booleans(),
        }
    ),
    max_size=6,
)


def _strip_volatile(d: dict) -> dict:
    o = dict(d)
    o.pop("updated_at", None)
    o.pop("created_at", None)
    return o


def _payload_from_generated(
    skill_xp: dict,
    unlock_status: dict,
    badges_earned: list,
    daily: list,
    weekly: list,
) -> dict:
    """要件1.5に沿ったペイロード（保存・読込ラウンドトリップ検証用）"""
    return {
        "skill_xp": skill_xp,
        "unlock_status": unlock_status,
        "badges": {"earned": badges_earned},
        "quests": {"daily": daily, "weekly": weekly},
        "xp_history": [],
        "scenario_completions": {},
        "quiz_history": [],
        "stats": {
            "total_scenarios_completed": 0,
            "total_quizzes_answered": 0,
            "total_quizzes_correct": 0,
            "total_journal_entries": 0,
            "consecutive_days": 0,
            "last_activity_date": None,
            "unique_scenarios_tried": 0,
        },
    }


# Feature: gamification, Property 1: ユーザーデータ保存・読み込みラウンドトリップ
@given(
    skill_xp=_skill_xp_st,
    unlock_status=_unlock_st,
    badges_earned=_badge_earned_st,
    daily=_quest_list_st,
    weekly=_quest_list_st,
)
@settings(max_examples=100)
def test_property_1_user_data_round_trip(skill_xp, unlock_status, badges_earned, daily, weekly):
    payload = _payload_from_generated(skill_xp, unlock_status, badges_earned, daily, weekly)
    with tempfile.TemporaryDirectory() as tmp:
        svc = UserDataService(data_dir=tmp)
        uid = "pbt_user_1"
        # Given: 有効なユーザーデータ
        # When: 保存してから読み込む
        svc.save_user_data(uid, payload)
        loaded = svc.get_user_data(uid)
        # Then: 揮発フィールド以外は等価（要件1.2, 1.3, 1.5）
        assert loaded["user_id"] == uid
        assert _strip_volatile(loaded) == _strip_volatile({**payload, "user_id": uid})


class TestUserDataServiceUnit:
    """要件1.1〜1.4 のユニットテスト"""

    def test_new_user_creates_default_when_missing_file(self):
        # Given: 空の一時ディレクトリと未保存ユーザID
        # When: get_user_data を呼ぶ
        # Then: デフォルト構造が返る（要件1.1相当・永続化前提データ）
        with tempfile.TemporaryDirectory() as tmp:
            svc = UserDataService(data_dir=tmp)
            d = svc.get_user_data("new-user-abc")
            assert d["user_id"] == "new-user-abc"
            assert set(d["skill_xp"].keys()) == set(_AXES)
            assert d["unlock_status"]["beginner"] is True
            assert d["unlock_status"]["intermediate"] is False

    def test_save_and_load(self):
        # Given: 保存するデータ
        # When: save → get
        # Then: コアフィールドが一致する
        with tempfile.TemporaryDirectory() as tmp:
            svc = UserDataService(data_dir=tmp)
            uid = "u1"
            body = _payload_from_generated(
                {a: 1 for a in _AXES},
                {"beginner": True, "intermediate": True, "advanced": False},
                [],
                [],
                [],
            )
            svc.save_user_data(uid, body)
            got = svc.get_user_data(uid)
            assert got["skill_xp"] == body["skill_xp"]
            assert got["unlock_status"] == body["unlock_status"]

    def test_corrupt_json_returns_default_and_renames_bak(self):
        # Given: 破損したJSONファイル
        # When: get_user_data
        # Then: デフォルトが返り、元ファイルが .bak に退避される（design エラーハンドリング）
        with tempfile.TemporaryDirectory() as tmp:
            svc = UserDataService(data_dir=tmp)
            uid = "corrupt"
            path = svc._get_file_path(uid)
            os.makedirs(tmp, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write("{ not json")
            d = svc.get_user_data(uid)
            assert d["user_id"] == uid
            assert not os.path.isfile(path)
            assert os.path.isfile(path + ".bak")

    def test_missing_file_returns_default(self):
        # Given: ファイルが存在しない
        # When: get_user_data
        # Then: デフォルト
        with tempfile.TemporaryDirectory() as tmp:
            svc = UserDataService(data_dir=tmp)
            d = svc.get_user_data("ghost")
            assert d["stats"]["total_scenarios_completed"] == 0

    def test_data_dir_auto_created(self):
        # Given: 親ディレクトリのみ存在
        # When: save_user_data
        # Then: user_data 相当のディレクトリが作成される
        with tempfile.TemporaryDirectory() as tmp:
            nested = os.path.join(tmp, "nested", "ud")
            svc = UserDataService(data_dir=nested)
            svc.save_user_data("x", {"skill_xp": {a: 0 for a in _AXES}})
            assert os.path.isdir(nested)

    def test_save_user_data_rejects_none(self):
        # Given: data が None
        # When: save_user_data
        # Then: TypeError
        with tempfile.TemporaryDirectory() as tmp:
            svc = UserDataService(data_dir=tmp)
            with pytest.raises(TypeError):
                svc.save_user_data("u", None)  # type: ignore[arg-type]

    def test_empty_user_id_raises(self):
        # Given: 空の user_id
        # When: _get_file_path
        # Then: ValueError
        with tempfile.TemporaryDirectory() as tmp:
            svc = UserDataService(data_dir=tmp)
            with pytest.raises(ValueError):
                svc._get_file_path("")

    def test_large_history_payload(self):
        # Given: 大量の xp_history
        # When: 保存・読込
        # Then: ラウンドトリップで整合
        hist = [
            {
                "timestamp": "2025-01-01T00:00:00+00:00",
                "source": "scenario_completion",
                "scenario_id": None,
                "xp_gains": {a: 1 for a in _AXES},
                "scores_snapshot": {a: 50 for a in _AXES},
            }
            for _ in range(200)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            svc = UserDataService(data_dir=tmp)
            uid = "heavy"
            data = _payload_from_generated(
                {a: 0 for a in _AXES},
                {"beginner": True, "intermediate": False, "advanced": False},
                [],
                [],
                [],
            )
            data["xp_history"] = hist
            svc.save_user_data(uid, data)
            loaded = svc.get_user_data(uid)
            assert len(loaded["xp_history"]) == 200
