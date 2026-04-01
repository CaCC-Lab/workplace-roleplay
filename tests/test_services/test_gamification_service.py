"""
GamificationService のユニットテストおよびプロパティベーステスト

参照: .kiro/specs/gamification/requirements.md, design.md, tasks.md
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings, strategies as st

from services.gamification_service import (
    GamificationService,
    calculate_xp_from_scores,
)
from services.user_data_service import UserDataService

_AXES = (
    "empathy",
    "clarity",
    "active_listening",
    "adaptability",
    "positivity",
    "professionalism",
)

_scores_st = st.fixed_dictionaries({a: st.integers(min_value=-50, max_value=150) for a in _AXES})


def _svc_with_data(data: dict, now=None):
    uds = MagicMock()
    uds.get_user_data = MagicMock(return_value=data)
    uds.save_user_data = MagicMock()
    return GamificationService(uds, now=now)


# Feature: gamification, Property 2: 6軸スコアからのXP計算の正当性
@given(scores=_scores_st)
@settings(max_examples=100)
def test_property_2_xp_from_scores(scores):
    # Given: 任意の6軸スコア辞書（境界を含む）
    # When: calculate_xp_from_scores
    # Then: 各軸は非負整数で、クランプ後スコアに比例（要件2.1, 2.2）
    out = calculate_xp_from_scores(scores, "normal")
    for a in _AXES:
        assert a in out
        v = out[a]
        assert isinstance(v, int)
        assert v >= 0
        exp = max(0, min(100, int(scores.get(a, 0) or 0)))
        assert v == exp


# Feature: gamification, Property 3: 成長データの自己比較計算
@given(axis_vals=st.lists(st.integers(min_value=0, max_value=50), min_size=1, max_size=15))
@settings(max_examples=100)
def test_property_3_last_n_average_matches_arithmetic_mean(axis_vals):
    # Given: xp_history（1件以上）
    # When: get_growth_data
    # Then: empathy 軸の直近10回平均は直近 N 件（N≤10）の算術平均と一致（要件2.4）
    history = []
    base = datetime(2025, 6, 1, tzinfo=timezone.utc)
    for i, val in enumerate(axis_vals):
        history.append(
            {
                "timestamp": (base + timedelta(hours=i)).isoformat(),
                "source": "scenario_completion",
                "xp_gains": {a: (val if a == "empathy" else 0) for a in _AXES},
                "scores_snapshot": {},
            }
        )
    data = {"xp_history": history, "skill_xp": {a: 0 for a in _AXES}}
    fixed_now = base + timedelta(days=30)
    svc = _svc_with_data(data, now=lambda: fixed_now)
    g = svc.get_growth_data("u")
    recent_n = min(10, len(history))
    tail = history[-recent_n:]
    expected_avg = sum(int(e["xp_gains"]["empathy"]) for e in tail) / len(tail)
    assert abs(g["last_10_average"]["empathy"] - expected_avg) < 1e-9


class TestGamificationServiceUnit:
    def test_add_xp_updates_skill_and_history(self):
        # Given: 空に近いユーザーデータ
        # When: add_xp
        # Then: skill_xp と xp_history が更新される
        with tempfile.TemporaryDirectory() as tmp:
            uds = UserDataService(data_dir=tmp)
            uid = "g1"
            uds.save_user_data(uid, uds.get_user_data(uid))
            gs = GamificationService(uds)
            gs.add_xp(
                uid,
                {
                    "empathy": 10,
                    "clarity": 0,
                    "active_listening": 0,
                    "adaptability": 0,
                    "positivity": 0,
                    "professionalism": 0,
                    "scores_snapshot": {"empathy": 80},
                },
                "scenario_completion",
            )
            d = uds.get_user_data(uid)
            assert d["skill_xp"]["empathy"] == 10
            assert len(d["xp_history"]) == 1

    def test_scores_out_of_range_clamped(self):
        # Given: 範囲外スコア
        # When: calculate_xp_from_scores
        # Then: 0-100 にクランプ（design エラーハンドリング）
        out = calculate_xp_from_scores({"empathy": -10, "clarity": 200}, "x")
        assert out["empathy"] == 0
        assert out["clarity"] == 100

    def test_missing_axis_keys_treated_as_zero(self):
        # Given: キー不足
        # When: calculate_xp_from_scores
        # Then: 不足キーは 0
        out = calculate_xp_from_scores({"empathy": 50}, "x")
        assert out["clarity"] == 0

    def test_harassment_same_numeric_xp_as_normal(self):
        # Given: 同じスコア
        # When: harassment と通常で計算
        # Then: 数値XPは同じ（要件2.5 は表現の話）
        scores = {a: 40 for a in _AXES}
        a = calculate_xp_from_scores(scores, "normal")
        b = calculate_xp_from_scores(scores, GamificationService.HARASSMENT_SCENARIO)
        assert a == b

    def test_growth_data_empty_history(self):
        # Given: 履歴0件
        # When: get_growth_data
        # Then: 平均0・エラーなし
        svc = _svc_with_data({"xp_history": [], "skill_xp": {a: 0 for a in _AXES}})
        g = svc.get_growth_data("u")
        assert g["history_count"] == 0
        assert g["recent_entries_used"] == 0
        assert g["last_10_average"]["empathy"] == 0.0
