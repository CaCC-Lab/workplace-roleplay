"""
Compliant API manager tests for improved coverage.
"""

import pytest
import time
from unittest.mock import patch, MagicMock
import os


class TestCompliantAPIManager:
    """CompliantAPIManagerクラスのテスト"""

    def test_APIキー読み込み成功(self):
        """環境変数からAPIキーを読み込む"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-api-key"}):
            from compliant_api_manager import CompliantAPIManager

            manager = CompliantAPIManager()
            assert manager.api_key == "test-api-key"

    def test_APIキーなしでエラー(self):
        """APIキーがない場合はエラー"""
        with patch.dict(os.environ, {}, clear=True):
            # 既存の環境変数をクリア
            if "GOOGLE_API_KEY" in os.environ:
                del os.environ["GOOGLE_API_KEY"]

            from compliant_api_manager import CompliantAPIManager

            with pytest.raises(ValueError) as exc_info:
                CompliantAPIManager()

            assert "GOOGLE_API_KEY" in str(exc_info.value)

    def test_リクエスト履歴のクリーンアップ(self):
        """古いリクエスト履歴をクリーンアップ"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            from compliant_api_manager import CompliantAPIManager

            manager = CompliantAPIManager()
            # 2時間前のリクエスト履歴を追加
            old_time = time.time() - 7200
            manager.request_history = [old_time]

            manager._clean_old_requests()

            assert len(manager.request_history) == 0

    def test_リクエスト可能チェック_成功(self):
        """リクエスト可能な場合"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            from compliant_api_manager import CompliantAPIManager

            manager = CompliantAPIManager()

            can_request, wait_seconds = manager._can_make_request()

            assert can_request is True
            assert wait_seconds is None

    def test_リクエスト可能チェック_分単位制限(self):
        """分単位のレート制限"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            from compliant_api_manager import CompliantAPIManager

            manager = CompliantAPIManager()
            # 現在時刻で最大リクエスト数を記録
            current_time = time.time()
            manager.request_history = [current_time] * manager.max_requests_per_minute

            can_request, wait_seconds = manager._can_make_request()

            assert can_request is False
            assert wait_seconds is not None
            assert wait_seconds > 0

    def test_リクエスト可能チェック_時間単位制限(self):
        """時間単位のレート制限"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            from compliant_api_manager import CompliantAPIManager

            manager = CompliantAPIManager()
            # 過去1時間のリクエストで最大数に到達
            current_time = time.time()
            manager.request_history = [current_time - i * 5 for i in range(manager.max_requests_per_hour)]

            can_request, wait_seconds = manager._can_make_request()

            assert can_request is False
            assert wait_seconds is not None

    def test_リクエスト可能チェック_エラー後バックオフ(self):
        """エラー後のバックオフ期間中"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            from compliant_api_manager import CompliantAPIManager

            manager = CompliantAPIManager()
            manager.consecutive_errors = 3
            manager.last_error_time = time.time()

            can_request, wait_seconds = manager._can_make_request()

            assert can_request is False
            assert wait_seconds is not None

    def test_APIキー取得成功(self):
        """APIキーの取得成功"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            from compliant_api_manager import CompliantAPIManager

            manager = CompliantAPIManager()

            api_key = manager.get_api_key()

            assert api_key == "test-key"
            assert len(manager.request_history) == 1

    def test_APIキー取得_レート制限(self):
        """レート制限時のAPIキー取得"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            from compliant_api_manager import CompliantAPIManager, RateLimitException

            manager = CompliantAPIManager()
            # レート制限に達するまでリクエスト
            current_time = time.time()
            manager.request_history = [current_time] * manager.max_requests_per_minute

            with pytest.raises(RateLimitException):
                manager.get_api_key()

    def test_成功記録(self):
        """API呼び出し成功の記録"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            from compliant_api_manager import CompliantAPIManager

            manager = CompliantAPIManager()
            manager.consecutive_errors = 5

            manager.record_success()

            assert manager.consecutive_errors == 0

    def test_エラー記録(self):
        """APIエラーの記録"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            from compliant_api_manager import CompliantAPIManager

            manager = CompliantAPIManager()

            manager.record_error(Exception("Test error"))

            assert manager.consecutive_errors == 1
            assert manager.last_error_time > 0

    def test_レート制限エラー記録(self):
        """レート制限エラーの記録"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            from compliant_api_manager import CompliantAPIManager

            manager = CompliantAPIManager()
            manager.consecutive_errors = 10

            manager.record_error(Exception("429 Rate limit exceeded"))

            # 最大5回に制限される
            assert manager.consecutive_errors <= 5

    def test_成功リクエスト記録(self):
        """成功したリクエストの記録"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            from compliant_api_manager import CompliantAPIManager

            manager = CompliantAPIManager()
            manager.consecutive_errors = 3

            manager.record_successful_request("test-key")

            assert manager.consecutive_errors == 0

    def test_失敗リクエスト記録(self):
        """失敗したリクエストの記録"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            from compliant_api_manager import CompliantAPIManager

            manager = CompliantAPIManager()

            manager.record_failed_request("test-key", Exception("Error"))

            assert manager.consecutive_errors == 1

    def test_失敗リクエスト記録_レート制限(self):
        """レート制限での失敗リクエスト記録"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            from compliant_api_manager import CompliantAPIManager

            manager = CompliantAPIManager()
            manager.consecutive_errors = 10

            manager.record_failed_request("test-key", Exception("quota exceeded"))

            assert manager.consecutive_errors <= 5

    def test_ステータス取得(self):
        """現在の状態情報を取得"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-api-key"}):
            from compliant_api_manager import CompliantAPIManager

            manager = CompliantAPIManager()

            status = manager.get_status()

            assert "api_key_suffix" in status
            assert status["api_key_suffix"] == "pi-key"
            assert "can_make_request" in status
            assert "compliant_implementation" in status
            assert status["compliant_implementation"] is True


class TestRateLimitException:
    """RateLimitException例外のテスト"""

    def test_例外作成(self):
        """例外の作成"""
        from compliant_api_manager import RateLimitException

        exc = RateLimitException("Test message")

        assert str(exc) == "Test message"


class TestCreateCompliantGeminiClient:
    """create_compliant_gemini_client関数のテスト"""

    def test_クライアント作成成功(self):
        """クライアント作成成功"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            from compliant_api_manager import create_compliant_gemini_client

            with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_client:
                mock_client.return_value = MagicMock()

                client, manager = create_compliant_gemini_client()

                assert client is not None
                assert manager is not None

    def test_クライアント作成_レート制限(self):
        """レート制限でクライアント作成失敗"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            from compliant_api_manager import (
                create_compliant_gemini_client,
                RateLimitException,
                CompliantAPIManager,
            )

            with patch.object(CompliantAPIManager, "get_api_key") as mock_get_key:
                mock_get_key.side_effect = RateLimitException("Rate limit")

                with pytest.raises(RateLimitException):
                    create_compliant_gemini_client()

    def test_クライアント作成_一般エラー(self):
        """一般エラーでクライアント作成失敗"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            from compliant_api_manager import create_compliant_gemini_client

            with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_client:
                mock_client.side_effect = Exception("API Error")

                with pytest.raises(Exception):
                    create_compliant_gemini_client()


