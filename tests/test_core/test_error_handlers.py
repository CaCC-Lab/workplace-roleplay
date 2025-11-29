"""
Error handlers tests for improved coverage.
"""

import pytest
from unittest.mock import MagicMock, patch
from flask import Flask

from core.error_handlers import register_error_handlers
from errors import (
    AppError,
    ValidationError,
    RateLimitError,
    ExternalAPIError,
    LLMError,
    NotFoundError,
)


@pytest.fixture
def test_app():
    """テスト用Flaskアプリケーション"""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"

    # テスト用ルートを追加
    @app.route("/test/app-error")
    def raise_app_error():
        raise AppError("Test app error", code="TEST_ERROR", status_code=400)

    @app.route("/test/validation-error")
    def raise_validation_error():
        raise ValidationError("Validation failed", field="test_field")

    @app.route("/test/rate-limit-error")
    def raise_rate_limit_error():
        raise RateLimitError("Rate limit exceeded", retry_after=60)

    @app.route("/test/external-api-error")
    def raise_external_api_error():
        raise ExternalAPIError("test_service", "External API failed")

    @app.route("/test/llm-error")
    def raise_llm_error():
        raise LLMError("LLM failed", provider="test_provider")

    @app.route("/test/unexpected-error")
    def raise_unexpected_error():
        raise RuntimeError("Unexpected error")

    @app.route("/api/test")
    def api_test():
        return {"status": "ok"}

    register_error_handlers(app)
    return app


@pytest.fixture
def test_client(test_app):
    """テストクライアント"""
    return test_app.test_client()


class TestRegisterErrorHandlers:
    """register_error_handlers関数のテスト"""

    def test_404エラーハンドラが動作する(self, test_client):
        """404エラーハンドラが正しく動作すること"""
        response = test_client.get("/nonexistent-route-for-test")
        assert response.status_code == 404

    def test_500エラーハンドラが動作する(self, test_client):
        """500エラーハンドラが正しく動作すること"""
        response = test_client.get("/test/unexpected-error")
        assert response.status_code == 500


class TestAppErrorHandler:
    """AppErrorハンドラのテスト"""

    def test_AppErrorが適切に処理される(self, test_client):
        """AppErrorがJSON形式で返される"""
        response = test_client.get("/test/app-error")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_エラーIDが生成される(self, test_client):
        """エラーIDがレスポンスに含まれる"""
        response = test_client.get("/test/app-error")
        data = response.get_json()

        # エラー構造とerror_idの存在を確認
        assert isinstance(data.get("error"), dict)
        assert "error_id" in data["error"]


class TestValidationErrorHandler:
    """ValidationErrorハンドラのテスト"""

    def test_ValidationErrorが適切に処理される(self, test_client):
        """ValidationErrorがJSON形式で返される"""
        response = test_client.get("/test/validation-error")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data


class TestRateLimitErrorHandler:
    """RateLimitErrorハンドラのテスト"""

    def test_RateLimitErrorが適切に処理される(self, test_client):
        """RateLimitErrorがJSON形式で返される"""
        response = test_client.get("/test/rate-limit-error")

        assert response.status_code == 429
        data = response.get_json()
        assert "error" in data


class TestExternalAPIErrorHandler:
    """ExternalAPIErrorハンドラのテスト"""

    def test_ExternalAPIErrorが適切に処理される(self, test_client):
        """ExternalAPIErrorがJSON形式で返される"""
        response = test_client.get("/test/external-api-error")

        assert response.status_code == 503
        data = response.get_json()
        assert "error" in data


class TestLLMErrorHandler:
    """LLMErrorハンドラのテスト"""

    def test_LLMErrorが適切に処理される(self, test_client):
        """LLMErrorがJSON形式で返される"""
        response = test_client.get("/test/llm-error")

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data


class TestNotFoundHandler:
    """404エラーハンドラのテスト"""

    def test_存在しないページで404を返す(self, test_client):
        """存在しないページで404が返される"""
        response = test_client.get("/nonexistent-page")

        assert response.status_code == 404

    def test_favicon_icoで204を返す(self, test_client):
        """favicon.icoへのアクセスで204を返す"""
        response = test_client.get("/favicon.ico")

        assert response.status_code == 204

    def test_APIエンドポイントの404はJSONを返す(self, test_client):
        """存在しないAPIエンドポイントでJSONが返される"""
        response = test_client.get("/api/nonexistent")

        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data


class TestInternalErrorHandler:
    """500エラーハンドラのテスト"""

    def test_予期しないエラーで500を返す(self, test_client):
        """予期しないエラーで500が返される"""
        response = test_client.get("/test/unexpected-error")

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data


class TestUnexpectedErrorHandler:
    """予期しないエラーハンドラのテスト"""

    def test_未知のエラーが処理される(self, test_client):
        """未知のエラーが適切に処理される"""
        response = test_client.get("/test/unexpected-error")

        assert response.status_code == 500

    def test_AppErrorの場合はそのまま処理(self, test_app):
        """AppErrorの場合はhandle_errorに渡される"""
        from core.error_handlers import register_error_handlers

        # AppErrorを投げるルートを追加
        @test_app.route("/test/app-error-direct")
        def raise_app_error_direct():
            error = AppError("Direct error", code="DIRECT", status_code=418)
            raise error

        client = test_app.test_client()
        response = client.get("/test/app-error-direct")

        # ステータスコードが保持される
        assert response.status_code == 418


class TestErrorLogging:
    """エラーロギングのテスト"""

    def test_エラーがログに記録される(self, test_app, caplog):
        """エラーがログに記録される"""
        import logging

        with caplog.at_level(logging.ERROR):
            client = test_app.test_client()
            client.get("/test/app-error")

        # エラーログが記録されていることを確認
        assert len(caplog.records) > 0
        assert any("Error" in record.message for record in caplog.records)


class TestErrorIdGeneration:
    """エラーID生成のテスト"""

    def test_ユニークなエラーIDが生成される(self, test_client):
        """異なるリクエストで異なるエラーIDが生成される"""
        response1 = test_client.get("/test/app-error")
        response2 = test_client.get("/test/app-error")

        data1 = response1.get_json()
        data2 = response2.get_json()

        # 両方に error_id が含まれていることと、値が異なることを確認
        assert isinstance(data1.get("error"), dict)
        assert isinstance(data2.get("error"), dict)
        assert "error_id" in data1["error"]
        assert "error_id" in data2["error"]
        assert data1["error"]["error_id"] != data2["error"]["error_id"]
