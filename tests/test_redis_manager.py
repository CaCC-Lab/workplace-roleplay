"""
Redis manager tests for improved coverage.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
import json


class TestRedisSessionManager:
    """RedisSessionManagerクラスのテスト"""

    def test_初期化_デフォルト値(self):
        """デフォルト値での初期化"""
        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager()

            assert manager.host == "localhost"
            assert manager.port == 6379
            assert manager.db == 0
            assert manager.fallback_enabled is True

    def test_初期化_カスタム値(self):
        """カスタム値での初期化"""
        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(
                host="custom-host",
                port=6380,
                db=1,
                fallback_enabled=False,
            )

            assert manager.host == "custom-host"
            assert manager.port == 6380
            assert manager.db == 1

    def test_接続成功(self):
        """Redis接続成功"""
        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager()

            assert manager._is_connected is True

    def test_接続失敗_フォールバック有効(self):
        """接続失敗時のフォールバック"""
        import redis

        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.side_effect = redis.ConnectionError("Connection refused")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(fallback_enabled=True)

            assert manager._is_connected is False
            assert manager.fallback_enabled is True

    def test_接続失敗_フォールバック無効(self):
        """接続失敗でフォールバックも無効"""
        import redis

        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.side_effect = redis.ConnectionError("Connection refused")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager, RedisConnectionError

            with pytest.raises(RedisConnectionError):
                RedisSessionManager(fallback_enabled=False)

    def test_get_接続時(self):
        """Redis接続時のget操作"""
        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.get.return_value = '{"key": "value"}'
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager()
            result = manager.get("test_key")

            assert result == {"key": "value"}

    def test_get_JSON以外の値(self):
        """JSON以外の値のget"""
        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.get.return_value = "plain text"
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager()
            result = manager.get("test_key")

            assert result == "plain text"

    def test_get_値なし(self):
        """存在しないキーのget"""
        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.get.return_value = None
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager()
            result = manager.get("nonexistent")

            assert result is None

    def test_set_dict値(self):
        """dict値のset"""
        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.set.return_value = True
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager()
            result = manager.set("test_key", {"key": "value"})

            assert result is True

    def test_set_有効期限付き(self):
        """有効期限付きのset"""
        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.setex.return_value = True
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager()
            result = manager.set("test_key", "value", expire=3600)

            assert result is True
            mock_client.setex.assert_called()

    def test_delete(self):
        """キーの削除"""
        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.delete.return_value = 1
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager()
            result = manager.delete("test_key")

            assert result is True

    def test_exists(self):
        """キーの存在確認"""
        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.exists.return_value = 1
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager()
            result = manager.exists("test_key")

            assert result is True

    def test_clear_pattern(self):
        """パターンに一致するキーの削除"""
        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.keys.return_value = ["key1", "key2"]
            mock_client.delete.return_value = 2
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager()
            result = manager.clear_pattern("key*")

            assert result == 2

    def test_health_check_接続時(self):
        """接続時のヘルスチェック"""
        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager()
            result = manager.health_check()

            assert result["connected"] is True
            assert "info" in result

    def test_health_check_切断時(self):
        """切断時のヘルスチェック"""
        import redis

        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.side_effect = redis.ConnectionError("Not connected")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(fallback_enabled=True)
            result = manager.health_check()

            assert result["connected"] is False

    def test_has_fallback(self):
        """フォールバック機能の確認"""
        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(fallback_enabled=True)

            assert manager.has_fallback() is True

    def test_get_connection_info(self):
        """接続情報の取得"""
        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager()
            result = manager.get_connection_info()

            assert "host" in result
            assert "port" in result
            assert "connected" in result

    def test_フォールバック操作_get(self):
        """フォールバック操作 - get"""
        import redis

        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.side_effect = redis.ConnectionError("Not connected")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(fallback_enabled=True)
            manager._fallback_storage["test_key"] = "test_value"

            result = manager.get("test_key")

            assert result == "test_value"

    def test_フォールバック操作_set(self):
        """フォールバック操作 - set"""
        import redis

        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.side_effect = redis.ConnectionError("Not connected")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(fallback_enabled=True)
            result = manager.set("new_key", "new_value")

            assert result is True
            assert manager._fallback_storage["new_key"] == "new_value"

    def test_フォールバック操作_delete(self):
        """フォールバック操作 - delete"""
        import redis

        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.side_effect = redis.ConnectionError("Not connected")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(fallback_enabled=True)
            manager._fallback_storage["to_delete"] = "value"

            result = manager.delete("to_delete")

            assert result is True
            assert "to_delete" not in manager._fallback_storage

    def test_フォールバック操作_exists(self):
        """フォールバック操作 - exists"""
        import redis

        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.side_effect = redis.ConnectionError("Not connected")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(fallback_enabled=True)
            manager._fallback_storage["existing"] = "value"

            result = manager.exists("existing")

            assert result is True

    def test_フォールバック操作_clear_pattern(self):
        """フォールバック操作 - clear_pattern"""
        import redis

        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.side_effect = redis.ConnectionError("Not connected")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(fallback_enabled=True)
            manager._fallback_storage["test:1"] = "value1"
            manager._fallback_storage["test:2"] = "value2"
            manager._fallback_storage["other"] = "value3"

            result = manager.clear_pattern("test")

            assert result == 2


class TestSessionConfig:
    """SessionConfigクラスのテスト"""

    def test_開発環境設定取得(self):
        """開発環境の設定取得"""
        from utils.redis_manager import SessionConfig

        config = SessionConfig.get_redis_config("development")

        assert config["SESSION_TYPE"] == "redis"
        assert config["SESSION_COOKIE_SECURE"] is False

    def test_本番環境設定取得(self):
        """本番環境の設定取得"""
        from utils.redis_manager import SessionConfig

        config = SessionConfig.get_redis_config("production")

        assert config["SESSION_TYPE"] == "redis"
        assert config["SESSION_COOKIE_SECURE"] is True

    def test_設定検証_成功(self):
        """設定検証成功"""
        from utils.redis_manager import SessionConfig

        config = SessionConfig.get_redis_config()

        # 例外が発生しなければ成功
        SessionConfig.validate_config(config)

    def test_設定検証_必須キー不足(self):
        """必須キーが不足している場合"""
        from utils.redis_manager import SessionConfig

        config = {"SESSION_TYPE": "redis"}

        with pytest.raises(ValueError) as exc_info:
            SessionConfig.validate_config(config)

        assert "必須設定項目が不足しています" in str(exc_info.value)

    def test_設定検証_開発環境でセキュアクッキー(self):
        """開発環境でセキュアクッキーが有効な場合の警告"""
        from utils.redis_manager import SessionConfig

        config = {
            "SESSION_TYPE": "redis",
            "SESSION_USE_SIGNER": True,
            "SESSION_KEY_PREFIX": "test:",
            "SESSION_COOKIE_SECURE": True,
        }

        with patch.dict("os.environ", {"FLASK_ENV": "development"}):
            # 警告は出るが例外は発生しない
            SessionConfig.validate_config(config)


class TestRedisConnectionError:
    """RedisConnectionError例外のテスト"""

    def test_例外作成(self):
        """例外の作成"""
        from utils.redis_manager import RedisConnectionError

        exc = RedisConnectionError("Connection failed")

        assert str(exc) == "Connection failed"
