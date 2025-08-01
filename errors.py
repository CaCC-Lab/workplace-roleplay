"""
エラーハンドリングの共通化
カスタム例外クラスとエラーコードの定義
"""
from typing import Optional, Dict, Any
from flask import jsonify, current_app
from functools import wraps
import traceback
import logging

# ロガーの設定
logger = logging.getLogger(__name__)


class AppError(Exception):
    """アプリケーション基底エラークラス"""
    
    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        
    def to_dict(self, include_details: bool = True) -> Dict[str, Any]:
        """エラーを辞書形式に変換"""
        error_dict = {
            "error": {
                "message": self.message,
                "code": self.code
            }
        }
        
        if include_details and self.details:
            error_dict["error"]["details"] = self.details
            
        return error_dict


class ValidationError(AppError):
    """バリデーションエラー"""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.field = field
        if field:
            details = details or {}
            details["field"] = field
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            details=details
        )


class AuthenticationError(AppError):
    """認証エラー"""
    
    def __init__(self, message: str = "認証が必要です"):
        super().__init__(
            message=message,
            code="AUTHENTICATION_REQUIRED",
            status_code=401
        )


class AuthorizationError(AppError):
    """認可エラー"""
    
    def __init__(self, message: str = "権限がありません"):
        super().__init__(
            message=message,
            code="PERMISSION_DENIED",
            status_code=403
        )


class NotFoundError(AppError):
    """リソース未発見エラー"""
    
    def __init__(self, resource: str, identifier: Optional[str] = None):
        message = f"{resource}が見つかりません"
        if identifier:
            message += f" (ID: {identifier})"
        super().__init__(
            message=message,
            code="RESOURCE_NOT_FOUND",
            status_code=404,
            details={"resource": resource, "identifier": identifier}
        )


class ExternalAPIError(AppError):
    """外部API関連エラー"""
    
    def __init__(self, service: str, message: str, original_error: Optional[str] = None):
        details = {"service": service}
        if original_error:
            details["original_error"] = original_error
        super().__init__(
            message=f"{service}との通信でエラーが発生しました: {message}",
            code="EXTERNAL_API_ERROR",
            status_code=503,
            details=details
        )


class RateLimitError(AppError):
    """レート制限エラー"""
    
    def __init__(self, service: str = "API", retry_after: Optional[int] = None):
        details = {"service": service}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(
            message=f"{service}のレート制限に達しました。しばらく待ってから再試行してください。",
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details
        )


class TimeoutError(AppError):
    """タイムアウトエラー"""
    
    def __init__(self, operation: str, timeout_seconds: Optional[int] = None):
        message = f"{operation}がタイムアウトしました"
        details = {"operation": operation}
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
            message += f" ({timeout_seconds}秒)"
        super().__init__(
            message=message,
            code="OPERATION_TIMEOUT",
            status_code=504,
            details=details
        )


def handle_error(error: Exception) -> tuple:
    """
    エラーハンドリングの共通処理
    
    Args:
        error: 発生したエラー
        
    Returns:
        tuple: (response, status_code)
    """
    # 開発環境かどうか
    is_development = current_app.config.get("ENV") == "development"
    
    # AppErrorの場合
    if isinstance(error, AppError):
        logger.error(
            f"Application error: {error.code}",
            extra={
                "error_code": error.code,
                "error_message": error.message,
                "error_details": error.details,
                "status_code": error.status_code
            }
        )
        return jsonify(error.to_dict(include_details=is_development)), error.status_code
    
    # その他のエラー
    logger.exception(
        "Unhandled exception occurred",
        extra={
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc() if is_development else None
        }
    )
    
    # 本番環境では詳細を隠す
    if is_development:
        error_response = {
            "error": {
                "message": str(error),
                "code": "INTERNAL_SERVER_ERROR",
                "type": type(error).__name__,
                "traceback": traceback.format_exc().split('\n')
            }
        }
    else:
        error_response = {
            "error": {
                "message": "内部エラーが発生しました。しばらくしてから再試行してください。",
                "code": "INTERNAL_SERVER_ERROR"
            }
        }
    
    return jsonify(error_response), 500


def handle_llm_specific_error(error: Exception, model_name: str = "Gemini") -> AppError:
    """
    LLM固有のエラーを共通のAppErrorに変換
    
    Args:
        error: LLMから発生したエラー
        model_name: 使用しているモデル名
        
    Returns:
        AppError: 変換されたエラー
    """
    error_str = str(error).lower()
    
    # レート制限エラー
    if any(keyword in error_str for keyword in ["rate limit", "quota", "429"]):
        return RateLimitError(service=model_name)
    
    # タイムアウトエラー
    if any(keyword in error_str for keyword in ["timeout", "timed out"]):
        return TimeoutError(operation=f"{model_name} API呼び出し")
    
    # APIキーエラー
    if any(keyword in error_str for keyword in ["api key", "unauthorized", "401"]):
        return ExternalAPIError(
            service=model_name,
            message="APIキーが無効です",
            original_error=str(error)
        )
    
    # その他のAPIエラー
    return ExternalAPIError(
        service=model_name,
        message="API呼び出しに失敗しました",
        original_error=str(error)
    )


def with_error_handling(func):
    """
    エラーハンドリングデコレータ
    関数実行時のエラーを自動的にハンドリング
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return handle_error(e)
    return wrapper