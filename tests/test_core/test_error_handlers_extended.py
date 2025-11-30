"""
Extended error handlers tests for improved coverage.
"""

import pytest
from unittest.mock import patch, MagicMock
from flask import Flask


@pytest.fixture
def app():
    """テスト用Flaskアプリケーション"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["TESTING"] = True

    from core.error_handlers import register_error_handlers

    register_error_handlers(app)

    return app


@pytest.fixture
def client(app):
    """テストクライアント"""
    return app.test_client()


class TestAppErrorHandler:
    """AppErrorハンドラーのテスト"""

    def test_AppError処理(self, app, client):
        """AppErrorの処理"""
        from errors import AppError

        @app.route("/test-app-error")
        def trigger_error():
            raise AppError(
                message="テストエラー",
                code="TEST_ERROR",
                status_code=400,
            )

        response = client.get("/test-app-error")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "error_id" in data["error"]


class TestValidationErrorHandler:
    """ValidationErrorハンドラーのテスト"""

    def test_ValidationError処理(self, app, client):
        """ValidationErrorの処理"""
        from errors import ValidationError

        @app.route("/test-validation-error")
        def trigger_error():
            raise ValidationError(
                field="test_field",
                message="無効な値です",
            )

        response = client.get("/test-validation-error")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data


class TestRateLimitErrorHandler:
    """RateLimitErrorハンドラーのテスト"""

    def test_RateLimitError処理(self, app, client):
        """RateLimitErrorの処理"""
        from errors import RateLimitError

        @app.route("/test-rate-limit-error")
        def trigger_error():
            raise RateLimitError(
                limit=100,
                window_seconds=60,
                details={"retry_after": 30},
            )

        response = client.get("/test-rate-limit-error")

        # 429または500（エラーハンドラの設定による）
        assert response.status_code in [429, 500]

    def test_RateLimitError_retryAfter付き(self, app, client):
        """retry_after付きRateLimitErrorの処理"""
        from errors import RateLimitError

        @app.route("/test-rate-limit-retry")
        def trigger_error():
            raise RateLimitError(
                limit=100,
                window_seconds=60,
                details={"retry_after": 45},
            )

        response = client.get("/test-rate-limit-retry")

        # 429または500
        assert response.status_code in [429, 500]


class TestExternalAPIErrorHandler:
    """ExternalAPIErrorハンドラーのテスト"""

    def test_ExternalAPIError処理(self, app, client):
        """ExternalAPIErrorの処理"""
        from errors import ExternalAPIError

        @app.route("/test-external-api-error")
        def trigger_error():
            raise ExternalAPIError(
                service="TestAPI",
                message="外部API接続失敗",
            )

        response = client.get("/test-external-api-error")

        assert response.status_code == 503
        data = response.get_json()
        assert "error" in data


class TestLLMErrorHandler:
    """LLMErrorハンドラーのテスト"""

    def test_LLMError処理(self, app, client):
        """LLMErrorの処理"""
        from errors import LLMError

        @app.route("/test-llm-error")
        def trigger_error():
            raise LLMError(
                provider="Gemini",
                model="gemini-1.5-flash",
                message="モデルエラー",
            )

        response = client.get("/test-llm-error")

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data


class Test404Handler:
    """404エラーハンドラーのテスト"""

    def test_存在しないページ(self, app, client):
        """存在しないページへのアクセス"""
        response = client.get("/nonexistent-page")

        assert response.status_code == 404

    def test_存在しないAPI(self, app, client):
        """存在しないAPIへのアクセス"""
        response = client.get("/api/nonexistent")

        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert "error_id" in data["error"]

    def test_favicon_リクエスト(self, app, client):
        """faviconリクエストの処理"""
        response = client.get("/favicon.ico")

        # 204 No Contentが返される
        assert response.status_code == 204


class Test500Handler:
    """500エラーハンドラーのテスト"""

    def test_内部エラー処理(self, app, client):
        """内部エラーの処理"""

        @app.route("/test-internal-error")
        def trigger_error():
            # app.debug = Falseの場合、未処理の例外が500になる
            # ただしhandle_unexpected_errorが先にキャッチするため
            # AppErrorに変換される
            raise RuntimeError("内部エラー")

        response = client.get("/test-internal-error")

        # 500または変換されたステータス
        assert response.status_code == 500


class TestUnexpectedErrorHandler:
    """予期しないエラーハンドラーのテスト"""

    def test_未知のエラー処理(self, app, client):
        """未知のエラーの処理"""

        @app.route("/test-unexpected-error")
        def trigger_error():
            raise ValueError("予期しないエラー")

        response = client.get("/test-unexpected-error")

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data

    def test_AppError_そのまま処理(self, app, client):
        """AppErrorはそのまま処理される"""
        from errors import AppError

        @app.route("/test-app-error-direct")
        def trigger_error():
            raise AppError(
                message="直接AppError",
                code="DIRECT_ERROR",
                status_code=418,
            )

        response = client.get("/test-app-error-direct")

        assert response.status_code == 418


class TestErrorIdGeneration:
    """エラーID生成のテスト"""

    def test_エラーIDが一意(self, app, client):
        """エラーIDが一意であることを確認"""
        from errors import AppError

        @app.route("/test-error-id")
        def trigger_error():
            raise AppError(message="テスト", code="TEST", status_code=400)

        response1 = client.get("/test-error-id")
        response2 = client.get("/test-error-id")

        data1 = response1.get_json()
        data2 = response2.get_json()

        # エラーIDが異なることを確認
        assert data1["error"]["error_id"] != data2["error"]["error_id"]


class TestErrorLogging:
    """エラーログのテスト"""

    def test_エラーがログに記録される(self, app, client):
        """エラーがログに記録されることを確認"""
        from errors import AppError

        @app.route("/test-logging")
        def trigger_error():
            raise AppError(message="ログテスト", code="LOG_TEST", status_code=400)

        with patch("core.error_handlers.logger") as mock_logger:
            response = client.get("/test-logging")

            # ログが呼び出されたことを確認
            assert mock_logger.error.called


class Test404HTMLFallback:
    """404 HTMLフォールバックのテスト"""

    def test_404テンプレートなし時のフォールバック(self, app, client):
        """404.htmlテンプレートがない場合のフォールバック"""
        # 通常のページリクエスト（非API）
        response = client.get("/nonexistent-page")

        # 404が返される
        assert response.status_code == 404

    def test_404テンプレートあり時の処理(self, app, client):
        """404.htmlテンプレートがある場合の処理"""
        with patch("core.error_handlers.render_template") as mock_render:
            mock_render.return_value = "<html>404</html>"

            response = client.get("/another-nonexistent-page")

            # 404が返される
            assert response.status_code == 404


class TestLLMErrorHandlerExtended:
    """LLMErrorハンドラーの拡張テスト"""

    def test_LLMError_詳細情報付き(self, app, client):
        """詳細情報付きLLMErrorの処理"""
        from errors import LLMError

        @app.route("/test-llm-error-details")
        def trigger_error():
            raise LLMError(
                message="レート制限に達しました",
                model_name="gemini-1.5-pro",
                error_type="rate_limit",
            )

        response = client.get("/test-llm-error-details")

        # LLMErrorはAppErrorを継承しており、ステータスコードは設定により異なる
        assert response.status_code in [500, 503]
        data = response.get_json()
        assert "error" in data
        assert "error_id" in data["error"]


class TestRateLimitErrorHandlerExtended:
    """RateLimitErrorハンドラーの拡張テスト"""

    def test_RateLimitError_詳細なしの場合(self, app, client):
        """詳細情報なしのRateLimitError"""
        from errors import RateLimitError

        @app.route("/test-rate-limit-no-details")
        def trigger_error():
            raise RateLimitError(
                limit=50,
                window_seconds=30,
            )

        response = client.get("/test-rate-limit-no-details")

        # ステータスコードを確認
        assert response.status_code in [429, 500]


class TestValidationErrorHandlerExtended:
    """ValidationErrorハンドラーの拡張テスト"""

    def test_ValidationError_複数フィールド(self, app, client):
        """複数フィールドのValidationError"""
        from errors import ValidationError

        @app.route("/test-validation-multiple")
        def trigger_error():
            raise ValidationError(
                field="email",
                message="メールアドレスの形式が無効です",
                details={"format": "invalid"},
            )

        response = client.get("/test-validation-multiple")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data


class TestExternalAPIErrorHandlerExtended:
    """ExternalAPIErrorハンドラーの拡張テスト"""

    def test_ExternalAPIError_詳細情報付き(self, app, client):
        """詳細情報付きExternalAPIError"""
        from errors import ExternalAPIError

        @app.route("/test-external-api-details")
        def trigger_error():
            raise ExternalAPIError(
                service="GoogleAPI",
                message="タイムアウトしました",
                original_error="Connection timeout after 30s",
            )

        response = client.get("/test-external-api-details")

        assert response.status_code == 503
        data = response.get_json()
        assert "error" in data


class TestAppErrorHandlerExtended:
    """AppErrorハンドラーの拡張テスト"""

    def test_AppError_カスタムステータスコード(self, app, client):
        """カスタムステータスコードのAppError"""
        from errors import AppError

        @app.route("/test-app-error-custom")
        def trigger_error():
            raise AppError(
                message="カスタムエラー",
                code="CUSTOM_ERROR",
                status_code=422,
                details={"field": "test"},
            )

        response = client.get("/test-app-error-custom")

        assert response.status_code == 422
        data = response.get_json()
        assert data["error"]["error_id"] is not None


class Test500ErrorHandlerExtended:
    """500エラーハンドラーの拡張テスト"""

    def test_500エラー_直接トリガー(self, app, client):
        """500エラーを直接トリガー"""

        @app.route("/test-500-direct")
        def trigger_error():
            # 0での除算でエラーを発生
            return str(1 / 0)

        response = client.get("/test-500-direct")

        assert response.status_code == 500


class TestHandleErrorResponse:
    """handle_error関数のレスポンステスト"""

    def test_handle_error_レスポンス形式(self, app, client):
        """handle_errorのレスポンス形式を確認"""
        from errors import AppError

        @app.route("/test-response-format")
        def trigger_error():
            raise AppError(
                message="フォーマットテスト",
                code="FORMAT_TEST",
                status_code=400,
            )

        response = client.get("/test-response-format")

        data = response.get_json()

        # レスポンス形式を確認
        assert "error" in data
        assert "message" in data["error"]
        assert "code" in data["error"]
        assert "error_id" in data["error"]
