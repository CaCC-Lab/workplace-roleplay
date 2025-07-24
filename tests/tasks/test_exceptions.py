"""
Celeryタスク例外クラスのテスト
"""
import pytest
from unittest.mock import Mock
from tasks.exceptions import (
    LLMError, TemporaryLLMError, PermanentLLMError,
    RateLimitError, NetworkError, ServiceUnavailableError,
    AuthenticationError, QuotaExceededError, InvalidRequestError,
    ContextLengthError, ContentFilterError,
    classify_error, get_error_metadata
)


class TestLLMErrorHierarchy:
    """LLMError階層のテスト"""
    
    def test_base_llm_error(self):
        """基底LLMErrorクラスのテスト"""
        error = LLMError("test error", error_code="TEST_001")
        assert str(error) == "test error"
        assert error.error_code == "TEST_001"
        assert error.should_retry is False
        assert error.retry_after is None
    
    def test_temporary_error_properties(self):
        """一時的エラーのプロパティテスト"""
        error = TemporaryLLMError("temporary error")
        assert error.should_retry is True
        assert isinstance(error, LLMError)
    
    def test_permanent_error_properties(self):
        """永続的エラーのプロパティテスト"""
        error = PermanentLLMError("permanent error")
        assert error.should_retry is False
        assert isinstance(error, LLMError)
    
    def test_rate_limit_error(self):
        """レート制限エラーのテスト"""
        error = RateLimitError(retry_after=120)
        assert error.should_retry is True
        assert error.retry_after == 120
        assert isinstance(error, TemporaryLLMError)
    
    def test_network_error(self):
        """ネットワークエラーのテスト"""
        error = NetworkError("connection failed")
        assert error.should_retry is True
        assert error.retry_after == 1
        assert isinstance(error, TemporaryLLMError)
    
    def test_authentication_error(self):
        """認証エラーのテスト"""
        error = AuthenticationError("invalid api key")
        assert error.should_retry is False
        assert isinstance(error, PermanentLLMError)


class TestErrorClassification:
    """エラー分類機能のテスト"""
    
    def test_classify_http_429_error(self):
        """HTTP 429エラーの分類テスト"""
        # モックレスポンスオブジェクト
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '60'}
        
        original_error = Exception("Rate limit exceeded")
        original_error.response = mock_response
        
        classified = classify_error(original_error)
        assert isinstance(classified, RateLimitError)
        assert classified.retry_after == 60
        assert "HTTP 429" in str(classified)
    
    def test_classify_http_503_error(self):
        """HTTP 503エラーの分類テスト"""
        mock_response = Mock()
        mock_response.status_code = 503
        
        original_error = Exception("Service unavailable")
        original_error.response = mock_response
        
        classified = classify_error(original_error)
        assert isinstance(classified, ServiceUnavailableError)
        assert "HTTP 503" in str(classified)
    
    def test_classify_http_401_error(self):
        """HTTP 401エラーの分類テスト"""
        mock_response = Mock()
        mock_response.status_code = 401
        
        original_error = Exception("Unauthorized")
        original_error.response = mock_response
        
        classified = classify_error(original_error)
        assert isinstance(classified, AuthenticationError)
        assert "HTTP 401" in str(classified)
    
    def test_classify_http_413_error(self):
        """HTTP 413エラーの分類テスト"""
        mock_response = Mock()
        mock_response.status_code = 413
        
        original_error = Exception("Request too large")
        original_error.response = mock_response
        
        classified = classify_error(original_error)
        assert isinstance(classified, ContextLengthError)
        assert "HTTP 413" in str(classified)
    
    def test_classify_rate_limit_by_message(self):
        """メッセージパターンによるレート制限エラーの分類テスト"""
        test_cases = [
            "rate limit exceeded",
            "too many requests",
            "quota exceeded",
            "requests per minute limit reached"
        ]
        
        for message in test_cases:
            error = Exception(message)
            classified = classify_error(error)
            assert isinstance(classified, RateLimitError), f"Failed for: {message}"
    
    def test_classify_network_error_by_message(self):
        """メッセージパターンによるネットワークエラーの分類テスト"""
        test_cases = [
            "connection error",
            "network timeout",
            "connection refused",
            "socket error",
            "dns error"
        ]
        
        for message in test_cases:
            error = Exception(message)
            classified = classify_error(error)
            assert isinstance(classified, NetworkError), f"Failed for: {message}"
    
    def test_classify_service_unavailable_by_message(self):
        """メッセージパターンによるサービス利用不可エラーの分類テスト"""
        test_cases = [
            "service unavailable",
            "server error",
            "internal error",
            "temporarily unavailable",
            "maintenance mode"
        ]
        
        for message in test_cases:
            error = Exception(message)
            classified = classify_error(error)
            assert isinstance(classified, ServiceUnavailableError), f"Failed for: {message}"
    
    def test_classify_authentication_error_by_message(self):
        """メッセージパターンによる認証エラーの分類テスト"""
        test_cases = [
            "unauthorized",
            "authentication failed",
            "invalid api key",
            "permission denied",
            "access denied"
        ]
        
        for message in test_cases:
            error = Exception(message)
            classified = classify_error(error)
            assert isinstance(classified, AuthenticationError), f"Failed for: {message}"
    
    def test_classify_context_length_error_by_message(self):
        """メッセージパターンによるコンテキスト長エラーの分類テスト"""
        test_cases = [
            "context length exceeded",
            "token limit reached",
            "input too long",
            "maximum context size",
            "exceeds token limit"
        ]
        
        for message in test_cases:
            error = Exception(message)
            classified = classify_error(error)
            assert isinstance(classified, ContextLengthError), f"Failed for: {message}"
    
    def test_classify_content_filter_error_by_message(self):
        """メッセージパターンによるコンテンツフィルターエラーの分類テスト"""
        test_cases = [
            "content filtered",
            "safety policy violation",
            "inappropriate content",
            "blocked content",
            "filtered response"
        ]
        
        for message in test_cases:
            error = Exception(message)
            classified = classify_error(error)
            assert isinstance(classified, ContentFilterError), f"Failed for: {message}"
    
    def test_classify_python_exception_types(self):
        """Python例外タイプによる分類テスト"""
        test_cases = [
            ("ConnectionError", NetworkError),
            ("TimeoutError", NetworkError),
            ("HTTPError", NetworkError)
        ]
        
        for exception_name, expected_class in test_cases:
            # 動的に例外クラスを作成
            exception_class = type(exception_name, (Exception,), {})
            error = exception_class("test error")
            
            classified = classify_error(error)
            assert isinstance(classified, expected_class), f"Failed for: {exception_name}"
    
    def test_classify_unknown_error(self):
        """未分類エラーのデフォルト処理テスト"""
        error = Exception("unknown error type")
        classified = classify_error(error)
        
        assert isinstance(classified, TemporaryLLMError)
        assert "Unclassified error" in str(classified)
        assert classified.original_error is error


