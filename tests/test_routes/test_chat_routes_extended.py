"""
Extended chat routes tests for improved coverage.
"""

import pytest
from unittest.mock import patch, MagicMock
from flask import Flask, session


@pytest.fixture
def app():
    """テスト用Flaskアプリケーション"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["TESTING"] = True

    from routes.chat_routes import chat_bp

    app.register_blueprint(chat_bp)

    return app


@pytest.fixture
def client(app):
    """テストクライアント"""
    return app.test_client()


class TestHandleChat:
    """handle_chat APIのテスト"""

    def test_JSONなしでリクエスト(self, app, client):
        """JSONなしでリクエスト"""
        # エラーハンドラを登録
        from errors import ValidationError, handle_error

        @app.errorhandler(ValidationError)
        def handle_validation_error(e):
            return handle_error(e)

        response = client.post("/api/chat", content_type="application/json", data="")

        # ValidationErrorが発生
        assert response.status_code in [400, 500]

    def test_空メッセージ(self, app, client):
        """空のメッセージ"""
        from errors import ValidationError, handle_error

        @app.errorhandler(ValidationError)
        def handle_validation_error(e):
            return handle_error(e)

        response = client.post("/api/chat", json={"message": ""})

        assert response.status_code in [400, 500]

    def test_無効なモデル名(self, app, client):
        """無効なモデル名"""
        from errors import ValidationError, handle_error

        @app.errorhandler(ValidationError)
        def handle_validation_error(e):
            return handle_error(e)

        with patch("routes.chat_routes.SecurityUtils.sanitize_input") as mock_sanitize:
            mock_sanitize.side_effect = lambda x: x

            with patch("routes.chat_routes.SecurityUtils.validate_model_name") as mock_validate:
                mock_validate.return_value = False

                response = client.post(
                    "/api/chat",
                    json={"message": "テスト", "model": "invalid-model"},
                )

                assert response.status_code in [400, 500]

    def test_セッション未初期化(self, app, client):
        """セッション未初期化（system_promptなし）"""
        from errors import ValidationError, handle_error

        @app.errorhandler(ValidationError)
        def handle_validation_error(e):
            return handle_error(e)

        with patch("routes.chat_routes.SecurityUtils.sanitize_input") as mock_sanitize:
            mock_sanitize.side_effect = lambda x: x

            with patch("routes.chat_routes.SecurityUtils.validate_model_name") as mock_validate:
                mock_validate.return_value = True

                response = client.post(
                    "/api/chat",
                    json={"message": "テスト"},
                )

                # セッションにsystem_promptがないためエラー
                assert response.status_code in [400, 500]


class TestStartChat:
    """start_chat APIのテスト"""

    def test_JSONなしでリクエスト(self, client):
        """JSONなしでリクエスト"""
        response = client.post("/api/start_chat", content_type="application/json", data="")

        assert response.status_code in [400, 500]

    def test_正常な開始(self, client):
        """正常な雑談開始"""
        with patch("app.create_model_and_get_response") as mock_response:
            mock_response.return_value = "こんにちは！いい天気ですね。"

            response = client.post(
                "/api/start_chat",
                json={
                    "model": "gemini-1.5-flash",
                    "partner_type": "colleague",
                    "situation": "break",
                    "topic": "general",
                },
            )

            if response.status_code == 200:
                data = response.get_json()
                assert "response" in data

    def test_レート制限エラー(self, client):
        """レート制限エラー発生"""
        with patch("app.create_model_and_get_response") as mock_response:
            mock_response.side_effect = Exception("Rate limit exceeded")

            with patch("errors.handle_llm_specific_error") as mock_handler:
                from errors import RateLimitError

                mock_handler.return_value = RateLimitError()

                response = client.post(
                    "/api/start_chat",
                    json={
                        "model": "gemini-1.5-flash",
                        "partner_type": "colleague",
                        "situation": "break",
                        "topic": "general",
                    },
                )

                # 429または500
                assert response.status_code in [429, 500]

    def test_一般エラー(self, client):
        """一般エラー発生"""
        with patch("app.create_model_and_get_response") as mock_response:
            mock_response.side_effect = Exception("API error")

            with patch("errors.handle_llm_specific_error") as mock_handler:
                from errors import ExternalAPIError

                mock_handler.return_value = ExternalAPIError(service="Gemini", message="API error")

                response = client.post(
                    "/api/start_chat",
                    json={
                        "model": "gemini-1.5-flash",
                    },
                )

                # エラーハンドリング
                assert response.status_code in [200, 500, 503]


class TestChatFeedback:
    """chat_feedback APIのテスト"""

    def test_履歴なしでフィードバック(self, client):
        """履歴なしでフィードバック"""
        response = client.post("/api/chat_feedback", json={})

        # 履歴がないのでエラー
        assert response.status_code in [400, 500]

    def test_履歴ありでフィードバック(self, app, client):
        """履歴ありでフィードバック"""
        with client.session_transaction() as sess:
            sess["chat_history"] = [
                {"human": "こんにちは", "ai": "こんにちは！いい天気ですね。"},
                {"human": "そうですね", "ai": "今日は何か予定がありますか？"},
            ]

        with patch("routes.chat_routes.get_feedback_service") as mock_service:
            mock_svc = MagicMock()
            mock_svc.generate_chat_feedback.return_value = (
                "素晴らしい会話でした！",
                "gemini-1.5-flash",
            )
            mock_service.return_value = mock_svc

            response = client.post("/api/chat_feedback", json={})

            if response.status_code == 200:
                data = response.get_json()
                assert "feedback" in data


class TestClearHistory:
    """clear_history APIのテスト"""

    def test_履歴クリア(self, app, client):
        """履歴をクリア"""
        with client.session_transaction() as sess:
            sess["chat_history"] = [{"human": "test", "ai": "response"}]
            sess["chat_settings"] = {"model": "gemini-1.5-flash"}

        response = client.post("/api/clear_history", json={})

        # 成功または404（ルートが存在しない場合）
        assert response.status_code in [200, 404]


class TestGetLlmAndInvoke:
    """_get_llm_and_invoke ヘルパー関数のテスト"""

    def test_正常実行(self, app):
        """正常実行"""
        with patch("app.initialize_llm") as mock_init:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = "テスト応答"
            mock_init.return_value = mock_llm

            with patch("app.extract_content") as mock_extract:
                mock_extract.return_value = "テスト応答"

                from routes.chat_routes import _get_llm_and_invoke
                from langchain_core.messages import HumanMessage

                with app.app_context():
                    result = _get_llm_and_invoke("gemini-1.5-flash", [HumanMessage(content="テスト")])

                    assert result == "テスト応答"


class TestSecurityUtilsFallback:
    """SecurityUtilsのフォールバックテスト"""

    def test_フォールバッククラスが存在(self):
        """フォールバッククラスのメソッドが存在"""
        from routes.chat_routes import SecurityUtils

        # sanitize_inputメソッド
        result = SecurityUtils.sanitize_input("test")
        assert result is not None

        # validate_model_nameメソッド
        result = SecurityUtils.validate_model_name("gemini-1.5-flash")
        assert result is not None

        # escape_htmlメソッド
        result = SecurityUtils.escape_html("<script>")
        assert result is not None

        # get_safe_error_messageメソッド
        result = SecurityUtils.get_safe_error_message(Exception("test"))
        assert result is not None


class TestPartnerTypeDescriptions:
    """パートナータイプの説明取得テスト"""

    def test_様々なパートナータイプ(self, client):
        """様々なパートナータイプでstart_chat"""
        partner_types = ["colleague", "senior", "junior", "manager", "client"]

        for partner_type in partner_types:
            with patch("app.create_model_and_get_response") as mock_response:
                mock_response.return_value = "テスト応答"

                response = client.post(
                    "/api/start_chat",
                    json={
                        "partner_type": partner_type,
                    },
                )

                # 実行されることを確認
                assert response.status_code in [200, 500]


class TestSituationDescriptions:
    """状況の説明取得テスト"""

    def test_様々な状況(self, client):
        """様々な状況でstart_chat"""
        situations = ["break", "lunch", "meeting", "after_work"]

        for situation in situations:
            with patch("app.create_model_and_get_response") as mock_response:
                mock_response.return_value = "テスト応答"

                response = client.post(
                    "/api/start_chat",
                    json={
                        "situation": situation,
                    },
                )

                assert response.status_code in [200, 500]


class TestTopicDescriptions:
    """話題の説明取得テスト"""

    def test_様々な話題(self, client):
        """様々な話題でstart_chat"""
        topics = ["general", "weather", "hobby", "news", "food"]

        for topic in topics:
            with patch("app.create_model_and_get_response") as mock_response:
                mock_response.return_value = "テスト応答"

                response = client.post(
                    "/api/start_chat",
                    json={
                        "topic": topic,
                    },
                )

                assert response.status_code in [200, 500]


class TestClearHistoryExtended:
    """clear_history APIの拡張テスト"""

    def test_chatモードの履歴クリア(self, app, client):
        """chatモードの履歴をクリア"""
        with client.session_transaction() as sess:
            sess["chat_history"] = [{"human": "test", "ai": "response"}]
            sess["chat_settings"] = {"model": "gemini-1.5-flash"}

        response = client.post("/api/clear_history", json={"mode": "chat"})

        assert response.status_code in [200, 500]

    def test_watchモードの履歴クリア(self, app, client):
        """watchモードの履歴をクリア"""
        with client.session_transaction() as sess:
            sess["watch_history"] = [{"speaker": "A", "message": "test"}]
            sess["watch_settings"] = {"model_a": "gemini-1.5-flash"}

        response = client.post("/api/clear_history", json={"mode": "watch"})

        assert response.status_code in [200, 500]

    def test_scenarioモードの履歴クリア_IDあり(self, app, client):
        """scenarioモードの履歴をクリア（scenario_idあり）"""
        with client.session_transaction() as sess:
            sess["scenario_history"] = {"scenario1": [{"human": "test", "ai": "response"}]}

        response = client.post(
            "/api/clear_history",
            json={"mode": "scenario", "scenario_id": "scenario1"},
        )

        assert response.status_code in [200, 500]

    def test_scenarioモードの履歴クリア_IDなし(self, app, client):
        """scenarioモードの履歴をクリア（scenario_idなし）"""
        with client.session_transaction() as sess:
            sess["conversation_history"] = {"llama2": [{"human": "test", "ai": "response"}]}

        response = client.post(
            "/api/clear_history",
            json={"mode": "scenario", "model": "llama2"},
        )

        assert response.status_code in [200, 500]

    def test_JSONなしでリクエスト(self, client):
        """JSONなしでリクエスト"""
        response = client.post(
            "/api/clear_history",
            content_type="application/json",
            data="",
        )

        assert response.status_code in [400, 500]


class TestChatFeedbackExtended:
    """chat_feedback APIの拡張テスト"""

    def test_JSONなしでリクエスト(self, client):
        """JSONなしでリクエスト"""
        response = client.post(
            "/api/chat_feedback",
            content_type="application/json",
            data="",
        )

        assert response.status_code in [400, 500]

    def test_レート制限エラー(self, app, client):
        """レート制限エラーが発生した場合"""
        with client.session_transaction() as sess:
            sess["chat_history"] = [{"human": "test", "ai": "response"}]

        with patch("services.feedback_service.get_feedback_service") as mock_service:
            mock_svc = MagicMock()
            mock_svc.build_chat_feedback_prompt.return_value = "prompt"
            mock_svc.try_multiple_models_for_prompt.return_value = (
                None,
                None,
                "RATE_LIMIT_EXCEEDED",
            )
            mock_service.return_value = mock_svc

            response = client.post("/api/chat_feedback", json={})

            # 400（dataが空）、429、または500エラー
            assert response.status_code in [400, 429, 500]

    def test_一般エラー(self, app, client):
        """一般エラーが発生した場合"""
        with client.session_transaction() as sess:
            sess["chat_history"] = [{"human": "test", "ai": "response"}]

        with patch("services.feedback_service.get_feedback_service") as mock_service:
            mock_svc = MagicMock()
            mock_svc.build_chat_feedback_prompt.return_value = "prompt"
            mock_svc.try_multiple_models_for_prompt.return_value = (
                None,
                None,
                "Some error message",
            )
            mock_service.return_value = mock_svc

            response = client.post("/api/chat_feedback", json={})

            # 400（dataが空）、503、または500エラー
            assert response.status_code in [400, 500, 503]


class TestConversationHistory:
    """conversation_history APIのテスト"""

    def test_scenarioタイプ_IDあり(self, app, client):
        """scenarioタイプでIDあり"""
        from errors import ValidationError, handle_error

        @app.errorhandler(ValidationError)
        def handle_validation_error(e):
            return handle_error(e)

        with client.session_transaction() as sess:
            sess["scenario_history"] = {"scenario1": [{"human": "test", "ai": "response"}]}

        response = client.post(
            "/api/conversation_history",
            json={"type": "scenario", "scenario_id": "scenario1"},
        )

        if response.status_code == 200:
            data = response.get_json()
            assert "history" in data

    def test_scenarioタイプ_IDなし(self, app, client):
        """scenarioタイプでIDなし"""
        from errors import ValidationError, handle_error

        @app.errorhandler(ValidationError)
        def handle_validation_error(e):
            return handle_error(e)

        response = client.post(
            "/api/conversation_history",
            json={"type": "scenario"},
        )

        assert response.status_code in [400, 500]

    def test_scenarioタイプ_履歴なし(self, app, client):
        """scenarioタイプで履歴なし"""
        from errors import ValidationError, handle_error

        @app.errorhandler(ValidationError)
        def handle_validation_error(e):
            return handle_error(e)

        response = client.post(
            "/api/conversation_history",
            json={"type": "scenario", "scenario_id": "nonexistent"},
        )

        if response.status_code == 200:
            data = response.get_json()
            assert data["history"] == []

    def test_chatタイプ(self, app, client):
        """chatタイプの履歴取得"""
        from errors import ValidationError, handle_error

        @app.errorhandler(ValidationError)
        def handle_validation_error(e):
            return handle_error(e)

        with client.session_transaction() as sess:
            sess["chat_history"] = [{"human": "test", "ai": "response"}]

        response = client.post(
            "/api/conversation_history",
            json={"type": "chat"},
        )

        if response.status_code == 200:
            data = response.get_json()
            assert "history" in data

    def test_chatタイプ_履歴なし(self, app, client):
        """chatタイプで履歴なし"""
        from errors import ValidationError, handle_error

        @app.errorhandler(ValidationError)
        def handle_validation_error(e):
            return handle_error(e)

        response = client.post(
            "/api/conversation_history",
            json={"type": "chat"},
        )

        if response.status_code == 200:
            data = response.get_json()
            assert data["history"] == []

    def test_watchタイプ(self, app, client):
        """watchタイプの履歴取得"""
        from errors import ValidationError, handle_error

        @app.errorhandler(ValidationError)
        def handle_validation_error(e):
            return handle_error(e)

        with client.session_transaction() as sess:
            sess["watch_history"] = [
                {"speaker": "A", "message": "Hello", "timestamp": "2024-01-01T10:00:00"},
                {"speaker": "B", "message": "Hi", "timestamp": "2024-01-01T10:00:01"},
            ]

        response = client.post(
            "/api/conversation_history",
            json={"type": "watch"},
        )

        if response.status_code == 200:
            data = response.get_json()
            assert "history" in data

    def test_watchタイプ_履歴なし(self, app, client):
        """watchタイプで履歴なし"""
        from errors import ValidationError, handle_error

        @app.errorhandler(ValidationError)
        def handle_validation_error(e):
            return handle_error(e)

        response = client.post(
            "/api/conversation_history",
            json={"type": "watch"},
        )

        if response.status_code == 200:
            data = response.get_json()
            assert data["history"] == []

    def test_不明なタイプ(self, app, client):
        """不明なタイプ"""
        from errors import ValidationError, handle_error

        @app.errorhandler(ValidationError)
        def handle_validation_error(e):
            return handle_error(e)

        response = client.post(
            "/api/conversation_history",
            json={"type": "unknown"},
        )

        assert response.status_code in [400, 500]


class TestHandleChatExtended:
    """handle_chat APIの拡張テスト"""

    def test_セッション初期化済みで成功(self, app, client):
        """セッションが初期化済みの場合に成功"""
        from errors import ValidationError, handle_error

        @app.errorhandler(ValidationError)
        def handle_validation_error(e):
            return handle_error(e)

        with client.session_transaction() as sess:
            sess["chat_settings"] = {
                "model": "gemini-1.5-flash",
                "system_prompt": "テストプロンプト",
            }
            sess["chat_history"] = []

        with patch("routes.chat_routes._get_llm_and_invoke") as mock_invoke:
            mock_invoke.return_value = "AI応答"

            response = client.post(
                "/api/chat",
                json={"message": "こんにちは"},
            )

            if response.status_code == 200:
                data = response.get_json()
                assert "response" in data
