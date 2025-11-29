"""
Chat routes tests for improved coverage.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestHandleChat:
    """POST /api/chat のテスト"""

    def test_チャットAPIが正常に応答を返す(self, csrf_client):
        """チャットセッション初期化済みの状態でメッセージを送信"""
        with csrf_client.session_transaction() as sess:
            sess["chat_settings"] = {
                "system_prompt": "あなたは職場での雑談練習をサポートするAIアシスタントです。",
                "model": "gemini-1.5-flash",
            }
            sess["chat_history"] = []

        with patch("routes.chat_routes._get_llm_and_invoke") as mock_invoke:
            mock_invoke.return_value = "こんにちは！今日はいい天気ですね。"

            response = csrf_client.post(
                "/api/chat",
                json={"message": "こんにちは", "model": "gemini-1.5-flash"},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert "response" in data

    def test_空のメッセージでエラーを返す(self, csrf_client):
        """空のメッセージを送信した場合"""
        with csrf_client.session_transaction() as sess:
            sess["chat_settings"] = {
                "system_prompt": "test",
                "model": "gemini-1.5-flash",
            }

        response = csrf_client.post(
            "/api/chat", json={"message": "", "model": "gemini-1.5-flash"}
        )

        assert response.status_code == 400

    def test_セッション未初期化でエラーを返す(self, csrf_client):
        """チャットセッションが初期化されていない場合"""
        response = csrf_client.post(
            "/api/chat", json={"message": "テスト", "model": "gemini-1.5-flash"}
        )

        assert response.status_code == 400

    def test_無効なモデル名でエラーを返す(self, csrf_client):
        """無効なモデル名を指定した場合"""
        with csrf_client.session_transaction() as sess:
            sess["chat_settings"] = {
                "system_prompt": "test",
                "model": "gemini-1.5-flash",
            }

        response = csrf_client.post(
            "/api/chat",
            json={"message": "テスト", "model": "invalid-model-name!!!"},
        )

        assert response.status_code == 400


class TestStartChat:
    """POST /api/start_chat のテスト"""

    def test_雑談開始が正常に動作する(self, csrf_client):
        """雑談を正常に開始できること"""
        with patch("app.create_model_and_get_response") as mock_create:
            mock_create.return_value = "おはようございます！今日もお仕事お疲れ様です。"

            response = csrf_client.post(
                "/api/start_chat",
                json={
                    "model": "gemini-1.5-flash",
                    "partner_type": "colleague",
                    "situation": "break",
                    "topic": "general",
                },
            )

            assert response.status_code == 200
            data = response.get_json()
            assert "response" in data

    def test_異なるパートナータイプで開始できる(self, csrf_client):
        """異なるパートナータイプで雑談を開始"""
        partner_types = ["colleague", "senior", "junior", "boss", "client"]

        for partner_type in partner_types:
            with patch("app.create_model_and_get_response") as mock_create:
                mock_create.return_value = "テスト応答"

                response = csrf_client.post(
                    "/api/start_chat",
                    json={
                        "model": "gemini-1.5-flash",
                        "partner_type": partner_type,
                        "situation": "break",
                        "topic": "general",
                    },
                )

                assert response.status_code == 200

    def test_異なる状況で開始できる(self, csrf_client):
        """異なる状況設定で雑談を開始"""
        situations = ["break", "lunch", "morning", "evening", "party"]

        for situation in situations:
            with patch("app.create_model_and_get_response") as mock_create:
                mock_create.return_value = "テスト応答"

                response = csrf_client.post(
                    "/api/start_chat",
                    json={
                        "model": "gemini-1.5-flash",
                        "partner_type": "colleague",
                        "situation": situation,
                        "topic": "general",
                    },
                )

                assert response.status_code == 200

    def test_異なる話題で開始できる(self, csrf_client):
        """異なる話題設定で雑談を開始"""
        topics = ["general", "hobby", "news", "food", "work"]

        for topic in topics:
            with patch("app.create_model_and_get_response") as mock_create:
                mock_create.return_value = "テスト応答"

                response = csrf_client.post(
                    "/api/start_chat",
                    json={
                        "model": "gemini-1.5-flash",
                        "partner_type": "colleague",
                        "situation": "break",
                        "topic": topic,
                    },
                )

                assert response.status_code == 200

    def test_レート制限エラーを適切に処理する(self, csrf_client):
        """レート制限エラーが発生した場合"""
        with patch("app.create_model_and_get_response") as mock_create:
            mock_create.side_effect = Exception("429 Resource has been exhausted")

            response = csrf_client.post(
                "/api/start_chat",
                json={
                    "model": "gemini-1.5-flash",
                    "partner_type": "colleague",
                    "situation": "break",
                    "topic": "general",
                },
            )

            # エラーが適切に処理されること
            assert response.status_code in [429, 500]


class TestClearHistory:
    """POST /api/clear_history のテスト"""

    def test_チャット履歴をクリアできる(self, csrf_client):
        """チャットモードの履歴をクリア"""
        with csrf_client.session_transaction() as sess:
            sess["chat_history"] = [{"human": "test", "ai": "response"}]
            sess["chat_settings"] = {"model": "test"}

        response = csrf_client.post("/api/clear_history", json={"mode": "chat"})

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"

        # セッション上の履歴が実際にクリアされていることも確認
        with csrf_client.session_transaction() as sess:
            assert sess.get("chat_history") in (None, [])

    def test_観戦履歴をクリアできる(self, csrf_client):
        """観戦モードの履歴をクリア"""
        with csrf_client.session_transaction() as sess:
            sess["watch_history"] = [{"speaker": "A", "message": "test"}]
            sess["watch_settings"] = {"topic": "test"}

        response = csrf_client.post("/api/clear_history", json={"mode": "watch"})

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"

        # セッション上の履歴が実際にクリアされていることも確認
        with csrf_client.session_transaction() as sess:
            assert sess.get("watch_history") in (None, [])

    def test_シナリオ履歴をクリアできる(self, csrf_client):
        """シナリオモードの履歴をクリア"""
        with csrf_client.session_transaction() as sess:
            sess["scenario_history"] = {
                "scenario_1": [{"human": "test", "ai": "response"}]
            }

        response = csrf_client.post(
            "/api/clear_history",
            json={"mode": "scenario", "scenario_id": "scenario_1"},
        )

        assert response.status_code == 200

    def test_conversation_history_クリアできる(self, csrf_client):
        """conversation_historyのクリア"""
        with csrf_client.session_transaction() as sess:
            sess["conversation_history"] = {"llama2": [{"human": "test", "ai": "response"}]}

        response = csrf_client.post(
            "/api/clear_history",
            json={"mode": "scenario", "model": "llama2"},
        )

        assert response.status_code == 200


class TestChatFeedback:
    """POST /api/chat_feedback のテスト"""

    def test_フィードバックを正常に生成できる(self, csrf_client):
        """チャットフィードバックを生成"""
        with csrf_client.session_transaction() as sess:
            sess["chat_history"] = [
                {"human": "こんにちは", "ai": "こんにちは！"},
                {"human": "今日は天気がいいですね", "ai": "そうですね、気持ちいい天気ですね。"},
            ]

        with patch(
            "services.feedback_service.FeedbackService.build_chat_feedback_prompt"
        ) as mock_build:
            mock_build.return_value = "フィードバックプロンプト"

            with patch(
                "services.feedback_service.FeedbackService.try_multiple_models_for_prompt"
            ) as mock_try:
                mock_try.return_value = (
                    "良いコミュニケーションでした！",
                    "gemini-1.5-flash",
                    None,
                )

                with patch(
                    "services.strength_service.StrengthService.update_feedback_with_strength_analysis"
                ) as mock_strength:
                    mock_strength.return_value = {
                        "feedback": "良いコミュニケーションでした！",
                        "model_used": "gemini-1.5-flash",
                        "status": "success",
                    }

                    response = csrf_client.post(
                        "/api/chat_feedback",
                        json={
                            "model": "gemini-1.5-flash",
                            "partner_type": "colleague",
                            "situation": "break",
                        },
                    )

                    assert response.status_code == 200
                    data = response.get_json()
                    assert "feedback" in data

    def test_履歴がない場合エラーを返す(self, csrf_client):
        """会話履歴がない場合"""
        response = csrf_client.post(
            "/api/chat_feedback",
            json={"model": "gemini-1.5-flash"},
        )

        assert response.status_code == 404

    def test_レート制限エラーを処理する(self, csrf_client):
        """レート制限エラーの処理"""
        with csrf_client.session_transaction() as sess:
            sess["chat_history"] = [{"human": "test", "ai": "response"}]

        with patch(
            "services.feedback_service.FeedbackService.build_chat_feedback_prompt"
        ) as mock_build:
            mock_build.return_value = "prompt"

            with patch(
                "services.feedback_service.FeedbackService.try_multiple_models_for_prompt"
            ) as mock_try:
                mock_try.return_value = (None, None, "RATE_LIMIT_EXCEEDED")

                response = csrf_client.post(
                    "/api/chat_feedback",
                    json={"model": "gemini-1.5-flash"},
                )

                assert response.status_code == 429

    def test_その他のエラーを処理する(self, csrf_client):
        """その他のエラーの処理"""
        with csrf_client.session_transaction() as sess:
            sess["chat_history"] = [{"human": "test", "ai": "response"}]

        with patch(
            "services.feedback_service.FeedbackService.build_chat_feedback_prompt"
        ) as mock_build:
            mock_build.return_value = "prompt"

            with patch(
                "services.feedback_service.FeedbackService.try_multiple_models_for_prompt"
            ) as mock_try:
                mock_try.return_value = (None, None, "API Error")

                response = csrf_client.post(
                    "/api/chat_feedback",
                    json={"model": "gemini-1.5-flash"},
                )

                assert response.status_code == 503


class TestConversationHistory:
    """POST /api/conversation_history のテスト"""

    def test_シナリオ履歴を取得できる(self, csrf_client):
        """シナリオタイプの履歴取得"""
        with csrf_client.session_transaction() as sess:
            sess["scenario_history"] = {
                "scenario_1": [{"human": "test", "ai": "response"}]
            }

        response = csrf_client.post(
            "/api/conversation_history",
            json={"type": "scenario", "scenario_id": "scenario_1"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "history" in data
        assert len(data["history"]) == 1

    def test_チャット履歴を取得できる(self, csrf_client):
        """チャットタイプの履歴取得"""
        with csrf_client.session_transaction() as sess:
            sess["chat_history"] = [{"human": "hello", "ai": "hi"}]

        response = csrf_client.post(
            "/api/conversation_history", json={"type": "chat"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "history" in data

    def test_観戦履歴を取得できる(self, csrf_client):
        """観戦タイプの履歴取得"""
        with csrf_client.session_transaction() as sess:
            sess["watch_history"] = [
                {"speaker": "A", "message": "hello", "timestamp": "2024-01-01"},
                {"speaker": "B", "message": "hi", "timestamp": "2024-01-01"},
            ]

        response = csrf_client.post(
            "/api/conversation_history", json={"type": "watch"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "history" in data

    def test_履歴がない場合空リストを返す(self, csrf_client):
        """履歴がない場合"""
        response = csrf_client.post(
            "/api/conversation_history", json={"type": "chat"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["history"] == []

    def test_シナリオIDなしでエラーを返す(self, csrf_client):
        """シナリオタイプでIDがない場合"""
        response = csrf_client.post(
            "/api/conversation_history", json={"type": "scenario"}
        )

        assert response.status_code == 400

    def test_不明な履歴タイプでエラーを返す(self, csrf_client):
        """不明な履歴タイプを指定した場合"""
        response = csrf_client.post(
            "/api/conversation_history", json={"type": "unknown"}
        )

        assert response.status_code == 400

    def test_シナリオ履歴が存在しない場合空リストを返す(self, csrf_client):
        """シナリオ履歴が存在しない場合"""
        response = csrf_client.post(
            "/api/conversation_history",
            json={"type": "scenario", "scenario_id": "nonexistent"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["history"] == []

    def test_観戦履歴が存在しない場合空リストを返す(self, csrf_client):
        """観戦履歴が存在しない場合"""
        response = csrf_client.post(
            "/api/conversation_history", json={"type": "watch"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["history"] == []
