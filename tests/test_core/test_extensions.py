"""
Core extensions tests for improved coverage.
"""

import pytest
import os
from unittest.mock import MagicMock, patch
from flask import Flask


class TestInitExtensions:
    """init_extensions関数のテスト"""

    def test_configなしで初期化(self):
        """configなしでデフォルト設定で初期化"""
        from core.extensions import init_extensions

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test-secret"

        with patch("core.extensions._initialize_session_store") as mock_init:
            mock_init.return_value = None

            result = init_extensions(app)

            assert mock_init.called

    def test_config指定で初期化(self):
        """config指定で初期化"""
        from core.extensions import init_extensions

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test-secret"
        mock_config = MagicMock()
        mock_config.SESSION_TYPE = "filesystem"

        with patch("core.extensions._initialize_session_store") as mock_init:
            mock_init.return_value = None

            result = init_extensions(app, config=mock_config)

            mock_init.assert_called_once_with(app, mock_config)


class TestInitializeSessionStore:
    """_initialize_session_store関数のテスト"""

    def test_filesystemセッションの初期化(self):
        """Filesystemセッションの初期化"""
        from core.extensions import _initialize_session_store

        app = Flask(__name__)
        mock_config = MagicMock()
        mock_config.SESSION_TYPE = "filesystem"
        mock_config.SESSION_FILE_DIR = "./test_session"

        with patch("core.extensions._setup_filesystem_session") as mock_fs:
            mock_fs.return_value = None

            result = _initialize_session_store(app, mock_config)

            mock_fs.assert_called_once()

    def test_Redis接続成功(self):
        """Redis接続成功時の初期化"""
        from core.extensions import _initialize_session_store

        app = Flask(__name__)
        mock_config = MagicMock()
        mock_config.SESSION_TYPE = "redis"
        mock_config.REDIS_HOST = "localhost"
        mock_config.REDIS_PORT = 6379
        mock_config.REDIS_DB = 0

        mock_redis_manager = MagicMock()
        mock_redis_manager.health_check.return_value = {"connected": True}
        mock_redis_manager.host = "localhost"
        mock_redis_manager.port = 6379
        mock_redis_manager._client = MagicMock()

        with patch("core.extensions.RedisSessionManager") as mock_class:
            mock_class.return_value = mock_redis_manager
            with patch("core.extensions.SessionConfig.get_redis_config") as mock_redis_config:
                mock_redis_config.return_value = {"SESSION_TYPE": "redis"}

                result = _initialize_session_store(app, mock_config)

                assert result == mock_redis_manager

    def test_Redis接続失敗_フォールバック有効(self):
        """Redis接続失敗時のフォールバック"""
        from core.extensions import _initialize_session_store

        app = Flask(__name__)
        mock_config = MagicMock()
        mock_config.SESSION_TYPE = "redis"
        mock_config.REDIS_HOST = "localhost"
        mock_config.REDIS_PORT = 6379
        mock_config.REDIS_DB = 0

        mock_redis_manager = MagicMock()
        mock_redis_manager.health_check.return_value = {
            "connected": False,
            "error": "Connection refused",
        }
        mock_redis_manager.has_fallback.return_value = True

        with patch("core.extensions.RedisSessionManager") as mock_class:
            mock_class.return_value = mock_redis_manager

            result = _initialize_session_store(app, mock_config)

            assert result == mock_redis_manager

    def test_Redis接続失敗_フォールバック無効(self):
        """Redis接続失敗でフォールバックも無効な場合"""
        from core.extensions import _initialize_session_store, RedisConnectionError

        app = Flask(__name__)
        mock_config = MagicMock()
        mock_config.SESSION_TYPE = "redis"
        mock_config.REDIS_HOST = "localhost"
        mock_config.REDIS_PORT = 6379
        mock_config.REDIS_DB = 0

        mock_redis_manager = MagicMock()
        mock_redis_manager.health_check.return_value = {
            "connected": False,
            "error": "Connection refused",
        }
        mock_redis_manager.has_fallback.return_value = False

        with patch("core.extensions.RedisSessionManager") as mock_class:
            mock_class.return_value = mock_redis_manager
            with patch("core.extensions._setup_filesystem_session") as mock_fs:
                mock_fs.return_value = None

                # RedisConnectionErrorが発生してもフォールバックする
                result = _initialize_session_store(app, mock_config)

                # エラー発生後、filesystemにフォールバック
                mock_fs.assert_called()

    def test_ImportError発生時(self):
        """ImportError発生時のフォールバック"""
        from core.extensions import _initialize_session_store

        app = Flask(__name__)
        mock_config = MagicMock()
        mock_config.SESSION_TYPE = "redis"

        with patch("core.extensions.RedisSessionManager") as mock_class:
            mock_class.side_effect = ImportError("redis not found")
            with patch("core.extensions._setup_filesystem_session") as mock_fs:
                mock_fs.return_value = None

                result = _initialize_session_store(app, mock_config)

                mock_fs.assert_called_once()

    def test_一般的なException発生時(self):
        """一般的なException発生時のフォールバック"""
        from core.extensions import _initialize_session_store

        app = Flask(__name__)
        mock_config = MagicMock()
        mock_config.SESSION_TYPE = "redis"

        with patch("core.extensions.RedisSessionManager") as mock_class:
            mock_class.side_effect = Exception("Unexpected error")
            with patch("core.extensions._setup_filesystem_session") as mock_fs:
                mock_fs.return_value = None

                result = _initialize_session_store(app, mock_config)

                mock_fs.assert_called_once()


