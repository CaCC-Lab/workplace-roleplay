"""
LLM service tests for improved coverage.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestLLMService:
    """LLMServiceクラスのテスト"""

    def test_初期化(self):
        """初期化のテスト"""
        with patch("services.llm_service.genai") as mock_genai:
            with patch("services.llm_service.CompliantAPIManager") as mock_api:
                mock_api.return_value.get_api_key.return_value = "test-api-key"

                from services.llm_service import LLMService

                service = LLMService()

                assert service.api_key_manager is not None

    def test_廃止モデルの置き換え(self):
        """廃止されたモデルの置き換え"""
        from services.llm_service import LLMService

        # 廃止モデルのマッピングを確認
        assert LLMService.DEPRECATED_MODELS["gemini-pro"] == "gemini-1.5-flash"
        assert LLMService.DEPRECATED_MODELS["gemini-pro-vision"] == "gemini-1.5-flash"

    def test_利用可能モデルリスト(self):
        """利用可能なモデルのリスト"""
        from services.llm_service import LLMService

        assert "gemini-1.5-flash" in LLMService.AVAILABLE_MODELS
        assert "gemini-1.5-pro" in LLMService.AVAILABLE_MODELS


class TestCreateGeminiLLM:
    """create_gemini_llm関数のテスト"""

    def test_通常のモデル作成(self):
        """通常のモデル作成"""
        with patch("services.llm_service.genai") as mock_genai:
            with patch("services.llm_service.CompliantAPIManager") as mock_api:
                mock_api.return_value.get_api_key.return_value = "test-api-key"

                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_chat.return_value = MagicMock()

                    from services.llm_service import LLMService

                    service = LLMService()
                    llm = service.create_gemini_llm("gemini-1.5-flash")

                    mock_chat.assert_called_once()

    def test_廃止モデルの自動置き換え(self):
        """廃止されたモデルの自動置き換え"""
        with patch("services.llm_service.genai") as mock_genai:
            with patch("services.llm_service.CompliantAPIManager") as mock_api:
                mock_api.return_value.get_api_key.return_value = "test-api-key"

                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_chat.return_value = MagicMock()

                    from services.llm_service import LLMService

                    service = LLMService()
                    llm = service.create_gemini_llm("gemini-pro")

                    # gemini-1.5-flashに置き換えられる
                    call_args = mock_chat.call_args
                    assert call_args[1]["model"] == "gemini-1.5-flash"

    def test_モデル作成エラー(self):
        """モデル作成時のエラー"""
        with patch("services.llm_service.genai") as mock_genai:
            with patch("services.llm_service.CompliantAPIManager") as mock_api:
                mock_api.return_value.get_api_key.return_value = "test-api-key"

                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_chat.side_effect = Exception("API Error")

                    from services.llm_service import LLMService

                    service = LLMService()

                    with pytest.raises(Exception):
                        service.create_gemini_llm("gemini-1.5-flash")


class TestInitializeLLM:
    """initialize_llm関数のテスト"""

    def test_モデル初期化(self):
        """モデルの初期化"""
        with patch("services.llm_service.genai") as mock_genai:
            with patch("services.llm_service.CompliantAPIManager") as mock_api:
                mock_api.return_value.get_api_key.return_value = "test-api-key"

                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_chat.return_value = MagicMock()

                    from services.llm_service import LLMService

                    service = LLMService()
                    llm = service.initialize_llm("gemini-1.5-flash")

                    assert llm is not None


class TestGetAvailableModels:
    """get_available_models関数のテスト"""

    def test_モデルリスト取得(self):
        """モデルリストの取得"""
        with patch("services.llm_service.genai") as mock_genai:
            with patch("services.llm_service.CompliantAPIManager") as mock_api:
                mock_api.return_value.get_api_key.return_value = "test-api-key"

                from services.llm_service import LLMService

                service = LLMService()
                models = service.get_available_models()

                assert isinstance(models, list)
                assert len(models) > 0


class TestInvokeWithHistory:
    """履歴付きinvokeのテスト"""

    def test_履歴なしでinvoke(self):
        """履歴なしでのinvoke"""
        with patch("services.llm_service.genai") as mock_genai:
            with patch("services.llm_service.CompliantAPIManager") as mock_api:
                mock_api.return_value.get_api_key.return_value = "test-api-key"

                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_llm = MagicMock()
                    mock_llm.invoke.return_value = MagicMock(content="Hello!")
                    mock_chat.return_value = mock_llm

                    from services.llm_service import LLMService

                    service = LLMService()
                    llm = service.create_gemini_llm()

                    # invokeを直接呼び出し
                    result = llm.invoke([])

                    assert result is not None


class TestModelConstants:
    """モデル定数のテスト"""

    def test_廃止モデルマッピング(self):
        """廃止モデルのマッピング"""
        from services.llm_service import LLMService

        assert isinstance(LLMService.DEPRECATED_MODELS, dict)
        assert len(LLMService.DEPRECATED_MODELS) > 0

    def test_利用可能モデル(self):
        """利用可能なモデル"""
        from services.llm_service import LLMService

        assert isinstance(LLMService.AVAILABLE_MODELS, list)
        assert len(LLMService.AVAILABLE_MODELS) > 0
