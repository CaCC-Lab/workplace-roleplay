"""
MultilingualTTSService のユニットテスト
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.multilingual_tts_service import MultilingualTTSService


@pytest.fixture
def svc():
    return MultilingualTTSService()


class TestSupportedLanguages:
    def test_includes_japanese(self, svc):
        langs = svc.get_supported_languages()
        codes = {x["code"] for x in langs}
        assert "ja" in codes

    def test_includes_other_languages_en_zh_ko(self, svc):
        langs = svc.get_supported_languages()
        codes = {x["code"] for x in langs}
        assert "en" in codes
        assert "zh" in codes
        assert "ko" in codes
        for row in langs:
            assert "name" in row
            assert "native_name" in row


class TestLanguageSupport:
    def test_unknown_language_not_supported(self, svc):
        assert svc.is_language_supported("xx") is False
        assert svc.is_language_supported("") is False


class TestVoiceForLanguage:
    def test_voice_has_required_keys(self, svc):
        v = svc.get_voice_for_language("ja")
        assert "voice_id" in v
        assert "name" in v
        assert "gender" in v
        assert len(v["voice_id"]) > 0


class TestSynthesizeText:
    def test_empty_text_returns_without_exception(self, svc):
        r = svc.synthesize_text("", "ja")
        assert isinstance(r, dict)
        assert "success" in r
        assert "audio_data_or_error" in r
        assert r["success"] is False

    def test_empty_whitespace_only(self, svc):
        r = svc.synthesize_text("   ", "ja")
        assert r["success"] is False
