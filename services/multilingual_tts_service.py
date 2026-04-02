"""
多言語 TTS のメタデータと合成エントリ（実音声は外部エンジン連携想定）
"""

from __future__ import annotations

from typing import Dict, List

_SUPPORTED_LANGUAGES: List[Dict[str, str]] = [
    {"code": "ja", "name": "Japanese", "native_name": "日本語"},
    {"code": "en", "name": "English", "native_name": "English"},
    {"code": "zh", "name": "Chinese (Mandarin)", "native_name": "中文"},
    {"code": "ko", "name": "Korean", "native_name": "한국어"},
]

_VOICES: Dict[str, Dict[str, str]] = {
    "ja": {
        "voice_id": "ja-JP-Neural2-A",
        "name": "Japanese Neural 2 A",
        "gender": "female",
    },
    "en": {
        "voice_id": "en-US-Neural2-D",
        "name": "English US Neural 2 D",
        "gender": "male",
    },
    "zh": {
        "voice_id": "cmn-CN-Neural2-A",
        "name": "Mandarin Neural 2 A",
        "gender": "female",
    },
    "ko": {
        "voice_id": "ko-KR-Neural2-A",
        "name": "Korean Neural 2 A",
        "gender": "female",
    },
}


class MultilingualTTSService:
    """対応言語・音声の参照と合成リクエストの結果整形。"""

    def get_supported_languages(self) -> List[dict]:
        return [dict(x) for x in _SUPPORTED_LANGUAGES]

    def is_language_supported(self, lang_code: str) -> bool:
        if not lang_code:
            return False
        code = str(lang_code).strip().lower().replace("_", "-")
        # 先頭2文字で zh-CN 等にも対応
        primary = code.split("-")[0]
        return any(
            x["code"] == code or x["code"] == primary
            for x in _SUPPORTED_LANGUAGES
        )

    def get_voice_for_language(self, lang_code: str) -> dict:
        code = self._normalize_lang(lang_code)
        if code not in _VOICES:
            return {
                "voice_id": "",
                "name": "",
                "gender": "unspecified",
            }
        return dict(_VOICES[code])

    def synthesize_text(self, text: str, lang_code: str) -> dict:
        """
        Returns:
            success: bool
            audio_data_or_error: バイト列またはメッセージ文字列
        """
        try:
            if not (text or "").strip():
                return {
                    "success": False,
                    "audio_data_or_error": "empty_text",
                }
            if not self.is_language_supported(lang_code):
                return {
                    "success": False,
                    "audio_data_or_error": "unsupported_language",
                }
            # 実エンジン未接続時はプレースホルダ（例外は出さない）
            return {
                "success": True,
                "audio_data_or_error": b"",
            }
        except Exception as exc:
            return {
                "success": False,
                "audio_data_or_error": str(exc),
            }

    def _normalize_lang(self, lang_code: str) -> str:
        if not lang_code:
            return ""
        code = str(lang_code).strip().lower().replace("_", "-")
        primary = code.split("-")[0]
        if code in _VOICES:
            return code
        if primary in _VOICES:
            return primary
        return code
