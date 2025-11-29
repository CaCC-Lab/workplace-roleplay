"""
構造化ログ設定モジュール
JSON形式のログ出力とローテーション機能を提供
"""
import json
import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Any, Dict, Optional

from flask import Flask, g, has_request_context, request


class JSONFormatter(logging.Formatter):
    """JSON形式のログフォーマッター"""
    
    def __init__(self, include_timestamp: bool = True, include_extra: bool = True):
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """ログレコードをJSON形式にフォーマット"""
        log_data = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        if self.include_timestamp:
            log_data["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        # 位置情報
        log_data["location"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
        }
        
        # リクエストコンテキストがある場合
        if has_request_context():
            log_data["request"] = {
                "method": request.method,
                "path": request.path,
                "remote_addr": request.remote_addr,
            }
            if hasattr(g, "request_id"):
                log_data["request_id"] = g.request_id
        
        # 例外情報
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # 追加フィールド
        if self.include_extra and hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class ContextLogger(logging.LoggerAdapter):
    """コンテキスト情報を含めるロガーアダプター"""
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """ログメッセージにコンテキスト情報を追加"""
        extra = kwargs.get("extra", {})
        
        # リクエストコンテキストからの情報追加
        if has_request_context():
            extra["request_path"] = request.path
            extra["request_method"] = request.method
            if hasattr(g, "request_id"):
                extra["request_id"] = g.request_id
        
        kwargs["extra"] = extra
        return msg, kwargs


def setup_logging(
    app: Optional[Flask] = None,
    log_level: str = "INFO",
    log_format: str = "json",
    log_dir: str = "logs",
    app_name: str = "workplace-roleplay",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """
    ログ設定をセットアップ
    
    Args:
        app: Flaskアプリケーション（オプション）
        log_level: ログレベル
        log_format: ログフォーマット（'json' または 'text'）
        log_dir: ログディレクトリ
        app_name: アプリケーション名
        max_bytes: ローテーションのファイルサイズ上限
        backup_count: バックアップファイル数
        
    Returns:
        設定されたロガー
    """
    # ログディレクトリ作成
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # ルートロガー設定
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # 既存のハンドラをクリア
    root_logger.handlers.clear()
    
    # フォーマッター選択
    if log_format.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    # コンソールハンドラ
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # アプリケーションログ（サイズベースローテーション）
    app_log_path = os.path.join(log_dir, f"{app_name}.log")
    app_handler = RotatingFileHandler(
        app_log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    app_handler.setLevel(getattr(logging, log_level.upper()))
    app_handler.setFormatter(formatter)
    root_logger.addHandler(app_handler)
    
    # エラーログ（日付ベースローテーション）
    error_log_path = os.path.join(log_dir, f"{app_name}-error.log")
    error_handler = TimedRotatingFileHandler(
        error_log_path,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    # アクセスログ（日付ベースローテーション）
    access_log_path = os.path.join(log_dir, f"{app_name}-access.log")
    access_logger = logging.getLogger("access")
    access_handler = TimedRotatingFileHandler(
        access_log_path,
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8"
    )
    access_handler.setLevel(logging.INFO)
    access_handler.setFormatter(formatter)
    access_logger.addHandler(access_handler)
    
    # Flaskアプリケーションへの登録
    if app:
        app.logger.handlers = root_logger.handlers
        app.logger.setLevel(getattr(logging, log_level.upper()))
    
    return root_logger


def get_logger(name: str) -> ContextLogger:
    """
    コンテキスト付きロガーを取得
    
    Args:
        name: ロガー名
        
    Returns:
        ContextLogger インスタンス
    """
    return ContextLogger(logging.getLogger(name), {})


def log_request_info(response):
    """
    リクエスト情報をログに記録（ミドルウェア用）
    
    Args:
        response: Flaskレスポンスオブジェクト
        
    Returns:
        レスポンスオブジェクト
    """
    logger = get_logger("access")
    
    log_data = {
        "method": request.method,
        "path": request.path,
        "status_code": response.status_code,
        "user_agent": request.user_agent.string if request.user_agent else None,
    }
    
    # レスポンス時間
    if hasattr(g, "start_time"):
        import time
        log_data["response_time_ms"] = (time.perf_counter() - g.start_time) * 1000
    
    # リクエストID
    if hasattr(g, "request_id"):
        log_data["request_id"] = g.request_id
    
    logger.info(
        f"{request.method} {request.path} - {response.status_code}",
        extra={"extra_data": log_data}
    )
    
    return response


def log_exception(error: Exception, context: Optional[Dict[str, Any]] = None):
    """
    例外をログに記録
    
    Args:
        error: 例外オブジェクト
        context: 追加コンテキスト情報
    """
    logger = get_logger("error")
    
    log_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
    
    if context:
        log_data.update(context)
    
    if has_request_context():
        log_data["request_path"] = request.path
        log_data["request_method"] = request.method
    
    logger.error(
        f"Exception occurred: {type(error).__name__}: {str(error)}",
        exc_info=True,
        extra={"extra_data": log_data}
    )
