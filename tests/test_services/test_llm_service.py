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


class TestGetOrCreateModel:
    """get_or_create_model関数のテスト"""

    def test_新規モデル作成(self):
        """新規モデルの作成"""
        with patch("services.llm_service.genai") as mock_genai:
            with patch("services.llm_service.CompliantAPIManager") as mock_api:
                mock_api.return_value.get_api_key.return_value = "test-api-key"

                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_chat.return_value = MagicMock()

                    from services.llm_service import LLMService

                    service = LLMService()
                    llm = service.get_or_create_model("gemini-1.5-flash")

                    assert llm is not None
                    # キャッシュされていることを確認
                    assert "gemini-1.5-flash" in service.models

    def test_キャッシュ済みモデル取得(self):
        """キャッシュ済みモデルの取得"""
        with patch("services.llm_service.genai") as mock_genai:
            with patch("services.llm_service.CompliantAPIManager") as mock_api:
                mock_api.return_value.get_api_key.return_value = "test-api-key"

                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_chat.return_value = MagicMock()

                    from services.llm_service import LLMService

                    service = LLMService()
                    # 1回目の呼び出し
                    llm1 = service.get_or_create_model("gemini-1.5-flash")
                    # 2回目の呼び出し（キャッシュから）
                    llm2 = service.get_or_create_model("gemini-1.5-flash")

                    # 同じインスタンス
                    assert llm1 is llm2


class TestInitializeLLMExtended:
    """initialize_llm関数の拡張テスト"""

    def test_geminiプレフィックス削除(self):
        """gemini/プレフィックスが削除される"""
        with patch("services.llm_service.genai") as mock_genai:
            with patch("services.llm_service.CompliantAPIManager") as mock_api:
                mock_api.return_value.get_api_key.return_value = "test-api-key"

                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_chat.return_value = MagicMock()

                    from services.llm_service import LLMService

                    service = LLMService()
                    llm = service.initialize_llm("gemini/gemini-1.5-flash")

                    # プレフィックスが削除されてモデルが作成される
                    call_args = mock_chat.call_args
                    assert call_args[1]["model"] == "gemini-1.5-flash"

    def test_初期化エラー(self):
        """初期化時のエラー"""
        with patch("services.llm_service.genai") as mock_genai:
            with patch("services.llm_service.CompliantAPIManager") as mock_api:
                mock_api.return_value.get_api_key.return_value = "test-api-key"

                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_chat.side_effect = Exception("Initialization failed")

                    from services.llm_service import LLMService

                    service = LLMService()

                    with pytest.raises(Exception):
                        service.initialize_llm("gemini-1.5-flash")


class TestBuildMessages:
    """_build_messages関数のテスト"""

    def test_システムプロンプト付きメッセージ構築(self):
        """システムプロンプト付きのメッセージ構築"""
        with patch("services.llm_service.genai") as mock_genai:
            with patch("services.llm_service.CompliantAPIManager") as mock_api:
                mock_api.return_value.get_api_key.return_value = "test-api-key"

                from services.llm_service import LLMService

                service = LLMService()
                history = [{"human": "こんにちは", "ai": "こんにちは！"}]
                messages = service._build_messages(history, "質問があります", system_prompt="あなたはアシスタントです")

                # システムメッセージ + 履歴 + 現在のメッセージ
                assert len(messages) == 4

    def test_システムプロンプトなしメッセージ構築(self):
        """システムプロンプトなしのメッセージ構築"""
        with patch("services.llm_service.genai") as mock_genai:
            with patch("services.llm_service.CompliantAPIManager") as mock_api:
                mock_api.return_value.get_api_key.return_value = "test-api-key"

                from services.llm_service import LLMService

                service = LLMService()
                history = []
                messages = service._build_messages(history, "質問があります")

                # 現在のメッセージのみ
                assert len(messages) == 1


