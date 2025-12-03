"""
Watch routes tests for improved coverage.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestWatchModePage:
    """GET /watch のテスト"""

    def test_観戦モードページを表示(self, client):
        """観戦モードページの表示"""
        response = client.get("/watch")

        assert response.status_code == 200


class TestStartWatch:
    """POST /api/watch/start のテスト"""

    def test_観戦モードを正常に開始(self, csrf_client):
        """観戦モードの正常な開始"""
        with patch("app.initialize_llm") as mock_llm:
            mock_llm_instance = MagicMock()
            mock_llm.return_value = mock_llm_instance

            with patch("services.watch_service.WatchService.generate_initial_message") as mock_gen:
                mock_gen.return_value = "こんにちは！今日はいい天気ですね。"

                response = csrf_client.post(
                    "/api/watch/start",
                    json={
                        "model_a": "gemini-1.5-flash",
                        "model_b": "gemini-1.5-pro",
                        "partner_type": "colleague",
                        "situation": "break",
                        "topic": "general",
                    },
                )

                assert response.status_code == 200
                data = response.get_json()
                assert "message" in data
                assert "太郎:" in data["message"]

    def test_無効なリクエストでエラー(self, csrf_client):
        """無効なリクエストでエラーを返す"""
        response = csrf_client.post("/api/watch/start", json=None)

        # 無効なリクエストは400または500を返す
        assert response.status_code in [400, 500]

    def test_無効なモデルAでエラー(self, csrf_client):
        """無効なモデルA名でエラー"""
        with patch("routes.watch_routes.SecurityUtils") as mock_security:
            mock_security.validate_model_name.return_value = False

            response = csrf_client.post(
                "/api/watch/start",
                json={
                    "model_a": "invalid!!!",
                    "model_b": "gemini-1.5-pro",
                },
            )

            assert response.status_code == 400

    def test_LLM初期化エラー時(self, csrf_client):
        """LLM初期化でエラーが発生した場合"""
        with patch("app.initialize_llm") as mock_llm:
            mock_llm.side_effect = Exception("LLM initialization failed")

            response = csrf_client.post(
                "/api/watch/start",
                json={
                    "model_a": "gemini-1.5-flash",
                    "model_b": "gemini-1.5-pro",
                    "partner_type": "colleague",
                    "situation": "break",
                    "topic": "general",
                },
            )

            # エラーが適切に処理されること
            assert response.status_code in [500, 503]


class TestNextWatchMessage:
    """POST /api/watch/next のテスト"""

    def test_次のメッセージを正常に生成(self, csrf_client):
        """次のメッセージの正常な生成"""
        with csrf_client.session_transaction() as sess:
            sess["watch_settings"] = {
                "model_a": "gemini-1.5-flash",
                "model_b": "gemini-1.5-pro",
                "partner_type": "colleague",
                "situation": "break",
                "topic": "general",
                "current_speaker": "A",
            }
            sess["watch_history"] = [
                {
                    "speaker": "A",
                    "message": "こんにちは！",
                    "timestamp": "2024-01-01T10:00:00",
                }
            ]

        with patch("app.initialize_llm") as mock_llm:
            mock_llm_instance = MagicMock()
            mock_llm.return_value = mock_llm_instance

            with patch("services.watch_service.WatchService.generate_next_message") as mock_gen:
                mock_gen.return_value = "こんにちは！良い天気ですね。"

                response = csrf_client.post("/api/watch/next", json={})

                assert response.status_code == 200
                data = response.get_json()
                assert "message" in data

    def test_セッション未初期化でエラー(self, csrf_client):
        """セッション未初期化でエラー"""
        response = csrf_client.post("/api/watch/next", json={})

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_LLMエラー時の処理(self, csrf_client):
        """LLMでエラーが発生した場合の処理"""
        with csrf_client.session_transaction() as sess:
            sess["watch_settings"] = {
                "model_a": "gemini-1.5-flash",
                "model_b": "gemini-1.5-pro",
                "partner_type": "colleague",
                "situation": "break",
                "topic": "general",
                "current_speaker": "A",
            }
            sess["watch_history"] = [
                {
                    "speaker": "A",
                    "message": "こんにちは！",
                    "timestamp": "2024-01-01T10:00:00",
                }
            ]

        with patch("app.initialize_llm") as mock_llm:
            mock_llm.side_effect = Exception("429 Resource has been exhausted")

            response = csrf_client.post("/api/watch/next", json={})

            # エラーが適切に処理されること
            assert response.status_code in [429, 500, 503]

    def test_スピーカー切り替え(self, csrf_client):
        """スピーカーが正しく切り替わることを確認"""
        with csrf_client.session_transaction() as sess:
            sess["watch_settings"] = {
                "model_a": "gemini-1.5-flash",
                "model_b": "gemini-1.5-pro",
                "partner_type": "colleague",
                "situation": "break",
                "topic": "general",
                "current_speaker": "A",
            }
            sess["watch_history"] = [{"speaker": "A", "message": "テスト", "timestamp": "2024-01-01"}]

        with patch("app.initialize_llm") as mock_llm:
            mock_llm_instance = MagicMock()
            mock_llm.return_value = mock_llm_instance

            with patch("services.watch_service.WatchService.generate_next_message") as mock_gen:
                mock_gen.return_value = "返答です"

                response = csrf_client.post("/api/watch/next", json={})

                assert response.status_code == 200
                data = response.get_json()
                # 花子（スピーカーB）の返答
                assert "花子:" in data["message"]
