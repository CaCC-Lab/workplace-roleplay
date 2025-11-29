"""
TTS (Text-to-Speech) service for the workplace-roleplay application.
NOTE: TTS functionality is currently disabled due to high costs.
"""

from typing import Any, Dict, Optional


class TTSService:
    """TTS関連のビジネスロジックを処理するサービス"""

    def get_voice_for_emotion(self, emotion: str) -> str:
        """
        感情に最適な音声を選択

        Args:
            emotion: 感情（happy, sad, angry等）

        Returns:
            str: 音声名
        """
        emotion_voice_map = {
            "happy": "autonoe",
            "excited": "fenrir",
            "sad": "vindemiatrix",
            "tired": "enceladus",
            "angry": "algenib",
            "worried": "achernar",
            "calm": "schedar",
            "confident": "alnilam",
            "professional": "orus",
            "friendly": "achird",
            "whisper": "enceladus",
            "spooky": "umbriel",
        }
        return emotion_voice_map.get(emotion, "kore")

    def generate_tts(
        self,
        text: str,
        voice_name: str = "kore",
        voice_style: Optional[str] = None,
        emotion: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        テキストを音声に変換（現在は停止中）

        Args:
            text: 変換するテキスト
            voice_name: 音声名
            voice_style: 音声スタイル（オプション）
            emotion: 感情（オプション）

        Returns:
            Dict[str, Any]: エラーレスポンス（機能停止中）
        """
        return {
            "error": "TTS機能は現在停止中です",
            "message": "高額請求が発生したため、TTS機能を停止しています。",
            "details": {
                "cost": "250,000円 ($1,667)",
                "characters": "16,675,000文字の音声生成",
                "requests": "約166,750回のリクエスト",
            },
            "alternative": "ブラウザ内蔵のWeb Speech APIをご利用ください",
            "fallback_available": True,
        }


# グローバルインスタンス
_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """TTSServiceのシングルトンインスタンスを取得"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
