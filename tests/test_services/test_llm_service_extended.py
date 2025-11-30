"""
Extended LLM service tests for improved coverage.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestLLMService:
    """LLMServiceクラスのテスト"""

    def test_初期化(self):
        """LLMServiceの初期化"""
        with patch("services.llm_service.CompliantAPIManager") as mock_manager:
            mock_manager.return_value.get_api_key.return_value = "test-key"

            with patch("services.llm_service.genai.configure"):
                from services.llm_service import LLMService

                service = LLMService()

                assert service.models == {}

    def test_初期化_genai_エラー(self):
        """Gemini API初期化エラー時"""
        with patch("services.llm_service.CompliantAPIManager") as mock_manager:
            mock_manager.return_value.get_api_key.side_effect = Exception("API Error")

            from services.llm_service import LLMService

            # エラーでも初期化は完了
            service = LLMService()

    def test_create_gemini_llm_通常モデル(self):
        """通常モデルの作成"""
        with patch("services.llm_service.CompliantAPIManager") as mock_manager:
            mock_manager.return_value.get_api_key.return_value = "test-key"

            with patch("services.llm_service.genai.configure"):
                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_chat.return_value = MagicMock()

                    from services.llm_service import LLMService

                    service = LLMService()
                    llm = service.create_gemini_llm("gemini-1.5-flash")

                    mock_chat.assert_called_once()

    def test_create_gemini_llm_廃止モデル(self):
        """廃止されたモデルの代替"""
        with patch("services.llm_service.CompliantAPIManager") as mock_manager:
            mock_manager.return_value.get_api_key.return_value = "test-key"

            with patch("services.llm_service.genai.configure"):
                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_chat.return_value = MagicMock()

                    from services.llm_service import LLMService

                    service = LLMService()
                    llm = service.create_gemini_llm("gemini-pro-vision")

                    # 代替モデルで呼ばれていることを確認
                    call_args = mock_chat.call_args
                    assert "gemini-1.5-flash" in str(call_args)

    def test_create_gemini_llm_エラー(self):
        """LLM作成エラー"""
        with patch("services.llm_service.CompliantAPIManager") as mock_manager:
            mock_manager.return_value.get_api_key.return_value = "test-key"

            with patch("services.llm_service.genai.configure"):
                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_chat.side_effect = Exception("Model Error")

                    from services.llm_service import LLMService

                    service = LLMService()

                    with pytest.raises(Exception):
                        service.create_gemini_llm("gemini-1.5-flash")

    def test_initialize_llm_プレフィックス削除(self):
        """gemini/プレフィックスの削除"""
        with patch("services.llm_service.CompliantAPIManager") as mock_manager:
            mock_manager.return_value.get_api_key.return_value = "test-key"

            with patch("services.llm_service.genai.configure"):
                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_chat.return_value = MagicMock()

                    from services.llm_service import LLMService

                    service = LLMService()
                    llm = service.initialize_llm("gemini/gemini-1.5-flash")

                    mock_chat.assert_called_once()

    def test_initialize_llm_エラー(self):
        """initialize_llmエラー"""
        with patch("services.llm_service.CompliantAPIManager") as mock_manager:
            mock_manager.return_value.get_api_key.return_value = "test-key"

            with patch("services.llm_service.genai.configure"):
                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_chat.side_effect = Exception("Init Error")

                    from services.llm_service import LLMService

                    service = LLMService()

                    with pytest.raises(Exception):
                        service.initialize_llm("gemini-1.5-flash")

    def test_get_or_create_model_キャッシュヒット(self):
        """モデルキャッシュのヒット"""
        with patch("services.llm_service.CompliantAPIManager") as mock_manager:
            mock_manager.return_value.get_api_key.return_value = "test-key"

            with patch("services.llm_service.genai.configure"):
                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_model = MagicMock()
                    mock_chat.return_value = mock_model

                    from services.llm_service import LLMService

                    service = LLMService()

                    # 1回目の呼び出し
                    model1 = service.get_or_create_model("gemini-1.5-flash")
                    # 2回目の呼び出し（キャッシュから）
                    model2 = service.get_or_create_model("gemini-1.5-flash")

                    assert model1 is model2
                    # ChatGoogleGenerativeAIは1回だけ呼ばれる
                    assert mock_chat.call_count == 1

    def test_build_messages_システムプロンプトあり(self):
        """システムプロンプト付きのメッセージ構築"""
        with patch("services.llm_service.CompliantAPIManager") as mock_manager:
            mock_manager.return_value.get_api_key.return_value = "test-key"

            with patch("services.llm_service.genai.configure"):
                from services.llm_service import LLMService

                service = LLMService()
                history = [
                    {"human": "こんにちは", "ai": "こんにちは！"},
                ]

                messages = service._build_messages(
                    history, "今日の天気は？", "あなたはアシスタントです"
                )

                assert len(messages) == 4  # System + Human + AI + Human

    def test_build_messages_システムプロンプトなし(self):
        """システムプロンプトなしのメッセージ構築"""
        with patch("services.llm_service.CompliantAPIManager") as mock_manager:
            mock_manager.return_value.get_api_key.return_value = "test-key"

            with patch("services.llm_service.genai.configure"):
                from services.llm_service import LLMService

                service = LLMService()
                history = [
                    {"human": "こんにちは", "ai": "こんにちは！"},
                ]

                messages = service._build_messages(history, "今日の天気は？")

                assert len(messages) == 3  # Human + AI + Human

    def test_invoke_sync_コンテンツ抽出(self):
        """同期呼び出しとコンテンツ抽出"""
        with patch("services.llm_service.CompliantAPIManager") as mock_manager:
            mock_manager.return_value.get_api_key.return_value = "test-key"

            with patch("services.llm_service.genai.configure"):
                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_model = MagicMock()
                    mock_response = MagicMock()
                    mock_response.content = "応答内容"
                    mock_model.invoke.return_value = mock_response
                    mock_chat.return_value = mock_model

                    from services.llm_service import LLMService

                    service = LLMService()
                    result = service.invoke_sync("プロンプト")

                    assert result == "応答内容"

    def test_invoke_sync_コンテンツ抽出なし(self):
        """同期呼び出し（コンテンツ抽出なし）"""
        with patch("services.llm_service.CompliantAPIManager") as mock_manager:
            mock_manager.return_value.get_api_key.return_value = "test-key"

            with patch("services.llm_service.genai.configure"):
                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_model = MagicMock()
                    mock_response = MagicMock()
                    mock_model.invoke.return_value = mock_response
                    mock_chat.return_value = mock_model

                    from services.llm_service import LLMService

                    service = LLMService()
                    result = service.invoke_sync("プロンプト", extract_content=False)

                    assert result == mock_response

    def test_invoke_sync_エラー(self):
        """同期呼び出しエラー"""
        with patch("services.llm_service.CompliantAPIManager") as mock_manager:
            mock_manager.return_value.get_api_key.return_value = "test-key"

            with patch("services.llm_service.genai.configure"):
                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_model = MagicMock()
                    mock_model.invoke.side_effect = Exception("Invoke Error")
                    mock_chat.return_value = mock_model

                    from services.llm_service import LLMService

                    service = LLMService()

                    with pytest.raises(Exception):
                        service.invoke_sync("プロンプト")

    def test_get_available_models(self):
        """利用可能モデルのリスト取得"""
        with patch("services.llm_service.CompliantAPIManager") as mock_manager:
            mock_manager.return_value.get_api_key.return_value = "test-key"

            with patch("services.llm_service.genai.configure"):
                from services.llm_service import LLMService

                service = LLMService()
                models = service.get_available_models()

                assert "gemini-1.5-flash" in models
                assert "gemini-1.5-pro" in models

    def test_cleanup(self):
        """リソースのクリーンアップ"""
        with patch("services.llm_service.CompliantAPIManager") as mock_manager:
            mock_manager.return_value.get_api_key.return_value = "test-key"

            with patch("services.llm_service.genai.configure"):
                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_chat.return_value = MagicMock()

                    from services.llm_service import LLMService

                    service = LLMService()
                    service.get_or_create_model("gemini-1.5-flash")

                    assert len(service.models) == 1

                    service.cleanup()

                    assert len(service.models) == 0


class TestDeprecatedModels:
    """廃止モデルのマッピングテスト"""

    def test_全ての廃止モデルがマッピングされている(self):
        """全ての廃止モデルがマッピングされていることを確認"""
        from services.llm_service import LLMService

        deprecated = LLMService.DEPRECATED_MODELS

        assert "gemini-pro-vision" in deprecated
        assert "gemini-1.0-pro-vision" in deprecated
        assert "gemini-pro" in deprecated

        # 代替モデルが有効なモデルであることを確認
        for deprecated_model, replacement in deprecated.items():
            assert "gemini-1.5" in replacement or "gemini-2" in replacement
