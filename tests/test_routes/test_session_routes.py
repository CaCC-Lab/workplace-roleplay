"""
Session routes tests for improved coverage.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestSessionHealthCheck:
    """GET /api/session/health のテスト"""

    def test_Redisセッション健全性チェック(self, client):
        """Redisセッションの健全性チェック"""
        with patch("core.extensions.get_redis_session_manager") as mock_get:
            mock_manager = MagicMock()
            mock_manager.health_check.return_value = {
                "connected": True,
                "fallback_active": False,
            }
            mock_manager.get_connection_info.return_value = {
                "host": "localhost",
                "port": 6379,
            }
            mock_get.return_value = mock_manager

            response = client.get("/api/session/health")

            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "healthy"
            assert data["session_store"] == "redis"

    def test_Redisフォールバック時の健全性チェック(self, client):
        """Redisフォールバック時の健全性チェック"""
        with patch("core.extensions.get_redis_session_manager") as mock_get:
            mock_manager = MagicMock()
            mock_manager.health_check.return_value = {
                "connected": False,
                "fallback_active": True,
                "error": "Connection refused",
            }
            mock_manager.get_connection_info.return_value = {}
            mock_get.return_value = mock_manager

            response = client.get("/api/session/health")

            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "degraded"
            assert data["session_store"] == "fallback"

    def test_ファイルシステムセッションの健全性チェック(self, client):
        """ファイルシステムセッションの健全性チェック"""
        with patch("core.extensions.get_redis_session_manager") as mock_get:
            mock_get.return_value = None

            response = client.get("/api/session/health")

            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "healthy"
            assert data["session_store"] == "filesystem"

    def test_健全性チェックでエラー発生時(self, client):
        """健全性チェックでエラーが発生した場合"""
        with patch("core.extensions.get_redis_session_manager") as mock_get:
            mock_get.side_effect = Exception("Connection error")

            response = client.get("/api/session/health")

            assert response.status_code == 500
            data = response.get_json()
            assert "error" in data


class TestSessionInfo:
    """GET /api/session/info のテスト"""

    def test_セッション情報を取得(self, client):
        """セッション情報の取得"""
        with client.session_transaction() as sess:
            sess["chat_history"] = [{"human": "test", "ai": "response"}]
            sess["model_choice"] = "gemini-1.5-flash"

        response = client.get("/api/session/info")

        assert response.status_code == 200
        data = response.get_json()
        assert "session_keys" in data
        assert "session_type" in data
        assert data["has_chat_history"] is True

    def test_空のセッション情報を取得(self, client):
        """空のセッションの情報取得"""
        response = client.get("/api/session/info")

        assert response.status_code == 200
        data = response.get_json()
        assert "session_keys" in data
        assert "estimated_size_bytes" in data


class TestClearSessionData:
    """POST /api/session/clear のテスト"""

    def test_全セッションデータをクリア(self, csrf_client):
        """全セッションデータのクリア"""
        with csrf_client.session_transaction() as sess:
            sess["chat_history"] = [{"human": "test", "ai": "response"}]
            sess["scenario_chat_history"] = [{"human": "test", "ai": "response"}]
            sess["watch_history"] = [{"speaker": "A", "message": "test"}]

        response = csrf_client.post("/api/session/clear", json={"type": "all"})

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert data["cleared_type"] == "all"

    def test_チャット履歴のみクリア(self, csrf_client):
        """チャット履歴のみクリア"""
        with csrf_client.session_transaction() as sess:
            sess["chat_history"] = [{"human": "test", "ai": "response"}]
            sess["scenario_chat_history"] = [{"human": "test", "ai": "response"}]

        response = csrf_client.post("/api/session/clear", json={"type": "chat"})

        assert response.status_code == 200
        data = response.get_json()
        assert data["cleared_type"] == "chat"

        # チャット履歴がクリアされていることを確認
        with csrf_client.session_transaction() as sess:
            assert "chat_history" not in sess
            # シナリオ履歴は残っている
            assert "scenario_chat_history" in sess

    def test_シナリオ履歴のみクリア(self, csrf_client):
        """シナリオ履歴のみクリア"""
        with csrf_client.session_transaction() as sess:
            sess["chat_history"] = [{"human": "test", "ai": "response"}]
            sess["scenario_chat_history"] = [{"human": "test", "ai": "response"}]
            sess["current_scenario_id"] = "scenario1"

        response = csrf_client.post("/api/session/clear", json={"type": "scenario"})

        assert response.status_code == 200
        data = response.get_json()
        assert data["cleared_type"] == "scenario"

    def test_観戦履歴のみクリア(self, csrf_client):
        """観戦履歴のみクリア"""
        with csrf_client.session_transaction() as sess:
            sess["watch_history"] = [{"speaker": "A", "message": "test"}]

        response = csrf_client.post("/api/session/clear", json={"type": "watch"})

        assert response.status_code == 200
        data = response.get_json()
        assert data["cleared_type"] == "watch"

    def test_無効なクリアタイプでエラー(self, csrf_client):
        """無効なクリアタイプでエラー"""
        response = csrf_client.post("/api/session/clear", json={"type": "invalid"})

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_JSONなしでデフォルトタイプを使用(self, csrf_client):
        """JSONなしの場合はデフォルトでallを使用"""
        response = csrf_client.post("/api/session/clear", json={})

        assert response.status_code == 200
        data = response.get_json()
        assert data["cleared_type"] == "all"
