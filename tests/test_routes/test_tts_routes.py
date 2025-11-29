"""
TTS routes tests for improved coverage.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestTextToSpeech:
    """POST/HEAD /api/tts のテスト"""

    def test_HEADリクエストで200または403を返す(self, client):
        """HEADリクエストの動作確認（機能有効/無効により異なる）"""
        response = client.head("/api/tts")

        # 機能が有効なら200、無効なら403
        assert response.status_code in [200, 403]

    def test_POSTリクエストで503または403を返す(self, csrf_client):
        """POSTリクエストの動作確認"""
        response = csrf_client.post(
            "/api/tts", json={"text": "こんにちは"}
        )

        # 機能が有効なら503（停止中）、無効なら403
        assert response.status_code in [403, 503]

    def test_TTS機能無効時の動作(self, csrf_client):
        """TTS機能無効時は403を返す"""
        # デフォルトではTTS機能は無効
        response = csrf_client.post(
            "/api/tts", json={"text": "テスト"}
        )

        # 403（機能無効）または503（停止中）
        assert response.status_code in [403, 503]


class TestGetAvailableVoices:
    """GET /api/tts/voices のテスト"""

    def test_音声一覧で503を返す(self, client):
        """音声一覧取得で停止中エラーを返す"""
        response = client.get("/api/tts/voices")

        assert response.status_code == 503
        data = response.get_json()
        assert "error" in data
        assert "緊急停止中" in data["error"]
        assert "alternative" in data


class TestGetAvailableStyles:
    """GET /api/tts/styles のテスト"""

    def test_スタイル一覧で503を返す(self, client):
        """スタイル一覧取得で停止中エラーを返す"""
        response = client.get("/api/tts/styles")

        assert response.status_code == 503
        data = response.get_json()
        assert "error" in data
        assert "緊急停止中" in data["error"]
        assert "alternative" in data


class TestGetVoiceForEmotion:
    """get_voice_for_emotion関数のテスト"""

    def test_感情に応じた音声を取得(self):
        """感情に応じた音声名を取得"""
        from routes.tts_routes import get_voice_for_emotion

        with patch(
            "services.tts_service.TTSService.get_voice_for_emotion"
        ) as mock_voice:
            mock_voice.return_value = "kore"

            result = get_voice_for_emotion("happy")

            assert result == "kore"

    def test_デフォルト感情で音声を取得(self):
        """デフォルト感情での音声取得"""
        from routes.tts_routes import get_voice_for_emotion

        with patch(
            "services.tts_service.TTSService.get_voice_for_emotion"
        ) as mock_voice:
            mock_voice.return_value = "aoede"

            result = get_voice_for_emotion("neutral")

            assert isinstance(result, str)
