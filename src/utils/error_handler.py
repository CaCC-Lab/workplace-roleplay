"""エラーハンドリングユーティリティ"""
import logging
from functools import wraps
from typing import Callable, Any, Optional, Dict
from flask import jsonify

logger = logging.getLogger(__name__)


class AppError(Exception):
    """アプリケーション固有のエラー基底クラス"""
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ValidationError(AppError):
    """入力検証エラー"""
    def __init__(self, message: str, field: Optional[str] = None):
        details = {"field": field} if field else {}
        super().__init__(message, status_code=400, details=details)


class AuthenticationError(AppError):
    """認証エラー"""
    def __init__(self, message: str = "認証が必要です"):
        super().__init__(message, status_code=401)


class AuthorizationError(AppError):
    """認可エラー"""
    def __init__(self, message: str = "権限がありません"):
        super().__init__(message, status_code=403)


class NotFoundError(AppError):
    """リソースが見つからないエラー"""
    def __init__(self, resource: str, identifier: Any):
        message = f"{resource}が見つかりません: {identifier}"
        super().__init__(message, status_code=404, details={"resource": resource, "id": identifier})


class ExternalServiceError(AppError):
    """外部サービスエラー"""
    def __init__(self, service: str, message: str):
        full_message = f"{service}サービスエラー: {message}"
        super().__init__(full_message, status_code=503, details={"service": service})


def handle_errors(f: Callable) -> Callable:
    """エラーハンドリングデコレーター"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except AppError as e:
            logger.error(f"Application error in {f.__name__}: {e.message}", extra={"details": e.details})
            return jsonify({
                "success": False,
                "error": e.message,
                "details": e.details
            }), e.status_code
        except ValueError as e:
            logger.error(f"Value error in {f.__name__}: {str(e)}")
            return jsonify({
                "success": False,
                "error": "入力値が不正です",
                "details": {"message": str(e)}
            }), 400
        except Exception as e:
            logger.exception(f"Unexpected error in {f.__name__}")
            return jsonify({
                "success": False,
                "error": "予期しないエラーが発生しました",
                "details": {"type": type(e).__name__}
            }), 500
    
    return decorated_function


def format_error_response(error: Exception, request_info: Optional[Dict] = None) -> Dict[str, Any]:
    """エラーレスポンスをフォーマット"""
    if isinstance(error, AppError):
        return {
            "success": False,
            "error": error.message,
            "error_type": type(error).__name__,
            "details": error.details,
            "request_info": request_info
        }
    else:
        return {
            "success": False,
            "error": "システムエラーが発生しました",
            "error_type": type(error).__name__,
            "details": {"message": str(error)},
            "request_info": request_info
        }


def log_error(error: Exception, context: Optional[Dict] = None) -> None:
    """エラーをログに記録"""
    if isinstance(error, AppError):
        if error.status_code >= 500:
            logger.error(f"{type(error).__name__}: {error.message}", extra={"context": context, "details": error.details})
        else:
            logger.warning(f"{type(error).__name__}: {error.message}", extra={"context": context, "details": error.details})
    else:
        logger.exception("Unexpected error occurred", extra={"context": context})