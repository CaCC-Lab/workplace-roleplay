"""
Model routes tests for improved coverage.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestApiModels:
    """GET /api/models のテスト"""

    def test_モデル一覧を取得できる(self, client):
        """モデル選択が有効な場合にモデル一覧を取得"""
        with patch("routes.model_routes.is_model_selection_enabled") as mock_enabled:
            mock_enabled.return_value = True

            with patch("routes.model_routes.get_all_available_models") as mock_models:
                mock_models.return_value = {
                    "models": [
                        {"id": "gemini/gemini-1.5-pro", "name": "gemini-1.5-pro", "provider": "gemini"},
                        {"id": "gemini/gemini-1.5-flash", "name": "gemini-1.5-flash", "provider": "gemini"},
                    ],
                    "categories": {"gemini": []},
                }

                response = client.get("/api/models")

                assert response.status_code == 200
                data = response.get_json()
                assert "models" in data
                assert len(data["models"]) == 2

    def test_モデル選択無効時はデフォルトモデルを返す(self, client):
        """モデル選択が無効な場合"""
        with patch("routes.model_routes.is_model_selection_enabled") as mock_enabled:
            mock_enabled.return_value = False

            response = client.get("/api/models")

            assert response.status_code == 200
            data = response.get_json()
            assert "feature_disabled" in data
            assert data["feature_disabled"] is True
            assert "message" in data


class TestGetAllAvailableModels:
    """get_all_available_models関数のテスト"""

    def test_Gemini_APIからモデルを取得(self):
        """Gemini APIからモデル一覧を取得"""
        from routes.model_routes import get_all_available_models

        with patch("google.generativeai.configure"):
            with patch("google.generativeai.list_models") as mock_list:
                mock_model1 = MagicMock()
                mock_model1.name = "models/gemini-1.5-pro"
                mock_model2 = MagicMock()
                mock_model2.name = "models/gemini-1.5-flash"

                mock_list.return_value = [mock_model1, mock_model2]

                result = get_all_available_models()

                assert "models" in result
                assert len(result["models"]) == 2

    def test_APIキーがない場合フォールバック(self):
        """APIキーがない場合はフォールバックモデルを返す"""
        from routes.model_routes import get_all_available_models

        with patch("routes.model_routes.config") as mock_config:
            mock_config.GOOGLE_API_KEY = None

            result = get_all_available_models()

            assert "models" in result
            # フォールバックモデルが返される
            assert any("gemini" in m["id"] for m in result["models"])

    def test_例外発生時フォールバック(self):
        """例外発生時はフォールバックモデルを返す"""
        from routes.model_routes import get_all_available_models

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
        from routes.model_routes import _get_fallback_models

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


class TestApiFeatureFlags:
    """GET /api/feature_flags のテスト"""

    def test_機能フラグを取得できる(self, client):
        """機能フラグの取得"""
        response = client.get("/api/feature_flags")

        assert response.status_code == 200
        data = response.get_json()
        # 少なくとも基本的なフラグが含まれている
        assert isinstance(data, dict)

    def test_機能フラグ取得エラー時(self, client):
        """機能フラグ取得でエラーが発生した場合"""
        with patch("routes.model_routes.get_feature_flags") as mock_flags:
            mock_flags.side_effect = Exception("Config error")

            response = client.get("/api/feature_flags")

            assert response.status_code == 500
            data = response.get_json()
            assert "error" in data


class TestGetCsrfToken:
    """GET /api/csrf-token のテスト"""

    def test_CSRFトークンを取得できる(self, client):
        """CSRFトークンの取得"""
        response = client.get("/api/csrf-token")

        assert response.status_code == 200
        data = response.get_json()
        assert "csrf_token" in data
        assert "expires_in" in data
        assert data["expires_in"] == 3600
        assert len(data["csrf_token"]) > 0

    def test_CSRFトークンが一貫している(self, client):
        """同じセッションで同じトークンが返される"""
        response1 = client.get("/api/csrf-token")
        data1 = response1.get_json()

        response2 = client.get("/api/csrf-token")
        data2 = response2.get_json()

        # 同じセッションでは同じトークンが返される
        assert data1["csrf_token"] == data2["csrf_token"]

    def test_CSRFToken_フォールバック動作(self, client):
        """CSRFTokenクラスのフォールバック動作確認"""
        with patch("utils.security.CSRFToken.get_or_create") as mock_csrf:
            mock_csrf.side_effect = Exception("Import error")

            response = client.get("/api/csrf-token")

            # フォールバックでも正常に動作
            assert response.status_code == 200
            data = response.get_json()
            assert "csrf_token" in data


class TestGetApiKeyStatus:
    """GET /api/key_status のテスト"""

    def test_APIキー状態を取得できる(self, client):
        """APIキーの状態取得"""
        with patch("compliant_api_manager.get_compliant_api_manager") as mock_manager:
            mock_instance = MagicMock()
            mock_instance.get_status.return_value = {
                "total_keys": 4,
                "available_keys": 4,
                "current_key_index": 0,
            }
            mock_manager.return_value = mock_instance

            response = client.get("/api/key_status")

            assert response.status_code == 200
            data = response.get_json()
            assert "total_keys" in data

    def test_APIキー状態取得エラー時(self, client):
        """APIキー状態取得でエラーが発生した場合"""
        with patch("compliant_api_manager.get_compliant_api_manager") as mock_manager:
            mock_manager.side_effect = Exception("Manager error")

            response = client.get("/api/key_status")

            assert response.status_code == 500
            data = response.get_json()
            assert "error" in data
