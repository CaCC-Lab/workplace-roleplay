"""
utils.runtime のユニットテスト
"""

import tempfile
from pathlib import Path

from utils.runtime import is_serverless, local_data_dir


def test_通常環境ではカレントディレクトリ配下(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)

    assert is_serverless() is False
    assert local_data_dir("user_data") == Path("user_data")


def test_Vercelでは一時ディレクトリ配下(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")

    assert is_serverless() is True
    assert local_data_dir("user_data") == Path(tempfile.gettempdir()) / "user_data"
