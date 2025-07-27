"""
Celeryタスク用のカスタム例外クラス

LLMプロバイダー（Gemini）のエラーを分類し、
適切なリトライ戦略を適用するための例外階層を定義
"""
import re
from typing import Optional, Dict, Any


class LLMError(Exception):
    """LLM関連エラーの基底クラス"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None, error_code: Optional[str] = None):
        super().__init__(message)
        self.original_error = original_error
        self.error_code = error_code
        self.should_retry = False
        self.retry_after = None  # 推奨される待機時間（秒）


class TemporaryLLMError(LLMError):
    """一時的なLLMエラー（リトライ可能）"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None, error_code: Optional[str] = None):
        super().__init__(message, original_error, error_code)
        self.should_retry = True


class PermanentLLMError(LLMError):
    """永続的なLLMエラー（リトライ不可）"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None, error_code: Optional[str] = None):
        super().__init__(message, original_error, error_code)
        self.should_retry = False


class RateLimitError(TemporaryLLMError):
    """レート制限エラー"""
    
    def __init__(self, message: str = "API rate limit exceeded", retry_after: int = 60, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class NetworkError(TemporaryLLMError):
    """ネットワーク関連エラー"""
    
    def __init__(self, message: str = "Network connection error", **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = 1  # 短い待機時間


class ServiceUnavailableError(TemporaryLLMError):
    """サービス利用不可エラー"""
    
    def __init__(self, message: str = "Service temporarily unavailable", retry_after: int = 30, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class AuthenticationError(PermanentLLMError):
    """認証エラー（リトライしても解決しない）"""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, **kwargs)


class QuotaExceededError(PermanentLLMError):
    """クォータ超過エラー（リトライしても解決しない）"""
    
    def __init__(self, message: str = "API quota exceeded", **kwargs):
        super().__init__(message, **kwargs)


class InvalidRequestError(PermanentLLMError):
    """無効なリクエストエラー（リトライしても解決しない）"""
    
    def __init__(self, message: str = "Invalid request parameters", **kwargs):
        super().__init__(message, **kwargs)


class ContextLengthError(PermanentLLMError):
    """コンテキスト長制限エラー（リトライしても解決しない）"""
    
    def __init__(self, message: str = "Context length limit exceeded", **kwargs):
        super().__init__(message, **kwargs)


class ContentFilterError(PermanentLLMError):
    """コンテンツフィルターエラー（リトライしても解決しない）"""
    
    def __init__(self, message: str = "Content filtered by safety policies", **kwargs):
        super().__init__(message, **kwargs)


def classify_error(error: Exception) -> LLMError:
    """
    例外を分析してLLMError派生クラスに分類する
    
    Args:
        error: 発生した例外
        
    Returns:
        分類されたLLMError派生クラスのインスタンス
    """
    error_str = str(error).lower()
    error_type = type(error).__name__
    
    # Gemini API特有のエラーパターンをチェック
    if hasattr(error, 'response') and error.response:
        status_code = getattr(error.response, 'status_code', None)
        
        # HTTPステータスコードベースの分類
        if status_code == 429:
            # Retry-Afterヘッダーがあれば使用
            retry_after = 60
            if hasattr(error.response, 'headers'):
                retry_after_header = error.response.headers.get('Retry-After')
                if retry_after_header:
                    try:
                        retry_after = int(retry_after_header)
                    except ValueError:
                        pass
            return RateLimitError(
                f"Rate limit exceeded (HTTP {status_code})",
                original_error=error,
                retry_after=retry_after
            )
        
        elif status_code == 503:
            return ServiceUnavailableError(
                f"Service unavailable (HTTP {status_code})",
                original_error=error
            )
        
        elif status_code in [401, 403]:
            return AuthenticationError(
                f"Authentication failed (HTTP {status_code})",
                original_error=error
            )
        
        elif status_code == 413:
            return ContextLengthError(
                f"Request too large (HTTP {status_code})",
                original_error=error
            )
        
        elif status_code == 400:
            return InvalidRequestError(
                f"Bad request (HTTP {status_code})",
                original_error=error
            )
    
    # エラーメッセージベースの分類
    error_patterns = {
        # レート制限関連
        r'rate.{0,10}limit|quota.{0,10}exceed|too.{0,10}many.{0,10}request': RateLimitError,
        r'requests per (minute|hour|day)|throttle': RateLimitError,
        
        # ネットワーク関連
        r'connection.{0,10}(error|failed|timeout|refused)|network.{0,10}error': NetworkError,
        r'timeout|timed.{0,5}out|unreachable|dns.{0,10}error': NetworkError,
        r'socket.{0,10}error|connection.{0,10}reset': NetworkError,
        
        # サービス利用不可
        r'service.{0,10}unavailable|server.{0,10}error|internal.{0,10}error': ServiceUnavailableError,
        r'temporarily.{0,10}unavailable|maintenance': ServiceUnavailableError,
        
        # 認証関連
        r'unauthorized|authentication.{0,10}failed|invalid.{0,10}(api.{0,5})?key': AuthenticationError,
        r'permission.{0,10}denied|access.{0,10}denied': AuthenticationError,
        
        # クォータ関連
        r'quota.{0,10}exceeded|usage.{0,10}limit|billing': QuotaExceededError,
        
        # コンテキスト長制限
        r'context.{0,10}(length|size)|token.{0,10}limit|input.{0,10}too.{0,10}long': ContextLengthError,
        r'maximum.{0,10}(context|token)|exceeds.{0,10}limit': ContextLengthError,
        
        # コンテンツフィルター
        r'content.{0,10}filter|safety.{0,10}(policy|violation)|inappropriate': ContentFilterError,
        r'blocked.{0,10}content|filtered.{0,10}response': ContentFilterError,
        
        # 無効なリクエスト
        r'invalid.{0,10}(request|parameter|input)|bad.{0,10}request': InvalidRequestError,
        r'malformed|validation.{0,10}error': InvalidRequestError,
    }
    
    # パターンマッチングで分類
    for pattern, error_class in error_patterns.items():
        if re.search(pattern, error_str):
            return error_class(
                f"Classified as {error_class.__name__}: {str(error)}",
                original_error=error
            )
    
    # 特定のPython例外タイプからの分類
    if error_type in ['ConnectionError', 'TimeoutError', 'HTTPError']:
        return NetworkError(
            f"Network error ({error_type}): {str(error)}",
            original_error=error
        )
    
    # デフォルトは一時的エラーとして扱う（安全側に倒す）
    return TemporaryLLMError(
        f"Unclassified error ({error_type}): {str(error)}",
        original_error=error
    )


def get_error_metadata(error: LLMError) -> Dict[str, Any]:
    """
    エラーのメタデータを取得
    
    Args:
        error: LLMErrorインスタンス
        
    Returns:
        エラーのメタデータ辞書
    """
    return {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'should_retry': error.should_retry,
        'retry_after': error.retry_after,
        'error_code': error.error_code,
        'original_error_type': type(error.original_error).__name__ if error.original_error else None,
        'is_permanent': isinstance(error, PermanentLLMError),
        'is_temporary': isinstance(error, TemporaryLLMError)
    }


# 後方互換性のためのエイリアス
classify_gemini_error = classify_error