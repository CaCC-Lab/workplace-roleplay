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


class TestGetRecommendedVoice:
    """get_recommended_voice メソッドのテスト"""

    def test_感情ありで音声取得(self):
        """感情指定ありで音声を取得"""
        mock_llm = MagicMock()
        mock_session = MagicMock()
        mock_session.get_current_voice.return_value = "default_voice"

        from services.chat_service import ChatService
        from utils.constants import EMOTION_VOICE_MAPPING

        service = ChatService(llm_service=mock_llm, session_service=mock_session)

        # EMOTION_VOICE_MAPPINGに存在する感情をテスト
        if EMOTION_VOICE_MAPPING:
            emotion = list(EMOTION_VOICE_MAPPING.keys())[0]
            expected_voice = EMOTION_VOICE_MAPPING[emotion]

            result = service.get_recommended_voice(emotion)

            assert result == expected_voice

    def test_感情なしで音声取得(self):
        """感情指定なしで音声を取得"""
        mock_llm = MagicMock()
        mock_session = MagicMock()
        mock_session.get_current_voice.return_value = "default_voice"

        from services.chat_service import ChatService

        service = ChatService(llm_service=mock_llm, session_service=mock_session)

        result = service.get_recommended_voice(None)

        assert result == "default_voice"

    def test_不明な感情で音声取得(self):
        """不明な感情で音声を取得"""
        mock_llm = MagicMock()
        mock_session = MagicMock()
        mock_session.get_current_voice.return_value = "default_voice"

        from services.chat_service import ChatService

        service = ChatService(llm_service=mock_llm, session_service=mock_session)

        result = service.get_recommended_voice("unknown_emotion")

        assert result == "default_voice"


class TestValidateMessage:
    """validate_message メソッドのテスト"""

    def test_空メッセージ(self):
        """空のメッセージ"""
        mock_llm = MagicMock()
        mock_session = MagicMock()

        from services.chat_service import ChatService

        service = ChatService(llm_service=mock_llm, session_service=mock_session)

        is_valid, error = service.validate_message("")

        assert is_valid is False
        assert error is not None

    def test_長すぎるメッセージ(self):
        """長すぎるメッセージ"""
        mock_llm = MagicMock()
        mock_session = MagicMock()

        from services.chat_service import ChatService
        from utils.constants import MAX_MESSAGE_LENGTH

        service = ChatService(llm_service=mock_llm, session_service=mock_session)

        long_message = "a" * (MAX_MESSAGE_LENGTH + 1)
        is_valid, error = service.validate_message(long_message)

        assert is_valid is False
        assert "文字以内" in error

    def test_不適切な表現を含むメッセージ(self):
        """不適切な表現を含むメッセージ"""
        mock_llm = MagicMock()
        mock_session = MagicMock()

        from services.chat_service import ChatService

        service = ChatService(llm_service=mock_llm, session_service=mock_session)

        # 不適切な単語を含むメッセージ
        is_valid, error = service.validate_message("ばかなことを言うな")

        assert is_valid is False
        assert "不適切" in error

    def test_正常なメッセージ(self):
        """正常なメッセージ"""
        mock_llm = MagicMock()
        mock_session = MagicMock()

        from services.chat_service import ChatService

        service = ChatService(llm_service=mock_llm, session_service=mock_session)

        is_valid, error = service.validate_message("こんにちは、今日はいい天気ですね")

        assert is_valid is True
        assert error is None