class TestSetupFilesystemSession:
    """_setup_filesystem_session関数のテスト"""

    def test_セッションディレクトリ作成(self):
        """セッションディレクトリの作成"""
        from core.extensions import _setup_filesystem_session

        app = Flask(__name__)
        mock_config = MagicMock()
        mock_config.SESSION_FILE_DIR = "./test_session_dir"

        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = False
            with patch("os.makedirs") as mock_makedirs:
                result = _setup_filesystem_session(app, mock_config)

                assert result is None
                assert app.config["SESSION_TYPE"] == "filesystem"

    def test_ディレクトリ作成失敗時のフォールバック(self):
        """ディレクトリ作成失敗時のフォールバック"""
        from core.extensions import _setup_filesystem_session

        app = Flask(__name__)
        mock_config = MagicMock()
        mock_config.SESSION_FILE_DIR = "/invalid/path"

        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = False
            with patch("os.makedirs") as mock_makedirs:
                # 最初の呼び出しで失敗、2回目は成功
                mock_makedirs.side_effect = [PermissionError("Permission denied"), None]

                result = _setup_filesystem_session(app, mock_config)

                assert result is None
                # フォールバックディレクトリに変更
                assert app.config["SESSION_FILE_DIR"] == "./flask_session"

    def test_SESSION_FILE_DIRがNoneの場合(self):
        """SESSION_FILE_DIRがNoneの場合のデフォルト値"""
        from core.extensions import _setup_filesystem_session

        app = Flask(__name__)
        mock_config = MagicMock()
        mock_config.SESSION_FILE_DIR = None

        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True

            result = _setup_filesystem_session(app, mock_config)

            assert app.config["SESSION_FILE_DIR"] == "./flask_session"


class TestGetRedisSessionManager:
    """get_redis_session_manager関数のテスト"""

    def test_マネージャー取得(self):
        """Redisセッションマネージャーの取得"""
        from core import extensions
        from core.extensions import get_redis_session_manager

        # グローバル変数を設定
        mock_manager = MagicMock()
        extensions.redis_session_manager = mock_manager

        result = get_redis_session_manager()

        assert result == mock_manager

        # クリーンアップ
        extensions.redis_session_manager = None

    def test_マネージャーがNoneの場合(self):
        """マネージャーがNoneの場合"""
        from core import extensions
        from core.extensions import get_redis_session_manager

        extensions.redis_session_manager = None

        result = get_redis_session_manager()

        assert result is None
