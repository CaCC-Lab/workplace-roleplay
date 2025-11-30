"""
Extended errors module tests for improved coverage.
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
    app.config["ENV"] = "development"
    return app


class TestAppError:
    """AppErrorクラスのテスト"""

    def test_基本的な初期化(self):
        """基本的な初期化"""
        from errors import AppError

        error = AppError(
            message="テストエラー",
            code="TEST_ERROR",
            status_code=400,
        )

        assert error.message == "テストエラー"
        assert error.code == "TEST_ERROR"
        assert error.status_code == 400
        assert error.details == {}

    def test_詳細付き初期化(self):
        """詳細情報付きの初期化"""
        from errors import AppError

        error = AppError(
            message="テストエラー",
            code="TEST_ERROR",
            status_code=400,
            details={"field": "test_field"},
        )

        assert error.details == {"field": "test_field"}

    def test_to_dict(self):
        """辞書への変換"""
        from errors import AppError

        error = AppError(
            message="テストエラー",
            code="TEST_ERROR",
            status_code=400,
            details={"field": "test_field"},
        )

        result = error.to_dict()

        assert result["error"]["message"] == "テストエラー"
        assert result["error"]["code"] == "TEST_ERROR"
        assert result["error"]["details"]["field"] == "test_field"

    def test_to_dict_詳細なし(self):
        """詳細なしの辞書変換"""
        from errors import AppError

        error = AppError(
            message="テストエラー",
            code="TEST_ERROR",
            status_code=400,
        )

        result = error.to_dict(include_details=False)

        assert "details" not in result["error"]


class TestValidationError:
    """ValidationErrorクラスのテスト"""

    def test_フィールドなしで初期化(self):
        """フィールドなしで初期化"""
        from errors import ValidationError

        error = ValidationError(message="バリデーションエラー")

        assert error.message == "バリデーションエラー"
        assert error.code == "VALIDATION_ERROR"
        assert error.status_code == 400

    def test_フィールド付きで初期化(self):
        """フィールド付きで初期化"""
        from errors import ValidationError

        error = ValidationError(message="バリデーションエラー", field="email")

        assert error.details["field"] == "email"


class TestAuthenticationError:
    """AuthenticationErrorクラスのテスト"""

    def test_デフォルトメッセージ(self):
        """デフォルトメッセージでの初期化"""
        from errors import AuthenticationError

        error = AuthenticationError()

        assert error.message == "認証が必要です"
        assert error.code == "AUTHENTICATION_REQUIRED"
        assert error.status_code == 401

    def test_カスタムメッセージ(self):
        """カスタムメッセージでの初期化"""
        from errors import AuthenticationError

        error = AuthenticationError(message="トークンが無効です")

        assert error.message == "トークンが無効です"


class TestAuthorizationError:
    """AuthorizationErrorクラスのテスト"""

    def test_デフォルトメッセージ(self):
        """デフォルトメッセージでの初期化"""
        from errors import AuthorizationError

        error = AuthorizationError()

        assert error.message == "権限がありません"
        assert error.code == "PERMISSION_DENIED"
        assert error.status_code == 403


class TestNotFoundError:
    """NotFoundErrorクラスのテスト"""

    def test_リソースのみ(self):
        """リソース名のみでの初期化"""
        from errors import NotFoundError

        error = NotFoundError(resource="ユーザー")

        assert "ユーザーが見つかりません" in error.message
        assert error.status_code == 404

    def test_リソースとID(self):
        """リソース名とIDでの初期化"""
        from errors import NotFoundError

        error = NotFoundError(resource="ユーザー", identifier="123")

        assert "ユーザーが見つかりません" in error.message
        assert "ID: 123" in error.message


class TestExternalAPIError:
    """ExternalAPIErrorクラスのテスト"""

    def test_基本的な初期化(self):
        """基本的な初期化"""
        from errors import ExternalAPIError

        error = ExternalAPIError(
            service="Gemini",
            message="接続失敗",
        )

        assert "Gemini" in error.message
        assert error.status_code == 503

    def test_オリジナルエラー付き(self):
        """オリジナルエラー付きの初期化"""
        from errors import ExternalAPIError

        error = ExternalAPIError(
            service="Gemini",
            message="接続失敗",
            original_error="Connection timeout",
        )

        assert error.details["original_error"] == "Connection timeout"


class TestRateLimitError:
    """RateLimitErrorクラスのテスト"""

    def test_基本的な初期化(self):
        """基本的な初期化"""
        from errors import RateLimitError

        error = RateLimitError()

        assert error.status_code == 429
        assert error.code == "RATE_LIMIT_EXCEEDED"

    def test_retry_after付き(self):
        """retry_after付きの初期化"""
        from errors import RateLimitError

        error = RateLimitError(service="Gemini", retry_after=60)

        assert error.details["retry_after"] == 60


class TestTimeoutError:
    """TimeoutErrorクラスのテスト"""

    def test_基本的な初期化(self):
        """基本的な初期化"""
        from errors import TimeoutError

        error = TimeoutError(operation="API呼び出し")

        assert "タイムアウト" in error.message
        assert error.status_code == 504

    def test_タイムアウト秒数付き(self):
        """タイムアウト秒数付きの初期化"""
        from errors import TimeoutError

        error = TimeoutError(operation="API呼び出し", timeout_seconds=30)

        assert "30秒" in error.message
        assert error.details["timeout_seconds"] == 30


class TestLLMError:
    """LLMErrorクラスのテスト"""

    def test_基本的な初期化(self):
        """基本的な初期化"""
        from errors import LLMError

        error = LLMError(message="LLMエラー")

        assert error.message == "LLMエラー"
        assert error.status_code == 503

    def test_詳細情報付き(self):
        """詳細情報付きの初期化"""
        from errors import LLMError

        error = LLMError(
            message="LLMエラー",
            model_name="gemini-1.5-flash",
            error_type="RateLimitError",
            original_error="Too many requests",
        )

        assert error.details["model_name"] == "gemini-1.5-flash"
        assert error.details["error_type"] == "RateLimitError"
        assert error.details["original_error"] == "Too many requests"


class TestHandleError:
    """handle_error関数のテスト"""

    def test_AppErrorのハンドリング(self, app):
        """AppErrorのハンドリング"""
        from errors import handle_error, AppError

        with app.app_context():
            error = AppError(
                message="テストエラー",
                code="TEST_ERROR",
                status_code=400,
            )

            response, status_code = handle_error(error)

            assert status_code == 400

    def test_一般エラーのハンドリング_開発環境(self, app):
        """開発環境での一般エラーのハンドリング"""
        from errors import handle_error

        app.config["ENV"] = "development"

        with app.app_context():
            error = ValueError("一般エラー")

            response, status_code = handle_error(error)

            assert status_code == 500
            data = response.get_json()
            assert "traceback" in data["error"]

    def test_一般エラーのハンドリング_本番環境(self, app):
        """本番環境での一般エラーのハンドリング"""
        from errors import handle_error

        app.config["ENV"] = "production"

        with app.app_context():
            error = ValueError("一般エラー")

            response, status_code = handle_error(error)

            assert status_code == 500
            data = response.get_json()
            assert "traceback" not in data["error"]


class TestHandleLLMSpecificError:
    """handle_llm_specific_error関数のテスト"""

    def test_レート制限エラー(self):
        """レート制限エラーの変換"""
        from errors import handle_llm_specific_error, RateLimitError

        error = Exception("Rate limit exceeded")

        result = handle_llm_specific_error(error, "Gemini")

        assert isinstance(result, RateLimitError)

    def test_クォータエラー(self):
        """クォータエラーの変換"""
        from errors import handle_llm_specific_error, RateLimitError

        error = Exception("Quota exceeded")

        result = handle_llm_specific_error(error, "Gemini")

        assert isinstance(result, RateLimitError)

    def test_タイムアウトエラー(self):
        """タイムアウトエラーの変換"""
        from errors import handle_llm_specific_error, TimeoutError

        error = Exception("Connection timed out")

        result = handle_llm_specific_error(error, "Gemini")

        assert isinstance(result, TimeoutError)

    def test_APIキーエラー(self):
        """APIキーエラーの変換"""
        from errors import handle_llm_specific_error, ExternalAPIError

        error = Exception("Invalid API key")

        result = handle_llm_specific_error(error, "Gemini")

        assert isinstance(result, ExternalAPIError)

    def test_その他のエラー(self):
        """その他のエラーの変換"""
        from errors import handle_llm_specific_error, ExternalAPIError

        error = Exception("Unknown error")

        result = handle_llm_specific_error(error, "Gemini")

        assert isinstance(result, ExternalAPIError)


class TestWithErrorHandling:
    """with_error_handlingデコレータのテスト"""

    def test_正常実行(self, app):
        """正常実行"""
        from errors import with_error_handling

        @with_error_handling
        def test_func():
            return "success"

        with app.app_context():
            result = test_func()

            assert result == "success"

    def test_エラー発生時(self, app):
        """エラー発生時"""
        from errors import with_error_handling

        @with_error_handling
        def test_func():
            raise ValueError("テストエラー")

        with app.app_context():
            response, status_code = test_func()

            assert status_code == 500


class TestSecureErrorHandler:
    """secure_error_handlerデコレータのテスト"""

    def test_正常実行(self, app):
        """正常実行"""
        from errors import secure_error_handler

        @secure_error_handler
        def test_func():
            return "success"

        with app.test_request_context("/test"):
            result = test_func()

            assert result == "success"

    def test_AppError発生時(self, app):
        """AppError発生時"""
        from errors import secure_error_handler, AppError

        @secure_error_handler
        def test_func():
            raise AppError(
                message="テストエラー",
                code="TEST_ERROR",
                status_code=400,
            )

        with app.test_request_context("/test"):
            with patch("time.sleep"):  # 遅延をスキップ
                response, status_code = test_func()

                assert status_code == 400

    def test_一般エラー発生時(self, app):
        """一般エラー発生時"""
        from errors import secure_error_handler

        @secure_error_handler
        def test_func():
            raise ValueError("一般エラー")

        with app.test_request_context("/test"):
            with patch("time.sleep"):  # 遅延をスキップ
                response, status_code = test_func()

                assert status_code == 500
