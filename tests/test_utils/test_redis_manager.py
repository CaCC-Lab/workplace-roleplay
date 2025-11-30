"""
Redis manager tests for improved coverage.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestRedisConnectionError:
    """RedisConnectionError例外のテスト"""

    def test_例外が定義されている(self):
        """RedisConnectionError例外が定義されている"""
        from utils.redis_manager import RedisConnectionError

        error = RedisConnectionError("接続エラー")
        assert str(error) == "接続エラー"


class TestRedisSessionManager:
    """RedisSessionManagerクラスのテスト"""

    def test_初期化_フォールバック有効(self):
        """フォールバック有効での初期化"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.side_effect = redis_module.ConnectionError("Connection failed")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(
                host="localhost",
                port=6379,
                fallback_enabled=True,
            )

            # フォールバックモードで継続
            assert manager.fallback_enabled is True
            assert manager._is_connected is False

    def test_初期化_フォールバック無効(self):
        """フォールバック無効での初期化（接続失敗時に例外）"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.side_effect = redis_module.ConnectionError("Connection failed")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager, RedisConnectionError

            with pytest.raises(RedisConnectionError):
                RedisSessionManager(
                    host="localhost",
                    port=6379,
                    fallback_enabled=False,
                )

    def test_接続成功(self):
        """接続成功のテスト"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(
                host="localhost",
                port=6379,
            )

            assert manager._is_connected is True


class TestFallbackOperations:
    """フォールバック操作のテスト"""

    def test_get_フォールバック(self):
        """getのフォールバック操作"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.side_effect = redis_module.ConnectionError("Connection failed")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(fallback_enabled=True)
            manager._fallback_storage["test_key"] = "test_value"

            result = manager.get("test_key")

            assert result == "test_value"

    def test_set_フォールバック(self):
        """setのフォールバック操作"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.side_effect = redis_module.ConnectionError("Connection failed")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(fallback_enabled=True)

            result = manager.set("test_key", "test_value")

            assert result is True
            assert manager._fallback_storage["test_key"] == "test_value"

    def test_delete_フォールバック(self):
        """deleteのフォールバック操作"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.side_effect = redis_module.ConnectionError("Connection failed")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(fallback_enabled=True)
            manager._fallback_storage["test_key"] = "test_value"

            result = manager.delete("test_key")

            assert result is True
            assert "test_key" not in manager._fallback_storage

    def test_exists_フォールバック(self):
        """existsのフォールバック操作"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.side_effect = redis_module.ConnectionError("Connection failed")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(fallback_enabled=True)
            manager._fallback_storage["existing_key"] = "value"

            assert manager.exists("existing_key") is True
            assert manager.exists("nonexistent_key") is False

    def test_clear_pattern_フォールバック(self):
        """clear_patternのフォールバック操作"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.side_effect = redis_module.ConnectionError("Connection failed")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(fallback_enabled=True)
            manager._fallback_storage["session:1"] = "value1"
            manager._fallback_storage["session:2"] = "value2"
            manager._fallback_storage["other:1"] = "value3"

            result = manager.clear_pattern("session")

            assert result == 2
            assert "session:1" not in manager._fallback_storage
            assert "session:2" not in manager._fallback_storage
            assert "other:1" in manager._fallback_storage


class TestRedisOperations:
    """Redis操作のテスト"""

    def test_get_JSON値(self):
        """JSON値のget操作"""
        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.get.return_value = '{"key": "value"}'
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager()
            result = manager.get("test_key")

            assert result == {"key": "value"}

    def test_get_非JSON値(self):
        """非JSON値のget操作"""
        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.get.return_value = "plain text"
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager()
            result = manager.get("test_key")

            assert result == "plain text"

    def test_get_存在しないキー(self):
        """存在しないキーのget操作"""
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
        """dict値のset操作"""
        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.set.return_value = True
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager()
            result = manager.set("test_key", {"key": "value"})

            assert result is True

    def test_set_expire付き(self):
        """expire付きのset操作"""
        with patch("utils.redis_manager.redis.Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.setex.return_value = True
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager()
            result = manager.set("test_key", "value", expire=3600)

            assert result is True
            mock_client.setex.assert_called_once()


class TestHealthCheck:
    """ヘルスチェックのテスト"""

    def test_接続成功時のヘルスチェック(self):
        """接続成功時のヘルスチェック"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager()
            health = manager.health_check()

            assert health["connected"] is True
            assert "info" in health

    def test_接続失敗時のヘルスチェック(self):
        """接続失敗時のヘルスチェック"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.side_effect = redis_module.ConnectionError("Connection failed")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(fallback_enabled=True)
            health = manager.health_check()

            assert health["connected"] is False
            assert health["fallback_active"] is True


class TestConnectionInfo:
    """接続情報のテスト"""

    def test_接続情報取得(self):
        """接続情報の取得"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.side_effect = redis_module.ConnectionError("Connection failed")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(fallback_enabled=True)
            info = manager.get_connection_info()

            assert "host" in info
            assert "port" in info
            assert "connected" in info
            assert "fallback_enabled" in info


