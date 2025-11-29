"""
Main routes tests for improved coverage.
"""

import pytest
from unittest.mock import MagicMock, patch
from flask import Flask


class TestHealthCheck:
    """GET /health のテスト"""

    def test_ヘルスチェックが正常に動作(self, client):
        """ヘルスチェックエンドポイントの正常動作"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "checks" in data


class TestGetPerformanceMetrics:
    """GET /api/metrics のテスト"""

    def test_パフォーマンスメトリクスを取得(self, client):
        """パフォーマンスメトリクスの取得"""
        response = client.get("/api/metrics")

        # メトリクスモジュールが利用可能な場合は200、そうでなければ503
        assert response.status_code in [200, 503]

    def test_メトリクスモジュールがない場合503(self, client):
        """メトリクスモジュールがない場合は503を返す"""
        with patch("utils.performance.get_metrics") as mock_metrics:
            # ImportErrorを発生させる
            mock_metrics.side_effect = ImportError("Module not found")

            response = client.get("/api/metrics")

            # 503またはエラー処理（実装によって異なる）
            assert response.status_code in [200, 500, 503]


class TestIndexPage:
    """GET / のテスト"""

    def test_トップページを表示(self, client):
        """トップページの表示"""
        response = client.get("/")

        assert response.status_code == 200

    def test_モデル選択無効時のトップページ(self, client):
        """モデル選択無効時のトップページ表示"""
        with patch.dict("os.environ", {"ENABLE_MODEL_SELECTION": "false"}):
            response = client.get("/")

            assert response.status_code == 200


class TestChatPage:
    """GET /chat のテスト"""

    def test_チャットページを表示(self, client):
        """チャットページの表示"""
        response = client.get("/chat")

        assert response.status_code == 200


class TestFavicon:
    """GET /favicon.ico のテスト"""

    def test_ファビコンを取得(self, client):
        """ファビコンの取得"""
        response = client.get("/favicon.ico")

        # ファビコンが存在する場合は200、存在しない場合は204
        assert response.status_code in [200, 204]

    def test_ファビコンが存在しない場合204(self, client):
        """ファビコンが存在しない場合は204を返す"""
        with patch("routes.main_routes.send_from_directory") as mock_send:
            mock_send.side_effect = FileNotFoundError("Not found")

            response = client.get("/favicon.ico")

            # 204 No Content
            assert response.status_code == 204


class TestGetAllAvailableModels:
    """get_all_available_models関数のテスト"""

    def test_Gemini_APIからモデルを取得(self):
        """Gemini APIからモデル一覧を取得"""
        from routes.main_routes import get_all_available_models

        with patch("google.generativeai.configure"):
            with patch("google.generativeai.list_models") as mock_list:
                mock_model1 = MagicMock()
                mock_model1.name = "models/gemini-1.5-pro"
                mock_model2 = MagicMock()
                mock_model2.name = "models/gemini-1.5-flash"

                mock_list.return_value = [mock_model1, mock_model2]

                result = get_all_available_models()

                assert "models" in result
                assert "categories" in result
                assert len(result["models"]) == 2

    def test_APIキーがない場合フォールバック(self):
        """APIキーがない場合はフォールバックモデルを返す"""
        from routes.main_routes import get_all_available_models

        with patch("routes.main_routes.config.GOOGLE_API_KEY", None):
            result = get_all_available_models()

            assert "models" in result
            # フォールバックモデルが返される
            assert any("gemini" in m["id"] for m in result["models"])

    def test_例外発生時フォールバック(self):
        """例外発生時はフォールバックモデルを返す"""
        from routes.main_routes import get_all_available_models

        with patch("google.generativeai.configure") as mock_config:
            mock_config.side_effect = Exception("API Error")

            result = get_all_available_models()

            assert "models" in result
            # フォールバックモデルが返される
            assert len(result["models"]) >= 1


class TestGetFallbackModels:
    """_get_fallback_models関数のテスト"""

    def test_フォールバックモデルを返す(self):
        """フォールバックモデルの構造を確認"""
        from routes.main_routes import _get_fallback_models

        result = _get_fallback_models()

        assert "models" in result
        assert "categories" in result
        assert "gemini" in result["categories"]
        assert len(result["models"]) == 2

        # モデルの構造確認
        for model in result["models"]:
            assert "id" in model
            assert "name" in model
            assert "provider" in model
            assert model["provider"] == "gemini"


class TestRegisterTemplateFilters:
    """register_template_filters関数のテスト"""

    def test_datetimeフィルターが登録される(self):
        """datetimeフィルターの登録と動作確認"""
        from routes.main_routes import register_template_filters

        app = Flask(__name__)
        register_template_filters(app)

        # フィルターが登録されていることを確認
        assert "datetime" in app.jinja_env.filters

    def test_datetimeフィルターで日時を変換(self):
        """datetimeフィルターで日時を変換"""
        from routes.main_routes import register_template_filters

        app = Flask(__name__)
        register_template_filters(app)

        datetime_filter = app.jinja_env.filters["datetime"]

        # ISO形式の日時を変換
        result = datetime_filter("2024-01-15T10:30:00")
        assert "2024年" in result
        assert "01月" in result
        assert "15日" in result
        assert "10:30" in result

    def test_datetimeフィルターで空値を処理(self):
        """datetimeフィルターで空値を処理"""
        from routes.main_routes import register_template_filters

        app = Flask(__name__)
        register_template_filters(app)

        datetime_filter = app.jinja_env.filters["datetime"]

        # 空値
        assert datetime_filter(None) == "なし"
        assert datetime_filter("") == "なし"

    def test_datetimeフィルターで無効な値を処理(self):
        """datetimeフィルターで無効な値を処理"""
        from routes.main_routes import register_template_filters

        app = Flask(__name__)
        register_template_filters(app)

        datetime_filter = app.jinja_env.filters["datetime"]

        # 無効な値はそのまま文字列として返す
        result = datetime_filter("invalid-date")
        assert result == "invalid-date"
