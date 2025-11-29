"""
TTS service tests for improved coverage.
"""

import pytest
from services.tts_service import TTSService, get_tts_service


class TestTTSService:
    """TTSServiceクラスのテスト"""

    def test_happy感情で音声を取得(self):
        """happy感情で適切な音声を取得"""
        service = TTSService()
        result = service.get_voice_for_emotion("happy")

        assert result == "autonoe"

    def test_excited感情で音声を取得(self):
        """excited感情で適切な音声を取得"""
        service = TTSService()
        result = service.get_voice_for_emotion("excited")

        assert result == "fenrir"

    def test_sad感情で音声を取得(self):
        """sad感情で適切な音声を取得"""
        service = TTSService()
        result = service.get_voice_for_emotion("sad")

        assert result == "vindemiatrix"

    def test_tired感情で音声を取得(self):
        """tired感情で適切な音声を取得"""
        service = TTSService()
        result = service.get_voice_for_emotion("tired")

        assert result == "enceladus"

    def test_angry感情で音声を取得(self):
        """angry感情で適切な音声を取得"""
        service = TTSService()
        result = service.get_voice_for_emotion("angry")

        assert result == "algenib"

    def test_worried感情で音声を取得(self):
        """worried感情で適切な音声を取得"""
        service = TTSService()
        result = service.get_voice_for_emotion("worried")

        assert result == "achernar"

    def test_calm感情で音声を取得(self):
        """calm感情で適切な音声を取得"""
        service = TTSService()
        result = service.get_voice_for_emotion("calm")

        assert result == "schedar"

    def test_confident感情で音声を取得(self):
        """confident感情で適切な音声を取得"""
        service = TTSService()
        result = service.get_voice_for_emotion("confident")

        assert result == "alnilam"

    def test_professional感情で音声を取得(self):
        """professional感情で適切な音声を取得"""
        service = TTSService()
        result = service.get_voice_for_emotion("professional")

        assert result == "orus"

    def test_friendly感情で音声を取得(self):
        """friendly感情で適切な音声を取得"""
        service = TTSService()
        result = service.get_voice_for_emotion("friendly")

        assert result == "achird"

    def test_whisper感情で音声を取得(self):
        """whisper感情で適切な音声を取得"""
        service = TTSService()
        result = service.get_voice_for_emotion("whisper")

        assert result == "enceladus"

    def test_spooky感情で音声を取得(self):
        """spooky感情で適切な音声を取得"""
        service = TTSService()
        result = service.get_voice_for_emotion("spooky")

        assert result == "umbriel"

    def test_不明な感情でデフォルト音声(self):
        """不明な感情でデフォルト音声を取得"""
        service = TTSService()
        result = service.get_voice_for_emotion("unknown")

        assert result == "kore"

    def test_TTS生成は停止中エラーを返す(self):
        """TTS生成は停止中エラーを返す"""
        service = TTSService()
        result = service.generate_tts("テスト")

        assert "error" in result
        assert "停止中" in result["error"]
        assert "fallback_available" in result
        assert result["fallback_available"] is True

    def test_TTS生成のエラー詳細(self):
        """TTS生成のエラー詳細を確認"""
        service = TTSService()
        result = service.generate_tts("テスト", voice_name="aoede", emotion="happy")

        assert "details" in result
        assert "cost" in result["details"]
        assert "alternative" in result


class TestGetTTSService:
    """get_tts_service関数のテスト"""

    def test_シングルトンインスタンスを取得(self):
        """シングルトンインスタンスを取得"""
        service1 = get_tts_service()
        service2 = get_tts_service()

        assert service1 is service2
        assert isinstance(service1, TTSService)