class TestInvokeSync:
    """invoke_sync関数のテスト"""

    def test_同期呼び出し(self):
        """同期的なLLM呼び出し"""
        with patch("services.llm_service.genai") as mock_genai:
            with patch("services.llm_service.CompliantAPIManager") as mock_api:
                mock_api.return_value.get_api_key.return_value = "test-api-key"

                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_llm = MagicMock()
                    mock_llm.invoke.return_value = MagicMock(content="レスポンス")
                    mock_chat.return_value = mock_llm

                    from services.llm_service import LLMService

                    service = LLMService()
                    result = service.invoke_sync("テストプロンプト")

                    assert result == "レスポンス"

    def test_同期呼び出し_抽出なし(self):
        """同期的なLLM呼び出し（抽出なし）"""
        with patch("services.llm_service.genai") as mock_genai:
            with patch("services.llm_service.CompliantAPIManager") as mock_api:
                mock_api.return_value.get_api_key.return_value = "test-api-key"

                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_response = MagicMock(content="レスポンス")
                    mock_llm = MagicMock()
                    mock_llm.invoke.return_value = mock_response
                    mock_chat.return_value = mock_llm

                    from services.llm_service import LLMService

                    service = LLMService()
                    result = service.invoke_sync("テストプロンプト", extract_content=False)

                    assert result == mock_response

    def test_同期呼び出し_エラー(self):
        """同期的なLLM呼び出しエラー"""
        with patch("services.llm_service.genai") as mock_genai:
            with patch("services.llm_service.CompliantAPIManager") as mock_api:
                mock_api.return_value.get_api_key.return_value = "test-api-key"

                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_llm = MagicMock()
                    mock_llm.invoke.side_effect = Exception("API Error")
                    mock_chat.return_value = mock_llm

                    from services.llm_service import LLMService

                    service = LLMService()

                    with pytest.raises(Exception):
                        service.invoke_sync("テストプロンプト")


class TestCleanup:
    """cleanup関数のテスト"""

    def test_クリーンアップ(self):
        """リソースのクリーンアップ"""
        with patch("services.llm_service.genai") as mock_genai:
            with patch("services.llm_service.CompliantAPIManager") as mock_api:
                mock_api.return_value.get_api_key.return_value = "test-api-key"

                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:
                    mock_chat.return_value = MagicMock()

                    from services.llm_service import LLMService

                    service = LLMService()
                    # モデルを作成
                    service.get_or_create_model("gemini-1.5-flash")
                    assert len(service.models) > 0

                    # クリーンアップ
                    service.cleanup()
                    assert len(service.models) == 0


class TestStreamChatResponse:
    """stream_chat_response関数のテスト"""

    @pytest.mark.asyncio
    async def test_ストリーミングレスポンス(self):
        """ストリーミングレスポンスの生成"""
        with patch("services.llm_service.genai") as mock_genai:
            with patch("services.llm_service.CompliantAPIManager") as mock_api:
                mock_api.return_value.get_api_key.return_value = "test-api-key"

                with patch("services.llm_service.ChatGoogleGenerativeAI") as mock_chat:

                    async def mock_stream(*args, **kwargs):
                        for chunk in ["Hello", " World"]:
                            yield MagicMock(content=chunk)

                    mock_llm = MagicMock()
                    mock_llm.astream = mock_stream
                    mock_chat.return_value = mock_llm

                    from services.llm_service import LLMService

                    service = LLMService()

                    chunks = []
                    async for chunk in service.stream_chat_response("テスト", [], "gemini-1.5-flash"):
                        chunks.append(chunk)

                    assert len(chunks) > 0


class TestInitializeGenai:
    """_initialize_genai関数のテスト"""

    def test_初期化成功(self):
        """Gemini APIの初期化成功"""
        with patch("services.llm_service.genai") as mock_genai:
            with patch("services.llm_service.CompliantAPIManager") as mock_api:
                mock_api.return_value.get_api_key.return_value = "test-api-key"

                from services.llm_service import LLMService

                service = LLMService()

                # configureが呼ばれることを確認
                mock_genai.configure.assert_called_once()

    def test_初期化失敗(self):
        """Gemini APIの初期化失敗"""
        with patch("services.llm_service.genai") as mock_genai:
            mock_genai.configure.side_effect = Exception("API Error")

            with patch("services.llm_service.CompliantAPIManager") as mock_api:
                mock_api.return_value.get_api_key.return_value = "test-api-key"

                from services.llm_service import LLMService

                # 例外が発生しても初期化は完了する（警告のみ）
                service = LLMService()
                assert service is not None
