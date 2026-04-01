"""
ゲーミフィケーション関連の共有定数・ユーティリティ
"""

from __future__ import annotations

from datetime import datetime, timezone

SIX_AXES = (
    "empathy",
    "clarity",
    "active_listening",
    "adaptability",
    "positivity",
    "professionalism",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
