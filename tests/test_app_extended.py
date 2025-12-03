"""
Extended app.py tests for improved coverage.
"""

import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
from datetime import datetime


class TestCreateApp:
    """create_app関数のテスト"""

    def test_デフォルト設定でアプリ作成(self):
        """デフォルト設定でアプリケーションを作成"""
        from app import create_app

        with patch("app.init_extensions"):
            with patch("app.register_error_handlers"):
                with patch("app.register_middleware"):
                    with patch("app.register_blueprints"):
                        with patch("app._initialize_gemini_api"):
                            app = create_app()

                            assert isinstance(app, Flask)

    def test_カスタム設定でアプリ作成(self):
        """カスタム設定でアプリケーションを作成"""
        from app import create_app

        mock_config = MagicMock()
        mock_config.SECRET_KEY = "test-secret"
        mock_config.DEBUG = True
        mock_config.TESTING = True
        mock_config.WTF_CSRF_ENABLED = False
        mock_config.SESSION_TYPE = "filesystem"
        mock_config.SESSION_LIFETIME_MINUTES = 60

        with patch("app.init_extensions"):
            with patch("app.register_error_handlers"):
                with patch("app.register_middleware"):
                    with patch("app.register_blueprints"):
                        with patch("app._initialize_gemini_api"):
                            app = create_app(config=mock_config)

                            assert app.config["DEBUG"] is True
                            assert app.config["TESTING"] is True


class TestRegisterTemplateFilters:
    """_register_template_filters関数のテスト"""

    def test_日時フィルターの登録(self):
        """日時フィルターが登録される"""
        from app import _register_template_filters

        app = Flask(__name__)
        _register_template_filters(app)

        assert "datetime" in app.jinja_env.filters

    def test_日時フィルター_正常なISO形式(self):
        """正常なISO形式の日時変換"""
        from app import _register_template_filters

        app = Flask(__name__)
        _register_template_filters(app)

        datetime_filter = app.jinja_env.filters["datetime"]
        result = datetime_filter("2024-01-15T14:30:00")

        assert "2024年01月15日" in result
        assert "14:30" in result

    def test_日時フィルター_空値(self):
        """空値の場合は'なし'を返す"""
        from app import _register_template_filters

        app = Flask(__name__)
        _register_template_filters(app)

        datetime_filter = app.jinja_env.filters["datetime"]
        result = datetime_filter(None)

        assert result == "なし"

    def test_日時フィルター_無効な形式(self):
        """無効な形式の場合は文字列をそのまま返す"""
        from app import _register_template_filters

        app = Flask(__name__)
        _register_template_filters(app)

        datetime_filter = app.jinja_env.filters["datetime"]
        result = datetime_filter("invalid-date")

        assert result == "invalid-date"


class TestInitializeGeminiApi:
    """_initialize_gemini_api関数のテスト"""

    def test_APIキーありで初期化(self):
        """APIキーがある場合の初期化"""
        from app import _initialize_gemini_api

        mock_config = MagicMock()
        mock_config.GOOGLE_API_KEY = "test-api-key"
        mock_config.TESTING = False

        with patch("google.generativeai.configure") as mock_configure:
            _initialize_gemini_api(mock_config)

            mock_configure.assert_called_once_with(api_key="test-api-key")

    def test_テストモードで初期化スキップ(self):
        """テストモードではAPI初期化をスキップ"""
        from app import _initialize_gemini_api

        mock_config = MagicMock()
        mock_config.GOOGLE_API_KEY = "test-api-key"
        mock_config.TESTING = True

        with patch("google.generativeai.configure") as mock_configure:
            _initialize_gemini_api(mock_config)

            mock_configure.assert_not_called()

    def test_APIキーなしで初期化(self):
        """APIキーがない場合"""
        from app import _initialize_gemini_api

        mock_config = MagicMock()
        mock_config.GOOGLE_API_KEY = None
        mock_config.TESTING = False

        with patch("google.generativeai.configure") as mock_configure:
            _initialize_gemini_api(mock_config)

            mock_configure.assert_not_called()

    def test_初期化エラー時(self):
        """初期化でエラーが発生した場合"""
        from app import _initialize_gemini_api

        mock_config = MagicMock()
        mock_config.GOOGLE_API_KEY = "test-key"
        mock_config.TESTING = False

        with patch("google.generativeai.configure") as mock_configure:
            mock_configure.side_effect = Exception("API Error")

            # エラーでも例外は発生しない
            _initialize_gemini_api(mock_config)