class TestGlobalFunctions:
    """グローバル関数のテスト"""

    def test_get_compliant_api_manager(self):
        """マネージャーのシングルトン取得"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            import compliant_api_manager

            # グローバル変数をリセット
            compliant_api_manager._compliant_manager = None

            manager1 = compliant_api_manager.get_compliant_api_manager()
            manager2 = compliant_api_manager.get_compliant_api_manager()

            assert manager1 is manager2

    def test_get_compliant_google_api_key(self):
        """規約準拠のAPIキー取得"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            import compliant_api_manager

            compliant_api_manager._compliant_manager = None

            api_key = compliant_api_manager.get_compliant_google_api_key()

            assert api_key == "test-key"

    def test_record_compliant_api_usage(self):
        """API使用成功の記録"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            import compliant_api_manager

            compliant_api_manager._compliant_manager = None
            manager = compliant_api_manager.get_compliant_api_manager()
            manager.consecutive_errors = 5

            compliant_api_manager.record_compliant_api_usage()

            assert manager.consecutive_errors == 0

    def test_handle_compliant_api_error(self):
        """規約準拠のエラーハンドリング"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            import compliant_api_manager

            compliant_api_manager._compliant_manager = None
            manager = compliant_api_manager.get_compliant_api_manager()

            compliant_api_manager.handle_compliant_api_error(Exception("Test"))

            assert manager.consecutive_errors == 1
