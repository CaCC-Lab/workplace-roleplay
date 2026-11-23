"""
Gemini モデル一覧の取得と既定モデルの定義
"""

import re
from typing import List, Optional

DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"

FALLBACK_GEMINI_MODELS = [
    f"gemini/{DEFAULT_GEMINI_MODEL}",
    "gemini/gemini-3.6-flash",
    "gemini/gemini-3.5-flash-lite",
]

# gemini-<version>[-<variant>...] 形式（例: gemini-3.8-flash, gemini-4-neon, gemini-1.5-flash-001）
_GEMINI_MODEL_PATTERN = re.compile(r"^gemini-\d+(\.\d+)?(-[a-z0-9]+(\.[a-z0-9]+)*)*$")

# 会話に使えない Gemini 系モデル（音声合成・画像生成・埋め込み等）
_NON_CHAT_KEYWORDS = ("tts", "image", "embedding", "live", "audio", "aqa")


def _is_chat_model(model) -> bool:
    name = (getattr(model, "name", "") or "").lower()
    if "gemini" not in name or any(keyword in name for keyword in _NON_CHAT_KEYWORDS):
        return False
    actions = getattr(model, "supported_actions", None)
    return not actions or "generateContent" in actions


def list_gemini_model_ids(api_key: Optional[str]) -> List[str]:
    """
    google-genai SDK で会話に使える Gemini モデルを "gemini/<name>" 形式で返す

    Args:
        api_key: Google API キー

    Returns:
        List[str]: モデル ID のリスト

    Raises:
        Exception: API 呼び出しに失敗した場合
    """
    if not api_key:
        return []

    from google import genai

    client = genai.Client(api_key=api_key)
    return [f"gemini/{model.name.split('/')[-1]}" for model in client.models.list() if _is_chat_model(model)]


def is_valid_gemini_model_name(model_name: str) -> bool:
    """gemini/ 接頭辞の有無を問わず、Gemini のモデル名として正しい形式か"""
    if model_name.startswith("gemini/"):
        model_name = model_name[len("gemini/") :]
    return bool(_GEMINI_MODEL_PATTERN.match(model_name))


def supports_sampling_parameters(model_name: str) -> bool:
    """temperature などを受け付けるのは Gemini 2 系まで（3 系以降は非推奨）"""
    return model_name.startswith(("gemini-1", "gemini-2"))
