"""
QuizService のユニットテストおよびプロパティベーステスト

参照: .kiro/specs/gamification/requirements.md, design.md, tasks.md
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings, strategies as st

from services.quiz_service import QuizService


# Feature: gamification, Property 9: クイズ生成タイミング判定
@given(n=st.integers(min_value=0, max_value=500))
@settings(max_examples=100)
def test_property_9_should_generate_only_on_positive_multiple_of_interval(n):
    # Given: 非負整数 message_count
    # When: should_generate_quiz
    # Then: QUIZ_INTERVAL の正の倍数のときのみ True（要件5.1）
    svc = QuizService()
    expected = n > 0 and (n % svc.QUIZ_INTERVAL == 0)
    assert svc.should_generate_quiz(n) == expected


# Feature: gamification, Property 10: クイズ選択肢数の不変条件
@given(
    n_choices=st.integers(min_value=3, max_value=4),
    correct=st.integers(min_value=0, max_value=3),
)
@settings(max_examples=100)
def test_property_10_quiz_shape_invariants(n_choices, correct):
    # Given: 3〜4択と正解インデックス
    # When: クイズ辞書を検証可能な形で構築
    # Then: choices 長と correct_answer のインデックスが妥当（要件5.2）
    # 注: correct は n_choices 未満にクランプ
    n_choices = min(4, max(3, n_choices))
    correct = correct % n_choices
    choices = [f"c{i}" for i in range(n_choices)]
    quiz = {"question": "q", "choices": choices, "correct_answer": correct}
    svc = QuizService()
    assert svc._validate_quiz_shape(quiz) is True


# Feature: gamification, Property 11: クイズ正解時のXP付与
@given(
    n=st.integers(min_value=3, max_value=4),
    correct=st.integers(min_value=0, max_value=3),
    user=st.integers(min_value=0, max_value=3),
)
@settings(max_examples=100)
def test_property_11_bonus_xp_only_when_correct(n, correct, user):
    n = min(4, max(3, n))
    correct = correct % n
    user = user % n
    quiz = {"question": "q", "choices": [f"a{i}" for i in range(n)], "correct_answer": correct}
    svc = QuizService()
    r = svc.evaluate_answer(quiz, user, [])
    is_match = user == correct
    if is_match:
        assert r["bonus_xp"] > 0
    else:
        assert r["bonus_xp"] == 0


# Feature: gamification, Property 12: クイズ正答率計算
@given(flags=st.lists(st.booleans(), min_size=1, max_size=30))
@settings(max_examples=100)
def test_property_12_session_summary_accuracy(flags):
    # Given: 1件以上のクイズ回答履歴
    # When: get_session_summary
    # Then: 正答率 = 正解数 / 総数（要件5.5）
    quizzes = [{"is_correct": f} for f in flags]
    svc = QuizService()
    s = svc.get_session_summary("u", quizzes)
    n = len(flags)
    exp = sum(flags) / n
    assert abs(s["accuracy"] - exp) < 1e-9
    assert s["total"] == n


class TestQuizServiceUnit:
    def test_generate_fallback_when_llm_fails(self):
        # Given: LLM が例外を投げる
        # When: generate_quiz
        # Then: フォールバック（3択）が返る（design エラーハンドリング）
        llm = MagicMock()
        llm.generate_quiz_content.side_effect = RuntimeError("api")
        svc = QuizService(llm_service=llm)
        q = svc.generate_quiz([{"role": "user", "content": "x"}])
        assert 3 <= len(q["choices"]) <= 4

    def test_evaluate_requires_quiz(self):
        svc = QuizService()
        with pytest.raises(TypeError):
            svc.evaluate_answer(None, 0, [])

    def test_message_count_zero_false(self):
        svc = QuizService()
        assert svc.should_generate_quiz(0) is False
