"""
モード別モデル解決ヘルパー（Phase B）

優先順位:
    1. session_selected（UI で選択されたモデル）
    2. <MODE>_MODEL 環境変数
    3. DEFAULT_MODEL

モードは以下の4種類:
    - scenario : シナリオロールプレイ
    - chat     : 雑談
    - watch    : 観戦モード
    - feedback : フィードバック生成
"""
from __future__ import annotations

import os
from typing import Optional

from config import get_config

# モード名 → 環境変数名 のマッピング
_MODE_ENV_MAP = {
    "scenario": "SCENARIO_MODEL",
    "chat": "CHAT_MODEL",
    "watch": "WATCH_MODEL",
    "feedback": "FEEDBACK_MODEL",
}


def resolve_model(mode: str, session_selected: Optional[str] = None) -> str:
    """モード別にモデル名を解決する。

    Args:
        mode: "scenario" | "chat" | "watch" | "feedback"
        session_selected: UI で選択されたモデル名（あれば最優先）

    Returns:
        解決されたモデル名（例: "ollama/gemma4:31b-cloud"）

    Raises:
        ValueError: 未知の mode が渡された場合
    """
    if mode not in _MODE_ENV_MAP:
        raise ValueError(
            f"Unknown mode: {mode!r}. "
            f"Expected one of: {sorted(_MODE_ENV_MAP.keys())}"
        )

    # 1. session_selected が最優先
    if session_selected:
        selected = session_selected.strip()
        if selected:
            return selected

    # 2. <MODE>_MODEL env
    env_key = _MODE_ENV_MAP[mode]
    env_value = (os.environ.get(env_key) or "").strip()
    if env_value:
        return env_value

    # 3. DEFAULT_MODEL フォールバック
    return get_config().DEFAULT_MODEL
