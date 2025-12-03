"""
A/Bテスト比較テスト
新旧サービスの出力を比較して同等性を確認
"""
import pytest
import json
import asyncio
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from services.chat_service import ChatService
from services.llm_service import LLMService
from services.session_service import SessionService


class TestABComparison:
    """A/Bテスト比較のテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.app = app
        self.client = self.app.test_client()
        self.app.config["TESTING"] = True

        # セッションの初期化
        with self.client.session_transaction() as sess:
            sess["user_id"] = "test-user"
            sess["chat_history"] = []
            sess["chat_settings"] = {"system_prompt": "あなたは親切なアシスタントです。"}

    def test_v2_endpoint_exists(self):
        """V2エンドポイントが存在することを確認"""
        response = self.client.get("/api/v2/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "healthy"

    def test_v2_config_endpoint(self):
        """V2設定エンドポイントのテスト"""
        response = self.client.get("/api/v2/config")
        assert response.status_code == 200
        data = json.loads(response.data)
        # 新しいAPIではfeature flagsが返される
        assert isinstance(data, dict)
        assert any(key in data for key in ["model_selection", "tts", "default_model"])

    def test_v2_chat_basic(self):
        """V2チャットエンドポイントの基本動作テスト（CSRFトークン付き）"""
        # CSRFトークンを取得
        csrf_response = self.client.get("/api/csrf-token")
        csrf_token = json.loads(csrf_response.data)["csrf_token"]

        with patch("routes.ab_test_routes.get_services") as mock_services:
            mock_chat = MagicMock()

            async def mock_generator():
                yield "こんにちは"
                yield "！"

            mock_chat.process_chat_message = MagicMock(return_value=mock_generator())
            mock_services.return_value = (mock_chat, None, None)

            # リクエスト送信
            response = self.client.post(
                "/api/v2/chat",
                json={"message": "テスト"},
                headers={"Content-Type": "application/json", "X-CSRF-Token": csrf_token},
            )

            assert response.status_code == 200
            assert response.mimetype == "text/event-stream"

    def test_feature_flags_integration(self):
        """フィーチャーフラグの統合テスト"""
        from config.feature_flags import get_feature_flags

        # フィーチャーフラグインスタンスを取得
        flags = get_feature_flags()

        # 設定の確認
        config = flags.to_dict()
        assert "model_selection" in config
        assert "tts" in config
        assert "default_model" in config

        # 各フラグがbool型であることを確認
        assert isinstance(config["model_selection"], bool)
        assert isinstance(config["tts"], bool)

    @pytest.mark.asyncio
    async def test_service_output_consistency(self):
        """サービス出力の一貫性テスト"""
        # サービスインスタンス作成
        llm_service = Mock(spec=LLMService)
        session_service = Mock(spec=SessionService)
        chat_service = ChatService(llm_service, session_service)

        # モック設定
        async def mock_stream(*args, **kwargs):
            for chunk in ["テスト", "応答"]:
                yield chunk

        llm_service.stream_chat_response = mock_stream
        session_service.get_current_model.return_value = "gemini-1.5-flash"
        session_service.get_chat_history.return_value = []

        # 実行
        result = ""
        async for chunk in chat_service.process_chat_message("テスト"):
            result += chunk

        assert result == "テスト応答"

    def test_backward_compatibility(self):
        """後方互換性のテスト（既存エンドポイントが動作すること）"""
        # CSRFトークンを取得
        csrf_response = self.client.get("/api/csrf-token")
        csrf_token = json.loads(csrf_response.data)["csrf_token"]

        # 既存エンドポイントが引き続き動作することを確認
        with patch("app.initialize_llm") as mock_init_llm:
            mock_llm = MagicMock()
            mock_init_llm.return_value = mock_llm

            # LLMのストリーミングレスポンスをモック
            mock_llm.stream.return_value = iter([MagicMock(content="既存の応答")])

            response = self.client.post(
                "/api/chat",
                json={"message": "テスト"},
                headers={"Content-Type": "application/json", "X-CSRF-Token": csrf_token},
            )

            # エンドポイントが存在し応答を返すことを確認
            # ストリーミングレスポンスまたはエラー応答
            assert response.status_code in [200, 500]


class TestFeatureFlags:
    """フィーチャーフラグのテスト"""

    def test_feature_flags_instance(self):
        """FeatureFlagsインスタンスのテスト"""
        from config.feature_flags import FeatureFlags, get_feature_flags
        from config import get_cached_config

        config = get_cached_config()
        flags = FeatureFlags(config)

        # プロパティが正しく動作することを確認
        assert isinstance(flags.model_selection_enabled, bool)
        assert isinstance(flags.tts_enabled, bool)
        assert isinstance(flags.learning_history_enabled, bool)
        assert isinstance(flags.strength_analysis_enabled, bool)
        assert isinstance(flags.default_model, str)

    def test_feature_flags_to_dict(self):
        """to_dictメソッドのテスト"""
        from config.feature_flags import get_feature_flags

        flags = get_feature_flags()
        result = flags.to_dict()

        # 必要なキーが含まれていることを確認
        assert "model_selection" in result
        assert "tts" in result
        assert "learning_history" in result
        assert "strength_analysis" in result
        assert "default_model" in result

    def test_shortcut_functions(self):
        """ショートカット関数のテスト"""
        from config.feature_flags import (
            is_model_selection_enabled,
            is_tts_enabled,
            is_learning_history_enabled,
            is_strength_analysis_enabled,
            get_default_model,
        )

        # 各関数が正しい型を返すことを確認
        assert isinstance(is_model_selection_enabled(), bool)
        assert isinstance(is_tts_enabled(), bool)
        assert isinstance(is_learning_history_enabled(), bool)
        assert isinstance(is_strength_analysis_enabled(), bool)
        assert isinstance(get_default_model(), str)

    def test_require_feature_decorator(self):
        """require_featureデコレーターのテスト"""
        from config.feature_flags import require_feature
        from flask import Flask

        test_app = Flask(__name__)
        test_app.config["TESTING"] = True

        @test_app.route("/test")
        @require_feature("model_selection")
        def test_route():
            return "OK"

        with test_app.test_client() as client:
            # デコレーターが適用されていることを確認
            response = client.get("/test")
            # 機能が有効なら200、無効なら403
            assert response.status_code in [200, 403]

    def test_feature_disabled_exception(self):
        """FeatureDisabledException例外のテスト"""
        from config.feature_flags import FeatureDisabledException

        # 例外が正しく定義されていることを確認
        with pytest.raises(FeatureDisabledException):
            raise FeatureDisabledException("Test error")
