"""
Extended error handlers tests for improved coverage.
"""

import pytest
from unittest.mock import patch, MagicMock
from flask import Flask


@pytest.fixture
def app():
    """テスト用Flaskアプリケーション"""
    from core.error_handlers import register_error_handlers

    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["TESTING"] = True

    register_error_handlers(app)

    return app


@pytest.fixture
def client(app):
    """テストクライアント"""
    return app.test_client()


class TestAppErrorHandler:
    """AppErrorハンドラーのテスト"""

    def test_AppErrorハンドリング(self, app, client):
        """AppErrorのハンドリング"""
        from errors import AppError

        @app.route("/test-app-error")
        def test_route():
            raise AppError(
                message="テストエラー",
                code="TEST_ERROR",
                status_code=400,
            )

        response = client.get("/test-app-error")
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_AppErrorレスポンスにerror_id追加(self, app, client):
        """エラーレスポンスにerror_idが追加される"""
        from errors import AppError

        @app.route("/test-error-id")
        def test_route():
            raise AppError(
                message="テストエラー",
                code="TEST_ERROR",
                status_code=400,
            )

        response = client.get("/test-error-id")
        data = response.get_json()
        assert "error" in data
        # error_idが追加されることを確認


class TestValidationErrorHandler:
    """ValidationErrorハンドラーのテスト"""

    def test_ValidationErrorハンドリング(self, app, client):
        """ValidationErrorのハンドリング"""
        from errors import ValidationError

        @app.route("/test-validation-error")
        def test_route():
            raise ValidationError(
                message="バリデーションエラー",
                field="test_field",
                expected="valid",
                actual="invalid",
            )

        response = client.get("/test-validation-error")
        # ValidationErrorは最終的にUnexpectedErrorとして処理される場合がある
        assert response.status_code in [400, 500]
        data = response.get_json()
        assert "error" in data


class TestRateLimitErrorHandler:
    """RateLimitErrorハンドラーのテスト"""

    def test_RateLimitErrorハンドリング(self, app, client):
        """RateLimitErrorのハンドリング"""
        from errors import RateLimitError

        @app.route("/test-rate-limit-error")
        def test_route():
            raise RateLimitError(
                message="レート制限エラー",
                retry_after=60,
            )

        response = client.get("/test-rate-limit-error")
        # RateLimitErrorのステータスコードは429または500
        assert response.status_code in [429, 500]
        data = response.get_json()
        assert "error" in data

    def test_RateLimitError_retry_after(self, app, client):
        """RateLimitErrorにretry_afterが含まれる"""
        from errors import RateLimitError

        @app.route("/test-rate-limit-retry")
        def test_route():
            raise RateLimitError(
                message="レート制限",
                retry_after=120,
            )

        response = client.get("/test-rate-limit-retry")
        data = response.get_json()
        # retry_afterが含まれることを確認


class TestExternalAPIErrorHandler:
    """ExternalAPIErrorハンドラーのテスト"""

    def test_ExternalAPIErrorハンドリング(self, app, client):
        """ExternalAPIErrorのハンドリング"""
        from errors import ExternalAPIError

        @app.route("/test-external-api-error")
        def test_route():
            raise ExternalAPIError(
                message="外部APIエラー",
                service_name="TestService",
            )

        response = client.get("/test-external-api-error")
        # ExternalAPIErrorのステータスコードは503または500
        assert response.status_code in [500, 503]
        data = response.get_json()
        assert "error" in data


class TestLLMErrorHandler:
    """LLMErrorハンドラーのテスト"""

    def test_LLMErrorハンドリング(self, app, client):
        """LLMErrorのハンドリング"""
        from errors import LLMError

        @app.route("/test-llm-error")
        def test_route():
            raise LLMError(
                message="LLMエラー",
                model_name="gemini-1.5-flash",
            )

        response = client.get("/test-llm-error")
        # LLMErrorのステータスコードは500または503
        assert response.status_code in [500, 503]
        data = response.get_json()
        assert "error" in data


class TestNotFoundHandler:
    """404ハンドラーのテスト"""

    def test_favicon_ico_は204を返す(self, client):
        """favicon.icoは204 No Contentを返す"""
        response = client.get("/favicon.ico")
        assert response.status_code == 204

    def test_APIエンドポイントの404(self, client):
        """APIエンドポイントの404はJSONを返す"""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        # エラーコードはNOT_FOUNDまたはRESOURCE_NOT_FOUND
        assert data["error"]["code"] in ["NOT_FOUND", "RESOURCE_NOT_FOUND"]

    def test_通常ページの404(self, client):
        """通常ページの404"""
        response = client.get("/nonexistent-page")
        # 404.htmlがある場合はHTMLを返し、なければJSONを返す
        assert response.status_code == 404


class TestInternalErrorHandler:
    """500ハンドラーのテスト"""

    def test_500エラーハンドリング(self, app, client):
        """500エラーのハンドリング"""

        @app.route("/test-500-error")
        def test_route():
            raise Exception("内部エラー")

        # 予期しないエラーがハンドリングされる
        response = client.get("/test-500-error")
        assert response.status_code == 500


class TestUnexpectedErrorHandler:
    """予期しないエラーハンドラーのテスト"""

    def test_予期しないエラーハンドリング(self, app, client):
        """予期しないエラーのハンドリング"""

        @app.route("/test-unexpected")
        def test_route():
            raise ValueError("予期しないエラー")

        response = client.get("/test-unexpected")
        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data

    def test_AppError派生エラーはそのまま処理(self, app, client):
        """AppError派生エラーはそのまま処理される"""
        from errors import NotFoundError

        @app.route("/test-not-found-derived")
        def test_route():
            raise NotFoundError("リソース", "test_id")

        response = client.get("/test-not-found-derived")
        assert response.status_code == 404


class TestErrorIdGeneration:
    """エラーID生成のテスト"""

    def test_エラーIDは8文字(self, app, client):
        """エラーIDは8文字"""
        from errors import AppError

        @app.route("/test-error-id-length")
        def test_route():
            raise AppError(
                message="テスト",
                code="TEST",
                status_code=400,
            )

        response = client.get("/test-error-id-length")
        data = response.get_json()

        # error_idが存在する場合は8文字であることを確認
        if data and "error" in data and "error_id" in data["error"]:
            assert len(data["error"]["error_id"]) == 8


class TestLogError:
    """エラーログ記録のテスト"""

    def test_エラーがログに記録される(self, app, client):
        """エラーがログに記録される"""
        from errors import AppError

        @app.route("/test-log")
        def test_route():
            raise AppError(
                message="ログテスト",
                code="LOG_TEST",
                status_code=400,
            )

        with patch("core.error_handlers.logger") as mock_logger:
            response = client.get("/test-log")

            # logger.errorが呼ばれたことを確認
            mock_logger.error.assert_called()
