"""
FeedbackServiceのユニットテスト
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.feedback_service import FeedbackService, get_feedback_service


class TestFeedbackService:
    """FeedbackServiceのテストクラス"""

    @pytest.fixture
    def feedback_service(self):
        """FeedbackServiceインスタンス"""
        return FeedbackService()


class TestBuildChatFeedbackPrompt:
    """build_chat_feedback_promptメソッドのテスト"""

    @pytest.fixture
    def feedback_service(self):
        return FeedbackService()

    @pytest.fixture
    def sample_history(self):
        """テスト用の会話履歴"""
        return [
            {"role": "user", "content": "おはようございます"},
            {"role": "assistant", "content": "おはようございます！今日もお仕事頑張りましょう"},
            {"role": "user", "content": "そうですね、今日は会議がありますね"},
        ]

    def test_returns_string(self, feedback_service, sample_history):
        """プロンプトが文字列で返されることをテスト"""
        result = feedback_service.build_chat_feedback_prompt(sample_history, partner_type="同僚", situation="朝の挨拶")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_partner_type_info(self, feedback_service, sample_history):
        """相手タイプ情報が含まれることをテスト"""
        result = feedback_service.build_chat_feedback_prompt(sample_history, partner_type="上司", situation="報告")

        # プロンプトに相手情報が含まれていることを確認
        assert "対話相手" in result or "👥" in result

    def test_contains_situation_info(self, feedback_service, sample_history):
        """状況情報が含まれることをテスト"""
        result = feedback_service.build_chat_feedback_prompt(sample_history, partner_type="同僚", situation="ランチタイム")

        # プロンプトに状況情報が含まれていることを確認
        assert "状況" in result or "🏢" in result

    def test_contains_evaluation_criteria(self, feedback_service, sample_history):
        """評価基準が含まれることをテスト"""
        result = feedback_service.build_chat_feedback_prompt(sample_history, partner_type="同僚", situation="通常")

        # 評価関連のキーワードが含まれていることを確認
        assert "スコア" in result or "評価" in result
        assert "強み" in result or "良い点" in result or "コミュニケーション強み" in result

    def test_with_empty_history(self, feedback_service):
        """空の履歴での動作テスト"""
        result = feedback_service.build_chat_feedback_prompt([], partner_type="同僚", situation="通常")

        assert isinstance(result, str)
        assert len(result) > 0


class TestBuildScenarioFeedbackPrompt:
    """build_scenario_feedback_promptメソッドのテスト"""

    @pytest.fixture
    def feedback_service(self):
        return FeedbackService()

    @pytest.fixture
    def sample_history(self):
        return [
            {"role": "user", "content": "すみません、報告があります"},
            {"role": "assistant", "content": "はい、どうぞ"},
            {"role": "user", "content": "プロジェクトの進捗についてです"},
        ]

    @pytest.fixture
    def sample_scenario_data(self):
        return {"id": "test_scenario", "title": "進捗報告シナリオ", "role_info": "AIは上司役、ユーザーは部下役", "user_role": "上司"}

    @patch("services.feedback_service.get_scenario_service")
    def test_returns_string_normal_role(self, mock_get_service, feedback_service, sample_history, sample_scenario_data):
        """通常ロールでプロンプトが文字列で返されることをテスト"""
        mock_service = MagicMock()
        mock_service.get_user_role.return_value = "部下"
        mock_get_service.return_value = mock_service

        result = feedback_service.build_scenario_feedback_prompt(
            sample_history, sample_scenario_data, is_reverse_role=False
        )

        assert isinstance(result, str)
        assert len(result) > 0

    @patch("services.feedback_service.get_scenario_service")
    def test_returns_string_reverse_role(
        self, mock_get_service, feedback_service, sample_history, sample_scenario_data
    ):
        """リバースロールでプロンプトが文字列で返されることをテスト"""
        mock_service = MagicMock()
        mock_service.get_user_role.return_value = "上司"
        mock_get_service.return_value = mock_service

        result = feedback_service.build_scenario_feedback_prompt(
            sample_history, sample_scenario_data, is_reverse_role=True
        )

        assert isinstance(result, str)
        assert len(result) > 0

    @patch("services.feedback_service.get_scenario_service")
    def test_contains_scenario_title(self, mock_get_service, feedback_service, sample_history, sample_scenario_data):
        """シナリオタイトルが含まれることをテスト"""
        mock_service = MagicMock()
        mock_service.get_user_role.return_value = "部下"
        mock_get_service.return_value = mock_service

        result = feedback_service.build_scenario_feedback_prompt(
            sample_history, sample_scenario_data, is_reverse_role=False
        )

        assert "進捗報告シナリオ" in result

    @patch("services.feedback_service.get_scenario_service")
    def test_reverse_role_contains_harassment_prevention(
        self, mock_get_service, feedback_service, sample_history, sample_scenario_data
    ):
        """リバースロールでパワハラ防止評価が含まれることをテスト"""
        mock_service = MagicMock()
        mock_service.get_user_role.return_value = "上司"
        mock_get_service.return_value = mock_service

        result = feedback_service.build_scenario_feedback_prompt(
            sample_history, sample_scenario_data, is_reverse_role=True
        )

        assert "パワハラ防止" in result or "上司役" in result


class TestTryMultipleModelsForPrompt:
    """try_multiple_models_for_promptメソッドのテスト"""

    @pytest.fixture
    def feedback_service(self):
        return FeedbackService()

    @patch("services.feedback_service.get_cached_config")
    @patch("utils.gemini_models.list_gemini_model_ids")
    @patch("app.create_model_and_get_response")
    def test_returns_tuple(self, mock_create, mock_list_models, mock_config, feedback_service):
        """タプルが返されることをテスト"""
        mock_config.return_value.GOOGLE_API_KEY = "test-key"
        mock_list_models.return_value = ["gemini/gemini-2.5-flash"]
        mock_create.return_value = "フィードバック内容"

        result = feedback_service.try_multiple_models_for_prompt("テストプロンプト")

        assert isinstance(result, tuple)
        assert len(result) == 3

    @patch("services.feedback_service.get_cached_config")
    @patch("utils.gemini_models.list_gemini_model_ids")
    @patch("app.create_model_and_get_response")
    def test_returns_content_on_success(
        self, mock_create, mock_list_models, mock_config, feedback_service
    ):
        """成功時にコンテンツが返されることをテスト"""
        mock_config.return_value.GOOGLE_API_KEY = "test-key"
        mock_list_models.return_value = ["gemini/gemini-2.5-flash"]
        mock_create.return_value = "フィードバック内容"

        content, used_model, error = feedback_service.try_multiple_models_for_prompt("テストプロンプト")

        assert content == "フィードバック内容"
        assert error is None

    @patch("services.feedback_service.get_cached_config")
    @patch("utils.gemini_models.list_gemini_model_ids")
    def test_returns_error_when_no_models(self, mock_list_models, mock_config, feedback_service):
        """モデルがない場合にエラーが返されることをテスト"""
        mock_config.return_value.GOOGLE_API_KEY = "test-key"
        mock_list_models.return_value = []

        content, used_model, error = feedback_service.try_multiple_models_for_prompt("テストプロンプト")

        assert content == ""
        assert error is not None

    @patch("services.feedback_service.get_cached_config")
    @patch("utils.gemini_models.list_gemini_model_ids")
    @patch("app.create_model_and_get_response")
    def test_handles_rate_limit_error(
        self, mock_create, mock_list_models, mock_config, feedback_service
    ):
        """レート制限エラーのハンドリングテスト"""
        from google.api_core.exceptions import ResourceExhausted

        mock_config.return_value.GOOGLE_API_KEY = "test-key"
        mock_list_models.return_value = ["gemini/gemini-2.5-flash"]
        mock_create.side_effect = ResourceExhausted("Rate limit exceeded")

        content, used_model, error = feedback_service.try_multiple_models_for_prompt("テストプロンプト")

        assert content == ""
        assert error == "RATE_LIMIT_EXCEEDED"


class TestUpdateFeedbackWithStrengthAnalysis:
    """update_feedback_with_strength_analysisメソッドのテスト"""

    @pytest.fixture
    def feedback_service(self):
        return FeedbackService()

    @pytest.fixture
    def sample_feedback_response(self):
        return {"feedback": "良いコミュニケーションでした", "score": 85}

    def test_returns_dict(self, feedback_service, sample_feedback_response):
        """辞書が返されることをテスト"""
        result = feedback_service.update_feedback_with_strength_analysis(sample_feedback_response, session_type="chat")

        # 結果が辞書であることを確認（エラーが発生してもオリジナルが返される）
        assert isinstance(result, dict)

    def test_returns_original_on_error(self, feedback_service, sample_feedback_response):
        """エラー時にオリジナルが返されることをテスト"""
        # 強み分析のインポートが失敗しても元のレスポンスが返される
        result = feedback_service.update_feedback_with_strength_analysis(sample_feedback_response, session_type="chat")

        # オリジナルのレスポンスが返される（またはfeedbackキーを含む）
        assert "feedback" in result


class TestGetFeedbackService:
    """get_feedback_service関数のテスト"""

    def test_returns_feedback_service_instance(self):
        """FeedbackServiceインスタンスが返されることをテスト"""
        import services.feedback_service as module

        module._feedback_service = None

        service = get_feedback_service()

        assert isinstance(service, FeedbackService)

    def test_singleton_pattern(self):
        """シングルトンパターンのテスト"""
        import services.feedback_service as module

        module._feedback_service = None

        service1 = get_feedback_service()
        service2 = get_feedback_service()

        assert service1 is service2
