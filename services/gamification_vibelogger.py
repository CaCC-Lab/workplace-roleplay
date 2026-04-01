"""
ゲーミフィケーション用 vibelogger（テストでは GAMIFICATION_VIBE_LOG_FILE で出力先を固定）
"""

from __future__ import annotations

import os
from typing import Any, Optional

_vibe: Any = None


def reset_gamification_vibe_logger() -> None:
    """テスト用: シングルトンをクリアする"""
    global _vibe
    _vibe = None


def get_gamification_vibe_logger() -> Any:
    """vibelogger インスタンス（環境変数 GAMIFICATION_VIBE_LOG_FILE でファイルパスを上書き可能）"""
    global _vibe
    if _vibe is not None:
        return _vibe
    from vibelogger import VibeLogger, create_file_logger
    from vibelogger.config import VibeLoggerConfig

    path: Optional[str] = os.environ.get("GAMIFICATION_VIBE_LOG_FILE")
    if path:
        _vibe = VibeLogger(
            VibeLoggerConfig(
                log_file=path,
                auto_save=True,
                create_dirs=True,
                max_file_size_mb=10,
            )
        )
    else:
        _vibe = create_file_logger("workplace_gamification")
    return _vibe
