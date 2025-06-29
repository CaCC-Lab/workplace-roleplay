"""
エラーハンドリングモジュールのテスト
TDD原則に従い、共通エラーハンドリングの振る舞いをテスト
"""
import pytest
from unittest.mock import patch, MagicMock
import json
from flask import Flask, jsonify

from errors import (
    AppError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ExternalAPIError,
    RateLimitError,
    TimeoutError,
    handle_error,
    handle_llm_specific_error,
    with_error_handling
)


class TestAppError:
    """AppError基底クラスのテスト"""
    
    def test_基本的なエラー作成(self):
        """基本的なAppErrorが正しく作成されることを確認"""
        error = AppError("テストエラー", "TEST_ERROR", 500)
        
        assert error.message == "テストエラー"
        assert error.code == "TEST_ERROR"
        assert error.status_code == 500
        assert error.details == {}
    
    def test_詳細情報付きエラー作成(self):
        """詳細情報を含むエラーが正しく作成されることを確認"""
        details = {"field": "email", "value": "invalid"}
        error = AppError("詳細付きエラー", "DETAIL_ERROR", 400, details)
        
        assert error.details == details
    
    def test_エラーの辞書変換(self):
        """エラーが辞書形式に正しく変換されることを確認"""
        error = AppError("変換テスト", "CONVERT_TEST", 403, {"key": "value"})
        
        # 詳細を含む場合
        result = error.to_dict(include_details=True)
        assert result == {
            "error": {
                "message": "変換テスト",
                "code": "CONVERT_TEST",
                "details": {"key": "value"}
            }
        }
        
        # 詳細を含まない場合
        result = error.to_dict(include_details=False)
        assert "details" not in result["error"]


class TestSpecificErrors:
    """特定のエラークラスのテスト"""
    
    def test_ValidationError(self):
        """ValidationErrorが正しく作成されることを確認"""
        error = ValidationError("無効な値です", field="email")
        
        assert error.message == "無効な値です"
        assert error.code == "VALIDATION_ERROR"
        assert error.status_code == 400
        assert error.details["field"] == "email"
    
    def test_AuthenticationError(self):
        """AuthenticationErrorが正しく作成されることを確認"""
        error = AuthenticationError()
        
        assert error.message == "認証が必要です"
        assert error.code == "AUTHENTICATION_REQUIRED"
        assert error.status_code == 401
    
    def test_AuthorizationError(self):
        """AuthorizationErrorが正しく作成されることを確認"""
        error = AuthorizationError("管理者権限が必要です")
        
        assert error.message == "管理者権限が必要です"
        assert error.code == "PERMISSION_DENIED"
        assert error.status_code == 403
    
    def test_NotFoundError(self):
        """NotFoundErrorが正しく作成されることを確認"""
        error = NotFoundError("ユーザー", "12345")
        
        assert error.message == "ユーザーが見つかりません (ID: 12345)"
        assert error.code == "RESOURCE_NOT_FOUND"
        assert error.status_code == 404
        assert error.details["resource"] == "ユーザー"
        assert error.details["identifier"] == "12345"
    
    def test_ExternalAPIError(self):
        """ExternalAPIErrorが正しく作成されることを確認"""
        error = ExternalAPIError("Gemini", "接続失敗", "Connection timeout")
        
        assert "Gemini" in error.message
        assert "接続失敗" in error.message
        assert error.code == "EXTERNAL_API_ERROR"
        assert error.status_code == 503
        assert error.details["service"] == "Gemini"
        assert error.details["original_error"] == "Connection timeout"
    
    def test_RateLimitError(self):
        """RateLimitErrorが正しく作成されることを確認"""
        error = RateLimitError("Gemini API", retry_after=60)
        
        assert "Gemini API" in error.message
        assert "レート制限" in error.message
        assert error.code == "RATE_LIMIT_EXCEEDED"
        assert error.status_code == 429
        assert error.details["retry_after"] == 60
    
    def test_TimeoutError(self):
        """TimeoutErrorが正しく作成されることを確認"""
        error = TimeoutError("API呼び出し", timeout_seconds=30)
        
        assert "API呼び出し" in error.message
        assert "30秒" in error.message
        assert error.code == "OPERATION_TIMEOUT"
        assert error.status_code == 504
        assert error.details["operation"] == "API呼び出し"
        assert error.details["timeout_seconds"] == 30