class TestSessionConfig:
    """SessionConfigクラスのテスト"""

    def test_開発環境設定(self):
        """開発環境の設定取得"""
        from utils.redis_manager import SessionConfig

        config = SessionConfig.get_redis_config("development")

        assert config["SESSION_TYPE"] == "redis"
        assert config["SESSION_COOKIE_SECURE"] is False

    def test_本番環境設定(self):
        """本番環境の設定取得"""
        from utils.redis_manager import SessionConfig

        config = SessionConfig.get_redis_config("production")

        assert config["SESSION_TYPE"] == "redis"
        assert config["SESSION_COOKIE_SECURE"] is True

    def test_設定検証_成功(self):
        """設定検証の成功"""
        from utils.redis_manager import SessionConfig

        config = SessionConfig.get_redis_config()

        # 例外が発生しない
        SessionConfig.validate_config(config)

    def test_設定検証_失敗(self):
        """設定検証の失敗"""
        from utils.redis_manager import SessionConfig

        invalid_config = {"invalid": "config"}

        with pytest.raises(ValueError):
            SessionConfig.validate_config(invalid_config)


class TestHasFallback:
    """has_fallbackメソッドのテスト"""

    def test_フォールバック有効(self):
        """フォールバック有効の場合"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.side_effect = redis_module.ConnectionError("Connection failed")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(fallback_enabled=True)

            assert manager.has_fallback() is True


class TestRedisOperationsExtended:
    """Redis操作の拡張テスト"""

    def test_get_Redis例外時のエラー処理(self):
        """get操作時のRedis例外処理"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.get.side_effect = redis_module.RedisError("Redis error")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(fallback_enabled=True)

            # フォールバックに切り替わる
            result = manager.get("test_key")
            assert result is None

    def test_set_非dict非str値(self):
        """非dict/非str値のset操作"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.set.return_value = True
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager()
            result = manager.set("test_key", 12345)

            assert result is True

    def test_set_list値(self):
        """list値のset操作"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.set.return_value = True
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager()
            result = manager.set("test_key", [1, 2, 3])

            assert result is True

    def test_set_Redis例外時のエラー処理(self):
        """set操作時のRedis例外処理"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.set.side_effect = redis_module.RedisError("Redis error")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(fallback_enabled=True)

            # フォールバックに切り替わる
            result = manager.set("test_key", "value")
            assert result is True

    def test_delete_Redis例外時のエラー処理(self):
        """delete操作時のRedis例外処理"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.delete.side_effect = redis_module.RedisError("Redis error")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(fallback_enabled=True)
            manager._fallback_storage["test_key"] = "value"

            # フォールバックに切り替わる
            result = manager.delete("test_key")
            assert result is True

    def test_exists_Redis例外時のfalse返却(self):
        """exists操作時のRedis例外処理"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.exists.side_effect = redis_module.RedisError("Redis error")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(fallback_enabled=True)

            # フォールバックに切り替わる
            result = manager.exists("test_key")
            # フォールバックストレージには存在しないのでFalse
            assert result is False

    def test_clear_pattern_空パターン(self):
        """clear_patternで該当なしの場合"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.keys.return_value = []
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager()
            result = manager.clear_pattern("nonexistent:*")

            assert result == 0

    def test_clear_pattern_Redis例外時(self):
        """clear_pattern操作時のRedis例外処理"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client.keys.side_effect = redis_module.RedisError("Redis error")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(fallback_enabled=True)

            # フォールバックに切り替わる
            result = manager.clear_pattern("session:*")
            assert result == 0


class TestFormatConnectionError:
    """_format_connection_errorメソッドのテスト"""

    def test_エラーメッセージフォーマット(self):
        """エラーメッセージのフォーマット確認"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.side_effect = redis_module.ConnectionError("Connection refused")
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager(fallback_enabled=True)

            # _format_connection_errorを直接テスト
            error_msg = manager._format_connection_error("test error")

            assert "Redisサーバーに接続できません" in error_msg
            assert "test error" in error_msg
            assert "対処法" in error_msg


class TestLogRedisError:
    """_log_redis_errorメソッドのテスト"""

    def test_エラーログ出力(self):
        """エラーログの出力確認"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager

            manager = RedisSessionManager()

            with patch("utils.redis_manager.logger") as mock_logger:
                manager._log_redis_error("テスト操作", "詳細エラー")

                mock_logger.error.assert_called_once()
                call_args = mock_logger.error.call_args[0][0]
                assert "テスト操作" in call_args
                assert "詳細エラー" in call_args


class TestWithFallbackDecorator:
    """_with_fallbackデコレータのテスト"""

    def test_フォールバック無効時の例外(self):
        """フォールバック無効で接続なしの場合に例外"""
        import redis as redis_module

        with patch.object(redis_module, "Redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_redis.return_value = mock_client

            from utils.redis_manager import RedisSessionManager, RedisConnectionError

            manager = RedisSessionManager(fallback_enabled=False)
            manager._is_connected = False

            with pytest.raises(RedisConnectionError):
                manager.get("test_key")


class TestSessionConfigExtended:
    """SessionConfigの拡張テスト"""

    def test_デフォルト環境設定(self):
        """デフォルト環境の設定取得"""
        from utils.redis_manager import SessionConfig

        with patch.dict("os.environ", {"FLASK_ENV": "staging"}):
            config = SessionConfig.get_redis_config()

            assert config["SESSION_TYPE"] == "redis"

    def test_セキュアクッキー警告(self):
        """開発環境でセキュアクッキーが有効な場合の警告"""
        from utils.redis_manager import SessionConfig

        with patch.dict("os.environ", {"FLASK_ENV": "development"}):
            config = {"SESSION_TYPE": "redis", "SESSION_USE_SIGNER": True, "SESSION_KEY_PREFIX": "test:", "SESSION_COOKIE_SECURE": True}

            with patch("utils.redis_manager.logger") as mock_logger:
                SessionConfig.validate_config(config)

                mock_logger.warning.assert_called_once()
