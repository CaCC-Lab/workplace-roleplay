"""
入力値検証関連のユーティリティ関数
"""
import re
from typing import Any, List, Optional, Tuple


def validate_message_content(content: Any, max_length: int = 4000) -> Tuple[bool, Optional[str]]:
    """
    メッセージ内容の検証

    Args:
        content: 検証する内容
        max_length: 最大文字数

    Returns:
        (有効かどうか, エラーメッセージ)
    """
    if content is None:
        return False, "メッセージ内容が必要です"

    if not isinstance(content, str):
        return False, "メッセージは文字列である必要があります"

    if len(content.strip()) == 0:
        return False, "メッセージが空です"

    if len(content) > max_length:
        return False, f"メッセージが長すぎます（最大{max_length}文字）"

    # HTMLタグのチェック
    if re.search(r"<[^>]+>", content):
        return False, "HTMLタグは使用できません"

    return True, None


def validate_scenario_id(scenario_id: Any) -> Tuple[bool, Optional[str]]:
    """
    シナリオIDの検証

    Args:
        scenario_id: 検証するシナリオID

    Returns:
        (有効かどうか, エラーメッセージ)
    """
    if scenario_id is None:
        return False, "シナリオIDが必要です"

    if not isinstance(scenario_id, str):
        return False, "シナリオIDは文字列である必要があります"

    # シナリオIDの形式チェック（英数字とハイフン、アンダースコアのみ）
    if not re.match(r"^[a-zA-Z0-9_-]+$", scenario_id):
        return False, "シナリオIDが無効です"

    return True, None


def validate_model_name(model_name: Any, allowed_models: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
    """
    モデル名の検証

    Args:
        model_name: 検証するモデル名
        allowed_models: 許可されたモデルのリスト

    Returns:
        (有効かどうか, エラーメッセージ)
    """
    if model_name is None:
        return False, "モデル名が必要です"

    if not isinstance(model_name, str):
        return False, "モデル名は文字列である必要があります"

    # デフォルトの許可モデルリスト（SecurityUtilsと同期）
    if allowed_models is None:
        allowed_models = [
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash-002",
            "gemini-1.5-flash-8b",
            "gemini-1.5-pro",
            "gemini-1.5-pro-latest",
            "gemini-1.5-pro-002",
            "gemini-1.0-pro",
            "gemini-2.0-flash",
            "gemini-2.0-flash-exp",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",  # 追加！Geminiで存在確認済み
            "gemini-2.5-pro",
        ]

    if model_name not in allowed_models:
        return False, f"無効なモデル名です。使用可能: {', '.join(allowed_models)}"

    return True, None


def validate_voice_name(voice_name: Any, allowed_voices: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
    """
    音声名の検証

    Args:
        voice_name: 検証する音声名
        allowed_voices: 許可された音声のリスト

    Returns:
        (有効かどうか, エラーメッセージ)
    """
    if voice_name is None:
        return True, None  # 音声名はオプション

    if not isinstance(voice_name, str):
        return False, "音声名は文字列である必要があります"

    # デフォルトの許可音声リスト（一部抜粋）
    if allowed_voices is None:
        allowed_voices = [
            "kore",
            "aoede",
            "callirrhoe",
            "leda",
            "algieba",
            "enceladus",
            "charon",
            "fenrir",
            "orus",
            "iapetus",
            "puck",
            "zephyr",
            "umbriel",
            "schedar",
        ]

    voice_lower = voice_name.lower()
    if voice_lower not in allowed_voices:
        return False, "無効な音声名です"

    return True, None


def validate_json_data(data: Any, required_fields: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
    """
    JSONデータの基本的な検証

    Args:
        data: 検証するデータ
        required_fields: 必須フィールドのリスト

    Returns:
        (有効かどうか, エラーメッセージ)
    """
    if data is None:
        return False, "データが必要です"

    if not isinstance(data, dict):
        return False, "データは辞書形式である必要があります"

    if required_fields:
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return False, f"必須フィールドが不足しています: {', '.join(missing_fields)}"

    return True, None


def sanitize_input(text: str) -> str:
    """
    入力テキストのサニタイズ

    Args:
        text: サニタイズするテキスト

    Returns:
        サニタイズされたテキスト
    """
    if not isinstance(text, str):
        return str(text)

    # 制御文字を削除
    text = re.sub(r"[\x00-\x1F\x7F]", "", text)

    # 連続する空白を単一の空白に
    text = re.sub(r"\s+", " ", text)

    # 前後の空白を削除
    text = text.strip()

    return text