class TestErrorHandling:
    """エラーハンドリング関数のテスト"""
    
    @pytest.fixture
    def app(self):
        """テスト用のFlaskアプリを作成"""
        app = Flask(__name__)
        app.config['ENV'] = 'development'
        app.config['TESTING'] = True
        return app
    
    def test_handle_error_with_AppError(self, app):
        """AppErrorの処理が正しく動作することを確認"""
        with app.app_context():
            error = ValidationError("テストエラー", field="test")
            response, status_code = handle_error(error)
            
            # JSONレスポンスの確認
            data = json.loads(response.data)
            assert status_code == 400
            assert data["error"]["message"] == "テストエラー"
            assert data["error"]["code"] == "VALIDATION_ERROR"
            assert data["error"]["details"]["field"] == "test"
    
    def test_handle_error_with_generic_exception_dev(self, app):
        """開発環境で一般的な例外の処理を確認"""
        with app.app_context():
            app.config['ENV'] = 'development'
            error = ValueError("一般的なエラー")
            response, status_code = handle_error(error)
            
            data = json.loads(response.data)
            assert status_code == 500
            assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
            assert data["error"]["message"] == "一般的なエラー"
            assert "traceback" in data["error"]  # 開発環境ではトレースバック含む
    
    def test_handle_error_with_generic_exception_prod(self, app):
        """本番環境で一般的な例外の処理を確認"""
        with app.app_context():
            app.config['ENV'] = 'production'
            error = ValueError("一般的なエラー")
            response, status_code = handle_error(error)
            
            data = json.loads(response.data)
            assert status_code == 500
            assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
            assert data["error"]["message"] == "内部エラーが発生しました。しばらくしてから再試行してください。"
            assert "traceback" not in data["error"]  # 本番環境ではトレースバック含まない


class TestLLMSpecificErrorHandling:
    """LLM固有のエラーハンドリングのテスト"""
    
    def test_レート制限エラーの変換(self):
        """レート制限エラーが正しく変換されることを確認"""
        # 429エラー
        error = Exception("Error 429: Rate limit exceeded")
        result = handle_llm_specific_error(error, "Gemini")
        
        assert isinstance(result, RateLimitError)
        assert result.status_code == 429
        assert "Gemini" in result.details["service"]
        
        # quota exceeded
        error = Exception("Quota exceeded for this API")
        result = handle_llm_specific_error(error, "Gemini")
        
        assert isinstance(result, RateLimitError)
    
    def test_タイムアウトエラーの変換(self):
        """タイムアウトエラーが正しく変換されることを確認"""
        error = Exception("Request timed out after 30 seconds")
        result = handle_llm_specific_error(error, "Gemini")
        
        assert isinstance(result, TimeoutError)
        assert result.status_code == 504
        assert "Gemini API呼び出し" in result.message
    
    def test_認証エラーの変換(self):
        """認証エラーが正しく変換されることを確認"""
        # APIキーエラー
        error = Exception("Invalid API key provided")
        result = handle_llm_specific_error(error, "Gemini")
        
        assert isinstance(result, ExternalAPIError)
        assert "APIキーが無効" in result.message
        
        # 401エラー
        error = Exception("Error 401: Unauthorized")
        result = handle_llm_specific_error(error, "Gemini")
        
        assert isinstance(result, ExternalAPIError)
        assert "APIキーが無効" in result.message
    
    def test_その他のエラーの変換(self):
        """その他のエラーが汎用APIエラーに変換されることを確認"""
        error = Exception("Unknown error occurred")
        result = handle_llm_specific_error(error, "Gemini")
        
        assert isinstance(result, ExternalAPIError)
        assert "API呼び出しに失敗しました" in result.message
        assert result.details["original_error"] == "Unknown error occurred"


class TestErrorDecorator:
    """エラーハンドリングデコレータのテスト"""
    
    @pytest.fixture
    def app(self):
        """テスト用のFlaskアプリを作成"""
        app = Flask(__name__)
        app.config['ENV'] = 'development'
        app.config['TESTING'] = True
        return app
    
    def test_デコレータが正常な実行を妨げない(self, app):
        """デコレータが正常な関数実行を妨げないことを確認"""
        with app.app_context():
            @with_error_handling
            def normal_function():
                return jsonify({"result": "success"}), 200
            
            response, status = normal_function()
            data = json.loads(response.data)
            
            assert status == 200
            assert data["result"] == "success"
    
    def test_デコレータがエラーを捕捉する(self, app):
        """デコレータがエラーを適切に捕捉することを確認"""
        with app.app_context():
            @with_error_handling
            def error_function():
                raise ValidationError("デコレータテスト")
            
            response, status = error_function()
            data = json.loads(response.data)
            
            assert status == 400
            assert data["error"]["message"] == "デコレータテスト"
            assert data["error"]["code"] == "VALIDATION_ERROR"
    
    def test_デコレータが引数を正しく渡す(self, app):
        """デコレータが関数の引数を正しく渡すことを確認"""
        with app.app_context():
            @with_error_handling
            def function_with_args(x, y, z=10):
                return jsonify({"result": x + y + z}), 200
            
            response, status = function_with_args(1, 2, z=3)
            data = json.loads(response.data)
            
            assert status == 200
            assert data["result"] == 6