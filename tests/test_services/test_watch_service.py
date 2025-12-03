"""
WatchServiceのユニットテスト
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.watch_service import WatchService, get_watch_service


class TestWatchService:
    """WatchServiceのテストクラス"""

    @pytest.fixture
    def watch_service(self):
        """WatchServiceインスタンス"""
        return WatchService()

    @pytest.fixture
    def mock_llm(self):
        """モックLLM"""
        mock = MagicMock()
        mock.invoke.return_value = MagicMock(content="「こんにちは、花子さん」（にこやかに）")
        return mock


class TestSwitchSpeaker:
    """switch_speakerメソッドのテスト"""

    @pytest.fixture
    def watch_service(self):
        return WatchService()

    def test_switch_from_a_to_b(self, watch_service):
        """Aからbへの切り替えテスト"""
        result = watch_service.switch_speaker("A")
        assert result == "B"

    def test_switch_from_b_to_a(self, watch_service):
        """BからAへの切り替えテスト"""
        result = watch_service.switch_speaker("B")
        assert result == "A"

    def test_switch_multiple_times(self, watch_service):
        """複数回の切り替えテスト"""
        speaker = "A"
        for expected in ["B", "A", "B", "A"]:
            speaker = watch_service.switch_speaker(speaker)
            assert speaker == expected


class TestGetSpeakerDisplayName:
    """get_speaker_display_nameメソッドのテスト"""

    @pytest.fixture
    def watch_service(self):
        return WatchService()

    def test_speaker_a_is_taro(self, watch_service):
        """話者Aが太郎であることをテスト"""
        result = watch_service.get_speaker_display_name("A")
        assert result == "太郎"

    def test_speaker_b_is_hanako(self, watch_service):
        """話者Bが花子であることをテスト"""
        result = watch_service.get_speaker_display_name("B")
        assert result == "花子"

    def test_unknown_speaker(self, watch_service):
        """不明な話者の場合のテスト（デフォルトで花子）"""
        result = watch_service.get_speaker_display_name("C")
        # 実装では"A"以外は全て"花子"を返す
        assert result == "花子"


class TestGenerateInitialMessage:
    """generate_initial_messageメソッドのテスト"""

    @pytest.fixture
    def watch_service(self):
        return WatchService()

    @pytest.fixture
    def mock_llm(self):
        mock = MagicMock()
        mock.invoke.return_value = MagicMock(content="「おはようございます、花子さん」（明るく）")
        return mock

    def test_generate_initial_message_returns_string(self, watch_service, mock_llm):
        """初期メッセージが文字列で返されることをテスト"""
        result = watch_service.generate_initial_message(mock_llm, partner_type="同僚", situation="朝の挨拶", topic="天気")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_initial_message_calls_llm(self, watch_service, mock_llm):
        """LLMが呼び出されることをテスト"""
        watch_service.generate_initial_message(mock_llm, partner_type="上司", situation="会議前", topic="仕事")

        mock_llm.invoke.assert_called_once()

    def test_generate_initial_message_with_various_partner_types(self, watch_service, mock_llm):
        """様々な相手タイプでのテスト"""
        partner_types = ["同僚", "上司", "部下", "先輩", "後輩"]

        for partner_type in partner_types:
            result = watch_service.generate_initial_message(
                mock_llm, partner_type=partner_type, situation="通常業務", topic="仕事の話"
            )
            assert isinstance(result, str)


class TestGenerateNextMessage:
    """generate_next_messageメソッドのテスト"""

    @pytest.fixture
    def watch_service(self):
        return WatchService()

    @pytest.fixture
    def mock_llm(self):
        mock = MagicMock()
        mock.invoke.return_value = MagicMock(content="「そうですね、私もそう思います」（うなずきながら）")
        return mock

    @pytest.fixture
    def sample_history(self):
        """テスト用の会話履歴"""
        return [
            {"speaker": "A", "message": "「おはようございます」（明るく）"},
            {"speaker": "B", "message": "「おはようございます、太郎さん」（笑顔で）"},
            {"speaker": "A", "message": "「今日はいい天気ですね」（窓を見ながら）"},
        ]

    def test_generate_next_message_returns_string(self, watch_service, mock_llm, sample_history):
        """次のメッセージが文字列で返されることをテスト"""
        result = watch_service.generate_next_message(mock_llm, sample_history)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_next_message_calls_llm(self, watch_service, mock_llm, sample_history):
        """LLMが呼び出されることをテスト"""
        watch_service.generate_next_message(mock_llm, sample_history)

        mock_llm.invoke.assert_called_once()

    def test_generate_next_message_removes_speaker_prefix(self, watch_service, sample_history):
        """話者名プレフィックスが削除されることをテスト"""
        mock_llm = MagicMock()
        # 話者名付きの応答をモック
        mock_llm.invoke.return_value = MagicMock(content="花子: 「そうですね」（微笑みながら）")

        result = watch_service.generate_next_message(mock_llm, sample_history)

        # 花子: プレフィックスが削除されていることを確認
        assert not result.startswith("花子:")
        assert not result.startswith("太郎:")

    def test_generate_next_message_with_empty_history(self, watch_service, mock_llm):
        """空の履歴での動作テスト"""
        result = watch_service.generate_next_message(mock_llm, [])

        assert isinstance(result, str)


class TestGetWatchService:
    """get_watch_service関数のテスト"""

    def test_returns_watch_service_instance(self):
        """WatchServiceインスタンスが返されることをテスト"""
        # グローバル変数をリセット
        import services.watch_service as module

        module._watch_service = None

        service = get_watch_service()

        assert isinstance(service, WatchService)

    def test_singleton_pattern(self):
        """シングルトンパターンのテスト"""
        import services.watch_service as module

        module._watch_service = None

        service1 = get_watch_service()
        service2 = get_watch_service()

        assert service1 is service2
