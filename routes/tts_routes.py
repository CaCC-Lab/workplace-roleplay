"""
TTS (Text-to-Speech) routes for the workplace-roleplay application.
NOTE: TTS functionality is currently disabled due to high costs.
"""

from config.feature_flags import require_feature
from flask import Blueprint, jsonify, request

from errors import with_error_handling

# Blueprint作成
tts_bp = Blueprint("tts", __name__)


from services.tts_service import get_tts_service


def get_voice_for_emotion(emotion: str) -> str:
    """感情に最適な音声を選択する（サービス層経由）"""
    tts_service = get_tts_service()
    return tts_service.get_voice_for_emotion(emotion)


@tts_bp.route("/api/tts", methods=["POST", "HEAD"])
@require_feature("tts")
@with_error_handling
def text_to_speech():
    """
    テキストを音声に変換するAPI

    NOTE: TTS機能は高額請求により現在停止中

    HEADリクエスト: フロントエンドでの軽量状態チェック用
    POSTリクエスト: 実際のTTS生成（現在は停止中）
    """
    # HEADリクエストの場合は軽量レスポンス
    if request.method == "HEAD":
        return "", 200

    # POSTリクエストの場合は詳細なエラー情報を返す
    return (
        jsonify(
            {
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
        ),
        503,
    )


@tts_bp.route("/api/tts/voices", methods=["GET"])
def get_available_voices():
    """
    EMERGENCY SHUTDOWN: TTS機能は高額請求により停止中
    """
    return (
        jsonify(
            {
                "error": "TTS音声機能は高額請求により緊急停止中",
                "message": "Gemini TTSで25万円の請求が発生したため、全TTS機能を停止しました",
                "alternative": "ブラウザ内蔵のWeb Speech APIを使用してください",
            }
        ),
        503,
    )


@tts_bp.route("/api/tts/styles", methods=["GET"])
def get_available_styles():
    """
    EMERGENCY SHUTDOWN: TTS機能は高額請求により停止中
    """
    return (
        jsonify(
            {
                "error": "TTSスタイル機能は高額請求により緊急停止中",
                "message": "Gemini TTSで25万円の請求が発生したため、全TTS機能を停止しました",
                "alternative": "ブラウザ内蔵のWeb Speech APIを使用してください",
            }
        ),
        503,
    )


# 以下は将来的にTTS機能を復活させる場合のための参照コード
"""
TTS機能のフル実装（停止中）

@tts_bp.route("/api/tts", methods=["POST", "HEAD"])
@require_feature('tts')
@with_error_handling
def text_to_speech_full():
    if request.method == "HEAD":
        return "", 200

    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON"}), 400

    text = data.get("text", "")
    if not text:
        return jsonify({"error": "テキストが必要です"}), 400

    voice_name = data.get("voice", "kore")
    voice_style = data.get("style", None)
    emotion = data.get("emotion", None)

    # Gemini TTS APIを使用した音声生成ロジック
    # ... (停止中)

    return jsonify({
        "audio": audio_content,
        "format": "wav",
        "voice": voice_name,
        "provider": "gemini"
    })
"""
