"""
Logging configuration tests for improved coverage.
"""

import pytest
import logging
import json
import os
import tempfile
from unittest.mock import patch, MagicMock
from flask import Flask, g


@pytest.fixture
def app():
    """テスト用Flaskアプリケーション"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["TESTING"] = True
    return app


@pytest.fixture
def temp_log_dir():
    """一時ログディレクトリ"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestJSONFormatter:
    """JSONFormatterクラスのテスト"""

    def test_基本的なフォーマット(self):
        """基本的なログフォーマット"""
        from utils.logging_config import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert "timestamp" in data

    def test_タイムスタンプなし(self):
        """タイムスタンプを含めない"""
        from utils.logging_config import JSONFormatter

        formatter = JSONFormatter(include_timestamp=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert "timestamp" not in data

    def test_リクエストコンテキストあり(self, app):
        """リクエストコンテキスト情報を含む"""
        from utils.logging_config import JSONFormatter

        formatter = JSONFormatter()

        with app.test_request_context("/test-path"):
            g.request_id = "test-request-id"

            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            result = formatter.format(record)
            data = json.loads(result)

            assert "request" in data
            assert data["request"]["path"] == "/test-path"
            assert data["request_id"] == "test-request-id"

    def test_例外情報を含む(self):
        """例外情報を含む"""
        from utils.logging_config import JSONFormatter

        formatter = JSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert "exception" in data
        assert "ValueError" in data["exception"]

    def test_extra_dataを含む(self):
        """追加フィールドを含む"""
        from utils.logging_config import JSONFormatter

        formatter = JSONFormatter(include_extra=True)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.extra_data = {"custom_field": "custom_value"}

        result = formatter.format(record)
        data = json.loads(result)

        assert "extra" in data
        assert data["extra"]["custom_field"] == "custom_value"


class TestContextLogger:
    """ContextLoggerクラスのテスト"""

    def test_基本的なログ処理(self):
        """基本的なログ処理"""
        from utils.logging_config import ContextLogger

        base_logger = logging.getLogger("test_context")
        logger = ContextLogger(base_logger, {})

        msg, kwargs = logger.process("Test message", {})

        assert msg == "Test message"
        assert "extra" in kwargs

    def test_リクエストコンテキストあり(self, app):
        """リクエストコンテキスト情報を追加"""
        from utils.logging_config import ContextLogger

        base_logger = logging.getLogger("test_context_req")
        logger = ContextLogger(base_logger, {})

        with app.test_request_context("/api/test"):
            g.request_id = "req-123"

            msg, kwargs = logger.process("Test message", {})

            assert kwargs["extra"]["request_path"] == "/api/test"
            assert kwargs["extra"]["request_method"] == "GET"
            assert kwargs["extra"]["request_id"] == "req-123"


class TestSetupLogging:
    """setup_logging関数のテスト"""

    def test_基本的なセットアップ(self, temp_log_dir):
        """基本的なログセットアップ"""
        from utils.logging_config import setup_logging

        logger = setup_logging(
            log_level="DEBUG",
            log_format="json",
            log_dir=temp_log_dir,
            app_name="test-app",
        )

        assert logger is not None
        assert len(logger.handlers) >= 2  # コンソール + ファイル

    def test_テキストフォーマット(self, temp_log_dir):
        """テキストフォーマットでのセットアップ"""
        from utils.logging_config import setup_logging

        logger = setup_logging(
            log_level="INFO",
            log_format="text",
            log_dir=temp_log_dir,
            app_name="test-app-text",
        )

        assert logger is not None

    def test_Flaskアプリケーション連携(self, app, temp_log_dir):
        """Flaskアプリケーションとの連携"""
        from utils.logging_config import setup_logging

        logger = setup_logging(
            app=app,
            log_level="INFO",
            log_format="json",
            log_dir=temp_log_dir,
            app_name="test-flask-app",
        )

        assert app.logger.level == logging.INFO

    def test_ログディレクトリ作成(self, temp_log_dir):
        """ログディレクトリの自動作成"""
        from utils.logging_config import setup_logging

        new_log_dir = os.path.join(temp_log_dir, "new_logs")

        logger = setup_logging(
            log_dir=new_log_dir,
            app_name="test-new-dir",
        )

        assert os.path.exists(new_log_dir)


class TestGetLogger:
    """get_logger関数のテスト"""

    def test_ロガー取得(self):
        """ロガーの取得"""
        from utils.logging_config import get_logger, ContextLogger

        logger = get_logger("test_module")

        assert isinstance(logger, ContextLogger)


class TestLogRequestInfo:
    """log_request_info関数のテスト"""

    def test_リクエスト情報ログ(self, app):
        """リクエスト情報のログ記録"""
        from utils.logging_config import log_request_info

        with app.test_request_context("/api/test"):
            import time

            g.start_time = time.perf_counter()
            g.request_id = "test-req-id"

            response = MagicMock()
            response.status_code = 200

            result = log_request_info(response)

            assert result == response

    def test_リクエスト情報ログ_start_timeなし(self, app):
        """start_timeがない場合"""
        from utils.logging_config import log_request_info

        with app.test_request_context("/api/test"):
            response = MagicMock()
            response.status_code = 200

            result = log_request_info(response)

            assert result == response


class TestLogException:
    """log_exception関数のテスト"""

    def test_例外ログ(self, app):
        """例外のログ記録"""
        from utils.logging_config import log_exception

        with app.test_request_context("/api/error"):
            error = ValueError("Test error")

            # エラーなしで実行されることを確認
            log_exception(error)

    def test_例外ログ_コンテキスト付き(self, app):
        """コンテキスト付き例外ログ"""
        from utils.logging_config import log_exception

        with app.test_request_context("/api/error"):
            error = RuntimeError("Runtime error")
            context = {"user_id": "123", "action": "test"}

            log_exception(error, context)

    def test_例外ログ_リクエストコンテキストなし(self):
        """リクエストコンテキストなしでの例外ログ"""
        from utils.logging_config import log_exception

        error = Exception("General error")

        # リクエストコンテキストなしでも動作
        log_exception(error)
