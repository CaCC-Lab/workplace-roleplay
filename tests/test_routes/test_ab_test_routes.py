"""
A/B test routes tests for improved coverage.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from flask import Flask


@pytest.fixture
def app():
    """テスト用Flaskアプリケーション"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    from routes.ab_test_routes import ab_test_bp

    app.register_blueprint(ab_test_bp)

    return app


@pytest.fixture
def client(app):
    """テストクライアント"""
    return app.test_client()


class TestGetServices:
    """get_services関数のテスト"""

    def test_サービス取得(self):
        """サービスインスタンスの取得"""
        from routes.ab_test_routes import get_services

        with patch("routes.ab_test_routes.LLMService") as mock_llm:
            with patch("routes.ab_test_routes.SessionService") as mock_session:
                with patch("routes.ab_test_routes.ChatService") as mock_chat:
                    # グローバル変数をリセット
                    import routes.ab_test_routes

                    routes.ab_test_routes._chat_service = None
                    routes.ab_test_routes._session_service = None
                    routes.ab_test_routes._llm_service = None

                    chat, session, llm = get_services()

                    assert mock_llm.called
                    assert mock_session.called
                    assert mock_chat.called


class TestChatV2:
    """chat_v2エンドポイントのテスト"""

    def test_空メッセージ(self, app, client):
        """空のメッセージでリクエスト"""
        with patch("routes.ab_test_routes.CSRFProtection.require_csrf") as mock_csrf:
            mock_csrf.return_value = lambda f: f

            with patch("routes.ab_test_routes.rate_limiter.rate_limit") as mock_rate:
                mock_rate.return_value = lambda f: f

                response = client.post(
                    "/api/v2/chat",
                    json={"message": "", "model": "gemini-1.5-flash"},
                )

                assert response.status_code in [400, 403, 429]


class TestChatCompare:
    """chat_compareエンドポイントのテスト"""

    def test_空メッセージ(self, app, client):
        """空のメッセージでの比較"""
        with patch("routes.ab_test_routes.CSRFProtection.require_csrf") as mock_csrf:
            mock_csrf.return_value = lambda f: f

            response = client.post(
                "/api/v2/chat/compare",
                json={"message": ""},
            )

            assert response.status_code in [400, 403]


class TestGetABConfig:
    """get_ab_configエンドポイントのテスト"""

    def test_設定取得(self, client):
        """A/Bテスト設定の取得"""
        response = client.get("/api/v2/config")

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)


class TestHealthCheck:
    """health_checkエンドポイントのテスト"""

    def test_ヘルスチェック成功(self, client):
        """ヘルスチェックの成功"""
        with patch("routes.ab_test_routes.get_services") as mock_services:
            mock_services.return_value = (MagicMock(), MagicMock(), MagicMock())

            response = client.get("/api/v2/health")

            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "healthy"
            assert "services" in data
            assert "feature_flags" in data

    def test_ヘルスチェック失敗(self, client):
        """ヘルスチェックの失敗"""
        with patch("routes.ab_test_routes.get_services") as mock_services:
            mock_services.side_effect = Exception("Service error")

            response = client.get("/api/v2/health")

            assert response.status_code == 500
            data = response.get_json()
            assert data["status"] == "unhealthy"


class TestScenarioChatV2:
    """scenario_chat_v2エンドポイントのテスト"""

    def test_未実装レスポンス(self, client):
        """未実装のレスポンス"""
        response = client.post("/api/v2/scenario_chat", json={})

        assert response.status_code == 501
        data = response.get_json()
        assert "Coming soon" in data["message"]


class TestWatchStartV2:
    """watch_start_v2エンドポイントのテスト"""

    def test_未実装レスポンス(self, client):
        """未実装のレスポンス"""
        response = client.post("/api/v2/watch/start", json={})

        assert response.status_code == 501
        data = response.get_json()
        assert "Coming soon" in data["message"]


class TestChatV2Extended:
    """chat_v2エンドポイントの拡張テスト"""

    def test_例外発生時のエラーハンドリング(self, app, client):
        """例外発生時のエラーハンドリング"""
        with patch("routes.ab_test_routes.CSRFProtection.require_csrf") as mock_csrf:
            mock_csrf.return_value = lambda f: f

            with patch("routes.ab_test_routes.rate_limiter.rate_limit") as mock_rate:
                mock_rate.return_value = lambda f: f

                with patch("routes.ab_test_routes.get_services") as mock_services:
                    mock_services.side_effect = Exception("Service error")

                    response = client.post(
                        "/api/v2/chat",
                        json={"message": "テスト", "model": "gemini-1.5-flash"},
                    )

                    # エラーハンドリング
                    assert response.status_code in [403, 429, 500]


class TestChatCompareExtended:
    """chat_compareエンドポイントの拡張テスト"""

    def test_例外発生時のエラーハンドリング(self, app, client):
        """例外発生時のエラーハンドリング"""
        with patch("routes.ab_test_routes.CSRFProtection.require_csrf") as mock_csrf:
            mock_csrf.return_value = lambda f: f

            with patch("routes.ab_test_routes.get_services") as mock_services:
                mock_services.side_effect = Exception("Service error")

                response = client.post(
                    "/api/v2/chat/compare",
                    json={"message": "テスト"},
                )

                assert response.status_code in [403, 500]



class TestGetServicesExtended:
    """get_services関数の拡張テスト"""

    def test_シングルトンパターン(self):
        """サービスがシングルトンとして動作"""
        import routes.ab_test_routes

        # グローバル変数をリセット
        routes.ab_test_routes._chat_service = None
        routes.ab_test_routes._session_service = None
        routes.ab_test_routes._llm_service = None

        with patch("routes.ab_test_routes.LLMService") as mock_llm:
            with patch("routes.ab_test_routes.SessionService") as mock_session:
                with patch("routes.ab_test_routes.ChatService") as mock_chat:
                    from routes.ab_test_routes import get_services

                    # 1回目の呼び出し
                    chat1, session1, llm1 = get_services()

                    # 2回目の呼び出し（キャッシュされているはず）
                    chat2, session2, llm2 = get_services()

                    # LLMServiceは1回しか呼ばれない
                    assert mock_llm.call_count == 1
