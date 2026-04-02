"""
SummaryService のユニットテスト（LLM は Mock）
"""
import os
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.summary_service import SummaryService


@pytest.fixture
def sample_history():
    return [
        {"role": "user", "content": "進捗を報告したいです"},
        {"role": "assistant", "content": "どのタスクについてですか？"},
    ]


def _llm_ok_response():
    m = Mock()
    m.invoke.return_value = Mock(
        content=(
            '{"summary":"進捗報告のやり取りが行われた",'
            '"key_points":["目的を明確にした","相手の質問に応じた"],'
            '"learning_points":["報告前に論点を整理する"]}'
        )
    )
    return m


class TestSummaryServiceScenario:
    def test_scenario_mode_returns_summary_key_points_learning_points(self, sample_history):
        # Given: シナリオモード用の会話履歴と、正常 JSON を返すモック LLM
        llm = _llm_ok_response()
        svc = SummaryService(llm=llm)

        # When: 要約を生成する
        result = svc.generate_summary(sample_history, "scenario")

        # Then: summary / key_points / learning_points が含まれる
        assert isinstance(result, dict)
        assert "summary" in result
        assert "key_points" in result
        assert "learning_points" in result
        assert result["summary"] == "進捗報告のやり取りが行われた"
        assert result["key_points"] == ["目的を明確にした", "相手の質問に応じた"]
        assert result["learning_points"] == ["報告前に論点を整理する"]
        llm.invoke.assert_called_once()


class TestSummaryServiceChat:
    def test_chat_mode_returns_summary_structure(self, sample_history):
        # Given: 雑談モードと正常 JSON を返すモック LLM
        llm = _llm_ok_response()
        svc = SummaryService(llm=llm)

        # When: 雑談モードで要約を生成する
        result = svc.generate_summary(sample_history, "chat")

        # Then: 同様に summary / key_points / learning_points が得られる
        assert result["summary"] == "進捗報告のやり取りが行われた"
        assert len(result["key_points"]) >= 1
        assert len(result["learning_points"]) >= 1


class TestSummaryServiceEmptyHistory:
    def test_empty_history_returns_empty_summary(self):
        # Given: 空の履歴
        llm = Mock()
        svc = SummaryService(llm=llm)

        # When: 要約を生成する
        result = svc.generate_summary([], "scenario")

        # Then: 空の要約（文字列空・リスト空）で LLM は呼ばれない
        assert result["summary"] == ""
        assert result["key_points"] == []
        assert result["learning_points"] == []
        llm.invoke.assert_not_called()


class TestSummaryServiceLlmFailure:
    def test_llm_failure_returns_fallback_without_raising(self, sample_history):
        # Given: invoke が例外を投げるモック LLM
        llm = Mock()
        llm.invoke.side_effect = RuntimeError("Gemini API error")
        svc = SummaryService(llm=llm)

        # When: 要約を生成する
        result = svc.generate_summary(sample_history, "scenario")

        # Then: 例外にならずフォールバック要約が返る
        assert isinstance(result, dict)
        assert "[フォールバック]" in result["summary"]
        assert len(result["key_points"]) >= 1
        assert len(result["learning_points"]) >= 1


class TestSummaryServiceListTypes:
    def test_key_points_and_learning_points_are_lists(self, sample_history):
        # Given: 正常応答のモック LLM
        svc = SummaryService(llm=_llm_ok_response())

        # When: 要約を生成する
        result = svc.generate_summary(sample_history, "scenario")

        # Then: key_points と learning_points は list 型である
        assert isinstance(result["key_points"], list)
        assert isinstance(result["learning_points"], list)
        for x in result["key_points"]:
            assert isinstance(x, str)
        for x in result["learning_points"]:
            assert isinstance(x, str)
