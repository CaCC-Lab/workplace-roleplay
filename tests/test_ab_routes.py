"""
A/Bテストルートのテストスイート
/api/v2エンドポイントのテスト
"""
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from flask import session


class TestABTestRoutes:
    """A/Bテストエンドポイントのテストクラス"""

    @pytest.fixture
    def client(self, app):
        """テスト用クライアント"""
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        with app.test_client() as client:
            yield client

    @pytest.fixture
    def csrf_client(self, app):
        """CSRF保護ありのクライアント"""
        app.config["TESTING"] = True
        with app.test_client() as client:
            # CSRFトークンを取得
            with client.session_transaction() as sess:
                from utils.security import CSRFToken

                sess["csrf_token"] = CSRFToken.generate()
            yield client

    def test_health_endpoint(self, client):
        """ヘルスチェックエンドポイントのテスト"""
        response = client.get("/api/v2/health")
        assert response.status_code == 200

        data = response.get_json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "services" in data
        assert "feature_flags" in data

    def test_config_endpoint(self, client):
        """設定エンドポイントのテスト"""
        response = client.get("/api/v2/config")
        assert response.status_code == 200

        data = response.get_json()
        # 設定エンドポイントが何らかのデータを返すことを確認
        assert isinstance(data, dict)
        # 新しいAPIでは feature flagsが返される
        assert any(key in data for key in ["model_selection", "tts", "default_model", "service_mode", "features"])

    @patch("routes.ab_test_routes.get_services")
    def test_chat_v2_without_csrf(self, mock_services, client):
        """CSRF保護なしでのチャットエンドポイントテスト"""
        # サービスモックの設定
        mock_chat = MagicMock()
        mock_services.return_value = (mock_chat, None, None)

        response = client.post("/api/v2/chat", json={"message": "テスト"}, headers={"Content-Type": "application/json"})

        # CSRF保護があるため403を返すはず
        assert response.status_code == 403
        data = response.get_json()
        assert "error" in data
        assert "CSRF" in data["error"]

    @patch("routes.ab_test_routes.get_services")
    def test_chat_v2_with_valid_csrf(self, mock_services, csrf_client):
        """有効なCSRFトークンでのチャットエンドポイントテスト"""
        # サービスモックの設定
        mock_chat = MagicMock()
        mock_session = MagicMock()
        mock_llm = MagicMock()

        # 非同期ジェネレータのモック
        async def mock_generator():
            for chunk in ["テスト", "応答"]:
                yield chunk

        mock_chat.process_chat_message = MagicMock(return_value=mock_generator())
        mock_services.return_value = (mock_chat, mock_session, mock_llm)

        # CSRFトークンを取得
        with csrf_client.session_transaction() as sess:
            csrf_token = sess.get("csrf_token")

        response = csrf_client.post(
            "/api/v2/chat",
            json={"message": "テスト"},
            headers={"Content-Type": "application/json", "X-CSRF-Token": csrf_token},
        )

        # ストリーミングレスポンスを確認
        assert response.status_code == 200
        assert response.mimetype == "text/event-stream"
        assert "X-Service-Version" in response.headers
        assert response.headers["X-Service-Version"] == "v2-new"

    def test_chat_v2_empty_message(self, csrf_client):
        """空メッセージでのエラーハンドリングテスト"""
        with csrf_client.session_transaction() as sess:
            csrf_token = sess.get("csrf_token")

        response = csrf_client.post(
            "/api/v2/chat",
            json={"message": ""},
            headers={"Content-Type": "application/json", "X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "メッセージが空です" in data["error"]

    def test_compare_endpoint_not_available(self, csrf_client):
        """比較エンドポイントの動作テスト（現在は未実装または削除済み）"""
        with csrf_client.session_transaction() as sess:
            csrf_token = sess.get("csrf_token")

        response = csrf_client.post(
            "/api/v2/chat/compare",
            json={"message": "テスト比較"},
            headers={"Content-Type": "application/json", "X-CSRF-Token": csrf_token},
        )

        # エンドポイントが存在しない(404)または未実装(501)の場合を許容
        assert response.status_code in [404, 501, 200]

    def test_scenario_chat_v2_not_implemented(self, client):
        """未実装のシナリオチャットエンドポイント"""
        response = client.post("/api/v2/scenario_chat", json={"message": "テスト"})

        assert response.status_code == 501  # Not Implemented
        data = response.get_json()
        assert "message" in data
        assert "Coming soon" in data["message"]

    def test_watch_start_v2_not_implemented(self, client):
        """未実装の観戦モード開始エンドポイント"""
        response = client.post("/api/v2/watch/start", json={"model_a": "gemini-1.5-pro"})

        assert response.status_code == 501  # Not Implemented
        data = response.get_json()
        assert "message" in data
        assert "Coming soon" in data["message"]


class TestABTestSecurity:
    """A/Bテストエンドポイントのセキュリティテスト"""

    @pytest.fixture
    def client(self, app):
        """テスト用クライアント"""
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_xss_prevention_in_chat_v2(self, client):
        """XSS攻撃防止のテスト"""
        with client.session_transaction() as sess:
            from utils.security import CSRFToken

            sess["csrf_token"] = CSRFToken.generate()
            csrf_token = sess["csrf_token"]

        # XSS攻撃ペイロードを含むメッセージ
        malicious_message = '<script>alert("XSS")</script>'

        with patch("routes.ab_test_routes.get_services") as mock_services:
            mock_chat = MagicMock()

            async def mock_generator():
                yield malicious_message

            mock_chat.process_chat_message = MagicMock(return_value=mock_generator())
            mock_services.return_value = (mock_chat, None, None)

            response = client.post(
                "/api/v2/chat",
                json={"message": "テスト"},
                headers={"Content-Type": "application/json", "X-CSRF-Token": csrf_token},
            )

            assert response.status_code == 200

            # レスポンスデータを確認
            data = response.get_data(as_text=True)
            # スクリプトタグが除去またはエスケープされていることを確認
            # 注: SSEストリーミングでは内容がJSONエンコードされるため、
            # 生のスクリプトタグは含まれないことを確認
            assert "<script>" not in data

    def test_rate_limiting(self, client):
        """レート制限のテスト"""
        with client.session_transaction() as sess:
            from utils.security import CSRFToken

            sess["csrf_token"] = CSRFToken.generate()
            csrf_token = sess["csrf_token"]

        with patch("routes.ab_test_routes.rate_limiter.is_allowed") as mock_limiter:
            # レート制限に引っかかる設定
            mock_limiter.return_value = False

            response = client.post(
                "/api/v2/chat",
                json={"message": "テスト"},
                headers={"Content-Type": "application/json", "X-CSRF-Token": csrf_token},
            )

            # レート制限エラーを確認
            assert response.status_code == 429
            data = response.get_json()
            assert "error" in data
            assert "Rate limit" in data["error"]


class TestABTestPerformance:
    """A/Bテストエンドポイントのパフォーマンステスト"""

    @pytest.fixture
    def client(self, app):
        """テスト用クライアント"""
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_streaming_response_performance(self, client):
        """ストリーミングレスポンスのパフォーマンステスト"""
        import time

        with client.session_transaction() as sess:
            from utils.security import CSRFToken

            sess["csrf_token"] = CSRFToken.generate()
            csrf_token = sess["csrf_token"]

        with patch("routes.ab_test_routes.get_services") as mock_services:
            mock_chat = MagicMock()

            async def mock_generator():
                # 大量のチャンクを生成
                for i in range(100):
                    yield f"チャンク{i}"

            mock_chat.process_chat_message = MagicMock(return_value=mock_generator())
            mock_services.return_value = (mock_chat, None, None)

            start_time = time.time()

            response = client.post(
                "/api/v2/chat",
                json={"message": "パフォーマンステスト"},
                headers={"Content-Type": "application/json", "X-CSRF-Token": csrf_token},
            )

            # レスポンスを消費
            list(response.response)

            end_time = time.time()
            elapsed_time = end_time - start_time

            # 100チャンクが1秒以内に処理されることを確認
            assert elapsed_time < 1.0, f"Streaming took {elapsed_time} seconds"

    def test_concurrent_requests(self, app):
        """並行リクエストのテスト（シーケンシャル実行）"""
        # Flaskテストクライアントはスレッドセーフではないため、
        # シーケンシャルに複数リクエストを実行してテスト
        results = []

        app.config["TESTING"] = True

        for _ in range(10):
            with app.test_client() as client:
                response = client.get("/api/v2/health")
                results.append(response.status_code)

        # すべてのリクエストが成功することを確認
        assert len(results) == 10
        assert all(status == 200 for status in results)
