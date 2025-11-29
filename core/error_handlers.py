"""
Error handlers module.
Centralizes all Flask error handling.
"""

import logging
import uuid
from datetime import datetime

from flask import Flask, jsonify, render_template, request

from errors import (
    AppError,
    ExternalAPIError,
    LLMError,
    NotFoundError,
    RateLimitError,
    ValidationError,
    handle_error,
)

# ロガーの設定
logger = logging.getLogger(__name__)


def register_error_handlers(app: Flask):
    """
    エラーハンドラーをFlaskアプリケーションに登録

    Args:
        app: Flaskアプリケーションインスタンス
    """

    def _generate_error_id() -> str:
        """エラーIDを生成"""
        return str(uuid.uuid4())[:8]

    def _log_error(error: Exception, error_id: str, status_code: int):
        """エラーをログに記録"""
        logger.error(
            f"Error {error_id}: {type(error).__name__}",
            extra={
                "error_id": error_id,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "status_code": status_code,
                "path": request.path,
                "method": request.method,
                "endpoint": request.endpoint,
                "timestamp": datetime.now().isoformat(),
            },
            exc_info=True,
        )

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        """アプリケーション固有のエラーハンドラー"""
        error_id = _generate_error_id()
        _log_error(error, error_id, error.status_code)

        # エラーIDをレスポンスに追加
        response = handle_error(error)
        if isinstance(response, tuple) and len(response) == 2:
            json_response, status_code = response
            if hasattr(json_response, "get_json"):
                data = json_response.get_json()
                if data and "error" in data:
                    data["error"]["error_id"] = error_id
                    return jsonify(data), status_code
        return response

    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError):
        """バリデーションエラーのハンドラー"""
        error_id = _generate_error_id()
        _log_error(error, error_id, error.status_code)

        response = handle_error(error)
        if isinstance(response, tuple) and len(response) == 2:
            json_response, status_code = response
            if hasattr(json_response, "get_json"):
                data = json_response.get_json()
                if data and "error" in data:
                    data["error"]["error_id"] = error_id
                    return jsonify(data), status_code
        return response

    @app.errorhandler(RateLimitError)
    def handle_rate_limit_error(error: RateLimitError):
        """レート制限エラーのハンドラー"""
        error_id = _generate_error_id()
        _log_error(error, error_id, error.status_code)

        response = handle_error(error)
        if isinstance(response, tuple) and len(response) == 2:
            json_response, status_code = response
            if hasattr(json_response, "get_json"):
                data = json_response.get_json()
                if data and "error" in data:
                    data["error"]["error_id"] = error_id
                    if "retry_after" in error.details:
                        data["error"]["retry_after"] = error.details["retry_after"]
                    return jsonify(data), status_code
        return response

    @app.errorhandler(ExternalAPIError)
    def handle_external_api_error(error: ExternalAPIError):
        """外部APIエラーのハンドラー"""
        error_id = _generate_error_id()
        _log_error(error, error_id, error.status_code)

        response = handle_error(error)
        if isinstance(response, tuple) and len(response) == 2:
            json_response, status_code = response
            if hasattr(json_response, "get_json"):
                data = json_response.get_json()
                if data and "error" in data:
                    data["error"]["error_id"] = error_id
                    return jsonify(data), status_code
        return response

    @app.errorhandler(LLMError)
    def handle_llm_error(error: LLMError):
        """LLMエラーのハンドラー"""
        error_id = _generate_error_id()
        _log_error(error, error_id, error.status_code)

        response = handle_error(error)
        if isinstance(response, tuple) and len(response) == 2:
            json_response, status_code = response
            if hasattr(json_response, "get_json"):
                data = json_response.get_json()
                if data and "error" in data:
                    data["error"]["error_id"] = error_id
                    return jsonify(data), status_code
        return response

    @app.errorhandler(404)
    def handle_not_found(error):
        """404エラーのハンドラー"""
        # favicon.icoの場合は204 No Contentを返す
        if request.path == "/favicon.ico":
            return "", 204

        error_id = _generate_error_id()
        _log_error(error, error_id, 404)

        if request.path.startswith("/api/"):
            # APIエンドポイントの場合はJSON形式で返す
            not_found_error = NotFoundError("APIエンドポイント", request.path)
            response = handle_error(not_found_error)
            if isinstance(response, tuple) and len(response) == 2:
                json_response, status_code = response
                if hasattr(json_response, "get_json"):
                    data = json_response.get_json()
                    if data and "error" in data:
                        data["error"]["error_id"] = error_id
                        return jsonify(data), status_code
            return response

        # 通常のページの場合は404ページを表示（フォールバック付き）
        try:
            return render_template("404.html"), 404
        except:
            # 404.htmlが存在しない場合のフォールバック
            return (
                jsonify(
                    {
                        "error": {
                            "message": "Page not found",
                            "code": "NOT_FOUND",
                            "error_id": error_id,
                            "path": request.path,
                        }
                    }
                ),
                404,
            )

    @app.errorhandler(500)
    def handle_internal_error(error):
        """500エラーのハンドラー"""
        error_id = _generate_error_id()
        _log_error(error, error_id, 500)

        internal_error = AppError(
            message="内部エラーが発生しました",
            code="INTERNAL_SERVER_ERROR",
            status_code=500,
            details={"error_id": error_id},
        )
        return handle_error(internal_error)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        """予期しないエラーのハンドラー"""
        error_id = _generate_error_id()
        _log_error(error, error_id, 500)

        # 既知のエラー型の場合はそのまま処理
        if isinstance(error, AppError):
            return handle_error(error)

        # 未知のエラーの場合は汎用エラーに変換
        unexpected_error = AppError(
            message="予期しないエラーが発生しました",
            code="UNEXPECTED_ERROR",
            status_code=500,
            details={"error_id": error_id, "error_type": type(error).__name__},
        )
        return handle_error(unexpected_error)
