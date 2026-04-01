"""
RealtimeFeedbackService のユニットテスト（LLM は Mock）
"""
import os
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.realtime_feedback_service import RealtimeFeedbackService


def _mock_llm_analyze_ok():
    m = Mock()
    m.invoke.return_value = Mock(
        content=(
            '{"has_feedback":true,"feedback_type":"tone",'
            '"suggestion":"敬語をそろえると伝わりやすいです",'
            '"alternatives":["お忙しいところ恐れ入ります","ご確認ください"]}'
        )
    )
    return m


class TestAnalyzeMessage:
    def test_normal_message_returns_feedback(self):
        # Given: 通常メッセージと正常 JSON を返すモック LLM
        svc = RealtimeFeedbackService(llm=_mock_llm_analyze_ok())
        history = [{"role": "assistant", "content": "進捗はどうですか"}]
        ctx = {"title": "定例報告"}

        # When: 分析する
        result = svc.analyze_message("まあなんとかやってます", history, ctx)

        # Then: フィードバック構造が返る
        assert result["has_feedback"] is True
        assert result["feedback_type"] == "tone"
        assert len(result["suggestion"]) > 0
        assert isinstance(result["alternatives"], list)

    def test_empty_message_has_no_feedback(self):
        # Given: 空のユーザー発言
        llm = Mock()
        svc = RealtimeFeedbackService(llm=llm)

        # When: 分析する
        result = svc.analyze_message("", [], {})

        # Then: フィードバックなし・LLM 未使用
        assert result["has_feedback"] is False
        assert result["feedback_type"] is None
        assert result["suggestion"] == ""
        assert result["alternatives"] == []
        llm.invoke.assert_not_called()

    def test_llm_failure_does_not_raise(self):
        # Given: invoke が例外を投げるモック
        llm = Mock()
        llm.invoke.side_effect = RuntimeError("API down")
        svc = RealtimeFeedbackService(llm=llm)

        # When: 分析する
        result = svc.analyze_message("テストです", [], {})

        # Then: 例外にならず安全な辞書
        assert result["has_feedback"] is False
        assert result["alternatives"] == []


class TestGenerateAlternatives:
    def test_alternatives_capped_at_three(self):
        # Given: 5 件の配列を返すモック
        llm = Mock()
        llm.invoke.return_value = Mock(
            content='["A","B","C","D","E"]'
        )
        svc = RealtimeFeedbackService(llm=llm)

        # When: 代替案を生成
        alts = svc.generate_alternatives("お疲れ様です", [])

        # Then: 最大 3 件
        assert len(alts) == 3
        assert alts == ["A", "B", "C"]

    def test_generate_alternatives_empty_message_returns_empty(self):
        svc = RealtimeFeedbackService(llm=Mock())
        assert svc.generate_alternatives("   ", []) == []

    def test_generate_alternatives_llm_failure_returns_empty_no_raise(self):
        llm = Mock()
        llm.invoke.side_effect = ValueError("bad")
        svc = RealtimeFeedbackService(llm=llm)

        assert svc.generate_alternatives("こんにちは", []) == []


class TestShouldProvideFeedback:
    def test_interval_three_requires_three_user_messages(self):
        # Given: interval=3
        svc = RealtimeFeedbackService()

        # When / Then: ユーザー 2 回は False、3 回は True
        h2 = [
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
            {"role": "user", "content": "c"},
        ]
        assert svc.should_provide_feedback(h2, interval=3) is False

        h3 = h2 + [{"role": "assistant", "content": "d"}, {"role": "user", "content": "e"}]
        assert svc.should_provide_feedback(h3, interval=3) is True
