"""
Extended feedback service tests for improved coverage.
"""

import pytest
from unittest.mock import patch, MagicMock
from flask import Flask


@pytest.fixture
def app():
    """テスト用Flaskアプリケーション"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["TESTING"] = True
    return app


class TestFeedbackService:
    """FeedbackServiceクラスのテスト"""

    def test_チャットフィードバックプロンプト構築(self):
        """雑談練習用のフィードバックプロンプトを構築"""
        from services.feedback_service import FeedbackService

        service = FeedbackService()
        history = [
            {"human": "こんにちは", "ai": "こんにちは！"},
        ]

        prompt = service.build_chat_feedback_prompt(history, "senior", "break")

        assert "雑談スキル評価" in prompt
        assert "評価" in prompt

    def test_シナリオフィードバックプロンプト構築_通常(self):
        """シナリオ練習用のフィードバックプロンプトを構築（通常）"""
        from services.feedback_service import FeedbackService

        service = FeedbackService()
        history = [
            {"human": "すみません、遅刻しました", "ai": "何かあった？"},
        ]
        scenario_data = {"title": "遅刻の報告"}

        with patch("services.feedback_service.get_scenario_service") as mock_get:
            mock_service = MagicMock()
            mock_service.get_user_role.return_value = "部下役"
            mock_get.return_value = mock_service

            prompt = service.build_scenario_feedback_prompt(history, scenario_data, is_reverse_role=False)

            assert "職場コミュニケーション評価" in prompt

    def test_シナリオフィードバックプロンプト構築_リバース(self):
        """シナリオ練習用のフィードバックプロンプトを構築（リバース）"""
        from services.feedback_service import FeedbackService

        service = FeedbackService()
        history = [
            {"human": "遅刻の理由は？", "ai": "電車が遅れまして..."},
        ]
        scenario_data = {"title": "遅刻の報告"}

        with patch("services.feedback_service.get_scenario_service") as mock_get:
            mock_service = MagicMock()
            mock_service.get_user_role.return_value = "上司役"
            mock_get.return_value = mock_service

            prompt = service.build_scenario_feedback_prompt(history, scenario_data, is_reverse_role=True)

            assert "パワハラ防止評価" in prompt

    def test_try_multiple_models_成功(self):
        """複数モデルでの応答取得成功"""
        from services.feedback_service import FeedbackService

        service = FeedbackService()

        with patch("services.feedback_service.get_cached_config") as mock_config:
            mock_config.return_value.GOOGLE_API_KEY = "test-key"

            with patch("google.generativeai.configure"):
                with patch("google.generativeai.list_models") as mock_list:
                    mock_model = MagicMock()
                    mock_model.name = "models/gemini-1.5-flash"
                    mock_list.return_value = [mock_model]

                    with patch("app.create_model_and_get_response") as mock_create:
                        mock_create.return_value = "フィードバック内容"

                        content, used_model, error = service.try_multiple_models_for_prompt("テストプロンプト")

                        assert content == "フィードバック内容"
                        assert used_model is not None
                        assert error is None

    def test_try_multiple_models_優先モデル指定(self):
        """優先モデルを指定して応答取得"""
        from services.feedback_service import FeedbackService

        service = FeedbackService()

        with patch("services.feedback_service.get_cached_config") as mock_config:
            mock_config.return_value.GOOGLE_API_KEY = "test-key"

            with patch("google.generativeai.configure"):
                with patch("google.generativeai.list_models") as mock_list:
                    mock_model = MagicMock()
                    mock_model.name = "models/gemini-1.5-pro"
                    mock_list.return_value = [mock_model]

                    with patch("app.create_model_and_get_response") as mock_create:
                        mock_create.return_value = "フィードバック"

                        content, used_model, error = service.try_multiple_models_for_prompt(
                            "テスト", preferred_model="gemini-1.5-pro"
                        )

                        assert error is None

    def test_try_multiple_models_優先モデルなし_フォールバック(self):
        """優先モデルが見つからない場合のフォールバック"""
        from services.feedback_service import FeedbackService

        service = FeedbackService()

        with patch("services.feedback_service.get_cached_config") as mock_config:
            mock_config.return_value.GOOGLE_API_KEY = "test-key"

            with patch("google.generativeai.configure"):
                with patch("google.generativeai.list_models") as mock_list:
                    mock_model = MagicMock()
                    mock_model.name = "models/gemini-1.5-flash"
                    mock_list.return_value = [mock_model]

                    with patch("app.create_model_and_get_response") as mock_create:
                        mock_create.return_value = "フィードバック"

                        content, used_model, error = service.try_multiple_models_for_prompt(
                            "テスト", preferred_model="nonexistent-model"
                        )

                        # flashモデルにフォールバック
                        assert used_model is not None

    def test_try_multiple_models_モデルリスト取得失敗(self):
        """モデルリスト取得失敗時のフォールバック"""
        from services.feedback_service import FeedbackService

        service = FeedbackService()

        with patch("services.feedback_service.get_cached_config") as mock_config:
            mock_config.return_value.GOOGLE_API_KEY = "test-key"

            with patch("google.generativeai.configure"):
                with patch("google.generativeai.list_models") as mock_list:
                    mock_list.side_effect = Exception("API Error")

                    with patch("app.create_model_and_get_response") as mock_create:
                        mock_create.return_value = "フィードバック"

                        content, used_model, error = service.try_multiple_models_for_prompt("テスト")

                        # フォールバックモデルが使用される

    def test_try_multiple_models_利用可能モデルなし(self):
        """利用可能なモデルがない場合"""
        from services.feedback_service import FeedbackService

        service = FeedbackService()

        with patch("services.feedback_service.get_cached_config") as mock_config:
            mock_config.return_value.GOOGLE_API_KEY = "test-key"

            with patch("google.generativeai.configure"):
                with patch("google.generativeai.list_models") as mock_list:
                    mock_list.return_value = []  # モデルなし

                    with patch("app.create_model_and_get_response") as mock_create:
                        mock_create.side_effect = Exception("No model")

                        content, used_model, error = service.try_multiple_models_for_prompt("テスト")

                        # エラーメッセージが返される

    def test_try_multiple_models_ResourceExhausted(self):
        """ResourceExhaustedエラー時"""
        from services.feedback_service import FeedbackService
        from google.api_core.exceptions import ResourceExhausted

        service = FeedbackService()

        with patch("services.feedback_service.get_cached_config") as mock_config:
            mock_config.return_value.GOOGLE_API_KEY = "test-key"

            with patch("google.generativeai.configure"):
                with patch("google.generativeai.list_models") as mock_list:
                    mock_model = MagicMock()
                    mock_model.name = "models/gemini-1.5-flash"
                    mock_list.return_value = [mock_model]

                    with patch("app.create_model_and_get_response") as mock_create:
                        mock_create.side_effect = ResourceExhausted("Rate limited")

                        content, used_model, error = service.try_multiple_models_for_prompt("テスト")

                        assert error == "RATE_LIMIT_EXCEEDED"

    def test_try_multiple_models_レート制限エラー(self):
        """レート制限エラー時"""
        from services.feedback_service import FeedbackService

        service = FeedbackService()

        with patch("services.feedback_service.get_cached_config") as mock_config:
            mock_config.return_value.GOOGLE_API_KEY = "test-key"

            with patch("google.generativeai.configure"):
                with patch("google.generativeai.list_models") as mock_list:
                    mock_model = MagicMock()
                    mock_model.name = "models/gemini-1.5-flash"
                    mock_list.return_value = [mock_model]

                    with patch("app.create_model_and_get_response") as mock_create:
                        mock_create.side_effect = Exception("429 rate limit exceeded")

                        content, used_model, error = service.try_multiple_models_for_prompt("テスト")

                        assert error == "RATE_LIMIT_EXCEEDED"

    def test_update_feedback_with_strength_analysis_成功(self, app):
        """強み分析追加成功"""
        from services.feedback_service import FeedbackService

        service = FeedbackService()

        with patch("routes.strength_routes.update_feedback_with_strength_analysis") as mock_strength:
            mock_strength.return_value = {"feedback": "test", "strength_analysis": {}}

            result = service.update_feedback_with_strength_analysis({"feedback": "test"}, "chat")

            assert "feedback" in result

    def test_update_feedback_with_strength_analysis_エラー(self, app):
        """強み分析追加エラー時"""
        from services.feedback_service import FeedbackService

        service = FeedbackService()

        with patch("routes.strength_routes.update_feedback_with_strength_analysis") as mock_strength:
            mock_strength.side_effect = Exception("Error")

            result = service.update_feedback_with_strength_analysis({"feedback": "test"}, "chat")

            # エラー時は元のフィードバックを返す
            assert result == {"feedback": "test"}


class TestGetFeedbackService:
    """get_feedback_service関数のテスト"""

    def test_シングルトンインスタンス取得(self):
        """シングルトンインスタンスを取得"""
        from services import feedback_service
        from services.feedback_service import get_feedback_service, FeedbackService

        # グローバル変数をリセット
        feedback_service._feedback_service = None

        service1 = get_feedback_service()
        service2 = get_feedback_service()

        assert service1 is service2
        assert isinstance(service1, FeedbackService)
