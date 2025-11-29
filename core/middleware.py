"""
Middleware module.
Handles CSRF protection, performance monitoring, and other request/response processing.
"""

import logging
import time

from flask import Flask, g, jsonify, request, session

# CSRF保護が必要なエンドポイントのリスト
CSRF_PROTECTED_ENDPOINTS = [
    "/api/clear_history",
    "/api/chat",
    "/api/scenario_chat",
    "/api/watch/start",
    "/api/watch/next",
    "/api/scenario_feedback",
    "/api/chat_feedback",
    "/api/start_chat",
    "/api/start_scenario",
    "/api/start_watch",
    "/api/session/clear",
]

# パフォーマンス計測対象外のエンドポイント
PERF_EXCLUDED_ENDPOINTS = [
    "/health",
    "/static/",
    "/flasgger_static/",
]


def register_middleware(app: Flask):
    """
    ミドルウェアをFlaskアプリケーションに登録

    Args:
        app: Flaskアプリケーションインスタンス
    """

    @app.before_request
    def start_timer():
        """リクエスト開始時間を記録"""
        g.start_time = time.perf_counter()

    @app.before_request
    def csrf_middleware():
        """CSRFミドルウェア - 保護されたエンドポイントでCSRF検証を行う"""
        # POSTリクエストかつ保護対象のエンドポイントの場合
        if request.method == "POST" and request.path in CSRF_PROTECTED_ENDPOINTS:
            try:
                from utils.security import CSRFToken

                # トークンの取得（ヘッダーまたはフォームから）
                token = (
                    request.headers.get("X-CSRF-Token")
                    or request.headers.get("X-CSRFToken")
                    or request.form.get("csrf_token")
                )

                # トークンの検証
                if not CSRFToken.validate(token, session):
                    # ロギング
                    logging.getLogger("utils.security").warning(
                        f"CSRF token validation failed for {request.path}"
                    )

                    return (
                        jsonify(
                            {
                                "error": "CSRF token validation failed",
                                "code": "CSRF_TOKEN_INVALID"
                                if token
                                else "CSRF_TOKEN_MISSING",
                            }
                        ),
                        403,
                    )
            except ImportError:
                # CSRFTokenクラスが存在しない場合はスキップ
                pass

    @app.after_request
    def record_metrics(response):
        """リクエスト完了時にメトリクスを記録"""
        # 除外対象のエンドポイントはスキップ
        if any(request.path.startswith(ep) for ep in PERF_EXCLUDED_ENDPOINTS):
            return response
        
        try:
            from utils.performance import get_metrics
            
            if hasattr(g, 'start_time'):
                duration_ms = (time.perf_counter() - g.start_time) * 1000
                metrics = get_metrics()
                metrics.record_request(
                    endpoint=request.path,
                    duration_ms=duration_ms,
                    status_code=response.status_code
                )
                
                # 遅いリクエストをログ
                if duration_ms > 1000:  # 1秒以上
                    logging.getLogger("performance").warning(
                        f"Slow request: {request.method} {request.path} "
                        f"took {duration_ms:.2f}ms"
                    )
        except ImportError:
            pass
        
        return response


def get_csrf_protected_endpoints():
    """
    CSRF保護対象のエンドポイントリストを取得

    Returns:
        list: 保護対象のエンドポイントパスのリスト
    """
    return CSRF_PROTECTED_ENDPOINTS.copy()


def add_csrf_protected_endpoint(endpoint: str):
    """
    CSRF保護対象のエンドポイントを追加

    Args:
        endpoint: 追加するエンドポイントパス
    """
    if endpoint not in CSRF_PROTECTED_ENDPOINTS:
        CSRF_PROTECTED_ENDPOINTS.append(endpoint)