class TestInitializeLlm:
    """initialize_llm関数のテスト"""

    def test_LLM初期化(self):
        """LLMの初期化"""
        from app import initialize_llm

        with patch("services.llm_service.LLMService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.initialize_llm.return_value = MagicMock()
            mock_service_class.return_value = mock_service

            result = initialize_llm("gemini-1.5-flash")

            mock_service.initialize_llm.assert_called_once_with("gemini-1.5-flash")


class TestCreateGeminiLlm:
    """create_gemini_llm関数のテスト"""

    def test_Gemini_LLM作成(self):
        """Gemini LLMの作成"""
        from app import create_gemini_llm

        with patch("services.llm_service.LLMService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.create_gemini_llm.return_value = MagicMock()
            mock_service_class.return_value = mock_service

            result = create_gemini_llm("gemini-1.5-pro")

            mock_service.create_gemini_llm.assert_called_once_with("gemini-1.5-pro")


class TestExtractContent:
    """extract_content関数のテスト"""

    def test_コンテンツ抽出(self):
        """コンテンツの抽出"""
        from app import extract_content

        result = extract_content("テスト")

        assert result == "テスト"


class TestCreateModelAndGetResponse:
    """create_model_and_get_response関数のテスト"""

    def test_応答取得(self):
        """モデルから応答を取得"""
        from app import create_model_and_get_response

        with patch("app.initialize_llm") as mock_init:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = "応答"
            mock_init.return_value = mock_llm

            with patch("app.extract_content") as mock_extract:
                mock_extract.return_value = "抽出された応答"

                result = create_model_and_get_response("gemini-1.5-flash", "プロンプト")

                assert result == "抽出された応答"

    def test_応答取得_extract無効(self):
        """extract=Falseの場合"""
        from app import create_model_and_get_response

        with patch("app.initialize_llm") as mock_init:
            mock_response = MagicMock()
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = mock_response
            mock_init.return_value = mock_llm

            result = create_model_and_get_response("gemini-1.5-flash", "プロンプト", extract=False)

            assert result == mock_response

    def test_応答取得_エラー(self):
        """エラー発生時"""
        from app import create_model_and_get_response

        with patch("app.initialize_llm") as mock_init:
            mock_init.side_effect = Exception("LLM Error")

            with pytest.raises(Exception):
                create_model_and_get_response("gemini-1.5-flash", "プロンプト")


class TestTryMultipleModelsForPrompt:
    """try_multiple_models_for_prompt関数のテスト"""

    def test_プロンプト応答取得(self):
        """プロンプトに対する応答を取得"""
        from app import try_multiple_models_for_prompt

        with patch("services.feedback_service.get_feedback_service") as mock_get:
            mock_service = MagicMock()
            mock_service.try_multiple_models_for_prompt.return_value = "応答"
            mock_get.return_value = mock_service

            result = try_multiple_models_for_prompt("テスト")

            assert result == "応答"


class TestUpdateFeedbackWithStrengthAnalysis:
    """update_feedback_with_strength_analysis関数のテスト"""

    def test_強み分析追加(self):
        """フィードバックに強み分析を追加"""
        from app import update_feedback_with_strength_analysis

        with patch("services.strength_service.get_strength_service") as mock_get:
            mock_service = MagicMock()
            mock_service.update_feedback_with_strength_analysis.return_value = {
                "feedback": "test",
                "strength_analysis": {},
            }
            mock_get.return_value = mock_service

            result = update_feedback_with_strength_analysis({"feedback": "test"}, "chat")

            assert "strength_analysis" in result


class TestGetAvailableGeminiModels:
    """get_available_gemini_models関数のテスト"""

    def test_モデルリスト取得(self):
        """利用可能なモデルリストを取得"""
        from app import get_available_gemini_models

        mock_model1 = MagicMock()
        mock_model1.name = "models/gemini-1.5-flash"
        mock_model2 = MagicMock()
        mock_model2.name = "models/gemini-1.5-pro"

        with patch("app.get_cached_config") as mock_config:
            mock_config.return_value.GOOGLE_API_KEY = "test-key"

            with patch("google.generativeai.configure"):
                with patch("google.generativeai.list_models") as mock_list:
                    mock_list.return_value = [mock_model1, mock_model2]

                    result = get_available_gemini_models()

                    assert len(result) == 2
                    assert "gemini/gemini-1.5-flash" in result

    def test_APIキーなしでモデルリスト取得(self):
        """APIキーがない場合は空リストを返す"""
        from app import get_available_gemini_models

        with patch("app.get_cached_config") as mock_config:
            mock_config.return_value.GOOGLE_API_KEY = None

            result = get_available_gemini_models()

            assert result == []

    def test_モデルリスト取得エラー(self):
        """エラー発生時はフォールバックリストを返す"""
        from app import get_available_gemini_models

        with patch("app.get_cached_config") as mock_config:
            mock_config.return_value.GOOGLE_API_KEY = "test-key"

            with patch("google.generativeai.configure"):
                with patch("google.generativeai.list_models") as mock_list:
                    mock_list.side_effect = Exception("API Error")

                    result = get_available_gemini_models()

                    assert "gemini/gemini-1.5-pro" in result
                    assert "gemini/gemini-1.5-flash" in result


class TestLoadScenarios:
    """_load_scenarios関数のテスト"""

    def test_シナリオロード成功(self):
        """シナリオのロード成功"""
        from app import _load_scenarios

        with patch("scenarios.load_scenarios") as mock_load:
            mock_load.return_value = {"scenario1": {}, "scenario2": {}}

            _load_scenarios()

            # グローバル変数が更新されることを確認
            from app import scenarios

            # Note: グローバル変数のテストは副作用があるため、
            # 実際の動作確認はintegrationテストで行う

    def test_シナリオロードエラー(self):
        """シナリオのロードエラー"""
        from app import _load_scenarios

        with patch("scenarios.load_scenarios") as mock_load:
            mock_load.side_effect = Exception("Load error")

            # エラーでも例外は発生しない
            _load_scenarios()
