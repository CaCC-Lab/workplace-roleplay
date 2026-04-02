"""
観戦モード /api/watch/next と QuizService の統合テスト

参照: .kiro/specs/gamification/requirements.md 要件5.1, 5.3
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from services.quiz_service import QuizService


def _watch_session_base():
    return {
        "model_a": "gemini-1.5-flash",
        "model_b": "gemini-1.5-pro",
        "partner_type": "colleague",
        "situation": "break",
        "topic": "general",
    }


class TestWatchQuizIntegration:
    """message_count と QUIZ_INTERVAL に応じた quiz フィールドの有無"""

    def test_watch_next_includes_quiz_when_message_count_is_multiple_of_interval(self, csrf_client):
        # Given: 履歴が4件（次の発言で5件目 = QUIZ_INTERVAL）
        # When: POST /api/watch/next
        # Then: レスポンスに quiz が含まれる（要件5.1）
        with csrf_client.session_transaction() as sess:
            sess["watch_settings"] = {
                **_watch_session_base(),
                "current_speaker": "B",
            }
            sess["watch_history"] = [
                {"speaker": "A", "message": "a1", "timestamp": "2024-01-01T10:00:00"},
                {"speaker": "B", "message": "b1", "timestamp": "2024-01-01T10:00:01"},
                {"speaker": "A", "message": "a2", "timestamp": "2024-01-01T10:00:02"},
                {"speaker": "B", "message": "b2", "timestamp": "2024-01-01T10:00:03"},
            ]

        with patch("app.initialize_llm") as mock_llm:
            mock_llm.return_value = MagicMock()
            with patch("services.watch_service.WatchService.generate_next_message") as mock_gen:
                mock_gen.return_value = "次の発言です。"
                response = csrf_client.post("/api/watch/next", json={})

        assert response.status_code == 200
        data = response.get_json()
        assert "quiz" in data
        assert "choices" in data["quiz"]
        assert 3 <= len(data["quiz"]["choices"]) <= 4

    def test_watch_next_omits_quiz_when_message_count_not_multiple_of_interval(self, csrf_client):
        # Given: 履歴が2件（次で3件目、5の倍数でない）
        # When: POST /api/watch/next
        # Then: quiz は含まれない
        with csrf_client.session_transaction() as sess:
            sess["watch_settings"] = {
                **_watch_session_base(),
                "current_speaker": "B",
            }
            sess["watch_history"] = [
                {"speaker": "A", "message": "a1", "timestamp": "2024-01-01T10:00:00"},
                {"speaker": "B", "message": "b1", "timestamp": "2024-01-01T10:00:01"},
            ]

        with patch("app.initialize_llm") as mock_llm:
            mock_llm.return_value = MagicMock()
            with patch("services.watch_service.WatchService.generate_next_message") as mock_gen:
                mock_gen.return_value = "三回目の発言。"
                response = csrf_client.post("/api/watch/next", json={})

        assert response.status_code == 200
        data = response.get_json()
        assert "quiz" not in data

    def test_watch_next_uses_llm_quiz_when_quiz_service_has_llm_mock(self, csrf_client, monkeypatch):
        # Given: QuizService に LLM モックを渡す（フォールバックではないクイズ）
        # When: 5件目でクイズ生成
        # Then: LLM が返した question がそのまま含まれる（要件5.3）
        mock_llm = MagicMock()
        mock_llm.generate_quiz_content.return_value = {
            "question": "INTEGRATION_LLM_QUIZ_QUESTION",
            "choices": ["甲", "乙", "丙"],
            "correct_answer": 1,
        }

        def _factory():
            return QuizService(llm_service=mock_llm)

        monkeypatch.setattr("routes.watch_routes.get_watch_quiz_service", _factory)

        with csrf_client.session_transaction() as sess:
            sess["watch_settings"] = {
                **_watch_session_base(),
                "current_speaker": "B",
            }
            sess["watch_history"] = [
                {"speaker": "A", "message": "a1", "timestamp": "2024-01-01T10:00:00"},
                {"speaker": "B", "message": "b1", "timestamp": "2024-01-01T10:00:01"},
                {"speaker": "A", "message": "a2", "timestamp": "2024-01-01T10:00:02"},
                {"speaker": "B", "message": "b2", "timestamp": "2024-01-01T10:00:03"},
            ]

        with patch("app.initialize_llm") as mock_llm_watch:
            mock_llm_watch.return_value = MagicMock()
            with patch("services.watch_service.WatchService.generate_next_message") as mock_gen:
                mock_gen.return_value = "五件目。"
                response = csrf_client.post("/api/watch/next", json={})

        assert response.status_code == 200
        data = response.get_json()
        assert data["quiz"]["question"] == "INTEGRATION_LLM_QUIZ_QUESTION"
        assert data["quiz"]["choices"] == ["甲", "乙", "丙"]
        mock_llm.generate_quiz_content.assert_called_once()
