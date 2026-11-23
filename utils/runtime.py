"""
実行環境の判定と、書き込み可能なローカルディレクトリの解決
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def is_serverless() -> bool:
    """Vercel などファイルシステムが読み取り専用のサーバーレス環境で動いているか"""
    return bool(os.environ.get("VERCEL"))


def local_data_dir(name: str) -> Path:
    """ローカル保存用ディレクトリ（サーバーレスでは書き込める一時領域を使う）"""
    if is_serverless():
        return Path(tempfile.gettempdir()) / name
    return Path(name)