class TestErrorMetadata:
    """エラーメタデータ取得のテスト"""
    
    def test_get_error_metadata_temporary(self):
        """一時的エラーのメタデータテスト"""
        original_error = Exception("original error")
        error = RateLimitError(
            "rate limit error",
            original_error=original_error,
            error_code="RATE_001",
            retry_after=60
        )
        
        metadata = get_error_metadata(error)
        
        expected = {
            'error_type': 'RateLimitError',
            'error_message': 'rate limit error',
            'should_retry': True,
            'retry_after': 60,
            'error_code': 'RATE_001',
            'original_error_type': 'Exception',
            'is_permanent': False,
            'is_temporary': True
        }
        
        assert metadata == expected
    
    def test_get_error_metadata_permanent(self):
        """永続的エラーのメタデータテスト"""
        error = AuthenticationError("auth failed", error_code="AUTH_001")
        
        metadata = get_error_metadata(error)
        
        expected = {
            'error_type': 'AuthenticationError',
            'error_message': 'auth failed',
            'should_retry': False,
            'retry_after': None,
            'error_code': 'AUTH_001',
            'original_error_type': None,
            'is_permanent': True,
            'is_temporary': False
        }
        
        assert metadata == expected
    
    def test_get_error_metadata_no_original_error(self):
        """原因エラーがない場合のメタデータテスト"""
        error = NetworkError("network failed")
        
        metadata = get_error_metadata(error)
        
        assert metadata['original_error_type'] is None
        assert metadata['error_type'] == 'NetworkError'
        assert metadata['should_retry'] is True


class TestGeminiSpecificErrors:
    """Gemini API特有のエラーパターンテスト"""
    
    def test_gemini_rate_limit_patterns(self):
        """Gemini APIのレート制限エラーパターン"""
        test_messages = [
            "Quota exceeded for requests per minute",
            "Resource exhausted: quota exceeded",
            "Too many requests. Try again later",
            "Rate limit exceeded. Retry after 60 seconds"
        ]
        
        for message in test_messages:
            error = Exception(message)
            classified = classify_error(error)
            assert isinstance(classified, RateLimitError)
    
    def test_gemini_safety_filter_patterns(self):
        """Gemini APIの安全フィルターエラーパターン"""
        test_messages = [
            "The response was blocked due to safety concerns",
            "Content filtered by safety policies",
            "Response blocked by safety filters",
            "Safety violation detected"
        ]
        
        for message in test_messages:
            error = Exception(message)
            classified = classify_error(error)
            assert isinstance(classified, ContentFilterError)
    
    def test_gemini_context_length_patterns(self):
        """Gemini APIのコンテキスト長エラーパターン"""
        test_messages = [
            "Input text is too long",
            "Token limit exceeded",
            "Context window size exceeded",
            "Request exceeds maximum token limit"
        ]
        
        for message in test_messages:
            error = Exception(message)
            classified = classify_error(error)
            assert isinstance(classified, ContextLengthError)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])