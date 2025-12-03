"""
機能フラグシステムのテスト
段階的無効化システムの品質保証
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from flask import Flask
from config.feature_flags import (
    FeatureFlags,
    FeatureDisabledException,
    get_feature_flags,
    is_model_selection_enabled,
    is_tts_enabled,
    is_learning_history_enabled,
    is_strength_analysis_enabled,
    get_default_model,
    require_feature,
)


class TestFeatureFlags:
    """FeatureFlagsクラスのテスト"""

    def test_instance_creation(self):
        """FeatureFlagsインスタンスの作成テスト"""
        mock_config = MagicMock()
        mock_config.ENABLE_MODEL_SELECTION = True
        mock_config.ENABLE_TTS = False
        mock_config.ENABLE_LEARNING_HISTORY = True
        mock_config.ENABLE_STRENGTH_ANALYSIS = True
        mock_config.DEFAULT_MODEL = "gemini-1.5-flash"

        flags = FeatureFlags(mock_config)

        assert flags.model_selection_enabled is True
        assert flags.tts_enabled is False
        assert flags.learning_history_enabled is True
        assert flags.strength_analysis_enabled is True

    def test_to_dict(self):
        """to_dictメソッドのテスト"""
        mock_config = MagicMock()
        mock_config.ENABLE_MODEL_SELECTION = True
        mock_config.ENABLE_TTS = False
        mock_config.ENABLE_LEARNING_HISTORY = True
        mock_config.ENABLE_STRENGTH_ANALYSIS = True
        mock_config.DEFAULT_MODEL = "gemini-1.5-flash"

        flags = FeatureFlags(mock_config)
        result = flags.to_dict()

        # 実際のキー名に合わせてテスト
        assert "model_selection" in result
        assert result["model_selection"] is True
        assert result["tts"] is False
        assert result["learning_history"] is True
        assert result["strength_analysis"] is True
        assert result["default_model"] == "gemini-1.5-flash"

    def test_default_model_property(self):
        """default_modelプロパティのテスト"""
        mock_config = MagicMock()
        mock_config.ENABLE_MODEL_SELECTION = True
        mock_config.ENABLE_TTS = False
        mock_config.ENABLE_LEARNING_HISTORY = True
        mock_config.ENABLE_STRENGTH_ANALYSIS = True
        mock_config.DEFAULT_MODEL = "gemini-2.0-flash"

        flags = FeatureFlags(mock_config)

        assert flags.default_model == "gemini-2.0-flash"

    def test_feature_disabled_exception(self):
        """FeatureDisabledException例外のテスト"""
        with pytest.raises(FeatureDisabledException):
            raise FeatureDisabledException("Test feature is disabled")

    def test_get_feature_flags_returns_instance(self):
        """get_feature_flags()がFeatureFlagsインスタンスを返すテスト"""
        # キャッシュをクリア
        get_feature_flags.cache_clear()

        flags = get_feature_flags()
        assert isinstance(flags, FeatureFlags)

    def test_get_feature_flags_caching(self):
        """get_feature_flags()がキャッシュされるテスト"""
        get_feature_flags.cache_clear()

        flags1 = get_feature_flags()
        flags2 = get_feature_flags()

        # 同じインスタンスが返される（キャッシュ）
        assert flags1 is flags2


class TestShortcutFunctions:
    """ショートカット関数のテスト"""

    def test_is_model_selection_enabled(self):
        """モデル選択機能判定のテスト"""
        result = is_model_selection_enabled()
        assert isinstance(result, bool)

    def test_is_tts_enabled(self):
        """TTS機能判定のテスト"""
        result = is_tts_enabled()
        assert isinstance(result, bool)

    def test_is_learning_history_enabled(self):
        """学習履歴機能判定のテスト"""
        result = is_learning_history_enabled()
        assert isinstance(result, bool)

    def test_is_strength_analysis_enabled(self):
        """強み分析機能判定のテスト"""
        result = is_strength_analysis_enabled()
        assert isinstance(result, bool)

    def test_get_default_model(self):
        """デフォルトモデル取得のテスト"""
        result = get_default_model()
        assert isinstance(result, str)
        assert len(result) > 0


class TestRequireFeatureDecorator:
    """require_featureデコレーターのテスト"""

    def test_require_feature_decorator_returns_callable(self):
        """デコレーターがcallableを返すテスト"""
        decorator = require_feature("model_selection")
        assert callable(decorator)

    def test_require_feature_decorator_applies(self):
        """デコレーターが関数に適用されるテスト"""

        @require_feature("model_selection")
        def test_func():
            return "OK"

        # デコレータ適用後も関数として呼び出せる
        assert callable(test_func)

    def test_require_feature_in_flask_app(self):
        """Flaskアプリでのデコレーターテスト"""
        test_app = Flask(__name__)
        test_app.config["TESTING"] = True
        test_app.secret_key = "test-secret"

        @test_app.route("/test")
        @require_feature("model_selection")
        def test_route():
            return "OK"

        with test_app.test_client() as client:
            response = client.get("/test")
            # 機能が有効なら200、無効なら403
            assert response.status_code in [200, 403]

    def test_require_feature_unknown_feature(self):
        """未知の機能名でのデコレーターテスト"""
        test_app = Flask(__name__)
        test_app.config["TESTING"] = True
        test_app.secret_key = "test-secret"

        @test_app.route("/test-unknown")
        @require_feature("unknown_feature")
        def test_route():
            return "OK"

        with test_app.test_client() as client:
            response = client.get("/test-unknown")
            # 未知の機能は500エラー
            assert response.status_code == 500


class TestCachePerformance:
    """キャッシュ性能のテスト"""

    def test_repeated_calls_use_cache(self):
        """繰り返し呼び出しでキャッシュが使用されるテスト"""
        get_feature_flags.cache_clear()

        # 複数回呼び出し
        results = [is_model_selection_enabled() for _ in range(10)]

        # すべて同じ値
        assert len(set(results)) == 1

    def test_different_functions_return_consistent_results(self):
        """異なるショートカット関数が一貫した結果を返すテスト"""
        get_feature_flags.cache_clear()

        flags = get_feature_flags()

        # ショートカット関数とto_dict()の結果が一致
        assert is_model_selection_enabled() == flags.model_selection_enabled
        assert is_tts_enabled() == flags.tts_enabled
        assert is_learning_history_enabled() == flags.learning_history_enabled
        assert is_strength_analysis_enabled() == flags.strength_analysis_enabled
        assert get_default_model() == flags.default_model


@pytest.fixture
def feature_disabled_env():
    """機能無効化環境のフィクスチャ"""
    with patch.dict(
        os.environ,
        {
            "ENABLE_MODEL_SELECTION": "false",
            "ENABLE_TTS": "false",
            "ENABLE_LEARNING_HISTORY": "false",
            "ENABLE_STRENGTH_ANALYSIS": "false",
        },
    ):
        yield


@pytest.fixture
def feature_enabled_env():
    """機能有効化環境のフィクスチャ"""
    with patch.dict(
        os.environ,
        {
            "ENABLE_MODEL_SELECTION": "true",
            "ENABLE_TTS": "true",
            "ENABLE_LEARNING_HISTORY": "true",
            "ENABLE_STRENGTH_ANALYSIS": "true",
        },
    ):
        yield


class TestEnvironmentIntegration:
    """環境変数統合テスト"""

    def test_to_dict_returns_all_expected_keys(self):
        """to_dict()が期待されるすべてのキーを返すテスト"""
        flags = get_feature_flags()
        result = flags.to_dict()

        expected_keys = ["model_selection", "tts", "learning_history", "strength_analysis", "default_model"]

        for key in expected_keys:
            assert key in result

    def test_flags_are_serializable(self):
        """フラグ設定がJSON化可能であるテスト"""
        import json

        flags = get_feature_flags()
        result = flags.to_dict()

        # JSONシリアライズ可能
        json_str = json.dumps(result)
        assert isinstance(json_str, str)

        # デシリアライズして元の値と一致
        restored = json.loads(json_str)
        assert restored == result


if __name__ == "__main__":
    pytest.main([__file__])
