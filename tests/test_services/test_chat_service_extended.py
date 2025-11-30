"""
Extended chat service tests for improved coverage.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock


class TestChatService:
    """ChatServiceクラスのテスト"""

    def test_初期化_デフォルト(self):
        """デフォルトパラメータでの初期化"""
        with patch("services.chat_service.LLMService") as mock_llm:
            with patch("services.chat_service.SessionService") as mock_session:
                mock_llm.return_value = MagicMock()
                mock_session.return_value = MagicMock()

                from services.chat_service import ChatService

                service = ChatService()

                assert service.llm_service is not None
                assert service.session_service is not None

    def test_初期化_カスタムサービス(self):
        """カスタムサービスでの初期化"""
        mock_llm = MagicMock()
        mock_session = MagicMock()

        from services.chat_service import ChatService

        service = ChatService(llm_service=mock_llm, session_service=mock_session)

        assert service.llm_service == mock_llm
        assert service.session_service == mock_session


class TestProcessChatMessage:
    """process_chat_message メソッドのテスト"""

    @pytest.mark.asyncio
    async def test_空メッセージ(self):
        """空のメッセージ"""
        mock_llm = MagicMock()
        mock_session = MagicMock()

        from services.chat_service import ChatService

        service = ChatService(llm_service=mock_llm, session_service=mock_session)

        result = []
        async for chunk in service.process_chat_message(""):
            result.append(chunk)

        assert "無効" in "".join(result)

    @pytest.mark.asyncio
    async def test_長すぎるメッセージ(self):
        """長すぎるメッセージ"""
        mock_llm = MagicMock()
        mock_session = MagicMock()

        from services.chat_service import ChatService
        from utils.constants import MAX_MESSAGE_LENGTH

        service = ChatService(llm_service=mock_llm, session_service=mock_session)

        long_message = "a" * (MAX_MESSAGE_LENGTH + 1)

        result = []
        async for chunk in service.process_chat_message(long_message):
            result.append(chunk)

        assert "無効" in "".join(result)

    @pytest.mark.asyncio
    async def test_正常なメッセージ処理(self):
        """正常なメッセージ処理"""
        mock_llm = MagicMock()
        mock_session = MagicMock()
        mock_session.get_current_model.return_value = "gemini-1.5-flash"
        mock_session.get_chat_history.return_value = []

        # AsyncGeneratorをモック
        async def mock_stream(*args, **kwargs):
            yield "こんにちは"
            yield "！"

        mock_llm.stream_chat_response = mock_stream

        from services.chat_service import ChatService

        service = ChatService(llm_service=mock_llm, session_service=mock_session)

        result = []
        async for chunk in service.process_chat_message("テスト", model_name="gemini"):
            result.append(chunk)

        assert "".join(result) == "こんにちは！"


class TestProcessScenarioMessage:
    """process_scenario_message メソッドのテスト"""

    @pytest.mark.asyncio
    async def test_シナリオが見つからない(self):
        """シナリオが見つからない場合"""
        mock_llm = MagicMock()
        mock_session = MagicMock()

        with patch("services.chat_service.get_scenario_by_id") as mock_get:
            mock_get.return_value = None

            from services.chat_service import ChatService

            service = ChatService(llm_service=mock_llm, session_service=mock_session)

            result = []
            async for chunk in service.process_scenario_message(
                "nonexistent", "テスト"
            ):
                result.append(chunk)

            assert "見つかりません" in "".join(result)

    @pytest.mark.asyncio
    async def test_空メッセージ(self):
        """空のメッセージ"""
        mock_llm = MagicMock()
        mock_session = MagicMock()

        from services.chat_service import ChatService

        service = ChatService(llm_service=mock_llm, session_service=mock_session)

        result = []
        async for chunk in service.process_scenario_message("scenario1", ""):
            result.append(chunk)

        assert "無効" in "".join(result)

    @pytest.mark.asyncio
    async def test_正常なシナリオメッセージ処理(self):
        """正常なシナリオメッセージ処理"""
        mock_llm = MagicMock()
        mock_session = MagicMock()
        mock_session.get_current_model.return_value = "gemini-1.5-flash"
        mock_session.get_scenario_history.return_value = []

        # モックシナリオ
        mock_scenario = {
            "id": "test",
            "character": {
                "name": "佐藤部長",
                "role": "上司",
                "personality": "厳しいが公正",
            },
            "situation": "会議後の報告",
            "instructions": "真剣に対応してください",
        }

        async def mock_stream(*args, **kwargs):
            yield "わかりました"

        mock_llm.stream_chat_response = mock_stream

        with patch("services.chat_service.get_scenario_by_id") as mock_get:
            mock_get.return_value = mock_scenario

            from services.chat_service import ChatService

            service = ChatService(llm_service=mock_llm, session_service=mock_session)

            result = []
            async for chunk in service.process_scenario_message(
                "test", "報告します"
            ):
                result.append(chunk)

            assert "わかりました" in "".join(result)


class TestWatchConversation:
    """観戦モードのテスト"""

    @pytest.mark.asyncio
    async def test_観戦開始(self):
        """観戦モード開始"""
        mock_llm = MagicMock()
        mock_session = MagicMock()
        mock_session.get_watch_models.return_value = {
            "model1": "gemini-1.5-flash",
            "model2": "gemini-1.5-pro",
        }

        async def mock_stream(*args, **kwargs):
            yield "こんにちは、今日の天気は良いですね！"

        mock_llm.stream_chat_response = mock_stream

        from services.chat_service import ChatService

        service = ChatService(llm_service=mock_llm, session_service=mock_session)

        result = []
        async for chunk in service.start_watch_conversation("天気"):
            result.append(chunk)

        import json

        data = json.loads("".join(result))
        assert data["speaker"] == "model1"

    @pytest.mark.asyncio
    async def test_観戦継続_履歴なし(self):
        """履歴なしで観戦継続"""
        mock_llm = MagicMock()
        mock_session = MagicMock()
        mock_session.get_watch_models.return_value = {
            "model1": "gemini-1.5-flash",
            "model2": "gemini-1.5-pro",
        }
        mock_session.get_watch_topic.return_value = None
        mock_session.get_watch_history.return_value = []

        from services.chat_service import ChatService

        service = ChatService(llm_service=mock_llm, session_service=mock_session)

        result = []
        async for chunk in service.continue_watch_conversation():
            result.append(chunk)

        import json

        data = json.loads("".join(result))
        assert "error" in data


class TestGenerateChatFeedback:
    """generate_chat_feedback メソッドのテスト"""

    @pytest.mark.asyncio
    async def test_履歴なしでフィードバック(self):
        """履歴なしでフィードバック生成"""
        mock_llm = MagicMock()
        mock_session = MagicMock()
        mock_session.get_chat_history.return_value = []

        from services.chat_service import ChatService

        service = ChatService(llm_service=mock_llm, session_service=mock_session)

        result = await service.generate_chat_feedback()

        # 履歴なしのメッセージが返される
        assert result is not None


class TestGenerateScenarioFeedback:
    """generate_scenario_feedback メソッドのテスト"""

    @pytest.mark.asyncio
    async def test_シナリオなしでフィードバック(self):
        """シナリオが見つからない場合"""
        mock_llm = MagicMock()
        mock_session = MagicMock()
        mock_session.get_scenario_history.return_value = []

        with patch("services.chat_service.get_scenario_by_id") as mock_get:
            mock_get.return_value = None

            from services.chat_service import ChatService

            service = ChatService(llm_service=mock_llm, session_service=mock_session)

            result = await service.generate_scenario_feedback("nonexistent")

            assert result is not None

    @pytest.mark.asyncio
    async def test_履歴なしでフィードバック(self):
        """履歴なしでフィードバック"""
        mock_llm = MagicMock()
        mock_session = MagicMock()
        mock_session.get_scenario_history.return_value = []

        with patch("services.chat_service.get_scenario_by_id") as mock_get:
            mock_get.return_value = {"title": "テストシナリオ"}

            from services.chat_service import ChatService

            service = ChatService(llm_service=mock_llm, session_service=mock_session)

            result = await service.generate_scenario_feedback("scenario1")

            # 履歴なしのメッセージが返される
            assert result is not None