class TestGenerateChatFeedbackExtended:
    """generate_chat_feedback メソッドの拡張テスト"""

    @pytest.mark.asyncio
    async def test_履歴ありでフィードバック生成(self):
        """履歴ありでフィードバック生成"""
        mock_llm = MagicMock()
        mock_llm.invoke_sync.return_value = "良いコミュニケーションでした！"

        mock_session = MagicMock()
        mock_session.get_chat_history.return_value = [
            {"human": "こんにちは", "ai": "こんにちは！"}
        ]
        mock_session.get_current_model.return_value = "gemini-1.5-flash"

        from services.chat_service import ChatService

        service = ChatService(llm_service=mock_llm, session_service=mock_session)

        result = await service.generate_chat_feedback()

        assert result == "良いコミュニケーションでした！"

    @pytest.mark.asyncio
    async def test_フィードバック文字数制限(self):
        """フィードバックの文字数制限"""
        mock_llm = MagicMock()
        # MAX_FEEDBACK_LENGTH以上の長いフィードバック
        mock_llm.invoke_sync.return_value = "a" * 5000

        mock_session = MagicMock()
        mock_session.get_chat_history.return_value = [
            {"human": "こんにちは", "ai": "こんにちは！"}
        ]
        mock_session.get_current_model.return_value = "gemini-1.5-flash"

        from services.chat_service import ChatService
        from utils.constants import MAX_FEEDBACK_LENGTH

        service = ChatService(llm_service=mock_llm, session_service=mock_session)

        result = await service.generate_chat_feedback()

        # 文字数制限を超えた場合は切り捨て
        assert len(result) <= MAX_FEEDBACK_LENGTH


class TestGenerateScenarioFeedbackExtended:
    """generate_scenario_feedback メソッドの拡張テスト"""

    @pytest.mark.asyncio
    async def test_履歴ありでフィードバック生成(self):
        """履歴ありでフィードバック生成"""
        mock_llm = MagicMock()
        mock_llm.invoke_sync.return_value = "良い対応でした！"

        mock_session = MagicMock()
        mock_session.get_scenario_history.return_value = [
            {"human": "報告します", "ai": "はい、どうぞ"}
        ]
        mock_session.get_current_model.return_value = "gemini-1.5-flash"

        mock_scenario = {
            "title": "報告シナリオ",
            "situation": "上司への報告",
            "your_role": "部下",
            "character": {"name": "佐藤部長"},
            "feedback_points": ["明確さ", "簡潔さ"],
        }

        with patch("services.chat_service.get_scenario_by_id") as mock_get:
            mock_get.return_value = mock_scenario

            from services.chat_service import ChatService

            service = ChatService(llm_service=mock_llm, session_service=mock_session)

            result = await service.generate_scenario_feedback("scenario1")

            assert result == "良い対応でした！"
            # 学習記録が追加されることを確認
            mock_session.add_learning_record.assert_called_once()


class TestContinueWatchConversation:
    """continue_watch_conversation メソッドのテスト"""

    @pytest.mark.asyncio
    async def test_Model2の番(self):
        """Model2の番"""
        mock_llm = MagicMock()
        mock_session = MagicMock()
        mock_session.get_watch_models.return_value = {
            "model1": "gemini-1.5-flash",
            "model2": "gemini-1.5-pro",
        }
        mock_session.get_watch_topic.return_value = "天気"
        mock_session.get_watch_history.return_value = [
            {
                "model1": {"name": "model1", "message": "今日はいい天気ですね"},
                "model2": {"name": "model2", "message": ""},
            }
        ]

        async def mock_stream(*args, **kwargs):
            yield "そうですね、本当に！"

        mock_llm.stream_chat_response = mock_stream

        from services.chat_service import ChatService

        service = ChatService(llm_service=mock_llm, session_service=mock_session)

        result = []
        async for chunk in service.continue_watch_conversation():
            result.append(chunk)

        import json

        data = json.loads("".join(result))
        assert data["speaker"] == "model2"

    @pytest.mark.asyncio
    async def test_Model1の番(self):
        """Model1の番"""
        mock_llm = MagicMock()
        mock_session = MagicMock()
        mock_session.get_watch_models.return_value = {
            "model1": "gemini-1.5-flash",
            "model2": "gemini-1.5-pro",
        }
        mock_session.get_watch_topic.return_value = "天気"
        mock_session.get_watch_history.return_value = [
            {
                "model1": {"name": "model1", "message": "今日はいい天気ですね"},
                "model2": {"name": "model2", "message": "そうですね！"},
            }
        ]

        async def mock_stream(*args, **kwargs):
            yield "明日も晴れるといいですね"

        mock_llm.stream_chat_response = mock_stream

        from services.chat_service import ChatService

        service = ChatService(llm_service=mock_llm, session_service=mock_session)

        result = []
        async for chunk in service.continue_watch_conversation():
            result.append(chunk)

        import json

        data = json.loads("".join(result))
        assert data["speaker"] == "model1"
